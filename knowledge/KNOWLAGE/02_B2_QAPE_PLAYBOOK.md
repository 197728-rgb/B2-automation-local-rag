# 02 B-2 / QAPE PLAYBOOK

The single authoritative home for the operating method. Rules are referenced by number
from `01_ACTIVE_RULES.md` and not restated.

## Phase 1 — Lock the job

1. Declare the job mode and name the baseline document — new work starts from the
   current clean blank, rework continues from the same working form. *(Rule 3)*
2. Identify the exact deliverable family and controlled template, by controlled title and
   revision as printed on the document.
3. Lock scope: in-scope forms, activity codes, and the QAPE elements actually assigned.
4. Record template identity before evaluating any evidence. *(Rule 4)*

Scope is established once. Re-inventory only on a named trigger: new material arrives, an
identity becomes uncertain, or a completeness check exposes a gap.

## Phase 2 — Inspect destination contracts

For every writable field or QAPE leaf, determine before choosing evidence: *(Rule 5)*

- semantic label as printed;
- expected record and data type;
- dropdown or content-control vocabulary where present;
- static or prefilled text;
- merged-cell ownership;
- conditional applicability;
- semantic leaf identity; its current row is resolved afterwards, not used to identify it. *(Rule 7)*

## Phase 3 — Discover authoritative evidence

1. Search all in-scope authoritative source families. *(Rule 2)*
2. Do not treat filenames, folders, prior reports, or examples as fact authority.
3. Do not accept a capped, filtered, or paginated result as a complete inventory unless
   independently validated. *(Rule 18)*
4. Record source exhaustion before classifying required evidence as absent, and rule out
   environment failure first. *(Rules 9, 10)*

## Phase 4 — Resolve identities

Resolve each semantic identity independently, with exact structured matching rather than
substring logic. *(Rule 13)*

Do not collapse Procedure, Form/Report, and qualification records that share an
identifier. *(Rule 6)* Do not identify a QAPE leaf by printed section number alone.
*(Rule 7)*

One source identity resolves to one target row; work one entity at a time. *(Rule 8)*

Resolve field identity by form/version, section, exact label, meaning, entity, and current
control or merge owner. Page, table, row, column, and cell positions are run-local
diagnostics only, never a durable key and never carried in from another run. *(Rule 4)*

## Phase 5 — Evaluate predicates

Keep predicates separate: documented coverage · implementation · qualification · approval ·
demonstration · current-event proof. *(Rule 14)*

Program-level and technical-demonstration evidence are not interchangeable in either
direction. A master or register entry may support identity or status; it does not
establish that a specific audited event occurred.

## Phase 6 — Assign disposition

Every required semantic identity receives one explicit state: *(Rules 11, 12)*

`POPULATED_VERIFIED` · `BLANK_UNSUPPORTED` · `WITHHELD_FLAGGED_DISCREPANCY`

A blank is a governed state: it asserts that nothing was required or supported, and that
assertion needs the same authorization as a value. Never infer that an event did not occur
because current evidence does not prove it.

Nothing reaches handoff unevaluated.

## Phase 7 — Write

1. Confirm the candidate passes the admissibility check for its destination type.
   *(Rule 15)*
2. Confirm the write location is authorized by an approved exact-version map, or by a
   run-specific semantic map derived from the current form and validated against it
   before any write. *(Rule 16)*
3. Resolve the unique cell or control, writing to the merge owner and never to a
   continuation cell.
4. Write the authorized value and apply that field's formatting in the same operation.
   *(Rule 19)*
5. Leave unrelated runs, cells, and geometry untouched.

## Phase 8 — Verify

Three independent passes, none substituting for another: *(Rule 20)*

- **Semantic** — dispositions resolved both ways, rows distinct, traceability complete,
  marks aligned to assigned scope.
- **Machine-readable** — extraction returns the intended values; control selections
  extract; merged ownership correct.
- **Structural and visual** — protected structure matches the pristine template; every
  page rendered and inspected, including the document tail.

## Phase 9 — Findings and release

A finding requires requirement, field meaning, entity identity, materiality, and proof.
Missing proof is HOLD, never REJECT. Draft, final, and released documents carry different
completion expectations.

Then apply `04_REGRESSION_AND_RELEASE_GATES.md`. Release readiness is the gate's output,
not an assessment of the work.

## Applying this to an unfamiliar deliverable

The phases do not change. Three things are rediscovered each time: which controlled form,
which fields and sections it actually contains, and which codes or elements are assigned.
Anything that cannot run without knowing the activity code in advance is written wrong —
fix the step rather than adding a code-specific branch.
