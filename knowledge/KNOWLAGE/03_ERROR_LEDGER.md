# 03 ERROR LEDGER

Generalized failure classes only. This file is not current audit authority and contains no
customer-specific B-2 / QAPE facts.

Every class carries `ERROR → ROOT CAUSE → DURABLE RULE → REGRESSION TEST → RELEASE GATE`.
Where `Test` reads `—`, the class is governed by a rule but nothing yet fails on
recurrence; that is stated rather than implied.

## Authority and evidence

| ID | Failure class | Root cause | Rule | Test | Gate |
|---|---|---|---|---|---|
| E-001 | Convenience source outranked authoritative evidence | A nearby string, filename, folder, archive name, or example was easier to use than the governing record | 2 | — | 3 |
| E-002 | Retrieval similarity selected a write location | Proposing a candidate and authorizing a destination were treated as one capability | 16 | — | 8 |
| E-003 | Extraction noise reached a required field | No plausibility check stood between extraction and fill | 15 | R-05 | 8 |
| E-004 | A pattern calibrated on clean text discarded valid extracted values | The ideal input was used as the specification instead of the observed input | 15 | R-05 | 8 |
| E-005 | A degraded or fallback source was substituted without disclosure | Fallback was silent by default, so its output was indistinguishable from a confident one | 15 | — | 8 |
| E-006 | Evidence absence was declared after one extraction path | The search was mistaken for the record | 9 | — | 3 |
| E-007 | Environment failure was reported as absent evidence | A missing tool, unreachable source, and unmaterialized file all present as "nothing found" | 10 | R-11 | 3 |
| E-008 | A master or register entry was treated as event proof | Static status was confused with proof of a specific occurrence | 14 | R-08 | 5 |
| E-009 | Documented coverage was accepted as implementation proof | Distinct predicates were evaluated as one question | 14 | — | 5 |

## Identity

| ID | Failure class | Root cause | Rule | Test | Gate |
|---|---|---|---|---|---|
| E-010 | Record types sharing an identifier were conflated | Procedure, Form/Report, and qualification records were treated as one identity | 6 | R-06 | 4 |
| E-011 | A QAPE leaf identity collided | A printed section number was treated as uniquely identifying a physical leaf | 7 | R-07 | 4 |
| E-012 | Substring matching produced a false identity decision | Naive containment replaced structured identity resolution | 13 | R-09 | 8 |
| E-013 | Distinct records were merged into one logical row | A row was treated as a text bucket rather than a record | 8 | R-01, R-02 | 4 |
| E-014 | Position was used as a field's durable identity, or coordinates were reused across runs | Geometry was stored as knowledge instead of derived per run | 4 | R-10, R-20 | 1 |
| E-015 | Semantically different fields were compared | Physical proximity was mistaken for semantic identity | 4 | R-12 | 4 |

## Completeness

| ID | Failure class | Root cause | Rule | Test | Gate |
|---|---|---|---|---|---|
| E-016 | A populated baseline value disappeared with no disposition | Completeness was checked in one direction only | 11 | R-03 | 6 |
| E-017 | A disposition claimed preservation while the destination stayed blank | The claim was recorded without being verified against the target | 11 | R-03 | 6 |
| E-018 | A conflict or low-confidence value collapsed into an ordinary blank or a silent fill | Binary populated/blank logic had no explicit conflict state | 12 | R-04 | 6 |
| E-019 | Rework restarted from a clean blank, losing correct existing content | Needing corrections was mistaken for needing a rebuild | 3 | R-13, R-14, R-21 | 1 |
| E-020 | A conditional section was populated, or marked not-applicable, without authority | Presence on the controlled form was mistaken for applicability | 11 | — | 5 |
| E-021 | A non-assigned element was evaluated as required | The full element set was assumed rather than read from the assignment | 1 (scope, Rule 3) | — | 1 |
| E-022 | Narrative, comments, or citations were silently truncated | A hidden length cap was treated as harmless formatting logic | 17 | — | 7 |
| E-023 | A narrowed or paginated result became a false inventory | A cap, filter, regex, or page boundary was treated as complete discovery | 18 | — | 3 |

## Output fidelity

| ID | Failure class | Root cause | Rule | Test | Gate |
|---|---|---|---|---|---|
| E-024 | A value present in the document XML rendered as an empty cell | It was written inside a placeholder or content control rather than as visible content | 20 | — | 10 |
| E-025 | A visibly selected control extracted as blank | Only the rendered layer was verified | 20 | R-15 | 12 |
| E-026 | A post-hoc formatting pass altered protected content | Formatting was treated as a step separable from the write | 19 | R-16 | 9 |
| E-027 | Structural damage escaped text-level checks | Visible text looked plausible while sections, headers, footers, or XML structure changed | 19 | R-16 | 9 |
| E-028 | Structurally meaningful but visually empty XML was deleted | Visual emptiness was treated as structural emptiness | 19 | — | 9 |
| E-029 | A filled deliverable was handed off without passing structural validation | The guard was advisory rather than blocking | 19 | — | 9 |
| E-030 | A draft-stage signature blank was reported as a final-release defect | Document status was not established before completion was judged | 3 | R-17 | 5 |

## Process and knowledge integrity

| ID | Failure class | Root cause | Rule | Test | Gate |
|---|---|---|---|---|---|
| E-031 | Shipping logic depended on scratch state from a prior run | Temporary artifacts became hidden runtime dependencies | 21 | — | 11 |
| E-032 | Concurrent runs collided in a shared output location | Run isolation was implicit rather than structural | 21 | — | 11 |
| E-033 | A fix was verified on a helper path while the shipping path was unchanged | The helper was mistaken for the deliverable | 23 | — | 12 |
| E-034 | A fix was lost to branch churn and re-implemented repeatedly | Nothing failed in its absence | 23 | — | 12 |
| E-035 | Documentation asserted behaviour the implementation did not have | The claim was never checked against a run | 23 | — | 13 |
| E-036 | A control passed its test while the documented interface bypassed it | The fixture was written against the implementation rather than the interface operators are told to use | 3 | R-14 | 13 |
| E-037 | A completeness or absence claim was published with nothing that could falsify it | The check was written to confirm the expected answer rather than to find the failure | 23 | R-18 | 13 |
| E-038 | A correction was reported as applied without confirming it landed | The report was written from intent rather than from verification | 23 | — | 13 |
| E-039 | Input parsing accepted a single separator, so a valid multi-value input read as one unknown token | The parser was specified against one input shape | 13 | — | 13 |
| E-040 | Two documents governed one subject with no declared precedence | Each reader followed a different one until the conflict surfaced at delivery | 22 | — | 13 |
| E-041 | A near-duplicate reference was used with no canonical marker | Copies diverge once one is edited, and nothing records which won | 22 | — | 13 |
| E-042 | A superseded artifact was selected because supersession was not marked | Currency was inferred from position, timestamp, or filename | 22 | — | 13 |
| E-043 | A snapshot enumerated the filesystem instead of the governed file list | What the repository already excluded was back in scope by default | 1 | R-18 | 13 |
| E-044 | Customer incident anatomy entered reusable knowledge | Historical detail was preserved where only generalized method belonged | 24 | R-18 | 13 |
| E-045 | Work expanded past the request; adjacent problems were absorbed | Each step was justified against the previous step rather than against the request | 25 | R-19 | 13 |

## Coverage

45 failure classes · 21 with an executable regression test · 24 governed by rule only.

The untested set is honest backlog, not an omission. Several classes turn on judgment —
whether documented coverage establishes implementation, whether a section is applicable —
and a check asserting otherwise would manufacture confidence rather than provide it.
Candidates worth building are listed in `04_REGRESSION_AND_RELEASE_GATES.md`.
