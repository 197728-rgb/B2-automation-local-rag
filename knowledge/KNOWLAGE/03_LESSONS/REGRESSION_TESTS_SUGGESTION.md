# Regression Tests

Ten controls run today. Each asserts **both halves**: the known-bad case must fail, the
known-good case must pass. A control that rejects everything is not a control, which is
why the good half is mandatory.

```bash
python regression/run_regression.py
```

## Working controls

| Test | Incident | Known-bad (must FAIL) | Known-good (must PASS) |
|---|---|---|---|
| TEST-001 | AAR-R001 | `M. StuckeyM. Perry \| IIII \| UTTVT` | two rows: `M. Stuckey \| II \| UTT`, `M. Perry \| II \| VT` |
| TEST-002 | AAR-R002 | `UTT MeterStep Block`, `Thickness ReadingsMeter Verification` | two rows, each identity intact |
| TEST-003 | AAR-R003 | baseline has revision/record type/entry type; target missing any | all three preserved |
| TEST-005 | AAR-R005 | visible `Tank Car Tank`, machine-readable blank | visible and extracted equal |
| TEST-006 | AAR-R006 | `rows_after != rows_before`, or a document-wide formatting pass | geometry unchanged, no sweep |
| TEST-007 | AAR-R007 | NEW FILL chosen while an accepted baseline exists | MAINTENANCE with that baseline |
| TEST-008 | AAR-R008 | `date_permission_received` compared against `date_approved` | same field both sides |
| TEST-009 | AAR-R009 | signature blank reported as a defect on a DRAFT | reported on a RELEASED document |
| TEST-010 | AAR-R010 | Type COC `PRESERVE_BASELINE` with a blank target; owner instructions `UNACCOUNTED` | both preserved with values present |
| TEST-026 | AAR-R026 | delivered items outside the declared requested scope | delivered ⊆ requested |

Concatenation is caught by controlled vocabulary, not by opinion: a level outside
{I, II, III} or a method outside the NDT set is two values merged.

## Suggested next controls

The 16 `RULE ONLY` incidents in `ERROR_LEDGER.md`, ranked by whether a test would catch
the real defect rather than fake coverage.

**Worth building — mechanically checkable**

| Incident | Known-bad | Known-good |
|---|---|---|
| AAR-R017 | handoff recorded with `structure_guard: failed` or absent | guard present and passing |
| AAR-R015 | a value written while its candidate set holds a conflict or sub-threshold confidence | conflicts and low confidence remain in the review artifact |
| AAR-R016 | value present in XML, absent from the rendered cell | present in both |
| AAR-R023 | two reference artifacts for one subject, neither marked canonical | exactly one canonical marker |
| AAR-R013 | value produced by a fallback path with no fallback recorded | path recorded on the value |
| AAR-R024 | absence concluded while preflight shows a missing binary or unreachable source | preflight clean before absence |

**Harder — needs a corpus, not a fixture**

AAR-R012 (OCR noise) and AAR-R022 (fix lost to churn) need realistic OCR samples and
repository history respectively. Synthetic fixtures would pass without proving anything.

**Not mechanically testable — leave as rules**

AAR-R018 (does a procedure prove implementation), AAR-R011 and AAR-R019 (scope and
authority judgments), AAR-R020 (applicability), AAR-R021 and AAR-R025 (require knowing
what *should* have been checked). A check asserting otherwise would manufacture false
confidence, which is worse than an honest `RULE ONLY`.

## Adding a control

1. Write the known-bad fixture and **run it first — confirm it fails.** A control that has
   never failed has never been tested.
2. Write the known-good fixture; confirm it passes.
3. Add the expected-results file and the manifest entry.
4. Map it to a gate counter in `01_ACTIVE_RULES/RELEASE_GATES.md` if recurrence would
   materially damage the output.
