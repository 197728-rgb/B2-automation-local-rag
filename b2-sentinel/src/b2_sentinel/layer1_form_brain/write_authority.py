"""Write Authority Matrix - exact approval-map loader.

Refuses 'nearest', 'latest', 'similar', or generic maps. Only an exact
form_id + form_version match is accepted.
"""
from __future__ import annotations

import json
from pathlib import Path

from ..core.models import ApprovalMap
from ..core.paths import MAPS_DIR, form_map_path


class UnauthorizedMapError(Exception):
    pass


_FORBIDDEN_SUFFIXES = ("_latest", "_similar", "_nearest", "_generic")


def load_exact_approval_map(form_id: str, form_version: str = "2026") -> ApprovalMap:
    """Load schemas/maps/<form_id>.json and verify exact match.

    Refuses any path containing forbidden suffixes.
    """
    map_path = form_map_path(form_id)
    if not map_path.exists():
        raise FileNotFoundError(
            f"No exact approval map for form_id={form_id!r} at {map_path}. "
            "SENTINEL refuses nearest/latest/similar fallbacks."
        )
    name_lower = map_path.name.lower()
    for forbidden in _FORBIDDEN_SUFFIXES:
        if forbidden in name_lower:
            raise UnauthorizedMapError(
                f"Refusing to use map with forbidden suffix {forbidden!r}: {map_path}"
            )

    with map_path.open(encoding="utf-8") as fh:
        raw = json.load(fh)

    am = ApprovalMap.model_validate(raw)

    if am.form_id != form_id:
        raise UnauthorizedMapError(
            f"Map form_id mismatch: requested {form_id!r}, file declared {am.form_id!r}"
        )
    if form_version and am.form_version != form_version:
        raise UnauthorizedMapError(
            f"Map form_version mismatch for {form_id!r}: "
            f"requested {form_version!r}, file declared {am.form_version!r}"
        )

    _verify_no_duplicate_coordinates(am)
    return am


def _verify_no_duplicate_coordinates(am: ApprovalMap) -> None:
    seen: dict[tuple[int, int, int], str] = {}
    for fid, field in am.fields.items():
        if field.field_id != fid:
            raise UnauthorizedMapError(
                f"Field key {fid!r} does not match field.field_id {field.field_id!r}"
            )
        coord = (field.table_index, field.row, field.col)
        if coord in seen:
            raise UnauthorizedMapError(
                f"Duplicate coordinate {coord} on fields {seen[coord]!r} and {fid!r}"
            )
        seen[coord] = fid


def list_available_forms() -> list[str]:
    return sorted(p.stem for p in MAPS_DIR.glob("*.json") if not p.name.endswith(".approval_map.json"))


def write_authority_matrix(am: ApprovalMap) -> dict[str, dict[str, object]]:
    """Flat matrix: every authorized cell -> coordinate + metadata.

    This is the only object Layer 4 trusts when deciding 'am I allowed to write here?'.
    """
    out: dict[str, dict[str, object]] = {}
    for fid, field in am.fields.items():
        out[fid] = {
            "field_id": fid,
            "table_index": field.table_index,
            "row": field.row,
            "col": field.col,
            "required": field.required,
            "cell_role": field.cell_role,
            "label": field.label,
            "write_mode": getattr(field, "write_mode", "replace"),
            "authority": "exact_approval_map",
        }
    return out
