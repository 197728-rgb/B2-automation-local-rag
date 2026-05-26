export interface AuditRequirement {
  id: string;
  fieldLabel: string;
  fieldType: "narrative" | "number" | "date" | "boolean" | "table" | "unknown";
  expectedUnit?: string;
  formLocation: {
    documentType: "docx" | "pdf" | "image";
    page?: number;
    tableIndex?: number;
    rowIndex?: number;
    columnIndex?: number;
    paragraphIndex?: number;
    nearbyHeader?: string;
    cellPath?: string;
  };
  contextualIntent: string;
  searchDirective: string;
  requiredEvidenceType: "text" | "number" | "table" | "calculation" | "policy" | "unknown";
  required: boolean;
  docupipeSchemaId?: string;
  mappedSchemaPath?: string;
  mappingConfidence: number;
  canAutoFill: boolean;
  fallbackBehavior: "fill_not_verified" | "leave_blank" | "use_default" | "use_best_effort";
}

export interface MachineFieldMapV1 {
  version: "machine_field_map.v1";
  templateFile: string;
  generatedAt: string;
  activityCode?: string;
  fields: AuditRequirement[];
  summary: {
    detectedFieldCount: number;
    autoFillableFieldCount: number;
    lowConfidenceFieldCount: number;
    fallbackFieldCount: number;
  };
}

export interface EvidenceItem {
  sourceFile: string;
  pageNumber?: number;
  sectionLabel?: string;
  evidenceType: "text" | "table" | "number" | "calculation";
  extractedContent: string;
  relevanceReason: string;
  confidence: number;
  sourceAuthorityScore: number;
  sourceDate?: string;
}

export interface EvidenceBundle {
  requirementId: string;
  items: EvidenceItem[];
  gaps: string[];
  contradictions: string[];
}

export interface SynthesizedAnswer {
  requirementId: string;
  rawAnswer: string;
  formattedAnswer: string;
  citations: string[];
  synthesisConfidence: number;
  reasoningTrail: string;
}

export interface ValidationRecord {
  requirementId: string;
  isValid: boolean;
  appliedFallback: boolean;
  actionTaken: "accepted" | "modified_by_fallback" | "blanked";
  resolvedAnswer: string;
  validationErrors: string[];
}

export interface FormWriterTrail {
  requirementId: string;
  writeCoordinates: string;
  writeStatus: "success" | "failed" | "skipped";
  errorMessage?: string;
}

export interface PipelineAuditTrail {
  pipelineVersion: string;
  executionTimestamp: string;
  status: "completed" | "completed_with_low_confidence" | "failed";
  templateFile: string;
  outputFile: string;
  summaryMetrics: {
    totalFieldsProcessed: number;
    successfullyFilled: number;
    fallbackAppliedCount: number;
    failedWritesCount: number;
  };
  records: Array<{
    requirement: AuditRequirement;
    evidence: EvidenceBundle;
    synthesis: SynthesizedAnswer;
    validation: ValidationRecord;
    writeResult: FormWriterTrail;
  }>;
}

export const NOT_VERIFIED_TEXT = "Not verified in provided source documents.";
