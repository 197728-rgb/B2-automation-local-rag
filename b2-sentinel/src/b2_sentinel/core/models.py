"""SENTINEL Pydantic models.

Every artifact, ledger, decision, and report has a typed schema here. Models
are validation-first: bad data fails loud at the boundary, not silently downstream.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from .status import DecisionState, FinalStatus, RolloverDecision, WriteAuthority


class _Base(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class _BaseLoose(BaseModel):
    """For inputs we don't fully control (existing approval maps, etc.)."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)


# ---------------------------------------------------------------------------
# Layer 1 - Form Brain
# ---------------------------------------------------------------------------


class FieldNode(_Base):
    """A single field in the Form Obligation Graph."""

    field_id: str
    label: str
    table_index: int
    row: int
    col: int
    cell_role: Literal["target", "label", "notes", "header"] = "target"
    write_mode: Literal["replace", "append_after_label"] = "replace"

    required: bool = True
    optional: bool = False
    n_a_allowed: bool = False
    evidence_required: bool = True
    completion_blocker_if_missing: bool = True
    write_authority: WriteAuthority = WriteAuthority.EXACT_APPROVAL_MAP
    never_write: bool = False

    aliases: list[str] = Field(default_factory=list)
    preferred_evidence_keys: list[str] = Field(default_factory=list)
    expansion_search_terms: list[str] = Field(default_factory=list)


class ObligationGraph(_Base):
    """Layer 1 output - the form's complete obligation map."""

    form_id: str
    form_version: str
    template_path: str
    structure_fingerprint: str | None = None
    fields: dict[str, FieldNode]

    required_total: int = 0
    optional_total: int = 0
    never_write_total: int = 0

    def required_field_ids(self) -> list[str]:
        return sorted(fid for fid, f in self.fields.items() if f.required and not f.never_write)

    def n_a_eligible_field_ids(self) -> list[str]:
        return sorted(fid for fid, f in self.fields.items() if f.n_a_allowed)


# ---------------------------------------------------------------------------
# Layer 2 - Evidence Hunter
# ---------------------------------------------------------------------------


class SourceChunk(_Base):
    """One unit of extracted evidence."""

    chunk_id: str
    source_file: str
    source_type: Literal["pdf", "docx", "json", "csv", "txt", "md", "eml"]
    page: int | None = None
    text: str
    scope_hint: str | None = None  # which form this chunk likely belongs to


class EvidenceLedgerEntry(_Base):
    """The Field Evidence Ledger row from the spec."""

    field_id: str
    candidate_value: str | None = None
    source_file: str | None = None
    source_type: str | None = None
    page: int | None = None
    chunk_id: str | None = None
    source_text: str | None = None
    confidence: float = 0.0
    scope: str | None = None
    decision: Literal["usable", "weak", "conflict", "out_of_scope", "missing"] = "missing"
    alternates: list[dict[str, Any]] = Field(default_factory=list)
    alias_used: str | None = None
    wave_found_in: int | None = None


class EvidenceLedger(_Base):
    form_id: str
    entries: dict[str, EvidenceLedgerEntry]
    source_index: list[str]


# ---------------------------------------------------------------------------
# Layer 3 - Decision Engine
# ---------------------------------------------------------------------------


class ConfidenceBundle(_Base):
    """Five-axis confidence per the Innovation Layer."""

    retrieval: float = 0.0
    extraction: float = 0.0
    authorization: float = 0.0
    write: float = 0.0
    completion: float = 0.0


class FieldDecision(_Base):
    field_id: str
    state: DecisionState
    value: str | None = None
    reason: str
    confidence: ConfidenceBundle = Field(default_factory=ConfidenceBundle)
    evidence_ref: EvidenceLedgerEntry | None = None
    write_authority: WriteAuthority = WriteAuthority.UNAUTHORIZED
    explainability: str | None = None


# ---------------------------------------------------------------------------
# Layer 4 - Controlled Writer
# ---------------------------------------------------------------------------


class PatchInstruction(_Base):
    field_id: str
    table_index: int
    row: int
    col: int
    value: str
    write_mode: Literal["replace", "append_after_label"] = "replace"
    label_text: str | None = None
    authorized: bool = False
    write_authority: "WriteAuthority | None" = None


class PatchPlan(_Base):
    form_id: str
    writes: list[PatchInstruction]
    blocked: list[FieldDecision]
    n_a_inserts: list[PatchInstruction] = Field(default_factory=list)


class ManualCorrectionEntry(_Base):
    operation: Literal["manual_controlled_replacement"] = "manual_controlled_replacement"
    old: str
    new: str
    target_form: str
    occurrences_found: int
    occurrences_replaced: int
    risk: Literal["low", "medium", "high"] = "low"
    validated: bool = False


# ---------------------------------------------------------------------------
# Layer 5 - Structure Guard
# ---------------------------------------------------------------------------


class StructureFingerprint(_Base):
    table_count: int
    rows_per_table: list[int]
    cells_per_row: list[list[int]]
    paragraph_count: int
    content_control_count: int
    relationships_count: int
    xml_valid: bool


class StructureGuardReport(_Base):
    form_id: str
    blank_fingerprint: StructureFingerprint
    filled_fingerprint: StructureFingerprint
    tables_added: int
    tables_removed: int
    rows_added: int
    rows_removed: int
    cells_added: int
    cells_removed: int
    xml_valid: bool
    structure_guard_passed: bool
    notes: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Layer 6 - Completion Judge
# ---------------------------------------------------------------------------


class CompletionReport(_Base):
    form_id: str
    overall_passed_format: bool
    overall_passed_completion: bool
    overall_passed: bool
    final_status: FinalStatus
    required_total: int
    required_filled: int
    required_blocked: int
    review_required_count: int
    conflict_count: int
    low_confidence_count: int
    approved_na_count: int
    blocked_no_source_count: int
    blocked_unauthorized_count: int
    blockers: list[str]
    notes: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Layer 7 - Exception Engine
# ---------------------------------------------------------------------------


class NAExceptionEntry(_Base):
    field_id: str
    status: Literal["approved_na", "denied"] = "approved_na"
    reason: str
    authority: str = "approved_exception_policy"
    approved_by: str = "policy_reference"
    completion_effect: Literal["not_blocking", "blocking"] = "not_blocking"
    policy_id: str | None = None


# ---------------------------------------------------------------------------
# Layer 8 - Audit Packet
# ---------------------------------------------------------------------------


class FieldTraceability(_Base):
    field_id: str
    final_state: DecisionState
    value: str | None = None
    source_file: str | None = None
    page: int | None = None
    chunk_id: str | None = None
    confidence: ConfidenceBundle
    write_authority: WriteAuthority
    explainability: str


class RunManifest(_Base):
    run_id: str
    started_at: datetime
    finished_at: datetime | None = None
    forms: list[str]
    artifacts: dict[str, list[str]]
    final_statuses: dict[str, FinalStatus]
    overall_passed: bool
    errors: dict[str, str] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Innovations
# ---------------------------------------------------------------------------


class EvidenceDebtEntry(_Base):
    field_id: str
    debt_type: Literal["missing_source", "weak_source", "out_of_scope_source"]
    blocking: bool
    recommended_source: str
    search_terms: list[str]
    resolution_paths: list[str]


class RolloverEntry(_Base):
    field_id: str
    old_value: str | None = None
    new_candidate: str | None = None
    rollover_decision: RolloverDecision
    reason: str


class AliasRule(_Base):
    from_key: str = Field(alias="from")
    to_field: str = Field(alias="to")
    direction: Literal["write_bridge", "read_only"] = "write_bridge"
    forms: list[str] = Field(default_factory=list)
    risk: Literal["low", "medium", "high"] = "low"
    authority: str = "approved_alias_rule"


class RunDelta(_Base):
    previous_status: FinalStatus | None = None
    current_status: FinalStatus
    resolved_blockers: list[str] = Field(default_factory=list)
    remaining_blockers: list[str] = Field(default_factory=list)
    new_blockers: list[str] = Field(default_factory=list)
    net_progress: Literal["improved", "regressed", "unchanged"] = "unchanged"


# ---------------------------------------------------------------------------
# Existing approval-map shape (input) - loose to tolerate seed files
# ---------------------------------------------------------------------------


class ApprovalMapField(_BaseLoose):
    field_id: str
    table_index: int
    row: int
    col: int
    required: bool = True
    cell_role: str = "target"
    label: str
    write_mode: str = "replace"


class ApprovalMap(_BaseLoose):
    form_id: str
    form_version: str
    manifest_path: str | None = None
    template_path: str | None = None
    fields: dict[str, ApprovalMapField]
