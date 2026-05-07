"""M-1002 template registry (48 Karen B-2 blanks) + legacy classifier -> template key."""
from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path

_CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"
_REGISTRY_PATH = _CONFIG_DIR / "m1002_template_registry.json"

# Minimal fallback if registry JSON is missing (old 9-template layout).
_FALLBACK_TEMPLATES: dict[str, str] = {
    "C5I": "C5I.docx",
    "C5S": "C5S.docx",
    "C5V": "C5V.docx",
    "C6R": "C6R.docx",
    "B89": "B89.docx",
    "C7": "C7_C8_C10.docx",
    "C8": "C7_C8_C10.docx",
    "C10": "C7_C8_C10.docx",
    "C7_C8_C10": "C7_C8_C10.docx",
}


@lru_cache
def _registry_payload() -> dict:
    if not _REGISTRY_PATH.is_file():
        return {}
    return json.loads(_REGISTRY_PATH.read_text(encoding="utf-8"))


def template_map() -> dict[str, str]:
    """form_code -> filename under forms_dir."""
    data = _registry_payload()
    m = data.get("templates")
    if isinstance(m, dict) and m:
        return dict(m)
    return dict(_FALLBACK_TEMPLATES)


def legacy_to_registry_map() -> dict[str, str]:
    data = _registry_payload()
    m = data.get("legacy_to_registry")
    out = dict(m) if isinstance(m, dict) else {}
    if not out and _FALLBACK_TEMPLATES:
        # Old 9-code layout: keys are both registry and legacy
        return {k: k for k in _FALLBACK_TEMPLATES}
    return out


def default_registry_key() -> str:
    data = _registry_payload()
    return str(data.get("default_registry_key") or "C5_V")


def resolve_form_code(raw: str | None) -> str:
    """
    Map legacy classifier code (e.g. C5V), explicit override, or registry key to canonical template key.
    Unknown values fall back to default_registry_key().
    """
    templates = template_map()
    legacy = legacy_to_registry_map()
    default = default_registry_key()
    if not raw:
        return default
    r = str(raw).strip()
    if r in templates:
        return r
    if r in legacy:
        return legacy[r]
    ru = r.upper()
    by_upper = {k.upper(): k for k in templates}
    if ru in by_upper:
        return by_upper[ru]
    for lk, vk in legacy.items():
        if lk.upper() == ru:
            return vk
    return default


def all_template_keys() -> list[str]:
    return sorted(template_map().keys())


def clear_registry_cache() -> None:
    _registry_payload.cache_clear()


if __name__ == "__main__":
    # Health check: M-1002 DOCX registry only. Evidence → spreadsheet columns live in the
    # audit_evidence_extractor consolidated_field_map pipeline, not here.
    print("=== M-1002 template registry (DOCX filenames) ===")
    print(f"Registry JSON: {_REGISTRY_PATH}")
    print(f"Default registry key: {default_registry_key()}")
    mapping = template_map()
    print(f"Template entries: {len(mapping)}\n")
    print(json.dumps(mapping, indent=2, default=str))
