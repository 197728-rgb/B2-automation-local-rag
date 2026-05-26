import { AuditRequirement, NOT_VERIFIED_TEXT, SynthesizedAnswer, ValidationRecord } from "./schemas.js";

export function validateAnswer(
  requirement: AuditRequirement,
  synthesis: SynthesizedAnswer,
  confidenceThreshold = 0.7
): ValidationRecord {
  const errors: string[] = [];
  let resolvedAnswer = synthesis.formattedAnswer;
  let appliedFallback = false;
  let actionTaken: "accepted" | "modified_by_fallback" | "blanked" = "accepted";

  if (!requirement.canAutoFill || synthesis.synthesisConfidence < confidenceThreshold) {
    errors.push(`Confidence below threshold: ${synthesis.synthesisConfidence}`);
    appliedFallback = true;
  }

  if (requirement.required && (!resolvedAnswer || resolvedAnswer.trim() === "")) {
    errors.push("Missing required value.");
    appliedFallback = true;
  }

  if (appliedFallback) {
    switch (requirement.fallbackBehavior) {
      case "leave_blank":
        resolvedAnswer = "";
        actionTaken = "blanked";
        break;
      case "use_default":
        resolvedAnswer = requirement.expectedUnit ? `0 ${requirement.expectedUnit}` : "N/A";
        actionTaken = "modified_by_fallback";
        break;
      case "fill_not_verified":
        resolvedAnswer = NOT_VERIFIED_TEXT;
        actionTaken = "modified_by_fallback";
        break;
      case "use_best_effort":
      default:
        resolvedAnswer = synthesis.formattedAnswer?.trim() || NOT_VERIFIED_TEXT;
        actionTaken = "modified_by_fallback";
        break;
    }
  }

  if (resolvedAnswer.includes("REVIEW_REQUIRED")) {
    resolvedAnswer = NOT_VERIFIED_TEXT;
    appliedFallback = true;
    actionTaken = "modified_by_fallback";
  }

  return {
    requirementId: requirement.id,
    isValid: !appliedFallback,
    appliedFallback,
    actionTaken,
    resolvedAnswer,
    validationErrors: errors,
  };
}
