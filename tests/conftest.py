"""Test harness defaults for locked-down Windows workspaces."""

from __future__ import annotations

import os
from pathlib import Path


_repo_root = Path(__file__).resolve().parents[1]
_temp_root = _repo_root / ".pytest_tmp_root"
_temp_root.mkdir(exist_ok=True)
os.environ.setdefault("PYTEST_DEBUG_TEMPROOT", str(_temp_root))
