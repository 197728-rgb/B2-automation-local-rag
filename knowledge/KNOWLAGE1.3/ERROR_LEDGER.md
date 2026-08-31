# Error Ledger

Registry of failure mechanisms that have actually occurred in this program of work.

This file owns **what went wrong and where it was seen**. It does not describe controls
(`DURABLE_FIXES.md`, `F-##`), principles (`HARD_LESSONS.md`, `L-##`), or refusal points
(`DO_NOT_REPEAT.md`, `G-#`).

**Observed in** codes: `REPO` = project source or git history · `SKILL` = B2S platform
skill guide · `DRIVE` = Google Drive knowledge store · `PRIOR` = prior engagement
recorded in version 1.2 · `DOCS` = project documentation. Full provenance for each code
is in `KNOWLEDGE_SOURCES_INDEX.md`.

## Baseline and session state

| ID | Failure mechanism | Observed in | Control |
|---|---|---|---|
| E-001 | An accepted, completed current form was rebuilt from a blank because a blank was available | PRIOR | F-01 |
| E-002 | Facility evidence from one audit was carried into another session as if it were permanent knowledge | PRIOR | F-02 |
| E-047 | Full inventory and hashing were repeated after scope was already locked, costing time and inviting drift | PRIOR | F-03 |

## Identity and physical targeting

| ID | Failure mechanism | Observed in | Control |
|---|---|---|---|
| E-003 | Table/row/cell coordinates were carried over from a prior run and reused as authority | PRIOR | F-05, F-06 |
| E-004 | Approval-map cells went stale after the controlled template's merge layout changed | REPO (`a72a16e`, B81/B89/B90) | F-06 |
| E-005 | A write landed in a vertical-merge continuation cell instead of the merge owner | REPO, PRIOR | F-07 |
| E-006 | Two distinct people were merged into one repeating row | PRIOR | F-08 |
| E-007 | Two distinct equipment or calibration records were merged into one repeating row | PRIOR | F-08 |
| E-008 | Adjacent fields with different definitions were treated as interchangeable | PRIOR | F-05 |

## Evidence authority and extraction

| ID | Failure mechanism | Observed in | Control |
|---|---|---|---|
| E-009 | A value was taken from a related but non-authoritative source | PRIOR | F-09 |
| E-010 | A value was authorized by a filename, folder name, ZIP name, or chat text | PRIOR | F-02, F-09 |
| E-011 | Retrieval similarity was allowed to select a writable location, not just a candidate value | REPO (`AGENTS.md`, `.cursor/rules`) | F-10 |
| E-012 | OCR noise was autofilled into a required field | REPO (`4d5cdfc`, B89 equipment) | F-11 |
| E-013 | A format assumption was too narrow for real OCR output and silently dropped valid values | REPO (`2f7da03`, TCO date separators) | F-11 |
| E-014 | A fallback path substituted a weaker source without disclosing the substitution | REPO (`1e59359`, PITP fallback) | F-12 |
| E-015 | Absence was declared after a single extraction path returned nothing | PRIOR | F-13 |
| E-016 | A low-confidence candidate was silently promoted to a filled value | REPO (`GOVERNANCE.md`) | F-14 |
| E-017 | Conflicting candidates were resolved by picking one, without recording the conflict | REPO (`GOVERNANCE.md`) | F-14 |

## Content preservation on rollover

| ID | Failure mechanism | Observed in | Control |
|---|---|---|---|
| E-018 | Owner permission and written-instruction content was dropped | PRIOR | F-15, F-16 |
| E-019 | Demonstration type or classification was dropped | PRIOR | F-15, F-16 |
| E-020 | Design-control classification / Type COC value was dropped | PRIOR | F-15, F-16 |
| E-021 | TCID revision, type, or entry was dropped or shifted into the wrong column | PRIOR | F-15, F-16 |
| E-022 | An auditor objective-evidence note was dropped | PRIOR | F-15, F-16 |

## Output fidelity

| ID | Failure mechanism | Observed in | Control |
|---|---|---|---|
| E-023 | A value was written into the DOCX XML but left inside a placeholder/content control, so the cell rendered blank in Word | REPO (`7adc4f2`, superseded by `c43e215`) | F-17 |
| E-024 | A visibly selected dropdown extracted as empty for machine checkers | PRIOR | F-18 |
| E-025 | A document-wide or changed-cell formatting sweep ran after the write | PRIOR | F-19 |
| E-026 | Controlled template structure was altered: row, merge, label, or page geometry | PRIOR | F-20 |
| E-027 | A filled DOCX was handed off without a passing structure guard | REPO (`AGENTS.md`) | F-20 |
| E-048 | A tool wrote paragraph-level replacements and silently simplified inline formatting, and detected content controls and MERGEFIELDs without writing them | SKILL (bundle Tool 03, v1) | F-17, F-18 |

## Scope, applicability, and findings

| ID | Failure mechanism | Observed in | Control |
|---|---|---|---|
| E-028 | Every QAPE element was assumed to be audited | PRIOR | F-04 |
| E-029 | Procedure or manual language was accepted as proof of implementation | PRIOR | F-21 |
| E-030 | B-2 technical measurement was used as QAPE program evidence, or QAPE narrative as B-2 technical proof | PRIOR | F-21 |
| E-031 | An optional or conditional section was populated because the blank form contained it | PRIOR | F-04, F-22 |
| E-032 | N/A was written to avoid a blank, without an authorizing rule | PRIOR | F-22 |
| E-033 | A draft-stage signature blank was treated as a final-release defect | PRIOR | F-23 |
| E-034 | REJECT was issued on suspicion, without requirement, identity, materiality, and proof | PRIOR | F-24 |

## Process, sources, and delivery

| ID | Failure mechanism | Observed in | Control |
|---|---|---|---|
| E-035 | A fix was verified on a helper or test path while the shipping path stayed unchanged | PRIOR | F-25 |
| E-036 | A fix was lost to revert and merge churn, then re-implemented repeatedly | REPO (`4ae44da` → `b18f74c` revert → restored at `2206e2a`, `91e1747`, `41ed7b7`) | F-26 |
| E-037 | Documentation described behavior the code did not implement | DOCS (retrieval-fallback docstring; README OCR-artifact claim) | F-27 |
| E-038 | Input parsing accepted one separator only, so a valid multi-value input was read as one unknown token | DOCS (`--review-forms` comma-only split) | F-28 |
| E-039 | Two source documents disagreed and both remained authoritative, with no stated precedence | DOCS (write authority: exact approval maps vs `machine_field_map.v1`) | F-29 |
| E-040 | Multiple near-identical copies of a reference document existed with no canonical marker | DRIVE (`B2 Master Schema` ×4, `B-2 Master Schema` ×2); REPO (`templates/` short-name aliases beside full controlled filenames) | F-30 |
| E-041 | A superseded registry file was used because the superseding one was not distinguishable by name | SKILL (`SOP.zip`: bare `field_registry.json` vs `SOP_00_*`) | F-30 |
| E-042 | Concurrent runs wrote to a shared output folder and collided | SKILL | F-31 |
| E-043 | The environment was assumed available: package index reachable, OCR binary on PATH, cloud-only files materialized on disk | DOCS (proxy 403 on install); SKILL (Tesseract PATH, OneDrive placeholders) | F-32 |
| E-044 | Temporary, debug, or render artifacts shipped inside the delivery folder | PRIOR | F-33 |
| E-045 | Completion was claimed because an output file existed, not because gates passed | PRIOR | F-34 |
| E-046 | A controlled instruction set was patched incrementally until its knowledge fragmented | PRIOR | F-35 |
| E-049 | A completeness or absence claim was published without a check that enforces it, and was false | SESSION (this pack's "no facility data" claim; 11 evidence-bearing files were present) | F-36 |
| E-050 | A snapshot walked the filesystem instead of the tracked file list, so ignored local state was in scope | SESSION (builder would have copied `.env` and `inputs/` in a working checkout) | F-37 |
