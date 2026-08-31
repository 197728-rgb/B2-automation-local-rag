# AAR Audit Report Playbook

The procedure. Activity-code agnostic, element agnostic, facility agnostic, tool agnostic.

This file owns **the sequence of work**. Field mechanics live in
`FIELD_AUTHORITY_AND_COMPLETENESS.md`; stop conditions in `DO_NOT_REPEAT.md`; verification
cases in `VALIDATION_AND_REGRESSION.md`.

---

## Phase 0 — Mode lock

Choose one, and record it with the baseline document.

| Mode | Applies when | Authority |
|---|---|---|
| **MAINTENANCE / ROLLOVER** | An accepted, completed current-form document exists | Change only evidence-supported exceptions; preserve everything still valid |
| **NEW FILL** | No accepted completed baseline exists, and a current approved blank is available | Populate only evidence-supported fields |
| **FINAL REVIEW** | Asked to check, analyze, or approve | No write authority; outcome is APPROVE / REJECT / HOLD |

A blank form being available is not by itself a reason to enter NEW FILL.

Gate: G-1.

## Phase 1 — One-time scope inventory

Once, at job start, classify everything supplied:

1. in-scope B-2 forms, by controlled title and activity code;
2. QAPE summary and detail records, and which elements are actually audited;
3. current supporting evidence groups;
4. current controlled blank and reference forms;
5. everything else — examples, drafts, temporary files, automation artifacts —
   marked as out of scope.

Re-inventory only on a named trigger: new files arrive, an identity becomes uncertain, or
a completeness check finds an unexpected gap.

Gate: G-2.

## Phase 2 — Form and element discovery

Read the document in hand.

**For each B-2 form:** read the controlled title and header; identify the activity code
and variant; enumerate the labelled fields and sections actually present; classify each
as scalar, selection/control, narrative, repeating row, or conditional section.

**For QAPE:** read the current summary marks and assignments; identify the elements
actually audited; locate their detail rows; keep the manual determination and the
compliance determination as separate questions; leave non-audited elements alone unless
current instructions say otherwise.

Nothing about a form's structure is inherited from a previous form, a previous year, or
this pack.

## Phase 3 — Authority and identity

For every destination fact, establish: its semantic identity, the source classes
admissible for it, the exact entity it concerns, its applicability, and its
revision/effective context.

Proximity, familiarity, filename, folder, and other facilities' examples authorize
nothing.

Gate: G-4.

## Phase 4 — Field mapping

Resolve the **semantic destination first**, then the unique physical target in the
current file. Never in the other order.

For repeating tables, work one entity at a time: identify the entity, resolve its row,
write that entity, move on.

Gate: G-3, G-6.

## Phase 5 — Evidence reconciliation

Assign every relevant field and every populated baseline fact a disposition. The
disposition set and the completeness rules are defined in
`FIELD_AUTHORITY_AND_COMPLETENESS.md`.

Nothing may reach handoff undecided.

Gate: G-5.

## Phase 6 — Governed write

Writer modes only:

1. resolve the unique physical cell or control;
2. write only the authorized value;
3. apply that field's formatting in the same operation;
4. leave unrelated runs, cells, and geometry untouched.

Gate: G-6.

## Phase 7 — Verification

Three independent passes, all required, none substituting for another:

- **Semantic** — baseline facts preserved, new values supported, rows distinct,
  traceability fields complete, marks aligned to audited scope.
- **Machine-readable** — extraction returns the intended values; control selections are
  extractable; merged-cell ownership is correct.
- **Visual** — every page rendered and inspected, including tail pages: no truncation,
  no broken tables, no unintended blank pages, no geometry damage.

Gate: G-7.

## Phase 8 — Release

Confirm on the delivered artifact — not on a copy, a helper, or an earlier run — that
every disposition is resolved, no baseline fact was lost, no entity was merged, no
template geometry changed, and the delivery folder holds only intended finals.

State completion only after that.

Gate: G-8 for findings, G-9 for completion.

---

## Applying this to a report type not seen before

The phases do not change. Only three things are rediscovered each time:

1. **Which form**, from its controlled title and revision.
2. **Which fields and sections**, from that form's own structure.
3. **Which elements or codes are in scope**, from the current assignment.

If a step in this playbook cannot be executed without knowing the activity code in
advance, that step is written wrong — fix the step rather than adding a code-specific
branch.
