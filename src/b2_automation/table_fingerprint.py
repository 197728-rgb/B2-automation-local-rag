"""Deterministic table fingerprinting for Exhibit B-2 forms.

Detects accidental column drift or wrong template/version without modifying
table OOXML geometry.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

from docx import Document
from docx.table import Table

from b2_automation.audit_text_safety import normalize_cell_text


@dataclass(frozen=True)
class TableFingerprint:
    table_index: int
    row_count: int
    header_rows: tuple[tuple[str, ...], ...]
    digest: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "table_index": self.table_index,
            "row_count": self.row_count,
            "header_rows": [list(row) for row in self.header_rows],
            "digest": self.digest,
        }


@dataclass
class FingerprintComparison:
    table_index: int
    status: str  # match | drift | missing_expected | extra_table
    expected_digest: str | None = None
    actual_digest: str | None = None
    expected_headers: list[list[str]] | None = None
    actual_headers: list[list[str]] | None = None
    detail: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "table_index": self.table_index,
            "status": self.status,
            "expected_digest": self.expected_digest,
            "actual_digest": self.actual_digest,
            "expected_headers": self.expected_headers,
            "actual_headers": self.actual_headers,
            "detail": self.detail,
        }


def _row_unique_cells(table: Table, row_idx: int, max_cols: int = 24) -> tuple[str, ...]:
    if row_idx >= len(table.rows):
        return ()
    row = table.rows[row_idx]
    seen: set[int] = set()
    cells: list[str] = []
    for cell in row.cells[:max_cols]:
        tc_id = id(cell._tc)
        if tc_id in seen:
            continue
        seen.add(tc_id)
        norm = normalize_cell_text(cell.text, preserve_line_breaks=False).text
        cells.append(norm)
    return tuple(cells)


def _header_rows_for_table(table: Table, max_header_rows: int = 3) -> tuple[tuple[str, ...], ...]:
    rows: list[tuple[str, ...]] = []
    for ri in range(min(max_header_rows, len(table.rows))):
        row = _row_unique_cells(table, ri)
        if any(cell.strip() for cell in row):
            rows.append(row)
    return tuple(rows)


def _digest_header_rows(header_rows: tuple[tuple[str, ...], ...]) -> str:
    payload = json.dumps(header_rows, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def fingerprint_docx_tables(docx_path: Path, *, max_header_rows: int = 3) -> list[TableFingerprint]:
    doc = Document(docx_path)
    out: list[TableFingerprint] = []
    for ti, table in enumerate(doc.tables):
        headers = _header_rows_for_table(table, max_header_rows=max_header_rows)
        digest = _digest_header_rows(headers)
        out.append(
            TableFingerprint(
                table_index=ti,
                row_count=len(table.rows),
                header_rows=headers,
                digest=digest,
            )
        )
    return out


def load_expected_fingerprints(root: Path, form_id: str) -> dict[int, dict[str, Any]] | None:
    """Load schemas/fingerprints/{form_id}.json if present."""
    path = root / "schemas" / "fingerprints" / f"{form_id}.json"
    if not path.is_file():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    tables = data.get("tables") or {}
    out: dict[int, dict[str, Any]] = {}
    for key, spec in tables.items():
        out[int(key)] = spec
    return out


def compare_fingerprints(
    actual: list[TableFingerprint],
    expected: Mapping[int, Mapping[str, Any]] | None,
    *,
    form_id: str,
) -> list[FingerprintComparison]:
    if not expected:
        return [
            FingerprintComparison(
                table_index=fp.table_index,
                status="missing_expected",
                actual_digest=fp.digest,
                actual_headers=[list(r) for r in fp.header_rows],
                detail=f"No fingerprint schema for form {form_id!r}; table {fp.table_index} not validated",
            )
            for fp in actual
        ]

    results: list[FingerprintComparison] = []
    for fp in actual:
        spec = expected.get(fp.table_index)
        if spec is None:
            results.append(
                FingerprintComparison(
                    table_index=fp.table_index,
                    status="extra_table",
                    actual_digest=fp.digest,
                    actual_headers=[list(r) for r in fp.header_rows],
                    detail="Table index not listed in expected fingerprint schema",
                )
            )
            continue
        exp_digest = str(spec.get("digest") or "")
        exp_headers = spec.get("header_rows") or []
        if exp_digest and fp.digest == exp_digest:
            results.append(
                FingerprintComparison(
                    table_index=fp.table_index,
                    status="match",
                    expected_digest=exp_digest,
                    actual_digest=fp.digest,
                    expected_headers=exp_headers,
                    actual_headers=[list(r) for r in fp.header_rows],
                )
            )
            continue
        # Soft match: compare normalized header token sequences if digest missing
        exp_rows = tuple(tuple(str(c) for c in row) for row in exp_headers)
        if not exp_digest and exp_rows == fp.header_rows:
            results.append(
                FingerprintComparison(
                    table_index=fp.table_index,
                    status="match",
                    actual_digest=fp.digest,
                    expected_headers=exp_headers,
                    actual_headers=[list(r) for r in fp.header_rows],
                    detail="Header sequence match (no digest in schema)",
                )
            )
            continue
        results.append(
            FingerprintComparison(
                table_index=fp.table_index,
                status="drift",
                expected_digest=exp_digest or None,
                actual_digest=fp.digest,
                expected_headers=exp_headers,
                actual_headers=[list(r) for r in fp.header_rows],
                detail="Header sequence or digest differs from expected form/version fingerprint",
            )
        )
    return results


def write_fingerprint_schema(docx_path: Path, form_id: str, out_path: Path) -> Path:
    """Generate fingerprint JSON from a reference template (read-only scan)."""
    fps = fingerprint_docx_tables(docx_path)
    payload = {
        "form_id": form_id,
        "source_template": str(docx_path),
        "tables": {
            str(fp.table_index): {
                "digest": fp.digest,
                "row_count": fp.row_count,
                "header_rows": [list(row) for row in fp.header_rows],
            }
            for fp in fps
        },
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return out_path


def infer_form_id_from_filename(path: Path) -> str:
    name = path.stem.upper()
    for token, form in (
        ("COVER", "Cover_Page"),
        ("B24", "B24_RL2"),
        ("B81", "B81"),
        ("B89", "B89"),
        ("B90", "B90"),
        ("C6R", "C6r"),
        ("C6", "C6r"),
        ("C7", "C7"),
        ("C8", "C8"),
        ("C10", "C10"),
        ("C5", "C5"),
    ):
        if token in name:
            return form
    slug = re.sub(r"[^A-Za-z0-9]+", "_", path.stem).strip("_")
    return slug or "unknown"
