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
