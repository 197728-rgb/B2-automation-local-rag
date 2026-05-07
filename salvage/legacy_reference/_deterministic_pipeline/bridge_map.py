"""
bridge_map.py — Deterministic key-to-location mapping for B2 DOCX forms.

Each entry resolves a canonical key to an exact document, table, row, and
column target with insertion rules. Does NOT extract files or write to Word.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Literal

import docx


@dataclass
class CellTarget:
    table_anchor: str
    table_index_hint: int | None = None
    row_anchor_col: int | None = None
    row_anchor_text: str | None = None
    row_anchor_regex: str | None = None
    row_index_exact: int | None = None
    target_col: int = 1
    write_mode: Literal["replace_run_text", "replace_paragraph_text", "replace_cell_text"] = "replace_run_text"
    allow_insert_row: bool = False
    must_preserve_row_count: bool = True
    skip_if_ambiguous: bool = True
    ambiguous_pick: int | None = None  # pick Nth match (0-based) when ambiguous


def _find_table(doc: docx.Document, anchor: str, index_hint: int | None = None) -> tuple[int, object] | None:
    """Find a table whose first-row text contains the anchor string."""
    matches = []
    for ti, table in enumerate(doc.tables):
        header_text = " ".join(c.text for c in table.rows[0].cells).lower()
        if anchor.lower() in header_text:
            matches.append((ti, table))
    if not matches:
        return None
    if index_hint is not None and index_hint < len(matches):
        return matches[index_hint]
    if len(matches) == 1:
        return matches[0]
    return None


def _find_row(table, anchor_col: int, anchor_text: str | None, anchor_regex: str | None) -> list[tuple[int, object]]:
    """Find rows where cell at anchor_col matches the anchor text/regex."""
    hits = []
    for ri, row in enumerate(table.rows):
        if anchor_col >= len(row.cells):
            continue
        cell_text = row.cells[anchor_col].text.strip()
        if anchor_text and anchor_text.lower() in cell_text.lower():
            hits.append((ri, row))
        elif anchor_regex and re.search(anchor_regex, cell_text, re.IGNORECASE):
            hits.append((ri, row))
    return hits


def resolve_targets(doc: docx.Document, mapping: list[dict]) -> list[dict]:
    """
    Resolve a list of mapping entries against a loaded DOCX.

    Each entry in `mapping` must have:
      - canonical_key, display_value
      - target: a CellTarget (or dict with CellTarget fields)

    Returns list of resolved targets with table_index, row_index, col_index,
    old_value, cell reference, and status.
    """
    results = []
    for entry in mapping:
        t = entry["target"]
        if isinstance(t, dict):
            t = CellTarget(**t)

        found_table = _find_table(doc, t.table_anchor, t.table_index_hint)
        if not found_table:
            results.append({**entry, "status": "table_not_found", "table_anchor": t.table_anchor})
            continue

        ti, table = found_table

        if t.row_index_exact is not None:
            if t.row_index_exact < len(table.rows):
                rows = [(t.row_index_exact, table.rows[t.row_index_exact])]
            else:
                rows = []
        elif t.row_anchor_text or t.row_anchor_regex:
            rows = _find_row(table, t.row_anchor_col or 0, t.row_anchor_text, t.row_anchor_regex)
        else:
            rows = [(0, table.rows[0])]

        if not rows:
            results.append({
                **entry, "status": "row_not_found",
                "table_index": ti, "table_anchor": t.table_anchor,
            })
            continue

        if len(rows) > 1:
            if t.ambiguous_pick is not None and t.ambiguous_pick < len(rows):
                rows = [rows[t.ambiguous_pick]]
            elif t.skip_if_ambiguous:
                results.append({
                    **entry, "status": "ambiguous_row",
                    "table_index": ti, "matches": len(rows),
                })
                continue

        ri, row = rows[0]
        if t.target_col >= len(row.cells):
            results.append({
                **entry, "status": "col_out_of_range",
                "table_index": ti, "row_index": ri, "target_col": t.target_col,
            })
            continue

        cell = row.cells[t.target_col]
        old_value = cell.text.strip()

        results.append({
            **entry,
            "status": "resolved",
            "table_index": ti,
            "row_index": ri,
            "col_index": t.target_col,
            "old_value": old_value,
            "cell": cell,
            "write_mode": t.write_mode,
        })

    return results
