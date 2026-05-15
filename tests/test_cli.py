"""CLI smoke tests."""

import json
import os
import subprocess
import sys
import zipfile
from pathlib import Path

from docx import Document

_REPO = Path(__file__).resolve().parents[1]


def _run_cli(args: list[str], *, cwd: Path | None = None, env: dict | None = None):
    env = {**os.environ, "PYTHONPATH": str(_REPO / "src"), **(env or {})}
    return subprocess.run(
        [sys.executable, "-m", "b2_automation.cli", *args],
        capture_output=True,
        text=True,
        check=False,
        cwd=cwd or _REPO,
        env=env,
    )


def _docx_text(path: Path) -> str:
    doc = Document(str(path))
    return "\n".join(cell.text for table in doc.tables for row in table.rows for cell in row.cells)


def test_b2_help():
    r = _run_cli(["--help"])
    assert r.returncode == 0
    assert "discover" in r.stdout
    assert "sample-pipeline" in r.stdout
    assert "inbox" in r.stdout


def test_b2_inbox_help_defaults_to_local_review():
    r = _run_cli(["inbox", "--help"])
    assert r.returncode == 0
    assert "B24_RL2" in r.stdout
    assert "B81" in r.stdout
    assert "B89" in r.stdout
    assert "B90" in r.stdout
    assert "Cover_Page" in r.stdout


def test_b2_inbox_rejects_unknown_review_form(tmp_path):
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    (inbox / "evidence.txt").write_text("B91 evidence", encoding="utf-8")
    r = _run_cli(["inbox", "--inbox", str(inbox), "--out", str(tmp_path / "out"), "--review-forms", "B91"])
    assert r.returncode == 2
    assert "Unknown review form 'B91'" in r.stderr
    assert "valid --review-forms choices" in r.stderr
    assert "B24_RL2" in r.stderr


def test_b2_inbox_rejects_b24_rl1_review_form(tmp_path):
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    (inbox / "evidence.txt").write_text("evidence", encoding="utf-8")
    r = _run_cli(["inbox", "--inbox", str(inbox), "--out", str(tmp_path / "out"), "--review-forms", "B24_RL1"])
    assert r.returncode == 2
    assert "Unknown review form 'B24_RL1'" in r.stderr


def test_b2_inbox_accepts_comma_separated_review_forms(tmp_path):
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    (inbox / "evidence.txt").write_text("facility: Demo Shop\ndate: 2026-01-05", encoding="utf-8")
    r = _run_cli([
        "inbox",
        "--inbox",
        str(inbox),
        "--out",
        str(tmp_path / "out"),
        "--review-forms",
        "B81,B89",
    ])
    assert r.returncode in {0, 1}
    assert "Status:" in r.stdout


def test_b2_discover_no_templates_dir(tmp_path):
    r = _run_cli(
        ["discover"],
        cwd=tmp_path,
        env={"B2_PROJECT_ROOT": str(tmp_path)},
    )
    assert r.returncode == 2


def test_b2_inbox_zip_b24_end_to_end_quality_gate(tmp_path):
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    fixture = (_REPO / "tests" / "fixtures" / "dlga_b24_table_pairs_fixture.txt").read_text(encoding="utf-8")
    with zipfile.ZipFile(inbox / "inbox.zip", "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("DLGA-B24_table_pairs.txt", fixture)

    out_dir = tmp_path / "out"
    r = _run_cli(["inbox", "--inbox", str(inbox), "--out", str(out_dir), "--review-forms", "B24_RL2"])
    assert r.returncode == 0
    assert "Status: review_required" in r.stdout

    manifest = json.loads((out_dir / "run_manifest.json").read_text(encoding="utf-8"))
    review = json.loads((out_dir / "review" / "local_rag_review.json").read_text(encoding="utf-8"))
    structure_guard = json.loads((out_dir / "structure_guard_report.json").read_text(encoding="utf-8"))
    b24_docx = next(item for item in manifest["docx_generation"] if item["form_id"] == "B24_RL2")

    assert structure_guard["pass"] is True
    assert manifest["structure_guard_passed"] is True
    assert b24_docx["status"] == "filled"

    selected = {row["field_id"]: row["selected_value"] for row in review["form_packets"]["B24_RL2"]["field_decisions"]}
    assert selected["facility_name"] == "CIT"
    assert selected["tco_permission_date"] == "5/20/2024"
    assert selected["pitp_document_name"] == "PITP"
    assert selected["tank_design_spec"] == "DOT111A100W1 / AAR211A100W1"
    assert selected["four_two_drawing_number"] == "D43520"
    assert set(manifest["manual_fields"]["B24_RL2"]) == {"test_plate_tank_material", "test_plate_tank_mtr", "attachment_material"}

    text = _docx_text(Path(b24_docx["filled_docx"])).lower()
    for junk in ("day where the action", "a):", "malformed ocr fragment"):
        assert junk not in text


def test_b2_inbox_zip_b24_rejects_prose_for_numeric_and_date_cells(tmp_path):
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    fixture = "\n".join(
        [
            "[structured_docx_table_evidence]",
            "Tank Car Owner (TCO) Name: CIT",
            "Date Permission/Instruction Received from TCO: 5/20/2024",
            "Written Instructions from TCO: Facility received written confirmation from owner Allowing FACILITY Procedures.",
            "PITP Document Name: PITP",
            "PITP ID: should follow owner guidance in procedure",
            "Date Approved: day where the action",
            "AAR Form 4-2 (AAR No.): see owner email thread",
            "Drawing Number: as noted by inspector in general prose",
            "Car Mark and Number: DBUX 250086",
            "Tank Car Design Spec/Stencil Spec: DOT111A100W1 / AAR211A100W1",
        ]
    )
    with zipfile.ZipFile(inbox / "inbox.zip", "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("DLGA-B24_prose_noise.txt", fixture)

    out_dir = tmp_path / "out"
    r = _run_cli(["inbox", "--inbox", str(inbox), "--out", str(out_dir), "--review-forms", "B24_RL2"])
    assert r.returncode == 0

    manifest = json.loads((out_dir / "run_manifest.json").read_text(encoding="utf-8"))
    b24_docx = next(item for item in manifest["docx_generation"] if item["form_id"] == "B24_RL2")
    manual = set(manifest["manual_fields"]["B24_RL2"])
    assert {"pitp_id", "pitp_date_approved", "aar_form_4_2_number", "four_two_drawing_number"} <= manual

    text = _docx_text(Path(b24_docx["filled_docx"])).lower()
    for junk in (
        "day where the action",
        "should follow owner guidance in procedure",
        "see owner email thread",
        "as noted by inspector in general prose",
    ):
        assert junk not in text
