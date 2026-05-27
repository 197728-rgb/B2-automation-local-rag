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


_LABEL_VALUE_RE = re.compile(r"^\s*([A-Za-z0-9 _./()&\-#\[\]]+)[:=]\s*(.+?)\s*$")
_NON_ALNUM_RE = re.compile(r"[^a-z0-9]+", re.I)
_EMBEDDED_LABEL_RE = re.compile(r"\b\d+\.\s+[A-Za-z][A-Za-z0-9 /#&().\-]{2,60}:\s*")
_DATE_FIELD_RE = re.compile(r"date|_date$|^date_", re.I)
_DATE_VALUE_RE = re.compile(
    r"^\s*(?:\d{1,2}/\d{1,2}/\d{2,4}|\d{4}-\d{2}-\d{2})(?:\s+\d{1,2}:\d{2}(?:\s*[AP]M)?)?\s*$",
    re.I,
)

_STRUCTURED_FIELD_KEY_ALIASES: dict[str, tuple[str, ...]] = {
    "facility_name": ("tankCarOwnerName", "tank car owner name"),
    "tco_permission_date": ("datePermissionReceived", "date permission received"),
    "pitp_document_name": ("0procedureName",),
    "pitp_id": ("0procedureId",),
    "pitp_approved_by": ("0approvedBy",),
    "pitp_date_approved": ("0dateApproved",),
    "car_mark": ("carMarkAndNumber", "car mark and number"),
    "tank_design_spec": (
        "tankCarDesignSpecification",
        "tank car design specification",
        "tank car design spec",
    ),
    "aar_form_4_2_number": ("aarForm42Number", "aar form42 number"),
    "four_two_drawing_number": ("0drawingNumber", "drawingNumber"),
    "test_plate_tank_material": ("0materialSpecification", "tank plate material"),
    "test_plate_tank_mtr": ("0mtrNumber", "mtrNumber"),
    "attachment_material": ("2materialSpecification", "2materialDescription"),
    "car.design_spec": (
        "tankCarDesignSpecification",
        "tank car design specification",
        "tank car design spec",
        "tank car design spec/stencil spec",
    ),
    "aar.form_4_2.number": ("aarForm42Number", "aar form42 number"),
    "tank_car_or_lining_coating_owner_tco_l_co_name": (
        "tankCarOwnerName",
        "tank car owner name",
    ),
    "aar_4_2_aar_number": ("aarForm42Number", "aar form42 number"),
    "4_2_drawing_type": ("0drawingType", "drawingType"),
    "date_received_function_specific_training": (
        "0functionSpecificTrainingDate",
        "functionSpecificTrainingDate",
    ),
    "tank_car_tank_plate_material_type_grade": ("0materialSpecification",),
    "mill_test_report_number": ("0mtrNumber", "mtrNumber"),
    "observed_thickness": ("0thickness", "thickness"),
    "observed_height": ("0height", "height"),
    "observed_width": ("0width", "width"),
}


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
    keyed = [(k, k.lower(), _normalized_key(k)) for k in keys if k]
    candidates: list[tuple[str, SourceChunk, str | None, float]] = []
    for label, value, chunk in pairs:
        label_norm = _normalized_key(label)
        best: tuple[str, float] | None = None
        for k, k_low, k_norm in keyed:
            if label == k_low or _norm_matches(label_norm, k_norm):
                strength = 1.0
            elif label_norm and k_norm and (k_norm in label_norm or label_norm in k_norm):
                strength = 0.72
            elif k_low in label or label in k_low:
                strength = 0.7
            else:
                continue
            if (
                "." in label
                and label_norm
                and not _field_context_matches(node.field_id, label_norm)
                and not _is_first_procedure_pitp(node.field_id, label_norm, chunk.chunk_id)
            ):
                strength = min(strength, 0.45)
            if _needs_field_context(node.field_id, label_norm, k_norm):
                context_norm = label_norm + _normalized_key(chunk.chunk_id)
                if (
                    not _field_context_matches(node.field_id, context_norm)
                    and not _is_first_procedure_pitp(node.field_id, label_norm, chunk.chunk_id)
                ):
                    strength = min(strength, 0.45)
            if chunk.source_type == "json":
                strength = min(1.0, strength + 0.08)
            if _looks_overcaptured_value(value):
                strength = min(strength, 0.45)
            if _looks_non_date_for_date_field(node.field_id, value):
                strength = min(strength, 0.45)
            if best is None or strength > best[1]:
                best = (k, strength)
        if best is not None:
            k, strength = best
            alias_used = k if k != node.field_id and k != node.label.lower() else None
            candidates.append((value, chunk, alias_used, strength))
    return candidates


def _keys_for_field(node: FieldNode, alias_brain: AliasBrain, form_id: str) -> Iterable[str]:
    yield node.field_id
    yield node.label.lower()
    for k in _STRUCTURED_FIELD_KEY_ALIASES.get(node.field_id, ()):
        yield k
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

    # Prefer candidates from single-scope files when both exist, but do not let
    # a weak single-scope PDF over-capture discard stronger structured JSON.
    single_scope = [c for c in candidates if c[1].source_file not in multi_scope_files]
    if (
        single_scope
        and len(single_scope) < len(candidates)
        and max(c[3] for c in single_scope) >= max(c[3] for c in candidates) - 0.05
    ):
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
        top_strength = max(c[3] for c in primary_group)
        next_strength = max(max(c[3] for c in grp) for _, grp in ranked_groups[1:])
        if top_strength >= 0.75 and next_strength <= 0.55:
            return EvidenceLedgerEntry(
                field_id=field_id,
                candidate_value=primary_value,
                source_file=primary[1].source_file,
                source_type=primary[1].source_type,
                page=primary[1].page,
                chunk_id=primary[1].chunk_id,
                source_text=_first_line(primary[1].text),
                confidence=min(0.95, 0.6 + 0.35 * primary[3]),
                scope=primary[1].scope_hint,
                decision="usable",
                alternates=alternates,
                alias_used=primary[2],
                wave_found_in=2,
            )

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


def _normalized_key(value: str) -> str:
    """Normalize labels so camelCase JSON keys match snake_case form fields."""
    return _NON_ALNUM_RE.sub("", value).lower()


def _norm_matches(label_norm: str, key_norm: str) -> bool:
    if not label_norm or not key_norm:
        return False
    if label_norm == key_norm:
        return True
    for token in ("tco", "lco"):
        label_trimmed = label_norm.replace(token, "")
        key_trimmed = key_norm.replace(token, "")
        if len(label_trimmed) > 4 and len(key_trimmed) > 4 and label_trimmed == key_trimmed:
            return True
    return False


def _looks_overcaptured_value(value: str) -> bool:
    """Detect PDF/table text that swallowed following numbered labels."""
    return bool(_EMBEDDED_LABEL_RE.search(value))


def _looks_non_date_for_date_field(field_id: str, value: str) -> bool:
    """Demote boolean/status text that matched a date field by label overlap."""
    return bool(_DATE_FIELD_RE.search(field_id)) and not bool(_DATE_VALUE_RE.match(value))


def _field_context_matches(field_id: str, label_norm: str) -> bool:
    """Return true when a dotted JSON label belongs to the field's own context."""
    generic = {"id", "name", "type", "date", "number", "code"}
    roots = [part for part in re.split(r"[._]", field_id) if part and part not in generic]
    return any(root and root in label_norm for root in roots)


def _needs_field_context(field_id: str, label_norm: str, key_norm: str) -> bool:
    """Generic procedure/document labels need a field-specific context anchor."""
    if not (field_id.startswith("pitp.") or field_id.startswith("pitp_")):
        return False
    generic_labels = {"procedurename", "procedureid", "documentname"}
    generic_labels.update({f"0{x}" for x in generic_labels})
    generic_keys = {"procedurename", "procedureid", "documentname", "pitpdocumentname"}
    return label_norm in generic_labels or key_norm in generic_keys


def _is_first_procedure_pitp(field_id: str, label_norm: str, chunk_id: str) -> bool:
    """The combined JSON uses procedures[0] for the PITP row."""
    if not (field_id.startswith("pitp.") or field_id.startswith("pitp_")):
        return False
    return "section.procedures" in chunk_id and label_norm.startswith("0")
