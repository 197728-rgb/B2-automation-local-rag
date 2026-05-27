"""Source-file extractors: PDF, DOCX, JSON, CSV, TXT, MD into SourceChunks.

Each extractor returns an iterable of SourceChunk; ids are stable so
downstream traceability stays intact across runs.
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
import zipfile
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import Any

from lxml import etree

from ..core.models import SourceChunk

W_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def _chunk_id(source_file: str, suffix: str) -> str:
    h = hashlib.sha1(f"{source_file}::{suffix}".encode("utf-8")).hexdigest()[:12]
    return f"{Path(source_file).stem}.{suffix}.{h}"


def extract_pdf(path: Path) -> Iterator[SourceChunk]:
    """One chunk per page using pdfplumber."""
    try:
        import pdfplumber  # type: ignore
    except ImportError:
        return iter(())

    with pdfplumber.open(path) as pdf:
        for page_idx, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            text = text.strip()
            if not text:
                continue
            yield SourceChunk(
                chunk_id=_chunk_id(path.name, f"page.{page_idx}"),
                source_file=path.name,
                source_type="pdf",
                page=page_idx,
                text=text,
                scope_hint=_resolve_scope(text, path.name),
            )
            for table_idx, table in enumerate(page.extract_tables() or []):
                lines = _label_value_lines_from_pdf_table(table)
                if not lines:
                    continue
                table_text = "\n".join(lines)
                yield SourceChunk(
                    chunk_id=_chunk_id(path.name, f"page.{page_idx}.table.{table_idx}"),
                    source_file=path.name,
                    source_type="pdf",
                    page=page_idx,
                    text=table_text,
                    scope_hint=_resolve_scope(f"{text}\n{table_text}", path.name),
                )


def extract_docx(path: Path) -> Iterator[SourceChunk]:
    """Paragraphs + table-cell label:value pairs from a DOCX."""
    if not zipfile.is_zipfile(path):
        return iter(())

    chunks: list[SourceChunk] = []
    with zipfile.ZipFile(path) as zf:
        try:
            doc_xml = zf.read("word/document.xml")
        except KeyError:
            return iter(chunks)

    root = etree.fromstring(doc_xml)
    body = root.find(f"{W_NS}body")
    if body is None:
        return iter(chunks)

    para_idx = 0
    for p in body.iter(f"{W_NS}p"):
        text = "".join(t.text or "" for t in p.iter(f"{W_NS}t")).strip()
        if not text:
            continue
        para_idx += 1
        chunks.append(
            SourceChunk(
                chunk_id=_chunk_id(path.name, f"p.{para_idx}"),
                source_file=path.name,
                source_type="docx",
                text=text,
                scope_hint=_resolve_scope(text, path.name),
            )
        )

    table_idx = 0
    for table in body.iter(f"{W_NS}tbl"):
        rows = list(table.iter(f"{W_NS}tr"))
        # Look for label/value row pairs (label row, then value row with same cell count)
        for r_idx in range(len(rows) - 1):
            label_cells = [_cell_text(c) for c in rows[r_idx].iter(f"{W_NS}tc")]
            value_cells = [_cell_text(c) for c in rows[r_idx + 1].iter(f"{W_NS}tc")]
            if len(label_cells) == len(value_cells) and any(label_cells) and any(value_cells):
                pairs = [
                    f"{lab.strip()}: {val.strip()}"
                    for lab, val in zip(label_cells, value_cells)
                    if lab.strip() and val.strip()
                ]
                if pairs:
                    chunks.append(
                        SourceChunk(
                            chunk_id=_chunk_id(path.name, f"tbl.{table_idx}.row.{r_idx}"),
                            source_file=path.name,
                            source_type="docx",
                            text="\n".join(pairs),
                            scope_hint=_resolve_scope("\n".join(label_cells + value_cells), path.name),
                        )
                    )
        table_idx += 1
    return iter(chunks)


def _cell_text(cell: Any) -> str:
    return "".join(t.text or "" for t in cell.iter(f"{W_NS}t")).strip()


def extract_json(path: Path) -> Iterator[SourceChunk]:
    """Flatten JSON to label: value lines per top-level section."""
    try:
        with path.open(encoding="utf-8") as fh:
            data = json.load(fh)
    except (json.JSONDecodeError, OSError):
        return iter(())
    chunks: list[SourceChunk] = []

    def emit(section: str, payload: Any) -> None:
        lines = list(_flatten_json_lines(payload, prefix=""))
        if not lines:
            return
        chunks.append(
            SourceChunk(
                chunk_id=_chunk_id(path.name, f"section.{section}"),
                source_file=path.name,
                source_type="json",
                text="\n".join(lines),
                scope_hint=_resolve_scope(section + " " + " ".join(lines), path.name),
            )
        )

    if isinstance(data, dict):
        for k, v in data.items():
            emit(str(k), v)
    elif isinstance(data, list):
        for i, v in enumerate(data):
            emit(f"item.{i}", v)
    else:
        emit("root", data)

    return iter(chunks)


def _flatten_json_lines(payload: Any, prefix: str) -> Iterator[str]:
    if isinstance(payload, dict):
        for k, v in payload.items():
            new_prefix = f"{prefix}.{k}" if prefix else str(k)
            yield from _flatten_json_lines(v, new_prefix)
    elif isinstance(payload, list):
        for i, v in enumerate(payload):
            new_prefix = f"{prefix}[{i}]"
            yield from _flatten_json_lines(v, new_prefix)
    elif payload is None:
        return
    else:
        yield f"{prefix}: {payload}"


_INLINE_LABEL_VALUE_RE = re.compile(
    r"\b([A-Za-z0-9][A-Za-z0-9 _./()&\-#]{2,80}?)\s*:\s*([^:]{1,120})(?=$|\s{2,}|\n)",
    re.I,
)

_TABLE_SECTION_RE = re.compile(
    r"^(?:association of|american railroads|equipment|materials?|documents?|"
    r"design control|personnel|environment|quality records|test fixture|"
    r"special process|additional auditor|m-1002 exhibit|page \d+ of \d+)$",
    re.I,
)

_LABEL_HINT_RE = re.compile(
    r"\b(name|date|id|number|no\.?|spec|specification|drawing|revision|rev|"
    r"owner|instruction|performed|training|approved|record|result|equipment|"
    r"material|heat|width|height|thickness|pressure|temperature|calibration|"
    r"method|procedure|status|type|location|expiration|qualified|function)\b",
    re.I,
)


def _label_value_lines_from_pdf_table(table: list[list[Any]]) -> list[str]:
    """Convert extracted PDF table rows into conservative label:value lines.

    Filled official forms often render as a label row followed by a value row.
    This emits evidence chunks only; write authority still comes from the exact
    approval map downstream.
    """
    rows = [[_clean_pdf_cell(cell) for cell in row] for row in table if row]
    out: list[str] = []
    seen: set[str] = set()

    for row in rows:
        for cell in row:
            for match in _INLINE_LABEL_VALUE_RE.finditer(cell):
                _append_pdf_pair(out, seen, match.group(1), match.group(2))

    for idx in range(len(rows) - 1):
        for span in (2, 1):
            value_idx = idx + span
            if value_idx >= len(rows):
                continue
            if span == 2 and not _is_pdf_label_continuation(rows[idx + 1]):
                continue
            labels = (
                _merge_pdf_label_rows(rows[idx], rows[idx + 1])
                if span == 2
                else rows[idx]
            )
            values = rows[value_idx]
            if not _looks_like_pdf_label_row(labels, values):
                continue
            for label, value in _pair_pdf_label_values(labels, values):
                _append_pdf_pair(out, seen, label, value)
    return out


def _clean_pdf_cell(cell: Any) -> str:
    if cell is None:
        return ""
    return re.sub(r"\s+", " ", str(cell).replace("\n", " ")).strip()


def _merge_pdf_label_rows(first: list[str], second: list[str]) -> list[str]:
    width = max(len(first), len(second))
    merged: list[str] = []
    for i in range(width):
        parts = []
        if i < len(first) and first[i]:
            parts.append(first[i])
        if i < len(second) and second[i]:
            parts.append(second[i])
        merged.append(" ".join(parts).strip())
    return merged


def _looks_like_pdf_label_row(labels: list[str], values: list[str]) -> bool:
    label_cells = [cell for cell in labels if cell]
    value_cells = [cell for cell in values if cell]
    if not label_cells or not value_cells:
        return False
    if len(label_cells) == 1 and _is_pdf_section_heading(label_cells[0]):
        return False
    return any(_LABEL_HINT_RE.search(cell) for cell in label_cells)


def _is_pdf_label_continuation(row: list[str]) -> bool:
    cells = [cell for cell in row if cell]
    if not cells:
        return False
    return any(_LABEL_HINT_RE.search(cell) for cell in cells)


def _pair_pdf_label_values(labels: list[str], values: list[str]) -> Iterator[tuple[str, str]]:
    positions = [
        idx
        for idx, label in enumerate(labels)
        if label and not _is_pdf_section_heading(label)
    ]
    for n, pos in enumerate(positions):
        label = labels[pos]
        end = positions[n + 1] if n + 1 < len(positions) else len(values)
        start = max(0, pos - 1)
        value = values[pos].strip() if pos < len(values) and values[pos].strip() else None
        if not value:
            value = _first_pdf_value(values, start, end)
        if not value:
            value = _nearest_pdf_value(values, pos)
        if value:
            yield label, value


def _first_pdf_value(values: list[str], start: int, end: int) -> str | None:
    for idx in range(start, min(end, len(values))):
        value = values[idx].strip()
        if value:
            return value
    return None


def _nearest_pdf_value(values: list[str], pos: int) -> str | None:
    for distance in range(0, 3):
        for idx in (pos - distance, pos + distance):
            if 0 <= idx < len(values) and values[idx].strip():
                return values[idx].strip()
    return None


def _append_pdf_pair(out: list[str], seen: set[str], label: str, value: str) -> None:
    label = re.sub(r"\s+", " ", label).strip(" :-")
    value = re.sub(r"\s+", " ", value).strip()
    if not label or not value:
        return
    if label.lower() == value.lower():
        return
    if _is_pdf_section_heading(value):
        return
    line = f"{label}: {value}"
    key = line.lower()
    if key not in seen:
        seen.add(key)
        out.append(line)


def _is_pdf_section_heading(value: str) -> bool:
    value = value.strip()
    if not value:
        return False
    return bool(_TABLE_SECTION_RE.match(value)) or (
        value.isupper() and len(value.split()) <= 6 and not any(ch.isdigit() for ch in value)
    )


def extract_csv(path: Path) -> Iterator[SourceChunk]:
    try:
        with path.open(encoding="utf-8", newline="") as fh:
            reader = csv.DictReader(fh)
            chunks: list[SourceChunk] = []
            for i, row in enumerate(reader):
                lines = [f"{k}: {v}" for k, v in row.items() if v]
                if not lines:
                    continue
                chunks.append(
                    SourceChunk(
                        chunk_id=_chunk_id(path.name, f"row.{i}"),
                        source_file=path.name,
                        source_type="csv",
                        text="\n".join(lines),
                        scope_hint=_resolve_scope("\n".join(lines), path.name),
                    )
                )
            return iter(chunks)
    except OSError:
        return iter(())


def extract_text(path: Path, source_type: str = "txt") -> Iterator[SourceChunk]:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return iter(())
    parts = re.split(r"\n\s*\n", text)
    chunks: list[SourceChunk] = []
    for i, part in enumerate(parts):
        part = part.strip()
        if not part:
            continue
        chunks.append(
            SourceChunk(
                chunk_id=_chunk_id(path.name, f"chunk.{i}"),
                source_file=path.name,
                source_type=source_type,  # type: ignore[arg-type]
                text=part,
                scope_hint=_resolve_scope(part, path.name),
            )
        )
    return iter(chunks)


_EXACT_SCOPE_PATTERNS = {
    "Cover_Page": re.compile(r"exhibit\s+b-2\s+cover|cover\s+sheet|part\s+1:\s+general\s+information", re.I),
    "B24_RL2": re.compile(r"exhibit\s+b-2\s+b24|activity\s+code\s+b24|\bB24:", re.I),
    "B81_B24_only": re.compile(r"exhibit\s+b-2\.?B81|activity\s+code\s+B81|\bB81:", re.I),
    "B89": re.compile(r"exhibit\s+b-2\.?B89|activity\s+code\s+B89|\bB89:", re.I),
    "B90_RLS": re.compile(r"exhibit\s+b-2\.?B90|activity\s+code\s+B90|\bB90:", re.I),
    "C5S_Safety_Relief_Devices_512026": re.compile(r"exhibit\s+b-2\.?C5\s*\(?S\)?|activity\s+code\s+C5\s*\(?S\)?|\bC5\s*\(?S\)?:", re.I),
    "C5V_Valves_512026": re.compile(r"exhibit\s+b-2\.?C5\s*\(?V\)?|activity\s+code\s+C5\s*\(?V\)?|\bC5\s*\(?V\)?:", re.I),
    "C6r_RR_Service_Equipment_with_Modification_512026": re.compile(r"exhibit\s+b-2\.?C6r|activity\s+code\s+C6r|\bC6r:", re.I),
    "C7_C8__C10_Combination_Coatings": re.compile(r"exhibit\s+b-2\.?C7,\s*C8,\s*&\s*C10|activity\s+code\s+C7,\s*C8,\s*&\s*C10|\bC7:", re.I),
}

_SCOPE_PATTERNS = {
    "B89": re.compile(r"\bB89\b|insulation|jacket|patch\s+plate", re.I),
    "B81_B24_only": re.compile(r"\bB81\b|qualification\s+of\s+tank", re.I),
    "B90_RLS": re.compile(r"\bB90\b|stub\s+sill", re.I),
    "B24_RL2": re.compile(r"\bB24\b|repair\s+level\s+RL2", re.I),
    "C5S_Safety_Relief_Devices_512026": re.compile(r"\bC5\s*\(?S\)?\b|safety\s+relief", re.I),
    "C5V_Valves_512026": re.compile(r"\bC5\s*\(?V\)?\b|\bvalves?\b", re.I),
    "C6r_RR_Service_Equipment_with_Modification_512026": re.compile(r"\bC6r\b|remove\s+and\s+replace|service\s+equipment", re.I),
    "C7_C8__C10_Combination_Coatings": re.compile(r"\bC7\b|\bC8\b|\bC10\b|interior\s+coatings?|coating\s+owner", re.I),
    "Cover_Page": re.compile(r"\baudit\s+type\b|station\s+stencil|cover\s+page|opening\s+meeting|closing\s+meeting|boe\s+lead\s+auditor", re.I),
}

_FILENAME_SCOPE_PATTERNS = {
    "B89": re.compile(r"B89", re.I),
    "B81_B24_only": re.compile(r"B81", re.I),
    "B90_RLS": re.compile(r"B90", re.I),
    "B24_RL2": re.compile(r"B24", re.I),
    "C5S_Safety_Relief_Devices_512026": re.compile(r"C5S|C5\s*\(?S\)?", re.I),
    "C5V_Valves_512026": re.compile(r"C5V|C5\s*\(?V\)?", re.I),
    "C6r_RR_Service_Equipment_with_Modification_512026": re.compile(r"C6R", re.I),
    "C7_C8__C10_Combination_Coatings": re.compile(r"C7|C8|C10", re.I),
    "Cover_Page": re.compile(r"\bcover\b", re.I),
}


def _filename_scope(filename: str) -> str | None:
    """Derive scope from the filename. Returns form_id only if exactly one matches."""
    matches = [
        form_id
        for form_id, pat in _FILENAME_SCOPE_PATTERNS.items()
        if pat.search(filename)
    ]
    if len(matches) == 1:
        return matches[0]
    return None


def _guess_scope(text: str) -> str | None:
    """Cheap scope hint from text content - matches one form_id at most."""
    if not text:
        return None
    for form_id, pat in _EXACT_SCOPE_PATTERNS.items():
        if pat.search(text):
            return form_id
    for form_id, pat in _SCOPE_PATTERNS.items():
        if pat.search(text):
            return form_id
    return None


def _resolve_scope(text: str, filename: str) -> str | None:
    """Combined scope: filename is authoritative when available.

    If the filename clearly identifies a form, use that — text mentions of
    other forms inside a file named 'cover URBC 2025.pdf' are incidental
    references, not scope indicators. Text-based scope only applies to files
    with no filename-derived scope (like 'Combine' or 'URBC 2025').
    """
    file_scope = _filename_scope(filename)
    if file_scope is not None:
        return file_scope
    return _guess_scope(text)


def extract_any(path: Path) -> list[SourceChunk]:
    """Dispatch by extension. Returns a concrete list to make life easy."""
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return list(extract_pdf(path))
    if suffix == ".docx":
        return list(extract_docx(path))
    if suffix == ".json":
        return list(extract_json(path))
    if suffix == ".csv":
        return list(extract_csv(path))
    if suffix in (".txt", ".md"):
        return list(extract_text(path, source_type="txt" if suffix == ".txt" else "md"))
    return []


def collect_inbox(inbox: Path) -> list[SourceChunk]:
    """Walk inbox/, extract every supported file. Skips prior_b2_packet/."""
    out: list[SourceChunk] = []
    if not inbox.exists():
        return out
    skip = {"prior_b2_packet"}
    for entry in inbox.iterdir():
        if entry.is_dir() and entry.name in skip:
            continue
        if entry.is_dir():
            for sub in entry.rglob("*"):
                if sub.is_file():
                    out.extend(extract_any(sub))
            continue
        if entry.is_file():
            out.extend(extract_any(entry))
    return out
