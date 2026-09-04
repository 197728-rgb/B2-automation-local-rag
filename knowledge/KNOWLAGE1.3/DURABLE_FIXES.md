# Durable Fixes

Registry of controls. Each control defeats one or more mechanisms in `ERROR_LEDGER.md`
and is considered *in place* only when its minimum proof exists in the run record.

This file owns **the control and its proof artifact**. It does not restate the failure
(see `E-###`), the principle (`L-##`), the refusal point (`G-#`), or the test case (`R-##`).

## Scope and state

| ID | Control | Minimum proof | Defeats |
|---|---|---|---|
| F-01 | **Mode lock.** Declare MAINTENANCE / NEW FILL / FINAL REVIEW and the baseline document before any read of evidence | Run record names the mode and the exact baseline file | E-001 |
| F-02 | **Session evidence isolation.** One audit, one session; only that audit's evidence is admitted | Evidence inventory lists only files supplied for this audit | E-002, E-010 |
| F-03 | **One-time scope inventory with named re-scan triggers.** Re-inventory only on new files, uncertain identity, or a completeness gap | Inventory is dated once; each later re-scan cites its trigger | E-047 |
| F-04 | **Discovery from the current controlled document.** Fields, sections, conditional blocks, and audited elements are read from the document in hand | Discovered field/element list carries the form's controlled title and revision | E-028, E-031 |

## Identity and targeting

| ID | Control | Minimum proof | Defeats |
|---|---|---|---|
| F-05 | **Semantic destination identity before physical targeting.** Resolve form, section, field label, entity, and applicability first | Every write cites its semantic key (schema in `FIELD_AUTHORITY_AND_COMPLETENESS.md`) | E-003, E-008 |
| F-06 | **Per-run structure re-derivation with fingerprint check.** Coordinates are derived fresh from the current file and invalidated when the template fingerprint changes | Structure report for this run; fingerprint compared to the map's recorded fingerprint | E-003, E-004 |
| F-07 | **Merge-owner resolution before write.** The unique physical owner of a merged region is identified; continuation cells are never written | Write report names the owning cell for every merged target | E-005 |
| F-08 | **Repeating-row identity lock.** One source entity to one target row; identity keys are declared, never concatenated | Row-to-entity table with a distinct identity key per row | E-006, E-007 |

## Evidence authority

| ID | Control | Minimum proof | Defeats |
|---|---|---|---|
| F-09 | **Per-field authority matrix.** Each destination fact names the source classes admissible for it | Every populated value links to an admissible source and location | E-009, E-010 |
| F-10 | **Write-authority separation.** Retrieval and LLM reasoning may suggest and explain; only an exact per-form/version map may authorize a write location | Authorization record names the exact map and version used | E-011 |
| F-11 | **Extraction-noise gate.** Candidate values pass a format and plausibility check for their field type before they are eligible to fill; the check is widened to real observed input, not to the ideal case | Rejected candidates are recorded with the rule that rejected them | E-012, E-013 |
| F-12 | **Explicit fallback disclosure.** Any degraded or substituted source is named in the artifact, never silently swapped | Value record shows the path actually used | E-014 |
| F-13 | **Source exhaustion before absence.** All applicable fields, controls, continuations, attachments, and widgets are searched before UNVERIFIABLE | Absence record lists the surfaces searched | E-015 |
| F-14 | **No silent promotion.** Low confidence and conflict are terminal states that stay visible | Review artifact carries every low-confidence and conflicting candidate | E-016, E-017 |

## Completeness

| ID | Control | Minimum proof | Defeats |
|---|---|---|---|
| F-15 | **High-risk field checklist.** The named-risk fields are inspected explicitly on every run, present or not | Checklist result recorded per form (list in `FIELD_AUTHORITY_AND_COMPLETENESS.md`) | E-018–E-022 |
| F-16 | **Two-way completeness ledger.** Every populated source fact and every relevant target field ends with a recorded disposition | Ledger with no unresolved entry in either direction | E-018–E-022 |

## Output fidelity

| ID | Control | Minimum proof | Defeats |
|---|---|---|---|
| F-17 | **Visible-render verification.** The written value is confirmed visible in the rendered document, not trapped inside a placeholder or content control | Rendered page image or equivalent showing the value in its cell | E-023, E-048 |
| F-18 | **Machine-readable control verification.** Extracted text equals the intended visible value for every control-backed field | Extraction readback matching intended values | E-024, E-048 |
| F-19 | **Write-level formatting.** Value and its formatting are applied in the same governed operation; no later normalization pass | Write report shows formatting applied per write; no document-wide pass logged | E-025 |
| F-20 | **Structure guard as a hard blocker.** Template geometry is compared before and after; handoff is blocked on failure | Passing structure-guard report for the delivered file | E-026, E-027 |

## Applicability and findings

| ID | Control | Minimum proof | Defeats |
|---|---|---|---|
| F-21 | **Evidence-family separation.** Program-level and technical-demonstration evidence are evaluated as different questions | Each citation labelled with the family it satisfies | E-029, E-030 |
| F-22 | **Blank and N/A authorization.** A controlled blank or an N/A is written only when scope or form logic permits it | Disposition cites the authorizing rule | E-031, E-032 |
| F-23 | **Document-status lock.** Draft, final, and released state is established before completion fields are judged | Status recorded per document under review | E-033 |
| F-24 | **Finding admissibility test.** A defect requires requirement + identity + field meaning + materiality + proof; missing proof is HOLD | Each finding records all five; HOLD used where proof is absent | E-034 |

## Process, sources, delivery

| ID | Control | Minimum proof | Defeats |
|---|---|---|---|
| F-25 | **Shipping-path validation.** The corrected logic is proven on the path that produced the delivered file | Delivered artifact re-derived after the fix, and checked | E-035 |
| F-26 | **Regression lock on every restored fix.** A fix that has ever been lost gets a test that fails without it | Named test referenced by the fix | E-036 |
| F-27 | **Doc–code parity check.** Documentation claims about behavior and outputs are verified against a run, or corrected | Claim-to-observation list for changed docs | E-037 |
| F-28 | **Tolerant input, strict validation.** Accept the separators and spellings users really type; validate the resulting values strictly | Parser tests covering each accepted input shape | E-038 |
| F-29 | **Declared precedence for overlapping sources.** Where two documents govern the same subject, one states the split and both point to it | Precedence statement reachable from each document | E-039 |
| F-30 | **Canonical-copy rule.** Exactly one canonical artifact per subject; every other copy is named as superseded or deleted | Canonical marker or supersession notice on each near-duplicate set | E-040, E-041 |
| F-31 | **Per-run isolated output directories.** Every run writes to its own directory; nothing writes to a shared output root | Run directory keyed to run identity | E-042 |
| F-32 | **Environment preflight.** Network reach, OCR binary, file materialization, and template presence are checked before the run, and failures are reported as environment state, not as evidence absence | Preflight result recorded at run start | E-043 |
| F-33 | **Exact delivery allowlist.** The delivery folder contains the intended finals and nothing else | Delivery listing compared to the allowlist | E-044 |
| F-34 | **Completion gate.** Completion is claimed only after every gate in `DO_NOT_REPEAT.md` has passed on the delivered artifact | Gate results recorded against the delivered file | E-045 |
| F-35 | **Full instruction replacement.** Controlled instruction sets are reissued whole, never patched in fragments | Instruction set carries a single version identifier | E-046 |
| F-36 | **Claims are enforced by a check that can fail.** Any published completeness or absence claim ships with an automated check that blocks release when the claim is false | The check exists, runs in the build, and has been shown to fail on a violating input | E-049 |
| F-37 | **Snapshots source from the tracked file list.** What the repository already ignores is out of scope by construction, not by a hand-maintained exclusion list | Snapshot file list derived from `git ls-files` | E-050 |
