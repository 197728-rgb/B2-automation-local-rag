"""N/A Policy loader.

Reads schemas/na_policy/<form_id>.json. The file shape:
    {
        "form_id": "B89",
        "fields": {
            "test_fixture.weld.length": {
                "reason": "No weld length applicable to this activity condition",
                "policy_id": "NA-B89-WELD-LEN-001",
                "approved_by": "approved_exception_policy"
            }
        }
    }
"""
from __future__ import annotations

import json
from pathlib import Path

from ..core.paths import NA_POLICY_DIR


def load_policy(form_id: str) -> dict[str, dict]:
    p = NA_POLICY_DIR / f"{form_id}.json"
    if not p.exists():
        return {}
    with p.open(encoding="utf-8") as fh:
        data = json.load(fh)
    fields = data.get("fields", {})
    if not isinstance(fields, dict):
        return {}
    return fields
