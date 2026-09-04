#!/usr/bin/env python3
"""Release gate: emits the disposition ledger and decides READY / NOT READY.

Release readiness is this tool's output, not an assessment of the work.

    python release_gate.py RUN_RECORD.json [--json]

Exit 0 = READY FOR HUMAN REVIEW. Exit 1 = NOT READY.
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

# Counters map failure classes to the release gate they block.
COUNTERS = {
    "MERGED IDENTITIES": {"E-013"},
    "IDENTITY DEFECTS": {"E-010", "E-011", "E-012", "E-014", "E-015"},
    "UNRESOLVED DISPOSITIONS": {"E-016", "E-017", "E-018"},
    "UNSUPPORTED EVIDENCE": {"E-003", "E-005", "E-006", "E-007", "E-008"},
    "STRUCTURE VIOLATIONS": {"E-026", "E-027"},
    "MACHINE-READABILITY FAILURES": {"E-025"},
    "STATUS AND MODE DEFECTS": {"E-019", "E-030", "E-036"},
    "KNOWLEDGE-BOUNDARY DEFECTS": {"E-043", "E-044", "E-045"},
}


def build_ledger(record: dict) -> list[dict]:
    rows = [{"identity": d.get("key", "?"),
             "destination": d.get("target", d.get("key", "?")),
             "disposition": d.get("disposition", "UNEVALUATED")}
            for d in record.get("dispositions", [])]
    for row in record.get("rows", []):
        cells = row.get("cells", {})
        rows.append({"identity": cells.get("name") or cells.get("equipment_name") or "?",
                     "destination": f"{row.get('table','?')} row {row.get('row','?')}",
                     "disposition": "POPULATED_VERIFIED"})
    return rows


def regression_status() -> tuple[bool, str]:
    try:
        result = subprocess.run([sys.executable, str(ROOT / "run_regression.py"), "--json"],
                                capture_output=True, text=True, cwd=ROOT, timeout=120)
    except (OSError, subprocess.SubprocessError) as exc:
        return False, f"suite could not run: {exc}"
    if result.returncode == 0:
        return True, "all controls working"
    try:
        broken = [r["test"] for r in json.loads(result.stdout)["results"] if r["status"] != "PASS"]
        return False, "broken controls: " + ", ".join(broken)
    except (ValueError, KeyError):
        return False, "suite failed"


def evaluate(record: dict) -> dict:
    findings = validators.run_all(record)
    counts = {name: 0 for name in COUNTERS}
    other = 0
    for f in findings:
        for name, errors in COUNTERS.items():
            if f.error in errors:
                counts[name] += 1
                break
        else:
            other += 1
    if other:
        counts["OTHER BLOCKING FINDINGS"] = other
    suite_ok, suite_detail = regression_status()
    ready = all(v == 0 for v in counts.values()) and suite_ok
    return {"ledger": build_ledger(record), "counters": counts,
            "regression": {"passed": suite_ok, "detail": suite_detail},
            "findings": [f.as_dict() for f in findings],
            "decision": "READY FOR HUMAN REVIEW" if ready else "NOT READY"}


def render(report: dict) -> str:
    out, ledger = ["DISPOSITION LEDGER", ""], report["ledger"]
    if ledger:
        w1 = max(len(str(r["identity"])) for r in ledger) + 2
        w2 = max(len(str(r["destination"])) for r in ledger) + 2
        out.append(f"{'IDENTITY'.ljust(w1)}{'DESTINATION'.ljust(w2)}DISPOSITION")
        out.append("-" * (w1 + w2 + 28))
        out += [f"{str(r['identity']).ljust(w1)}{str(r['destination']).ljust(w2)}{r['disposition']}"
                for r in ledger]
    else:
        out.append("(no required identities recorded)")
    out += ["", ""]
    out += [f"{name}: {value}" for name, value in report["counters"].items()]
    suite = report["regression"]
    out.append(f"REGRESSION SUITE: {'PASS' if suite['passed'] else 'FAIL'} ({suite['detail']})")
    if report["findings"]:
        out += ["", "BLOCKING FINDINGS"]
        out += [f"  [{f['error']}] {f['location']}: {f['detail']}" for f in report["findings"]]
    out += ["", report["decision"]]
    return "\n".join(out)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_record", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report = evaluate(json.loads(args.run_record.read_text(encoding="utf-8")))
    print(json.dumps(report, indent=2) if args.json else render(report))
    return 0 if report["decision"].startswith("READY") else 1


if __name__ == "__main__":
    sys.exit(main())
