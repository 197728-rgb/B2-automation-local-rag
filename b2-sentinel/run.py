#!/usr/bin/env python3
"""B2 SENTINEL one-command runner.

Usage:
    python run.py                          # all 5 forms, default inbox/outputs
    python run.py --form B89               # single form
    python run.py --inbox custom/ --output runs/
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
SRC = REPO_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from b2_sentinel.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
