import { LlmClient } from "./llmClient.js";
import { AuditRequirement, EvidenceBundle, SynthesizedAnswer } from "./schemas.js";

export async function synthesizeAnswer(
  requirement: AuditRequirement,
  bundle: EvidenceBundle,
  client: LlmClient
): Promise<SynthesizedAnswer> {
  const prompt = `
Formulate target value entry for: "${requirement.fieldLabel}"
Required Value Format Type: ${requirement.fieldType} (Unit: ${requirement.expectedUnit || "None"})
=== HARVESTED EVIDENCE ===
${JSON.stringify(bundle, null, 2)}
===
Use only supplied evidence. Do not invent facts. Never request human review.
`;

  const jsonSchema = {
    type: "OBJECT",
    properties: {
      rawAnswer: { type: "STRING" },
      formattedAnswer: { type: "STRING" },
      citations: { type: "ARRAY", items: { type: "STRING" } },
      synthesisConfidence: { type: "NUMBER" },
      reasoningTrail: { type: "STRING" },
    },
    required: ["rawAnswer", "formattedAnswer", "citations", "synthesisConfidence", "reasoningTrail"],
  };

  const result = await client.generateStructuredJson<Omit<SynthesizedAnswer, "requirementId">>(
    prompt,
    jsonSchema
  );
  return { requirementId: requirement.id, ...result };
}

/** Alias for SPEC controller skeleton */
export const synthesizeHumanResponse = synthesizeAnswer;
