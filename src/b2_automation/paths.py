"""Resolve project root (repo directory containing templates/ and pyproject.toml)."""

from __future__ import annotations

import os
from pathlib import Path


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
