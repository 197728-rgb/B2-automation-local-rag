"""Structure guard outcomes for local inbox runs (Stage 7)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from b2_automation.inbox_pipeline import run_inbox_pipeline


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_inbox_local_structure_guard_failure_recorded(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = _repo_root()
    template = root / "templates" / "B24_RL1.docx"
    if not template.is_file():
        pytest.skip(f"missing template: {template}")

    inbox = tmp_path / "inbox"
    inbox.mkdir()
    (inbox / "packet_one.txt").write_text(
        "\n".join(
            [
                "Cover Page Facility: Midwest Tank Rail Inc",
                "B24 RL2 objective evidence Date: 2026-05-07",
                "B81 stub sill evidence Car: DOTX 123456",
            ]
        ),
        encoding="utf-8",
    )

    def _fake_patch(*args: object, **kwargs: object):
        from pathlib import Path as P

        from b2_automation.ooxml_writer import PatchOutcome

        outp = kwargs.get("output_path")
        if outp is None and len(args) > 3:
            outp = args[3]
        path = P(outp)  # type: ignore[arg-type]
        return PatchOutcome(
            output_docx=path.resolve(),
            structure_guard_report=None,
            structure_guard_passed=False,
            patched_fields=(),
            errors=("injected structure guard failure",),
        )

    monkeypatch.setattr("b2_automation.inbox_pipeline.patch_docx_cells", _fake_patch)

    result = run_inbox_pipeline(root=root, inbox=inbox, out_dir=tmp_path / "run")
    assert result.status == "review_required"
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    failed = manifest.get("structure_guard_failed_forms") or []
    assert len(failed) >= 1
    review = json.loads(result.review_json_path.read_text(encoding="utf-8"))
    assert review.get("structure_guard_failed_forms")
    assert manifest.get("structure_guard_passed") is False
