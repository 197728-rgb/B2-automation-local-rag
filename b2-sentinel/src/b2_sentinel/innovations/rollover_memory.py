"""Innovation 2 - Rollover Memory.

Compares old B-2 vs new B-2 and classifies each field's rollover eligibility:
    safe_to_roll | roll_with_date_check | requires_new_evidence | do_not_roll | obsolete | conflict.

Heuristics borrowed conceptually from TOOLS/output/dlga_rollover_smart.py
(date-aware fields require date_check; personnel changes => do_not_roll;
identical static facility values => safe_to_roll).
"""
from __future__ import annotations

import re
import zipfile
from pathlib import Path
from typing import Any

from lxml import etree

from ..core.models import (
    EvidenceLedger,
    ObligationGraph,
    RolloverEntry,
)
from ..core.status import RolloverDecision
from ..layer4_controlled_writer.ooxml_writer import W


_DATE_FIELDS_KEYWORDS = ("date", "permission", "calibration")
_PERSONNEL_FIELDS_KEYWORDS = ("welder", "auditor", "approved_by", "name")


def _read_visible_cells(path: Path) -> dict[tuple[int, int, int], str]:
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
                tcPr = tc.find(f"{W}tcPr")
                span = 1
                if tcPr is not None:
                    gs = tcPr.find(f"{W}gridSpan")
                    if gs is not None:
                        try:
                            span = int(gs.get(f"{W}val", "1"))
                        except (TypeError, ValueError):
                            span = 1
                text_parts = []
                for p in tc.findall(f"{W}p"):
                    text_parts.append("".join(t.text or "" for t in p.iter(f"{W}t")))
                text = "\n".join(text_parts).strip()
                for delta in range(span):
                    out[(tbl_idx, row_idx, visual_col + delta)] = text
                visual_col += span
    return out


def evaluate_rollover(
    *,
    graph: ObligationGraph,
    new_ledger: EvidenceLedger,
    prior_filled_path: Path | None,
) -> list[RolloverEntry]:
    if not prior_filled_path or not prior_filled_path.exists():
        return []

    prior_cells = _read_visible_cells(prior_filled_path)
    out: list[RolloverEntry] = []
    for fid, node in graph.fields.items():
        if node.never_write:
            continue
        coord = (node.table_index, node.row, node.col)
        old_value = prior_cells.get(coord, "").strip() or None
        ledger_entry = new_ledger.entries.get(fid)
        new_candidate = ledger_entry.candidate_value if ledger_entry else None

        decision, reason = _classify(node, old_value, new_candidate)
        out.append(
            RolloverEntry(
                field_id=fid,
                old_value=old_value,
                new_candidate=new_candidate,
                rollover_decision=decision,
                reason=reason,
            )
        )
    return out


def _classify(node, old_value: str | None, new_candidate: str | None) -> tuple[RolloverDecision, str]:
    fid_lower = node.field_id.lower()
    label_lower = node.label.lower()
    is_date = any(k in fid_lower or k in label_lower for k in _DATE_FIELDS_KEYWORDS)
    is_personnel = any(k in fid_lower or k in label_lower for k in _PERSONNEL_FIELDS_KEYWORDS)

    if old_value is None and new_candidate is None:
        return RolloverDecision.REQUIRES_NEW_EVIDENCE, "no value in either run"
    if old_value is None and new_candidate:
        return RolloverDecision.SAFE_TO_ROLL, "new evidence present, no prior value"
    if old_value and new_candidate is None:
        if is_personnel:
            return RolloverDecision.DO_NOT_ROLL, "personnel field; new evidence required"
        if is_date:
            return RolloverDecision.OBSOLETE, "date field with no new evidence"
        return RolloverDecision.REQUIRES_NEW_EVIDENCE, "prior value present but new evidence missing"

    # Both present
    assert old_value is not None and new_candidate is not None
    if old_value == new_candidate:
        if is_date:
            return RolloverDecision.ROLL_WITH_DATE_CHECK, "date matches; verify period validity"
        return RolloverDecision.SAFE_TO_ROLL, "identical to prior packet"
    if is_personnel:
        return RolloverDecision.DO_NOT_ROLL, "personnel changed in new evidence"
    return RolloverDecision.CONFLICT, "value differs from prior packet"
