"""Innovation 7 - Run-to-Run Delta.

Compares the current completion report against the most recent prior
completion_report.json under outputs/ and emits a RunDelta noting which
blockers were resolved, which remain, and which are new.
"""
from __future__ import annotations

import json
from pathlib import Path

from ..core.models import (
    CompletionReport,
    RunDelta,
)
from ..core.status import FinalStatus


def find_previous_report(form_id: str, outputs_dir: Path, current_run_id: str) -> Path | None:
    if not outputs_dir.exists():
        return None
    candidates: list[Path] = []
    for run_dir in outputs_dir.iterdir():
        if not run_dir.is_dir():
            continue
        if run_dir.name == current_run_id:
            continue
        rep = run_dir / form_id / "completion_report.json"
        if rep.exists():
            candidates.append(rep)
    if not candidates:
        return None
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0]


def compute_run_delta(
    *,
    current: CompletionReport,
    previous_path: Path | None,
) -> RunDelta:
    if previous_path is None:
        return RunDelta(
            previous_status=None,
            current_status=current.final_status,
            remaining_blockers=list(current.blockers),
            net_progress="unchanged",
        )

    try:
        with previous_path.open(encoding="utf-8") as fh:
            previous = json.load(fh)
    except (OSError, json.JSONDecodeError):
        return RunDelta(
            previous_status=None,
            current_status=current.final_status,
            remaining_blockers=list(current.blockers),
            net_progress="unchanged",
        )

    prev_blockers = set(previous.get("blockers", []))
    curr_blockers = set(current.blockers)
    resolved = sorted(prev_blockers - curr_blockers)
    new = sorted(curr_blockers - prev_blockers)
    remaining = sorted(prev_blockers & curr_blockers)

    if resolved and not new:
        net = "improved"
    elif new and not resolved:
        net = "regressed"
    elif resolved and new:
        net = "improved" if len(resolved) >= len(new) else "regressed"
    else:
        net = "unchanged"

    try:
        prev_status = FinalStatus(previous.get("final_status"))
    except (ValueError, TypeError):
        prev_status = None

    return RunDelta(
        previous_status=prev_status,
        current_status=current.final_status,
        resolved_blockers=resolved,
        remaining_blockers=remaining,
        new_blockers=new,
        net_progress=net,
    )
