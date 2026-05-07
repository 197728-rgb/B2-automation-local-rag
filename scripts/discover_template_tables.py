"""Backward-compatible wrapper; prefer `b2 discover` after `pip install -e .`."""

from pathlib import Path
import sys

_repo = Path(__file__).resolve().parents[1]
_src = _repo / "src"
if _src.is_dir():
    sys.path.insert(0, str(_src))

from b2_automation.discover import run_discovery
from b2_automation.paths import resolve_project_root

if __name__ == "__main__":
    for path in run_discovery(root=resolve_project_root()):
        print(f"Wrote {path}")
