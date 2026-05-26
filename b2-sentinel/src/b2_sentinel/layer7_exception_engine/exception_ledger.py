"""NA Exception Log writer."""
from __future__ import annotations

import json
from pathlib import Path

from ..core.models import NAExceptionEntry


def write_exception_log(entries: list[NAExceptionEntry], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "form_id": entries[0].field_id.split(".")[0] if entries else None,
        "count": len(entries),
        "entries": [json.loads(e.model_dump_json()) for e in entries],
    }
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
