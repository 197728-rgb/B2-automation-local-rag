"""Controlled manual old->new replacement with audit ledger.

The Ferrari version of manual correction: counts occurrences before,
verifies single-target replacement, and produces a ManualCorrectionEntry.
"""
from __future__ import annotations

import re
import shutil
import zipfile
from pathlib import Path

from lxml import etree

from ..core.models import ManualCorrectionEntry
from .ooxml_writer import W, _replace_zip_member


def manual_replace(
    target_docx: Path,
    *,
    old: str,
    new: str,
    target_form: str,
    expect_occurrences: int = 1,
    risk: str = "low",
) -> ManualCorrectionEntry:
    if not target_docx.exists():
        raise FileNotFoundError(target_docx)

    with zipfile.ZipFile(target_docx) as zf:
        doc = zf.read("word/document.xml")

    parser = etree.XMLParser(remove_blank_text=False)
    root = etree.fromstring(doc, parser=parser)

    # Count visible occurrences across w:t nodes, joining within paragraphs
    para_texts: list[tuple[etree._Element, str]] = []
    for p in root.iter(f"{W}p"):
        ts = list(p.iter(f"{W}t"))
        text = "".join(t.text or "" for t in ts)
        para_texts.append((p, text))

    occurrences_found = sum(t.count(old) for _, t in para_texts)
    if occurrences_found != expect_occurrences:
        return ManualCorrectionEntry(
            old=old, new=new, target_form=target_form,
            occurrences_found=occurrences_found, occurrences_replaced=0,
            risk=_risk(risk), validated=False,
        )

    occurrences_replaced = 0
    for p, joined in para_texts:
        if old not in joined:
            continue
        ts = list(p.iter(f"{W}t"))
        if not ts:
            continue
        # Concentrate text in the first w:t for safety
        new_joined = joined.replace(old, new, 1)
        ts[0].text = new_joined
        for t in ts[1:]:
            t.text = ""
        occurrences_replaced += 1

    new_bytes = etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)
    _replace_zip_member(target_docx, "word/document.xml", new_bytes)

    return ManualCorrectionEntry(
        old=old, new=new, target_form=target_form,
        occurrences_found=occurrences_found,
        occurrences_replaced=occurrences_replaced,
        risk=_risk(risk),
        validated=occurrences_replaced == expect_occurrences,
    )


def _risk(value: str) -> str:
    if value not in ("low", "medium", "high"):
        return "low"
    return value
