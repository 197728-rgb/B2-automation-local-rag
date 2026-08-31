# Release Gates

The shipping decision. Owned here; referenced elsewhere as `AR-12`.

## The counters

Before any handoff, produce a disposition ledger — every source fact, its target, and what
happened to it — then these counters:

```
UNACCOUNTED SOURCE FACTS         must be 0     (AR-07)
UNSUPPORTED TARGET VALUES        must be 0     (AR-08)
MERGED IDENTITIES                must be 0     (AR-06)
STRUCTURE VIOLATIONS             must be 0     (AR-09, AR-10)
MACHINE-READABILITY FAILURES     must be 0     (AR-11)
REGRESSION SUITE                 must PASS     (03_LESSONS/regression/)
```

Any non-zero counter, or a failing suite, is **DO NOT SHIP**. There is no override, and no
judgment call that substitutes for a zero.

## Running it

```bash
python 03_LESSONS/regression/run_regression.py            # are the controls working?
python 03_LESSONS/regression/release_gate.py RUN.json     # may this ship?
```

Exit code 0 is SHIP. Exit code 1 is DO NOT SHIP. Run-record format: `RUN_RECORD_SCHEMA.md`.

## Gate order during a job

| Gate | When | Blocks until |
|---|---|---|
| G-1 Mode | Before reading evidence | Mode and baseline named (AR-01, AR-02) |
| G-2 Scope | Before treating scope as known | Scope derived from current controlled documents (AR-04) |
| G-3 Authority | Before a value is eligible | Admissible source recorded (AR-03, AR-08) |
| G-4 Absence | Before declaring a field absent | Every applicable surface searched; environment ruled out |
| G-5 Write | Before writing | Merge owner resolved, one identity per row, formatting bound in (AR-06, AR-09, AR-10) |
| G-6 Handoff | Before handing off a document | Three-way verification passes (AR-11) |
| G-7 Finding | Before issuing a finding | Requirement, field meaning, identity, materiality, proof — all five. Missing proof is HOLD |
| G-8 Ship | Before claiming completion | All counters zero, suite passing (AR-12) |

## The completion rule

A claim of completeness or absence ships with a check that can fail, and that has been
**demonstrated failing on a violating input** before it is trusted.

An unverified claim is intent presented as a result. This is the archive's founding
incident — see `04_FORENSIC_ARCHIVE/incidents/AAR-R025.md`.
