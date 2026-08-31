# 01 ACTIVE RULES

The rules that always govern. This file is the single authoritative home for always-on
rules; every other file references them by number rather than restating them.

## 1. Customer-data firewall
Reusable knowledge stores failure classes, controls, tests, and decision rules — never
customer facts. The full exclusion list is in `README.md`; this rule makes it binding.

## 2. Authority floor
Current authoritative evidence establishes facts. Filenames, folder names, archive names,
prior reports, examples, chat, shorthand, and memory may assist discovery but never
independently establish a current fact.

## 3. Job mode and baseline lock
Declare the mode and name the baseline document before reading evidence. Mode is matched
by meaning, not by exact spelling; an unrecognized mode is a defect, not a default.

- **NEW WORK = CLEAN CURRENT BLANK.** Start from the current approved clean blank form and
  populate it only from current audit evidence.
- **REWORK = SAME WORKING FORM.** Continue from the same working form already filled,
  generated, or reviewed. Preserve all correct existing values; change only identified
  defects or evidence-supported exceptions; keep the same controlled form/version and
  template structure; rerun every applicable semantic, machine-readable, visual,
  regression, and release validation. Corrections being required is not a reason to
  restart.
- **REBUILD FROM BLANK = EXCEPTION ONLY.** Permitted during rework only when the working
  document is corrupted, the wrong controlled form/version was used, template structure
  was materially damaged, or clean regeneration is explicitly required. The exception is
  named in the run record.
- **FINAL REVIEW** carries no write authority.

## 4. Identity order, and no position-based field authority
Deliverable order:

`FORM IDENTITY → CONTROLLED TEMPLATE → SCOPE → DESTINATION CONTRACT → EVIDENCE → WRITE`

Field identity resolves in this order, and only this order:

`CONTROLLED FORM/VERSION → SECTION → EXACT FIELD LABEL → SEMANTIC MEANING → ENTITY/RECORD IDENTITY → CURRENT CONTROL/MERGE OWNER`

Never identify, map, compare, or populate a field using page, table, row, column, or cell
index as its durable identity. Positions may be used only for run-local diagnostics and
structural validation — never as reusable mapping or as evidence authority.

Never reuse physical coordinates from another audit, a prior form version, or a previous
run. Coordinates are derived output that expires with the document instance.

## 5. Destination-field contract first
Before selecting evidence, inspect the controlled destination: label, control vocabulary,
static or prefilled text, merge ownership, current value, expected data type, and
conditional meaning.

## 6. Record-type identity lock
Procedure, Form/Report, and qualification records are separate identities. Resolve their
attributes independently even when they share an identifier.

## 7. QAPE leaf identity lock
A printed section number is not a unique leaf key. Use composite semantic identity plus
physical row location.

## 8. One record per logical row
One person, instrument, qualification, or calibration is one logical record. Distinct
identities never share a row and values are never concatenated. A value outside its
controlled vocabulary is treated as two values merged, not as an unusual value.

## 9. Source exhaustion before absence
Do not classify required evidence as absent until all applicable authoritative source
families and in-scope locations have been searched without unvalidated caps.

## 10. Evidence absence is epistemic
`NO PROOF IN CURRENT PACKET` does not mean `EVENT DID NOT OCCUR`. An environment failure —
unreachable source, missing tool, unmaterialized file — is environment state, never
evidence absence.

## 11. Two-way completeness
- `SUPPORTED + BLANK = DEFECT`
- `UNSUPPORTED + POPULATED = DEFECT`
- `UNKNOWN = KEEP WORKING`
- `UNEVALUATED = DEFECT`

A disposition claiming preservation while the destination is blank is a defect.

## 12. Conflict preservation
Use distinct dispositions: `POPULATED_VERIFIED`, `BLANK_UNSUPPORTED`,
`WITHHELD_FLAGGED_DISCREPANCY`. Never collapse a conflict, or a low-confidence value, into
an ordinary blank or a silent fill.

## 13. Exact identity matching
Do not use naive substring matching for identity decisions. Use normalized exact
identities, structured keys, or bounded tokens.

## 14. Predicate separation
Documented coverage, implementation, qualification, approval, demonstration, and
current-event proof are distinct predicates. A procedure or master list may support
identity or documented coverage; neither establishes that a specific audited event
occurred.

## 15. Candidate admissibility
A candidate value passes a format and plausibility check for its destination type before
it is eligible to fill, and the check is calibrated to real extracted input rather than
the ideal case. Any fallback or degraded source is named in the artifact.

## 16. Write authority separation
Retrieval, ranking, and model judgment propose candidates. Only an exact, versioned map
authorizes a write location — never a generic, nearest, latest, or similar one.

## 17. No silent truncation
Never silently cap narrative, comments, objective evidence, citations, or discovery
inventories.

## 18. Complete discovery requires validation
A capped, narrowed, partial, or paginated result is not proof of completeness unless
independently validated by a broader method.

## 19. Protected structure and write-level formatting
Formatting is applied as part of the authorized write, never as a later document-wide or
changed-cell pass. After structural edits, verify protected structure against the pristine
template: sections, headers, footers, bookmarks, content controls, merged ownership, body
order, row geometry, and document tail. A visually empty paragraph or cell may carry
structural XML and is never deleted on visible emptiness alone.

## 20. Semantic repeatability
Raw hash or text equality is not enough. Verify decisions, normalized structure, field
readback, protected structure, and every rendered page. What a reader sees and what an
extractor reads must agree in both directions.

## 21. Cold-start independence
Shipping logic reconstructs from durable governed inputs and never depends on ephemeral
scratch artifacts from a prior run, including per-run output directories.

## 22. Canonical source
Exactly one canonical artifact per subject; every other copy is marked superseded or
removed. Where two documents govern the same subject, one states the split and both
reference it.

## 23. Claims require falsifiable checks
Any completeness or absence claim ships with an automated check that fails when the claim
is false, and that has been demonstrated failing on a violating input before it is
trusted. A reported correction is itself a claim: confirm the change landed.

## 24. Learning boundary
Generalize the failure class and the preventive control. Do not preserve customer incident
anatomy in reusable knowledge.

## 25. Scope discipline
Deliver what was asked. An adjacent problem — a failing check you did not cause, a defect
found in passing, a better structure — is named and handed back, not absorbed.
