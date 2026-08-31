# DOCX Rules

## 1. Formatting belongs to the write

Value and formatting are applied in one governed operation. No document-wide pass, no
changed-cell sweep afterward — a later pass cannot distinguish an authorized change from
untouched controlled content, so it can only act indiscriminately.

Protected geometry — rows, columns, merges, labels, page structure — is identical before
and after, outside the authorized cells.

**Known-bad:** `rows_after != rows_before`, or `document_wide_formatting_pass: true` → FAIL

Blocks AAR-R006. Enforced by `check_structure_preserved`.

## 2. Visible and machine-readable must agree

A reader sees the render; an automated checker sees the extraction. Both are consumed
downstream, and a field can satisfy one while failing the other.

**Known-bad:** visible `Tank Car Tank`, machine-readable blank → FAIL
**Known-good:** visible and extracted values equal → PASS

A value written into the XML but left inside a placeholder or content control renders as
an empty cell. That is the same defect from the other direction.

Blocks AAR-R005, AAR-R016. Enforced by `check_machine_readability`.

## 3. Write authority is separate from suggestion

Retrieval proposes candidates. Only an exact per-form, per-version map authorizes a write
location. Never a generic, nearest, latest, or similar map.

Resolve the merge owner before writing; a continuation cell never receives a write.

Blocks AAR-R011.
