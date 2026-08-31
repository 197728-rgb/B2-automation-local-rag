#!/usr/bin/env python3
"""The shipping gate. Emits the disposition ledger and decides SHIP / DO NOT SHIP.

Nothing ships on judgment. A run ships when every counter is zero and the regression
suite passes; otherwise it is blocked, and the ledger says exactly why.

    python release_gate.py RUN_RECORD.json [--json]

Exit code 0 = SHIP. Exit code 1 = DO NOT SHIP.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import validators  # noqa: E402

# Each counter is owned by the incidents that produce it, so a non-zero number points
# straight at the ledger entry rather than at a vague "validation failed".
COUNTERS = {
    "UNACCOUNTED SOURCE FACTS": {"AAR-R003", "AAR-R004", "AAR-R010"},
    "UNSUPPORTED TARGET VALUES": {"AAR-R008"},
    "MERGED IDENTITIES": {"AAR-R001", "AAR-R002"},
    "STRUCTURE VIOLATIONS": {"AAR-R006", "AAR-R007"},
    "MACHINE-READABILITY FAILURES": {"AAR-R005"},
}


def build_ledger(record: dict) -> list[dict]:
    """One row per source fact: where it came from, where it went, what happened to it."""
    rows = []
    for fact in record.get("source_facts", []):
        rows.append({
            "source_fact": fact.get("key", "?"),
            "target": fact.get("target", fact.get("key", "?")),
            "disposition": fact.get("disposition", "UNACCOUNTED"),
        })
    for row in record.get("rows", []):
        cells = row.get("cells", {})
        identity = cells.get("name") or cells.get("equipment_name") or "?"
        rows.append({
            "source_fact": f"{identity} ({row.get('kind', 'row')})",
            "target": f"{row.get('table', '?')} row {row.get('row', '?')}",
            "disposition": "WRITTEN",
        })
    return rows


def regression_status() -> tuple[bool, str]:
    runner = ROOT / "run_regression.py"
    try:
        result = subprocess.run(
            [sys.executable, str(runner), "--json"],
            capture_output=True, text=True, cwd=runner.parent, timeout=120,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return False, f"regression suite could not run: {exc}"
    if result.returncode == 0:
        return True, "all controls working"
    try:
        broken = [r["test"] for r in json.loads(result.stdout)["results"]
                  if r["status"] != "PASS"]
        return False, "broken controls: " + ", ".join(broken)
    except (ValueError, KeyError):
        return False, "regression suite failed"


def evaluate(record: dict) -> dict:
    findings = validators.run_all(record)

    counts = {name: 0 for name in COUNTERS}
    unattributed = 0
    for finding in findings:
        for name, incidents in COUNTERS.items():
            if finding.incident in incidents:
                counts[name] += 1
                break
        else:
            unattributed += 1
    if unattributed:
        counts["OTHER BLOCKING FINDINGS"] = unattributed

    suite_ok, suite_detail = regression_status()
    ship = all(value == 0 for value in counts.values()) and suite_ok

    return {
        "ledger": build_ledger(record),
        "counters": counts,
        "regression": {"passed": suite_ok, "detail": suite_detail},
        "findings": [f.as_dict() for f in findings],
        "decision": "SHIP" if ship else "DO NOT SHIP",
    }


def render(report: dict) -> str:
    out = ["DISPOSITION LEDGER", ""]
    ledger = report["ledger"]
    if ledger:
        w1 = max(len(r["source_fact"]) for r in ledger) + 2
        w2 = max(len(str(r["target"])) for r in ledger) + 2
        out.append(f"{'SOURCE FACT'.ljust(w1)}{'TARGET'.ljust(w2)}DISPOSITION")
        out.append("-" * (w1 + w2 + 20))
        for row in ledger:
            out.append(f"{row['source_fact'].ljust(w1)}{str(row['target']).ljust(w2)}"
                       f"{row['disposition']}")
    else:
        out.append("(no source facts recorded)")

    out += ["", ""]
    for name, value in report["counters"].items():
        out.append(f"{name}: {value}")
    suite = report["regression"]
    out.append(f"REGRESSION SUITE: {'PASS' if suite['passed'] else 'FAIL'} "
               f"({suite['detail']})")

    if report["findings"]:
        out += ["", "BLOCKING FINDINGS"]
        for f in report["findings"]:
            out.append(f"  [{f['incident']}] {f['location']}: {f['detail']}")

    out += ["", report["decision"]]
    return "\n".join(out)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_record", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    record = json.loads(args.run_record.read_text(encoding="utf-8"))
    report = evaluate(record)
    print(json.dumps(report, indent=2) if args.json else render(report))
    return 0 if report["decision"] == "SHIP" else 1


if __name__ == "__main__":
    sys.exit(main())
