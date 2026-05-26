import { LlmClient } from "./llmClient.js";
import { extractDocxSemanticHtml } from "./docxFormExtractor.js";
import { AuditRequirement, MachineFieldMapV1 } from "./schemas.js";

export async function analyzeDocxForm(
  docxPath: string,
  availableSchemas: unknown[],
  client: LlmClient,
  confidenceThreshold = 0.75
): Promise<MachineFieldMapV1> {
  const htmlContent = await extractDocxSemanticHtml(docxPath);
  const prompt = `
Analyze this blank audit form and output machine_field_map.v1 JSON.
FORM HTML:
${htmlContent}
AVAILABLE SCHEMAS:
${JSON.stringify(availableSchemas, null, 2)}
Detect fillable fields, infer intent, search directives, schema paths, and DOCX write locations (tableIndex, rowIndex, columnIndex).
Do not ask for human review.
`;

  const jsonSchema = {
    type: "OBJECT",
    properties: {
      activityCode: { type: "STRING" },
      fields: {
        type: "ARRAY",
        items: {
          type: "OBJECT",
          properties: {
            id: { type: "STRING" },
            fieldLabel: { type: "STRING" },
            fieldType: {
              type: "STRING",
              enum: ["narrative", "number", "date", "boolean", "table", "unknown"],
            },
            expectedUnit: { type: "STRING", nullable: true },
            formLocation: {
              type: "OBJECT",
              properties: {
                documentType: { type: "STRING" },
                tableIndex: { type: "INTEGER", nullable: true },
                rowIndex: { type: "INTEGER", nullable: true },
                columnIndex: { type: "INTEGER", nullable: true },
                paragraphIndex: { type: "INTEGER", nullable: true },
                nearbyHeader: { type: "STRING" },
                cellPath: { type: "STRING" },
              },
              required: ["documentType"],
            },
            contextualIntent: { type: "STRING" },
            searchDirective: { type: "STRING" },
            requiredEvidenceType: {
              type: "STRING",
              enum: ["text", "number", "table", "calculation", "policy", "unknown"],
            },
            required: { type: "BOOLEAN" },
            docupipeSchemaId: { type: "STRING", nullable: true },
            mappedSchemaPath: { type: "STRING", nullable: true },
            mappingConfidence: { type: "NUMBER" },
            canAutoFill: { type: "BOOLEAN" },
            fallbackBehavior: {
              type: "STRING",
              enum: ["fill_not_verified", "leave_blank", "use_default", "use_best_effort"],
            },
          },
          required: [
            "id",
            "fieldLabel",
            "fieldType",
            "formLocation",
            "contextualIntent",
            "searchDirective",
            "requiredEvidenceType",
            "required",
            "mappingConfidence",
            "canAutoFill",
            "fallbackBehavior",
          ],
        },
      },
    },
    required: ["fields"],
  };

  const rawMap = await client.generateStructuredJson<{
    activityCode?: string;
    fields: AuditRequirement[];
  }>(prompt, jsonSchema);

  let lowConfidenceFieldCount = 0;
  let fallbackFieldCount = 0;
  let autoFillableFieldCount = 0;

  const fields = rawMap.fields.map((field) => {
    if (field.mappingConfidence < confidenceThreshold) {
      field.canAutoFill = false;
      lowConfidenceFieldCount++;
    }
    if (field.canAutoFill) autoFillableFieldCount++;
    else fallbackFieldCount++;
    return field;
  });

  return {
    version: "machine_field_map.v1",
    templateFile: docxPath,
    generatedAt: new Date().toISOString(),
    activityCode: rawMap.activityCode,
    fields,
    summary: {
      detectedFieldCount: fields.length,
      autoFillableFieldCount,
      lowConfidenceFieldCount,
      fallbackFieldCount,
    },
  };
}

export async function analyzeBlankForm(
  docxPath: string,
  availableSchemas: unknown[],
  client?: LlmClient
): Promise<MachineFieldMapV1> {
  return analyzeDocxForm(docxPath, availableSchemas, client ?? new LlmClient());
}
