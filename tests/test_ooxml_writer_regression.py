"""Regression coverage for raw OOXML DOCX production writes."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from docx import Document

from b2_automation.b24_normalizer import normalize_docupipe_payload_for_b24_rl1
from b2_automation.b24_pipeline import run_b24_rl1_from_docupipe
from b2_automation.b24_rl1_filler import load_manifest
from b2_automation.ooxml_writer import count_docx_structure, patch_docx_cells
from b2_automation.paths import B24_SHARED_TEMPLATE_DOCX

pytestmark = pytest.mark.legacy_rl1


def _repo() -> Path:
    return Path(__file__).resolve().parents[1]


def _fixture() -> Path:
    return _repo() / "samples" / "docupipe" / "realistic_b24_response.json"


def _doc_text(path: Path) -> str:
    doc = Document(path)
    parts: list[str] = [p.text for p in doc.paragraphs]
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                parts.append(cell.text)
    return "\n".join(parts)


def test_ooxml_patch_preserves_table_cell_structure(tmp_path: Path) -> None:
    root = _repo()
    template = root / "templates" / B24_SHARED_TEMPLATE_DOCX
    if not template.is_file():
        pytest.skip(f"missing template: {template}")
    manifest = load_manifest(root / "schemas" / "templates" / "B24_RL1.json")
    out = tmp_path / "ooxml_filled.docx"
    guard_path = tmp_path / "structure_guard_report.json"

    outcome = patch_docx_cells(
        template,
        manifest,
        {"tco_name": "OOXML TCO", "car_mark": "UTLX 556891"},
        out,
        structure_guard_report_path=guard_path,
    )

    assert outcome.structure_guard_passed is True
    assert guard_path.is_file()
    guard = json.loads(guard_path.read_text(encoding="utf-8"))
    assert guard["pass"] is True
    before = count_docx_structure(template)
    after = count_docx_structure(out)
    for key in ("tables", "rows", "cells", "gridSpan", "vMerge"):
        assert after[key] == before[key]
    assert after["text_nodes"] - before["text_nodes"] == guard["text_nodes_delta_expected"]
    blob = _doc_text(out)
    assert "OOXML TCO" in blob
    assert "UTLX 556891" in blob


def test_b24_production_path_uses_ooxml_flow_with_stable_structure(tmp_path: Path) -> None:
    root = _repo()
    template = root / "templates" / B24_SHARED_TEMPLATE_DOCX
    if not template.is_file():
        pytest.skip(f"missing template: {template}")
    out = tmp_path / "production_b24.docx"

    run_b24_rl1_from_docupipe(_fixture(), root, out)

    guard = json.loads((tmp_path / "structure_guard_report.json").read_text(encoding="utf-8"))
    assert guard["pass"] is True
    before = count_docx_structure(template)
    after = count_docx_structure(out)
    assert after["tables"] == before["tables"]
    assert after["cells"] == before["cells"]
    blob = _doc_text(out)
    assert "Midwest Tank Rail Inc" in blob
    assert "MC-2024-77" in blob
    assert "source" in blob.lower()


def test_ooxml_production_path_uses_normalized_values(tmp_path: Path) -> None:
    root = _repo()
    manifest = load_manifest(root / "schemas" / "templates" / "B24_RL1.json")
    fields = normalize_docupipe_payload_for_b24_rl1(json.loads(_fixture().read_text(encoding="utf-8")))
    out = tmp_path / "normalized_values.docx"
    outcome = patch_docx_cells(root / "templates" / B24_SHARED_TEMPLATE_DOCX, manifest, fields, out)

    assert outcome.structure_guard_passed is True
    blob = _doc_text(out)
    assert "Midwest Tank Rail Inc" in blob
    assert "UTLX 556891" in blob


def test_exact_approval_map_coordinate_mismatch_fails_guard(tmp_path: Path) -> None:
    root = _repo()
    template = root / "templates" / B24_SHARED_TEMPLATE_DOCX
    if not template.is_file():
        pytest.skip(f"missing template: {template}")
    manifest = load_manifest(root / "schemas" / "templates" / "B24_RL1.json")
    approval = {
        "fields": {
            "tco_name": {
                "field_id": "tco_name",
                "table_index": 99,
                "row": 4,
                "col": 0,
                "label": "wrong table index",
            }
        }
    }
    out = tmp_path / "denied.docx"
    guard_path = tmp_path / "structure_guard_report.json"
    outcome = patch_docx_cells(
        template,
        manifest,
        {"tco_name": "Should Not Hand Off"},
        out,
        approval_map=approval,
        structure_guard_report_path=guard_path,
    )
    assert outcome.structure_guard_passed is False
    assert not out.is_file()
    guard = json.loads(guard_path.read_text(encoding="utf-8"))
    assert guard["pass"] is False
