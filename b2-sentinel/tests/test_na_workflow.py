"""Tests for Layer 7: N/A Exception Workflow."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from b2_sentinel.core.models import (
    EvidenceLedgerEntry,
    FieldNode,
    NAExceptionEntry,
    ObligationGraph,
)
from b2_sentinel.core.status import WriteAuthority


def _node(field_id: str, n_a_allowed: bool = True, required: bool = True) -> FieldNode:
    return FieldNode(
        field_id=field_id,
        label=field_id.replace(".", " "),
        table_index=0,
        row=0,
        col=0,
        required=required,
        n_a_allowed=n_a_allowed,
        evidence_required=True,
        completion_blocker_if_missing=True,
    )


def _graph(fields: dict[str, FieldNode]) -> ObligationGraph:
    return ObligationGraph(
        form_id="B89",
        form_version="2026",
        template_path="templates/B89.docx",
        fields=fields,
        required_total=len(fields),
    )


def _missing(field_id: str) -> EvidenceLedgerEntry:
    return EvidenceLedgerEntry(field_id=field_id, decision="missing")


def _usable(field_id: str) -> EvidenceLedgerEntry:
    return EvidenceLedgerEntry(
        field_id=field_id,
        candidate_value="value",
        decision="usable",
        confidence=0.9,
    )


class TestNAWorkflow:
    def test_approved_na_when_policy_allows(self, monkeypatch):
        node = _node("test.field", n_a_allowed=True)
        graph = _graph({"test.field": node})
        ledger = {"test.field": _missing("test.field")}

        mock_policy = {
            "test.field": {
                "reason": "Not applicable for this condition",
                "policy_id": "NA-TEST-001",
                "approved_by": "approved_exception_policy",
            }
        }
        monkeypatch.setattr(
            "b2_sentinel.layer7_exception_engine.na_workflow.load_policy",
            lambda form_id: mock_policy,
        )

        from b2_sentinel.layer7_exception_engine.na_workflow import evaluate_na

        approvals, log = evaluate_na(graph, ledger)
        assert approvals.get("test.field") is True
        assert len(log) == 1
        assert log[0].status == "approved_na"
        assert log[0].policy_id == "NA-TEST-001"

    def test_no_approval_when_no_policy_entry(self, monkeypatch):
        node = _node("test.field", n_a_allowed=True)
        graph = _graph({"test.field": node})
        ledger = {"test.field": _missing("test.field")}

        monkeypatch.setattr(
            "b2_sentinel.layer7_exception_engine.na_workflow.load_policy",
            lambda form_id: {},
        )

        from b2_sentinel.layer7_exception_engine.na_workflow import evaluate_na

        approvals, log = evaluate_na(graph, ledger)
        assert "test.field" not in approvals
        assert len(log) == 0

    def test_no_approval_when_na_not_allowed_on_field(self, monkeypatch):
        node = _node("test.field", n_a_allowed=False)
        graph = _graph({"test.field": node})
        ledger = {"test.field": _missing("test.field")}

        monkeypatch.setattr(
            "b2_sentinel.layer7_exception_engine.na_workflow.load_policy",
            lambda form_id: {
                "test.field": {"reason": "Trying to force N/A", "policy_id": "NA-FAKE"},
            },
        )

        from b2_sentinel.layer7_exception_engine.na_workflow import evaluate_na

        approvals, log = evaluate_na(graph, ledger)
        assert "test.field" not in approvals

    def test_not_evaluated_when_evidence_usable(self, monkeypatch):
        node = _node("test.field", n_a_allowed=True)
        graph = _graph({"test.field": node})
        ledger = {"test.field": _usable("test.field")}

        monkeypatch.setattr(
            "b2_sentinel.layer7_exception_engine.na_workflow.load_policy",
            lambda form_id: {
                "test.field": {"reason": "N/A", "policy_id": "NA-TEST-001"},
            },
        )

        from b2_sentinel.layer7_exception_engine.na_workflow import evaluate_na

        approvals, log = evaluate_na(graph, ledger)
        assert "test.field" not in approvals
        assert len(log) == 0
