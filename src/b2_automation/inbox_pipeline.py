"""Inbox pipeline for local-first B-2 evidence review."""

from __future__ import annotations

import json
import re
import shutil
import zipfile
from io import BytesIO
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Mapping
from xml.etree import ElementTree as ET

from b2_automation.approval_maps import ApprovalBundle, load_exact_approval_bundle_checked
from b2_automation.evidence_assistant import build_delta_report, build_role_views, enrich_chunk_metadata, ensure_clause_map_db, write_eval_seed
from b2_automation.evidence_outputs import build_canonical_evidence_document, build_field_traceability_document
from b2_automation.local_extraction import (
    DEFAULT_REVIEW_FORMS,
    LOCAL_EVIDENCE_EXTENSIONS,
    LocalEvidenceDocument,
    build_form_packets,
    chunk_text,
    extract_local_document,
    normalize_review_forms,
    supported_evidence_files,
    utc_now,
    write_local_artifacts,
)
from b2_automation.ooxml_writer import patch_docx_cells

DEFAULT_LOW_CONFIDENCE_THRESHOLD = 0.70
REVIEW_REQUIRED_TEXT = "REVIEW_REQUIRED"
DOCX_TABLE_MARKER = "[structured_docx_table_evidence]"
AUTO_TABLE_PREFIX = "auto_table"
MAX_ZIP_EVIDENCE_DEPTH = 5
WORD_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
QAM_PROCEDURE_ROWS: tuple[tuple[str, str], ...] = (
    ("2.5", "Production, Inspection, and Test Plan (2.5)"),
    ("2.7", "Document Control (2.7)"),
    ("2.8", "Measure and Testing Equipment (2.8)"),
    ("2.9", "Purchasing and Subcontracting (2.9)"),
    ("2.10", "Incoming Material (2.10)"),
    ("2.11", "In-Process Inspection (2.11)"),
    ("2.12", "Final Inspection (2.12)"),
    ("2.13", "Inspection Status (2.13)"),
    ("2.14", "Identification and Traceability (2.14)"),
    ("2.16", "Preservation, Packaging, and Shipping (2.16)"),
    ("2.17", "Quality Records (2.17)"),
    ("2.23", "Contract Review (2.23)"),
    ("2.24", "Design Control (2.24)"),
)
QAM_PROCEDURE_SECTIONS = {section for section, _label in QAM_PROCEDURE_ROWS}
LABEL_WORDS = (
    "name",
    "date",
    "permission",
    "instruction",
    "car",
    "mark",
    "number",
    "spec",
    "stencil",
    "form",
    "drawing",
    "revision",
    "description",
    "material",
    "id",
    "status",
    "function",
    "training",
    "procedure",
    "approved",
    "record",
    "result",
    "equipment",
    "calibration",
    "location",
    "temperature",
    "method",
    "observed",
    "pitp",
)
LABEL_STOPWORDS = {
    "a",
    "an",
    "and",
    "by",
    "for",
    "from",
    "in",
    "of",
    "on",
    "or",
    "the",
    "to",
    "with",
    "aar",
    "tank",
    "car",
}


@dataclass(frozen=True)
class InboxPipelineResult:
    run_dir: Path
    manifest_path: Path
    review_json_path: Path
    review_md_path: Path
    filled_docx_path: Path | None
    filled_docx_paths: tuple[Path, ...]
    status: str


@dataclass(frozen=True)
class _DocxTableCell:
    text: str
    visual_col: int
    span: int


def _utc_now() -> str:
    return utc_now()


def _retrieval_summary(packets: dict[str, dict[str, Any]], forms: tuple[str, ...]) -> str:
    modes = sorted({str(packets.get(f, {}).get("retrieval_method") or "unknown") for f in forms})
    return "local semantic ranking: " + ", ".join(modes) + " (evidence-only; exact maps authorize writes)"


def _stage_inbox_evidence(inbox: Path, run_dir: Path) -> Path:
    staging_dir = run_dir / "staged_inbox"
    if staging_dir.exists():
        shutil.rmtree(staging_dir)
    staging_dir.mkdir(parents=True, exist_ok=True)
    for path in sorted(inbox.iterdir()):
        if not path.is_file():
            continue
        if path.suffix.lower() == ".zip":
            try:
                with zipfile.ZipFile(path) as zf:
                    _stage_zip_members(zf, staging_dir, prefix=safe_archive_stem(path), depth=0)
            except zipfile.BadZipFile:
                continue
            continue
        if path.suffix.lower() in LOCAL_EVIDENCE_EXTENSIONS:
            _copy_staged_file(path, staging_dir, safe_archive_member_name(path.name))
    return staging_dir


def _stage_zip_members(zf: zipfile.ZipFile, staging_dir: Path, *, prefix: str, depth: int) -> None:
    if depth >= MAX_ZIP_EVIDENCE_DEPTH:
        return
    for info in zf.infolist():
        if info.is_dir():
            continue
        member_name = safe_archive_member_name(info.filename)
        suffix = Path(member_name).suffix.lower()
        if suffix == ".zip":
            try:
                with zipfile.ZipFile(BytesIO(zf.read(info))) as nested:
                    _stage_zip_members(nested, staging_dir, prefix=f"{prefix}__{Path(member_name).stem}", depth=depth + 1)
            except zipfile.BadZipFile:
                continue
            continue
        if suffix in LOCAL_EVIDENCE_EXTENSIONS:
            _write_staged_bytes(staging_dir, f"{prefix}__{member_name}", zf.read(info))


def safe_archive_stem(path: Path) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", path.stem).strip("._") or "archive"


def safe_archive_member_name(name: str) -> str:
    parts = [part for part in re.split(r"[\\/]+", name) if part and part not in {".", ".."}]
    flat = "__".join(parts) if parts else "member"
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", flat).strip("._") or "member"


def _copy_staged_file(source: Path, staging_dir: Path, name: str) -> Path:
    dest = _unique_staged_path(staging_dir, name)
    shutil.copy2(source, dest)
    return dest


def _write_staged_bytes(staging_dir: Path, name: str, data: bytes) -> Path:
    dest = _unique_staged_path(staging_dir, name)
    dest.write_bytes(data)
    return dest


def _unique_staged_path(staging_dir: Path, name: str) -> Path:
    candidate = staging_dir / name
    if not candidate.exists():
        return candidate
    stem = candidate.stem
    suffix = candidate.suffix
    for index in range(2, 10_000):
        candidate = staging_dir / f"{stem}_{index}{suffix}"
        if not candidate.exists():
            return candidate
    raise RuntimeError(f"Could not create unique staged evidence name for {name!r}")


def _clear_scoped_filled_docx(filled_dir: Path, forms: tuple[str, ...]) -> None:
    for form in forms:
        try:
            (filled_dir / f"{form}_filled.docx").unlink()
        except FileNotFoundError:
            pass


def _augment_docx_table_evidence(documents: list[LocalEvidenceDocument]) -> list[LocalEvidenceDocument]:
    """Append row-paired DOCX table evidence so filled B-2 examples become usable RAG input."""
    augmented: list[LocalEvidenceDocument] = []
    for doc in documents:
        if doc.source_path.suffix.lower() != ".docx":
            augmented.append(doc)
            continue
        structured = _read_docx_table_pairs(doc.source_path)
        if not structured:
            augmented.append(doc)
            continue
        metadata = dict(doc.metadata or {})
        metadata["docx_table_structured_evidence"] = True
        metadata["docx_table_structured_characters"] = len(structured)
        augmented.append(
            replace(
                doc,
                text=(str(doc.text or "") + "\n\n" + DOCX_TABLE_MARKER + "\n" + structured).strip(),
                metadata=metadata,
            )
        )
    return augmented


def _read_docx_table_pairs(path: Path) -> str:
    try:
        with zipfile.ZipFile(path) as zf:
            root = ET.fromstring(zf.read("word/document.xml"))
    except OSError:
        return ""
    except (zipfile.BadZipFile, KeyError, ET.ParseError):
        return ""
    out: list[str] = []
    seen: set[str] = set()
    for table_index, table in enumerate(root.iter(f"{WORD_NS}tbl")):
        physical_rows = [_table_row_physical_cells(row) for row in table.iter(f"{WORD_NS}tr")]
        expanded_rows = [_expand_physical_cells(row) for row in physical_rows]
        for row_index, cells in enumerate(expanded_rows):
            compact = _collapse_adjacent_duplicates(cells)
            row_text = " | ".join(cell for cell in compact if cell)
            _emit_unique(out, seen, f"table_{table_index}_row_{row_index}: {row_text}")
        for label_cells, value_cells in zip(physical_rows, physical_rows[1:]):
            labels = _expand_physical_cells(label_cells)
            values = _expand_physical_cells(value_cells)
            if not _looks_like_label_row(labels) or _looks_like_label_row(values):
                continue
            for label_cell in label_cells:
                label = _clean_cell(label_cell.text)
                if not label or not _looks_like_label(label):
                    continue
                value_cell = _value_cell_for_visual_col(value_cells, label_cell.visual_col)
                if value_cell is None:
                    continue
                value = _clean_cell(value_cell.text)
                if not value or label == value or _looks_like_label(value):
                    continue
                _emit_unique(out, seen, f"{label}: {value}")
    return "\n".join(out)


def _table_row_physical_cells(row: ET.Element) -> list[_DocxTableCell]:
    cells: list[_DocxTableCell] = []
    visual_col = 0
    for cell in row.iter(f"{WORD_NS}tc"):
        text = _clean_cell(" ".join(node.text or "" for node in cell.iter(f"{WORD_NS}t")))
        span = 1
        grid_span = next(cell.iter(f"{WORD_NS}gridSpan"), None)
        if grid_span is not None:
            try:
                span = max(1, int(grid_span.attrib.get(f"{WORD_NS}val", "1")))
            except ValueError:
                span = 1
        cells.append(_DocxTableCell(text=text, visual_col=visual_col, span=span))
        visual_col += span
    return cells


def _table_row_cells(row: ET.Element) -> list[str]:
    return _expand_physical_cells(_table_row_physical_cells(row))


def _expand_physical_cells(cells: list[_DocxTableCell]) -> list[str]:
    expanded: list[str] = []
    for cell in cells:
        expanded.extend([cell.text] * cell.span)
    return expanded


def _value_cell_for_visual_col(cells: list[_DocxTableCell], visual_col: int) -> _DocxTableCell | None:
    for cell in cells:
        if cell.visual_col <= visual_col < cell.visual_col + cell.span:
            return cell
    return None


def _looks_like_label_row(cells: list[str]) -> bool:
    nonblank = [_clean_cell(cell) for cell in cells if _clean_cell(cell)]
    if not nonblank or len({cell.lower() for cell in nonblank}) == 1:
        return False
    label_hits = sum(1 for cell in nonblank if _looks_like_label(cell))
    value_hits = sum(1 for cell in nonblank if _looks_like_value(cell))
    return label_hits >= max(1, len(nonblank) // 3) and label_hits >= value_hits


def _looks_like_label(text: str) -> bool:
    lower = _clean_cell(text).lower()
    if not lower:
        return False
    return lower.endswith(":") or any(word in lower for word in LABEL_WORDS) or (lower.upper() == lower and len(lower.split()) <= 8)


def _looks_like_value(text: str) -> bool:
    cleaned = _clean_cell(text)
    if not cleaned:
        return False
    if re.search(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b|\b[A-Z]{2,6}\s*[- ]?\d{3,8}\b", cleaned):
        return True
    if re.search(r"\b\d+(?:\.\d+)?\s*(?:psi|psig|f|mils?|in|%)\b", cleaned, flags=re.IGNORECASE):
        return True
    return bool(re.search(r"[a-z]", cleaned) and len(cleaned.split()) <= 12)


def _collapse_adjacent_duplicates(cells: list[str]) -> list[str]:
    out: list[str] = []
    last = None
    for cell in cells:
        if cell and cell != last:
            out.append(cell)
        last = cell
    return out


def _clean_cell(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "").replace("\u00a0", " ")).strip(" |")


def _emit_unique(out: list[str], seen: set[str], line: str) -> None:
    line = _clean_cell(line)
    if line and line not in seen:
        seen.add(line)
        out.append(line)


def _collect_label_value_evidence(documents: list[LocalEvidenceDocument]) -> dict[str, list[str]]:
    return _collect_label_value_evidence_from_texts([doc.text for doc in documents])


def _collect_packet_label_value_evidence(packet: Mapping[str, Any]) -> dict[str, list[str]]:
    texts: list[str] = []
    for row in packet.get("retrieved_context", []) or []:
        if isinstance(row, Mapping):
            texts.append(str(row.get("full_text") or row.get("text") or ""))
    evidence = _collect_label_value_evidence_from_texts(texts)
    for decision in packet.get("field_decisions", []) or []:
        if not isinstance(decision, Mapping):
            continue
        value = _clean_cell(str(decision.get("selected_value") or ""))
        if not value or value.startswith(REVIEW_REQUIRED_TEXT):
            continue
        field_id = str(decision.get("field_id") or "")
        if not field_id:
            continue
        key = _normalize_label_key(field_id)
        if not key:
            continue
        evidence.setdefault(key, [])
        if value not in evidence[key]:
            evidence[key].append(value)
    return evidence


def _collect_label_value_evidence_from_texts(texts: list[str]) -> dict[str, list[str]]:
    evidence: dict[str, list[str]] = {}
    pending_key: str | None = None
    for text in texts:
        for raw_line in str(text or "").splitlines():
            line = _clean_cell(raw_line)
            if not line:
                continue
            if ":" not in line:
                if pending_key is None:
                    continue
                bucket = evidence.setdefault(pending_key, [])
                if not bucket:
                    bucket.append(line)
                else:
                    bucket[-1] = _clean_cell(bucket[-1] + " " + line)
                pending_key = None
                continue
            if pending_key is not None:
                pending_key = None
            label, value = line.split(":", 1)
            label = re.sub(r"^table_[0-9]+_row_[0-9]+\s*", "", label).strip()
            value = _clean_cell(value)
            if not label:
                pending_key = None
                continue
            if value.startswith(REVIEW_REQUIRED_TEXT):
                pending_key = None
                continue
            key = _normalize_label_key(label)
            if not key:
                pending_key = None
                continue
            bucket = evidence.setdefault(key, [])
            if not value:
                pending_key = key
                continue
            pending_key = None
            if len(value) > 160:
                continue
            if value not in bucket:
                bucket.append(value)
    return evidence


def _merge_label_evidence(primary: Mapping[str, list[str]], fallback: Mapping[str, list[str]]) -> dict[str, list[str]]:
    merged: dict[str, list[str]] = {}
    for source in (primary, fallback):
        for key, values in source.items():
            bucket = merged.setdefault(str(key), [])
            for value in values:
                if value not in bucket:
                    bucket.append(value)
    return merged


_MONTHS = {
    "ene": 1,
    "enero": 1,
    "jan": 1,
    "january": 1,
    "feb": 2,
    "febrero": 2,
    "february": 2,
    "mar": 3,
    "marzo": 3,
    "march": 3,
    "abr": 4,
    "abril": 4,
    "apr": 4,
    "april": 4,
    "may": 5,
    "mayo": 5,
    "jun": 6,
    "junio": 6,
    "june": 6,
    "jul": 7,
    "julio": 7,
    "july": 7,
    "ago": 8,
    "agosto": 8,
    "aug": 8,
    "august": 8,
    "sep": 9,
    "sept": 9,
    "septiembre": 9,
    "september": 9,
    "oct": 10,
    "octubre": 10,
    "october": 10,
    "nov": 11,
    "noviembre": 11,
    "november": 11,
    "dic": 12,
    "diciembre": 12,
    "dec": 12,
    "december": 12,
}
_MONTH_PATTERN = "|".join(sorted(map(re.escape, _MONTHS), key=len, reverse=True))


def _extract_cover_qam_procedure_records(documents: list[LocalEvidenceDocument]) -> dict[str, dict[str, str]]:
    records: dict[str, dict[str, str]] = {}
    for doc in documents:
        section = _extract_qam_section(doc.source_file, doc.text)
        if section not in QAM_PROCEDURE_SECTIONS:
            continue
        record = {
            "procedure_id": f"GQAP {section}",
            "approved_by": _extract_qam_approver(doc.text),
            "date_approved": _extract_qam_revision_date(doc.text),
            "revision": _extract_qam_version(doc.text),
        }
        record = {key: value for key, value in record.items() if value}
        if not record:
            continue
        existing = records.setdefault(section, {})
        for key, value in record.items():
            existing.setdefault(key, value)
    approvers = {record.get("approved_by") for record in records.values() if record.get("approved_by")}
    if len(approvers) == 1:
        approver = next(iter(approvers))
        for record in records.values():
            record.setdefault("approved_by", approver)
    return records


def _extract_qam_section(source_file: str, text: str) -> str | None:
    compact = _clean_cell(text)
    match = re.search(r"\bCODIGO\b.{0,120}?\bGQAP\s*[-_ ]?\s*2\s*[._ -]\s*([0-9]{1,2})\b", compact, flags=re.IGNORECASE)
    if match:
        return f"2.{int(match.group(1))}"
    matches = re.findall(r"\bGQAP\s*[-_ ]?\s*2\s*[._ -]\s*([0-9]{1,2})\b", str(source_file), flags=re.IGNORECASE)
    if matches:
        return f"2.{int(matches[-1])}"
    return None


def _extract_qam_approver(text: str) -> str:
    if re.search(r"\bBenjamin\s+De\s+La\s+Garza\b", text, flags=re.IGNORECASE):
        return "B. De La Garza"
    compact = _clean_cell(text)
    match = re.search(
        r"\bAPROBO\s*/\s*APPRO(?:VED|VED|V?ED)\s+BY\b.{0,180}?\b(?:Ing|Lic)\.\s+([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+){1,4})",
        compact,
        flags=re.IGNORECASE,
    )
    if not match:
        return ""
    parts = match.group(1).split()
    if len(parts) >= 2:
        return f"{parts[0][0]}. {' '.join(parts[1:])}"
    return match.group(1)


def _extract_qam_revision_date(text: str) -> str:
    compact = _clean_cell(text).replace("–", "-").replace("—", "-")
    prefix_match = re.search(r"\b(?:FECHA\s+DE\s+REVISION|Revision\s+Date|Revision\s+date)\b(.{0,240})", compact, flags=re.IGNORECASE)
    search_texts = [prefix_match.group(1)] if prefix_match else []
    search_texts.append(compact[:4000])
    match = next(
        (
            found
            for candidate in search_texts
            if (found := re.search(rf"\b([0-9]{{1,2}})\s*-\s*({_MONTH_PATTERN})\s*-\s*([0-9]{{4}})\b", candidate, flags=re.IGNORECASE))
        ),
        None,
    )
    if match:
        day = int(match.group(1))
        month = _MONTHS[match.group(2).lower()]
        year = int(match.group(3))
        return f"{month}/{day}/{year}"
    match = next(
        (
            found
            for candidate in search_texts
            if (found := re.search(rf"\b({_MONTH_PATTERN})\s*-\s*([0-9]{{1,2}})\s*-\s*([0-9]{{4}})\b", candidate, flags=re.IGNORECASE))
        ),
        None,
    )
    if match:
        month = _MONTHS[match.group(1).lower()]
        day = int(match.group(2))
        year = int(match.group(3))
        return f"{month}/{day}/{year}"
    return ""


def _extract_qam_version(text: str) -> str:
    compact = _clean_cell(text)
    match = re.search(r"\bNUMERO\s+DE\s+VERSION\b.{0,80}?\b([0-9]{1,2})\b", compact, flags=re.IGNORECASE)
    return match.group(1) if match else ""


def _normalize_label_key(label: str) -> str:
    label = _clean_cell(label).lower()
    label = label.replace("/", " ").replace("&", " and ")
    label = re.sub(r"\([^)]*\)", " ", label)
    label = re.sub(r"[^a-z0-9]+", " ", label)
    tokens = [tok for tok in label.split() if tok and tok not in LABEL_STOPWORDS]
    return " ".join(tokens)


def _label_tokens(label: str) -> set[str]:
    return set(_normalize_label_key(label).split())


def _value_looks_like_date(value: str) -> bool:
    return bool(
        re.fullmatch(r"[0-9]{4}-[0-9]{1,2}-[0-9]{1,2}|[0-9]{1,2}/[0-9]{1,2}/[0-9]{2,4}", value)
        or re.fullmatch(r"[0-9]{1,2}[-\s][A-Za-z]+[-\s][0-9]{2,4}", value)
    )


def _value_looks_like_design_spec(value: str) -> bool:
    if re.fullmatch(r"(?:tank\s+car|car\s+type|t[-\s]?joint|junta\s+t)", value.strip(), flags=re.IGNORECASE):
        return False
    return bool(re.search(r"\b(?:DOT|AAR)\s*[0-9][A-Z0-9./-]{3,}\b", value, flags=re.IGNORECASE))


def _label_value_is_compatible(label: str, value: str) -> bool:
    tokens = _label_tokens(label)
    cleaned = _clean_cell(value)
    if not cleaned:
        return False
    lower = cleaned.lower()
    if lower in {"n/a", "na", "none", "-", "—"}:
        return False
    if re.fullmatch(r"[a-z]\)", lower):
        return False
    if re.search(r"(?:^|\s)[a-z]\)(?:\s+[a-z]\)){1,}", lower):
        return False
    if re.search(r"\bday\s+where\s+the\s+action\b", lower):
        return False
    if re.fullmatch(r"equipment\s+red(?:\s+equipment\s+red)*", lower):
        return False
    if re.search(r"(?:^|\s)121405\)(?:\s|$)", lower):
        return False
    if re.search(r"(?:^|\s)1j1~?'?(?:\s|$)", lower):
        return False
    if re.search(r"\bconfirmaci[oó6]n\s+por\s+correo\s+electr[oó6]nico\b", lower) and not (tokens & {"instruction", "instructions", "permission", "tco", "owner", "comments", "notes"}):
        return False
    if re.fullmatch(r"rls", lower) and (tokens & {"material", "description", "location", "facility", "design", "stencil", "specification"}) and not (tokens & {"stub", "sill", "type"}):
        return False
    if re.fullmatch(r"t[-\s]?joint", lower) and not (tokens & {"stub", "sill", "joint", "type", "description"}):
        return False
    if {"station", "stencil"} <= tokens:
        return bool(re.fullmatch(r"[A-Z0-9.-]{1,16}", cleaned, flags=re.IGNORECASE))
    if ({"design", "spec"} <= tokens or {"stencil", "spec"} <= tokens) and not _value_looks_like_design_spec(cleaned):
        return False
    if "date" in tokens and not _value_looks_like_date(cleaned):
        return False
    if "mark" in tokens and re.fullmatch(r"[A-Z]{2,10}(?:[-\s][A-Z0-9]{2,10})?", cleaned, flags=re.IGNORECASE):
        return True
    numeric_label_tokens = {"id", "number", "no", "form", "drawing", "spec", "stencil", "mark", "mtr"}
    if tokens & numeric_label_tokens and not re.search(r"\d", cleaned):
        return False
    if "approved" in tokens and "date" not in tokens and "by" not in tokens:
        if len(cleaned.split()) > 3:
            return False
        if not re.fullmatch(r"[A-Za-z0-9./-]{1,16}(?:\s+[A-Za-z0-9./-]{1,16}){0,2}", cleaned):
            return False
    if {"revision"} & tokens or {"rev"} <= tokens:
        return bool(re.fullmatch(r"[A-Za-z0-9._-]{1,16}", cleaned))
    return True


def _best_compatible_value(label: str, values: list[str]) -> str | None:
    compatible = [_clean_cell(value) for value in values if _label_value_is_compatible(label, value)]
    if not compatible:
        return None
    if "date" in _label_tokens(label):
        compatible.sort(key=lambda value: (0 if _value_looks_like_date(value) else 1, len(value)))
        return compatible[0]
    return compatible[0]


def _best_value_for_label(label: str, evidence: Mapping[str, list[str]]) -> str | None:
    key = _normalize_label_key(label)
    direct = evidence.get(key)
    if direct:
        chosen = _best_compatible_value(label, direct)
        if chosen:
            return chosen
    for preferred_key in _preferred_evidence_keys(key):
        values = evidence.get(preferred_key)
        if values:
            chosen = _best_compatible_value(label, values)
            if chosen:
                return chosen
    tokens = _label_tokens(label)
    if not tokens:
        return None
    numeric_label_tokens = {"id", "number", "no", "form", "drawing", "spec", "stencil", "mark", "mtr"}
    sensitive_label_tokens = {
        "calibration",
        "equipment",
        "function",
        "location",
        "material",
        "method",
        "ndt",
        "personnel",
        "procedure",
        "stencil",
        "stenciling",
        "thermocouple",
        "training",
        "visual",
        "welding",
    }
    best_key = ""
    best_score = 0.0
    for candidate_key in evidence.keys():
        candidate_tokens = set(str(candidate_key).split())
        if not candidate_tokens:
            continue
        # Avoid weak cross-field matching for sensitive label classes.
        if "date" in tokens and "date" not in candidate_tokens:
            continue
        if tokens & numeric_label_tokens and not (candidate_tokens & numeric_label_tokens):
            continue
        if {"date", "approved"} <= tokens and "pitp" not in tokens and "pitp" in candidate_tokens:
            continue
        overlap = len(tokens & candidate_tokens)
        if overlap == 0:
            continue
        sensitive = tokens & sensitive_label_tokens
        if sensitive and not (candidate_tokens & sensitive):
            continue
        if len(tokens) >= 3 and overlap < 2:
            continue
        score = overlap / max(len(tokens), len(candidate_tokens))
        if tokens <= candidate_tokens or candidate_tokens <= tokens:
            score += 0.25
        if {"date", "permission"} <= tokens and {"date", "permission"} <= candidate_tokens:
            score += 0.25
        if {"drawing", "number"} <= tokens and {"drawing", "number"} <= candidate_tokens:
            score += 0.25
        if {"material", "thickness"} <= tokens and "thickness" in candidate_tokens:
            score += 0.25
        if score > best_score:
            best_key = str(candidate_key)
            best_score = score
    if best_score >= 0.38 and best_key:
        values = evidence.get(best_key) or []
        chosen = _best_compatible_value(label, values)
        if chosen:
            return chosen
    return None


def _preferred_evidence_keys(key: str) -> tuple[str, ...]:
    tokens = set(key.split())
    preferred: list[str] = []
    if {"date", "permission"} <= tokens:
        preferred.extend(["tco permission date", "permission received"])
    if {"written", "instruction"} <= tokens or {"instruction", "received"} <= tokens:
        preferred.extend(["tco written instructions", "tco instructions"])
    if {"drawing", "number"} <= tokens:
        preferred.extend(["four two drawing number", "drawing number", "aar form 4 2 number"])
    if "revision" in tokens and "drawing" in tokens:
        preferred.extend(["four two drawing revision", "drawing revision"])
    if {"material", "thickness"} <= tokens:
        preferred.extend(["observed thickness", "thickness", "test fixture patch plate size"])
    if "contour" in tokens and "plate" in tokens:
        preferred.extend(["observed contour test plate", "test plate tank material"])
    if "rls" in tokens or "weldin" in tokens or "welding" in tokens:
        preferred.extend(["tco written instructions", "stub sill type", "materials stub sill spec"])
    if "calibration" in tokens or "calibrations" in tokens:
        preferred.extend(["calibration due", "calibration"])
    if "function" in tokens and "performed" in tokens:
        preferred.extend(["function performed"])
    if "measure" in tokens and "equipment" in tokens:
        preferred.extend(["measure test equipment"])
    if "ndt" in tokens:
        preferred.extend(["ndt method", "ndt equipment"])
    if "visual" in tokens or "acuity" in tokens:
        preferred.extend(["visual acuity exam due date"])
    if "stub" in tokens and "sill" in tokens:
        preferred.extend(
            [
                "location facility stub sill qualification stenciling was observed",
                "stub sill type",
            ]
        )
    if "thermocouple" in tokens:
        preferred.extend(
            [
                "control thermocouples required procedure",
                "spare thermocouples required procedure",
                "observed control thermocouples applied",
                "observed spare thermocouples applied",
                "observed monitor thermocouples applied if required",
            ]
        )
    if "two" in tokens and "piece" in tokens and "tee" in tokens:
        preferred.extend(
            [
                "observed two piece tee joint configuration width",
                "observed two piece tee joint configuration height",
                "observed distance between test plate positions",
                "observed welder position",
            ]
        )
    if "stenciling" in tokens or "stencil" in tokens:
        preferred.extend(["location facility stenciling was observed"])
    return tuple(preferred)


def _append_table_autofill_cells(
    *,
    form: str,
    bundle: ApprovalBundle,
    fill_manifest: dict[str, Any],
    values: dict[str, str],
    confidences: dict[str, float],
    label_evidence: Mapping[str, list[str]],
    qam_procedure_records: Mapping[str, Mapping[str, str]] | None = None,
) -> tuple[list[str], list[str]]:
    """Add label-driven table cells so the output is not limited to the small approval map."""
    if form == "Cover_Page":
        # Cover page approval is intentionally limited to its exact map.
        # Broad label/value auto-fill can otherwise pull B24 body evidence into
        # a cover template that shares the same large grid structure. The QAM
        # procedure table is safe because each row is keyed by explicit GQAP
        # procedure headers in the evidence.
        return _append_cover_page_qam_procedure_cells(
            bundle=bundle,
            fill_manifest=fill_manifest,
            values=values,
            confidences=confidences,
            qam_procedure_records=qam_procedure_records or {},
        )
    cells = list(fill_manifest.get("cells") or [])
    existing_coords = {
        (int(cell["table_index"]), int(cell["row"]), int(cell["col"]))
        for cell in cells
        if isinstance(cell, Mapping) and {"table_index", "row", "col"} <= set(cell.keys())
    }
    added: list[str] = []
    manual: list[str] = []
    for spec, label in _template_autofill_specs(bundle.template_path, existing_coords):
        fid = str(spec["field_id"])
        value = _best_value_for_label(label, label_evidence)
        if value is None:
            manual.append(fid)
            continue
        values[fid] = value
        confidences[fid] = 0.99
        cells.append(spec)
        added.append(fid)
    fill_manifest["cells"] = cells
    return added, manual


def _append_cover_page_qam_procedure_cells(
    *,
    bundle: ApprovalBundle,
    fill_manifest: dict[str, Any],
    values: dict[str, str],
    confidences: dict[str, float],
    qam_procedure_records: Mapping[str, Mapping[str, str]],
) -> tuple[list[str], list[str]]:
    if not qam_procedure_records:
        return [], []
    cells = list(fill_manifest.get("cells") or [])
    existing_coords = {
        (int(cell["table_index"]), int(cell["row"]), int(cell["col"]))
        for cell in cells
        if isinstance(cell, Mapping) and {"table_index", "row", "col"} <= set(cell.keys())
    }
    added: list[str] = []
    manual: list[str] = []
    field_names = {
        1: ("procedure_id", "Procedure ID"),
        2: ("approved_by", "Approved By"),
        3: ("date_approved", "Date Approved"),
        4: ("revision", "Revision"),
    }
    for spec, section, field_name in _cover_page_qam_part4_specs(bundle.template_path, existing_coords):
        record = qam_procedure_records.get(section) or {}
        value = _clean_cell(str(record.get(field_name) or ""))
        fid = str(spec["field_id"])
        if not value:
            value = _marker(fid, "missing QAM procedure metadata; needs manual completion")
            manual.append(fid)
        values[fid] = value
        confidences[fid] = 0.99
        spec["label"] = f"{dict(QAM_PROCEDURE_ROWS).get(section, section)} {field_names[int(spec['col'])][1]}"
        cells.append(spec)
        added.append(fid)
    fill_manifest["cells"] = cells
    return added, manual


def _cover_page_qam_part4_specs(
    template_path: Path,
    existing_coords: set[tuple[int, int, int]],
) -> list[tuple[dict[str, Any], str, str]]:
    try:
        with zipfile.ZipFile(template_path) as zf:
            root = ET.fromstring(zf.read("word/document.xml"))
    except (OSError, zipfile.BadZipFile, KeyError, ET.ParseError):
        return []
    specs: list[tuple[dict[str, Any], str, str]] = []
    used_coords = set(existing_coords)
    field_names = {
        1: "procedure_id",
        2: "approved_by",
        3: "date_approved",
        4: "revision",
    }
    for table_index, table in enumerate(root.iter(f"{WORD_NS}tbl")):
        rows = list(table.iter(f"{WORD_NS}tr"))
        expanded_rows = [_expand_physical_cells(_table_row_physical_cells(row)) for row in rows]
        table_text = " ".join(_clean_cell(cell) for row in expanded_rows for cell in row)
        if not re.search(r"\bPART\s*4\b", table_text, flags=re.IGNORECASE):
            continue
        if "Quality Assurance Manual" not in table_text:
            continue
        for row_index, row in enumerate(rows):
            physical_cells = _table_row_physical_cells(row)
            if len(physical_cells) < 5:
                continue
            label = _clean_cell(physical_cells[0].text)
            section_match = re.search(r"\((2\.[0-9]{1,2})\)", label)
            if not section_match:
                continue
            section = section_match.group(1)
            if section not in QAM_PROCEDURE_SECTIONS:
                continue
            for col, field_name in field_names.items():
                coord = (table_index, row_index, col)
                if coord in used_coords:
                    continue
                current = ""
                for cell in physical_cells:
                    if cell.visual_col == col:
                        current = _clean_cell(cell.text)
                        break
                if current and not _is_template_placeholder(current):
                    continue
                used_coords.add(coord)
                field_id = f"{AUTO_TABLE_PREFIX}.cover_qam_part4.{section.replace('.', '_')}.{field_name}"
                specs.append(
                    (
                        {
                            "field_id": field_id,
                            "table_index": table_index,
                            "row": row_index,
                            "col": col,
                            "required": False,
                            "cell_role": "target",
                            "label": label,
                        },
                        section,
                        field_name,
                    )
                )
    return specs


def _template_autofill_specs(template_path: Path, existing_coords: set[tuple[int, int, int]]) -> list[tuple[dict[str, Any], str]]:
    try:
        with zipfile.ZipFile(template_path) as zf:
            root = ET.fromstring(zf.read("word/document.xml"))
    except (OSError, zipfile.BadZipFile, KeyError, ET.ParseError):
        return []
    specs: list[tuple[dict[str, Any], str]] = []
    used_coords = set(existing_coords)
    for table_index, table in enumerate(root.iter(f"{WORD_NS}tbl")):
        physical_rows = [_table_row_physical_cells(row) for row in table.iter(f"{WORD_NS}tr")]
        expanded_rows = [_expand_physical_cells(row) for row in physical_rows]
        for row_index in range(len(physical_rows) - 1):
            label_cells = physical_rows[row_index]
            value_cells = physical_rows[row_index + 1]
            if not _looks_like_label_row(expanded_rows[row_index]):
                continue
            if _looks_like_label_row(expanded_rows[row_index + 1]):
                continue
            for label_cell in label_cells:
                label = _clean_cell(label_cell.text)
                if not label or not _looks_like_label(label):
                    continue
                value_cell = _value_cell_for_visual_col(value_cells, label_cell.visual_col)
                if value_cell is None:
                    continue
                current_value = _clean_cell(value_cell.text)
                if current_value and not _is_template_placeholder(current_value):
                    continue
                coord = (table_index, row_index + 1, value_cell.visual_col)
                if coord in used_coords:
                    continue
                used_coords.add(coord)
                field_id = f"{AUTO_TABLE_PREFIX}.t{table_index}.r{row_index + 1}.c{value_cell.visual_col}.{_slug_label(label)}"
                specs.append(
                    (
                        {
                            "field_id": field_id,
                            "table_index": table_index,
                            "row": row_index + 1,
                            "col": value_cell.visual_col,
                            "required": False,
                            "cell_role": "target",
                            "label": label,
                        },
                        label,
                    )
                )
    return specs


def _is_template_placeholder(text: str) -> bool:
    lower = _clean_cell(text).lower()
    if not lower:
        return True
    return lower in {"n/a", "na", "none", "-", "—"} or "click" in lower or "enter" in lower or lower.startswith("{{")


def _slug_label(label: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", _normalize_label_key(label))
    slug = slug.strip("_")[:48]
    return slug or "field"


def _field_values_from_packet(packet: dict[str, Any]) -> tuple[dict[str, str], dict[str, float], dict[str, str]]:
    values: dict[str, str] = {}
    confidences: dict[str, float] = {}
    manual_reasons: dict[str, str] = {}
    for decision in packet.get("field_decisions", []):
        value = decision.get("selected_value")
        if value is None or str(value).strip() == "":
            continue
        field_id = str(decision["field_id"])
        state = str(decision.get("state") or "")
        if state not in {"FILL", "REVIEW_REQUIRED", "LOW_CONFIDENCE"}:
            continue
        values[field_id] = str(value).strip()
        confidences[field_id] = float(decision.get("confidence") or 1.0)
        reason = _review_marker_reason(field_id, str(value), str(decision.get("reason") or ""))
        if reason:
            manual_reasons[field_id] = reason
    return values, confidences, manual_reasons


def _manifest_cells_for_fill(bundle: ApprovalBundle, values: Mapping[str, str]) -> dict[str, Any]:
    raw_fields = bundle.approval_map.get("fields") or {}
    approved_ids = {str(k) for k in raw_fields.keys()} if isinstance(raw_fields, dict) else set()
    cells = [
        spec
        for spec in bundle.manifest.get("cells") or []
        if str(spec.get("field_id", "")) in values and str(spec.get("field_id", "")) in approved_ids
    ]
    return {**dict(bundle.manifest), "cells": cells}


def _marker(field_id: str, reason: str) -> str:
    return f"{REVIEW_REQUIRED_TEXT}: {field_id} {reason}".strip()


def _review_marker_reason(field_id: str, value: str, fallback: str = "") -> str:
    text = str(value or "").strip()
    prefix = f"{REVIEW_REQUIRED_TEXT}: {field_id}"
    if text.startswith(prefix):
        reason = text[len(prefix):].strip()
        return reason or fallback or "requires manual completion"
    if text.startswith(REVIEW_REQUIRED_TEXT):
        return text[len(REVIEW_REQUIRED_TEXT):].lstrip(": ").strip() or fallback or "requires manual completion"
    return fallback if "review" in fallback.lower() or "missing" in fallback.lower() else ""


def _add_missing_required_map_markers(
    bundle: ApprovalBundle,
    values: dict[str, str],
    confidences: dict[str, float],
    manual_reasons: dict[str, str],
) -> list[str]:
    fields = bundle.approval_map.get("fields") or {}
    if not isinstance(fields, Mapping):
        return []
    manual: list[str] = []
    for field_id, spec in fields.items():
        if not isinstance(spec, Mapping) or not bool(spec.get("required")):
            continue
        fid = str(field_id)
        if str(values.get(fid) or "").strip():
            continue
        reason = "missing PDF evidence candidate; needs manual completion"
        values[fid] = _marker(fid, reason)
        confidences[fid] = 1.0
        manual_reasons[fid] = reason
        manual.append(fid)
    return sorted(manual)


def _sanitize_map_values_against_labels(
    form: str,
    bundle: ApprovalBundle,
    values: dict[str, str],
    confidences: dict[str, float],
    manual_reasons: dict[str, str],
) -> None:
    fields = bundle.approval_map.get("fields") or {}
    if not isinstance(fields, Mapping):
        return
    for field_id, spec in fields.items():
        if not isinstance(spec, Mapping):
            continue
        fid = str(field_id)
        current = str(values.get(fid) or "").strip()
        if not current or current.startswith(REVIEW_REQUIRED_TEXT):
            continue
        label = str(spec.get("label") or fid)
        required = bool(spec.get("required"))
        unsafe_reason = _unsafe_mapped_value_reason(form, fid, label, current)
        if not unsafe_reason and _label_value_is_compatible(label, current):
            continue
        if required:
            reason = unsafe_reason or "rejected incompatible PDF/autofill value; needs manual completion"
            values[fid] = _marker(fid, reason)
            confidences[fid] = 1.0
            manual_reasons[fid] = f"{reason}; rejected value: {current}"
        else:
            values.pop(fid, None)
            confidences.pop(fid, None)


def _unsafe_mapped_value_reason(form: str, field_id: str, label: str, value: str) -> str:
    fid = str(field_id)
    lower = _clean_cell(value).lower()
    if fid in {"car_mark", "car.mark", "car_number"}:
        if re.search(r"\b(?:probeta|muestra|specimen)\b", lower):
            return "rejected junk car identity text; needs manual completion"
        expected_codes = {
            "B24_RL2": {"b24"},
            "B81": {"b81"},
            "B89": {"b89"},
            "B90": {"b90"},
        }.get(form, set())
        value_codes = {match.group(1).lower() for match in re.finditer(r"\b(b(?:24|81|89|90))\b", lower)}
        if expected_codes and value_codes and not (value_codes & expected_codes):
            return "rejected cross-form car identity; needs manual completion"
    if fid in {"pitp.name", "pitp_document_name"} and re.fullmatch(r"pc[-\s]?tc[-\s]?\d+", lower, flags=re.IGNORECASE):
        return "rejected PITP ID in document-name cell; needs manual completion"
    if fid in {"tank_design_spec", "car.design_spec", "car.stencil_spec"} and not _value_looks_like_design_spec(value):
        return "rejected non-DOT/AAR design or stencil value; needs manual completion"
    if fid.startswith("materials.") and re.fullmatch(
        r"(?:rls|t[-\s]?joint|confirmaci[oó6]n\s+por\s+correo\s+electr[oó6]nico)",
        lower,
        flags=re.IGNORECASE,
    ):
        return "rejected cross-field text in material cell; needs manual completion"
    if re.search(r"\b(?:rls|t[-\s]?joint|confirmaci[oó6]n\s+por\s+correo\s+electr[oó6]nico)\b", lower):
        sensitive = {"material", "location", "facility", "design", "stencil", "specification"}
        allowed = {"stub", "sill", "type", "instruction", "instructions", "permission", "tco", "owner"}
        tokens = _label_tokens(label)
        if tokens & sensitive and not (tokens & allowed):
            return "rejected cross-field text in mapped cell; needs manual completion"
    return ""


def _manual_fields(values: Mapping[str, str]) -> list[str]:
    return sorted(fid for fid, value in values.items() if str(value).startswith(REVIEW_REQUIRED_TEXT))


def _filled_docx_safety_errors(form: str, docx_path: Path, values: Mapping[str, str]) -> list[str]:
    errors: list[str] = []
    for field_id, value in values.items():
        text = _clean_cell(str(value))
        if text.startswith(REVIEW_REQUIRED_TEXT):
            continue
        reason = _unsafe_mapped_value_reason(form, str(field_id), str(field_id), text)
        if reason:
            errors.append(f"{form}/{field_id}: {reason}")
    try:
        with zipfile.ZipFile(docx_path) as zf:
            xml = zf.read("word/document.xml").decode("utf-8", errors="replace")
    except (OSError, zipfile.BadZipFile, KeyError):
        return errors
    text = " ".join(html_unescape(part) for part in re.findall(r"<w:t(?:\s[^>]*)?>(.*?)</w:t>", xml, flags=re.DOTALL))
    text = re.sub(r"\s+", " ", text)
    if form == "Cover_Page":
        if not re.search(r"\bPART\s+1\s*:\s*General", text, flags=re.IGNORECASE):
            errors.append("Cover_Page: output does not contain PART 1: General Information")
        if "CAR OWNER PERMISSIONS" in text or "Demonstration Type Repair Level" in text:
            errors.append("Cover_Page: output appears to use a B24 body template")
    return errors


def html_unescape(value: str) -> str:
    return (
        str(value)
        .replace("&lt;", "<")
        .replace("&gt;", ">")
        .replace("&amp;", "&")
        .replace("&quot;", '"')
        .replace("&apos;", "'")
    )


def _write_local_filled_docx(
    *,
    root: Path,
    run_dir: Path,
    filled_dir: Path,
    packets: dict[str, dict[str, Any]],
    low_confidence_threshold: float,
    label_evidence: Mapping[str, list[str]],
    qam_procedure_records: Mapping[str, Mapping[str, str]],
) -> list[dict[str, Any]]:
    work_dir = run_dir / "patch_work"
    guard_dir = run_dir / "structure_guard_reports"
    work_dir.mkdir(parents=True, exist_ok=True)
    guard_dir.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, Any]] = []

    for form, packet in packets.items():
        values, confidences, manual_reasons = _field_values_from_packet(packet)
        load_result = load_exact_approval_bundle_checked(root, form)
        bundle = load_result.bundle
        result: dict[str, Any] = {
            "form_id": form,
            "attempted": False,
            "status": "skipped_no_fill_decisions",
            "approval_map": str(bundle.map_path) if bundle else None,
            "template": str(bundle.template_path) if bundle and bundle.template_path.is_file() else None,
            "filled_docx": None,
            "structure_guard_report": None,
            "structure_guard_passed": False,
            "patched_fields": [],
            "manual_fields": [],
            "manual_field_reasons": {},
            "auto_table_fields": [],
            "auto_table_manual_fields": [],
            "errors": list(load_result.errors),
        }
        if bundle is None:
            result["status"] = "skipped_missing_exact_approval_map"
            results.append(result)
            continue
        if not bundle.template_path.is_file():
            result["status"] = "skipped_missing_template"
            results.append(result)
            continue

        _sanitize_map_values_against_labels(form, bundle, values, confidences, manual_reasons)
        _add_missing_required_map_markers(bundle, values, confidences, manual_reasons)
        if not values:
            results.append(result)
            continue

        fill_manifest = _manifest_cells_for_fill(bundle, values)
        form_label_evidence = _merge_label_evidence(_collect_packet_label_value_evidence(packet), label_evidence)
        auto_fields, auto_manual_fields = _append_table_autofill_cells(
            form=form,
            bundle=bundle,
            fill_manifest=fill_manifest,
            values=values,
            confidences=confidences,
            label_evidence=form_label_evidence,
            qam_procedure_records=qam_procedure_records,
        )
        result["auto_table_fields"] = auto_fields
        result["auto_table_manual_fields"] = sorted(auto_manual_fields)
        # True manual follow-ups: exact-map / decision REVIEW_REQUIRED markers only (never auto_table field_ids).
        map_manual_field_ids = sorted(_manual_fields(values))
        result["manual_fields"] = map_manual_field_ids
        result["manual_field_reasons"] = {fid: manual_reasons.get(fid, "requires manual completion") for fid in map_manual_field_ids}
        if not fill_manifest.get("cells"):
            result["status"] = "skipped_no_matching_manifest_cells"
            result["errors"] = result["errors"] + ["No selected field IDs matched exact map cells or template table value rows."]
            results.append(result)
            continue

        candidate_docx = work_dir / f"{form}_candidate.docx"
        final_docx = filled_dir / f"{form}_filled.docx"
        guard_path = guard_dir / f"{form}_structure_guard_report.json"
        outcome = patch_docx_cells(
            bundle.template_path,
            fill_manifest,
            values,
            candidate_docx,
            field_confidences=confidences,
            required_field_ids=set(),
            low_confidence_threshold=low_confidence_threshold,
            structure_guard_report_path=guard_path,
            approval_map=None,
        )
        safety_errors = _filled_docx_safety_errors(form, candidate_docx, values) if outcome.structure_guard_passed else []
        passed_all_guards = outcome.structure_guard_passed and not safety_errors
        result.update(
            {
                "attempted": True,
                "status": "filled" if passed_all_guards else "discarded_structure_guard_failed",
                "structure_guard_report": str(outcome.structure_guard_report) if outcome.structure_guard_report else None,
                "structure_guard_passed": passed_all_guards,
                "patched_fields": list(outcome.patched_fields),
                "manual_fields": sorted(set(map_manual_field_ids) & set(outcome.patched_fields)),
                "manual_field_reasons": {
                    fid: manual_reasons.get(fid, "requires manual completion")
                    for fid in sorted(set(map_manual_field_ids) & set(outcome.patched_fields))
                },
                "auto_table_fields": sorted(set(auto_fields) & set(outcome.patched_fields)),
                "auto_table_manual_fields": sorted(auto_manual_fields),
                "errors": list(outcome.errors) + safety_errors,
            }
        )
        if passed_all_guards:
            final_docx.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(candidate_docx), final_docx)
            result["filled_docx"] = str(final_docx)
        else:
            try:
                candidate_docx.unlink()
            except FileNotFoundError:
                pass
            guard_payload = json.loads(guard_path.read_text(encoding="utf-8")) if guard_path.is_file() else {}
            result["failure_reason"] = "structure_guard_failed"
            result["structure_guard_errors"] = list(guard_payload.get("errors") or [])
            if safety_errors:
                result["failure_reason"] = "filled_docx_safety_validation_failed"
                result["structure_guard_errors"] = safety_errors
        results.append(result)

    attempted = [item for item in results if item.get("attempted")]
    aggregate = {"pass": all(bool(item.get("structure_guard_passed")) for item in attempted) if attempted else True, "forms": results}
    (run_dir / "structure_guard_report.json").write_text(json.dumps(aggregate, indent=2, sort_keys=True), encoding="utf-8")
    return results


def _run_local_rag_inbox_pipeline(*, root: Path, inbox: Path, out_dir: Path, review_forms: tuple[str, ...] | None, low_confidence_threshold: float) -> InboxPipelineResult:
    inbox = inbox.resolve()
    run_dir = out_dir.resolve()
    raw_dir = run_dir / "raw"
    review_dir = run_dir / "review"
    filled_dir = run_dir / "filled"
    for p in (raw_dir, review_dir, filled_dir):
        p.mkdir(parents=True, exist_ok=True)

    staged_inbox = _stage_inbox_evidence(inbox, run_dir)
    inputs = supported_evidence_files(staged_inbox)
    if not inputs:
        raise FileNotFoundError(f"No supported local evidence files found in inbox: {inbox}")

    forms = normalize_review_forms(review_forms)
    _clear_scoped_filled_docx(filled_dir, forms)
    documents = _augment_docx_table_evidence([extract_local_document(path) for path in inputs])
    label_evidence = _collect_label_value_evidence(documents)
    qam_procedure_records = _extract_cover_qam_procedure_records(documents)
    chunks_by_source = {}
    for doc in documents:
        chunks_by_source[doc.source_file] = [
            enrich_chunk_metadata(
                source_file=doc.source_file,
                source_sha256=doc.sha256,
                extracted_at=str(doc.metadata.get("extracted_at") or ""),
                chunk=chunk,
            )
            for chunk in chunk_text(doc.text)
        ]

    packets = build_form_packets(documents, chunks_by_source, forms, low_confidence_threshold=low_confidence_threshold)
    artifact_index = write_local_artifacts(raw_dir=raw_dir, review_dir=review_dir, documents=documents, chunks_by_source=chunks_by_source, packets=packets)

    current_doc_index = {doc.source_file: doc.sha256 for doc in documents}
    index_path = review_dir / "document_index.json"
    previous_doc_index = json.loads(index_path.read_text(encoding="utf-8")) if index_path.is_file() else {}
    (review_dir / "delta_report.json").write_text(json.dumps(build_delta_report(previous_index=previous_doc_index, current_index=current_doc_index), indent=2, sort_keys=True), encoding="utf-8")
    index_path.write_text(json.dumps(current_doc_index, indent=2, sort_keys=True), encoding="utf-8")
    ensure_clause_map_db(review_dir / "regulation_clause_map.sqlite")
    write_eval_seed(review_dir / "evaluation_seed.json")

    review_json = review_dir / "local_rag_review.json"
    review_md = review_dir / "local_rag_review.md"
    manifest_path = run_dir / "run_manifest.json"
    rag_selection_path = run_dir / "rag_selection_report.json"

    missing_context = [form for form, packet in packets.items() if not packet["retrieved_context"]]
    docx_results = _write_local_filled_docx(
        root=root,
        run_dir=run_dir,
        filled_dir=filled_dir,
        packets=packets,
        low_confidence_threshold=low_confidence_threshold,
        label_evidence=label_evidence,
        qam_procedure_records=qam_procedure_records,
    )
    failed_docx = [item for item in docx_results if item.get("attempted") and not item.get("structure_guard_passed")]
    manual_fields = {str(item["form_id"]): list(item.get("manual_fields") or []) for item in docx_results if item.get("manual_fields")}
    manual_field_reasons = {
        str(item["form_id"]): dict(item.get("manual_field_reasons") or {})
        for item in docx_results
        if item.get("manual_field_reasons")
    }
    auto_table_manual_fields = {
        str(item["form_id"]): list(item.get("auto_table_manual_fields") or [])
        for item in docx_results
        if item.get("auto_table_manual_fields")
    }
    status = "review_required" if missing_context or failed_docx or manual_fields or auto_table_manual_fields else "success"

    canonical_path = run_dir / "canonical_evidence.json"
    trace_path = run_dir / "field_traceability.json"
    canonical_doc = build_canonical_evidence_document(forms=forms, packets=packets, docx_results=docx_results, root=root)
    trace_doc = build_field_traceability_document(forms=forms, packets=packets, docx_results=docx_results, root=root)
    canonical_path.write_text(json.dumps(canonical_doc, indent=2, sort_keys=True), encoding="utf-8")
    trace_path.write_text(json.dumps(trace_doc, indent=2, sort_keys=True), encoding="utf-8")
    (review_dir / "role_views.json").write_text(json.dumps(build_role_views(canonical=canonical_doc, run_logs=artifact_index), indent=2, sort_keys=True), encoding="utf-8")

    review = {
        "generated_at": _utc_now(),
        "status": status,
        "mode": "local_rag_extraction",
        "docupipe_used": False,
        "legacy_adapter_used": False,
        "forms": list(forms),
        "production_scope_forms": list(DEFAULT_REVIEW_FORMS),
        "inputs": [{"source_file": d.source_file, "sha256": d.sha256, "extraction_method": d.extraction_method, "status": "extracted"} for d in documents],
        "form_packets": packets,
        "missing_context_forms": missing_context,
        "decision_summary_by_form": {fid: packets[fid].get("decision_summary") for fid in forms},
        "write_authority": "exact approval maps plus template label/value row autofill; unresolved cells are listed in manifest",
        "docx_generation": docx_results,
        "review_blocked_forms": [],
        "blocking_review_reasons": {},
        "manual_fields": manual_fields,
        "manual_field_reasons": manual_field_reasons,
        "auto_table_manual_fields": auto_table_manual_fields,
        "skipped_review_required": [],
        "structure_guard_failed_forms": [item["form_id"] for item in failed_docx],
        "approval_map_and_fill_errors": [{"form_id": item["form_id"], "errors": list(item.get("errors") or [])} for item in docx_results if item.get("errors")],
        "canonical_evidence": str(canonical_path),
        "field_traceability": str(trace_path),
    }
    review_json.write_text(json.dumps(review, indent=2, sort_keys=True), encoding="utf-8")

    lines = ["# Local RAG Inbox Review", "", f"Run status: **{status}**", f"Generated: {review['generated_at']}", "", "## DOCX writing"]
    for item in docx_results:
        manual = item.get("manual_fields") or []
        suffix = f" ({len(manual)} manual fields)" if manual else ""
        auto_count = len(item.get("auto_table_fields") or [])
        auto_suffix = f", {auto_count} table-row autofill fields" if auto_count else ""
        lines.append(f"- {item['form_id']}: {item['status']}{suffix}{auto_suffix}")
        for field_id, reason in sorted((item.get("manual_field_reasons") or {}).items()):
            lines.append(f"  - {field_id}: {reason}")
    review_md.write_text("\n".join(lines) + "\n", encoding="utf-8")

    rag_selection = {
        "selected_approval_maps": [item.get("approval_map") for item in docx_results if item.get("approval_map")],
        "retrieved_context_used": list(artifact_index["per_form_reviews"].keys()),
        "decision": "best_extracted_values_plus_template_table_autofill_and_manifest_manual_fields",
        "uncertainty": "Remaining unresolved mapped/table fields are listed in run_manifest.json manual_fields.",
    }
    rag_selection_path.write_text(json.dumps(rag_selection, indent=2, sort_keys=True), encoding="utf-8")

    guard_summary_path = run_dir / "structure_guard_report.json"
    guard_summary = json.loads(guard_summary_path.read_text(encoding="utf-8")) if guard_summary_path.is_file() else {"pass": False}
    outputs = [str(canonical_path), str(trace_path), str(review_json), str(review_md), str(rag_selection_path), str(artifact_index["aggregate_review_path"])]
    outputs += [str(item["filled_docx"]) for item in docx_results if item.get("filled_docx")]
    run_manifest = {
        "status": status,
        "mode": "local_rag_extraction",
        "docupipe_used": False,
        "legacy_adapter_used": False,
        "ocr_engine": "local text/PDF extraction with OCR fallback for scanned PDFs",
        "llm_runner": "not required for deterministic local review",
        "embedding_model": _retrieval_summary(packets, forms),
        "vector_db": "none; local TF-IDF / keyword",
        "forms": list(forms),
        "review_json": str(review_json),
        "review_markdown": str(review_md),
        "rag_selection_report": str(rag_selection_path),
        "docx_generation": docx_results,
        "review_blocked_forms": [],
        "blocking_review_reasons": {},
        "manual_fields": manual_fields,
        "manual_field_reasons": manual_field_reasons,
        "auto_table_manual_fields": auto_table_manual_fields,
        "skipped_review_required": [],
        "structure_guard_failed_forms": [item["form_id"] for item in failed_docx],
        "structure_guard_report": str(guard_summary_path),
        "structure_guard_passed": bool(guard_summary.get("pass")),
        "artifacts": artifact_index,
        "outputs": outputs,
    }
    manifest_path.write_text(json.dumps(run_manifest, indent=2, sort_keys=True), encoding="utf-8")

    filled_paths = tuple(Path(str(item["filled_docx"])) for item in docx_results if item.get("filled_docx"))
    first_filled = filled_paths[0] if filled_paths else None
    return InboxPipelineResult(run_dir, manifest_path, review_json, review_md, first_filled, filled_paths, status)


def run_inbox_pipeline(*, root: Path, inbox: Path, out_dir: Path, low_confidence_threshold: float = DEFAULT_LOW_CONFIDENCE_THRESHOLD, review_forms: tuple[str, ...] | None = None) -> InboxPipelineResult:
    return _run_local_rag_inbox_pipeline(root=root, inbox=inbox, out_dir=out_dir, review_forms=review_forms, low_confidence_threshold=low_confidence_threshold)
