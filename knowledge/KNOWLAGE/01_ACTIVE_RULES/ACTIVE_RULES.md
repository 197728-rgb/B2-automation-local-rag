# Active Rules

Twelve rules. Always loaded, always followed. Nothing else in this archive overrides them.

Each rule is stated **here and nowhere else**. Other files reference `AR-##`; they do not
restate it. Method is in `02_WORKING_METHOD/`, evidence for why in `03_LESSONS/`.

| ID | Rule |
|---|---|
| **AR-01** | **Lock job mode first.** MAINTENANCE, NEW FILL, or FINAL REVIEW, named before any evidence is read, together with the baseline document. FINAL REVIEW has no write authority. |
| **AR-02** | **An existing completed current form is the maintenance baseline.** Rebuild from a blank only when no accepted baseline exists, or when rebuild is explicitly required. A blank being available is not a reason. |
| **AR-03** | **Current audit evidence is the only authority for current facility values.** Not filenames, folders, ZIP names, chat, prior audits, examples, or this archive. |
| **AR-04** | **Discover fields from the current B-2/QAPE form.** Read the controlled title and revision in hand. Never rely on table, row, or cell coordinates from a previous run. |
| **AR-05** | **Resolve semantic field identity before physical target.** What the field *is*, then where it currently lives. Never the reverse. |
| **AR-06** | **One person, equipment item, qualification, or calibration is one logical record.** Distinct identities never share a row; values are never concatenated. |
| **AR-07** | **No populated baseline value disappears without a disposition.** Every source fact ends as CONFIRMED_VALUE, PRESERVE_BASELINE, CONTROLLED_BLANK, AUTHORIZED_NA, WITHHOLD_CONFLICT, or UNVERIFIABLE. |
| **AR-08** | **No target value is written without evidence.** Every written value names an admissible source for that specific field. Retrieval and model judgment propose; only an exact, versioned map authorizes a location. |
| **AR-09** | **Preserve protected template structure.** Rows, columns, merges, labels, and page geometry are identical before and after, outside authorized cells. Write to the merge owner, never a continuation cell. |
| **AR-10** | **Apply formatting during the write, not afterward.** Value and formatting are one operation. No document-wide or changed-cell pass. |
| **AR-11** | **Verify three ways: semantic content, machine-readable controls, and every rendered page.** A clean render is necessary and not sufficient. What a reader sees must equal what an extractor reads. |
| **AR-12** | **Do not ship with failed release gates.** See `RELEASE_GATES.md`. Completion is the gate's output, not an assessment. |

## When a rule cannot be followed

Say so, name the rule, and stop. Do not proceed under a weakened version of it.
