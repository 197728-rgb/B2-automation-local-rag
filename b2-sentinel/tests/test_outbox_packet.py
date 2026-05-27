"""Outbox publication contract tests."""
from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import fitz

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import b2_sentinel.cli as cli_module
from b2_sentinel.core.status import FinalStatus


def _write_marker_pdf(path: Path, marker: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = fitz.open()
    try:
        page = doc.new_page()
        page.insert_text((72, 72), marker)
        doc.save(path)
    finally:
        doc.close()


def _fake_result(form_id: str, run_dir: Path):
    form_dir = run_dir / form_id
    form_dir.mkdir(parents=True, exist_ok=True)
    (form_dir / f"{form_id}_filled.docx").write_bytes(b"fake-docx-for-export")
    return SimpleNamespace(
        form_id=form_id,
        overall_passed=True,
        final_status=FinalStatus.SUCCESS,
        out_dir=form_dir,
    )


def test_complete_packet_merges_cover_page_first(monkeypatch, tmp_path: Path) -> None:
    def fake_export(docx_path: Path, pdf_path: Path) -> Path:
        marker = docx_path.name.removesuffix("_filled.docx")
        _write_marker_pdf(pdf_path, marker)
        return pdf_path

    monkeypatch.setattr(cli_module, "export_docx_to_pdf", fake_export)

    run_dir = tmp_path / "logs" / "run"
    outbox = tmp_path / "outbox"
    selected = ["B89", "Cover_Page", "B90"]
    results = [_fake_result(form_id, run_dir) for form_id in selected]

    errors = cli_module._publish_outbox_pdfs(selected, results, outbox)

    assert errors == {}
    packet = outbox / "B2_COMPLETE_PACKET.pdf"
    assert packet.exists()
    with fitz.open(packet) as doc:
        page_text = [doc.load_page(i).get_text("text") for i in range(doc.page_count)]
    assert page_text == ["Cover_Page\n", "B89\n", "B90\n"]


def test_complete_packet_not_created_when_a_selected_form_fails(monkeypatch, tmp_path: Path) -> None:
    def fake_export(docx_path: Path, pdf_path: Path) -> Path:
        marker = docx_path.name.removesuffix("_filled.docx")
        _write_marker_pdf(pdf_path, marker)
        return pdf_path

    monkeypatch.setattr(cli_module, "export_docx_to_pdf", fake_export)

    run_dir = tmp_path / "logs" / "run"
    outbox = tmp_path / "outbox"
    selected = ["Cover_Page", "B89"]
    cover = _fake_result("Cover_Page", run_dir)
    failed = SimpleNamespace(
        form_id="B89",
        overall_passed=False,
        final_status=FinalStatus.FAILED_LOW_CONFIDENCE_RESOLUTION,
        out_dir=run_dir / "B89",
    )

    errors = cli_module._publish_outbox_pdfs(selected, [cover, failed], outbox)

    assert errors == {}
    assert (outbox / "Cover_Page_filled.pdf").exists()
    assert not (outbox / "B89_filled.pdf").exists()
    assert not (outbox / "B2_COMPLETE_PACKET.pdf").exists()
