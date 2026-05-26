import mammoth from "mammoth";
import fs from "node:fs";
import path from "node:path";
import {
  AuditRequirement,
  EvidenceBundle,
  MachineFieldMapV1,
  SynthesizedAnswer,
} from "./schemas.js";
import { loadSourceDocumentsContext } from "./sourceLoader.js";

const MOCK_FIELDS = [
  "Facility Name",
  "Activity Code",
  "NDT Personnel",
  "Procedure Reference",
  "Quality Records",
];

function slugId(label: string): string {
  return label.toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_|_$/g, "");
}

function extractSnippet(context: string, label: string): string {
  const lower = context.toLowerCase();
  const key = label.toLowerCase();
  const idx = lower.indexOf(key);
  if (idx < 0) return "";
  const slice = context.slice(idx, idx + 400);
  const line = slice.split("\n").find((l) => l.trim().length > 10) ?? slice;
  return line.replace(/\*\*/g, "").trim().slice(0, 280);
}

export async function mockAnalyzeDocxForm(docxPath: string): Promise<MachineFieldMapV1> {
  const buf = fs.readFileSync(docxPath);
  await mammoth.extractRawText({ buffer: buf });

  const fields: AuditRequirement[] = MOCK_FIELDS.map((label, i) => ({
    id: slugId(label),
    fieldLabel: label,
    fieldType: "narrative" as const,
    formLocation: {
      documentType: "docx" as const,
      tableIndex: 0,
      rowIndex: i,
      columnIndex: 1,
      nearbyHeader: label,
    },
    contextualIntent: `Capture ${label} from facility evidence.`,
    searchDirective: `Find ${label} in company profile, personnel, or procedures sources.`,
    requiredEvidenceType: "text" as const,
    required: true,
    mappingConfidence: 0.92,
    canAutoFill: true,
    fallbackBehavior: "use_best_effort" as const,
    mappedSchemaPath:
      label === "Activity Code" ? "demonstration.station" : undefined,
    docupipeSchemaId: label === "Activity Code" ? "B24_RL2_2026" : undefined,
  }));

  return {
    version: "machine_field_map.v1",
    templateFile: docxPath,
    generatedAt: new Date().toISOString(),
    activityCode: "B24-RL2",
    fields,
    summary: {
      detectedFieldCount: fields.length,
      autoFillableFieldCount: fields.length,
      lowConfidenceFieldCount: 0,
      fallbackFieldCount: 0,
    },
  };
}

export function mockGatherEvidence(
  requirement: AuditRequirement,
  sourceDocumentsContext: string
): EvidenceBundle {
  const snippet = extractSnippet(sourceDocumentsContext, requirement.fieldLabel);
  const items =
    snippet.length > 0
      ? [
          {
            sourceFile: "mock-sources",
            evidenceType: "text" as const,
            extractedContent: snippet,
            relevanceReason: `Matched label "${requirement.fieldLabel}" in source bundle.`,
            confidence: 0.85,
            sourceAuthorityScore: 0.8,
          },
        ]
      : [];

  return {
    requirementId: requirement.id,
    items,
    gaps: items.length ? [] : [`No explicit mention of ${requirement.fieldLabel} in sources.`],
    contradictions: [],
  };
}

export function mockSynthesizeAnswer(
  requirement: AuditRequirement,
  bundle: EvidenceBundle
): SynthesizedAnswer {
  const top = bundle.items[0]?.extractedContent ?? "";
  const formatted = top || "DATA_UNRESOLVED";
  return {
    requirementId: requirement.id,
    rawAnswer: formatted,
    formattedAnswer: formatted,
    citations: bundle.items.map((i) => i.sourceFile),
    synthesisConfidence: top ? 0.88 : 0.4,
    reasoningTrail: top
      ? `Mock synthesis: used first source snippet for ${requirement.fieldLabel}.`
      : `Mock synthesis: no snippet found for ${requirement.fieldLabel}.`,
  };
}

export function loadMockContext(sourceFolder: string): string {
  return loadSourceDocumentsContext(path.resolve(sourceFolder));
}
