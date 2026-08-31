# Repeatable B-2 / QAPE Workflow

Activity-code agnostic, element agnostic, facility agnostic, tool agnostic. The phases do
not change between jobs; only what is discovered inside them does.

Rules are `01_ACTIVE_RULES/ACTIVE_RULES.md`. This file is *how to execute them in order*
and does not restate them.

## Phase 0 — Mode lock (AR-01, AR-02)

| Mode | Applies when | Authority |
|---|---|---|
| MAINTENANCE / ROLLOVER | An accepted completed current-form document exists | Change only evidence-supported exceptions; preserve everything still valid |
| NEW FILL | No accepted completed baseline, and a current approved blank exists | Populate only evidence-supported fields |
| FINAL REVIEW | Asked to check, analyze, or approve | No write authority. APPROVE / REJECT / HOLD only |

Gate G-1.

## Phase 1 — Scope inventory, once

Classify everything supplied: in-scope B-2 forms by controlled title and activity code;
QAPE summary and detail records and which elements are actually audited; supporting
evidence groups; controlled blanks and references; and everything out of scope — examples,
drafts, temporary files, automation artifacts.

Re-inventory only on a named trigger: new files arrive, an identity becomes uncertain, or
a completeness check finds a gap. Repeated rescanning after scope lock wastes time and
lets scope drift silently.

Gate G-2.

## Phase 2 — Form and element discovery (AR-04)

**B-2, per form:** read the controlled title and header; identify activity code and
variant; enumerate the labelled fields and sections actually present; classify each as
scalar, selection/control, narrative, repeating row, or conditional section.

**QAPE:** read current summary marks and assignments; identify the elements actually
audited; locate their detail rows; keep Manual and Compliance as separate determinations;
leave non-audited elements alone unless current instructions say otherwise.

Nothing about structure is inherited from a previous form, year, or this archive.

## Phase 3 — Authority and identity (AR-03, AR-05, AR-08)

For every destination fact establish: semantic identity, admissible source classes, exact
entity identity, applicability, and revision/effective context.

Proximity, familiarity, and another facility's example authorize nothing.

Gate G-3.

## Phase 4 — Field mapping (AR-05, AR-06)

Semantic destination first, then the unique physical target in the current file.

Repeating tables are worked one entity at a time: identify the entity, resolve its row,
write that entity, move on. Mechanics in `FIELD_MAPPING_AND_COMPLETENESS.md`.

## Phase 5 — Evidence reconciliation (AR-07)

Assign every relevant target field and every populated baseline fact a disposition from
the controlled set. Nothing reaches handoff undecided.

Before concluding a required field is absent, exhaust the applicable surfaces — fields,
controls, continuations, attachments, widgets — and rule out an environment failure. An
unreachable index, a missing OCR binary, and an unmaterialized cloud file all present as
"nothing found" and lead to exactly the wrong correction.

Gate G-4.

## Phase 6 — Governed write (AR-09, AR-10)

Resolve the unique cell or control; write only the authorized value; apply that field's
formatting in the same operation; leave unrelated runs, cells, and geometry untouched.

Gate G-5.

## Phase 7 — Verification (AR-11)

Three independent passes, none substituting for another:

- **Semantic** — baseline facts preserved, new values supported, rows distinct,
  traceability complete, marks aligned to audited scope.
- **Machine-readable** — extraction returns intended values; control selections extract;
  merged-cell ownership correct.
- **Visual** — every page rendered and inspected, tail pages included: no truncation, no
  broken tables, no unintended blank pages, no geometry damage.

Gate G-6.

## Phase 8 — Findings and release (AR-12)

A finding requires requirement, field meaning, entity identity, materiality, and proof.
Missing proof is HOLD, never REJECT. Draft, final, and released documents are held to
different completion requirements.

Then run the gate. Completion is its output.

Gates G-7, G-8.

## Applying this to a form type not seen before

The phases hold. Only three things are rediscovered: which form (controlled title and
revision), which fields and sections (that form's own structure), and which codes or
elements are in scope (the current assignment).

If a step cannot run without knowing the activity code in advance, the step is written
wrong. Fix the step; do not add a code-specific branch.
