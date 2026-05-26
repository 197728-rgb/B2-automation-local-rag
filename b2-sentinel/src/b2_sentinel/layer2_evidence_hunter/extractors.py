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


_SCOPE_PATTERNS = {
    "B89": re.compile(r"\bB89\b|insulation|jacket|patch\s+plate|test\s+plate", re.I),
    "B81": re.compile(r"\bB81\b|qualification\s+of\s+tank", re.I),
    "B90": re.compile(r"\bB90\b|stub\s+sill", re.I),
    "B24_RL2": re.compile(r"\bB24\b|repair\s+level\s+RL2", re.I),
    "Cover_Page": re.compile(r"audit(?:\s+type)?|station\s+stencil|cover\s+page|opening\s+meeting|closing\s+meeting", re.I),
}

_FILENAME_SCOPE_PATTERNS = {
    "B89": re.compile(r"B89", re.I),
    "B81": re.compile(r"B81", re.I),
    "B90": re.compile(r"B90", re.I),
    "B24_RL2": re.compile(r"B24", re.I),
    "C6R": re.compile(r"C6R", re.I),
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
