"""Tests for the Run-to-Run Delta innovation."""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from b2_sentinel.core.models import CompletionReport, RunDelta
from b2_sentinel.core.status import FinalStatus
from b2_sentinel.innovations.run_delta import compute_run_delta


def _report(
    blockers: list[str],
    status: FinalStatus = FinalStatus.BLOCKED_PENDING_NO_SOURCE_OR_NA_RESOLUTION,
) -> CompletionReport:
    return CompletionReport(
        form_id="B89",
        overall_passed_format=True,
        overall_passed_completion=(status == FinalStatus.SUCCESS),
        overall_passed=(status == FinalStatus.SUCCESS),
        final_status=status,
        required_total=10,
        required_filled=10 - len(blockers),
        required_blocked=len(blockers),
        review_required_count=0,
        conflict_count=0,
        low_confidence_count=0,
        approved_na_count=0,
        blocked_no_source_count=len(blockers),
        blocked_unauthorized_count=0,
        blockers=blockers,
    )


def _write_prev(report: CompletionReport) -> Path:
    tmp = Path(tempfile.mktemp(suffix=".json"))
    tmp.write_text(report.model_dump_json(indent=2), encoding="utf-8")
    return tmp


class TestRunDelta:
    def test_improved_when_blocker_resolved(self):
        prev = _report(blockers=["car.mark", "aar.form_4_2.number"])
        curr = _report(blockers=["aar.form_4_2.number"])
        prev_path = _write_prev(prev)
        try:
            delta = compute_run_delta(current=curr, previous_path=prev_path)
            assert delta.net_progress == "improved"
            assert "car.mark" in delta.resolved_blockers
        finally:
            prev_path.unlink(missing_ok=True)

    def test_regressed_when_new_blocker_added(self):
        prev = _report(blockers=["car.mark"])
        curr = _report(blockers=["car.mark", "new.field"])
        prev_path = _write_prev(prev)
        try:
            delta = compute_run_delta(current=curr, previous_path=prev_path)
            assert delta.net_progress == "regressed"
            assert "new.field" in delta.new_blockers
        finally:
            prev_path.unlink(missing_ok=True)

    def test_unchanged_when_same_blockers(self):
        prev = _report(blockers=["car.mark"])
        curr = _report(blockers=["car.mark"])
        prev_path = _write_prev(prev)
        try:
            delta = compute_run_delta(current=curr, previous_path=prev_path)
            assert delta.net_progress == "unchanged"
            assert len(delta.resolved_blockers) == 0
            assert len(delta.new_blockers) == 0
        finally:
            prev_path.unlink(missing_ok=True)

    def test_no_previous_report(self):
        curr = _report(blockers=["car.mark"])
        delta = compute_run_delta(current=curr, previous_path=None)
        assert delta.previous_status is None
        assert delta.net_progress == "unchanged"

    def test_success_from_blocked(self):
        prev = _report(blockers=["car.mark"], status=FinalStatus.BLOCKED_PENDING_NO_SOURCE_OR_NA_RESOLUTION)
        curr = _report(blockers=[], status=FinalStatus.SUCCESS)
        prev_path = _write_prev(prev)
        try:
            delta = compute_run_delta(current=curr, previous_path=prev_path)
            assert delta.net_progress == "improved"
            assert "car.mark" in delta.resolved_blockers
        finally:
            prev_path.unlink(missing_ok=True)
