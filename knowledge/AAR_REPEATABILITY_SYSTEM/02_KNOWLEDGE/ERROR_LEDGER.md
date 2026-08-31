# Incident Ledger

Every incident carries a permanent ID. Tests reference the ID, the release gate counts by
ID, and the forensic archive holds the original occurrence.

An incident is **prevented** only when a control exists, a test exercises it, and the gate
enforces it. `PREVENTED` below means all three; `RULE ONLY` means the rule exists but no
test can fail — those are the gaps worth closing next.

| ID | Incident | Control | Test | Gate counter | State |
|---|---|---|---|---|---|
| AAR-R001 | Repeating personnel records concatenated into one row | `B2_RULES` §1 | TEST-B81-001 | MERGED IDENTITIES | PREVENTED |
| AAR-R002 | Repeating equipment/calibration records concatenated | `B2_RULES` §1 | TEST-B81-002 | MERGED IDENTITIES | PREVENTED |
| AAR-R003 | TCID fields silently dropped on rollover | `B2_RULES` §3 | TEST-B24-003 | UNACCOUNTED SOURCE FACTS | PREVENTED |
| AAR-R004 | Owner instructions silently dropped | `B2_RULES` §3 | TEST-B24-010 | UNACCOUNTED SOURCE FACTS | PREVENTED |
| AAR-R005 | Visible content-control value machine-readable as blank | `DOCX_RULES` §2 | TEST-DOCX-005 | MACHINE-READABILITY FAILURES | PREVENTED |
| AAR-R006 | Post-hoc formatting altered protected content | `DOCX_RULES` §1 | TEST-DOCX-006 | STRUCTURE VIOLATIONS | PREVENTED |
| AAR-R007 | Current completed form unnecessarily rebuilt | `CORE_GATES` G-1 | TEST-CORE-007 | STRUCTURE VIOLATIONS | PREVENTED |
| AAR-R008 | Checker compared semantically different fields | `CORE_GATES` G-4 | TEST-CORE-008 | UNSUPPORTED TARGET VALUES | PREVENTED |
| AAR-R009 | Draft signature treated as final-document defect | `QAPE_RULES` §4 | TEST-QAPE-009 | — | PREVENTED |
| AAR-R010 | Populated baseline field blank in rollover with no disposition | `CORE_GATES` G-5 | TEST-B24-010 | UNACCOUNTED SOURCE FACTS | PREVENTED |
| AAR-R011 | Retrieval similarity allowed to authorize a write location | `DOCX_RULES` §3 | — | — | RULE ONLY |
| AAR-R012 | OCR noise autofilled into a required field | `B2_RULES` §4 | — | — | RULE ONLY |
| AAR-R013 | A fallback substituted a weaker source without disclosure | `B2_RULES` §4 | — | — | RULE ONLY |
| AAR-R014 | Absence declared after a single extraction path | `CORE_GATES` G-3 | — | — | RULE ONLY |
| AAR-R015 | Low-confidence or conflicting value silently promoted | `CORE_GATES` G-4 | — | — | RULE ONLY |
| AAR-R016 | Value written into XML but trapped inside a content control | `DOCX_RULES` §2 | — | — | RULE ONLY |
| AAR-R017 | Filled document handed off without a passing structure guard | `RELEASE_RULES` §2 | — | — | RULE ONLY |
| AAR-R018 | Procedure language accepted as proof of implementation | `QAPE_RULES` §2 | — | — | RULE ONLY |
| AAR-R019 | Non-audited QAPE element evaluated as required | `QAPE_RULES` §1 | — | — | RULE ONLY |
| AAR-R020 | Conditional section populated with no applicable evidence | `B2_RULES` §5 | — | — | RULE ONLY |
| AAR-R021 | Fix verified on a helper path while the shipping path was unchanged | `RELEASE_RULES` §3 | — | — | RULE ONLY |
| AAR-R022 | Fix lost to revert/merge churn and re-implemented repeatedly | `RELEASE_RULES` §4 | — | — | RULE ONLY |
| AAR-R023 | Near-duplicate reference used with no canonical marker | `RELEASE_RULES` §5 | — | — | RULE ONLY |
| AAR-R024 | Environment failure reported as absent evidence | `CORE_GATES` G-3 | — | — | RULE ONLY |
| AAR-R025 | A completeness or absence claim published without a check that enforces it | `RELEASE_RULES` §1 | — | — | RULE ONLY |
| AAR-R026 | Agent expanded scope past the request: absorbed adjacent problems instead of naming them | `CORE_GATES` G-6 | TEST-CORE-026 | — | PREVENTED |

## AAR-R025 is this system's own founding incident

The knowledge pack that preceded this system stated: *"Confirmed absent from this archive:
no facility name, personnel identifier, car mark, calibration date, finding, or completed
form."*

That claim was false. The archive carried three completed B-2 forms with their validation
reports, a fixture holding a TCO name and an approver, and a facility profile with an NDT
personnel roster. The claim had been written, reviewed, and published; nothing could fail
because of it.

It is the clearest possible statement of why this system exists. A lesson that lives only
in a document is a lesson the next session can write around. The fix was not better
wording — it was a check that refuses to build, demonstrated failing on the contaminated
input before it was trusted.

Full incident: `../04_FORENSIC_ARCHIVE/incidents/AAR-R025.md`.
