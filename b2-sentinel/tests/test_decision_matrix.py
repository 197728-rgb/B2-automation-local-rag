"""Tests for the 8-state decision matrix (Layer 3)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from b2_sentinel.core.models import EvidenceLedgerEntry, FieldNode
from b2_sentinel.core.status import DecisionState, WriteAuthority
from b2_sentinel.layer3_decision_engine.decide import decide_field


def _node(
    required: bool = True,
    n_a_allowed: bool = False,
    never_write: bool = False,
    write_authority: WriteAuthority = WriteAuthority.EXACT_APPROVAL_MAP,
) -> FieldNode:
    return FieldNode(
        field_id="test.field",
        label="Test Field",
        table_index=0,
        row=0,
        col=0,
        required=required,
        n_a_allowed=n_a_allowed,
        evidence_required=required,
        completion_blocker_if_missing=required,
        never_write=never_write,
        write_authority=write_authority,
    )


def _evidence(
    decision: str = "usable",
    confidence: float = 0.9,
    candidate_value: str | None = "value",
) -> EvidenceLedgerEntry:
    return EvidenceLedgerEntry(
        field_id="test.field",
        candidate_value=candidate_value,
        source_file="test.pdf",
        source_type="pdf",
        confidence=confidence,
        decision=decision,
    )


class TestDecisionMatrix:
    """Every cell of the decision matrix from the spec."""

    def test_fill_when_evidence_found_and_authorized(self):
        node = _node(required=True)
        evidence = _evidence(decision="usable", confidence=0.9)
        result = decide_field(node, evidence, n_a_approved=False)
        assert result.state == DecisionState.FILL

    def test_blocked_unauthorized_when_no_authority(self):
        node = _node(required=True, write_authority=WriteAuthority.UNAUTHORIZED)
        evidence = _evidence(decision="usable", confidence=0.9)
        result = decide_field(node, evidence, n_a_approved=False)
        assert result.state == DecisionState.BLOCKED_UNAUTHORIZED

    def test_approved_na_when_no_evidence_but_na_approved(self):
        node = _node(required=True, n_a_allowed=True)
        evidence = _evidence(decision="missing", candidate_value=None)
        result = decide_field(node, evidence, n_a_approved=True)
        assert result.state == DecisionState.APPROVED_NA

    def test_blocked_no_source_when_no_evidence_required(self):
        node = _node(required=True, n_a_allowed=False)
        evidence = _evidence(decision="missing", candidate_value=None)
        result = decide_field(node, evidence, n_a_approved=False, review_marker_allowed=False)
        assert result.state == DecisionState.BLOCKED_NO_SOURCE

    def test_optional_blank_when_not_required_no_evidence(self):
        node = _node(required=False)
        evidence = _evidence(decision="missing", candidate_value=None)
        result = decide_field(node, evidence, n_a_approved=False)
        assert result.state == DecisionState.OPTIONAL_BLANK

    def test_low_confidence_when_evidence_weak(self):
        node = _node(required=True)
        evidence = _evidence(decision="weak", confidence=0.35)
        result = decide_field(node, evidence, n_a_approved=False)
        assert result.state == DecisionState.LOW_CONFIDENCE

    def test_conflict_when_multiple_values(self):
        node = _node(required=True)
        evidence = _evidence(decision="conflict", confidence=0.8)
        result = decide_field(node, evidence, n_a_approved=False)
        assert result.state == DecisionState.CONFLICT

    def test_review_required_when_no_evidence_but_marker_allowed(self):
        node = _node(required=True, n_a_allowed=True)
        evidence = _evidence(decision="missing", candidate_value=None)
        result = decide_field(node, evidence, n_a_approved=False, review_marker_allowed=True)
        assert result.state == DecisionState.REVIEW_REQUIRED

    def test_none_evidence_treated_as_missing(self):
        node = _node(required=True, n_a_allowed=False)
        result = decide_field(node, None, n_a_approved=False, review_marker_allowed=False)
        assert result.state == DecisionState.BLOCKED_NO_SOURCE

    def test_never_write_field_optional_blank(self):
        node = _node(required=True, never_write=True)
        evidence = _evidence(decision="usable")
        result = decide_field(node, evidence, n_a_approved=False)
        assert result.state == DecisionState.OPTIONAL_BLANK
