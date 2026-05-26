#!/usr/bin/env python3
"""Benchmark harness for SPEC-1 acceptance metrics (evaluation only)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize autonomous run_manifest for MVP metrics")
    parser.add_argument("run_manifest", type=Path, help="Path to run_manifest.json")
    args = parser.parse_args()
    data = json.loads(args.run_manifest.read_text(encoding="utf-8"))
    total = len(data.get("fallback_field_ids", [])) + len(data.get("low_confidence_field_ids", []))
    print(json.dumps({
        "status": data.get("status"),
        "templates_processed": data.get("templates_processed"),
        "structure_guard_passed": data.get("structure_guard_passed"),
        "low_confidence_count": len(data.get("low_confidence_field_ids", [])),
        "fallback_count": len(data.get("fallback_field_ids", [])),
        "human_review_artifacts": data.get("human_review_artifacts"),
        "note": "Compare field-level results against gold JSON for recall/mapping/write metrics",
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
