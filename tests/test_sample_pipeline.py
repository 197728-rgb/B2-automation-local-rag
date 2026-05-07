"""Regression: sample DocuPipe JSON fixture produces a readable DOCX."""

from __future__ import annotations

from pathlib import Path

from docx import Document

from b2_automation.sample_pipeline import run_sample_pipeline


def _fixture_path() -> Path:
    return Path(__file__).resolve().parents[1] / "samples" / "docupipe" / "minimal_docupipe_response.json"


def test_sample_pipeline_writes_docx(tmp_path: Path) -> None:
    fixture = _fixture_path()
    assert fixture.is_file(), f"missing fixture: {fixture}"
    out = tmp_path / "sample_pipeline_out.docx"
    written = run_sample_pipeline(fixture, out)
    assert written == out.resolve()
    assert out.is_file()
    assert out.stat().st_size > 2_000
    doc = Document(out)
    blob = "\n".join(p.text for p in doc.paragraphs)
    assert "ACME Tank Services" in blob
    assert "qdlhfq5G" in blob
    assert "0.91" in blob or "organization confidence" in blob.lower()
