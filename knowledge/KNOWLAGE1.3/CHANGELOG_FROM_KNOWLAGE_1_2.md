# Changelog from Version 1.2

Delta from `CLAUDE_KNOWLEDGE_REPEATABILITY_FIXED`. That package is superseded and should
not be loaded alongside this one.

---

## Kept

Version 1.2's core held up against everything read this session and carries forward
unchanged in substance:

semantic identity before physical targeting · field-specific authority · two-way
completeness · source exhaustion before absence · repeating-row identity · manual versus
compliance separation · merged-cell and content-control awareness · state-based baseline
selection · write-level formatting · shipping-path validation · known-bad plus known-good
regression · exact delivery allowlist · document-status lock · new-audit/new-session
evidence isolation · no prompt patches.

## Restructured

Version 1.2 stated the same fact in several files — the personnel-row rule appeared in its
error ledger, its hard lessons, and its do-not-repeat list. That is survivable at fifteen
files and becomes contradiction as the pack grows.

1.3 gives each file one axis and one ID space, and cross-references by ID:

| Axis | 1.3 file | ID |
|---|---|---|
| What went wrong, and where | `ERROR_LEDGER.md` | `E-###` |
| What prevents it, and its proof | `DURABLE_FIXES.md` | `F-##` |
| Why it generalizes | `HARD_LESSONS.md` | `L-##` |
| What was wrongly believed | `FAILED_ASSUMPTIONS.md` | `A-##` |
| When to refuse to continue | `DO_NOT_REPEAT.md` | `G-#` |
| What test proves it | `VALIDATION_AND_REGRESSION.md` | `R-##` |

`DO_NOT_REPEAT.md` changed most: from 27 restated prohibitions to 9 ordered gates, each
naming a stop condition and what releases it. The prohibitions themselves were not lost —
they are the mechanisms in `ERROR_LEDGER.md` and the controls in `DURABLE_FIXES.md`.

## Added

**Grounding.** 1.2 was documentation-only and could not cite where its lessons came from.
1.3 traces 15 mechanisms to specific commits, documents, and observed store state, with
provenance codes in `ERROR_LEDGER.md` and sources in `KNOWLEDGE_SOURCES_INDEX.md`.

**New mechanisms not present in 1.2** — E-011 through E-014, E-016, E-017, E-023, E-036
through E-043, and E-048. These come from the repository, its history, the platform skill
guide, and the Drive store: retrieval authorizing locations, OCR noise reaching required
fields, patterns too narrow for real OCR output, undisclosed fallbacks, silent promotion of
low-confidence and conflicting values, values trapped inside content controls, fixes lost
to revert churn, documentation drift, single-separator parsing, undeclared precedence
between guidance documents, uncanonical duplicates, superseded registry selection, shared
output collisions, and environment failure misread as missing evidence.

**New controls** F-06, F-10 through F-12, F-17, F-26 through F-32, answering those.

**New material.** Project source, git history, the platform skill guide, and a Drive index
are packed as snapshots. `KNOWLEDGE_SOURCES_INDEX.md`, `SESSION_SUMMARY.md`, and
`GOOGLE_DRIVE_UPDATE_SUGGESTIONS.md` are new. `tools/build_knowlage_archive.py` makes the
archive reproducible and generates both manifests.

**Conflict resolution.** Seven real disagreements between sources are resolved once, as
`C-1` through `C-7`. The write-authority split — exact approval maps for the local inbox
path, `machine_field_map.v1` for the autonomous path — was stated by neither source.

## Corrected

**"Blank is never the safe default" is stated more carefully.** 1.2's framing risked being
read as a prohibition on blanks. A controlled blank is a legitimate disposition; what needs
authorization is the claim it makes.

**Regression coverage was one-sided.** 1.2 named known-bad and known-good in principle but
listed mostly known-bad cases. 1.3 pairs both halves for all 32 cases, so a control cannot
pass by rejecting everything.

**Completion was under-specified.** 1.2 required gates to pass. 1.3 requires them to pass
*on the delivered artifact* (G-9, F-25), which is the failure that keeps recurring.

## Removed

1.2's `CLAUDE_REFERENCE_SUGGESTION.md`, `KNOWLEDGE_UPDATE_SUGGESTIONS.md`,
`FUTURE_AGENT_NOTES.md`, and `ENGAGEMENT_LESSONS_SUGGESTION.md` overlapped heavily — the
activation block, the promotion list, and the startup notes each restated the others.
Consolidated into `ENGAGEMENT_LESSONS_SUGGESTION.md` (proposals, with cost and benefit
stated) and `FUTURE_AGENT_NOTES.md` (startup and extension only).

1.2's separate `MANIFEST.md` narrative is gone; both manifests are now generated.

Nothing from 1.2 was dropped on judgment alone. Every removal is either restated once
elsewhere under an ID or listed above.
