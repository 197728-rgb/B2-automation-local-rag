"""Load exact per-form/version approval maps for OOXML writes (Stage 6).

Exact coordinate authorization only: manifest cells must match approval ``fields``
entry ``table_index`` / ``row`` / ``col`` per ``field_id``. No nearest-match or
generic fallback maps.

Canonical map path only: ``schemas/maps/<form_id>.json``. Legacy
``*.approval_map.json`` duplicates are ignored by the loader (keep them for human
diff only if needed).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from b2_automation.local_extraction import DEFAULT_REVIEW_FORMS


@dataclass(frozen=True)
class ApprovalBundle:
    manifest: Mapping[str, Any]
    approval_map: Mapping[str, Any]
    template_path: Path
    map_path: Path


@dataclass(frozen=True)
class ApprovalMapLoadResult:
    """Structured result so callers can inspect *why* a load failed."""
    bundle: ApprovalBundle | None
    errors: tuple[str, ...] = ()


def load_exact_approval_bundle(
    root: Path,
    form_id: str,
    *,
    expected_version: str | None = None,
) -> ApprovalBundle | None:
    """Return manifest + approval map + template path, or None if missing or invalid."""
    result = load_exact_approval_bundle_checked(root, form_id, expected_version=expected_version)
    return result.bundle


def load_exact_approval_bundle_checked(
    root: Path,
    form_id: str,
    *,
    expected_version: str | None = None,
) -> ApprovalMapLoadResult:
    """Like ``load_exact_approval_bundle`` but returns structured errors."""
    map_path = _find_exact_map_path(root, form_id)
    if map_path is None:
        return ApprovalMapLoadResult(bundle=None, errors=(f"No approval map found for {form_id}",))

    bundle_file = json.loads(map_path.read_text(encoding="utf-8"))
    errors: list[str] = []

    if str(bundle_file.get("form_id")) != form_id:
        return ApprovalMapLoadResult(bundle=None, errors=(f"form_id mismatch: map has {bundle_file.get('form_id')!r}, expected {form_id!r}",))

    if expected_version is not None:
        map_version = str(bundle_file.get("form_version", ""))
        if map_version != expected_version:
            return ApprovalMapLoadResult(
                bundle=None,
                errors=(f"form_version mismatch: map has {map_version!r}, expected {expected_version!r}",),
            )

    fields = bundle_file.get("fields")
    if not isinstance(fields, dict) or not fields:
        return ApprovalMapLoadResult(bundle=None, errors=("approval map has no fields",))

    fv = bundle_file.get("form_version")
    if form_id in DEFAULT_REVIEW_FORMS:
        if fv is None or not str(fv).strip():
            return ApprovalMapLoadResult(bundle=None, errors=("approval map must declare non-empty form_version",))

    coord_errors = _check_duplicate_coordinates(fields)
    if coord_errors:
        return ApprovalMapLoadResult(bundle=None, errors=tuple(coord_errors))

    manifest_rel = bundle_file.get("manifest_path") or bundle_file.get("manifest_relative")
    template_rel = bundle_file.get("template_path") or bundle_file.get("template_relative")
    template_name = bundle_file.get("template")
    if not template_rel and template_name:
        template_rel = f"templates/{template_name}"
    if not template_rel:
        return ApprovalMapLoadResult(bundle=None, errors=("approval map has no template_path",))

    template_path = (root / str(template_rel)).resolve()

    if not manifest_rel:
        if form_id in DEFAULT_REVIEW_FORMS:
            return ApprovalMapLoadResult(
                bundle=None,
                errors=("approval map must include manifest_path for first-class production forms",),
            )
        manifest = {
            "form_id": form_id,
            "template": template_path.name,
            "cells": list(fields.values()),
        }
    else:
        manifest_path = (root / str(manifest_rel)).resolve()
        if not manifest_path.is_file():
            return ApprovalMapLoadResult(bundle=None, errors=(f"manifest not found: {manifest_path}",))
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    align_errors = _validate_manifest_alignment(fields, manifest, form_id)
    if align_errors:
        return ApprovalMapLoadResult(bundle=None, errors=tuple(align_errors))

    approval_for_writer = {
        "form_id": bundle_file.get("form_id"),
        "form_version": bundle_file.get("form_version"),
        "fields": fields,
    }
    bundle = ApprovalBundle(
        manifest=manifest,
        approval_map=approval_for_writer,
        template_path=template_path,
        map_path=map_path,
    )
    return ApprovalMapLoadResult(bundle=bundle, errors=tuple(errors))


def _validate_manifest_alignment(fields: dict[str, Any], manifest: Mapping[str, Any], form_id: str) -> list[str]:
    """Reject bundles where template manifest cells disagree with approval ``fields``."""
    errors: list[str] = []
    cells = manifest.get("cells") if isinstance(manifest, Mapping) else None
    if not isinstance(cells, list):
        return ["manifest has no cells list"]

    by_fid: dict[str, Mapping[str, Any]] = {}
    for cell in cells:
        if not isinstance(cell, Mapping):
            continue
        fid = str(cell.get("field_id") or "")
        if fid:
            by_fid[fid] = cell

    for fid, spec in fields.items():
        if not isinstance(spec, Mapping):
            errors.append(f"{form_id}/{fid}: field entry is not an object")
            continue
        cell = by_fid.get(str(fid))
        if cell is None:
            errors.append(f"{form_id}/{fid}: field_id missing from manifest cells")
            continue
        try:
            sc = (int(spec["table_index"]), int(spec["row"]), int(spec["col"]))
            mc = (int(cell["table_index"]), int(cell["row"]), int(cell["col"]))
        except (KeyError, TypeError, ValueError) as exc:
            errors.append(f"{form_id}/{fid}: invalid coordinates ({exc})")
            continue
        if sc != mc:
            errors.append(
                f"{form_id}/{fid}: manifest cell {mc} does not match approval map cell {sc}",
            )

    field_keys = {str(k) for k in fields.keys()}
    manifest_keys = set(by_fid.keys())
    extra = manifest_keys - field_keys
    if extra:
        errors.append(f"{form_id}: manifest has field_ids not present in approval map: {sorted(extra)}")
    return errors


def _check_duplicate_coordinates(fields: dict[str, Any]) -> list[str]:
    """Reject maps where two distinct field_ids target the same cell."""
    seen: dict[tuple[int, int, int], str] = {}
    errors: list[str] = []
    for fid, spec in fields.items():
        if not isinstance(spec, dict):
            continue
        try:
            coord = (int(spec["table_index"]), int(spec["row"]), int(spec["col"]))
        except (KeyError, TypeError, ValueError):
            errors.append(f"{fid}: missing or invalid coordinates")
            continue
        prior = seen.get(coord)
        if prior is not None and prior != fid:
            errors.append(f"duplicate coordinate {coord}: {prior!r} and {fid!r} target the same cell")
        else:
            seen[coord] = fid
    return errors


def _find_exact_map_path(root: Path, form_id: str) -> Path | None:
    path = root / "schemas" / "maps" / f"{form_id}.json"
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    if data.get("fields") and data.get("form_id") == form_id:
        return path
    return None
