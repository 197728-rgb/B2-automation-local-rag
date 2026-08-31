"""Investigator Agent — gatherEvidence per AuditRequirement."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from b2_automation.autonomous_contracts import AuditRequirement, EvidenceBundle, EvidenceItem
from b2_automation.local_extraction import (
    LocalEvidenceDocument,
    chunk_text,
    extract_local_document,
    supported_evidence_files,
)
from b2_automation.local_semantic_retrieval import retrieve_chunks_for_form

_CACHE: dict[str, tuple[list[LocalEvidenceDocument], dict[str, list[dict[str, Any]]]]] = {}


def _cache_key(folder: Path) -> str:
    files = sorted(supported_evidence_files(folder))
    return str(folder.resolve()) + ":" + "|".join(str(p) for p in files)


def _load_evidence_cache(source_folder: Path) -> tuple[list[LocalEvidenceDocument], dict[str, list[dict[str, Any]]]]:
    key = _cache_key(source_folder)
    if key in _CACHE:
        return _CACHE[key]
    documents: list[LocalEvidenceDocument] = []
    chunks_by_source: dict[str, list[dict[str, Any]]] = {}
    for path in supported_evidence_files(source_folder):
        doc = extract_local_document(path)
        documents.append(doc)
        chunks_by_source[doc.source_file] = chunk_text(doc.text)
    _CACHE[key] = (documents, chunks_by_source)
    return documents, chunks_by_source


def _authority_score(path: Path) -> float:
    name = path.name.lower()
    if "policy" in name or "procedure" in name:
        return 0.95
    if "report" in name or "audit" in name:
        return 0.85
    if "log" in name or "record" in name:
        return 0.75
    return 0.65


def _tokenize(text: str) -> list[str]:
    return [t.lower() for t in re.findall(r"[a-z0-9]+", text, flags=re.IGNORECASE) if len(t) > 2]


def _items_from_chunks(
    req: AuditRequirement,
    documents: list[LocalEvidenceDocument],
    chunks_by_source: dict[str, list[dict[str, Any]]],
    form_id: str,
) -> list[EvidenceItem]:
    retrieved, _method = retrieve_chunks_for_form(form_id, documents, chunks_by_source, top_k=8)
    directive_tokens = set(_tokenize(req.search_directive + " " + req.field_label))
    items: list[EvidenceItem] = []
    ranked = sorted(
        retrieved,
        key=lambda hit: (
            sum(1 for t in directive_tokens if t in str(hit.get("text") or "").lower()),
            float(hit.get("semantic_score") or 0.0),
            float(hit.get("retrieval_score") or 0.0),
        ),
        reverse=True,
    )
    for hit in ranked[:5]:
        text = str(hit.get("chunk_excerpt") or hit.get("text") or "")[:1200]
        if not text.strip():
            continue
        score = float(hit.get("retrieval_score") or hit.get("score") or 0.0)
        source_file = str(hit.get("source_file") or "")
        path = next((d.source_path for d in documents if d.source_file == source_file), None)
        items.append(
            EvidenceItem(
                source_file=source_file,
                page_number=int(hit.get("page") or hit.get("source_page") or 0) or None,
                section_label=str(hit.get("section") or "") or None,
                evidence_type="text",  # type: ignore[arg-type]
                extracted_content=text,
                relevance_reason=f"Semantic match for: {req.field_label}",
                confidence=min(0.99, max(0.35, score + 0.4)),
                source_authority_score=_authority_score(path) if path else 0.65,
            )
        )
    return items


def gather_evidence(
    requirement: AuditRequirement,
    source_folder: Path,
    *,
    form_id: str = "B24_RL2",
    cache: dict[str, Any] | None = None,
) -> EvidenceBundle:
    """gatherEvidence stage — always returns a bundle."""
    source_folder = Path(source_folder)
    if not source_folder.is_dir():
        return EvidenceBundle(
            requirement_id=requirement.id,
            gaps=[f"Source folder not found: {source_folder}"],
        )

    if cache and cache.get("documents") and cache.get("chunks_by_source"):
        documents = cache["documents"]
        chunks_by_source = cache["chunks_by_source"]
    else:
        documents, chunks_by_source = _load_evidence_cache(source_folder)

    items = _items_from_chunks(requirement, documents, chunks_by_source, form_id)
    gaps: list[str] = []
    contradictions: list[str] = []

    if not items:
        gaps.append(f"No evidence found for '{requirement.field_label}' ({requirement.search_directive})")

    values = set()
    for item in items:
        snippet = item.extracted_content[:200].lower()
        values.add(re.sub(r"\s+", " ", snippet).strip())

    if len(values) > 3:
        contradictions.append("Multiple distinct evidence snippets; authority resolution may apply")

    return EvidenceBundle(
        requirement_id=requirement.id,
        items=items,
        gaps=gaps,
        contradictions=contradictions,
    )


def preload_evidence_cache(source_folder: Path) -> dict[str, Any]:
    documents, chunks_by_source = _load_evidence_cache(source_folder)
    return {"documents": documents, "chunks_by_source": chunks_by_source}


def write_evidence_artifact(bundles: list[EvidenceBundle], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({b.requirement_id: b.to_dict() for b in bundles}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
