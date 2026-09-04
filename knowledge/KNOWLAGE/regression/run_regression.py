#!/usr/bin/env python3
"""Run the regression suite defined in fixtures.json.

Both halves are asserted: the known-bad case MUST produce findings, and the known-good
case MUST produce none. A control that rejects everything is not a control.

Exit 0 = every control works. Exit 1 = at least one control is not working.

    python run_regression.py [--json]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import validators

ROOT = Path(__file__).resolve().parent


def run() -> tuple[list[dict], bool]:
    suite = json.loads((ROOT / "fixtures.json").read_text(encoding="utf-8"))
    results, ok = [], True
    for test in suite["tests"]:
        check = getattr(validators, test["check"])
        bad, good = check(test["known_bad"]), check(test["known_good"])
        passed = bool(bad) and not good
        ok = ok and passed
        problems = []
        if not bad:
            problems.append("known-bad produced no findings")
        if good:
            problems.append("known-good rejected: " + "; ".join(f.detail for f in good))
        results.append({
            "test": test["id"], "prevents": test["prevents"], "check": test["check"],
            "known_bad": "FAIL" if bad else "PASS",
            "known_good": "FAIL" if good else "PASS",
            "status": "PASS" if passed else "BROKEN",
            "caught": [f.as_dict() for f in bad], "problems": problems,
        })
    return results, ok


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    results, ok = run()

    if args.json:
        print(json.dumps({"passed": ok, "results": results}, indent=2))
        return 0 if ok else 1

    print(f"{'TEST':6}  {'PREVENTS':9}  BAD   GOOD  STATUS")
    print("-" * 42)
    for r in results:
        print(f"{r['test']:6}  {r['prevents']:9}  {r['known_bad']:<5} {r['known_good']:<5} {r['status']}")
        for problem in r["problems"]:
            print(f"        !! {problem}")

    broken = [r for r in results if r["status"] != "PASS"]
    print()
    if broken:
        print(f"{len(broken)} of {len(results)} controls are NOT working.")
        return 1
    print(f"All {len(results)} controls working: every known-bad case fails, "
          "every known-good case passes.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
