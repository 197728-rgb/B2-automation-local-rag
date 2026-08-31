# Validation and Regression

The test cases that exercise the controls. A control with no case here is an intention,
not a control.

This file owns **the known-bad / known-good pairs**. What the control *is* and what proves
it is *in place* belongs to `DURABLE_FIXES.md`; when to refuse to continue belongs to
`DO_NOT_REPEAT.md`.

---

## Rule

Every control gets both halves:

- a **known-bad** case that must fail if the control works;
- a **known-good** case that must pass, so the control cannot be satisfied by rejecting
  everything.

Fixtures are synthetic and facility-neutral. Cases are never written against one activity
code or one element only.

---

## Content preservation

| ID | Known-bad (must fail) | Known-good (must pass) | Control |
|---|---|---|---|
| R-01 | A populated owner instruction present in the baseline is absent from the output | The value is carried through unchanged | F-16 |
| R-02 | A demonstration type, design-control value, TCID entry, or auditor note present in the baseline is absent from the output | Each is present in its correct semantic column | F-15 |
| R-03 | A target field reaches handoff with no disposition | Every relevant field carries one disposition from the defined set | F-16 |

## Row and entity integrity

| ID | Known-bad (must fail) | Known-good (must pass) | Control |
|---|---|---|---|
| R-04 | Two technicians with different qualification records occupy one row | Two rows, each with its own dates and qualifications | F-08 |
| R-05 | Two equipment items with different IDs or calibration records occupy one row | Two rows, each identity intact | F-08 |
| R-06 | A write lands in a vertical-merge continuation cell | The write lands in the merge owner | F-07 |

## Targeting and structure

| ID | Known-bad (must fail) | Known-good (must pass) | Control |
|---|---|---|---|
| R-07 | A map built against an earlier template revision is applied after the merge layout changed | Fingerprint mismatch is detected and the map is re-derived before any write | F-06 |
| R-08 | A row is added, a merge changed, a label overwritten, or page geometry altered | Structure is byte-identical outside the authorized cells | F-20 |
| R-09 | A coordinate from a previous run is accepted as a target | Targets resolve only from structure derived this run | F-05, F-06 |

## Output fidelity

| ID | Known-bad (must fail) | Known-good (must pass) | Control |
|---|---|---|---|
| R-10 | A value written into the XML renders as an empty cell because it sits inside a placeholder or content control | The value is visible in the rendered cell | F-17 |
| R-11 | A visibly selected control extracts as empty | Visible value and extracted value agree | F-18 |
| R-12 | Formatting is applied by a pass over changed cells or the whole document after the write | Formatting appears only on authorized writes, applied with them | F-19 |

## Evidence and authority

| ID | Known-bad (must fail) | Known-good (must pass) | Control |
|---|---|---|---|
| R-13 | Retrieval similarity alone selects a write location | Writes authorize only from an exact per-form/version map | F-10 |
| R-14 | OCR noise is filled into a required field | The candidate is rejected by the format and plausibility gate, and the rejection is recorded | F-11 |
| R-15 | A field is filled from a source not admissible for that field | Every value links to an admissible source and location | F-09 |
| R-16 | A low-confidence or conflicting candidate is filled silently | Both remain visible as terminal states in the review artifact | F-14 |
| R-17 | A degraded or fallback source is used with no record of the substitution | The path actually used appears in the value record | F-12 |
| R-18 | A field is reported absent after one extraction path | The searched surfaces are listed before absence is claimed | F-13 |

## Scope and applicability

| ID | Known-bad (must fail) | Known-good (must pass) | Control |
|---|---|---|---|
| R-19 | A non-audited element is evaluated as required | Only assigned elements are evaluated | F-04 |
| R-20 | Documented-system language alone produces a compliance determination | Manual and compliance determinations draw on their own evidence families | F-21 |
| R-21 | A conditional section is populated with no applicable evidence, or N/A is written with no authorizing rule | The section holds a controlled blank with the rule cited | F-22 |
| R-22 | A draft-stage signature blank produces a defect | The signature requirement applies only at final or released status | F-23 |
| R-23 | A finding issues without requirement, identity, materiality, and proof | Missing proof yields HOLD | F-24 |

## Input tolerance

| ID | Known-bad (must fail) | Known-good (must pass) | Control |
|---|---|---|---|
| R-24 | A multi-value input using a separator the parser does not accept is read as one unknown token | Comma, whitespace, and mixed separators all parse; unknown values are still rejected strictly | F-28 |
| R-25 | A pattern tuned on clean text discards a valid value that appears with OCR-typical separators or spacing | Both clean and OCR-shaped forms of the same value are accepted | F-11 |

## Process and delivery

| ID | Known-bad (must fail) | Known-good (must pass) | Control |
|---|---|---|---|
| R-26 | A restored fix has no test that fails without it | Removing the fix fails a named test | F-26 |
| R-27 | Two concurrent runs write to the same output directory | Each run's artifacts are isolated to its own run directory | F-31 |
| R-28 | A documentation claim about outputs is contradicted by an actual run | Documented outputs match an observed run, or the doc is corrected | F-27 |
| R-29 | A near-duplicate reference is loaded with no canonical marker present | The canonical copy is selected by its marker, superseded copies are rejected | F-30 |
| R-30 | A temp, debug, or render artifact is present in the delivery folder | The delivery listing matches the allowlist exactly | F-33 |
| R-31 | A fix is verified on a helper path while the delivered artifact is unchanged | Reverting the fix changes the delivered artifact, proving the shipping path runs it | F-25 |
| R-32 | Missing network, OCR binary, or unmaterialized input is reported as absent evidence | Preflight reports it as environment state and the run does not conclude absence | F-32 |

---

## Release evidence

Before shipping, run against the exact artifact to be delivered:

1. reopen the generated file;
2. parse the intended values;
3. compare every disposition in both completeness directions;
4. inspect repeating-row identity;
5. validate controls and merge ownership;
6. render and inspect every page;
7. compare the delivery folder to the allowlist;
8. run at least one known-bad and one known-good case for every control the change
   touched.
