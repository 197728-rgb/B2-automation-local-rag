"""Raw OOXML cell patcher.

Walks word/document.xml with lxml, locates target cells by visual coordinate
(table_index, row, col with gridSpan accounting), unwraps any wrapping
content controls (w:sdt) so written text is visible in Word, and replaces
cell text. Two write modes:
    - replace: clear existing w:t nodes, write new value into first
    - append_after_label: keep existing label text, append ': value'

Lessons borrowed from the existing local-rag ooxml_writer:
  * gridSpan handling (visual columns vs physical cells)
  * w:sdt unwrap so values are not hidden inside content controls
  * structure-preserving rewrites (no add/remove tables/rows/cells)
"""
from __future__ import annotations

import shutil
import zipfile
from pathlib import Path

from lxml import etree

from ..core.models import PatchInstruction, PatchPlan

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
W = f"{{{W_NS}}}"
NSMAP = {"w": W_NS}


class WriterError(Exception):
    pass


def patch_docx(template: Path, out_path: Path, plan: PatchPlan) -> dict[str, list[str]]:
    """Apply a PatchPlan to a copy of the template, write to out_path.

    Returns a per-field result mapping for traceability.
    """
    if not template.exists():
        raise WriterError(f"Template not found: {template}")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(template, out_path)

    # Read document.xml
    with zipfile.ZipFile(out_path) as zf:
        try:
            doc_bytes = zf.read("word/document.xml")
        except KeyError:
            raise WriterError("word/document.xml missing from template")

    parser = etree.XMLParser(remove_blank_text=False)
    root = etree.fromstring(doc_bytes, parser=parser)

    body = root.find(f"{W}body")
    if body is None:
        raise WriterError("document body missing")

    tables = list(body.iter(f"{W}tbl"))

    results: dict[str, list[str]] = {"applied": [], "skipped": [], "errors": []}

    instructions = list(plan.writes) + list(plan.n_a_inserts)
    for inst in instructions:
        if not inst.authorized:
            results["skipped"].append(f"{inst.field_id}: not authorized")
            continue
        try:
            ok = _apply_to_cell(tables, inst)
            if ok:
                results["applied"].append(inst.field_id)
            else:
                results["skipped"].append(f"{inst.field_id}: cell not found")
        except Exception as exc:  # noqa: BLE001
            results["errors"].append(f"{inst.field_id}: {exc}")

    # Write back
    new_bytes = etree.tostring(
        root, xml_declaration=True, encoding="UTF-8", standalone=True,
    )
    _replace_zip_member(out_path, "word/document.xml", new_bytes)
    return results


def _apply_to_cell(tables: list[etree._Element], inst: PatchInstruction) -> bool:
    if inst.table_index >= len(tables):
        return False
    table = tables[inst.table_index]
    rows = list(table.iter(f"{W}tr"))
    if inst.row >= len(rows):
        return False
    row = rows[inst.row]
    target_cell = _cell_at_visual_col(row, inst.col)
    if target_cell is None:
        return False

    _unwrap_sdt(target_cell)

    if inst.write_mode == "append_after_label":
        return _append_after_label(target_cell, inst.value)
    return _replace_cell_text(target_cell, inst.value)


def _cell_at_visual_col(row: etree._Element, visual_col: int) -> etree._Element | None:
    """Return the w:tc whose visual span covers `visual_col`."""
    cur = 0
    for tc in row.findall(f"{W}tc"):
        span = _grid_span(tc)
        if cur <= visual_col < cur + span:
            return tc
        cur += span
    return None


def _grid_span(tc: etree._Element) -> int:
    tcPr = tc.find(f"{W}tcPr")
    if tcPr is not None:
        gs = tcPr.find(f"{W}gridSpan")
        if gs is not None:
            try:
                return int(gs.get(f"{W}val", "1"))
            except (TypeError, ValueError):
                return 1
    return 1


def _unwrap_sdt(cell: etree._Element) -> None:
    """Replace each w:sdt inside the cell with its w:sdtContent children."""
    for sdt in list(cell.iter(f"{W}sdt")):
        content = sdt.find(f"{W}sdtContent")
        if content is None:
            continue
        parent = sdt.getparent()
        if parent is None:
            continue
        idx = list(parent).index(sdt)
        for i, child in enumerate(list(content)):
            parent.insert(idx + i, child)
        parent.remove(sdt)


def _replace_cell_text(cell: etree._Element, value: str) -> bool:
    """Clear existing w:t nodes; write `value` into the first usable run."""
    paragraphs = cell.findall(f"{W}p")
    if not paragraphs:
        return False

    # Clear all but first paragraph's runs
    for p in paragraphs:
        for t in p.iter(f"{W}t"):
            t.text = ""

    p0 = paragraphs[0]
    runs = p0.findall(f"{W}r")
    if runs:
        ts = runs[0].findall(f"{W}t")
        if ts:
            ts[0].text = value
            for t in ts[1:]:
                t.text = ""
        else:
            t = etree.SubElement(runs[0], f"{W}t")
            t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
            t.text = value
    else:
        r = etree.SubElement(p0, f"{W}r")
        t = etree.SubElement(r, f"{W}t")
        t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
        t.text = value
    return True


def _append_after_label(cell: etree._Element, value: str) -> bool:
    """For label-style cells: keep existing label text, append ': value'."""
    paragraphs = cell.findall(f"{W}p")
    if not paragraphs:
        return False
    p0 = paragraphs[0]
    runs = p0.findall(f"{W}r")
    target_run = runs[-1] if runs else None
    if target_run is None:
        target_run = etree.SubElement(p0, f"{W}r")
    t = etree.SubElement(target_run, f"{W}t")
    t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    t.text = f" {value}"
    return True


def _replace_zip_member(zip_path: Path, member: str, new_bytes: bytes) -> None:
    """Rewrite the zip swapping `member`'s content."""
    tmp = zip_path.with_suffix(zip_path.suffix + ".tmp")
    with zipfile.ZipFile(zip_path, "r") as zin:
        with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
            for item in zin.infolist():
                if item.filename == member:
                    zout.writestr(item, new_bytes)
                else:
                    zout.writestr(item, zin.read(item.filename))
    tmp.replace(zip_path)
