# Future Agent Notes

## Starting a job

1. Read `../01_ACTIVE_RULES/CORE_GATES.md`. It is short by design; read all of it.
2. Read the rules for what you are touching: `B2_RULES`, `QAPE_RULES`, `DOCX_RULES`.
3. Lock mode and baseline (G-1) before reading any evidence.
4. Work the gates in order. The gates are the job.
5. Before claiming completion, run the gate:

```bash
python ../tools/release_gate.py my_run_record.json
```

`SHIP` or `DO NOT SHIP` is the answer. Not your assessment of the work.

## What this system assumes about you

That you will not remember. The rules are short so they can be loaded every time; the
tests exist because a rule you have read is still a rule you can rationalize past; the
gate exists because a test you can choose to skip is not a gate.

None of this is a comment on any particular session. It is the design assumption.

## When something recurs

Do not open with "it happened again". Open with *which link broke*:

1. Was there a rule? → `01_ACTIVE_RULES/`
2. Was there a test? → `ERROR_LEDGER.md`, `State` column
3. Did the test run? → regression output for that run
4. Was the test right? → does its known-bad case still fail?
5. Did the shipping path use the validator? → `RELEASE_RULES` §3

Each answer points at a different fix. Only the first is "write a rule".

## Adding what you learn

`../tools/LESSON_PROMOTION.md` decides how far an incident travels. The short version:
facility-specific stays in the forensic archive; generalizable gets an incident ID;
testable gets a known-bad and a known-good; materially damaging gets a rule and a gate
counter.

Run the known-bad case and watch it fail **before** you trust the control. A control that
has never failed has never been tested.

## Do not

- Do not treat the forensic archive as audit authority. It records what happened once.
- Do not carry facility evidence between sessions, in either direction.
- Do not patch this system in fragments. Reissue it whole (AAR-R023 applies to rule sets).
- Do not add a rule you cannot test and cannot enforce without saying so in the ledger.
