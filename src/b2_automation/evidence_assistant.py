"""Local Evidence Assistant primitives for audit-ready retrieval and reporting."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ConfidencePolicy:
    high: float = 0.85
    medium: float = 0.70


def hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()


def enrich_chunk_metadata(*, source_file: str, source_sha256: str, extracted_at: str, chunk: dict[str, Any]) -> dict[str, Any]:
    text = str(chunk.get("text") or "")
    return {
        **chunk,
        "source_file": source_file,
        "source_sha256": source_sha256,
        "section": str(chunk.get("section") or "body"),
        "timestamp": extracted_at,
        "chunk_hash": hash_text(text),
        "confidence": float(chunk.get("confidence") or 1.0),
    }


def build_delta_report(*, previous_index: dict[str, str], current_index: dict[str, str]) -> dict[str, Any]:
    prev_items = set(previous_index.items())
    curr_items = set(current_index.items())
    new_docs = sorted([doc for doc in current_index if doc not in previous_index])
    deleted_docs = sorted([doc for doc in previous_index if doc not in current_index])
    changed_docs = sorted([doc for doc in current_index if doc in previous_index and current_index[doc] != previous_index[doc]])
    duplicates: dict[str, list[str]] = {}
    by_hash: dict[str, list[str]] = {}
    for doc, digest in current_index.items():
        by_hash.setdefault(digest, []).append(doc)
    for digest, docs in by_hash.items():
        if len(docs) > 1:
            duplicates[digest] = sorted(docs)
    return {
        "new_documents": new_docs,
        "changed_documents": changed_docs,
        "deleted_documents": deleted_docs,
        "duplicate_files": duplicates,
        "summary": {
            "previous_count": len(prev_items),
            "current_count": len(curr_items),
        },
    }


def confidence_gated_answer(*, question: str, retrieved_rows: list[dict[str, Any]], policy: ConfidencePolicy = ConfidencePolicy()) -> dict[str, Any]:
    if not retrieved_rows:
        return {
            "question": question,
            "tier": "low",
            "answer": "Evidence is insufficient to answer this question.",
            "citations": [],
        }
    best = max(float(row.get("confidence") or 0.0) for row in retrieved_rows)
    citations = [
        {
            "source_file": row.get("source_file"),
            "chunk_id": row.get("chunk_id"),
            "chunk_hash": row.get("chunk_hash"),
        }
        for row in retrieved_rows
        if row.get("source_file") and row.get("chunk_id") is not None and row.get("chunk_hash")
    ]
    if not citations:
        return {
            "question": question,
            "tier": "low",
            "answer": "Evidence is insufficient because no citation-ready chunks were retrieved.",
            "citations": [],
        }
    if best >= policy.high:
        tier = "high"
        answer = "Answer supported by high-confidence evidence."
    elif best >= policy.medium:
        tier = "medium"
        answer = "Answer is partially supported; reviewer caveat required."
    else:
        tier = "low"
        answer = "Evidence is insufficient to provide a reliable answer."
    return {"question": question, "tier": tier, "answer": answer, "citations": citations}


def ensure_clause_map_db(path: Path) -> None:
    con = sqlite3.connect(path)
    try:
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS requirement_clauses (
                requirement_id TEXT NOT NULL,
                source TEXT NOT NULL,
                clause TEXT NOT NULL,
                obligation TEXT NOT NULL,
                evidence_needed TEXT NOT NULL,
                risk_level TEXT NOT NULL,
                related_docs TEXT NOT NULL
            )
            """
        )
        try:
            con.execute("CREATE VIRTUAL TABLE IF NOT EXISTS requirement_clauses_fts USING fts5(requirement_id, source, clause, obligation, evidence_needed, risk_level, related_docs)")
        except sqlite3.OperationalError as exc:
            if "fts5" not in str(exc).lower():
                raise
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS requirement_clauses_search (
                    requirement_id TEXT,
                    source TEXT,
                    clause TEXT,
                    obligation TEXT,
                    evidence_needed TEXT,
                    risk_level TEXT,
                    related_docs TEXT
                )
                """
            )
        con.commit()
    finally:
        con.close()


def build_role_views(*, canonical: dict[str, Any], run_logs: dict[str, Any]) -> dict[str, Any]:
    fields = canonical.get("fields", [])
    schema = canonical.get("schema")
    schema_forms = schema.get("forms") if isinstance(schema, dict) else []
    forms = canonical.get("forms") or schema_forms or []
    if not forms:
        forms = sorted({field.get("form") for field in fields if field.get("form")})
    gaps = [f for f in fields if str(f.get("reviewer_status")) in {"missing", "conflict", "low_confidence", "review_required"}]
    return {
        "auditor": {"citations": canonical.get("citation_evidence", []), "gaps": gaps, "evidence_map": fields},
        "operator": {"instructions": "Use selected values only where reviewer_status is ok.", "fields": [f for f in fields if f.get("reviewer_status") == "ok"]},
        "admin": {"ingestion_logs": run_logs, "index_health": {"forms": len(forms), "field_count": len(fields)}},
        "management": {"risk_summary": {"gap_count": len(gaps), "forms": forms}},
    }


def write_eval_seed(path: Path) -> None:
    qa = [
        {"question": "Where is corrective action evidence stored?", "expected_contains": ["review", "raw"]},
        {"question": "Which process references B2?", "expected_contains": ["B24_RL2", "B81", "B89", "B90", "Cover_Page"]},
        {"question": "What records prove inspection completion?", "expected_contains": ["field_decisions", "canonical_evidence"]},
    ]
    path.write_text(json.dumps({"seed_questions": qa}, indent=2), encoding="utf-8")
