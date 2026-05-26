"""Wave 2 - normalize, alias-resolve, conflict-detect.

For each field in the obligation graph, scan all chunks for label:value
matches (and alias matches), collect candidate values, mark conflicts when
multiple distinct values appear, and pick the strongest non-conflicting
candidate as the field's primary evidence.

Cognitive integration: after static alias lookup fails, the Semantic Alias
Resolver is consulted (when enabled). Tier 1-2 aliases are auto-usable;
tier 3 are logged only.
"""
from __future__ import annotations

import re
from collections import defaultdict
from typing import Iterable

from ..cognitive.alias_resolver import resolve_semantic_alias
from ..cognitive.config import get_cognitive_config
from ..core.models import (
    EvidenceLedgerEntry,
    FieldNode,
    ObligationGraph,
    SourceChunk,
)
from ..innovations.alias_brain import AliasBrain
from .retrieval import rank_chunks


_LABEL_VALUE_RE = re.compile(r"^\s*([A-Za-z0-9 _./()&\-#]+)[:=]\s*(.+?)\s*$")


def _identify_multi_scope_files(chunks: list[SourceChunk]) -> set[str]:
    """Find files that produced chunks with 2+ different non-None scope hints."""
    scopes_by_file: dict[str, set[str]] = defaultdict(set)
    for chunk in chunks:
        if chunk.scope_hint is not None:
            scopes_by_file[chunk.source_file].add(chunk.scope_hint)
    return {f for f, scopes in scopes_by_file.items() if len(scopes) >= 2}


def wave2_normalize(
    chunks: list[SourceChunk],
    graph: ObligationGraph,
    *,
    alias_brain: AliasBrain | None = None,
) -> dict[str, EvidenceLedgerEntry]:
    """Returns {field_id: best EvidenceLedgerEntry} for the form."""
    alias_brain = alias_brain or AliasBrain()
    form_id = graph.form_id

    multi_scope_files = _identify_multi_scope_files(chunks)

    # Pre-filter: only include chunks whose scope is compatible with this form.
    compatible_chunks = [
        c for c in chunks
        if c.scope_hint is None or c.scope_hint == form_id
    ]

    # Pre-pass: collect all label/value pairs from compatible chunks
    pairs: list[tuple[str, str, SourceChunk]] = []
    for chunk in compatible_chunks:
        for line in chunk.text.splitlines():
            m = _LABEL_VALUE_RE.match(line)
            if not m:
                continue
            label = m.group(1).strip().lower()
            value = m.group(2).strip()
            if not label or not value:
                continue
            pairs.append((label, value, chunk))

    out: dict[str, EvidenceLedgerEntry] = {}
    for fid, node in graph.fields.items():
        if node.never_write:
            continue
        candidates = _candidates_for_field(node, pairs, alias_brain, graph.form_id)
        out[fid] = _pick_best(fid, candidates, node, chunks, multi_scope_files)
    return out


def _candidates_for_field(
    node: FieldNode,
    pairs: list[tuple[str, str, SourceChunk]],
    alias_brain: AliasBrain,
    form_id: str,
) -> list[tuple[str, SourceChunk, str | None, float]]:
    """Returns (value, chunk, alias_used, label_match_strength)."""
    keys = set(_keys_for_field(node, alias_brain, form_id))
    candidates: list[tuple[str, SourceChunk, str | None, float]] = []
    for label, value, chunk in pairs:
        for k in keys:
            k_low = k.lower()
            if label == k_low:
                strength = 1.0
            elif k_low in label or label in k_low:
                strength = 0.7
            else:
                continue
            alias_used = k if k != node.field_id and k != node.label.lower() else None
            candidates.append((value, chunk, alias_used, strength))
            break
    return candidates


def _keys_for_field(node: FieldNode, alias_brain: AliasBrain, form_id: str) -> Iterable[str]:
    yield node.field_id
    yield node.label.lower()
    for k in node.preferred_evidence_keys:
        yield k
    for a in node.aliases:
        yield a
    for a in alias_brain.aliases_for(node.field_id, form_id):
        yield a.from_key


def _try_cognitive_alias(
    label: str,
    context: str,
    form_id: str,
    graph: ObligationGraph,
) -> str | None:
    """Attempt cognitive alias resolution for an unmatched label.

    Returns field_id if a tier 1-2 alias is found, None otherwise.
    """
    config = get_cognitive_config()
    if not config.is_component_enabled("alias_resolver"):
        return None
    alias = resolve_semantic_alias(
        label,
        context_text=context,
        form_id=form_id,
        graph=graph,
    )
    if alias and alias.auto_usable and alias.to_field in graph.fields:
        return alias.to_field
    return None


def _pick_best(
    field_id: str,
    candidates: list[tuple[str, SourceChunk, str | None, float]],
    node: FieldNode,
    all_chunks: list[SourceChunk],
    multi_scope_files: set[str] | None = None,
) -> EvidenceLedgerEntry:
    if not candidates:
        return EvidenceLedgerEntry(
            field_id=field_id,
            decision="missing",
            confidence=0.0,
            scope=node.field_id.split(".", 1)[0],
            wave_found_in=2,
        )

    multi_scope_files = multi_scope_files or set()

    # Prefer candidates from single-scope files when both exist.
    single_scope = [c for c in candidates if c[1].source_file not in multi_scope_files]
    if single_scope and len(single_scope) < len(candidates):
        candidates = single_scope

    all_from_multi_scope = all(
        c[1].source_file in multi_scope_files for c in candidates
    ) if multi_scope_files else False

    # Same-file conflicts are typically parsing ambiguity, not real conflicts
    all_same_file = len({c[1].source_file for c in candidates}) == 1

    # Group by distinct values to detect conflict
    by_value: dict[str, list[tuple[str, SourceChunk, str | None, float]]] = defaultdict(list)
    for c in candidates:
        by_value[c[0]].append(c)

    if len(by_value) > 1:
        ranked_groups = sorted(
            by_value.items(),
            key=lambda kv: max(c[3] for c in kv[1]),
            reverse=True,
        )
        primary_value, primary_group = ranked_groups[0]
        primary = max(primary_group, key=lambda c: c[3])
        alternates = [
            {
                "value": val,
                "source_file": grp[0][1].source_file,
                "page": grp[0][1].page,
                "chunk_id": grp[0][1].chunk_id,
            }
            for val, grp in ranked_groups[1:]
        ]

        # When all candidates come from multi-scope files or a single file,
        # the conflict is unreliable (cross-car contamination or parsing
        # ambiguity). Demote to weak instead of hard conflict.
        if all_from_multi_scope or all_same_file:
            return EvidenceLedgerEntry(
                field_id=field_id,
                candidate_value=primary_value,
                source_file=primary[1].source_file,
                source_type=primary[1].source_type,
                page=primary[1].page,
                chunk_id=primary[1].chunk_id,
                source_text=_first_line(primary[1].text),
                confidence=0.5,
                scope=primary[1].scope_hint,
                decision="weak",
                alternates=alternates,
                alias_used=primary[2],
                wave_found_in=2,
            )

        return EvidenceLedgerEntry(
            field_id=field_id,
            candidate_value=primary_value,
            source_file=primary[1].source_file,
            source_type=primary[1].source_type,
            page=primary[1].page,
            chunk_id=primary[1].chunk_id,
            source_text=_first_line(primary[1].text),
            confidence=0.55,
            scope=primary[1].scope_hint,
            decision="conflict",
            alternates=alternates,
            alias_used=primary[2],
            wave_found_in=2,
        )

    # No conflict - rank within
    primary = max(candidates, key=lambda c: c[3])
    confidence = min(0.95, 0.6 + 0.35 * primary[3])
    decision = "usable" if confidence >= 0.65 else "weak"
    return EvidenceLedgerEntry(
        field_id=field_id,
        candidate_value=primary[0],
        source_file=primary[1].source_file,
        source_type=primary[1].source_type,
        page=primary[1].page,
        chunk_id=primary[1].chunk_id,
        source_text=_first_line(primary[1].text),
        confidence=confidence,
        scope=primary[1].scope_hint,
        decision=decision,
        alias_used=primary[2],
        wave_found_in=2,
    )


def _first_line(s: str) -> str:
    line = next((l for l in s.splitlines() if l.strip()), "")
    return line[:240]
