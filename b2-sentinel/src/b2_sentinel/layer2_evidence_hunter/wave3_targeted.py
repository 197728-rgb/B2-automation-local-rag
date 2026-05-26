"""Wave 3 - targeted missing-field expansion search.

For every field still 'missing' or 'weak' after Wave 2, build an expansion
query from the obligation graph (`expansion_search_terms`) and rank the
chunks by it. If the top chunk meaningfully overlaps the field, lift its
text into the ledger as a hint (decision='weak').

Cognitive integration: when enabled, the Evidence Synthesizer is called to
combine related fragments that individually aren't sufficient proof.
"""
from __future__ import annotations

import re

from ..cognitive.config import get_cognitive_config
from ..cognitive.synthesizer import synthesize_evidence
from ..core.models import (
    EvidenceLedgerEntry,
    ObligationGraph,
    SourceChunk,
)
from .retrieval import rank_chunks


def wave3_targeted(
    chunks: list[SourceChunk],
    graph: ObligationGraph,
    ledger: dict[str, EvidenceLedgerEntry],
) -> dict[str, EvidenceLedgerEntry]:
    """Mutates `ledger` in place; also returns it for chaining."""
    form_id = graph.form_id
    for fid, entry in ledger.items():
        if entry.decision in ("usable", "conflict"):
            continue
        node = graph.fields[fid]
        if not node.expansion_search_terms:
            continue
        query = " ".join([node.label, *node.expansion_search_terms])
        # Prefer in-scope chunks; fall back to all if no in-scope matches
        in_scope = [c for c in chunks if c.scope_hint is None or c.scope_hint == form_id]
        ranked = rank_chunks(in_scope, query, limit=5) if in_scope else []
        if not ranked or ranked[0][1] < 0.05:
            ranked = rank_chunks(chunks, query, limit=5)
        if not ranked:
            continue
        best_chunk, best_score = ranked[0]
        if best_score < 0.05:
            continue
        snippet = _snippet_around_terms(best_chunk.text, node.expansion_search_terms)
        if not snippet:
            continue

        # Try to extract a value from the snippet using label:value patterns.
        extracted_value = _extract_value_from_snippet(
            snippet, node.expansion_search_terms, node.label
        )

        # Also try extracting from ALL top-ranked chunks (prefer B89-scoped)
        if not extracted_value:
            for chunk, score in ranked[:5]:
                if score < 0.05:
                    break
                if chunk.scope_hint and chunk.scope_hint != form_id:
                    continue
                s = _snippet_around_terms(chunk.text, node.expansion_search_terms)
                if s:
                    extracted_value = _extract_value_from_snippet(
                        s, node.expansion_search_terms, node.label
                    )
                    if extracted_value:
                        best_chunk = chunk
                        best_score = score
                        snippet = s
                        break

        entry.source_file = best_chunk.source_file
        entry.source_type = best_chunk.source_type
        entry.page = best_chunk.page
        entry.chunk_id = best_chunk.chunk_id
        entry.source_text = snippet[:240]
        entry.scope = best_chunk.scope_hint or entry.scope
        entry.wave_found_in = 3

        if extracted_value:
            entry.candidate_value = extracted_value
            entry.confidence = max(entry.confidence, min(0.75, 0.5 + best_score))
            entry.decision = "usable"
        else:
            entry.confidence = max(entry.confidence, min(0.5, 0.3 + best_score))
            entry.decision = "weak"
    return ledger


def _snippet_around_terms(text: str, terms: list[str]) -> str | None:
    if not text:
        return None
    lower = text.lower()
    for term in terms:
        t = term.lower().strip()
        if not t:
            continue
        idx = lower.find(t)
        if idx == -1:
            continue
        start = max(0, idx - 60)
        end = min(len(text), idx + len(t) + 120)
        return re.sub(r"\s+", " ", text[start:end]).strip()
    return None


_VALUE_AFTER_LABEL = re.compile(
    r"(?:^|\n)\s*([A-Za-z0-9 _./()&\-#]+?)\s*[:=\-\u2013]\s*(.+?)(?:\n|$)",
    re.MULTILINE,
)

_COLON_VALUE = re.compile(r":\s*(.+?)(?:\s{2,}|\n|$)")


def _extract_value_from_snippet(
    snippet: str,
    search_terms: list[str],
    label: str,
) -> str | None:
    """Try to pull a concrete value from a snippet that matched search terms.

    Looks for patterns like:
      - "Label: Value"
      - "Label = Value"
      - "Label - Value"
    where Label matches one of our search terms or the field label.
    """
    if not snippet:
        return None

    snippet_lower = snippet.lower()
    all_terms = [label] + list(search_terms)

    for term in all_terms:
        t = term.lower().strip()
        if not t:
            continue
        idx = snippet_lower.find(t)
        if idx == -1:
            continue

        # Look for value after this term
        after_term = snippet[idx + len(t):]
        m = _COLON_VALUE.match(after_term)
        if m:
            value = m.group(1).strip()
            # Reject values that are clearly other labels or too long
            if value and len(value) <= 100 and not _looks_like_label(value):
                return value

    # Fallback: try all label:value patterns in the snippet
    for m in _VALUE_AFTER_LABEL.finditer(snippet):
        found_label = m.group(1).strip().lower()
        value = m.group(2).strip()
        for term in all_terms:
            t = term.lower().strip()
            if t and (t in found_label or found_label in t):
                if value and len(value) <= 100 and not _looks_like_label(value):
                    return value

    return None


def _looks_like_label(text: str) -> bool:
    """Heuristic: reject extracted 'values' that are actually the next label."""
    if text.endswith(":") or text.endswith("="):
        return True
    if re.match(r"^[A-Z][a-z]+ [A-Z][a-z]+ [A-Z][a-z]+$", text):
        return True
    return False
