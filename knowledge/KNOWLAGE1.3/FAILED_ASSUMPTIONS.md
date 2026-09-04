# Failed Assumptions

Beliefs that were actually held during this work and proved false.

This file owns **the belief and its correction**. Actions and controls live elsewhere
(`F-##`, `G-#`); this is the record of what was wrongly taken for granted.

| ID | The assumption | What is actually true |
|---|---|---|
| A-01 | One fixed table map fits every activity code | Field layout is a property of the specific controlled form in hand and must be discovered from it |
| A-02 | Every QAPE job audits the same elements | The audited set is assigned per package and is usually a subset |
| A-03 | Last year's row position identifies this year's field | Only semantic identity survives a revision; the row may not exist |
| A-04 | A related document can prove any related field | Admissibility is defined per destination fact, not per document |
| A-05 | An empty extraction means no value exists | Controls, merge owners, continuations, attachments, and alternate labels all return empty to a naive read |
| A-06 | Blank is always the safe default | A blank asserts non-applicability or non-requirement, which is a claim needing authorization |
| A-07 | N/A is safe for any unused row | N/A is a specific controlled state, valid only where the form or rule allows it |
| A-08 | Two similar people or two similar instruments can share a row | Similar is not the same; distinct identities require distinct records |
| A-09 | A written procedure proves the program is implemented | A procedure can support a manual determination; implementation needs evidence of the act |
| A-10 | A CONFIRMED tool finding is automatically valid | Requirement, field meaning, entity identity, and materiality still decide |
| A-11 | A successful render proves the fill is correct | The render only proves the document opens and paginates |
| A-12 | If the value is visible in Word, extraction will see it | Content controls and placeholders can display a value that extracts as empty |
| A-13 | If the value is in the XML, the user will see it | A value written inside a placeholder or control can render as an empty cell |
| A-14 | Fixing the helper fixes the delivered output | Only the shipping path determines what is delivered |
| A-15 | Starting from a blank is always safest | Where an accepted completed current form exists, it is the maintenance baseline |
| A-16 | Patching is always safer than regenerating | After proven corruption, regeneration from a correct source is the safer move |
| A-17 | More inventory is always safer | After scope lock, repeated scanning costs time and invites drift |
| A-18 | Two copies of a reference document are harmless redundancy | They diverge the first time one is edited, and nothing marks which one won |
| A-19 | A newer file in a bundle is the current one | Supersession is declared, not inferred from position, timestamp, or filename length |
| A-20 | The tool will find the evidence files it was pointed at | Cloud-placeholder files, unsynced folders, and permission gaps all present as missing input |
| A-21 | A regex tuned on clean text will hold on OCR output | Real OCR varies separators, spacing, and character shapes; narrow patterns silently discard valid values |
| A-22 | Documented behavior matches implemented behavior | Docstrings and READMEs drift ahead of and behind the code, in both directions |
| A-23 | Two guidance documents on one subject can both be authoritative | Without a declared split, each reader follows a different one and the conflict surfaces at delivery |
| A-24 | A fix, once merged, stays merged | Reverts and merge churn have repeatedly removed fixes that had no test defending them |
| A-25 | Concurrent runs can share one output folder | Shared output roots collide, overwrite, and produce artifacts belonging to no single run |
