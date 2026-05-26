"""SPEC-1 autonomous pipeline data contracts."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

FieldType = Literal["narrative", "number", "date", "boolean", "table", "unknown"]
EvidenceType = Literal["text", "number", "table", "calculation", "policy", "unknown"]
DocumentType = Literal["docx", "pdf", "image"]
FallbackBehavior = Literal["fill_not_verified", "leave_blank", "use_default", "use_best_effort"]
AutomationStatus = Literal[
    "completed",
    "completed_with_low_confidence",
    "completed_with_missing_evidence",
    "completed_with_conflict_resolution",
    "failed_with_fallback",
]

NOT_VERIFIED_TEXT = "Not verified in provided source documents."
NUMERIC_NOT_VERIFIED = "N/A - not verified in provided source documents"

HIGH_CONFIDENCE = 0.80
MEDIUM_CONFIDENCE = 0.55
MAPPING_CONFIDENCE_MIN = 0.50


@dataclass
class FormLocation:
    document_type: DocumentType
    page: int | None = None
    table_index: int | None = None
    row_index: int | None = None
    column_index: int | None = None
    paragraph_index: int | None = None
    nearby_header: str | None = None
    cell_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"documentType": self.document_type}
        if self.page is not None:
            d["page"] = self.page
        if self.table_index is not None:
            d["tableIndex"] = self.table_index
        if self.row_index is not None:
            d["rowIndex"] = self.row_index
        if self.column_index is not None:
            d["columnIndex"] = self.column_index
        if self.paragraph_index is not None:
            d["paragraphIndex"] = self.paragraph_index
        if self.nearby_header:
            d["nearbyHeader"] = self.nearby_header
        if self.cell_path:
            d["cellPath"] = self.cell_path
        return d

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> FormLocation:
        return cls(
            document_type=raw.get("documentType", "docx"),  # type: ignore[arg-type]
            page=raw.get("page"),
            table_index=raw.get("tableIndex"),
            row_index=raw.get("rowIndex"),
            column_index=raw.get("columnIndex"),
            paragraph_index=raw.get("paragraphIndex"),
            nearby_header=raw.get("nearbyHeader"),
            cell_path=raw.get("cellPath"),
        )


@dataclass
class AuditRequirement:
    id: str
    field_label: str
    field_type: FieldType
    form_location: FormLocation
    contextual_intent: str
    search_directive: str
    required_evidence_type: EvidenceType
    required: bool
    mapping_confidence: float
    can_auto_fill: bool
    fallback_behavior: FallbackBehavior
    expected_unit: str | None = None
    docupipe_schema_id: str | None = None
    mapped_schema_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d = {
            "id": self.id,
            "fieldLabel": self.field_label,
            "fieldType": self.field_type,
            "formLocation": self.form_location.to_dict(),
            "contextualIntent": self.contextual_intent,
            "searchDirective": self.search_directive,
            "requiredEvidenceType": self.required_evidence_type,
            "required": self.required,
            "mappingConfidence": self.mapping_confidence,
            "canAutoFill": self.can_auto_fill,
            "fallbackBehavior": self.fallback_behavior,
        }
        if self.expected_unit:
            d["expectedUnit"] = self.expected_unit
        if self.docupipe_schema_id:
            d["docupipeSchemaId"] = self.docupipe_schema_id
        if self.mapped_schema_path:
            d["mappedSchemaPath"] = self.mapped_schema_path
        return d

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> AuditRequirement:
        return cls(
            id=str(raw["id"]),
            field_label=str(raw.get("fieldLabel") or ""),
            field_type=raw.get("fieldType", "unknown"),  # type: ignore[arg-type]
            expected_unit=raw.get("expectedUnit"),
            form_location=FormLocation.from_dict(raw.get("formLocation") or {}),
            contextual_intent=str(raw.get("contextualIntent") or ""),
            search_directive=str(raw.get("searchDirective") or ""),
            required_evidence_type=raw.get("requiredEvidenceType", "unknown"),  # type: ignore[arg-type]
            required=bool(raw.get("required")),
            docupipe_schema_id=raw.get("docupipeSchemaId"),
            mapped_schema_path=raw.get("mappedSchemaPath"),
            mapping_confidence=float(raw.get("mappingConfidence") or 0.0),
            can_auto_fill=bool(raw.get("canAutoFill")),
            fallback_behavior=raw.get("fallbackBehavior", "fill_not_verified"),  # type: ignore[arg-type]
        )


@dataclass
class MachineFieldMapSummary:
    detected_field_count: int
    auto_fillable_field_count: int
    low_confidence_field_count: int
    fallback_field_count: int

    def to_dict(self) -> dict[str, int]:
        return {
            "detectedFieldCount": self.detected_field_count,
            "autoFillableFieldCount": self.auto_fillable_field_count,
            "lowConfidenceFieldCount": self.low_confidence_field_count,
            "fallbackFieldCount": self.fallback_field_count,
        }


@dataclass
class MachineFieldMapV1:
    template_file: str
    generated_at: str
    fields: list[AuditRequirement]
    summary: MachineFieldMapSummary
    version: str = "machine_field_map.v1"
    activity_code: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "templateFile": self.template_file,
            "generatedAt": self.generated_at,
            "activityCode": self.activity_code,
            "fields": [f.to_dict() for f in self.fields],
            "summary": self.summary.to_dict(),
        }

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> MachineFieldMapV1:
        fields = [AuditRequirement.from_dict(item) for item in raw.get("fields") or []]
        summary_raw = raw.get("summary") or {}
        summary = MachineFieldMapSummary(
            detected_field_count=int(summary_raw.get("detectedFieldCount") or len(fields)),
            auto_fillable_field_count=int(summary_raw.get("autoFillableFieldCount") or 0),
            low_confidence_field_count=int(summary_raw.get("lowConfidenceFieldCount") or 0),
            fallback_field_count=int(summary_raw.get("fallbackFieldCount") or 0),
        )
        return cls(
            template_file=str(raw.get("templateFile") or ""),
            generated_at=str(raw.get("generatedAt") or ""),
            fields=fields,
            summary=summary,
            activity_code=raw.get("activityCode"),
        )


@dataclass
class EvidenceItem:
    source_file: str
    evidence_type: EvidenceType
    extracted_content: str
    relevance_reason: str
    confidence: float
    source_authority_score: float
    page_number: int | None = None
    section_label: str | None = None
    source_date: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["evidenceType"] = self.evidence_type
        d["sourceFile"] = self.source_file
        d["extractedContent"] = self.extracted_content
        d["relevanceReason"] = self.relevance_reason
        d["sourceAuthorityScore"] = self.source_authority_score
        if self.page_number is not None:
            d["pageNumber"] = self.page_number
        if self.section_label:
            d["sectionLabel"] = self.section_label
        if self.source_date:
            d["sourceDate"] = self.source_date
        for k in list(d.keys()):
            if k in d and k[0].islower() and "_" in k:
                pass
        return {
            "sourceFile": self.source_file,
            "pageNumber": self.page_number,
            "sectionLabel": self.section_label,
            "evidenceType": self.evidence_type,
            "extractedContent": self.extracted_content,
            "relevanceReason": self.relevance_reason,
            "confidence": self.confidence,
            "sourceAuthorityScore": self.source_authority_score,
            "sourceDate": self.source_date,
        }


@dataclass
class EvidenceBundle:
    requirement_id: str
    items: list[EvidenceItem] = field(default_factory=list)
    gaps: list[str] = field(default_factory=list)
    contradictions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "requirementId": self.requirement_id,
            "items": [i.to_dict() for i in self.items],
            "gaps": list(self.gaps),
            "contradictions": list(self.contradictions),
        }


@dataclass
class Citation:
    source_file: str
    page_number: int | None = None
    section_label: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"sourceFile": self.source_file}
        if self.page_number is not None:
            d["pageNumber"] = self.page_number
        if self.section_label:
            d["sectionLabel"] = self.section_label
        return d


@dataclass
class SynthesizedAnswer:
    requirement_id: str
    text: str
    confidence: float
    justification: str
    automation_status: AutomationStatus
    fallback_applied: bool
    normalized_value: str | float | bool | None = None
    citations: list[Citation] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "requirementId": self.requirement_id,
            "text": self.text,
            "normalizedValue": self.normalized_value,
            "confidence": self.confidence,
            "justification": self.justification,
            "citations": [c.to_dict() for c in self.citations],
            "automationStatus": self.automation_status,
            "fallbackApplied": self.fallback_applied,
        }


@dataclass
class FieldPipelineResult:
    requirement: AuditRequirement
    evidence: EvidenceBundle
    answer: SynthesizedAnswer
    status: AutomationStatus

    def to_dict(self) -> dict[str, Any]:
        return {
            "fieldId": self.requirement.id,
            "label": self.requirement.field_label,
            "requirement": self.requirement.to_dict(),
            "evidence": self.evidence.to_dict(),
            "answer": self.answer.to_dict(),
            "status": self.status,
        }


@dataclass
class AutonomousRunResult:
    started_at: str
    completed_at: str
    blank_form_path: str
    source_folder: str
    output_dir: str
    status: str
    field_count: int
    completed_forms: list[str]
    field_results: list[FieldPipelineResult]
    manifest_path: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "startedAt": self.started_at,
            "completedAt": self.completed_at,
            "blankFormPath": self.blank_form_path,
            "sourceFolder": self.source_folder,
            "outputDir": self.output_dir,
            "status": self.status,
            "fieldCount": self.field_count,
            "completedForms": self.completed_forms,
            "results": [r.to_dict() for r in self.field_results],
            "manifestPath": self.manifest_path,
        }
