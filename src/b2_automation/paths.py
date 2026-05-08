"""Resolve project root (repo directory containing templates/ and pyproject.toml)."""

from __future__ import annotations

import os
from pathlib import Path

# Physical Word package kept under templates/: RL2 is canonical; legacy RL1 sample/DocuPipe
# helpers use this same file (shared table layout—no separate B24_RL1.docx in templates/).
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
