# Error Ledger

Authoritative incident registry. Every recurring material mistake carries a permanent ID
and the full chain:

**INCIDENT → ROOT CAUSE → GENERALIZED LESSON → DURABLE FIX → REGRESSION TEST → RELEASE GATE**

Fix detail and its proof artifact are in `DURABLE_FIXES.md`; why each lesson generalizes is
in `HARD_LESSONS.md`. Cells here are pointers, not restatements.

`PREVENTED` = rule, test, and gate all exist. `RULE ONLY` = a rule exists but nothing can
fail. The distinction is the backlog, and it is stated rather than hidden.

## Repeating-record integrity

| ID | Incident | Root cause | Generalized lesson | Fix | Test | Gate | State |
|---|---|---|---|---|---|---|---|
| AAR-R001 | Two personnel records concatenated into one row | Row treated as a text bucket, not a record | Distinct identities require distinct records | AR-06 | TEST-001 | MERGED IDENTITIES | PREVENTED |
| AAR-R002 | Two equipment/calibration records concatenated | Same | Same | AR-06 | TEST-002 | MERGED IDENTITIES | PREVENTED |

## Baseline preservation

| ID | Incident | Root cause | Generalized lesson | Fix | Test | Gate | State |
|---|---|---|---|---|---|---|---|
| AAR-R003 | TCID revision/record type/entry type dropped | Completeness checked one direction only | Completeness runs both ways | AR-07 | TEST-003 | UNACCOUNTED SOURCE FACTS | PREVENTED |
| AAR-R004 | Owner permission/written instructions dropped | High-risk fields not explicitly inspected | Fields that have gone missing get a standing checklist | AR-07 | TEST-010 | UNACCOUNTED SOURCE FACTS | PREVENTED |
| AAR-R010 | Populated baseline field blank in output, no disposition | Preservation claimed, never verified | A claimed disposition is checked against the target | AR-07 | TEST-010 | UNACCOUNTED SOURCE FACTS | PREVENTED |
| AAR-R007 | Accepted completed current form rebuilt from blank | Blank availability mistaken for a reason | Preservation beats regeneration when a baseline is accepted | AR-02 | TEST-007 | STRUCTURE VIOLATIONS | PREVENTED |

## Output fidelity

| ID | Incident | Root cause | Generalized lesson | Fix | Test | Gate | State |
|---|---|---|---|---|---|---|---|
| AAR-R005 | Visible control value extracts as blank | Only the render was checked | Visible and machine-readable are two results | AR-11 | TEST-005 | MACHINE-READABILITY FAILURES | PREVENTED |
| AAR-R016 | Value in XML renders as an empty cell | Value written inside a placeholder/content control | Same defect from the other direction | AR-11 | — | MACHINE-READABILITY FAILURES | RULE ONLY |
| AAR-R006 | Post-hoc formatting altered protected content | Formatting treated as a separate pass | Formatting belongs to the write | AR-09, AR-10 | TEST-006 | STRUCTURE VIOLATIONS | PREVENTED |
| AAR-R017 | Filled document handed off without a passing structure guard | Guard advisory rather than blocking | A guard that can be skipped is not a guard | AR-12 | — | STRUCTURE VIOLATIONS | RULE ONLY |

## Evidence authority

| ID | Incident | Root cause | Generalized lesson | Fix | Test | Gate | State |
|---|---|---|---|---|---|---|---|
| AAR-R008 | Checker compared semantically different fields | Physical proximity mistaken for identity | Identity precedes location | AR-05 | TEST-008 | UNSUPPORTED TARGET VALUES | PREVENTED |
| AAR-R011 | Retrieval similarity authorized a write location | Suggestion and authorization conflated | Ranking proposes; something deterministic bounds consequences | AR-08 | — | UNSUPPORTED TARGET VALUES | RULE ONLY |
| AAR-R012 | OCR noise autofilled into a required field | No plausibility gate before fill | A candidate passes a format check before eligibility | AR-08 | — | — | RULE ONLY |
| AAR-R013 | Weaker source substituted without disclosure | Fallback silent by default | Degradation must be loud | AR-08 | — | — | RULE ONLY |
| AAR-R014 | Absence declared after one extraction path | Search mistaken for the record | Absence is a conclusion, not an observation | AR-07 | — | — | RULE ONLY |
| AAR-R015 | Low-confidence or conflicting value silently promoted | Terminal states treated as warnings | Confidence and conflict are terminal, not advisory | AR-08 | — | — | RULE ONLY |
| AAR-R024 | Environment failure reported as absent evidence | Missing tool and missing record look identical | Rule out the environment before concluding absence | AR-07 | — | — | RULE ONLY |

## Scope and applicability

| ID | Incident | Root cause | Generalized lesson | Fix | Test | Gate | State |
|---|---|---|---|---|---|---|---|
| AAR-R018 | Procedure language accepted as proof of implementation | Manual and Compliance conflated | A procedure describes what should happen | AR-03 | — | — | RULE ONLY |
| AAR-R019 | Non-audited QAPE element evaluated as required | Full element set assumed | The audited set is assigned per package | AR-04 | — | — | RULE ONLY |
| AAR-R020 | Conditional section populated with no applicable evidence | Presence on the blank form mistaken for applicability | Blank is a governed state | AR-07 | — | — | RULE ONLY |
| AAR-R009 | Draft signature blank treated as a final-release defect | Document status not established | Status decides what completion means | AR-01 | TEST-009 | — | PREVENTED |

## Process and delivery

| ID | Incident | Root cause | Generalized lesson | Fix | Test | Gate | State |
|---|---|---|---|---|---|---|---|
| AAR-R021 | Fix verified on a helper while the shipping path was unchanged | Helper mistaken for the deliverable | A fix exists only on the path that ships | AR-12 | — | — | RULE ONLY |
| AAR-R022 | Fix lost to revert/merge churn, re-implemented repeatedly | No test defended it | A fix without a test is on loan | AR-12 | — | REGRESSION SUITE | RULE ONLY |
| AAR-R023 | Near-duplicate reference used with no canonical marker | No canonical copy declared | Duplicates are latent contradictions | AR-03 | — | — | RULE ONLY |
| AAR-R025 | Completeness/absence claim published with nothing that can falsify it | Check written to confirm, not to find failure | A claim is worth the check that can falsify it | AR-12 | — | REGRESSION SUITE | RULE ONLY |
| AAR-R026 | Scope expanded past the request; adjacent problems absorbed | Each step justified against the previous, not the request | Drift is a sequence of reasonable decisions | AR-01 | TEST-026 | — | PREVENTED |
| AAR-R027 | A control passed its test while the documented interface bypassed it | Fixture written against the implementation, not the interface operators are told to use | Test the spelling the documentation tells people to use | AR-12 | TEST-007b | — | PREVENTED |
| AAR-R028 | A correction was reported as applied without confirming it landed | Edit failed silently; the report was written from intent | Verify the edit, not the intention to edit | AR-12 | — | — | RULE ONLY |

## Coverage

28 incidents · 11 with executable regression · 17 `RULE ONLY`.

The `RULE ONLY` set is honest backlog. Several resist a mechanical test — whether a
procedure proves implementation is a judgment, and a check asserting otherwise would fake
coverage. Adding a control is worthwhile when a test genuinely catches the defect; padding
the table is not.
