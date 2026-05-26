"""Tests for Layer 5: Structure Guard."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from b2_sentinel.core.models import StructureFingerprint, StructureGuardReport


def _compare(form_id: str, blank: StructureFingerprint, filled: StructureFingerprint) -> StructureGuardReport:
    """Inline compare logic matching guard.py's algorithm for unit testing."""
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


class TestStructureGuard:
    def _make_fingerprint(self, **overrides) -> StructureFingerprint:
        defaults = dict(
            table_count=3,
            rows_per_table=[5, 10, 2],
            cells_per_row=[[4, 4, 4, 4, 4], [3] * 10, [2, 2]],
            paragraph_count=50,
            content_control_count=12,
            relationships_count=8,
            xml_valid=True,
        )
        defaults.update(overrides)
        return StructureFingerprint(**defaults)

    def test_identical_fingerprints_pass(self):
        blank = self._make_fingerprint()
        filled = self._make_fingerprint()
        report = _compare("B89", blank, filled)
        assert report.structure_guard_passed is True
        assert report.tables_added == 0
        assert report.tables_removed == 0

    def test_added_table_fails(self):
        blank = self._make_fingerprint(table_count=3)
        filled = self._make_fingerprint(
            table_count=4,
            rows_per_table=[5, 10, 2, 1],
            cells_per_row=[[4, 4, 4, 4, 4], [3] * 10, [2, 2], [1]],
        )
        report = _compare("B89", blank, filled)
        assert report.structure_guard_passed is False
        assert report.tables_added == 1

    def test_removed_rows_fails(self):
        blank = self._make_fingerprint(table_count=3, rows_per_table=[5, 10, 2])
        filled = self._make_fingerprint(table_count=3, rows_per_table=[5, 8, 2])
        report = _compare("B89", blank, filled)
        assert report.structure_guard_passed is False
        assert report.rows_removed == 2

    def test_invalid_xml_fails(self):
        blank = self._make_fingerprint()
        filled = self._make_fingerprint(xml_valid=False)
        report = _compare("B89", blank, filled)
        assert report.structure_guard_passed is False
