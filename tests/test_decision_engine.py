"""Tests for discrete decision states (Stage 5)."""

from __future__ import annotations

from b2_automation.cell_evidence import DecisionState
from b2_automation.decision_engine import decide_fields_for_local_packet, summarize_decisions


def test_conflict_when_two_high_confidence_values_disagree() -> None:
    retrieved = [{"chunk_id": 1, "score": 3, "text": "x", "source_file": "a.txt"}]
    suggestions = [
        {"field_id": "facility_name", "candidate_value": "A", "confidence": 0.95, "source_file": "a.txt", "chunk_id": 1},
        {"field_id": "facility_name", "candidate_value": "B", "confidence": 0.92, "source_file": "a.txt", "chunk_id": 1},
    ]
    decisions = decide_fields_for_local_packet(
        retrieved=retrieved,
        suggestions=suggestions,
        required_field_ids=("facility_name",),
        low_confidence_threshold=0.70,
    )
    assert len(decisions) == 1
    assert decisions[0].state == DecisionState.CONFLICT


def test_review_required_when_values_differ_but_not_both_high() -> None:
    retrieved = [{"chunk_id": 1, "score": 3, "text": "x", "source_file": "a.txt"}]
    suggestions = [
        {"field_id": "facility_name", "candidate_value": "A", "confidence": 0.85, "source_file": "a.txt", "chunk_id": 1},
        {"field_id": "facility_name", "candidate_value": "B", "confidence": 0.55, "source_file": "a.txt", "chunk_id": 1},
    ]
    decisions = decide_fields_for_local_packet(
        retrieved=retrieved,
        suggestions=suggestions,
        required_field_ids=("facility_name",),
        low_confidence_threshold=0.70,
    )
    assert decisions[0].state == DecisionState.REVIEW_REQUIRED


def test_missing_when_no_retrieval() -> None:
    decisions = decide_fields_for_local_packet(
        retrieved=[],
        suggestions=[],
        required_field_ids=("facility_name", "date"),
        low_confidence_threshold=0.70,
    )
    ids = {d.field_id for d in decisions}
    assert ids == {"date", "facility_name"}
    assert all(d.state == DecisionState.MISSING for d in decisions)


def test_fill_when_single_high_candidate() -> None:
    retrieved = [{"chunk_id": 1, "score": 3, "text": "x", "source_file": "a.txt"}]
    suggestions = [
        {"field_id": "facility_name", "candidate_value": "Solo", "confidence": 0.91, "source_file": "a.txt", "chunk_id": 1},
    ]
    decisions = decide_fields_for_local_packet(
        retrieved=retrieved,
        suggestions=suggestions,
        required_field_ids=("facility_name",),
        low_confidence_threshold=0.70,
    )
    assert decisions[0].state == DecisionState.FILL
    summary = summarize_decisions(decisions)
    assert summary["counts_by_state"]["FILL"] == 1
    assert summary["fill_eligible_field_ids"] == ["facility_name"]
