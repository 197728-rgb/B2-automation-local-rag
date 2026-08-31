# Do Not Repeat

Prohibition index, keyed to incidents. This file enforces nothing — enforcement is
`01_ACTIVE_RULES/` and `regression/`. The `State` column in `ERROR_LEDGER.md` says which
lines can actually fail.

| # | Do not | Incident |
|---|---|---|
| 1 | Put two people in one logical row | AAR-R001 |
| 2 | Put two equipment or calibration records in one row | AAR-R002 |
| 3 | Let a TCID revision, record type, or entry type disappear | AAR-R003 |
| 4 | Let owner permission or written instructions disappear | AAR-R004 |
| 5 | Accept a visible control value without checking it extracts | AAR-R005 |
| 6 | Run a document-wide or changed-cell formatting pass after the write | AAR-R006 |
| 7 | Rebuild an accepted completed current form from a blank | AAR-R007 |
| 8 | Compare two fields that are not the same semantic field | AAR-R008 |
| 9 | Treat a draft-stage signature blank as a final-release defect | AAR-R009 |
| 10 | Claim a baseline value was preserved while the target is blank | AAR-R010 |
| 11 | Let retrieval similarity choose a write location | AAR-R011 |
| 12 | Fill a required field from unvalidated OCR output | AAR-R012 |
| 13 | Substitute a weaker source without saying so | AAR-R013 |
| 14 | Declare evidence absent after one extraction path | AAR-R014 |
| 15 | Promote a low-confidence or conflicting value silently | AAR-R015 |
| 16 | Assume a value in the XML is visible to the reader | AAR-R016 |
| 17 | Hand off a filled document without a passing structure guard | AAR-R017 |
| 18 | Accept procedure language as proof of implementation | AAR-R018 |
| 19 | Evaluate a QAPE element that was not audited | AAR-R019 |
| 20 | Populate a conditional section because the blank form contains it | AAR-R020 |
| 21 | Verify a fix anywhere but the path that ships | AAR-R021 |
| 22 | Restore a lost fix without a test that fails without it | AAR-R022 |
| 23 | Use one of several near-identical references with no canonical marker | AAR-R023 |
| 24 | Report an environment failure as absent evidence | AAR-R024 |
| 25 | Publish a completeness or absence claim with nothing that can falsify it | AAR-R025 |
| 26 | Absorb an adjacent problem instead of naming it and handing it back | AAR-R026 |
| 27 | Authorize a value from a filename, folder, ZIP name, chat, or another facility's example | AAR-R003 |
| 28 | Carry one audit's facility evidence into another session | AAR-R023 |
