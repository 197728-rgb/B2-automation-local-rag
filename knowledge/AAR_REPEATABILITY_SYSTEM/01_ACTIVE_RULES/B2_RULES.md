# B-2 Rules

## 1. One identity per logical row

One source identity resolves to one target row. Distinct people, instruments,
calibrations, procedures, and records are never concatenated.

Identity keys — personnel: name or ID, qualification number, method and level.
Equipment: type, ID or serial, function, calibration record.

**Known-bad:** `M. StuckeyM. Perry | IIII | UTTVT` → FAIL
**Known-good:** `M. Stuckey | II | UTT` and `M. Perry | II | VT` → PASS

Blocks AAR-R001, AAR-R002. Enforced by `check_personnel_row_identity`,
`check_equipment_row_identity`. A level outside {I, II, III} or a method outside the
controlled set is treated as two values glued together.

## 2. Discover fields from the current controlled form

Field layout is a property of the form in hand — its controlled title and revision. Never
inherited from a previous form, a previous year, or this system. Physical coordinates are
derived output; they expire with the document instance.

## 3. High-risk fields are inspected every run

Whether or not the run expects them to change: owner permission and written instructions ·
demonstration type or classification · design-control classification and Type COC ·
personnel and qualification records · equipment and calibration records · NDT approver
identifiers · TCID revision, record type, entry type, work description · traceability and
marking · auditor objective-evidence notes · signature and attestation state.

These are the fields that have actually gone missing.

Blocks AAR-R003, AAR-R004.

## 4. Candidate values pass a noise gate

A candidate passes a format and plausibility check for its field type before it is
eligible to fill. The check is widened to real observed input, not the ideal case: OCR
varies separators, spacing, and character shapes.

Any fallback or degraded source is named in the artifact. A silent substitution produces
an output indistinguishable from a confident one.

Blocks AAR-R012, AAR-R013.

## 5. Conditional sections

A section on a blank form may be applicable, conditionally applicable, or unused. Do not
populate it because it exists; do not delete it because it is unused. `CONTROLLED_BLANK`
or `AUTHORIZED_NA`, with the authorizing rule cited.

Blocks AAR-R020.
