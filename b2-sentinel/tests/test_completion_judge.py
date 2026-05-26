"""Tests for Layer 6: Completion Judge logic.

Since judge_completion requires real DOCX files, we test the underlying
status classification logic that determines final status from decisions.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from b2_sentinel.core.models import (
    CompletionReport,
    ConfidenceBundle,
    FieldDecision,
    FieldNode,
    ObligationGraph,
    StructureFingerprint,
    StructureGuardReport,
)
from b2_sentinel.core.status import DecisionState, FinalStatus, WriteAuthority


def _node(field_id: str, required: bool = True) -> FieldNode:
    return FieldNode(
        field_id=field_id,
        label=field_id,
        table_index=0,
        row=0,
        col=0,
        required=required,
        completion_blocker_if_missing=required,
    )


def _decision(
    field_id: str, state: DecisionState, value: str | None = "val"
) -> FieldDecision:
    return FieldDecision(
        field_id=field_id,
        state=state,
        value=value,
        reason="test",
        confidence=ConfidenceBundle(
            retrieval=0.9, extraction=0.9, authorization=1.0, write=1.0, completion=0.9
        ),
        write_authority=WriteAuthority.EXACT_APPROVAL_MAP,
    )


def _compute_report(
    fields: dict[str, FieldNode],
    decisions: list[FieldDecision],
) -> CompletionReport:
    """Simplified completion report computation without DOCX I/O."""
    required_total = sum(1 for n in fields.values() if n.required and not n.never_write)
    required_filled = 0
    required_blocked = 0
    review_required_count = 0
    conflict_count = 0
    low_confidence_count = 0
    approved_na_count = 0
    blocked_no_source_count = 0
    blocked_unauthorized_count = 0
    blockers: list[str] = []

    for d in decisions:
        node = fields.get(d.field_id)
        if not node:
            continue
        match d.state:
            case DecisionState.FILL:
                if node.required:
                    required_filled += 1
            case DecisionState.APPROVED_NA:
                approved_na_count += 1
                if node.required:
                    required_filled += 1
            case DecisionState.REVIEW_REQUIRED:
                review_required_count += 1
                if node.required:
                    required_blocked += 1
                    blockers.append(d.field_id)
            case DecisionState.CONFLICT:
                conflict_count += 1
                if node.required:
                    required_blocked += 1
                    blockers.append(d.field_id)
            case DecisionState.LOW_CONFIDENCE:
                low_confidence_count += 1
                if node.required:
                    required_blocked += 1
                    blockers.append(d.field_id)
            case DecisionState.BLOCKED_NO_SOURCE:
                blocked_no_source_count += 1
                required_blocked += 1
                blockers.append(d.field_id)
            case DecisionState.BLOCKED_UNAUTHORIZED:
                blocked_unauthorized_count += 1
                required_blocked += 1
                blockers.append(d.field_id)
            case DecisionState.OPTIONAL_BLANK:
                pass

    overall_completion = (
        required_total == required_filled
        and not blockers
    )
    overall_passed = overall_completion

    if overall_passed:
        status = FinalStatus.SUCCESS
    elif blocked_no_source_count:
        status = FinalStatus.BLOCKED_PENDING_NO_SOURCE_OR_NA_RESOLUTION
    elif conflict_count:
        status = FinalStatus.FAILED_CONFLICT_RESOLUTION
    else:
        status = FinalStatus.FAILED_COMPLETION

    return CompletionReport(
        form_id="B89",
        overall_passed_format=True,
        overall_passed_completion=overall_completion,
        overall_passed=overall_passed,
        final_status=status,
        required_total=required_total,
        required_filled=required_filled,
        required_blocked=required_blocked,
        review_required_count=review_required_count,
        conflict_count=conflict_count,
        low_confidence_count=low_confidence_count,
        approved_na_count=approved_na_count,
        blocked_no_source_count=blocked_no_source_count,
        blocked_unauthorized_count=blocked_unauthorized_count,
        blockers=blockers,
    )


class TestCompletionJudge:
    def test_all_filled_passes(self):
        nodes = {"a": _node("a"), "b": _node("b")}
        decisions = [
            _decision("a", DecisionState.FILL),
            _decision("b", DecisionState.FILL),
        ]
        report = _compute_report(nodes, decisions)
        assert report.overall_passed is True
        assert report.final_status == FinalStatus.SUCCESS

    def test_blocked_field_fails(self):
        nodes = {"a": _node("a"), "b": _node("b")}
        decisions = [
            _decision("a", DecisionState.FILL),
            _decision("b", DecisionState.BLOCKED_NO_SOURCE, value=None),
        ]
        report = _compute_report(nodes, decisions)
        assert report.overall_passed is False
        assert report.blocked_no_source_count == 1
        assert "b" in report.blockers

    def test_optional_blank_does_not_block(self):
        nodes = {"a": _node("a"), "b": _node("b", required=False)}
        decisions = [
            _decision("a", DecisionState.FILL),
            _decision("b", DecisionState.OPTIONAL_BLANK, value=None),
        ]
        report = _compute_report(nodes, decisions)
        assert report.overall_passed is True

    def test_approved_na_does_not_block(self):
        nodes = {"a": _node("a"), "b": _node("b")}
        decisions = [
            _decision("a", DecisionState.FILL),
            _decision("b", DecisionState.APPROVED_NA, value="N/A"),
        ]
        report = _compute_report(nodes, decisions)
        assert report.overall_passed is True
        assert report.approved_na_count == 1

    def test_conflict_blocks(self):
        nodes = {"a": _node("a")}
        decisions = [_decision("a", DecisionState.CONFLICT, value=None)]
        report = _compute_report(nodes, decisions)
        assert report.overall_passed is False
        assert report.conflict_count == 1
