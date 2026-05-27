"""Cover page extraction guards for structured audit information."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from b2_sentinel.core.models import SourceChunk
from b2_sentinel.innovations.alias_brain import AliasBrain
from b2_sentinel.layer1_form_brain.obligation_graph import build_obligation_graph
from b2_sentinel.layer2_evidence_hunter.extractors import (
    _label_value_lines_from_pdf_table,
    extract_json,
)
from b2_sentinel.layer2_evidence_hunter.wave4_contamination import wave4_contamination
from b2_sentinel.layer2_evidence_hunter.wave2_normalize import wave2_normalize
from b2_sentinel.layer3_decision_engine.value_sanity import is_value_plausible


def test_cover_page_matches_camel_case_audit_information_json(tmp_path: Path) -> None:
    source = tmp_path / "audit.json"
    source.write_text(
        json.dumps(
            {
                "auditInformation": {
                    "stationStencil": "DLGA",
                    "auditType": "SP",
                    "facilityWorkforceSize": 50,
                    "openMeetingDate": "2026-05-05",
                    "closingMeetingDate": "2026-05-07",
                    "leadAuditor": "Lucho Rodriguez",
                    "auditTeamSize": 3,
                }
            }
        ),
        encoding="utf-8",
    )

    graph = build_obligation_graph("Cover_Page")
    chunks = list(extract_json(source))
    chunks.append(
        SourceChunk(
            chunk_id="pdf.page.3",
            source_file="packet.pdf",
            source_type="pdf",
            page=3,
            text="Closing Meeting: Yes",
            scope_hint="Cover_Page",
        )
    )

    entries = wave2_normalize(
        chunks,
        graph,
        alias_brain=AliasBrain(),
    )

    assert entries["station_stencil_code"].candidate_value == "DLGA"
    assert entries["audit_type"].candidate_value == "SP"
    assert entries["open_meeting_date"].candidate_value == "2026-05-05"
    assert entries["closing_meeting_date"].candidate_value == "2026-05-07"
    assert entries["closing_meeting_date"].decision == "usable"
    assert entries["boe_lead_auditor"].candidate_value == "Lucho Rodriguez"


def test_cover_page_sanity_rejects_pdf_overcapture() -> None:
    assert not is_value_plausible(
        "station_stencil_code",
        "UTBC 2. Audit Type: C1 3. Facility Workforce Size: 6",
    )
    assert not is_value_plausible(
        "open_meeting_date",
        "6/10/2025 5. Closing Meeting Date: 6/11/2025",
    )
    assert not is_value_plausible("closing_meeting_date", "Yes")


def test_specific_pitp_json_keys_beat_generic_nested_procedure_ids(tmp_path: Path) -> None:
    source = tmp_path / "b89.json"
    source.write_text(
        json.dumps(
            {
                "pitpProcedure": {
                    "documentName": "Production, Inspection, and Test",
                    "pitpId": "QP 2.5-03",
                },
                "weldInspection": {
                    "weldProcedure": {
                        "procedureName": "Visual Inspection of Welds",
                        "procedureId": "RES213",
                    }
                },
                "tcidRecords": {
                    "tcidProcedure": {
                        "procedureName": "TCID Procedure",
                        "procedureId": "RES217",
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    graph = build_obligation_graph("B89")
    entries = wave2_normalize(
        list(extract_json(source)),
        graph,
        alias_brain=AliasBrain.from_disk(),
    )

    assert entries["pitp.id"].decision == "usable"
    assert entries["pitp.id"].candidate_value == "QP 2.5-03"
    assert entries["pitp.name"].decision == "usable"
    assert entries["pitp.name"].candidate_value == "Production, Inspection, and Test"


def test_combined_json_array_labels_fill_b89_pitp_from_first_procedure(tmp_path: Path) -> None:
    source = tmp_path / "combined.json"
    source.write_text(
        json.dumps(
            {
                "procedures": [
                    {
                        "procedureName": "Production, Inspection, and Test Plan (2.5)",
                        "procedureId": "GQAP 2.5",
                    },
                    {
                        "procedureName": "TCID Procedure",
                        "procedureId": "PR-TC-19",
                    },
                ]
            }
        ),
        encoding="utf-8",
    )

    graph = build_obligation_graph("B89")
    entries = wave2_normalize(
        list(extract_json(source)),
        graph,
        alias_brain=AliasBrain.from_disk(),
    )

    assert entries["pitp.id"].decision == "usable"
    assert entries["pitp.id"].candidate_value == "GQAP 2.5"
    assert entries["pitp.name"].decision == "usable"
    assert entries["pitp.name"].candidate_value == "Production, Inspection, and Test Plan (2.5)"


def test_multi_scope_json_global_values_are_not_demoted() -> None:
    graph = build_obligation_graph("B89")
    entry = wave2_normalize(
        [
            SourceChunk(
                chunk_id="combined.section.carOwnerPermissions.1",
                source_file="combined.json",
                source_type="json",
                text="tankCarOwnerName: CIT",
                scope_hint=None,
            ),
            SourceChunk(
                chunk_id="combined.section.safetySystemDetails.2",
                source_file="combined.json",
                source_type="json",
                text="safetySystemType: Insulation/Jacket",
                scope_hint="B89",
            ),
        ],
        graph,
        alias_brain=AliasBrain.from_disk(),
    )["tco.name"]

    hardened = wave4_contamination(graph, {"tco.name": entry}, [
        SourceChunk(
            chunk_id="combined.section.carOwnerPermissions.1",
            source_file="combined.json",
            source_type="json",
            text="tankCarOwnerName: CIT",
            scope_hint=None,
        ),
        SourceChunk(
            chunk_id="combined.section.safetySystemDetails.2",
            source_file="combined.json",
            source_type="json",
            text="safetySystemType: Insulation/Jacket",
            scope_hint="B89",
        ),
        SourceChunk(
            chunk_id="combined.section.cover.3",
            source_file="combined.json",
            source_type="json",
            text="auditType: SP",
            scope_hint="Cover_Page",
        ),
    ])["tco.name"]

    assert hardened.decision == "usable"
    assert hardened.confidence >= 0.9


def test_structured_json_fills_b24_design_and_material_fields(tmp_path: Path) -> None:
    source = tmp_path / "combined.json"
    source.write_text(
        json.dumps(
            {
                "carOwnerPermissions": {
                    "tankCarOwnerName": "CIT",
                    "datePermissionReceived": "2024-05-20",
                },
                "designControl": {
                    "carMarkAndNumber": "DBUX 250086",
                    "tankCarDesignSpecification": "DOT111A100W1",
                    "aarForm42Number": "L016048A",
                    "drawings": [
                        {
                            "drawingType": "Tank Arrangement/Attachment",
                            "drawingNumber": "D43520",
                        }
                    ],
                },
                "materials": [
                    {
                        "materialSpecification": "A516 Gr. 70",
                        "mtrNumber": "B520005B",
                    },
                    {
                        "materialSpecification": "A516 Gr. 70",
                        "mtrNumber": "B520005B",
                    },
                    {"materialSpecification": "A572 Grade 50"},
                ],
                "procedures": [
                    {
                        "procedureName": "Production, Inspection, and Test Plan (2.5)",
                        "procedureId": "GQAP 2.5",
                        "approvedBy": "B. De La Garza",
                        "dateApproved": "2025-04-20",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    graph = build_obligation_graph("B24_RL2")
    entries = wave2_normalize(
        list(extract_json(source)),
        graph,
        alias_brain=AliasBrain.from_disk(),
    )

    assert entries["tco_permission_date"].candidate_value == "2024-05-20"
    assert entries["pitp_document_name"].candidate_value == "Production, Inspection, and Test Plan (2.5)"
    assert entries["pitp_id"].candidate_value == "GQAP 2.5"
    assert entries["pitp_approved_by"].candidate_value == "B. De La Garza"
    assert entries["tank_design_spec"].candidate_value == "DOT111A100W1"
    assert entries["four_two_drawing_number"].candidate_value == "D43520"
    assert entries["test_plate_tank_mtr"].candidate_value == "B520005B"
    assert entries["attachment_material"].candidate_value == "A572 Grade 50"


def test_pdf_table_rows_emit_label_value_evidence() -> None:
    lines = _label_value_lines_from_pdf_table(
        [
            ["Car Mark and Number", None, "Tank Car Design Specification", "AAR 4-2 (AAR Number)"],
            ["TILX 261510", None, "DOT111A100W1", "L056077"],
            ["", "Tank Car or Lining/Coating", "Date Permission", "Written Instructions from TCO / L/CO"],
            [None, "Owner (TCO / L/CO) Name", "Received", None],
            ["Trinity Leasing", None, "3/1/2026", "Facility received written confirmation."],
        ]
    )

    assert "Car Mark and Number: TILX 261510" in lines
    assert "Tank Car Design Specification: DOT111A100W1" in lines
    assert "AAR 4-2 (AAR Number): L056077" in lines
    assert (
        "Tank Car or Lining/Coating Owner (TCO / L/CO) Name: Trinity Leasing"
        in lines
    )
