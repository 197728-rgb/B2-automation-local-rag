"""Structure Guard pass/fail.

Compares blank-template fingerprint vs filled-output fingerprint. Any
unexpected delta in tables/rows/cells/paragraphs counts triggers a
guard FAIL, which means the filled DOCX must be discarded.
"""
from __future__ import annotations

from pathlib import Path

from ..core.models import StructureFingerprint, StructureGuardReport
from .fingerprint import fingerprint_docx


def run_structure_guard(
    *,
    form_id: str,
    blank_path: Path,
    filled_path: Path,
) -> StructureGuardReport:
    blank = fingerprint_docx(blank_path)
    filled = fingerprint_docx(filled_path)

    notes: list[str] = []
    tables_added = max(0, filled.table_count - blank.table_count)
    tables_removed = max(0, blank.table_count - filled.table_count)

    rows_added = 0
    rows_removed = 0
    for i in range(min(len(blank.rows_per_table), len(filled.rows_per_table))):
        diff = filled.rows_per_table[i] - blank.rows_per_table[i]
        if diff > 0:
            rows_added += diff
        else:
            rows_removed += -diff

    cells_added = 0
    cells_removed = 0
    for i in range(min(len(blank.cells_per_row), len(filled.cells_per_row))):
        b_table = blank.cells_per_row[i]
        f_table = filled.cells_per_row[i]
        for j in range(min(len(b_table), len(f_table))):
            diff = f_table[j] - b_table[j]
            if diff > 0:
                cells_added += diff
            else:
                cells_removed += -diff

    if tables_added or tables_removed:
        notes.append(f"table count drift: +{tables_added}/-{tables_removed}")
    if rows_added or rows_removed:
        notes.append(f"row count drift: +{rows_added}/-{rows_removed}")
    if cells_added or cells_removed:
        notes.append(f"cell count drift: +{cells_added}/-{cells_removed}")
    if not filled.xml_valid:
        notes.append("filled document XML is NOT valid")
    if filled.relationships_count != blank.relationships_count:
        notes.append(
            f"relationship count drift: blank={blank.relationships_count} filled={filled.relationships_count}"
        )

    passed = (
        filled.xml_valid
        and tables_added == 0 and tables_removed == 0
        and rows_added == 0 and rows_removed == 0
        and cells_added == 0 and cells_removed == 0
    )

    return StructureGuardReport(
        form_id=form_id,
        blank_fingerprint=blank,
        filled_fingerprint=filled,
        tables_added=tables_added,
        tables_removed=tables_removed,
        rows_added=rows_added,
        rows_removed=rows_removed,
        cells_added=cells_added,
        cells_removed=cells_removed,
        xml_valid=filled.xml_valid,
        structure_guard_passed=passed,
        notes=notes,
    )
