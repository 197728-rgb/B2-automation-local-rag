"""Cell-boundary validation for equipment/calibration and merged-cell tables.

Flags when extracted or filled text likely spans adjacent logical columns.
Never modifies DOCX structure.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from docx import Document
from docx.table import Table

from b2_automation.audit_text_safety import (
    count_date_tokens,
    looks_like_equipment_calibration_row,
    normalize_cell_text,
    split_pipe_delimited_values,
)

_DATE_COL_HINT = re.compile(r"\b(date|due|calibration|qualified|expires|expiration|approved)\b", re.I)
_ID_COL_HINT = re.compile(r"\b(id|serial|gauge|equipment|dlga)\b", re.I)


@dataclass(frozen=True)
class CellBoundaryIssue:
    form_location: str
    table_index: int
    row_index: int
    column_index: int
    code: str
    detail: str
    cell_preview: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "form_location": self.form_location,
            "table_index": self.table_index,
            "row_index": self.row_index,
            "column_index": self.column_index,
            "code": self.code,
            "detail": self.detail,
            "cell_preview": self.cell_preview,
        }


def _unique_row_cells(table: Table, row_idx: int) -> list[tuple[int, str]]:
    row = table.rows[row_idx]
    seen: set[int] = set()
    out: list[tuple[int, str]] = []
    for ci, cell in enumerate(row.cells):
        tc_id = id(cell._tc)
        if tc_id in seen:
            continue
        seen.add(tc_id)
        text = normalize_cell_text(cell.text).text
        out.append((ci, text))
    return out


def _header_for_column(table: Table, col_idx: int, search_rows: int = 4) -> str:
    parts: list[str] = []
    for ri in range(min(search_rows, len(table.rows))):
        for ci, text in _unique_row_cells(table, ri):
            if ci == col_idx and text.strip():
                parts.append(text.strip())
    return " | ".join(parts)


def validate_cell_boundaries(docx_path: str | Any, *, form_id: str = "unknown") -> list[CellBoundaryIssue]:
    doc = Document(str(docx_path))
    issues: list[CellBoundaryIssue] = []

    for ti, table in enumerate(doc.tables):
        if len(table.rows) < 2:
            continue
        header_cells = _unique_row_cells(table, 0)
        header_texts = [t for _, t in header_cells]
        is_equipment_table = looks_like_equipment_calibration_row(header_texts)
        # Also scan row 1 for sub-headers common in B-forms
        if not is_equipment_table and len(table.rows) > 1:
            is_equipment_table = looks_like_equipment_calibration_row(
                [t for _, t in _unique_row_cells(table, 1)]
            )

        for ri in range(1, len(table.rows)):
            cells = _unique_row_cells(table, ri)
            if not any(t.strip() for _, t in cells):
                continue

            for ci, text in cells:
                if not text.strip():
                    continue
                loc = f"{form_id}/T{ti}R{ri}C{ci}"
                preview = text[:120]

                # Pipe-delimited spill (common OCR/export artifact)
                pipe_parts = split_pipe_delimited_values(text)
                if len(pipe_parts) >= 2:
                    issues.append(
                        CellBoundaryIssue(
                            form_location=loc,
                            table_index=ti,
                            row_index=ri,
                            column_index=ci,
                            code="pipe_delimited_spill",
                            detail=f"Cell contains {len(pipe_parts)} pipe-delimited segments; may span columns",
                            cell_preview=preview,
                        )
                    )

                col_header = _header_for_column(table, ci)
                date_in_id_col = _ID_COL_HINT.search(col_header) and count_date_tokens(text) >= 2
                id_in_date_col = _DATE_COL_HINT.search(col_header) and re.search(
                    r"\b(?:DLGA|U\d{6,}|152[-\w]+)\b", text, re.I
                )
                if date_in_id_col:
                    issues.append(
                        CellBoundaryIssue(
                            form_location=loc,
                            table_index=ti,
                            row_index=ri,
                            column_index=ci,
                            code="date_in_id_column",
                            detail="Multiple dates in a column labeled like ID/equipment",
                            cell_preview=preview,
                        )
                    )
                if id_in_date_col:
                    issues.append(
                        CellBoundaryIssue(
                            form_location=loc,
                            table_index=ti,
                            row_index=ri,
                            column_index=ci,
                            code="id_in_date_column",
                            detail="Equipment/ID token in a column labeled like date/calibration",
                            cell_preview=preview,
                        )
                    )

                if is_equipment_table and len(text) > 180:
                    issues.append(
                        CellBoundaryIssue(
                            form_location=loc,
                            table_index=ti,
                            row_index=ri,
                            column_index=ci,
                            code="equipment_cell_overflow",
                            detail="Unusually long equipment/calibration cell; check adjacent column spill",
                            cell_preview=preview,
                        )
                    )

            # Duplicate non-empty values across distinct columns in same row (merge visibility artifact)
            values = [(ci, t.strip()) for ci, t in cells if t.strip()]
            seen_vals: dict[str, list[int]] = {}
            for ci, val in values:
                key = val.lower()
                if len(key) < 4:
                    continue
                seen_vals.setdefault(key, []).append(ci)
            for val, cols in seen_vals.items():
                if len(cols) < 2:
                    continue
                # Merged B-form rows often mirror WPS vs Observed with identical short tokens (Fillet, Manual, NA).
                # Flag only when duplication suggests OCR spill or multi-column capture.
                spill_like = (
                    len(cols) >= 3
                    or "|" in val
                    or count_date_tokens(val) >= 2
                    or len(val) > 60
                )
                if not spill_like:
                    continue
                issues.append(
                        CellBoundaryIssue(
                            form_location=f"{form_id}/T{ti}R{ri}",
                            table_index=ti,
                            row_index=ri,
                            column_index=cols[0],
                            code="duplicate_across_columns",
                            detail=f"Identical value repeated in columns {cols} (merged-cell or extraction drift)",
                            cell_preview=val[:120],
                        )
                    )

    return issues
