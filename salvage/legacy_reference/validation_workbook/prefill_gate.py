"""
Strict preflight: optionally skip DOCX fill when required fields are missing or candidates conflict.

Use with ``--strict-prefill``; override with ``--allow-incomplete-fill`` when a partial DOCX is acceptable.
"""

from __future__ import annotations

# Sensible defaults for tank B-2 style forms — override via ``--required-fields``.
DEFAULT_STRICT_REQUIRED_FIELDS: tuple[str, ...] = (
    "owner_name",
    "car_mark",
    "tank_spec",
)


def prefill_blockers(
    *,
    payload: dict[str, str],
    resolution: dict[str, str],
    strict_prefill: bool,
    required_fields: tuple[str, ...] | None,
    allow_incomplete_fill: bool,
) -> list[str]:
    if not strict_prefill or allow_incomplete_fill:
        return []
    reasons: list[str] = []
    req = required_fields if required_fields is not None else DEFAULT_STRICT_REQUIRED_FIELDS
    for f in req:
        v = (payload.get(f) or "").strip()
        if not v:
            reasons.append(f"missing_required:{f}")
    for field, res in resolution.items():
        if res == "conflict":
            reasons.append(f"conflict:{field}")
    return reasons
