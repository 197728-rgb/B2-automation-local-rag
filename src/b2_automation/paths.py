"""Resolve project root (repo directory containing templates/ and pyproject.toml)."""

from __future__ import annotations

import os
from pathlib import Path

# Physical Word package kept under templates/: shared B24 table layout for RL2 production fills.
B24_SHARED_TEMPLATE_DOCX = "B24_RL2.docx"


def resolve_project_root() -> Path:
    """Root used for templates/, outputs/, and inputs/."""
    env = os.environ.get("B2_PROJECT_ROOT", "").strip()
    if env:
        return Path(env).resolve()

    cwd = Path.cwd().resolve()
    for base in (cwd, *cwd.parents):
        if (base / "pyproject.toml").is_file() and (base / "templates").is_dir():
            return base

    pkg = Path(__file__).resolve().parent
    for base in (pkg.parent.parent, *pkg.parents):
        if (base / "templates").is_dir():
            return base.resolve()

    return cwd
