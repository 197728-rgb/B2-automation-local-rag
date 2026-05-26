"""End-to-end integration test.

Runs the full pipeline for B89 against the sample inbox and verifies that
the audit packet directory is created with the exact artifact contract.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from b2_sentinel.core.paths import TEMPLATES_DIR, MAPS_DIR, INBOX_DIR


EXPECTED_B89_ARTIFACTS = {
    "B89_filled.docx",
    "completion_report.json",
    "conflicts.json",
    "evidence_debt_ledger.json",
    "field_traceability.json",
    "low_confidence.json",
    "manual_correction_log.json",
    "missing_required_fields.json",
    "na_exception_log.json",
    "review.json",
    "review.md",
    "rollover_decisions.json",
    "run_delta.json",
    "source_evidence_index.json",
    "structure_guard_report.json",
}


@pytest.mark.skipif(
    not (MAPS_DIR / "B89.json").exists(),
    reason="B89 approval map not present",
)
@pytest.mark.skipif(
    not TEMPLATES_DIR.exists() or not any(TEMPLATES_DIR.glob("B89*.docx")),
    reason="B89 template DOCX not present",
)
class TestEndToEnd:
    def test_pipeline_b89_produces_contract_artifacts(self, tmp_path: Path):
        from b2_sentinel.pipeline import run_form

        output_dir = tmp_path / "outputs"
        run_id = "test_run"
        result = run_form(
            "B89",
            run_id=run_id,
            inbox=INBOX_DIR,
            outputs_dir=output_dir,
        )

        form_dir = output_dir / run_id / "B89"
        assert form_dir.exists(), "Expected B89 output directory"

        actual = {p.name for p in form_dir.iterdir() if p.is_file()}
        missing = EXPECTED_B89_ARTIFACTS - actual
        assert not missing, f"Missing expected artifacts: {sorted(missing)}"
        assert len(EXPECTED_B89_ARTIFACTS) == 15

        filled = form_dir / "B89_filled.docx"
        assert filled.exists(), "Expected filled DOCX"
        assert filled.stat().st_size > 10_000, "Filled DOCX is unexpectedly small"

        completion = json.loads((form_dir / "completion_report.json").read_text(encoding="utf-8"))
        assert completion["overall_passed_format"] is True
        assert completion["overall_passed_completion"] is True
        assert completion["overall_passed"] is True

        sg = json.loads((form_dir / "structure_guard_report.json").read_text(encoding="utf-8"))
        assert sg["structure_guard_passed"] is True, f"Structure guard failed: {sg.get('notes', [])}"

        assert result.form_id == "B89"
        assert result.overall_passed is True
        assert result.final_status.value == "success"

    def test_manifest_records_errors_field(self, tmp_path: Path):
        from datetime import datetime
        from b2_sentinel.core.status import FinalStatus
        from b2_sentinel.layer8_audit_packet.run_manifest import make_manifest, write_manifest

        manifest = make_manifest(
            run_id="manifest_test",
            started_at=datetime.now(),
            finished_at=datetime.now(),
            forms=["B89", "B81"],
            artifacts={"B89": ["completion_report.json"], "B81": []},
            final_statuses={"B89": FinalStatus.SUCCESS, "B81": FinalStatus.FAILED_RUNTIME_ERROR},
            errors={"B81": "RuntimeError: simulated"},
        )
        assert manifest.overall_passed is False
        assert manifest.errors["B81"] == "RuntimeError: simulated"

        out = tmp_path / "run_manifest.json"
        write_manifest(manifest, out)
        raw = json.loads(out.read_text(encoding="utf-8"))
        assert raw["errors"]["B81"] == "RuntimeError: simulated"
