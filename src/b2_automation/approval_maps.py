"""Load exact per-form/version approval maps for OOXML writes (Stage 6).

No fuzzy resolution: each map file must exist at schemas/maps/<form_id>.json.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping


@dataclass(frozen=True)
class ApprovalBundle:
    manifest: Mapping[str, Any]
    approval_map: Mapping[str, Any]
    template_path: Path
    map_path: Path


def load_exact_approval_bundle(root: Path, form_id: str) -> ApprovalBundle | None:
    """Return manifest + approval map + template path, or None if missing or invalid."""
    map_path = _find_exact_map_path(root, form_id)
    if map_path is None:
        return None
    bundle_file = json.loads(map_path.read_text(encoding="utf-8"))
    if str(bundle_file.get("form_id")) != form_id:
        return None
    manifest_rel = bundle_file.get("manifest_path") or bundle_file.get("manifest_relative")
    template_rel = bundle_file.get("template_path") or bundle_file.get("template_relative")
    template_name = bundle_file.get("template")
    if not template_rel and template_name:
        template_rel = f"templates/{template_name}"
    if not template_rel:
        return None
    template_path = (root / str(template_rel)).resolve()
    fields = bundle_file.get("fields")
    if not isinstance(fields, dict) or not fields:
        return None
    if manifest_rel:
        manifest_path = (root / str(manifest_rel)).resolve()
        if not manifest_path.is_file():
            return None
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    else:
        manifest = {
            "form_id": form_id,
            "template": template_path.name,
            "cells": list(fields.values()),
        }
    approval_for_writer = {
        "form_id": bundle_file.get("form_id"),
        "form_version": bundle_file.get("form_version"),
        "fields": fields,
    }
    return ApprovalBundle(manifest=manifest, approval_map=approval_for_writer, template_path=template_path, map_path=map_path)


def _find_exact_map_path(root: Path, form_id: str) -> Path | None:
    candidates = (
        root / "schemas" / "maps" / f"{form_id}.approval_map.json",
        root / "schemas" / "maps" / f"{form_id}.json",
    )
    for path in candidates:
        if path.is_file():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            if data.get("fields") and data.get("form_id") == form_id:
                return path
    return None
