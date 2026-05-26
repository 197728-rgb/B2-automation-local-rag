"""Required-cell policy overlays for generated template wiring.

Generated maps intentionally start with required=false because DOCX table
inference is structural, not regulatory sign-off. This policy layer promotes
approved field patterns to required obligations without rewriting the generated
approval maps.
"""
from __future__ import annotations

import fnmatch
import json
from functools import lru_cache
from typing import Any

from ..core.paths import SCHEMAS_DIR


POLICY_PATH = SCHEMAS_DIR / "required_policy" / "activity_required_policy.v1.json"


@lru_cache(maxsize=1)
def _load_policy() -> dict[str, Any]:
    if not POLICY_PATH.exists():
        return {"rules": []}
    with POLICY_PATH.open(encoding="utf-8") as fh:
        return json.load(fh)


def promotes_required(form_id: str, field_id: str, label: str) -> bool:
    """Return True when policy promotes this generated field to required."""
    form = form_id.lower()
    field = field_id.lower()
    label_norm = _norm(label)
    for rule in _load_policy().get("rules", []):
        if not _matches_form(rule, form):
            continue
        if _matches_any(field, label_norm, rule.get("optional_field_id_patterns", [])):
            continue
        if _matches_any(field, label_norm, rule.get("required_field_id_patterns", [])):
            return True
        if field_id in set(rule.get("required_field_ids", [])):
            return True
    return False


def _matches_form(rule: dict[str, Any], form: str) -> bool:
    forms = {str(item).lower() for item in rule.get("forms", [])}
    if form in forms:
        return True
    prefixes = [str(item).lower() for item in rule.get("form_prefixes", [])]
    return any(form.startswith(prefix) for prefix in prefixes)


def _matches_any(field: str, label_norm: str, patterns: list[str]) -> bool:
    for raw in patterns:
        pattern = str(raw).lower()
        if fnmatch.fnmatchcase(field, pattern):
            return True
        if fnmatch.fnmatchcase(label_norm, pattern):
            return True
    return False


def _norm(value: str) -> str:
    return "_".join(value.strip().lower().replace("/", " ").replace("-", " ").split())
