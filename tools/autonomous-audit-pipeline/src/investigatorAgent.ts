import { LlmClient } from "./llmClient.js";
import { AuditRequirement, EvidenceBundle } from "./schemas.js";

export async function gatherEvidence(
  requirement: AuditRequirement,
  sourceDocumentsContext: string,
  client: LlmClient
): Promise<EvidenceBundle> {
  const prompt = `
Requirement Target Label: ${requirement.fieldLabel}
Target Intent Context: ${requirement.contextualIntent}
Search Execution Directive: ${requirement.searchDirective}
Mapped Schema Path: ${requirement.mappedSchemaPath ?? "none"}
=== SOURCE EVIDENCE BASE ===
${sourceDocumentsContext}
=== END SOURCE BASE ===
Isolate matching facts, numbers, dates, or table metrics. Surface gaps and contradictions. Always return items array (may be empty).
`;

  const jsonSchema = {
    type: "OBJECT",
    properties: {
      items: {
        type: "ARRAY",
        items: {
          type: "OBJECT",
          properties: {
            sourceFile: { type: "STRING" },
            pageNumber: { type: "INTEGER", nullable: true },
            sectionLabel: { type: "STRING" },
            evidenceType: { type: "STRING", enum: ["text", "table", "number", "calculation"] },
            extractedContent: { type: "STRING" },
            relevanceReason: { type: "STRING" },
            confidence: { type: "NUMBER" },
            sourceAuthorityScore: { type: "NUMBER" },
            sourceDate: { type: "STRING" },
          },
          required: [
            "sourceFile",
            "evidenceType",
            "extractedContent",
            "relevanceReason",
            "confidence",
            "sourceAuthorityScore",
          ],
        },
      },
      gaps: { type: "ARRAY", items: { type: "STRING" } },
      contradictions: { type: "ARRAY", items: { type: "STRING" } },
    },
    required: ["items", "gaps", "contradictions"],
  };

  const result = await client.generateStructuredJson<Omit<EvidenceBundle, "requirementId">>(
    prompt,
    jsonSchema
  );
  return { requirementId: requirement.id, ...result };
}
