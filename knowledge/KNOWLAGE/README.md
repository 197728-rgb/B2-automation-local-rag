# KNOWLAGE — Consolidated AAR Audit Repeatability Archive

Purpose: prevent repeat mistakes and produce repeatable results for **any** B-2 activity
code and **any** QAPE element.

This is a reconciliation of every accessible knowledge source, not a concatenation. Stale
and conflicting guidance was removed; lessons were generalized so they do not depend on
one code, element, facility, or year.

## Layers

| Layer | Holds | Read |
|---|---|---|
| `01_ACTIVE_RULES/` | 12 rules that must always be followed, plus the release gates | Always |
| `02_WORKING_METHOD/` | The repeatable workflow and field-mapping method | Doing the work |
| `03_LESSONS/` | Incidents, lessons, fixes, assumptions, prohibitions, regression tests | When a gate blocks |
| `04_FORENSIC_ARCHIVE/` | Historical failures and examples | Debugging only — never audit authority |

`01_ACTIVE_RULES/ACTIVE_RULES.md` is 25 lines. That is deliberate: rules only work if they
are short enough to load every time.

## One authoritative home per rule

Each rule is stated once, in `ACTIVE_RULES.md`, under an `AR-##` identifier. Every other
file references the ID rather than restating it. Incidents use `AAR-R###`, tests use
`TEST-###`. Three identifier spaces, no crosswalk needed.

If you find the same rule stated in two files, one of them is a defect.

## What actually prevents recurrence

Layers 1, 2 and 4 are documents, and a document can be reasoned around. The regression
suite and the release gate cannot:

```
$ python 03_LESSONS/regression/run_regression.py
All 10 controls working: every known-bad case fails, every known-good case passes.

$ python 03_LESSONS/regression/release_gate.py RUN.json
MERGED IDENTITIES: 3
DO NOT SHIP
```

Every recurring material mistake carries the full chain — **INCIDENT → ROOT CAUSE →
GENERALIZED LESSON → DURABLE FIX → REGRESSION TEST → RELEASE GATE** — in
`03_LESSONS/ERROR_LEDGER.md`. Where a link is missing, the ledger says `RULE ONLY` rather
than implying coverage.

## Boundary

Permanent knowledge may hold: blank controlled B-2 and QAPE forms, requirements and
guidance, revision notices, work aids, reviewer instructions, and this archive.

It may never hold completed facility forms, or any facility name, person, equipment ID,
car mark, date, procedure, record, or finding — except inside `04_FORENSIC_ARCHIVE/`,
marked `HISTORICAL EXAMPLE — NOT CURRENT AUDIT AUTHORITY`.

Every audit starts in a new session and receives only that audit's evidence (AR-03).

## Start here

`04_FORENSIC_ARCHIVE/` is not part of normal work. For a job, read
`01_ACTIVE_RULES/ACTIVE_RULES.md`, then `02_WORKING_METHOD/WORKFLOW.md`, then run the gate.
Startup detail is in `FUTURE_AGENT_NOTES.md`.
