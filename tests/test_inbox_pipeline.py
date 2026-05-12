"""Inbox pipeline regression tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from docx import Document

from b2_automation.docupipe_client import DocuPipeConfigError, process_pdf
from b2_automation.inbox_pipeline import _clear_scoped_filled_docx, run_inbox_pipeline
from b2_automation.local_extraction import DEFAULT_REVIEW_FORMS, supported_evidence_files
from b2_automation.paths import B24_SHARED_TEMPLATE_DOCX


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_inbox_pipeline_local_default_generates_all_form_packets(tmp_path: Path) -> None:
    root = _repo_root()
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    (inbox / "packet_one.txt").write_text(
        "\n".join(
            [
                "Cover Page Facility: Midwest Tank Rail Inc",
                "B24 RL2 objective evidence Date: 2026-05-07",
                "B81 stub sill evidence Car: DOTX 123456",
                "B89 insulation test plate evidence",
                "B90 RLS return to service evidence Auditor: Casey",
            ]
        ),
        encoding="utf-8",
    )
    (inbox / "evidence_sample.txt").write_text(
        "Sample audit evidence line for local inbox dry run. Company: Example Railroad Year: 2025",
        encoding="utf-8",
    )
    (inbox / "procedure.txt").write_text(
        "Cover Page procedure note. The Facility: assigned code for AAR and internal action tracking.",
        encoding="utf-8",
    )

    result = run_inbox_pipeline(root=root, inbox=inbox, out_dir=tmp_path / "run")

    sample_tpl = root / "templates" / "B24_RL2.docx"
    run_manifest_data = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert result.status in {"success", "review_required"}
    if sample_tpl.is_file():
        guard = json.loads((tmp_path / "run" / "structure_guard_report.json").read_text(encoding="utf-8"))
        assert guard["pass"] is True
        assert run_manifest_data.get("structure_guard_passed") is True
        assert result.filled_docx_path is not None and result.filled_docx_path.is_file()
        assert result.filled_docx_path.name.endswith("_filled.docx")
        assert result.filled_docx_paths
        assert all(p.is_file() for p in result.filled_docx_paths)
        assert run_manifest_data.get("structure_guard_failed_forms") == []
    else:
        assert result.filled_docx_path is None
        assert result.filled_docx_paths == ()
    assert result.manifest_path.is_file()
    assert result.review_json_path.is_file()
    assert result.review_md_path.is_file()

    run_dir = tmp_path / "run"
    assert not list((run_dir / "raw").glob("*.docupipe.json"))
    assert (run_dir / "raw" / "packet_one.ocr.json").is_file()
    assert (run_dir / "raw" / "packet_one.metadata.json").is_file()
    assert (run_dir / "raw" / "packet_one.chunks.json").is_file()
    assert (run_dir / "raw" / "local_rag_retrieval.json").is_file()
    assert (run_dir / "rag_selection_report.json").is_file()

    review = json.loads(result.review_json_path.read_text(encoding="utf-8"))
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert review["docupipe_used"] is False
    assert manifest["docupipe_used"] is False
    assert manifest["legacy_adapter_used"] is False
    assert set(review["forms"]) == set(DEFAULT_REVIEW_FORMS)
    assert review["production_scope_forms"] == list(DEFAULT_REVIEW_FORMS)
    assert "evidence_sample.txt" not in {row["source_file"] for row in review["inputs"]}
    canonical = json.loads((run_dir / "canonical_evidence.json").read_text(encoding="utf-8"))
    facility_values = [
        str(row.get("selected_value") or "")
        for row in canonical["fields"]
        if row.get("field_id") == "facility_name" and row.get("selected_value")
    ]
    assert facility_values
    assert set(facility_values) == {"Midwest Tank Rail Inc"}
    cover_packet = json.loads((run_dir / "review" / "Cover_Page_evidence_packet.json").read_text(encoding="utf-8"))
    assert not [
        row
        for row in cover_packet["field_suggestions"]
        if row["field_id"] == "facility_name" and row["candidate_value"] == "assigned code for"
    ]
    for form in DEFAULT_REVIEW_FORMS:
        packet_path = run_dir / "review" / f"{form}_evidence_packet.json"
        assert packet_path.is_file()
        assert (run_dir / "review" / f"{form}_review.md").is_file()
        packet = json.loads(packet_path.read_text(encoding="utf-8"))
        assert packet.get("production_scope") is True
        assert "b24_rl1_legacy_only" not in packet
        assert "missing_fields" in packet
        assert "conflicts" in packet
        assert "low_confidence_fields" in packet
        assert "decision_summary" in packet
        assert "field_decisions" in packet
        for row in packet["field_decisions"]:
            assert row["state"] in {
                "FILL",
                "BLANK",
                "REVIEW_REQUIRED",
                "MISSING",
                "CONFLICT",
                "LOW_CONFIDENCE",
            }
        assert packet["field_suggestions"]


def test_clear_scoped_filled_docx_removes_stale_outputs(tmp_path: Path) -> None:
    filled = tmp_path / "filled"
    filled.mkdir()
    stale = filled / "B81_filled.docx"
    stale.write_bytes(b"PK\x03\x04")
    untouched = filled / "B89_filled.docx"
    untouched.write_bytes(b"PK\x03\x04")
    _clear_scoped_filled_docx(filled, ("B81",))
    assert not stale.is_file()
    assert untouched.is_file()


def test_inbox_pipeline_blocks_b81_fill_when_review_state_remains(tmp_path: Path) -> None:
    root = _repo_root()
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    (inbox / "b81_noise.txt").write_text(
        "\n".join(
            [
                "B81 stub sill evidence and side sill review for tank car repair.",
                "Facility: Demo Rail Shop",
                "This packet intentionally omits the required date.",
            ]
        ),
        encoding="utf-8",
    )
    out_dir = tmp_path / "run"
    filled_dir = out_dir / "filled"
    filled_dir.mkdir(parents=True)
    stale = filled_dir / "B81_filled.docx"
    stale.write_bytes(b"PK\x03\x04")

    result = run_inbox_pipeline(
        root=root,
        inbox=inbox,
        out_dir=out_dir,
        review_forms=("B81",),
        low_confidence_threshold=0.0,
    )

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    review = json.loads(result.review_json_path.read_text(encoding="utf-8"))
    b81_docx = next(item for item in manifest["docx_generation"] if item["form_id"] == "B81")
    b81_decisions = review["form_packets"]["B81"]["field_decisions"]

    assert result.status == "review_required"
    assert any(row["state"] == "FILL" for row in b81_decisions)
    assert any(row["state"] in {"MISSING", "CONFLICT", "LOW_CONFIDENCE", "REVIEW_REQUIRED"} for row in b81_decisions)
    assert b81_docx["status"] == "skipped_review_required"
    assert b81_docx["filled_docx"] is None
    assert "B81" in manifest["review_blocked_forms"]
    assert manifest["skipped_review_required"] == ["B81"]
    assert manifest["blocking_review_reasons"]["B81"]
    assert result.filled_docx_path is None
    assert result.filled_docx_paths == ()
    assert not stale.exists()


def test_inbox_pipeline_blocks_b81_docx_when_only_basic_fields_are_present(tmp_path: Path) -> None:
    root = _repo_root()
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    (inbox / "b81_bilingual.txt").write_text(
        "\n".join(
            [
                "B81 stub sill evidence for tank car repair.",
                "Estacion/ Station:",
                "Taller Mexico FTVM",
                "Fecha I Date: 06-Mayo-2025",
            ]
        ),
        encoding="utf-8",
    )

    result = run_inbox_pipeline(root=root, inbox=inbox, out_dir=tmp_path / "run", review_forms=("B81",))

    review = json.loads(result.review_json_path.read_text(encoding="utf-8"))
    packet = review["form_packets"]["B81"]
    selected = {row["field_id"]: row["selected_value"] for row in packet["field_decisions"]}
    assert selected["facility_name"] == "Taller Mexico FTVM"
    assert selected["date"] == "2025-05-06"
    assert packet["missing_fields"] == []
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    docx = manifest["docx_generation"][0]
    assert result.status == "review_required"
    assert docx["status"] == "skipped_review_required"
    assert "car.mark:MISSING" in "\n".join(docx["blocking_review_reasons"])
    assert result.filled_docx_path is None
    assert result.filled_docx_paths == ()


def test_inbox_pipeline_blocks_b81_run_level_evidence_when_required_map_fields_are_missing(tmp_path: Path) -> None:
    root = _repo_root()
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    (inbox / "Adobe Scan May 05, 2026.txt").write_text(
        "B81 stub sill evidence for tank car repair.",
        encoding="utf-8",
    )
    (inbox / "b24.1.txt").write_text(
        "B24 RL2 evidence\nEstacion/ Station: Taller Mexico FTVM\n",
        encoding="utf-8",
    )

    result = run_inbox_pipeline(root=root, inbox=inbox, out_dir=tmp_path / "run", review_forms=("B81",))

    review = json.loads(result.review_json_path.read_text(encoding="utf-8"))
    packet = review["form_packets"]["B81"]
    selected = {row["field_id"]: row["selected_value"] for row in packet["field_decisions"]}
    assert selected["facility_name"] == "Taller Mexico FTVM"
    assert selected["date"] == "2026-05-05"
    assert packet["missing_fields"] == []
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    docx = manifest["docx_generation"][0]
    assert result.status == "review_required"
    assert docx["status"] == "skipped_review_required"
    assert "B81" in manifest["review_blocked_forms"]
    assert result.filled_docx_path is None


def test_inbox_pipeline_patches_multiple_b24_mapped_fields(tmp_path: Path) -> None:
    root = _repo_root()
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    (inbox / "b24_mapped.txt").write_text(
        "\n".join(
            [
                "B24 RL2 MANTENIMIENTO Y MODIFICACION DE LOS CARROS TANQUE RL2",
                "Estacion/ Station: Taller Mexico FTVM",
                "Fecha I Date: 06-Mayo-2025",
                "Car Mark: PROBETA MUESTRA",
                "Car Number: PAWCT-824",
                "Car Type: TANK CAR",
                "pitp_document_name: PC-TC-01",
                "pitp_id: PC-TC-01",
                "pitp_approved_by: Casey",
                "pitp_date_approved: 2026-05-05",
                "aar_form_4_2_number: AAR-42-001",
                "four_two_drawing_number: DWG-100",
                "Specimen plate A516 Grado 70",
                "test_plate_tank_mtr: MTR-777",
                "attachment_material: A36",
            ]
        ),
        encoding="utf-8",
    )

    result = run_inbox_pipeline(root=root, inbox=inbox, out_dir=tmp_path / "run", review_forms=("B24_RL2",))

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    docx = manifest["docx_generation"][0]
    assert result.status == "success"
    assert {
        "facility_name",
        "tco_permission_date",
        "tco_written_instructions",
        "car_mark",
        "tank_design_spec",
        "test_plate_tank_material",
    }.issubset(set(docx["patched_fields"]))
    review = json.loads(result.review_json_path.read_text(encoding="utf-8"))
    selected = {row["field_id"]: row["selected_value"] for row in review["form_packets"]["B24_RL2"]["field_decisions"]}
    assert selected["car_mark"] == "PROBETA MUESTRA PAWCT-824"
    assert selected["tank_design_spec"] == "TANK CAR"
    filled_doc = Document(str(result.filled_docx_path))
    assert "MANTENIMIENTO Y MODIFICACION" in filled_doc.tables[0].rows[4].cells[8].text


def test_inbox_pipeline_patches_b89_from_docupipe_schema_json(tmp_path: Path) -> None:
    root = _repo_root()
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    (inbox / "Adobe Scan May 05, 2026.json").write_text(
        json.dumps(
            {
                "activity": {
                    "code": "B89",
                    "repairLevel": "RLJ",
                    "scope": "MANTENIMIENTO, MODIFICACION y CALIFICACION DE SISTEMAS DE SEGURIDAD",
                },
                "demonstration": {
                    "carNumber": "PAWCT-RLJ",
                    "carType": "TANK CAR",
                    "station": "Taller Mexico FTVM",
                },
                "aar": {"form42Number": "AAR-89-001"},
                "jacketPatch": {
                    "specimenPlate": "A36 1/8 in o A1110 cal. 11",
                    "patchPlateSize": "12 in X 12 in",
                    "targetFilletSize": "3/16 in filete",
                },
                "pitp": "PC-TC-01",
            }
        ),
        encoding="utf-8",
    )

    result = run_inbox_pipeline(root=root, inbox=inbox, out_dir=tmp_path / "run", review_forms=("B89",))

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    docx = manifest["docx_generation"][0]
    assert result.status == "success"
    assert docx["status"] == "filled"
    assert {
        "tco.name",
        "tco.permission_date",
        "tco.instructions",
        "car.mark",
        "car.design_spec",
        "safety_system.type",
        "aar.form_4_2.number",
        "materials.insulation.spec",
        "materials.jacket.spec",
        "test_fixture.patch_plate.size",
        "test_fixture.weld.length",
        "pitp.name",
        "pitp.id",
    }.issubset(set(docx["patched_fields"]))
    filled_doc = Document(str(result.filled_docx_path))
    assert "MANTENIMIENTO, MODIFICACION" in filled_doc.tables[0].rows[2].cells[5].text


def test_inbox_pipeline_patches_b90_from_stub_sill_packet_text(tmp_path: Path) -> None:
    root = _repo_root()
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    (inbox / "b90_packet.txt").write_text(
        "\n".join(
            [
                "B90 Maintenance, Alteration, and Qualification of Tank Car Stub Sills",
                "Estacion/ Station: Taller Mexico FTVM",
                "Fecha I Date: 06-Mayo-2025",
                "MANTENIMIENTO Y MODIFICACION DE STUB SILLS",
                "Car Mark: PROBETA MUESTRA",
                "Car Number: PAWCT-B90",
                "Car Type: TANK CAR",
                "General Arrangement - D-41759 L056040A",
                "Specimen plate A572 Grado 50",
                "Junta de soldaura en T/T-weld joint",
                "Plan de control PC-TC-01",
            ]
        ),
        encoding="utf-8",
    )

    result = run_inbox_pipeline(root=root, inbox=inbox, out_dir=tmp_path / "run", review_forms=("B90",))

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    docx = manifest["docx_generation"][0]
    assert result.status == "success"
    assert docx["status"] == "filled"
    assert {
        "tco.name",
        "tco.permission_date",
        "tco.instructions",
        "car.mark",
        "car.design_spec",
        "stub_sill.type",
        "aar.form_4_2.number",
        "materials.stub_sill.spec",
        "pitp.name",
        "pitp.id",
        "stub_sill.procedure.id",
    }.issubset(set(docx["patched_fields"]))
    filled_doc = Document(str(result.filled_docx_path))
    assert "MANTENIMIENTO Y MODIFICACION" in filled_doc.tables[0].rows[4].cells[5].text


def test_inbox_pipeline_local_rejects_unknown_review_form(tmp_path: Path) -> None:
    root = _repo_root()
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    (inbox / "evidence.txt").write_text("local evidence", encoding="utf-8")
    with pytest.raises(ValueError, match="Unknown review form"):
        run_inbox_pipeline(root=root, inbox=inbox, out_dir=tmp_path / "run", review_forms=("B24_RL1",))


def test_inbox_pipeline_missing_pdf_folder_content_fails_clearly(tmp_path: Path) -> None:
    root = _repo_root()
    inbox = tmp_path / "empty_inbox"
    inbox.mkdir()
    with pytest.raises(FileNotFoundError, match="No supported local evidence files found"):
        run_inbox_pipeline(root=root, inbox=inbox, out_dir=tmp_path / "run")


def test_pdf_inbox_ignores_tracked_smoke_evidence_txt(tmp_path: Path) -> None:
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    pdf = inbox / "real.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")
    (inbox / "evidence.txt").write_text(
        "Cover Page Facility: Smoke Fixture\nB24 RL2 Date: 2099-01-01\n",
        encoding="utf-8",
    )
    (inbox / "evidence_sample.txt").write_text("sample only", encoding="utf-8")

    assert [p.name for p in supported_evidence_files(inbox)] == [pdf.name]


def test_docupipe_live_mode_missing_credentials_fails(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("B2_DOCUPIPE_STUB", "0")
    monkeypatch.delenv("DOCUPIPE_API_KEY", raising=False)
    monkeypatch.delenv("DOCUPIPE_API_URL", raising=False)
    pdf = tmp_path / "input.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")
    with pytest.raises(DocuPipeConfigError, match="DOCUPIPE_API_KEY"):
        process_pdf(pdf)
