"""Completion Judge.

Re-reads the filled DOCX from disk (independent of the Writer) and asks:
    - Are required cells visibly populated?
    - Are any REVIEW_REQUIRED markers still present?
    - Are any blocked_no_source / blocked_unauthorized still unresolved?
    - Are conflicts / low_confidence resolved?
    - Did structure guard pass?

Produces a CompletionReport with the spec's distinct format-pass and
completion-pass bits.
"""
from __future__ import annotations

from pathlib import Path

from ..core.models import (
    CompletionReport,
    FieldDecision,
    ObligationGraph,
    StructureGuardReport,
)
from ..core.status import (
    DecisionState,
    FinalStatus,
)
from .visible_text import cell_visible_text


def judge_completion(
    *,
    graph: ObligationGraph,
    decisions: dict[str, FieldDecision],
    filled_path: Path,
    structure_report: StructureGuardReport,
) -> CompletionReport:
    cells = cell_visible_text(filled_path)

    required_total = sum(1 for n in graph.fields.values() if n.required and not n.never_write)
    required_filled = 0
    required_blocked = 0

    review_required = []
    conflicts = []
    low_confidence = []
    approved_na = []
    blocked_no_source = []
    blocked_unauthorized = []
    blockers: list[str] = []

    for fid, decision in decisions.items():
        node = graph.fields[fid]
        coord = (node.table_index, node.row, node.col)
        visible = cells.get(coord, "")

        match decision.state:
            case DecisionState.FILL:
                if node.required:
                    if visible and "<<REVIEW_REQUIRED>>" not in visible:
                        required_filled += 1
                    else:
                        required_blocked += 1
                        blockers.append(
                            f"{fid}: writer claimed FILL but cell visible text is empty/marker"
                        )
            case DecisionState.APPROVED_NA:
                approved_na.append(fid)
                if node.required:
                    required_filled += 1  # NA counts as resolved
            case DecisionState.REVIEW_REQUIRED:
                review_required.append(fid)
                if node.required:
                    required_blocked += 1
                    blockers.append(f"{fid}: REVIEW_REQUIRED")
            case DecisionState.CONFLICT:
                conflicts.append(fid)
                if node.required:
                    required_blocked += 1
                    blockers.append(f"{fid}: CONFLICT")
            case DecisionState.LOW_CONFIDENCE:
                low_confidence.append(fid)
                if node.required:
                    required_blocked += 1
                    blockers.append(f"{fid}: LOW_CONFIDENCE")
            case DecisionState.BLOCKED_NO_SOURCE:
                blocked_no_source.append(fid)
                required_blocked += 1
                blockers.append(f"{fid}: BLOCKED_NO_SOURCE")
            case DecisionState.BLOCKED_UNAUTHORIZED:
                blocked_unauthorized.append(fid)
                required_blocked += 1
                blockers.append(f"{fid}: BLOCKED_UNAUTHORIZED")
            case DecisionState.OPTIONAL_BLANK:
                pass

    overall_passed_format = structure_report.structure_guard_passed
    overall_passed_completion = (
        required_total == required_filled
        and not blocked_no_source
        and not blocked_unauthorized
        and not review_required
        and not conflicts
        and not low_confidence
    )
    overall_passed = overall_passed_format and overall_passed_completion

    final_status = _final_status_from(
        overall_passed=overall_passed,
        format_passed=overall_passed_format,
        review_required=review_required,
        conflicts=conflicts,
        low_confidence=low_confidence,
        blocked_no_source=blocked_no_source,
        blocked_unauthorized=blocked_unauthorized,
    )

    return CompletionReport(
        form_id=graph.form_id,
        overall_passed_format=overall_passed_format,
        overall_passed_completion=overall_passed_completion,
        overall_passed=overall_passed,
        final_status=final_status,
        required_total=required_total,
        required_filled=required_filled,
        required_blocked=required_blocked,
        review_required_count=len(review_required),
        conflict_count=len(conflicts),
        low_confidence_count=len(low_confidence),
        approved_na_count=len(approved_na),
        blocked_no_source_count=len(blocked_no_source),
        blocked_unauthorized_count=len(blocked_unauthorized),
        blockers=blockers,
        notes=list(structure_report.notes),
    )


def _final_status_from(
    *,
    overall_passed: bool,
    format_passed: bool,
    review_required: list[str],
    conflicts: list[str],
    low_confidence: list[str],
    blocked_no_source: list[str],
    blocked_unauthorized: list[str],
) -> FinalStatus:
    if overall_passed:
        return FinalStatus.SUCCESS
    if not format_passed:
        return FinalStatus.FAILED_STRUCTURE_GUARD
    if blocked_unauthorized:
        return FinalStatus.FAILED_UNAUTHORIZED_WRITE
    if conflicts:
        return FinalStatus.FAILED_CONFLICT_RESOLUTION
    if low_confidence:
        return FinalStatus.FAILED_LOW_CONFIDENCE_RESOLUTION
    if blocked_no_source:
        return FinalStatus.BLOCKED_PENDING_NO_SOURCE_OR_NA_RESOLUTION
    if review_required:
        return FinalStatus.BLOCKED_PENDING_REVIEW_REQUIRED
    return FinalStatus.FAILED_COMPLETION
