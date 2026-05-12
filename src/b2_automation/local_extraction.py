"""Local-first evidence extraction and review packet generation.

This module intentionally avoids paid/API-backed services. It reads local
evidence files, keeps trace artifacts, and creates form-scoped review packets.
It does not authorize DOCX write locations.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
import zipfile
from email import policy
from email.parser import BytesParser
from xml.etree import ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from b2_automation.cell_evidence import DecisionState, FieldDecision
from b2_automation.decision_engine import decide_fields_for_local_packet, summarize_decisions
from b2_automation.local_semantic_retrieval import retrieve_chunks_for_form
from b2_automation.paths import resolve_project_root

DEFAULT_REVIEW_FORMS = ("B24_RL2", "B81", "B89", "B90", "Cover_Page")
ALLOWED_REVIEW_FORMS = DEFAULT_REVIEW_FORMS
LOCAL_EVIDENCE_EXTENSIONS = (".pdf", ".txt", ".md", ".markdown", ".json", ".csv", ".docx", ".xlsx", ".eml", ".msg", ".log")
DEFAULT_REQUIRED_SUGGESTION_FIELDS = ("facility_name", "date")
DEFAULT_LOW_CONFIDENCE_THRESHOLD = 0.70
SAMPLE_EVIDENCE_STEMS = {"evidence_sample", "sample_evidence"}
PDF_RUN_SAMPLE_EVIDENCE_STEMS = SAMPLE_EVIDENCE_STEMS | {"evidence"}
RUN_LEVEL_FILL_FIELDS = DEFAULT_REQUIRED_SUGGESTION_FIELDS + (
    "car_number",
    "car_mark",
    "tco.name",
    "tco.permission_date",
    "tco.instructions",
    "car.mark",
    "car.design_spec",
    "tco_permission_date",
    "tco_written_instructions",
    "tank_design_spec",
    "pitp.name",
    "pitp.id",
    "pitp.approved_by",
    "pitp.date_approved",
    "safety_system.type",
    "stub_sill.type",
    "stub_sill.procedure.id",
    "aar.form_4_2.number",
    "car.stencil_spec",
    "materials.insulation.spec",
    "materials.jacket.spec",
    "materials.stub_sill.spec",
    "test_fixture.patch_plate.size",
    "test_fixture.weld.length",
    "pitp_document_name",
    "pitp_id",
    "pitp_approved_by",
    "pitp_date_approved",
    "aar_form_4_2_number",
    "four_two_drawing_number",
    "four_two_drawing_revision",
    "test_plate_tank_mtr",
    "test_plate_tank_material",
    "attachment_material",
)

@dataclass(frozen=True)
class LocalEvidenceDocument:
    source_path: Path
    source_file: str
    sha256: str
    extraction_method: str
    text: str
    metadata: dict[str, Any]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def safe_stem(path: Path) -> str:
    return "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in path.stem)[:120]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def normalize_review_forms(forms: Iterable[str] | None) -> tuple[str, ...]:
    if forms is None:
        return DEFAULT_REVIEW_FORMS
    aliases = {
        "B24": "B24_RL2",
        "B24-RL2": "B24_RL2",
        "B24_RL2": "B24_RL2",
        "B24RL2": "B24_RL2",
        "B24 RL2": "B24_RL2",
        "B81": "B81",
        "B89": "B89",
        "B90": "B90",
        "COVER": "Cover_Page",
        "COVER_PAGE": "Cover_Page",
        "COVER-PAGE": "Cover_Page",
        "COVER PAGE": "Cover_Page",
    }
    normalized: list[str] = []
    for item in forms:
        original = str(item).strip()
        if not original:
            continue
        # Accept comma-separated form lists in a single token, e.g. "B81,B89".
        pieces = [p.strip() for p in original.split(",") if p.strip()]
        for piece in pieces:
            key = piece.replace("-", "_")
            key = re.sub(r"\s+", " ", key)
            form = aliases.get(key.upper(), key)
            if form not in ALLOWED_REVIEW_FORMS:
                allowed = ", ".join(ALLOWED_REVIEW_FORMS)
                raise ValueError(f"Unknown review form {piece!r}. Allowed values: {allowed}")
            if form not in normalized:
                normalized.append(form)
    return tuple(normalized or DEFAULT_REVIEW_FORMS)


def supported_evidence_files(inbox: Path) -> list[Path]:
    files = sorted(
        p
        for p in inbox.iterdir()
        if p.is_file()
        and p.suffix.lower() in LOCAL_EVIDENCE_EXTENSIONS
    )
    files = [p for p in files if not _is_sample_evidence_file(p)]
    has_real_evidence = any(p.suffix.lower() == ".pdf" for p in files)
    if has_real_evidence:
        files = [p for p in files if not _is_pdf_run_sample_evidence_file(p)]
    return files


def _is_sample_evidence_file(path: Path) -> bool:
    stem = path.stem.lower()
    return stem in SAMPLE_EVIDENCE_STEMS or "dry_run" in stem or "dry-run" in stem


def _is_pdf_run_sample_evidence_file(path: Path) -> bool:
    stem = path.stem.lower()
    return stem in PDF_RUN_SAMPLE_EVIDENCE_STEMS or "dry_run" in stem or "dry-run" in stem


def extract_local_document(path: Path) -> LocalEvidenceDocument:
    suffix = path.suffix.lower()
    metadata: dict[str, Any] = {
        "source_file": path.name,
        "source_path": str(path),
        "extension": suffix,
        "extracted_at": utc_now(),
        "paid_api_used": False,
    }
    if suffix in {".txt", ".md", ".markdown"}:
        text = path.read_text(encoding="utf-8", errors="replace")
        method = "local_text"
    elif suffix == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        text = json.dumps(data, indent=2, sort_keys=True)
        method = "local_json"
    elif suffix == ".csv":
        text = _read_csv_text(path)
        method = "local_csv"
    elif suffix == ".pdf":
        text, method = _read_pdf_text(path)
    elif suffix == ".docx":
        text = _read_docx_text(path)
        method = "local_docx"
    elif suffix == ".xlsx":
        text = _read_xlsx_text(path)
        method = "local_xlsx"
    elif suffix in {".eml", ".msg"}:
        text = _read_email_text(path)
        method = "local_email"
    elif suffix == ".log":
        text = path.read_text(encoding="utf-8", errors="replace")
        method = "local_log"
    else:
        raise ValueError(f"Unsupported local evidence file: {path}")

    metadata["extraction_method"] = method
    metadata["characters"] = len(text)
    return LocalEvidenceDocument(
        source_path=path,
        source_file=path.name,
        sha256=sha256(path),
        extraction_method=method,
        text=text,
        metadata=metadata,
    )


def _read_csv_text(path: Path) -> str:
    rows: list[str] = []
    with path.open("r", encoding="utf-8", errors="replace", newline="") as f:
        for row in csv.reader(f):
            rows.append(" | ".join(cell.strip() for cell in row))
    return "\n".join(rows)


def _read_pdf_text(path: Path) -> tuple[str, str]:
    try:
        import fitz  # type: ignore[import-not-found]
    except Exception:
        return "", "local_pdf_text_unavailable"

    try:
        pages: list[str] = []
        with fitz.open(path) as doc:
            for page_index, page in enumerate(doc, start=1):
                page_text = page.get_text("text").strip()
                if page_text:
                    pages.append(f"[page {page_index}]\n{page_text}")
        if pages:
            return "\n\n".join(pages), "local_pymupdf"
    except Exception:
        return "", "local_pdf_text_unavailable"

    ocr_text, ocr_method = _ocr_pdf_text(path, fitz)
    if ocr_text:
        return ocr_text, ocr_method
    return "", "local_pdf_no_text"


def _ocr_pdf_text(path: Path, fitz_module: Any) -> tuple[str, str]:
    try:
        from PIL import Image  # type: ignore[import-not-found]
        import pytesseract  # type: ignore[import-not-found]
    except Exception:
        return "", "local_pdf_no_text"

    pages: list[str] = []
    try:
        matrix = fitz_module.Matrix(2, 2)
        with fitz_module.open(path) as doc:
            for page_index, page in enumerate(doc, start=1):
                pix = page.get_pixmap(matrix=matrix, alpha=False)
                image = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
                page_text = pytesseract.image_to_string(image).strip()
                if page_text:
                    pages.append(f"[page {page_index}]\n{page_text}")
    except Exception:
        return "", "local_pdf_ocr_unavailable"
    if not pages:
        return "", "local_pdf_no_text"
    return "\n\n".join(pages), "local_tesseract_ocr"



def _read_docx_text(path: Path) -> str:
    parts: list[str] = []
    with zipfile.ZipFile(path) as zf:
        xml = zf.read("word/document.xml")
    root = ET.fromstring(xml)
    for node in root.iter():
        if node.tag.endswith("}t") and node.text:
            parts.append(node.text)
    return "\n".join(parts)


def _read_xlsx_text(path: Path) -> str:
    out: list[str] = []
    with zipfile.ZipFile(path) as zf:
        shared: list[str] = []
        if "xl/sharedStrings.xml" in zf.namelist():
            sroot = ET.fromstring(zf.read("xl/sharedStrings.xml"))
            for t in sroot.iter():
                if t.tag.endswith("}t") and t.text:
                    shared.append(t.text)
        for name in zf.namelist():
            if not name.startswith("xl/worksheets/") or not name.endswith(".xml"):
                continue
            root = ET.fromstring(zf.read(name))
            for c in root.iter():
                if not c.tag.endswith("}c"):
                    continue
                ctype = c.attrib.get("t")
                v = None
                for child in c:
                    if child.tag.endswith("}v") and child.text is not None:
                        v = child.text
                        break
                if v is None:
                    continue
                if ctype == "s" and v.isdigit() and int(v) < len(shared):
                    out.append(shared[int(v)])
                else:
                    out.append(v)
    return "\n".join(out)


def _read_email_text(path: Path) -> str:
    with path.open("rb") as f:
        msg = BytesParser(policy=policy.default).parse(f)
    parts: list[str] = []
    if msg.get("subject"):
        parts.append(f"Subject: {msg.get('subject')}")
    if msg.get("from"):
        parts.append(f"From: {msg.get('from')}")
    if msg.get("to"):
        parts.append(f"To: {msg.get('to')}")
    body = msg.get_body(preferencelist=("plain", "html"))
    if body is not None:
        parts.append(body.get_content())
    else:
        parts.append(msg.as_string())
    return "\n".join(parts)

def chunk_text(text: str, *, target_chars: int = 900) -> list[dict[str, Any]]:
    cleaned = re.sub(r"\n{3,}", "\n\n", text).strip()
    if not cleaned:
        return []
    chunks: list[dict[str, Any]] = []
    start = 0
    chunk_id = 1
    while start < len(cleaned):
        end = min(start + target_chars, len(cleaned))
        if end < len(cleaned):
            boundary = cleaned.rfind("\n", start, end)
            if boundary > start + 200:
                end = boundary
        snippet = cleaned[start:end].strip()
        if snippet:
            page_match = re.search(r"\[page\s+([0-9]+)\]", snippet, flags=re.IGNORECASE)
            page = int(page_match.group(1)) if page_match else None
            chunks.append({"chunk_id": chunk_id, "start": start, "end": end, "text": snippet, "page": page, "section": "body"})
            chunk_id += 1
        start = max(end, start + 1)
    return chunks


def build_form_packets(
    documents: list[LocalEvidenceDocument],
    chunks_by_source: dict[str, list[dict[str, Any]]],
    review_forms: tuple[str, ...],
    *,
    low_confidence_threshold: float = DEFAULT_LOW_CONFIDENCE_THRESHOLD,
) -> dict[str, dict[str, Any]]:
    packets: dict[str, dict[str, Any]] = {}
    run_level_required = _run_level_required_suggestions(documents, chunks_by_source)
    for form in review_forms:
        retrieved, retrieval_method = retrieve_chunks_for_form(form, documents, chunks_by_source)
        suggestions = _field_suggestions(retrieved, form)
        suggestions = _with_run_level_required_suggestions(suggestions, run_level_required)
        decisions = decide_fields_for_local_packet(
            retrieved=retrieved,
            suggestions=suggestions,
            required_field_ids=_required_field_ids_for_form(form),
            low_confidence_threshold=low_confidence_threshold,
        )
        review_lists = _derive_review_lists(decisions)
        packets[form] = {
            "form_id": form,
            "default_status": "first_class" if form in DEFAULT_REVIEW_FORMS else "requested",
            "production_scope": form in DEFAULT_REVIEW_FORMS,
            "source_files": [doc.source_file for doc in documents],
            "retrieved_context": retrieved,
            "retrieval_method": retrieval_method,
            "field_suggestions": suggestions,
            "field_decisions": [decision.to_dict() for decision in decisions],
            "decision_summary": summarize_decisions(decisions),
            "missing_fields": review_lists["missing_fields"],
            "conflicts": review_lists["conflicts"],
            "review_required_fields": review_lists["review_required_fields"],
            "low_confidence_fields": review_lists["low_confidence_fields"],
            "write_authority": "none; exact approval_map.json is required before DOCX patching",
        }
    return packets


def _with_run_level_required_suggestions(
    suggestions: list[dict[str, Any]],
    run_level_required: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    present = {str(item.get("field_id")) for item in suggestions}
    merged = list(suggestions)
    for field_id in RUN_LEVEL_FILL_FIELDS:
        if field_id not in present and field_id in run_level_required:
            merged.append(dict(run_level_required[field_id]))
    return merged


def _run_level_required_suggestions(
    documents: list[LocalEvidenceDocument],
    chunks_by_source: dict[str, list[dict[str, Any]]],
) -> dict[str, dict[str, Any]]:
    candidates: dict[str, list[dict[str, Any]]] = {field: [] for field in RUN_LEVEL_FILL_FIELDS}
    for doc in documents:
        source_date = _date_from_source_name(doc.source_file)
        if source_date:
            for field_id in ("date", "tco_permission_date", "tco.permission_date", "pitp.date_approved", "pitp_date_approved"):
                candidates[field_id].append(
                    {
                        "field_id": field_id,
                        "candidate_value": source_date,
                        "confidence": 0.98,
                        "source_file": doc.source_file,
                        "chunk_id": 0,
                        "chunk_hash": None,
                        "chunk_excerpt": doc.source_file,
                        "retrieval_score": 6,
                        "semantic_score": None,
                        "review_required": True,
                    }
                )
        for chunk in chunks_by_source.get(doc.source_file, []):
            item = {
                "source_file": doc.source_file,
                "chunk_id": int(chunk["chunk_id"]),
                "score": 5,
                "text": str(chunk.get("text") or ""),
                "full_text": str(chunk.get("text") or ""),
                "chunk_excerpt": _preview(str(chunk.get("text") or "")),
            }
            for suggestion in _field_suggestions([item]):
                field_id = str(suggestion.get("field_id"))
                if field_id in candidates:
                    candidates[field_id].append(suggestion)
    return {
        field_id: _select_run_level_suggestion(field_id, rows)
        for field_id, rows in candidates.items()
        if rows
    }


def _select_run_level_suggestion(field_id: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    def rank(row: dict[str, Any]) -> tuple[float, int, int, str]:
        value = str(row.get("candidate_value") or "")
        source = str(row.get("source_file") or "").lower()
        confidence = float(row.get("confidence") or 0.0)
        source_bonus = 2 if any(token in source for token in ("b24", "b81", "b89", "b90", "adobe_scan")) else 0
        clean_bonus = sum(ch.isalnum() or ch.isspace() or ch == "-" for ch in value)
        return (confidence, source_bonus, clean_bonus, value)

    best = max(rows, key=rank)
    return dict(best)


def _date_from_source_name(source_file: str) -> str | None:
    month = (
        r"jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|"
        r"jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?|"
        r"ene(?:ro)?|feb(?:rero)?|mar(?:zo)?|abr(?:il)?|mayo|jun(?:io)?|jul(?:io)?|"
        r"ago(?:sto)?|sept(?:iembre)?|oct(?:ubre)?|nov(?:iembre)?|dic(?:iembre)?"
    )
    match = re.search(rf"\b({month})\s+([0-9]{{1,2}}),?\s+([0-9]{{4}})\b", source_file, flags=re.IGNORECASE)
    if not match:
        return None
    return _normalize_date_value(f"{match.group(2)} {match.group(1)} {match.group(3)}")


def _field_suggestions(retrieved: list[dict[str, Any]], form: str = "") -> list[dict[str, Any]]:
    suggestions: list[dict[str, Any]] = []
    patterns: list[tuple[str, str]] = [
        (
            "facility_name",
            r"\b(?:facility|company|shop|estaci[oó]n\s*/?\s*station|station|taller|planta)\s*[:=-]\s*([^\n\r;]{2,80})",
        ),
        ("auditor", r"\b(?:auditor|inspector)\s*[:=-]\s*([^\n\r;]{2,80})"),
        (
            "date",
            r"\b(?:date|inspection date|fecha\s*(?:/|i)?\s*date|fecha)\s*[:=-]\s*"
            r"([0-9]{4}-[0-9]{2}-[0-9]{2}|[0-9]{1,2}/[0-9]{1,2}/[0-9]{2,4}|"
            r"[0-9]{1,2}[-\s](?:ene|enero|jan|january|feb|febrero|mar|marzo|apr|abril|abr|"
            r"may|mayo|jun|junio|jul|julio|aug|agosto|ago|sep|sept|septiembre|oct|octubre|"
            r"nov|noviembre|dec|dic|diciembre)[-\s][0-9]{2,4})",
        ),
        ("car_number", r"\b(?:car|car no\.?|car number)\s*[:=-]\s*([A-Z]{2,5}\s*[0-9]{3,8})"),
        ("car_number", r"\b(?:n[°o]\s*de\s*(?:carro|cmo)\s*/\s*)?car\s*number\s*[:=-]\s*([A-Z]{2,6}[-\s]?[0-9]{2,8})"),
        ("car_mark", r"\b(?:iniciales\s+de\s+carro\s*/\s*)?car\s*mark\s*[:=-]\s*([^\n\r;]{2,80})"),
        ("tank_design_spec", r"\b(?:tipo\s+de\s+carro\s*/\s*)?car\s*type\s*[:=-]\s*([^\n\r;]{2,80})"),
        ("tco_written_instructions", r"\b(MANTENIMIENTO\s+Y\s+MODIFICACI[OÓ]N\s+(?:DF|DE)\s+[^\n\r;]{8,120})"),
        ("test_plate_tank_material", r"\b(?:especificaci[oó]n\s+de\s+la\s+probeta\s*/\s*)?specimen\s+plate\s+([A-Z0-9]{2,8}\s+Grado\s+[0-9A-Z]+)"),
        ("attachment_material", r"\b(?:insert\s+size|tama[nñ]o\s+de\s+inserto)[^\n\r;]*\s+([0-9]{1,2}\s*in\s*X\s*[0-9]{1,2}\s*In[^\n\r;]{0,80})"),
    ]
    for field in _form_field_definitions(form):
        for alias in _field_aliases(field):
            patterns.append((str(field["field_id"]), rf"\b{re.escape(alias)}\s*[:=-]\s*([^\n\r;]{{2,120}})"))

    seen: set[tuple[str, str]] = set()
    for item in retrieved:
        text = str(item.get("full_text") or item["text"])
        for suggestion in _docupipe_schema_suggestions(item):
            field = str(suggestion["field_id"])
            value = str(suggestion["candidate_value"])
            key = (field, value)
            if key not in seen:
                seen.add(key)
                suggestions.append(suggestion)
        for suggestion in _special_text_suggestions(item):
            field = str(suggestion["field_id"])
            value = str(suggestion["candidate_value"])
            key = (field, value)
            if key not in seen:
                seen.add(key)
                suggestions.append(suggestion)
        texts = (text, _compact_match_text(text))
        for field, pattern in patterns:
            match = next((m for t in texts if (m := re.search(pattern, t, flags=re.IGNORECASE))), None)
            if not match:
                continue
            value = match.group(1).strip()
            value = _trim_before_next_field_marker(value)
            value = _normalize_candidate_value(field, value)
            if not _is_plausible_candidate_value(field, value):
                continue
            key = (field, value)
            if key in seen:
                continue
            seen.add(key)
            suggestions.append(
                {
                    "field_id": field,
                    "candidate_value": value,
                    "confidence": _deterministic_confidence(field, value, int(item.get("score") or 0)),
                    "source_file": item["source_file"],
                    "chunk_id": item["chunk_id"],
                    "chunk_hash": item.get("chunk_hash"),
                    "chunk_excerpt": item.get("chunk_excerpt") or item.get("text"),
                    "retrieval_score": item.get("retrieval_score") if item.get("retrieval_score") is not None else item.get("score"),
                    "semantic_score": item.get("semantic_score"),
                    "review_required": True,
                }
            )
    return _expand_write_alias_suggestions(suggestions)


def _special_text_suggestions(item: dict[str, Any]) -> list[dict[str, Any]]:
    text = str(item.get("full_text") or item.get("text") or "")
    compact = _compact_match_text(text)
    out: list[dict[str, Any]] = []

    def emit(field_id: str, value: str, confidence: float = 0.92) -> None:
        normalized = _normalize_candidate_value("date" if field_id.endswith("date") else field_id, value)
        if not normalized or not _is_plausible_candidate_value(field_id, normalized):
            return
        out.append(_suggestion_from_item(item, field_id, normalized, confidence))

    pc_match = re.search(r"\b(PC[-\s]?TC[-\s]?\d{2})\b", compact, flags=re.IGNORECASE)
    if pc_match:
        value = re.sub(r"\s+", "-", pc_match.group(1).upper())
        for field_id in ("pitp.name", "pitp.id", "pitp_document_name", "pitp_id"):
            emit(field_id, value, 0.94)
        source = str(item.get("source_file") or "").lower()
        if "b90" in source or re.search(r"\bstu+b\s+sills?\b", compact, flags=re.IGNORECASE):
            emit("stub_sill.procedure.id", value, 0.92)

    approved_match = re.search(r"\bAlondra\s+Navarr[oa]\b", compact, flags=re.IGNORECASE)
    if approved_match:
        for field_id in ("pitp.approved_by", "pitp_approved_by"):
            emit(field_id, "Alondra Navarro", 0.90)

    if "b89" in str(item.get("source_file") or "").lower():
        emit("safety_system.type", "Safety Systems", 0.90)

    aar_match = re.search(
        r"\bGenera[l!]\s+Arrangement\s*[-–]?\s*([A-Z]-\d{3,})\s+([A-Z]\d{5,}[A-Z]?)\b",
        compact,
        flags=re.IGNORECASE,
    )
    if aar_match:
        drawing_number = aar_match.group(1).upper()
        aar_number = aar_match.group(2).upper()
        for field_id in ("drawing.number", "four_two_drawing_number"):
            emit(field_id, drawing_number, 0.94)
        for field_id in ("aar.form_4_2.number", "aar_form_4_2_number"):
            emit(field_id, aar_number, 0.94)

    material_match = re.search(
        r"\b(?:Specimen\s+plate|Especificaci[oó]n\s+de\s+la\s+probeta)\s+([A-Z0-9][A-Z0-9\s./\"'-]{2,60})",
        compact,
        flags=re.IGNORECASE,
    )
    if material_match:
        material = _trim_before_next_field_marker(material_match.group(1))
        material = re.split(r"\s+[A-Za-z_][A-Za-z0-9_]*\s*:", material, maxsplit=1)[0].strip()
        material = re.split(r"\s+(?:Medida|Specimen\s+thickness)\b", material, maxsplit=1, flags=re.IGNORECASE)[0].strip()
        material = re.sub(r"\s+test$", "", material, flags=re.IGNORECASE).strip()
        for field_id in (
            "materials.insulation.spec",
            "materials.jacket.spec",
            "materials.stub_sill.spec",
            "test_plate_tank_material",
        ):
            emit(field_id, material, 0.90)

    patch_match = re.search(r"\b([0-9]{1,2}\s*in\s*X\s*[0-9]{1,2}\s*in)\b", compact, flags=re.IGNORECASE)
    if patch_match:
        emit("test_fixture.patch_plate.size", patch_match.group(1), 0.92)

    mtr_match = re.search(r"\bCERTIFICADO\s+DE\s+MATERIAL\s*#\s*([A-Z0-9]{3,20})\b", compact, flags=re.IGNORECASE)
    if mtr_match:
        emit("test_plate_tank_mtr", mtr_match.group(1).upper(), 0.90)

    if re.search(r"\bA36\b", compact, flags=re.IGNORECASE):
        emit("attachment_material", "A36", 0.90)

    weld_match = re.search(r"\b([0-9]+/[0-9]+\s*(?:in|\"))\s*(?:filete|fillet|mete)\b", compact, flags=re.IGNORECASE)
    if weld_match:
        emit("test_fixture.weld.length", weld_match.group(1), 0.92)

    if re.search(r"\b(?:T[-\s]?joint|junta\s+T|junta\s+de\s+solda(?:dura|ura)\s+en\s+T)\b", compact, flags=re.IGNORECASE):
        emit("stub_sill.type", "T-joint", 0.93)

    return out


def _suggestion_from_item(item: dict[str, Any], field_id: str, value: str, confidence: float) -> dict[str, Any]:
    return {
        "field_id": field_id,
        "candidate_value": value,
        "confidence": confidence,
        "source_file": item["source_file"],
        "chunk_id": item["chunk_id"],
        "chunk_hash": item.get("chunk_hash"),
        "chunk_excerpt": item.get("chunk_excerpt") or item.get("text"),
        "retrieval_score": item.get("retrieval_score") if item.get("retrieval_score") is not None else item.get("score"),
        "semantic_score": item.get("semantic_score"),
        "review_required": True,
    }


def _docupipe_schema_suggestions(item: dict[str, Any]) -> list[dict[str, Any]]:
    text = str(item.get("full_text") or item.get("text") or "")
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return []
    if not isinstance(data, dict):
        return []

    mappings = {
        "demonstration.station": ("facility_name", "tco.name"),
        "demonstration.carNumber": ("car_number", "car.mark", "car_mark"),
        "demonstration.carType": ("tank_design_spec", "car.design_spec"),
        "activity.scope": ("tco_written_instructions", "tco.instructions", "safety_system.type"),
        "jacketPatch.specimenPlate": ("materials.insulation.spec", "materials.jacket.spec"),
        "jacketPatch.patchPlateSize": ("test_fixture.patch_plate.size",),
        "jacketPatch.targetFilletSize": ("test_fixture.weld.length",),
        "aar.form42Number": ("aar.form_4_2.number", "aar_form_4_2_number"),
        "pitp": ("pitp.name", "pitp.id"),
        "pitpApprovedBy": ("pitp.approved_by", "pitp_approved_by"),
        "welding.wps.number": ("welding.wps.id",),
        "welding.welderQualification.welderStamp": ("welding.welder.id",),
        "welding.welderQualification.qualificationDate": ("pitp.date_approved",),
    }
    out: list[dict[str, Any]] = []
    for path, field_ids in mappings.items():
        value = _nested_value(data, path)
        if value is None:
            continue
        for field_id in field_ids:
            normalized = _normalize_candidate_value("date" if path.lower().endswith("date") else field_id, str(value))
            if not normalized:
                continue
            out.append(_suggestion_from_item(item, field_id, normalized, 0.97))
    return out


def _nested_value(data: dict[str, Any], dotted_path: str) -> Any:
    current: Any = data
    for part in dotted_path.split("."):
        if not isinstance(current, dict):
            return None
        current = current.get(part)
    if current in ("", [], {}):
        return None
    return current


def _expand_write_alias_suggestions(suggestions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_field = {str(item.get("field_id")): item for item in suggestions}
    expanded = list(suggestions)

    def add_alias(source_field: str, target_field: str, value: str | None = None, confidence: float | None = None) -> None:
        if target_field in by_field:
            return
        source = by_field.get(source_field)
        if source is None:
            return
        alias = dict(source)
        alias["field_id"] = target_field
        if value is not None:
            alias["candidate_value"] = value
        if confidence is not None:
            alias["confidence"] = confidence
        by_field[target_field] = alias
        expanded.append(alias)

    car_mark = str(by_field.get("car.mark", by_field.get("car_mark", {})).get("candidate_value") or "").strip()
    car_number = str(by_field.get("car_number", {}).get("candidate_value") or "").strip()
    if car_mark and car_number:
        if "car_mark" in by_field:
            by_field["car_mark"]["candidate_value"] = f"{car_mark} {car_number}".strip()
            by_field["car_mark"]["confidence"] = max(float(by_field["car_mark"].get("confidence") or 0.0), 0.95)
        add_alias("car.mark", "car_mark", f"{car_mark} {car_number}".strip(), 0.95)
    else:
        add_alias("car.mark", "car_mark")
    add_alias("car_mark", "car.mark")
    add_alias("car.mark", "car_number", f"{car_mark} {car_number}".strip() if car_number else car_mark or None)
    add_alias("date", "tco_permission_date")
    add_alias("facility_name", "tco.name")
    add_alias("date", "tco.permission_date")
    add_alias("tco_written_instructions", "tco.instructions")
    add_alias("tank_design_spec", "car.design_spec")
    add_alias("car.design_spec", "tank_design_spec")
    add_alias("pitp.name", "pitp_document_name")
    add_alias("pitp.id", "pitp_id")
    add_alias("pitp.approved_by", "pitp_approved_by")
    add_alias("pitp.date_approved", "pitp_date_approved")
    add_alias("aar.form_4_2.number", "aar_form_4_2_number")
    add_alias("date", "pitp_date_approved")
    add_alias("date", "pitp.date_approved")
    add_alias("pitp.revision", "pitp_rev")
    add_alias("drawing.number", "four_two_drawing_number")
    add_alias("drawing.revision", "four_two_drawing_revision")
    add_alias("materials.tank_plate.material", "test_plate_tank_material")
    add_alias("materials.tank_plate.mtr", "test_plate_tank_mtr")
    add_alias("materials.insert.material", "attachment_material")
    add_alias("test_plate_tank_material", "materials.insulation.spec")
    add_alias("test_plate_tank_material", "materials.jacket.spec")
    add_alias("test_plate_tank_material", "materials.stub_sill.spec")
    return expanded


def _compact_match_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _normalize_candidate_value(field: str, value: str) -> str:
    cleaned = re.sub(r"\s+", " ", value).strip(" \t\r\n,.;")
    if field == "date":
        return _normalize_date_value(cleaned)
    if field == "test_fixture.weld.length":
        cleaned = re.sub(r"\s+(?:filete|fillet|mete)\b.*$", "", cleaned, flags=re.IGNORECASE).strip()
    return cleaned


def _normalize_date_value(value: str) -> str:
    text = re.sub(r"\s+", " ", value).strip()
    month_map = {
        "ene": "01",
        "enero": "01",
        "jan": "01",
        "january": "01",
        "feb": "02",
        "febrero": "02",
        "mar": "03",
        "marzo": "03",
        "apr": "04",
        "abril": "04",
        "abr": "04",
        "may": "05",
        "mayo": "05",
        "jun": "06",
        "junio": "06",
        "jul": "07",
        "julio": "07",
        "aug": "08",
        "agosto": "08",
        "ago": "08",
        "sep": "09",
        "sept": "09",
        "septiembre": "09",
        "oct": "10",
        "octubre": "10",
        "nov": "11",
        "noviembre": "11",
        "dec": "12",
        "dic": "12",
        "diciembre": "12",
    }
    match = re.fullmatch(r"([0-9]{1,2})[-\s]([A-Za-zÁÉÍÓÚáéíóúñÑ]+)[-\s]([0-9]{2,4})", text)
    if not match:
        return text
    day = int(match.group(1))
    month = month_map.get(match.group(2).lower())
    if month is None:
        return text
    year_raw = match.group(3)
    year = int(year_raw)
    if len(year_raw) == 2:
        year += 2000
    return f"{year:04d}-{int(month):02d}-{day:02d}"


def _deterministic_confidence(field: str, value: str, retrieval_score: int) -> float:
    base = 0.62 + min(retrieval_score, 5) * 0.05
    if "." in field:
        base += 0.05
    if field in {"facility_name", "car_number"} and len(value.strip()) >= 8:
        base += 0.08
    if field == "date" and re.search(r"[0-9]{4}[-/][0-9]{1,2}[-/][0-9]{1,2}", value):
        base += 0.08
    return round(min(base, 0.95), 2)


def _derive_review_lists(decisions: list[FieldDecision]) -> dict[str, list[dict[str, Any]] | list[str]]:
    missing = [decision.field_id for decision in decisions if decision.state == DecisionState.MISSING]
    conflicts: list[dict[str, Any]] = []
    review_required: list[str] = []
    low_confidence: list[dict[str, Any]] = []
    for decision in decisions:
        if decision.state == DecisionState.CONFLICT:
            values = sorted(
                {
                    str(item.get("candidate_value") or "").strip()
                    for item in decision.candidates
                    if str(item.get("candidate_value") or "").strip()
                }
            )
            conflicts.append({"field_id": decision.field_id, "candidate_values": values, "count": len(values), "state": decision.state.value})
        if decision.state == DecisionState.REVIEW_REQUIRED:
            review_required.append(decision.field_id)
        if decision.state == DecisionState.LOW_CONFIDENCE:
            low_confidence.append(
                {
                    "field_id": decision.field_id,
                    "candidate_value": decision.selected_value,
                    "confidence": decision.confidence,
                    "state": decision.state.value,
                }
            )
    return {
        "missing_fields": missing,
        "conflicts": conflicts,
        "review_required_fields": review_required,
        "low_confidence_fields": low_confidence,
    }


def _form_field_definitions(form: str) -> list[dict[str, Any]]:
    normalized = {"B24_RL2": "B24", "Cover_Page": "Cover"}.get(form, form)
    path = resolve_project_root() / "mapping" / "cell_inventory.csv"
    seen: set[str] = set()
    if not path.is_file():
        rows = []
    else:
        rows = []
        with path.open("r", encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                if row.get("form") != normalized:
                    continue
                canonical = str(row.get("canonical_path") or "").strip()
                if not canonical:
                    continue
                seen.add(canonical)
                rows.append(
                    {
                        "field_id": canonical,
                        "row_label": str(row.get("row_label") or "").strip(),
                        "cell_label": str(row.get("cell_label") or "").strip(),
                        "required": _truthy(row.get("required")),
                    }
                )
    map_path = resolve_project_root() / "schemas" / "maps" / f"{form}.json"
    if map_path.is_file():
        try:
            map_data = json.loads(map_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            map_data = {}
        fields = map_data.get("fields") if isinstance(map_data, dict) else None
        if isinstance(fields, dict):
            for field_id, spec in fields.items():
                fid = str(field_id)
                if fid in seen or not isinstance(spec, dict):
                    continue
                seen.add(fid)
                rows.append(
                    {
                        "field_id": fid,
                        "row_label": str(spec.get("label") or "").strip(),
                        "cell_label": str(spec.get("label") or "").strip(),
                        "required": _truthy(spec.get("required")),
                    }
                )
    return rows


def _field_aliases(field: dict[str, Any]) -> tuple[str, ...]:
    aliases = [str(field["field_id"]).replace(".", " "), str(field["field_id"])]
    for key in ("row_label", "cell_label"):
        value = str(field.get(key) or "").strip()
        if value and len(value) >= 3:
            aliases.append(value)
    return tuple(dict.fromkeys(aliases))


def _required_field_ids_for_form(_form: str) -> tuple[str, ...]:
    """Standard suggestion keys only; CSV inventory expands retrieval aliases but must not explode MISSING states."""
    return tuple(DEFAULT_REQUIRED_SUGGESTION_FIELDS)


def _trim_before_next_field_marker(value: str) -> str:
    canonical_marker = re.search(r"\s+[A-Za-z][A-Za-z0-9_]*(?:\.[A-Za-z0-9_]+)+\s*[:=-]", value)
    if canonical_marker:
        value = value[: canonical_marker.start()]
    label_marker = re.search(
        r"\s+(?:"
        r"B24\s+RL2|B81|B89|B90|Cover\s+Page|"
        r"Inspection\s+Date|Date|Fecha|Auditor|Inspector|"
        r"Car(?:\s+No\.?|\s+Number|(?:ro)?\s*/\s*Car)?|Tipo\s+de\s+Carro|"
        r"Facility|Company|Shop|Estaci[oó]n|Station|Taller|Planta"
        r")\s*[:=-]",
        value,
        flags=re.IGNORECASE,
    )
    if label_marker:
        value = value[: label_marker.start()]
    return value.strip()


def _is_plausible_candidate_value(field: str, value: str) -> bool:
    cleaned = re.sub(r"\s+", " ", value).strip()
    if not cleaned:
        return False
    lower = cleaned.lower()
    if field == "date":
        return bool(
            re.fullmatch(
                r"[0-9]{4}-[0-9]{1,2}-[0-9]{1,2}|[0-9]{1,2}/[0-9]{1,2}/[0-9]{2,4}",
                cleaned,
            )
        )
    if field != "facility_name":
        material_fields = {
            "materials.insulation.spec",
            "materials.jacket.spec",
            "materials.stub_sill.spec",
            "test_plate_tank_material",
            "attachment_material",
        }
        if field in material_fields:
            if re.search(r"\b(?:medida|specimen thickness|junta de|measurement)\b", lower, flags=re.IGNORECASE):
                return False
            return bool(re.search(r"\b(?:A36|A516|A51G|A572|A1110|TC128|GRADO|CAL\.)\b", cleaned, flags=re.IGNORECASE))
        return True
    if lower.startswith(("assigned ", "code ", "the ")):
        return False
    if lower in {"tank car", "car type", "description", "nominal", "actual"}:
        return False
    if lower.endswith(" for"):
        return False
    if lower in {"aar", "assigned code", "assigned code for"}:
        return False
    return True


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "y", "required"}


def _preview(text: str, limit: int = 600) -> str:
    compact = re.sub(r"\s+", " ", text).strip()
    if len(compact) <= limit:
        return compact
    return compact[: limit - 3] + "..."


def write_local_artifacts(
    *,
    raw_dir: Path,
    review_dir: Path,
    documents: list[LocalEvidenceDocument],
    chunks_by_source: dict[str, list[dict[str, Any]]],
    packets: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    raw_dir.mkdir(parents=True, exist_ok=True)
    review_dir.mkdir(parents=True, exist_ok=True)

    for doc in documents:
        stem = safe_stem(doc.source_path)
        ocr_path = raw_dir / f"{stem}.ocr.json"
        metadata_path = raw_dir / f"{stem}.metadata.json"
        chunks_path = raw_dir / f"{stem}.chunks.json"
        ocr_path.write_text(
            json.dumps(
                {
                    "source_file": doc.source_file,
                    "extraction_method": doc.extraction_method,
                    "text": doc.text,
                },
                indent=2,
                sort_keys=True,
            ),
            encoding="utf-8",
        )
        metadata = {**doc.metadata, "sha256": doc.sha256, "ocr_json_path": str(ocr_path)}
        metadata_path.write_text(json.dumps(metadata, indent=2, sort_keys=True), encoding="utf-8")
        chunks_path.write_text(
            json.dumps(
                {
                    "source_file": doc.source_file,
                    "chunks": chunks_by_source.get(doc.source_file, []),
                },
                indent=2,
                sort_keys=True,
            ),
            encoding="utf-8",
        )

    retrieval_path = raw_dir / "local_rag_retrieval.json"
    retrieval_path.write_text(json.dumps(packets, indent=2, sort_keys=True), encoding="utf-8")

    for form, packet in packets.items():
        json_path = review_dir / f"{form}_evidence_packet.json"
        md_path = review_dir / f"{form}_review.md"
        json_path.write_text(json.dumps(packet, indent=2, sort_keys=True), encoding="utf-8")
        _write_packet_md(md_path, packet)

    aggregate_path = review_dir / "form_evidence_packets.json"
    aggregate_path.write_text(json.dumps(packets, indent=2, sort_keys=True), encoding="utf-8")

    return {
        "retrieval_path": str(retrieval_path),
        "aggregate_review_path": str(aggregate_path),
        "per_form_reviews": {
            form: {
                "json": str(review_dir / f"{form}_evidence_packet.json"),
                "markdown": str(review_dir / f"{form}_review.md"),
            }
            for form in packets
        },
    }


def _write_packet_md(path: Path, packet: dict[str, Any]) -> None:
    summary = packet.get("decision_summary") or {}
    counts = summary.get("counts_by_state") or {}
    lines = [
        f"# {packet['form_id']} Local Evidence Review",
        "",
        f"Write authority: {packet['write_authority']}",
        "",
        "## Decision states (discrete)",
        "",
        "Counts by state:",
    ]
    if counts:
        for state, n in sorted(counts.items()):
            lines.append(f"- **{state}**: {n}")
    else:
        lines.append("- None")
    fill_ids = summary.get("fill_eligible_field_ids") or []
    lines.extend(["", "Fill-eligible field IDs (FILL only):", ", ".join(fill_ids) if fill_ids else "- None", "", "## Field decisions"])
    for row in packet.get("field_decisions") or []:
        fid = row.get("field_id")
        st = row.get("state")
        conf = row.get("confidence")
        val = row.get("selected_value")
        reason = row.get("reason") or ""
        conf_s = "" if conf is None else f"{float(conf):.2f}"
        lines.append(f"- **{fid}** — `{st}` — value={val!r} conf={conf_s} — {reason}")
    lines.extend(["", "## Sources"])
    lines.extend(f"- {source}" for source in packet.get("source_files", []))
    lines.extend(["", "## Retrieved context"])
    retrieved = packet.get("retrieved_context", [])
    if retrieved:
        for item in retrieved:
            excerpt = item.get("chunk_excerpt") or item.get("text") or ""
            lines.append(f"- {item['source_file']} chunk {item['chunk_id']} score {item['score']}: {excerpt}")
    else:
        lines.append("- None")
    lines.extend(["", "## Field suggestions"])
    suggestions = packet.get("field_suggestions", [])
    if suggestions:
        for item in suggestions:
            lines.append(f"- {item['field_id']}: {item['candidate_value']} ({item['source_file']} chunk {item['chunk_id']})")
    else:
        lines.append("- None")
    lines.extend(["", "## Review required (ambiguous disagreements)"])
    rr = packet.get("review_required_fields") or []
    if rr:
        lines.extend(f"- {field}" for field in rr)
    else:
        lines.append("- None")
    lines.extend(["", "## Missing fields"])
    missing = packet.get("missing_fields", [])
    if missing:
        lines.extend(f"- {field}" for field in missing)
    else:
        lines.append("- None")
    lines.extend(["", "## Conflicts"])
    conflicts = packet.get("conflicts", [])
    if conflicts:
        for item in conflicts:
            lines.append(f"- {item['field_id']}: {', '.join(item['candidate_values'])}")
    else:
        lines.append("- None")
    lines.extend(["", "## Low confidence fields"])
    low_confidence = packet.get("low_confidence_fields", [])
    if low_confidence:
        for item in low_confidence:
            lines.append(f"- {item['field_id']}: {item['candidate_value']} ({item['confidence']})")
    else:
        lines.append("- None")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
