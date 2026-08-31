# Future Agent Notes

## Starting a job

1. Read `01_ACTIVE_RULES/ACTIVE_RULES.md` — all of it; it is short on purpose.
2. Lock mode and baseline before reading evidence (AR-01, AR-02).
3. Follow `02_WORKING_METHOD/WORKFLOW.md` phase by phase.
4. Keep `FIELD_MAPPING_AND_COMPLETENESS.md` open while mapping fields.
5. Before claiming completion:

```bash
python 03_LESSONS/regression/release_gate.py my_run_record.json
```

`SHIP` or `DO NOT SHIP` is the answer — not your assessment of the work.

`03_LESSONS/` is reference. Go there when a gate blocks and you need to know why.

## What this archive assumes about you

That you will not remember. The rules are short so they can be reloaded every time; the
tests exist because a rule you have read is still a rule you can reason past; the gate
exists because a test you may skip is not a gate.

That is a design assumption, not a comment on any session.

## When something recurs

Do not open with "it happened again". Name which link broke:

1. Was there a rule? → `01_ACTIVE_RULES/`
2. Was there a test? → `ERROR_LEDGER.md`, `State` column
3. Did the test run? → regression output for that run
4. Was the test right? → does its known-bad case still fail?
5. Did the shipping path use the gate? → AR-12

Each answer points at a different fix. Only the first is "write a rule".

## Adding what you learn

Facility-specific → `04_FORENSIC_ARCHIVE/` only, marked historical, and stop.
Generalizable → an incident ID and a ledger row.
Testable → a known-bad and a known-good; **run the known-bad first and watch it fail.**
Materially damaging → a rule and a gate counter.

Most incidents stop at the forensic archive. That is the filter working, not a gap.

## Do not

- Do not treat the forensic archive as authority. It records what happened once.
- Do not carry facility evidence between sessions in either direction.
- Do not patch this archive in fragments; reissue it whole (AAR-R023 applies here too).
- Do not add a rule you cannot test and cannot enforce without marking it `RULE ONLY`.
- Do not absorb adjacent problems. Name them and hand them back (AAR-R026).
