"""Local-only semantic / lexical retrieval for form-scoped chunks.

No cloud APIs. Tries sklearn TF-IDF when available; otherwise a pure-Python
TF–IDF cosine ranker; falls back to the legacy keyword heuristic if the corpus
is empty. Retrieval scores are evidence-only and do not authorize DOCX writes.
"""

from __future__ import annotations

import hashlib
import math
import re
from typing import Any

from b2_automation.local_retrieval_constants import FORM_KEYWORDS

_TOKEN_RE = re.compile(r"[a-z0-9]+", re.IGNORECASE)


def _chunk_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()


def _tokenize(text: str) -> list[str]:
    return [t.lower() for t in _TOKEN_RE.findall(text)]


def _preview(text: str, limit: int = 600) -> str:
    compact = re.sub(r"\s+", " ", text).strip()
    if len(compact) <= limit:
        return compact
    return compact[: limit - 3] + "..."


def _keyword_score_for_chunk(form: str, chunk_text: str) -> int:
    keywords = FORM_KEYWORDS.get(form, (form.lower(),))
    lower = chunk_text.lower()
    score = sum(2 if phrase in lower else 0 for phrase in keywords)
    score += sum(1 for token in _tokenize(form) if len(token) > 1 and token in lower)
    return score


def _query_text(form: str) -> str:
    parts = list(FORM_KEYWORDS.get(form, ())) + [form.replace("_", " "), form]
    return " ".join(parts)


def _flatten_chunks(
    documents: list[Any],
    chunks_by_source: dict[str, list[dict[str, Any]]],
) -> list[tuple[str, int, str]]:
    """(source_file, chunk_id, full_text)."""
    rows: list[tuple[str, int, str]] = []
    for doc in documents:
        for chunk in chunks_by_source.get(doc.source_file, []):
            text = str(chunk.get("text") or "")
            rows.append((doc.source_file, int(chunk["chunk_id"]), text))
    return rows


def _sklearn_tfidf_rank(query: str, corpus_texts: list[str]) -> list[float] | None:
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer  # type: ignore[import-not-found]
        from sklearn.metrics.pairwise import cosine_similarity  # type: ignore[import-not-found]
    except Exception:
        return None
    if not corpus_texts:
        return None
    try:
        vectorizer = TfidfVectorizer(max_features=4096, stop_words="english")
        X = vectorizer.fit_transform(corpus_texts)
        q = vectorizer.transform([query])
        sims = cosine_similarity(q, X).flatten()
        return [float(sims[i]) for i in range(len(corpus_texts))]
    except Exception:
        return None


def _pure_tfidf_cosine(query: str, corpus_texts: list[str]) -> list[float]:
    """Tiny-corpus TF–IDF cosine similarity (no numpy)."""
    if not corpus_texts:
        return []
    docs_tokens = [_tokenize(t) for t in corpus_texts]
    q_tokens = _tokenize(query)
    n_docs = len(corpus_texts)

    df: dict[str, int] = {}
    for tokens in docs_tokens:
        seen = set(tokens)
        for t in seen:
            df[t] = df.get(t, 0) + 1

    def idf(term: str) -> float:
        return math.log((1.0 + n_docs) / (1.0 + df.get(term, 0))) + 1.0

    def vec(tokens: list[str]) -> dict[str, float]:
        tf: dict[str, float] = {}
        for t in tokens:
            tf[t] = tf.get(t, 0.0) + 1.0
        length = len(tokens) or 1
        out: dict[str, float] = {}
        for t, c in tf.items():
            out[t] = (c / length) * idf(t)
        return out

    qv = vec(q_tokens)
    doc_vecs = [vec(t) for t in docs_tokens]

    def cosine(a: dict[str, float], b: dict[str, float]) -> float:
        keys = set(a) & set(b)
        if not keys:
            return 0.0
        dot = sum(a[k] * b[k] for k in keys)
        na = math.sqrt(sum(v * v for v in a.values()))
        nb = math.sqrt(sum(v * v for v in b.values()))
        if na == 0 or nb == 0:
            return 0.0
        return dot / (na * nb)

    return [cosine(qv, dv) for dv in doc_vecs]


def _keyword_retrieval(
    form: str,
    documents: list[Any],
    chunks_by_source: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    """Original keyword/heuristic retrieval (fallback)."""
    keywords = FORM_KEYWORDS.get(form, (form.lower(),))
    scored: list[dict[str, Any]] = []
    for doc in documents:
        for chunk in chunks_by_source.get(doc.source_file, []):
            text_full = str(chunk.get("text") or "")
            lower = text_full.lower()
            kw = sum(2 if phrase in lower else 0 for phrase in keywords)
            kw += sum(1 for token in _tokenize(form) if len(token) > 1 and token in lower)
            if kw > 0:
                scored.append(
                    {
                        "source_file": doc.source_file,
                        "chunk_id": int(chunk["chunk_id"]),
                        "score": kw,
                        "text": _preview(text_full),
                    }
                )
    scored.sort(key=lambda item: (-int(item["score"]), str(item["source_file"]), int(item["chunk_id"])))
    return scored[:8]


def retrieve_chunks_for_form(
    form: str,
    documents: list[Any],
    chunks_by_source: dict[str, list[dict[str, Any]]],
    *,
    top_k: int = 8,
) -> tuple[list[dict[str, Any]], str]:
    """Rank chunks for a form. Returns (retrieved_rows, method_label)."""
    rows = _flatten_chunks(documents, chunks_by_source)
    if not rows:
        return [], "empty_corpus"

    query = _query_text(form)
    corpus_texts = [r[2] for r in rows]

    semantic_scores: list[float] | None = _sklearn_tfidf_rank(query, corpus_texts)
    method = "sklearn_tfidf"
    if semantic_scores is None:
        semantic_scores = _pure_tfidf_cosine(query, corpus_texts)
        method = "local_tfidf_cosine"

    if not semantic_scores or all(s <= 0.0 for s in semantic_scores):
        fallback = _keyword_retrieval(form, documents, chunks_by_source)
        enriched = [_with_telemetry_from_keyword_row(form, r, "keyword_fallback") for r in fallback]
        return enriched[:top_k], "keyword_fallback"

    out: list[dict[str, Any]] = []
    for i, (source_file, chunk_id, full_text) in enumerate(rows):
        sem = float(semantic_scores[i]) if i < len(semantic_scores) else 0.0
        kw = _keyword_score_for_chunk(form, full_text)
        combined = int(round(sem * 1000)) + kw * 2
        excerpt = _preview(full_text)
        out.append(
            {
                "source_file": source_file,
                "chunk_id": chunk_id,
                "score": combined,
                "semantic_score": round(sem, 6),
                "keyword_score": kw,
                "retrieval_score": combined,
                "text": excerpt,
                "chunk_excerpt": excerpt,
                "chunk_hash": _chunk_hash(full_text),
                "retrieval_method": method,
            }
        )

    out.sort(key=lambda item: (-float(item["semantic_score"]), -int(item["keyword_score"]), str(item["source_file"]), int(item["chunk_id"])))
    return out[:top_k], method


def _with_telemetry_from_keyword_row(form: str, row: dict[str, Any], method: str) -> dict[str, Any]:
    # row has text as preview only — re-hash preview for stability
    excerpt = str(row.get("text") or "")
    return {
        **row,
        "semantic_score": 0.0,
        "keyword_score": int(row.get("score") or 0),
        "retrieval_score": int(row.get("score") or 0),
        "chunk_excerpt": excerpt,
        "chunk_hash": _chunk_hash(excerpt),
        "retrieval_method": method,
    }
