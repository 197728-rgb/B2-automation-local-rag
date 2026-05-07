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

DEFAULT_REVIEW_FORMS = ("B24_RL2", "B81", "B89", "B90", "Cover_Page")
LOCAL_EVIDENCE_EXTENSIONS = (".pdf", ".txt", ".md", ".markdown", ".json", ".csv")

FORM_KEYWORDS: dict[str, tuple[str, ...]] = {
    "B24_RL2": ("b24", "b-24", "rl2", "repair level 2", "objective evidence"),
    "B81": ("b81", "b-81", "b81/b24", "stub sill", "only"),
    "B89": ("b89", "b-89", "insulation", "test plate"),
    "B90": ("b90", "b-90", "rls", "release", "return to service"),
    "Cover_Page": ("cover", "cover page", "aar", "audit", "facility", "company"),
}


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
        key = str(item).strip().replace("-", "_")
        form = aliases.get(key.upper(), key)
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
) -> dict[str, dict[str, Any]]:
    packets: dict[str, dict[str, Any]] = {}
    for form in review_forms:
        retrieved = _retrieve_for_form(form, documents, chunks_by_source)
        packets[form] = {
            "form_id": form,
            "default_status": "first_class" if form in DEFAULT_REVIEW_FORMS else "requested",
            "b24_rl1_legacy_only": form == "B24_RL1",
            "source_files": [doc.source_file for doc in documents],
            "retrieved_context": retrieved,
            "field_suggestions": _field_suggestions(retrieved),
            "missing_fields": [],
            "conflicts": [],
            "low_confidence_fields": [],
            "write_authority": "none; exact approval_map.json is required before DOCX patching",
        }
    return packets


def _retrieve_for_form(
    form: str,
    documents: list[LocalEvidenceDocument],
    chunks_by_source: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    keywords = FORM_KEYWORDS.get(form, (form.lower(),))
    scored: list[dict[str, Any]] = []
    for doc in documents:
        for chunk in chunks_by_source.get(doc.source_file, []):
            lower = str(chunk["text"]).lower()
            score = sum(2 if phrase in lower else 0 for phrase in keywords)
            score += sum(1 for token in re.findall(r"[a-z0-9]+", form.lower()) if token and token in lower)
            if score > 0:
                scored.append(
                    {
                        "source_file": doc.source_file,
                        "chunk_id": chunk["chunk_id"],
                        "score": score,
                        "text": _preview(str(chunk["text"])),
                    }
                )
    scored.sort(key=lambda item: (-int(item["score"]), str(item["source_file"]), int(item["chunk_id"])))
    return scored[:8]


def _field_suggestions(retrieved: list[dict[str, Any]]) -> list[dict[str, Any]]:
    suggestions: list[dict[str, Any]] = []
    patterns = (
        ("facility_name", r"\b(?:facility|company|shop)\s*[:=-]\s*([^\n\r;]{2,80})"),
        ("auditor", r"\b(?:auditor|inspector)\s*[:=-]\s*([^\n\r;]{2,80})"),
        ("date", r"\b(?:date|inspection date)\s*[:=-]\s*([0-9]{4}-[0-9]{2}-[0-9]{2}|[0-9]{1,2}/[0-9]{1,2}/[0-9]{2,4})"),
        ("car_number", r"\b(?:car|car no\.?|car number)\s*[:=-]\s*([A-Z]{2,5}\s*[0-9]{3,8})"),
    )
    seen: set[tuple[str, str]] = set()
    for item in retrieved:
        text = str(item["text"])
        for field, pattern in patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if not match:
                continue
            value = match.group(1).strip()
            key = (field, value)
            if key in seen:
                continue
            seen.add(key)
            suggestions.append(
                {
                    "field_id": field,
                    "candidate_value": value,
                    "confidence": 0.55,
                    "source_file": item["source_file"],
                    "chunk_id": item["chunk_id"],
                    "review_required": True,
                }
            )
    return suggestions


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
    lines = [
        f"# {packet['form_id']} Local Evidence Review",
        "",
        f"Write authority: {packet['write_authority']}",
        "",
        "## Sources",
    ]
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
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
