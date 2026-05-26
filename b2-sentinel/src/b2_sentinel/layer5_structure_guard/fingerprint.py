"""Structure fingerprint - read DOCX zip and capture structural shape."""
from __future__ import annotations

import zipfile
from pathlib import Path

from lxml import etree

from ..core.models import StructureFingerprint
from ..layer4_controlled_writer.ooxml_writer import W


def fingerprint_docx(path: Path) -> StructureFingerprint:
    if not path.exists():
        raise FileNotFoundError(path)

    with zipfile.ZipFile(path) as zf:
        try:
            doc = zf.read("word/document.xml")
        except KeyError:
            return _empty_fingerprint(xml_valid=False)
        rel_count = sum(1 for n in zf.namelist() if n.startswith("word/_rels/"))

    try:
        root = etree.fromstring(doc)
        xml_valid = True
    except etree.XMLSyntaxError:
        return _empty_fingerprint(xml_valid=False)

    body = root.find(f"{W}body")
    if body is None:
        return _empty_fingerprint(xml_valid=xml_valid)

    tables = list(body.iter(f"{W}tbl"))
    rows_per_table: list[int] = []
    cells_per_row: list[list[int]] = []
    for tbl in tables:
        rows = list(tbl.iter(f"{W}tr"))
        rows_per_table.append(len(rows))
        cells_per_row.append([len(list(r.iter(f"{W}tc"))) for r in rows])

    paragraph_count = sum(1 for _ in body.iter(f"{W}p"))
    sdt_count = sum(1 for _ in body.iter(f"{W}sdt"))

    return StructureFingerprint(
        table_count=len(tables),
        rows_per_table=rows_per_table,
        cells_per_row=cells_per_row,
        paragraph_count=paragraph_count,
        content_control_count=sdt_count,
        relationships_count=rel_count,
        xml_valid=xml_valid,
    )


def _empty_fingerprint(xml_valid: bool) -> StructureFingerprint:
    return StructureFingerprint(
        table_count=0,
        rows_per_table=[],
        cells_per_row=[],
        paragraph_count=0,
        content_control_count=0,
        relationships_count=0,
        xml_valid=xml_valid,
    )
