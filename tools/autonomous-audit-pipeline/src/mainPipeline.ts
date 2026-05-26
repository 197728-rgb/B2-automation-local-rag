import fs from "fs-extra";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { LlmClient } from "./llmClient.js";
import { analyzeDocxForm } from "./analystAgent.js";
import { gatherEvidence } from "./investigatorAgent.js";
import { synthesizeAnswer } from "./writerAgent.js";
import { validateAnswer } from "./validationGate.js";
import { writeCompletedDocx, prepareOutputCopy } from "./formWriter.js";
import { loadSourceDocumentsContext } from "./sourceLoader.js";
import { MachineFieldMapV1, PipelineAuditTrail } from "./schemas.js";
import {
  loadMockContext,
  mockAnalyzeDocxForm,
  mockGatherEvidence,
  mockSynthesizeAnswer,
} from "./mockAgents.js";

export async function executeAutonomousPipeline(
  blankFormPath: string,
  outputFormPath: string,
  availableSchemas: unknown[],
  sourceDocumentsContext: string,
  auditTrailOutputPath: string,
  options: { mock?: boolean } = {}
): Promise<PipelineAuditTrail> {
  const useMock = options.mock ?? !process.env.GEMINI_API_KEY;
  const client = useMock ? null : new LlmClient();

  if (useMock) {
    console.log("MOCK mode: deterministic field map and source snippets (no Gemini).");
  }

  console.log(`Phase 1: Structural form discovery on ${blankFormPath}...`);
  const fieldMap = useMock
    ? await mockAnalyzeDocxForm(blankFormPath)
    : await analyzeDocxForm(blankFormPath, availableSchemas, client!);

  await prepareOutputCopy(blankFormPath, outputFormPath);

  const auditTrail: PipelineAuditTrail = {
    pipelineVersion: "1.0.0-local-mvp",
    executionTimestamp: new Date().toISOString(),
    status: "completed",
    templateFile: blankFormPath,
    outputFile: outputFormPath,
    summaryMetrics: {
      totalFieldsProcessed: fieldMap.fields.length,
      successfullyFilled: 0,
      fallbackAppliedCount: 0,
      failedWritesCount: 0,
    },
    records: [],
  };

  console.log(`Phase 1 complete: ${fieldMap.fields.length} fields. Running stages 2-5...`);

  for (const field of fieldMap.fields) {
    console.log(`Processing: [${field.fieldLabel}]`);
    try {
      const evidence = useMock
        ? mockGatherEvidence(field, sourceDocumentsContext)
        : await gatherEvidence(field, sourceDocumentsContext, client!);
      const synthesis = useMock
        ? mockSynthesizeAnswer(field, evidence)
        : await synthesizeAnswer(field, evidence, client!);
      const validation = validateAnswer(field, synthesis);
      const writeResult = await writeCompletedDocx(field, validation, outputFormPath);

      if (validation.appliedFallback) auditTrail.summaryMetrics.fallbackAppliedCount++;
      if (writeResult.writeStatus === "success") {
        auditTrail.summaryMetrics.successfullyFilled++;
      } else {
        auditTrail.summaryMetrics.failedWritesCount++;
      }

      auditTrail.records.push({
        requirement: field,
        evidence,
        synthesis,
        validation,
        writeResult,
      });
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : String(error);
      auditTrail.summaryMetrics.failedWritesCount++;
      console.error(`Field ${field.id} failed: ${message}`);
    }
  }

  if (auditTrail.summaryMetrics.failedWritesCount > 0) {
    auditTrail.status = "failed";
  } else if (auditTrail.summaryMetrics.fallbackAppliedCount > 0) {
    auditTrail.status = "completed_with_low_confidence";
  }

  const auditDir = path.dirname(auditTrailOutputPath);
  await fs.ensureDir(auditDir);
  await fs.outputJson(auditTrailOutputPath, auditTrail, { spaces: 2 });

  const mapPath = path.join(auditDir, `${path.basename(blankFormPath, path.extname(blankFormPath))}_machine_field_map.v1.json`);
  await fs.outputJson(mapPath, fieldMap, { spaces: 2 });

  console.log(`Audit trail: ${auditTrailOutputPath}`);
  return auditTrail;
}

export async function runAuditorPipeline(
  blankFormPath: string,
  sourceFolder: string,
  outputDir: string,
  options: { mock?: boolean } = {}
): Promise<PipelineAuditTrail> {
  const schemasPath = path.join(path.dirname(blankFormPath), "available-schemas.json");
  let schemas: unknown[] = [];
  if (await fs.pathExists(schemasPath)) {
    schemas = await fs.readJson(schemasPath);
  }
  const context = options.mock ? loadMockContext(sourceFolder) : loadSourceDocumentsContext(sourceFolder);
  const stem = path.basename(blankFormPath, path.extname(blankFormPath));
  await fs.ensureDir(outputDir);
  const outDocx = path.join(outputDir, "completed", `${stem}_completed.docx`);
  const trailPath = path.join(outputDir, "audit-trail", `${stem}_pipeline_audit_trail.json`);
  return executeAutonomousPipeline(blankFormPath, outDocx, schemas, context, trailPath, options);
}

const isMain = process.argv[1] && fileURLToPath(import.meta.url) === path.resolve(process.argv[1]);

if (isMain) {
  const args = process.argv.slice(2).filter((a) => a !== "--mock");
  const mock = process.argv.includes("--mock") || !process.env.GEMINI_API_KEY;
  const [blank, sources, out] = args;
  if (!blank || !sources || !out) {
    console.error(
      "Usage: npx tsx src/mainPipeline.ts <blank-form.docx> <sources-dir> <output-dir> [--mock]"
    );
    process.exit(2);
  }
  runAuditorPipeline(blank, sources, out, { mock })
    .then((trail) => {
      console.log(JSON.stringify({ status: trail.status, output: trail.outputFile }, null, 2));
    })
    .catch((err) => {
      console.error(err);
      process.exit(1);
    });
}
