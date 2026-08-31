#!/usr/bin/env python3
"""Run the AAR regression suite.

Every test asserts both halves: the known-bad case MUST produce findings, and the
known-good case MUST produce none. A control that rejects everything is not a control,
which is why the good half is mandatory.

Exit code 0 = suite passed. Exit code 1 = at least one control is not working.

    python run_regression.py [--json]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import validators

ROOT = Path(__file__).resolve().parent


def _load(rel: str) -> dict:
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def run() -> tuple[list[dict], bool]:
    manifest = _load("regression_manifest.json")
    results, ok = [], True

    for test in manifest["tests"]:
        check = getattr(validators, test["check"])
        incident = test["protects_against"]
        expected = _load(test["expected"])

        bad = check(_load(test["known_bad"]))
        good = check(_load(test["known_good"]))

        bad_outcome = "FAIL" if bad else "PASS"
        good_outcome = "FAIL" if good else "PASS"
        bad_ok = bad_outcome == expected["known_bad"]
        good_ok = good_outcome == expected["known_good"]
        passed = bad_ok and good_ok
        ok = ok and passed

        problems = []
        if not bad_ok:
            problems.append(f"known-bad was not caught (expected {expected['known_bad']})")
        if not good_ok:
            problems.append(
                "known-good was rejected: "
                + "; ".join(f.detail for f in good)
            )

        results.append({
            "test": test["id"], "incident": incident, "check": test["check"],
            "known_bad": bad_outcome, "known_good": good_outcome,
            "status": "PASS" if passed else "BROKEN",
            "caught": [f.as_dict() for f in bad],
            "problems": problems,
        })
    return results, ok


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    args = parser.parse_args()

    results, ok = run()

    if args.json:
        print(json.dumps({"passed": ok, "results": results}, indent=2))
        return 0 if ok else 1

    width = max(len(r["test"]) for r in results)
    print(f"{'TEST'.ljust(width)}  INCIDENT    BAD   GOOD  STATUS")
    print("-" * (width + 34))
    for r in results:
        print(f"{r['test'].ljust(width)}  {r['incident']}  "
              f"{r['known_bad']:<5} {r['known_good']:<5} {r['status']}")
        for problem in r["problems"]:
            print(f"{' ' * (width + 2)}  !! {problem}")

    total = len(results)
    broken = [r for r in results if r["status"] != "PASS"]
    print()
    if broken:
        print(f"{len(broken)} of {total} controls are NOT working. "
              "An incident with a broken control is not prevented.")
        return 1
    print(f"All {total} controls working: every known-bad case fails, "
          "every known-good case passes.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
