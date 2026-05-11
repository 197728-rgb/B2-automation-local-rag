"""CLI smoke tests."""

import os
import subprocess
import sys
from pathlib import Path

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
