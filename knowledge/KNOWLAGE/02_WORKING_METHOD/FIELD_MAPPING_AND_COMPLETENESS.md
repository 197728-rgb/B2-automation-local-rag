# Field Mapping and Completeness

Mechanics of addressing a field, authorizing its value, and proving nothing was lost.
Sequence is `WORKFLOW.md`; rules are `AR-05` through `AR-08`.

## 1. Semantic key (AR-05)

```
Form | ActivityCodeOrElement | Section | FieldLabel | EntityKey | Applicability | RevisionState
```

`FieldLabel` is the exact printed label, not a paraphrase. `EntityKey` is required for
repeating rows. `RevisionState` is the form revision the key was resolved against.

A physical coordinate may be recorded **after** the key resolves. It expires with that
document instance and is never an input to the next run.

## 2. Authority matrix (AR-03, AR-08)

Per destination fact, before any value is eligible: the semantic key · the source classes
admissible for *this* fact · the exact entity · why the field applies · the revision or
validity window that must hold.

A source is admissible for a fact or it is not. Relevant, adjacent, recent, and
"supplied in the same folder" are not admissibility.

## 3. Dispositions (AR-07)

| Disposition | Meaning |
|---|---|
| `CONFIRMED_VALUE` | An admissible source proves this value |
| `PRESERVE_BASELINE` | An existing value remains supported and undisproven |
| `CONTROLLED_BLANK` | Blank is correct by scope or form logic, rule cited |
| `AUTHORIZED_NA` | N/A permitted here by form or rule, rule cited |
| `WITHHOLD_CONFLICT` | Admissible sources disagree; recorded, not resolved by preference |
| `UNVERIFIABLE` | Not found after exhaustion; surfaces searched are listed |

**Both directions are required.**

*Source → output:* every populated fact ends preserved, updated from stronger current
evidence, withheld for conflict, authorized N/A, or explicitly reported unplaceable. No
fact simply disappears.

*Output → evidence:* every relevant field ends as a supported value, a preserved supported
value, a controlled blank, an authorized N/A, a withheld conflict, or a reported
unverifiable. No field is silently invented or skipped.

Each direction catches what the other misses. Running one is not running the check.

A fact marked `PRESERVE_BASELINE` or `CONFIRMED_VALUE` whose target is blank is a defect:
the claim of preservation without the preservation.

## 4. Identity keys for repeating rows (AR-06)

| Record | Key components |
|---|---|
| Personnel | Name or ID; qualification number; method and level where they distinguish |
| Equipment | Type; ID or serial; function; calibration record identity |
| NDT technician | Technician ID; level; method; qualification and acuity validity |
| Procedure / record | Procedure or form number; revision; approval state |
| Material | Specification; heat, batch, or lot ID; status indicator |

Records sharing every component are one record. Differing in any component, two rows.

A single-valued cell holding two glued tokens is the signature of a merge: `M. StuckeyM.
Perry`, `IIII`, `UTTVT`, `Thickness ReadingsMeter Verification`. A level outside {I, II,
III} or a method outside the controlled set is two values merged, not an unusual value.

## 5. Conditional sections

Applicable, conditionally applicable, or unused in the observed demonstration. Do not
populate because the section exists; do not delete because it is unused.
`CONTROLLED_BLANK` or `AUTHORIZED_NA`, rule cited.

## 6. Evidence families

Program-level and technical-demonstration evidence answer different questions and are not
interchangeable in either direction. Documented-system evidence can support a Manual
determination; Compliance needs evidence of the act. Label each citation with the family
it satisfies.

## 7. High-risk fields — inspected every run

Whether or not the run expects them to change:

owner permission and written instructions · demonstration type or classification ·
design-control classification and Type COC · personnel and qualification records ·
equipment and calibration records · NDT approver identifiers · TCID revision, record type,
entry type, work description · traceability and marking · auditor objective-evidence notes
· signature and attestation state.

These are the fields that have actually gone missing. See `03_LESSONS/ERROR_LEDGER.md`.
