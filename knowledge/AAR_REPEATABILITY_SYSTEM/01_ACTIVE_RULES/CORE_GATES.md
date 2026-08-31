# Core Gates

Always loaded. These are refusal points, not advice. Work stops until the gate clears.

Each gate names the incidents it blocks. `RELEASE_RULES.md` decides what ships.

## G-1 — Mode and baseline, before reading evidence

Declare MAINTENANCE / NEW FILL / FINAL REVIEW and name the baseline document.

**Refuse to continue if** no mode is declared, or NEW FILL is chosen while an accepted
completed current form exists, or evidence from another audit is in the working set.

Blocks AAR-R007. Enforced by `check_baseline_selection`.

## G-2 — Scope from the current controlled documents

Derive in-scope forms, activity codes, and audited elements from the documents in hand.

**Refuse to continue if** scope came from a prior year, a filename, a folder name, or this
system.

Blocks AAR-R019, AAR-R020.

## G-3 — Absence is a conclusion, not an observation

**Refuse to declare a required field absent if** only one extraction path was tried, or if
the failure could be environmental — unreachable index, missing OCR binary, unmaterialized
cloud file.

An environment failure is reported as environment state. It is never evidence absence.

Blocks AAR-R014, AAR-R024.

## G-4 — Authority, before a value is eligible

Every value names an admissible source for that specific field. Retrieval and model
judgment propose; only an exact, versioned map authorizes a location.

**Refuse to write if** the only support is similarity, if a comparison is between two
different semantic fields, or if a low-confidence or conflicting candidate is being
promoted without surfacing.

Blocks AAR-R008, AAR-R011, AAR-R015. `check_field_comparison_identity` enforces the
comparison half.

## G-5 — Two-way completeness, before handoff

Every populated baseline fact and every relevant target field ends with one disposition
from the controlled set: `CONFIRMED_VALUE`, `PRESERVE_BASELINE`, `CONTROLLED_BLANK`,
`AUTHORIZED_NA`, `WITHHOLD_CONFLICT`, `UNVERIFIABLE`.

**Refuse to hand off if** any fact is `UNACCOUNTED`, or a fact claimed preserved is blank
in the target.

Blocks AAR-R003, AAR-R004, AAR-R010. Enforced by `check_two_way_completeness`.

## G-6 — Scope, before starting and before each new thread of work

State what was asked and what "done" looks like. Deliver that.

**Refuse to continue if** you are about to work on something the request did not ask for.
Adjacent problems — a failing check you did not cause, a defect a bot found in passing, a
better structure you thought of — get **named and handed back**, not absorbed.

Three questions, each time you are about to start something:

1. Did they ask for this?
2. If no: does the asked-for thing fail without it?
3. If still no: say it exists, and stop.

Rebuilding, restructuring, or "while I'm here" work is scope expansion regardless of how
sound it is. A correct improvement nobody asked for still spends the request's time and
still buries the deliverable.

Blocks AAR-R026. Enforced by `check_scope_discipline`.
