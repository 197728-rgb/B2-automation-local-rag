# Do Not Repeat — Refusal Gates

Nine ordered gates. Each names **when work stops** and **what unblocks it**. Nothing else
in this pack authorizes continuing past a gate that has not cleared.

This file owns **the stop condition and its release**. The mechanisms are in
`ERROR_LEDGER.md`, the controls in `DURABLE_FIXES.md`, the procedure in
`AAR_AUDIT_REPORT_PLAYBOOK.md`.

---

## G-1 — Before reading any evidence

**Stop if** the job mode or the baseline document is not declared, or evidence from
another audit is present in the working set.

**Release:** mode and baseline named in the run record; working set reduced to this
audit's evidence. → F-01, F-02

---

## G-2 — Before treating scope as known

**Stop if** the in-scope forms, activity codes, and audited elements came from anywhere
other than the current controlled documents — including a prior year, a filename, a
folder name, or this pack.

**Release:** scope list derived from the documents in hand, each carrying its controlled
title and revision. → F-03, F-04

---

## G-3 — Before resolving any physical cell

**Stop if** a coordinate was carried in from a prior run, or the template fingerprint has
not been checked against the map being used.

**Release:** structure derived fresh from the current file this run, fingerprint matched
or the map re-derived. → F-05, F-06

---

## G-4 — Before a value becomes eligible to write

**Stop if** the value has no admissible source for that specific field, if its only
support is retrieval similarity, if it has not passed the noise and format gate, or if
it arrived through an undisclosed fallback.

**Release:** admissible source and location recorded; authorization traced to an exact
map; format gate result and any fallback recorded. → F-09, F-10, F-11, F-12

---

## G-5 — Before declaring a required field absent

**Stop if** only one extraction path has been tried, or if the failure could be an
environment condition rather than a missing record.

**Release:** the searched surfaces are listed, and preflight confirms the environment was
sound. → F-13, F-32

---

## G-6 — Before the write

**Stop if** the target is a merge continuation rather than the merge owner, if two
entities would land in one row, or if formatting would be applied as a separate later
pass.

**Release:** merge owner identified, one entity per row with a distinct identity key,
formatting bound into the same operation. → F-07, F-08, F-19

---

## G-7 — Before handoff of any filled document

**Stop if** the structure guard has not passed, if any written value is not confirmed
visible in the render, if any control-backed field does not read back as its visible
value, or if a low-confidence or conflicting candidate was promoted without surfacing.

**Release:** passing structure guard, visible-render confirmation, machine readback
match, and every low-confidence or conflicting candidate present in the review artifact.
→ F-14, F-17, F-18, F-20

---

## G-8 — Before issuing any finding

**Stop if** the requirement, the field's meaning, the entity's identity, the materiality,
or the proof is missing; or if the document's draft/final/released status has not been
established.

**Release:** all five recorded, status established. Where proof is absent the outcome is
HOLD, not REJECT. → F-21, F-22, F-23, F-24

---

## G-9 — Before claiming completion

**Stop if** the fix was verified anywhere other than the path that produced the delivered
file; if a restored fix carries no regression test; if the delivery folder holds anything
outside the allowlist; if two governing documents still disagree with no declared
precedence; if a near-duplicate reference has no canonical marker; or if a documentation
claim about the run has not been checked against the run.

**Release:** every item above resolved on the delivered artifact, then completion is
stated. → F-25, F-26, F-27, F-29, F-30, F-33, F-34, F-35
