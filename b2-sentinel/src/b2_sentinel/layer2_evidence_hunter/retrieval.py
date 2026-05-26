"""Lightweight chunk ranker.

Uses sklearn's TfidfVectorizer when available; falls back to a deterministic
keyword overlap scorer otherwise. Either way the public API is the same:
`rank_chunks(chunks, query) -> list[(chunk, score)]`.
"""
from __future__ import annotations

import re
from typing import Iterable

from ..core.models import SourceChunk

_TOKEN_RE = re.compile(r"[A-Za-z0-9_./-]+")


def _tokenize(text: str) -> list[str]:
    return [tok.lower() for tok in _TOKEN_RE.findall(text)]


def rank_chunks(
    chunks: list[SourceChunk],
    query: str,
    *,
    limit: int | None = None,
) -> list[tuple[SourceChunk, float]]:
    """Return chunks ranked by relevance to the query.

    Tries sklearn TF-IDF first; falls back to keyword overlap if sklearn is
    missing or there are not enough chunks for vectorization.
    """
    if not chunks:
        return []

    sklearn_ranked = _try_tfidf(chunks, query)
    ranked = sklearn_ranked if sklearn_ranked is not None else _keyword_overlap(chunks, query)

    if limit is not None:
        ranked = ranked[:limit]
    return ranked


def _try_tfidf(chunks: list[SourceChunk], query: str) -> list[tuple[SourceChunk, float]] | None:
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer  # type: ignore
        from sklearn.metrics.pairwise import cosine_similarity  # type: ignore
    except ImportError:
        return None
    if len(chunks) < 2:
        return None
    docs = [c.text for c in chunks]
    try:
        vec = TfidfVectorizer(lowercase=True, ngram_range=(1, 2))
        m = vec.fit_transform(docs + [query])
    except ValueError:
        return None
    chunk_matrix = m[:-1]
    query_vec = m[-1]
    sims = cosine_similarity(query_vec, chunk_matrix).ravel()
    return sorted(
        ((chunks[i], float(sims[i])) for i in range(len(chunks))),
        key=lambda kv: kv[1],
        reverse=True,
    )


def _keyword_overlap(chunks: list[SourceChunk], query: str) -> list[tuple[SourceChunk, float]]:
    q_tokens = set(_tokenize(query))
    if not q_tokens:
        return [(c, 0.0) for c in chunks]
    scored: list[tuple[SourceChunk, float]] = []
    for c in chunks:
        c_tokens = set(_tokenize(c.text))
        if not c_tokens:
            scored.append((c, 0.0))
            continue
        overlap = len(q_tokens & c_tokens)
        score = overlap / max(len(q_tokens), 1)
        scored.append((c, score))
    scored.sort(key=lambda kv: kv[1], reverse=True)
    return scored
