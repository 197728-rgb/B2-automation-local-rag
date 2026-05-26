"""Tests for defensive audit validation (DLGA / Exhibit B-2 stability requirements)."""

from __future__ import annotations

from pathlib import Path

import pytest

from b2_automation.audit_text_safety import normalize_cell_text, strip_hidden_unicode
from b2_automation.audit_validation import validate_audit_docx, verify_safe_text_patch_only, write_validation_summary
from b2_automation.table_fingerprint import _digest_header_rows, infer_form_id_from_filename


def test_strip_hidden_unicode_and_zwsp() -> None:
    raw = "UTBC\u200b\u200c\u00ad250086\ufffd"
    cleaned, notes = strip_hidden_unicode(raw)
    assert "\u200b" not in cleaned
    assert "\ufffd" not in cleaned
    assert "250086" in cleaned
    assert notes


def test_normalize_cell_text_preserves_line_breaks() -> None:
    raw = "Black Paint-\n  6/10/2025"
    norm = normalize_cell_text(raw, preserve_line_breaks=True)
    assert "\n" in norm.text
    assert "6/10/2025" in norm.text


def test_infer_form_id_from_filename() -> None:
    assert infer_form_id_from_filename(Path("DLGA-B89.docx")) == "B89"
    assert infer_form_id_from_filename(Path("READY_DLGA-COVER PAGE.docx")) == "Cover_Page"


def test_digest_header_rows_stable() -> None:
    rows = (("Personnel ID", "Function Performed"), ("M. Marquez", "VT"))
    assert _digest_header_rows(rows) == _digest_header_rows(rows)


def test_validate_audit_docx_on_templates_extracted_cover() -> None:
    cover = Path(r"C:\Projects\templates_extracted\templates\FILLED_Cover Sheet..docx")
    if not cover.is_file():
        pytest.skip("FILLED Cover Sheet not present")
    report = validate_audit_docx(cover, form_id="Cover_Page", project_root=cover.parent)
    assert report.docx_path
    assert report.visual_export_checks
    out_json = cover.with_suffix(".test_validation.json")
    out_md = cover.with_suffix(".test_validation.md")
    try:
        write_validation_summary(report, json_path=out_json, md_path=out_md)
        assert out_json.is_file()
        assert out_md.is_file()
        assert "Audit validation summary" in out_md.read_text(encoding="utf-8")
    finally:
        out_json.unlink(missing_ok=True)
        out_md.unlink(missing_ok=True)


def test_safe_text_patch_only_identical_structure() -> None:
    cover = Path(r"C:\Projects\templates_extracted\templates\FILLED_Cover Sheet..docx")
    if not cover.is_file():
        pytest.skip("FILLED Cover Sheet not present")
    guard = verify_safe_text_patch_only(cover, cover)
    assert guard["pass"] is True
    assert guard.get("safe_text_patch_only") is True
