"""Validation Gate — deterministic validateAnswer."""

from __future__ import annotations

import re
from datetime import datetime

from b2_automation.autonomous_contracts import (
    HIGH_CONFIDENCE,
    MEDIUM_CONFIDENCE,
    NOT_VERIFIED_TEXT,
    NUMERIC_NOT_VERIFIED,
    AuditRequirement,
    AutomationStatus,
    EvidenceBundle,
    SynthesizedAnswer,
)
from b2_automation.docx_structure import extract_docx_structure


def _valid_date(text: str) -> bool:
    return bool(
        re.match(r"^\d{4}-\d{2}-\d{2}$", text.strip())
        or re.match(r"^\d{1,2}[/-]\d{1,2}[/-]\d{2,4}$", text.strip())
    )


def _valid_number(text: str) -> bool:
    return bool(re.match(r"^[-+]?\d*\.?\d+", text.strip().replace(",", "")))


def validate_answer(
    requirement: AuditRequirement,
    evidence: EvidenceBundle,
    drafted: SynthesizedAnswer,
    *,
    template_path: str | None = None,
) -> SynthesizedAnswer:
    """Always returns a final answer — never blocks for human review."""
    text = (drafted.text or "").strip()
    confidence = drafted.confidence
    fallback_applied = drafted.fallback_applied
    status: AutomationStatus = drafted.automation_status
    justification = drafted.justification

    if template_path and requirement.form_location.table_index is not None:
        try:
            structure = extract_docx_structure(template_path)
            ti = requirement.form_location.table_index
            if ti >= structure.table_count:
                text = NOT_VERIFIED_TEXT
                fallback_applied = True
                status = "failed_with_fallback"
                justification += "; invalid write coordinate"
        except OSError:
            pass

    if not requirement.can_auto_fill:
        if requirement.fallback_behavior == "leave_blank":
            text = ""
        else:
            text = NOT_VERIFIED_TEXT if requirement.field_type != "number" else NUMERIC_NOT_VERIFIED
        fallback_applied = True
        status = "failed_with_fallback"
        confidence = 0.0

    if evidence.gaps and not evidence.items:
        text = NOT_VERIFIED_TEXT if requirement.field_type != "number" else NUMERIC_NOT_VERIFIED
        fallback_applied = True
        status = "completed_with_missing_evidence"
        confidence = 0.0
        justification = f"Missing evidence: {'; '.join(evidence.gaps)}"

    elif evidence.contradictions and drafted.citations:
        status = "completed_with_conflict_resolution"
        justification += f"; resolved conflict: {evidence.contradictions[0]}"

    if requirement.field_type == "number" and text and not fallback_applied:
        if not _valid_number(text):
            text = NUMERIC_NOT_VERIFIED
            fallback_applied = True
            status = "completed_with_missing_evidence"

    if requirement.field_type == "date" and text and not fallback_applied:
        if not _valid_date(text):
            for fmt in ("%m/%d/%Y", "%d/%m/%Y"):
                try:
                    datetime.strptime(text[:10], fmt)
                    break
                except ValueError:
                    continue
            else:
                if not _valid_date(text):
                    text = NOT_VERIFIED_TEXT
                    fallback_applied = True

    if requirement.required and not text and requirement.fallback_behavior != "leave_blank":
        text = NOT_VERIFIED_TEXT if requirement.field_type != "number" else NUMERIC_NOT_VERIFIED
        fallback_applied = True
        status = "completed_with_missing_evidence"

    if drafted.citations and confidence >= HIGH_CONFIDENCE and not fallback_applied:
        status = "completed"
    elif confidence >= MEDIUM_CONFIDENCE and not fallback_applied:
        status = "completed_with_low_confidence"

    if "REVIEW_REQUIRED" in text.upper():
        text = NOT_VERIFIED_TEXT
        fallback_applied = True
        status = "failed_with_fallback"

    max_len = 2000
    if len(text) > max_len:
        text = text[: max_len - 3] + "..."

    return SynthesizedAnswer(
        requirement_id=requirement.id,
        text=text,
        normalized_value=drafted.normalized_value,
        confidence=confidence,
        justification=justification,
        citations=drafted.citations,
        automation_status=status,
        fallback_applied=fallback_applied,
    )
