# Hard Lessons

The generalizable principles behind the controls. Each is stated once, with the reason it
holds beyond the case that produced it.

This file owns **why**. It does not restate a failure (`E-###`), a control's mechanics
(`F-##`), a refusal point (`G-#`), or a test (`R-##`).

| ID | Principle | Why it generalizes |
|---|---|---|
| L-01 | Identity precedes location. | Meaning is stable across revisions; geometry is not. Anything keyed to geometry expires the next time the form is reissued. |
| L-02 | Document geometry is run-local. | A controlled form can be revised without notice, and a merge change moves every coordinate downstream of it. Coordinates are therefore derived output, never stored knowledge. |
| L-03 | Authority is field-specific. | "Related to" and "authoritative for" are different relations. A document can be perfectly relevant and still be inadmissible for the specific fact being asserted. |
| L-04 | A repeating row is a record, not a text bucket. | Rows exist to keep identities separable. Two identities in one row destroys the only thing the table was built to preserve. |
| L-05 | Absence is a conclusion, not an observation. | "Not found" is a statement about the search, not about the record. It is only about the record after every applicable surface has been searched. |
| L-06 | Completeness runs in both directions. | Guarding only the target lets source facts vanish; guarding only the source lets target fields be invented. Each direction misses what the other catches. |
| L-07 | Blank is a governed state. | Emptiness looks conservative but asserts something — that no value was required or supported. That assertion needs the same authorization as a value. |
| L-08 | Visible and machine-readable are two separate results. | Human reviewers read the render; automated checkers read the extraction. A field can satisfy one and fail the other, and both are consumed downstream. |
| L-09 | A clean render is necessary and not sufficient. | Rendering proves the file opens. It proves nothing about whether the right fact reached the right field. |
| L-10 | Formatting belongs to the write. | A later sweep cannot tell an authorized change from untouched controlled content, so it can only be applied indiscriminately. |
| L-11 | Preservation beats regeneration when a baseline is accepted. | Regeneration re-runs every risk the accepted document already survived. Old is not the same as wrong. |
| L-12 | Suggestion and authorization are different powers. | Probabilistic ranking is good at proposing candidates and bad at bounding consequences. The bound has to come from something deterministic. |
| L-13 | Degradation must be loud. | A silent fallback produces an output indistinguishable from a confident one, which removes exactly the signal a reviewer needs. |
| L-14 | Document status changes what completion means. | Draft, final, and released documents are held to different requirements; judging one by another's standard manufactures defects or hides them. |
| L-15 | A checker finding is a claim, not a verdict. | Tools apply rules without knowing field meaning, entity identity, or materiality. Those three decide whether a difference is a defect. |
| L-16 | A fix exists only on the path that ships. | Verifying a helper proves the helper. The delivered artifact is the only thing the reader receives. |
| L-17 | A fix without a regression test is on loan. | Branch churn, reverts, and merges reliably delete undefended changes. The test is what makes the fix survive its author. |
| L-18 | Duplicate references are latent contradictions. | Near-identical copies agree until one is edited. Without a canonical marker, the next reader picks by accident. |
| L-19 | Documentation is an assertion about behavior. | An unverified doc claim propagates as fact into every downstream decision that trusts it, and costs more to unwind than to check. |
| L-20 | Environment failure is not evidence absence. | An unreachable index, a missing binary, or an unmaterialized file all present as "nothing found", and lead to exactly the wrong correction. |
| L-21 | Repeatability comes from rules with dispositions, not from remembered specifics. | Any method keyed to one activity code, element set, facility, or year fails on the next one. Only the decision procedure transfers. |
| L-22 | Scope is established once and defended, not rediscovered. | Repeated rediscovery costs time and lets the accepted scope drift silently between passes. |
