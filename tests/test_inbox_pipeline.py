"""Inbox pipeline regression tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from docx import Document

from b2_automation.docupipe_client import DocuPipeConfigError, process_pdf
from b2_automation.inbox_pipeline import run_inbox_pipeline
from b2_automation.ooxml_writer import PatchOutcome
from b2_automation.local_extraction import DEFAULT_REVIEW_FORMS


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _doc_text(path: Path) -> str:
    doc = Document(path)
    parts: list[str] = [p.text for p in doc.paragraphs]
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                parts.append(cell.text)
    return "\n".join(parts)


def test_inbox_pipeline_local_default_generates_all_form_packets(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
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

    def _blocked_docupipe(_pdf: Path):
        raise AssertionError("DocuPipe must not be called by default")

    monkeypatch.setattr("b2_automation.inbox_pipeline.process_pdf", _blocked_docupipe)

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
        assert run_manifest_data.get("structure_guard_failed_forms") == []
    else:
        assert result.filled_docx_path is None
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


@pytest.mark.legacy_rl1
def test_inbox_pipeline_legacy_docupipe_stub_generates_traceable_outputs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = _repo_root()
    template = root / "templates" / "B24_RL1.docx"
    if not template.is_file():
        pytest.skip(f"missing template: {template}")

    inbox = tmp_path / "inbox"
    inbox.mkdir()
    (inbox / "packet_one.pdf").write_bytes(b"%PDF-1.4\n% fake test pdf\n")
    (inbox / "packet_two.pdf").write_bytes(b"%PDF-1.4\n% fake test pdf\n")

    monkeypatch.setenv("B2_DOCUPIPE_STUB", "1")
    monkeypatch.setenv("B2_DOCUPIPE_FIXTURE", str(root / "samples" / "docupipe" / "realistic_b24_response.json"))

    result = run_inbox_pipeline(root=root, inbox=inbox, out_dir=tmp_path / "run", legacy_docupipe=True)

    assert result.status == "success"
    assert result.manifest_path.is_file()
    assert result.review_json_path.is_file()
    assert result.review_md_path.is_file()
    assert result.filled_docx_path is not None and result.filled_docx_path.is_file()
    assert (tmp_path / "run" / "structure_guard_report.json").is_file()

    raw_files = sorted((tmp_path / "run" / "raw").glob("*.docupipe.json"))
    metadata_files = sorted((tmp_path / "run" / "raw").glob("*.metadata.json"))
    assert len(raw_files) == 2
    assert len(metadata_files) == 2

    review = json.loads(result.review_json_path.read_text(encoding="utf-8"))
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert manifest["mode"] == "legacy_docupipe_b24_rl1"
    assert manifest["legacy_adapter_used"] is True
    assert manifest["structure_guard_report"]
    assert len(review["inputs"]) == 2
    assert review["missing_required_fields"] == []
    assert review["low_confidence_fields"] == []
    assert {d["field_id"] for d in review["field_decisions"]} >= {"tco_name", "pitp_id", "car_type"}

    blob = _doc_text(result.filled_docx_path)
    assert "Midwest Tank Rail Inc" in blob
    assert "MC-2024-77" in blob
    assert "DOT-117J100W" in blob
    assert "source:" in blob.lower()
    assert "confidence=" in blob.lower()


def test_inbox_pipeline_local_rejects_b24_rl1_review_forms(tmp_path: Path) -> None:
    root = _repo_root()
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    (inbox / "evidence.txt").write_text("local evidence", encoding="utf-8")
    with pytest.raises(ValueError, match="legacy/sample-only"):
        run_inbox_pipeline(root=root, inbox=inbox, out_dir=tmp_path / "run", review_forms=("B24_RL1",))


def test_default_local_inbox_does_not_load_b24_rl1_manifest(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = _repo_root()
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    (inbox / "packet_one.txt").write_text("Cover Page Facility: Midwest\nB24 RL2 evidence\n", encoding="utf-8")

    def _load_manifest_forbidden(_path: object) -> dict:
        raise AssertionError("load_manifest must not be used on the default local inbox path")

    monkeypatch.setattr("b2_automation.inbox_pipeline.load_manifest", _load_manifest_forbidden)

    def _blocked_docupipe(_pdf: Path):
        raise AssertionError("DocuPipe must not be called by default local inbox")

    monkeypatch.setattr("b2_automation.inbox_pipeline.process_pdf", _blocked_docupipe)
    run_inbox_pipeline(root=root, inbox=inbox, out_dir=tmp_path / "run")


def test_inbox_pipeline_missing_pdf_folder_content_fails_clearly(tmp_path: Path) -> None:
    root = _repo_root()
    inbox = tmp_path / "empty_inbox"
    inbox.mkdir()
    with pytest.raises(FileNotFoundError, match="No supported local evidence files found"):
        run_inbox_pipeline(root=root, inbox=inbox, out_dir=tmp_path / "run")


def test_docupipe_live_mode_missing_credentials_fails(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("B2_DOCUPIPE_STUB", "0")
    monkeypatch.delenv("DOCUPIPE_API_KEY", raising=False)
    monkeypatch.delenv("DOCUPIPE_API_URL", raising=False)
    pdf = tmp_path / "input.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")
    with pytest.raises(DocuPipeConfigError, match="DOCUPIPE_API_KEY"):
        process_pdf(pdf)

@pytest.mark.legacy_rl1
def test_inbox_pipeline_uses_selected_confidence_for_low_confidence_flags(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = _repo_root()
    template = root / "templates" / "B24_RL1.docx"
    if not template.is_file():
        pytest.skip(f"missing template: {template}")

    inbox = tmp_path / "inbox"
    inbox.mkdir()
    low_pdf = inbox / "packet_low.pdf"
    high_pdf = inbox / "packet_high.pdf"
    low_pdf.write_bytes(b"%PDF-1.4\n")
    high_pdf.write_bytes(b"%PDF-1.4\n")

    def _fake_process_pdf(pdf: Path):
        confidence = 0.55 if pdf.name == low_pdf.name else 0.98
        return {
            "result": {
                "field_extractions": [
                    {
                        "field_key": "tco_name",
                        "value": "Midwest Tank Rail Inc",
                        "confidence": confidence,
                        "provenance": [{"page_index": 0}],
                    },
                    {
                        "field_key": "pitp_id",
                        "value": "MC-2024-77",
                        "confidence": 0.99,
                        "provenance": [{"page_index": 0}],
                    },
                    {
                        "field_key": "car_type",
                        "value": "DOT-117J100W",
                        "confidence": 0.99,
                        "provenance": [{"page_index": 0}],
                    },
                ]
            }
        }

    monkeypatch.setattr("b2_automation.inbox_pipeline.process_pdf", _fake_process_pdf)

    result = run_inbox_pipeline(root=root, inbox=inbox, out_dir=tmp_path / "run", legacy_docupipe=True)

    review = json.loads(result.review_json_path.read_text(encoding="utf-8"))
    assert review["low_confidence_fields"] == []


@pytest.mark.legacy_rl1
def test_inbox_pipeline_required_field_from_manifest_enforced(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = _repo_root()
    template = root / "templates" / "B24_RL1.docx"
    if not template.is_file():
        pytest.skip(f"missing template: {template}")

    inbox = tmp_path / "inbox"
    inbox.mkdir()
    (inbox / "packet_one.pdf").write_bytes(b"%PDF-1.4\n")

    def _fake_process_pdf(_pdf: Path):
        return {
            "result": {
                "field_extractions": [
                    {"field_key": "tco_name", "value": "Midwest Tank Rail Inc", "confidence": 0.99, "provenance": [{"page_index": 0}]},
                    {"field_key": "pitp_id", "value": "MC-2024-77", "confidence": 0.99, "provenance": [{"page_index": 0}]},
                    # car_type intentionally omitted to ensure required manifest fallback is enforced
                ]
            }
        }

    monkeypatch.setattr("b2_automation.inbox_pipeline.process_pdf", _fake_process_pdf)

    result = run_inbox_pipeline(root=root, inbox=inbox, out_dir=tmp_path / "run", legacy_docupipe=True)
    review = json.loads(result.review_json_path.read_text(encoding="utf-8"))
    run_manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))

    assert result.status == "review_required"
    assert "car_type" in review["missing_required_fields"]
    assert review["cell_inventory_summary"]["blank_required_MISSING"] >= 1

    total_from_summary = sum(int(v) for v in review["cell_inventory_summary"].values())
    assert total_from_summary == len(review["cell_inventory_report"])
    assert "car_type" in run_manifest["missing_required_fields"]


def test_legacy_pipeline_skips_docx_fill_without_exact_approval_map(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = _repo_root()
    map_path = root / "schemas" / "maps" / "B24_RL1.approval_map.json"
    if not map_path.is_file():
        pytest.skip(f"missing map: {map_path}")
    backup = root / "schemas" / "maps" / "B24_RL1.approval_map.json.bak"
    map_path.rename(backup)
    try:
        inbox = tmp_path / "inbox"
        inbox.mkdir()
        (inbox / "packet_one.pdf").write_bytes(b"%PDF-1.4\n")
        monkeypatch.setenv("B2_DOCUPIPE_STUB", "1")
        monkeypatch.setenv("B2_DOCUPIPE_FIXTURE", str(root / "samples" / "docupipe" / "realistic_b24_response.json"))
        result = run_inbox_pipeline(root=root, inbox=inbox, out_dir=tmp_path / "run", legacy_docupipe=True)
        review = json.loads(result.review_json_path.read_text(encoding="utf-8"))
        assert result.status == "review_required"
        assert review["filled_docx"] is None
    finally:
        backup.rename(map_path)


def test_legacy_pipeline_discards_docx_when_structure_guard_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = _repo_root()
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    (inbox / "packet_one.pdf").write_bytes(b"%PDF-1.4\n")
    monkeypatch.setenv("B2_DOCUPIPE_STUB", "1")
    monkeypatch.setenv("B2_DOCUPIPE_FIXTURE", str(root / "samples" / "docupipe" / "realistic_b24_response.json"))

    def _fake_patch(*args, **kwargs):
        output = Path(kwargs.get("output_path") or args[3])
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(b"fake")
        guard = Path(kwargs["structure_guard_report_path"])
        guard.write_text('{"pass": false, "errors": ["forced"]}', encoding="utf-8")
        return PatchOutcome(output, guard, False, tuple(), ("forced",))

    monkeypatch.setattr("b2_automation.inbox_pipeline.patch_docx_cells", _fake_patch)
    result = run_inbox_pipeline(root=root, inbox=inbox, out_dir=tmp_path / "run", legacy_docupipe=True)
    assert result.status == "review_required"
    assert result.filled_docx_path is None
    assert not (tmp_path / "run" / "filled" / "B24_RL1_filled.docx").exists()
