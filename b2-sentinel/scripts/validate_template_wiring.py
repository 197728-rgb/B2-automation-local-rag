"""Validate that every DOCX template is wired.

This is a structural wiring check, not a regulatory evidence-completion check.
It verifies:
- template exists
- map exists
- manifest exists
- N/A policy exists
- map form_id/version load through SENTINEL's approval-map guard
- coordinates are unique and within the DOCX table structure
"""
from __future__ import annotations

import json
import sys
import zipfile
from pathlib import Path
from typing import Any

from lxml import etree

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from b2_sentinel.layer1_form_brain.write_authority import load_exact_approval_map  # noqa: E402

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def _grid_span(tc: Any) -> int:
    node = tc.find(f".//{W}gridSpan")
    if node is None:
        return 1
    try:
        return max(1, int(node.get(f"{W}val") or "1"))
    except ValueError:
        return 1


def _table_shapes(docx: Path) -> list[list[set[int]]]:
    with zipfile.ZipFile(docx) as zf:
        xml = zf.read("word/document.xml")
    root = etree.fromstring(xml)
    shapes: list[list[set[int]]] = []
    for tbl in root.iter(f"{W}tbl"):
        rows: list[set[int]] = []
        for tr in tbl.iter(f"{W}tr"):
            cols: set[int] = set()
            col = 0
            for tc in tr.iter(f"{W}tc"):
                span = _grid_span(tc)
                for c in range(col, col + span):
                    cols.add(c)
                col += span
            rows.append(cols)
        shapes.append(rows)
    return shapes


def main() -> int:
    rows = []
    ok = True
    for docx in sorted((ROOT / "templates").glob("*.docx")):
        fid = docx.stem
        map_path = ROOT / "schemas" / "maps" / f"{fid}.json"
        manifest_path = ROOT / "schemas" / "templates" / f"{fid}.json"
        na_path = ROOT / "schemas" / "na_policy" / f"{fid}.json"
        status = "OK"
        errors: list[str] = []

        for label, path in [("map", map_path), ("manifest", manifest_path), ("na_policy", na_path)]:
            if not path.exists():
                errors.append(f"missing {label}")

        if not errors:
            try:
                amap = load_exact_approval_map(fid)
                shapes = _table_shapes(docx)
                seen = set()
                for field_id, field in amap.fields.items():
                    coord = (field.table_index, field.row, field.col)
                    if coord in seen:
                        errors.append(f"duplicate coord {coord}")
                    seen.add(coord)
                    if field.table_index >= len(shapes):
                        errors.append(f"{field_id}: table_index out of range")
                    elif field.row >= len(shapes[field.table_index]):
                        errors.append(f"{field_id}: row out of range")
                    elif field.col not in shapes[field.table_index][field.row]:
                        errors.append(f"{field_id}: col out of range")
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{type(exc).__name__}: {exc}")

        if errors:
            ok = False
            status = "FAIL"
        rows.append({"form_id": fid, "status": status, "errors": errors})

    report = {
        "template_count": len(rows),
        "passed": sum(1 for r in rows if r["status"] == "OK"),
        "failed": sum(1 for r in rows if r["status"] != "OK"),
        "rows": rows,
    }
    out = ROOT / "schemas" / "ALL_TEMPLATE_WIRING_VALIDATION.json"
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
