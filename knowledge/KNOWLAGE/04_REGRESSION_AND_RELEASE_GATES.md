# 04 REGRESSION AND RELEASE GATES

The single authoritative home for recurrence-prevention tests and release criteria.

## Regression fixtures

Twenty-one controls, each asserting both halves: the known-bad case must fail, the
known-good case must pass. A control that rejects everything is not a control.

Fixtures are executable and live in `regression/fixtures.json`; they use neutral
placeholders so a failure class can be exercised without importing an incident.

```bash
python regression/run_regression.py
```

| ID | Prevents | Fixture premise | Pass condition |
|---|---|---|---|
| R-01 | E-013 | Two personnel identities in one row, with a merged level and method | Each identity resolves to its own row; a value outside the controlled vocabulary is rejected |
| R-02 | E-013 | Two instrument records concatenated across name, identifier and function | Each record occupies its own row |
| R-03 | E-016 | One identity claimed verified with a blank destination; one left unevaluated | Both are reported as defects |
| R-04 | E-018 | Disagreeing sources, and a low-confidence candidate | Both resolve to `WITHHELD_FLAGGED_DISCREPANCY`, never a blank or a fill |
| R-05 | E-003 | An extraction-noise value accepted for a typed field; an undisclosed fallback | The candidate is rejected and the fallback is required to be recorded |
| R-06 | E-010 | One identifier carrying Procedure, Form/Report and qualification attributes | All three identities resolve independently |
| R-07 | E-011 | A repeated printed section number across distinct physical leaves | No leaf resolves from printed section number alone |
| R-08 | E-008 | A register entry offered as proof that an event occurred | Event occurrence is not asserted |
| R-09 | E-012 | One identity that is a token subset of another | Exact matching prevents the false binding |
| R-10 | E-014 | A physical coordinate carried in from a prior run | Coordinates resolve only from the current run |
| R-11 | E-007 | Absence concluded while the environment was degraded | Environment state is reported, not evidence absence |
| R-12 | E-015 | Two different semantic fields compared | The comparison is refused |
| R-13 | E-019 | Rebuild mode declared while an accepted baseline exists | The rebuild is blocked |
| R-14 | E-036 | An unrecognized mode spelling; and the documented spelling with a space | Unrecognized modes are a defect; documented spellings are honoured |
| R-15 | E-025 | A visible control value that extracts blank | Visible and extracted values must agree |
| R-16 | E-027 | Row count, header count and tail changed; a formatting pass after the write | Protected structure and write-level formatting are enforced |
| R-17 | E-030 | A signature blank reported on a draft document | The requirement applies only at released status |
| R-18 | E-044 | A knowledge update carrying customer-shaped content; a filesystem-walk snapshot | The update is rejected and the snapshot source is refused |
| R-19 | E-045 | Delivery containing an item outside the requested scope | Only requested items are delivered |
| R-20 | E-014 | A reusable mapping keyed by table/row/cell; another carrying coordinates from a prior run | Identity resolves from form/version, section, label, meaning, entity and merge owner, with coordinates derived this run |
| R-21 | E-019 | Rework restarted from a blank with no qualifying exception, losing a correct value | Rework continues from the working form and changes only identified defects |

## Release gates

A release candidate is ready for human review only when all applicable gates pass.

1. Job mode and baseline locked, and the mode is recognized.
2. Controlled deliverable identity and template locked.
3. Authoritative source discovery exhausted, or explicitly unresolved, with the
   environment ruled out.
4. Identity reconciliation complete: record types, QAPE leaves, rows, and coordinates.
5. Predicates evaluated separately; no register entry standing in for event proof.
6. Every required semantic identity carries an explicit disposition, and two-way
   completeness reports no unresolved defect unless explicitly flagged.
7. No silent truncation detected.
8. Exact identity checks pass; no write authorized by similarity.
9. Structural validation passes against the pristine template, including the tail.
10. First and final rendered pages inspected.
11. Cold-start run passes with no scratch dependency.
12. Semantic readback, structure, and render comparison pass on the artifact that ships.
13. Reusable knowledge contains no customer-specific B-2 / QAPE facts, and every published
    claim has a check that can falsify it.

Do not equate a successful process exit, a write count, or a raw hash with release
readiness.

```bash
python regression/release_gate.py RUN_RECORD.json
```

The gate emits a disposition ledger and eight counters — merged identities, identity
defects, unresolved dispositions, unsupported evidence, structure violations,
machine-readability failures, status and mode defects, knowledge-boundary defects. Any
non-zero counter, or a failing suite, is `NOT READY`.

## Candidates for new controls

Untested classes worth building next, where a check would catch the real defect rather
than approximate it: E-022 (silent truncation), E-023 (narrowed discovery treated as
complete), E-029 (handoff without structural validation), E-031 and E-032 (scratch
dependence and run collision), E-041 (uncanonical duplicate reference).

Classes best left governed by rule: E-009, E-020, E-021 — whether documented coverage
establishes implementation, whether a section is applicable, and which elements are
assigned are judgments. A check asserting otherwise would manufacture confidence.

## Adding a control

1. Write the known-bad fixture and **run it first — confirm it fails.** A control that has
   never failed has never been tested.
2. Add the known-good fixture and confirm it passes.
3. Map the failure class to a gate counter if recurrence would materially damage output.
