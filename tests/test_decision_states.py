"""Tests for discrete decision states and field-level decision aggregation."""

from __future__ import annotations

import json
from pathlib import Path

from b2_automation.approval_maps import load_exact_approval_bundle
from b2_automation.cell_evidence import DecisionState, decide_cell, parse_decision_state
from b2_automation.decision_engine import decide_fields_for_local_packet, summarize_decisions


def test_decide_cell_missing_required_is_missing_state() -> None:
    assert decide_cell("", confidence=None, threshold=0.7, required=True) == DecisionState.MISSING


def test_decide_cell_conflict_has_priority() -> None:
    assert (
        decide_cell("abc", confidence=0.95, threshold=0.7, required=True, conflict_detected=True)
        == DecisionState.CONFLICT
    )


def test_decide_cell_low_confidence_state() -> None:
    assert decide_cell("abc", confidence=0.5, threshold=0.7, required=False) == DecisionState.LOW_CONFIDENCE


def test_parse_decision_state_strict() -> None:
    assert parse_decision_state("FILL") == DecisionState.FILL
    assert parse_decision_state(None) is None
    assert parse_decision_state("not_a_state") is None


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
    assert decisions[0].state == DecisionState.FILL
    assert decisions[0].selected_value == "A"
    assert "conflicting" in decisions[0].reason.lower()


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
    assert decisions[0].state == DecisionState.FILL
    assert decisions[0].selected_value == "A"


def test_low_confidence_single_candidate() -> None:
    retrieved = [{"chunk_id": 1, "score": 1, "text": "x", "source_file": "a.txt"}]
    suggestions = [
        {"field_id": "facility_name", "candidate_value": "Low", "confidence": 0.55, "source_file": "a.txt", "chunk_id": 1},
    ]
    decisions = decide_fields_for_local_packet(
        retrieved=retrieved,
        suggestions=suggestions,
        required_field_ids=("facility_name",),
        low_confidence_threshold=0.70,
    )
    assert decisions[0].state == DecisionState.FILL
    assert decisions[0].selected_value == "Low"
    assert "low-confidence" in decisions[0].reason.lower()


def test_missing_when_no_retrieval() -> None:
    decisions = decide_fields_for_local_packet(
        retrieved=[],
        suggestions=[],
        required_field_ids=("facility_name", "date"),
        low_confidence_threshold=0.70,
    )
    ids = {d.field_id for d in decisions}
    assert ids == {"date", "facility_name"}
    assert all(d.state == DecisionState.FILL for d in decisions)
    assert all(str(d.selected_value or "").startswith("REVIEW_REQUIRED:") for d in decisions)


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


def test_non_allowlisted_suggestion_field_gets_decision() -> None:
    retrieved = [{"chunk_id": 1, "score": 3, "text": "x", "source_file": "a.txt"}]
    suggestions = [
        {"field_id": "carrier_code", "candidate_value": "BNSF", "confidence": 0.93, "source_file": "a.txt", "chunk_id": 1},
    ]
    decisions = decide_fields_for_local_packet(
        retrieved=retrieved,
        suggestions=suggestions,
        required_field_ids=(),
        low_confidence_threshold=0.70,
    )
    assert len(decisions) == 1
    assert decisions[0].field_id == "carrier_code"
    assert decisions[0].state == DecisionState.FILL


def test_canonical_map_path_preferred_when_legacy_also_exists(tmp_path: Path) -> None:
    root = tmp_path
    (root / "schemas" / "maps").mkdir(parents=True)
    (root / "schemas" / "templates").mkdir(parents=True)
    (root / "templates").mkdir(parents=True)
    manifest = {
        "template": "t.docx",
        "cells": [{"field_id": "facility_name", "table_index": 0, "row": 1, "col": 0, "label": "x"}],
    }
    (root / "schemas" / "templates" / "Mini.json").write_text(json.dumps(manifest), encoding="utf-8")
    (root / "templates" / "t.docx").write_bytes(b"PK\x05\x06" + b"\x00" * 18)

    canonical = {
        "form_id": "B24_RL2",
        "form_version": "1",
        "manifest_path": "schemas/templates/Mini.json",
        "template_path": "templates/t.docx",
        "fields": {
            "facility_name": {"field_id": "facility_name", "table_index": 0, "row": 1, "col": 0, "label": "x"},
        },
    }
    legacy = {
        "form_id": "B24_RL2",
        "template": "wrong.docx",
        "fields": {"other": {"field_id": "other", "table_index": 0, "row": 0, "col": 0}},
    }
    (root / "schemas" / "maps" / "B24_RL2.json").write_text(json.dumps(canonical), encoding="utf-8")
    (root / "schemas" / "maps" / "B24_RL2.approval_map.json").write_text(json.dumps(legacy), encoding="utf-8")

    bundle = load_exact_approval_bundle(root, "B24_RL2")
    assert bundle is not None
    assert bundle.map_path.name == "B24_RL2.json"
