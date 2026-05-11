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
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from b2_automation.cell_evidence import DecisionState, FieldDecision
from b2_automation.decision_engine import decide_fields_for_local_packet, summarize_decisions
from b2_automation.local_retrieval_constants import FORM_KEYWORDS
from b2_automation.local_semantic_retrieval import retrieve_chunks_for_form
from b2_automation.paths import resolve_project_root

DEFAULT_REVIEW_FORMS = ("B24_RL2", "B81", "B89", "B90", "Cover_Page")
# B24_RL1 is legacy/sample only; not a valid `b2 inbox --review-forms` value (use legacy commands
# or `b2 inbox --legacy-docupipe` for the DocuPipe adapter).
LEGACY_SAMPLE_FORM_IDS = ("B24_RL1",)
ALLOWED_REVIEW_FORMS = DEFAULT_REVIEW_FORMS
LOCAL_EVIDENCE_EXTENSIONS = (".pdf", ".txt", ".md", ".markdown", ".json", ".csv")
DEFAULT_REQUIRED_SUGGESTION_FIELDS = ("facility_name", "date")
DEFAULT_LOW_CONFIDENCE_THRESHOLD = 0.70

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
        "B24_RL1": "B24_RL1",
        "B24-RL1": "B24_RL1",
        "B24RL1": "B24_RL1",
        "B24 RL1": "B24_RL1",
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
            if form == "B24_RL1":
                raise ValueError(
                    "B24_RL1 is legacy/sample-only and cannot be selected via local inbox --review-forms. "
                    "Use `b2 inbox --legacy-docupipe` with a PDF inbox for the DocuPipe/B24_RL1 adapter, "
                    "or legacy commands `b2 fill-b24-rl1-sample` / `b2 fill-b24-rl1-from-docupipe`."
                )
            if form not in ALLOWED_REVIEW_FORMS:
                allowed = ", ".join(ALLOWED_REVIEW_FORMS)
                raise ValueError(f"Unknown review form {piece!r}. Allowed values: {allowed}")
            if form not in normalized:
                normalized.append(form)
    return tuple(normalized or DEFAULT_REVIEW_FORMS)


def supported_evidence_files(inbox: Path) -> list[Path]:
    return sorted(p for p in inbox.iterdir() if p.is_file() and p.suffix.lower() in LOCAL_EVIDENCE_EXTENSIONS)


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

        pages: list[str] = []
        with fitz.open(path) as doc:
            for page_index, page in enumerate(doc, start=1):
                page_text = page.get_text("text")
                pages.append(f"[page {page_index}]\n{page_text}")
        return "\n\n".join(pages), "local_pymupdf"
    except Exception:
        raw = path.read_bytes()
        return raw.decode("utf-8", errors="ignore"), "local_pdf_bytes_fallback"


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
            chunks.append({"chunk_id": chunk_id, "start": start, "end": end, "text": snippet})
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
    for form in review_forms:
        retrieved, retrieval_method = retrieve_chunks_for_form(form, documents, chunks_by_source)
        suggestions = _field_suggestions(retrieved, form)
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


def _field_suggestions(retrieved: list[dict[str, Any]], form: str = "") -> list[dict[str, Any]]:
    suggestions: list[dict[str, Any]] = []
    patterns: list[tuple[str, str]] = [
        ("facility_name", r"\b(?:facility|company|shop)\s*[:=-]\s*([^\n\r;]{2,80})"),
        ("auditor", r"\b(?:auditor|inspector)\s*[:=-]\s*([^\n\r;]{2,80})"),
        ("date", r"\b(?:date|inspection date)\s*[:=-]\s*([0-9]{4}-[0-9]{2}-[0-9]{2}|[0-9]{1,2}/[0-9]{1,2}/[0-9]{2,4})"),
        ("car_number", r"\b(?:car|car no\.?|car number)\s*[:=-]\s*([A-Z]{2,5}\s*[0-9]{3,8})"),
    ]
    for field in _form_field_definitions(form):
        for alias in _field_aliases(field):
            patterns.append((str(field["field_id"]), rf"\b{re.escape(alias)}\s*[:=-]\s*([^\n\r;]{{2,120}})"))

    seen: set[tuple[str, str]] = set()
    for item in retrieved:
        text = str(item["text"])
        for field, pattern in patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if not match:
                continue
            value = match.group(1).strip()
            value = _trim_before_next_field_marker(value)
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
    return suggestions


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
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            if row.get("form") != normalized:
                continue
            canonical = str(row.get("canonical_path") or "").strip()
            if not canonical:
                continue
            rows.append(
                {
                    "field_id": canonical,
                    "row_label": str(row.get("row_label") or "").strip(),
                    "cell_label": str(row.get("cell_label") or "").strip(),
                    "required": _truthy(row.get("required")),
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
    return value.strip()


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
            lines.append(f"- {item['source_file']} chunk {item['chunk_id']} score {item['score']}: {item['text']}")
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
