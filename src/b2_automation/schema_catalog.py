"""Load DocuPipe-style schema catalogs for Analyst Agent mapping."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from b2_automation.paths import resolve_project_root

_SCHEMA_DIRS = (
    "schemas/ACTIVITYS_SCHEMAS_2026_CLEANED",
    "schemas/activity_2026_cleaned",
)

_FORM_TO_SCHEMA_FILE = {
    "B24_RL2": "B24_strict_corrected.json",
    "B24": "B24_strict_corrected.json",
    "B89": "B89_strict_corrected.json",
    "B90": "B90_strict_corrected.json",
}


def _flatten_paths(data: Any, prefix: str = "") -> list[str]:
    paths: list[str] = []
    if isinstance(data, dict):
        for key, value in data.items():
            path = f"{prefix}.{key}" if prefix else key
            if isinstance(value, (dict, list)):
                paths.extend(_flatten_paths(value, path))
            else:
                paths.append(path)
    elif isinstance(data, list) and data and isinstance(data[0], dict):
        for idx, item in enumerate(data[:3]):
            paths.extend(_flatten_paths(item, f"{prefix}[{idx}]"))
    return paths


def _guess_activity_code(form_id: str) -> str:
    m = re.match(r"^(B\d+)", form_id.upper())
    return m.group(1) if m else form_id


def load_schema_document(root: Path, form_id: str) -> dict[str, Any] | None:
    root = Path(root)
    fname = _FORM_TO_SCHEMA_FILE.get(form_id) or _FORM_TO_SCHEMA_FILE.get(_guess_activity_code(form_id))
    if not fname:
        return None
    for sub in _SCHEMA_DIRS:
        path = root / sub / fname
        if path.is_file():
            return json.loads(path.read_text(encoding="utf-8"))
    return None


def load_available_schemas(root: Path | None = None, form_ids: tuple[str, ...] | None = None) -> list[dict[str, Any]]:
    """Compact schema catalog for LLM Analyst prompts."""
    root = root or resolve_project_root()
    forms = form_ids or tuple(_FORM_TO_SCHEMA_FILE.keys())
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for form_id in forms:
        if form_id in seen:
            continue
        seen.add(form_id)
        doc = load_schema_document(root, form_id)
        if not doc:
            continue
        paths = sorted(set(_flatten_paths(doc)))[:200]
        out.append(
            {
                "schema_id": f"{form_id}_2026",
                "form_id": form_id,
                "activity_code": _guess_activity_code(form_id),
                "paths": paths,
            }
        )
    return out


def infer_schema_path(field_label: str, catalog: list[dict[str, Any]], form_id: str) -> tuple[str | None, float]:
    """Heuristic schema path from label keywords."""
    label = field_label.lower()
    entry = next((c for c in catalog if c.get("form_id") == form_id or c.get("activity_code") == _guess_activity_code(form_id)), None)
    if not entry:
        return None, 0.0
    paths: list[str] = entry.get("paths") or []
    rules: list[tuple[str, str]] = [
        (r"tco|owner|station|facility", "demonstration.station"),
        (r"car mark|car number", "demonstration.carNumber"),
        (r"tank.*spec|stencil", "demonstration.carType"),
        (r"pitp.*name|document name", "pitp"),
        (r"pitp.*id", "pitp"),
        (r"approved by", "pitpApprovedBy"),
        (r"date approved", "welding.welderQualification.qualificationDate"),
        (r"permission|instruction", "tco.instructions"),
        (r"form 4-2|aar", "aar.form42Number"),
        (r"wps", "welding.wps.number"),
        (r"material", "insertRepair.specimenPlate"),
        (r"mtr", "insertRepair.specimenPlate"),
    ]
    for pattern, path in rules:
        if re.search(pattern, label):
            if path in paths or any(p.endswith(path.split(".")[-1]) for p in paths):
                return path, 0.75
            return path, 0.55
    for p in paths:
        if any(tok in p.lower() for tok in label.split() if len(tok) > 3):
            return p, 0.45
    return None, 0.0
