"""Writer Agent — synthesizeAnswer from evidence."""

from __future__ import annotations

import re
from typing import Any

from b2_automation.autonomous_contracts import (
    NOT_VERIFIED_TEXT,
    NUMERIC_NOT_VERIFIED,
    AuditRequirement,
    AutomationStatus,
    Citation,
    EvidenceBundle,
    EvidenceItem,
    FallbackBehavior,
    SynthesizedAnswer,
)
from b2_automation.llm_client import LlmError, generate_json

_FALLBACK_TEXT = {
    "fill_not_verified": NOT_VERIFIED_TEXT,
    "leave_blank": "",
    "use_default": "",
    "use_best_effort": NOT_VERIFIED_TEXT,
}


def _pick_best_item(items: list[EvidenceItem]) -> EvidenceItem | None:
    if not items:
        return None
    return max(items, key=lambda i: (i.confidence * i.source_authority_score, len(i.extracted_content)))


def _extract_value_snippet(item: EvidenceItem, field_type: str) -> str:
    text = item.extracted_content.strip()
    if field_type == "number":
        m = re.search(r"[-+]?\d*\.?\d+(?:\s*%)?", text)
        return m.group(0) if m else text.split(".")[0][:80]
    if field_type == "date":
        m = re.search(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b|\b\d{4}-\d{2}-\d{2}\b", text)
        return m.group(0) if m else text[:80]
    sentences = re.split(r"(?<=[.!?])\s+", text)
    return sentences[0][:500] if sentences else text[:500]


def _narrative_from_evidence(req: AuditRequirement, item: EvidenceItem) -> str:
    snippet = _extract_value_snippet(item, req.field_type)
    return f"Based on source documentation ({item.source_file}), {req.field_label}: {snippet}"


def _fallback_answer(req: AuditRequirement, reason: str) -> SynthesizedAnswer:
    behavior: FallbackBehavior = req.fallback_behavior
    if req.field_type == "number" and req.required:
        text = NUMERIC_NOT_VERIFIED
    else:
        text = _FALLBACK_TEXT.get(behavior, NOT_VERIFIED_TEXT)
    status: AutomationStatus = "completed_with_missing_evidence"
    if "conflict" in reason.lower():
        status = "completed_with_conflict_resolution"
    elif "failure" in reason.lower():
        status = "failed_with_fallback"
    return SynthesizedAnswer(
        requirement_id=req.id,
        text=text,
        confidence=0.0,
        justification=reason,
        automation_status=status,
        fallback_applied=True,
        citations=[],
    )


def synthesize_human_response(
    requirement: AuditRequirement,
    evidence: EvidenceBundle,
) -> SynthesizedAnswer:
    """synthesizeAnswer — Writer Agent."""
    if evidence.gaps and not evidence.items:
        return _fallback_answer(requirement, f"Missing evidence: {'; '.join(evidence.gaps)}")

    if not requirement.can_auto_fill:
        return _fallback_answer(
            requirement,
            f"Low mapping confidence ({requirement.mapping_confidence:.2f}); fallbackBehavior={requirement.fallback_behavior}",
        )

    best = _pick_best_item(evidence.items)
    if not best:
        return _fallback_answer(requirement, "No ranked evidence items")

    if evidence.contradictions:
        best = max(evidence.items, key=lambda i: i.source_authority_score)

    if requirement.field_type == "narrative":
        text = _narrative_from_evidence(requirement, best)
    else:
        text = _extract_value_snippet(best, requirement.field_type)

    confidence = min(0.99, best.confidence * best.source_authority_score)
    status: AutomationStatus = "completed"
    if confidence < 0.55:
        status = "completed_with_low_confidence"
    if evidence.gaps:
        status = "completed_with_missing_evidence"
    if evidence.contradictions:
        status = "completed_with_conflict_resolution"

    return SynthesizedAnswer(
        requirement_id=requirement.id,
        text=text,
        normalized_value=text if requirement.field_type != "narrative" else None,
        confidence=confidence,
        justification=f"Synthesized from {len(evidence.items)} evidence item(s). {best.relevance_reason}",
        citations=[
            Citation(
                source_file=best.source_file,
                page_number=best.page_number,
                section_label=best.section_label,
            )
        ],
        automation_status=status,
        fallback_applied=False,
    )


def synthesize_with_llm_optional(
    requirement: AuditRequirement,
    evidence: EvidenceBundle,
) -> SynthesizedAnswer:
    """Optional LLM polish when API keys are set."""
    base = synthesize_human_response(requirement, evidence)
    if base.fallback_applied or not evidence.items:
        return base
    prompt = f"""Synthesize a professional audit form answer.

Field: {requirement.field_label}
Intent: {requirement.contextual_intent}
Type: {requirement.field_type}
Evidence: {evidence.to_dict()}

Rules: use only supplied evidence; no invented facts; include citations; never ask for human review.
Return JSON matching SynthesizedAnswer schema keys: requirementId, text, confidence, justification, citations, automationStatus, fallbackApplied.
"""
    try:
        raw = generate_json(prompt)
        if isinstance(raw, dict) and raw.get("text"):
            return SynthesizedAnswer(
                requirement_id=requirement.id,
                text=str(raw["text"]),
                normalized_value=raw.get("normalizedValue"),
                confidence=float(raw.get("confidence") or base.confidence),
                justification=str(raw.get("justification") or base.justification),
                citations=base.citations,
                automation_status=raw.get("automationStatus", base.automation_status),  # type: ignore[arg-type]
                fallback_applied=bool(raw.get("fallbackApplied")),
            )
    except LlmError:
        pass
    return base
