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
    assert "fill-b24-rl1-sample" in r.stdout
    assert "fill-b24-rl1-from-docupipe" in r.stdout
    assert "inbox" in r.stdout


def test_b2_inbox_help_defaults_to_local_review():
    r = _run_cli(["inbox", "--help"])
    assert r.returncode == 0
    assert "--legacy-docupipe" in r.stdout
    assert "B24_RL2" in r.stdout
    assert "B81" in r.stdout
    assert "B89" in r.stdout
    assert "B90" in r.stdout
    assert "Cover_Page" in r.stdout


def test_b2_discover_no_templates_dir(tmp_path):
    r = _run_cli(
        ["discover"],
        cwd=tmp_path,
        env={"B2_PROJECT_ROOT": str(tmp_path)},
    )
    assert r.returncode == 2
