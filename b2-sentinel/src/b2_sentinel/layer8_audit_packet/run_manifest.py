"""Top-level run manifest writer."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from ..core.models import RunManifest
from ..core.status import FinalStatus


def make_manifest(
    *,
    run_id: str,
    started_at: datetime,
    finished_at: datetime,
    forms: list[str],
    artifacts: dict[str, list[str]],
    final_statuses: dict[str, FinalStatus],
    errors: dict[str, str] | None = None,
) -> RunManifest:
    errors = errors or {}
    overall = (
        len(final_statuses) == len(forms)
        and not errors
        and all(s is FinalStatus.SUCCESS for s in final_statuses.values())
    )
    return RunManifest(
        run_id=run_id,
        started_at=started_at,
        finished_at=finished_at,
        forms=forms,
        artifacts=artifacts,
        final_statuses=final_statuses,
        overall_passed=overall,
        errors=errors,
    )


def write_manifest(manifest: RunManifest, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(manifest.model_dump_json(indent=2), encoding="utf-8")
