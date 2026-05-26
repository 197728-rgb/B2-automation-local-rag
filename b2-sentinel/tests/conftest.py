"""Shared test fixtures for B2 SENTINEL."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC = REPO_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from b2_sentinel.core.models import (
    ApprovalMap,
    ApprovalMapField,
    ConfidenceBundle,
    EvidenceLedger,
    EvidenceLedgerEntry,
    FieldDecision,
    FieldNode,
    NAExceptionEntry,
    ObligationGraph,
    StructureFingerprint,
)
from b2_sentinel.core.status import DecisionState, WriteAuthority


@pytest.fixture
def sample_field_node() -> FieldNode:
    return FieldNode(
        field_id="car.mark",
        label="Car Initial & Number",
        table_index=0,
        row=1,
        col=1,
        required=True,
        n_a_allowed=False,
        evidence_required=True,
        completion_blocker_if_missing=True,
        aliases=["car_number", "tank_car_number"],
        expansion_search_terms=["car mark", "car initial", "reporting mark"],
    )


@pytest.fixture
def sample_optional_node() -> FieldNode:
    return FieldNode(
        field_id="remarks",
        label="Remarks",
        table_index=2,
        row=5,
        col=0,
        required=False,
        optional=True,
        n_a_allowed=False,
        evidence_required=False,
        completion_blocker_if_missing=False,
    )


@pytest.fixture
def sample_obligation_graph(sample_field_node: FieldNode) -> ObligationGraph:
    return ObligationGraph(
        form_id="B89",
        form_version="2026",
        template_path="templates/B89.docx",
        fields={"car.mark": sample_field_node},
        required_total=1,
        optional_total=0,
        never_write_total=0,
    )


@pytest.fixture
def sample_evidence_usable() -> EvidenceLedgerEntry:
    return EvidenceLedgerEntry(
        field_id="car.mark",
        candidate_value="UTLX 12345",
        source_file="Combine May 18, 2026.pdf",
        source_type="pdf",
        page=1,
        chunk_id="chunk-001",
        confidence=0.92,
        scope="B89",
        decision="usable",
        wave_found_in=1,
    )


@pytest.fixture
def sample_evidence_weak() -> EvidenceLedgerEntry:
    return EvidenceLedgerEntry(
        field_id="car.mark",
        candidate_value="UTLX?",
        source_file="notes.txt",
        source_type="txt",
        confidence=0.35,
        decision="weak",
        wave_found_in=3,
    )


@pytest.fixture
def sample_evidence_conflict() -> EvidenceLedgerEntry:
    return EvidenceLedgerEntry(
        field_id="car.mark",
        candidate_value="UTLX 12345",
        source_file="source_a.pdf",
        source_type="pdf",
        confidence=0.8,
        decision="conflict",
        alternates=[{"value": "GATX 67890", "source": "source_b.pdf"}],
        wave_found_in=2,
    )


@pytest.fixture
def sample_evidence_missing() -> EvidenceLedgerEntry:
    return EvidenceLedgerEntry(
        field_id="car.mark",
        decision="missing",
    )


@pytest.fixture
def sample_approval_map() -> ApprovalMap:
    return ApprovalMap(
        form_id="B89",
        form_version="2026",
        template_path="templates/B89.docx",
        fields={
            "car.mark": ApprovalMapField(
                field_id="car.mark",
                table_index=0,
                row=1,
                col=1,
                required=True,
                label="Car Initial & Number",
            )
        },
    )
