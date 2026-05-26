"""Cognitive Adaptive Self-Critique — contextual DOCX re-reading.

The LLM re-reads filled cells and asks intelligent questions about whether
the written values make contextual sense. This catches errors that pure
validators miss: misplaced values, wrong date formats, revision numbers in
date fields, single-character fills where dates belong, etc.

Called AFTER the deterministic visible-text check passes.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

from .adapter import get_adapter
from .config import get_cognitive_config
from .models import CritiqueFinding
from .prompts import SELF_CRITIQUE_SYSTEM, SELF_CRITIQUE_USER

if TYPE_CHECKING:
    from ..core.models import FieldDecision, FieldNode


class _CritiqueResponse(BaseModel):
    """Schema the LLM returns for self-critique."""

    findings: list[CritiqueFinding] = Field(default_factory=list)


class _SingleCritiqueResponse(BaseModel):
    """Single finding for per-field critique."""

    issue: str = ""
    severity: str = "note"
    recommendation: str = ""
    confidence: float = 0.0


def critique_field(
    node: "FieldNode",
    decision: "FieldDecision",
    *,
    cell_value: str,
    row_context: str = "",
    neighbor_context: str = "",
    form_id: str,
) -> list[CritiqueFinding]:
    """Run cognitive self-critique on a single filled cell.

    Returns empty list when cognitive layer is disabled.
    Returns findings with severity levels when issues detected.
    """
    config = get_cognitive_config()
    if not config.is_component_enabled("self_critique"):
        return []

    if not cell_value or not cell_value.strip():
        return []

    source_summary = ""
    if decision.evidence_ref:
        source_summary = (
            f"Source: {decision.evidence_ref.source_file or 'unknown'}, "
            f"confidence: {decision.evidence_ref.confidence}"
        )

    user_prompt = SELF_CRITIQUE_USER.format(
        form_id=form_id,
        field_id=node.field_id,
        field_label=node.label,
        row_context=row_context or f"Table {node.table_index}, Row {node.row}",
        cell_value=cell_value,
        decision_state=decision.state.value,
        source_summary=source_summary or "No source reference",
        neighbor_context=neighbor_context or "Not available",
        schema_name=_SingleCritiqueResponse.__name__,
    )

    adapter = get_adapter()
    response = adapter.reason(SELF_CRITIQUE_SYSTEM, user_prompt, _SingleCritiqueResponse)

    if not response.issue:
        return []

    severity = response.severity if response.severity in ("error", "warning", "note") else "note"

    return [CritiqueFinding(
        field_id=node.field_id,
        issue=response.issue,
        severity=severity,
        recommendation=response.recommendation,
        confidence=response.confidence,
        cell_value=cell_value,
    )]


def critique_form(
    fields_and_decisions: list[tuple["FieldNode", "FieldDecision", str]],
    *,
    form_id: str,
) -> list[CritiqueFinding]:
    """Run cognitive self-critique on all filled cells for a form.

    Each tuple is (node, decision, visible_cell_value).
    Returns aggregated findings across all fields.
    """
    config = get_cognitive_config()
    if not config.is_component_enabled("self_critique"):
        return []

    all_findings: list[CritiqueFinding] = []
    for node, decision, cell_value in fields_and_decisions:
        findings = critique_field(
            node,
            decision,
            cell_value=cell_value,
            form_id=form_id,
        )
        all_findings.extend(findings)
    return all_findings
