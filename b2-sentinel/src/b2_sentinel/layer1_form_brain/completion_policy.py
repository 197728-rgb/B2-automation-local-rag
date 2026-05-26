"""Completion Blocker Policy.

Per-field rules answering: "if this field is missing, does the form's
completion fail?" Defaults: required + evidence_required + no N-A allowance
= blocker. Forms can override via schemas/na_policy/.
"""
from __future__ import annotations

import json
from pathlib import Path

from ..core.paths import NA_POLICY_DIR


def na_policy_path(form_id: str) -> Path:
    return NA_POLICY_DIR / f"{form_id}.json"


def load_na_policy(form_id: str) -> dict[str, dict]:
    """Load approved N/A policy for a form. Returns {field_id: policy_entry}."""
    p = na_policy_path(form_id)
    if not p.exists():
        return {}
    with p.open(encoding="utf-8") as fh:
        data = json.load(fh)
    fields = data.get("fields", {})
    if not isinstance(fields, dict):
        raise ValueError(f"N/A policy for {form_id} has malformed 'fields' section")
    return fields


def is_completion_blocker(
    *,
    required: bool,
    n_a_approved: bool,
    evidence_present: bool,
    optional: bool,
) -> bool:
    """Pure rule used by Layer 1 + Layer 6.

    The job is incomplete if a required field has no evidence AND no
    approved N/A. Optional fields never block.
    """
    if optional or not required:
        return False
    if evidence_present:
        return False
    if n_a_approved:
        return False
    return True
