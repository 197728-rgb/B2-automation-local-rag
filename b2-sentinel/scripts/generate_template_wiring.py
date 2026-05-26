"""Generate inferred SENTINEL wiring for every DOCX template.

This is intentionally conservative:
- Existing hand-approved maps are not overwritten unless --force is used.
- Generated fields are marked required=false because they are inferred from DOCX
  structure, not regulatory sign-off.
- The generated maps are enough to wire templates into the pipeline, create
  obligation graphs, write authorized cells, and produce audit packets.
- Field-level regulatory completion still requires human/SME review to promote
  specific fields to required=true.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import zipfile
from pathlib import Path
from typing import Any

from lxml import etree

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
W = f"{{{W_NS}}}"

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "templates"
SCHEMAS = ROOT / "schemas"
MAPS = SCHEMAS / "maps"
MANIFESTS = SCHEMAS / "templates"
NA_POLICY = SCHEMAS / "na_policy"


def _text(el: Any) -> str:
    return " ".join("".join(t.text or "" for t in el.iter(f"{W}t")).split())


def _grid_span(tc: Any) -> int:
    node = tc.find(f".//{W}gridSpan")
    if node is None:
        return 1
    try:
        return max(1, int(node.get(f"{W}val") or "1"))
    except ValueError:
        return 1


def _tables(docx: Path) -> list[list[list[dict[str, Any]]]]:
    with zipfile.ZipFile(docx) as zf:
        xml = zf.read("word/document.xml")
    root = etree.fromstring(xml)
    out: list[list[list[dict[str, Any]]]] = []
    for tbl in root.iter(f"{W}tbl"):
        rows: list[list[dict[str, Any]]] = []
        for tr in tbl.iter(f"{W}tr"):
            cells: list[dict[str, Any]] = []
            col = 0
            for tc in tr.iter(f"{W}tc"):
                span = _grid_span(tc)
                cells.append({"col": col, "span": span, "text": _text(tc)})
                col += span
            rows.append(cells)
        out.append(rows)
    return out


def _norm_label(label: str) -> str:
    label = re.sub(r"^[0-9]+[.)]\s*", "", label.strip())
    label = label.replace("#", "number")
    label = re.sub(r"[^A-Za-z0-9]+", "_", label).strip("_").lower()
    label = re.sub(r"_+", "_", label)
    return label[:70] or "field"


def _looks_like_section(text: str) -> bool:
    if not text:
        return False
    if len(text) > 80:
        return True
    letters = re.sub(r"[^A-Za-z]", "", text)
    return bool(letters) and text.upper() == text and len(letters) > 6


def _is_value_cell(text: str) -> bool:
    if not text:
        return True
    return text.strip().lower() in {
        "choose an item.",
        "choose an item",
        "☐ yes",
        "☐ no",
        "yes",
        "no",
        "n/a",
    }


def _cell_at_visual_col(row: list[dict[str, Any]], col: int) -> dict[str, Any] | None:
    for cell in row:
        if cell["col"] <= col < cell["col"] + cell["span"]:
            return cell
    return None


def _unique(fid: str, seen: set[str]) -> str:
    base = fid
    idx = 2
    while fid in seen:
        fid = f"{base}_{idx}"
        idx += 1
    seen.add(fid)
    return fid


def infer_fields(form_id: str, docx: Path) -> dict[str, dict[str, Any]]:
    fields: dict[str, dict[str, Any]] = {}
    seen_ids: set[str] = set()
    seen_coords: set[tuple[int, int, int]] = set()

    for ti, rows in enumerate(_tables(docx)):
        for ri in range(len(rows) - 1):
            label_row = rows[ri]
            value_row = rows[ri + 1]
            non_empty_labels = [c for c in label_row if c["text"]]
            if not non_empty_labels:
                continue
            if len(non_empty_labels) == 1 and _looks_like_section(non_empty_labels[0]["text"]):
                continue

            for label_cell in non_empty_labels:
                label = label_cell["text"]
                if _looks_like_section(label):
                    continue
                value_cell = _cell_at_visual_col(value_row, label_cell["col"])
                if value_cell is None:
                    continue
                if not _is_value_cell(value_cell["text"]):
                    continue
                coord = (ti, ri + 1, value_cell["col"])
                if coord in seen_coords:
                    continue
                seen_coords.add(coord)
                fid = _unique(_norm_label(label), seen_ids)
                fields[fid] = {
                    "field_id": fid,
                    "table_index": ti,
                    "row": ri + 1,
                    "col": value_cell["col"],
                    "required": False,
                    "cell_role": "target",
                    "label": label,
                    "write_mode": "replace",
                    "inferred": True,
                    "inference": "label row followed by blank/dropdown value row",
                }

    # Fallback: expose blank cells with a non-empty left neighbor.
    for ti, rows in enumerate(_tables(docx)):
        for ri, row in enumerate(rows):
            prev_text = ""
            for cell in row:
                text = cell["text"]
                if _is_value_cell(text) and prev_text and not _looks_like_section(prev_text):
                    coord = (ti, ri, cell["col"])
                    if coord not in seen_coords:
                        seen_coords.add(coord)
                        fid = _unique(_norm_label(prev_text), seen_ids)
                        fields[fid] = {
                            "field_id": fid,
                            "table_index": ti,
                            "row": ri,
                            "col": cell["col"],
                            "required": False,
                            "cell_role": "target",
                            "label": prev_text,
                            "write_mode": "replace",
                            "inferred": True,
                            "inference": "blank/dropdown cell after left label",
                        }
                if text:
                    prev_text = text

    return fields


def fingerprint(docx: Path) -> str:
    with zipfile.ZipFile(docx) as zf:
        return hashlib.sha256(zf.read("word/document.xml")).hexdigest()


def write_json(path: Path, payload: dict[str, Any], force: bool) -> bool:
    if path.exists() and not force:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return True


def generate(force: bool = False) -> dict[str, Any]:
    report: dict[str, Any] = {"generated": [], "kept": [], "templates": {}}
    for docx in sorted(TEMPLATES.glob("*.docx")):
        form_id = docx.stem
        fields = infer_fields(form_id, docx)
        manifest = {
            "template": docx.name,
            "form_id": form_id,
            "structure_fingerprint": fingerprint(docx),
            "generated_by": "scripts/generate_template_wiring.py",
            "generation_mode": "inferred_from_docx_tables",
            "review_required": True,
            "cells": list(fields.values()),
        }
        amap = {
            "form_id": form_id,
            "form_version": "2026",
            "manifest_path": f"schemas/templates/{form_id}.json",
            "template_path": f"templates/{docx.name}",
            "generated_by": "scripts/generate_template_wiring.py",
            "generation_mode": "inferred_from_docx_tables",
            "review_required": True,
            "fields": fields,
        }
        na = {
            "form_id": form_id,
            "description": f"No approved N/A exceptions configured for {form_id}.",
            "generated_by": "scripts/generate_template_wiring.py",
            "fields": {},
        }

        changed = [
            write_json(MANIFESTS / f"{form_id}.json", manifest, force),
            write_json(MAPS / f"{form_id}.json", amap, force),
            write_json(NA_POLICY / f"{form_id}.json", na, force),
        ]
        status = "generated_or_updated" if any(changed) else "kept_existing"
        report["templates"][form_id] = {"status": status, "field_count": len(fields)}
        report["generated" if any(changed) else "kept"].append(form_id)
    return report


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="Overwrite existing wiring files.")
    args = ap.parse_args()
    report = generate(force=args.force)
    out = SCHEMAS / "TEMPLATE_WIRING_REPORT.json"
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
