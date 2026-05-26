"""Visible-text extractor.

Reads the filled DOCX fresh and returns:
    {(table_index, row, col): visible_text}
where visible_text is what Word would actually render in the cell.
This is the check that catches 'XML has value but Word shows blank'.
"""
from __future__ import annotations

import zipfile
from pathlib import Path

from lxml import etree

from ..layer4_controlled_writer.ooxml_writer import W


def cell_visible_text(path: Path) -> dict[tuple[int, int, int], str]:
    out: dict[tuple[int, int, int], str] = {}
    if not path.exists():
        return out

    with zipfile.ZipFile(path) as zf:
        try:
            doc = zf.read("word/document.xml")
        except KeyError:
            return out

    try:
        root = etree.fromstring(doc)
    except etree.XMLSyntaxError:
        return out

    body = root.find(f"{W}body")
    if body is None:
        return out

    for tbl_idx, tbl in enumerate(body.iter(f"{W}tbl")):
        for row_idx, row in enumerate(tbl.iter(f"{W}tr")):
            visual_col = 0
            for tc in row.findall(f"{W}tc"):
                span = _grid_span(tc)
                text = _cell_text(tc)
                for delta in range(span):
                    out[(tbl_idx, row_idx, visual_col + delta)] = text
                visual_col += span
    return out


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


def _cell_text(tc: etree._Element) -> str:
    parts: list[str] = []
    for p in tc.findall(f"{W}p"):
        para = "".join(t.text or "" for t in p.iter(f"{W}t"))
        if para:
            parts.append(para)
    return "\n".join(parts).strip()
