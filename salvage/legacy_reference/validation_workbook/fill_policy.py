"""
Conflict policy for B-2 fill after validation workbook.

Default: do not fill a field when multiple distinct candidate values exist (conflict).
Optional: --force-first-on-conflict uses the first candidate in collection order (legacy-style).
"""

from __future__ import annotations

from shared_core.extractor import FieldCandidate


def resolve_fill_payload(
    candidates: list[FieldCandidate],
    *,
    force_first_on_conflict: bool = False,
) -> tuple[dict[str, str], dict[str, str]]:
    """
    Build flat payload for writer from provenance candidates.

    Returns:
        payload: field -> single value (omit conflict fields unless force_first_on_conflict)
        field_resolution: field -> 'filled' | 'conflict' | 'skipped_single_candidate_needed'
    """
    by_field: dict[str, list[FieldCandidate]] = {}
    for c in candidates:
        by_field.setdefault(c.b2_field, []).append(c)

    payload: dict[str, str] = {}
    field_resolution: dict[str, str] = {}

    for field, clist in by_field.items():
        values = []
        seen_v: set[str] = set()
        for c in clist:
            v = (c.value or "").strip()
            if v and v not in seen_v:
                seen_v.add(v)
                values.append(v)
        if not values:
            continue
        if len(values) == 1:
            payload[field] = values[0]
            field_resolution[field] = "filled"
        else:
            if force_first_on_conflict:
                payload[field] = clist[0].value.strip()
                field_resolution[field] = "filled_forced_first"
            else:
                field_resolution[field] = "conflict"

    return payload, field_resolution
