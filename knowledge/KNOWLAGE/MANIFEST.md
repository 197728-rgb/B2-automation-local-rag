# Manifest

Consolidated AAR audit repeatability archive. Built 2026-08-31.

## Conflicts reconciled

Six resolved, one unresolved. Each is recorded once, here.

| # | Conflict | Resolution |
|---|---|---|
| 1 | Write authority: `AGENTS.md` and Cursor rules require exact approval maps; `SPEC-1-LOCAL-MVP.md` uses `machine_field_map.v1` with none | **RESOLVED** — an undeclared mode split, not a contradiction. Approval maps govern the review path, `machine_field_map.v1` the autonomous path; the structure guard blocks both. Stated once in AR-08 |
| 2 | Filled-output location: `<out>/filled/` vs a repo-wide `outputs/filled/` | **RESOLVED** — same rule at different `--out` values. The path-relative form is canonical |
| 3 | Review gating: one path emits review artifacts and can end `review_required`; the other emits neither | **RESOLVED** — mode-scoped. Terminal statuses do not transfer between modes |
| 4 | Filled-DOCX baseline: commit `7adc4f2` vs `c43e215` | **RESOLVED** — `c43e215` and later supersede. `7adc4f2` can leave values inside content controls (AAR-R016) |
| 5 | Registry selection inside `SOP.zip`: bare `field_registry.json` beside `SOP_00_*` | **RESOLVED** — the `SOP_00_` prefixed files are canonical per the archive's own supersession notice |
| 6 | Template naming: full controlled filenames beside short aliases (`B24_RL2.docx`) | **RESOLVED** — the full controlled filename carries identity and revision and is canonical; short names are code handles only, never a source of form identity |
| 7 | Google Drive near-duplicates: 6 copies of one evidence packet, 6 of one review file, 4 divergent `b2s_rollover_engine.py` (10,656–15,081 bytes), 4 `B2 Master Schema` docs, 2 `B-2 Master Schema` docs | **UNRESOLVED** — no canonical marker exists on any copy, and the engine copies differ enough to be different behaviour. Which is current cannot be determined without opening each; that is an owner decision, not one this archive can make. Tracked as AAR-R023 |

## Duplicate guidance removed

| Removed | Why |
|---|---|
| Personnel-row rule stated in three separate files (pack 1.2) | Now AR-06 alone; other files reference the ID |
| `DURABLE_FIXES.md` restating the rules in a second identifier scheme | Now holds fix implementation and proof artifact only |
| `ID_CROSSWALK.md` joining two of our own ID spaces | Deleted; collapsed from seven identifier schemes to three |
| `CLAUDE_REFERENCE_SUGGESTION.md` + `KNOWLEDGE_UPDATE_SUGGESTIONS.md` + overlapping engagement notes (pack 1.2) | Consolidated into `ENGAGEMENT_LESSONS_SUGGESTION.md` |
| `DO_NOT_REPEAT` as 27 restated prohibitions | Now a pointer index; enforcement lives in rules and tests |
| Startup instructions duplicated between README and agent notes | README maps contents; `FUTURE_AGENT_NOTES.md` owns startup |
| Gate definitions repeated in three files | Owned by `RELEASE_GATES.md` |

## Obsolete guidance removed

Dependency on a project router · dependency on prior KNOWLAGE archives · `TRAINER_QUALIFIED`
state · workstation paths and drive letters · generator-stage names · universal recursive
re-hashing before every mutation · `7adc4f2` as a fill reference.

## Repeatability controls added

| Control | Effect |
|---|---|
| 12 active rules, one authoritative home each | No rule stated twice; nothing to reconcile |
| Full chain per incident | Every recurring mistake carries root cause, lesson, fix, test, gate |
| 10 executable controls, both halves | Known-bad must fail, known-good must pass |
| Release gate with 5 counters | Non-zero blocks delivery; not a judgment call |
| Controlled vocabularies for level and method | Makes merged records mechanically detectable |
| `RULE ONLY` state | Coverage gaps stated rather than implied |
| Historical marking | Facility values confined to layer 4 and labelled |

## Files

| File | Bytes | SHA-256 |
|---|---:|---|
| `01_ACTIVE_RULES/ACTIVE_RULES.md` | 2668 | `953cb6b8bb238b31…` |
| `01_ACTIVE_RULES/RELEASE_GATES.md` | 2232 | `477260c7b83e962c…` |
| `01_ACTIVE_RULES/RUN_RECORD_SCHEMA.md` | 3034 | `fdd41136d137249d…` |
| `02_WORKING_METHOD/FIELD_MAPPING_AND_COMPLETENESS.md` | 4194 | `558841b6a62b4b4b…` |
| `02_WORKING_METHOD/WORKFLOW.md` | 4617 | `7266fbaf2673666b…` |
| `03_LESSONS/DO_NOT_REPEAT.md` | 2405 | `970b551a7ac0dd7a…` |
| `03_LESSONS/DURABLE_FIXES.md` | 2708 | `e331a62f9700b8f0…` |
| `03_LESSONS/ERROR_LEDGER.md` | 6747 | `c152f7ad0443ebbf…` |
| `03_LESSONS/FAILED_ASSUMPTIONS.md` | 2043 | `11f8b1d6f7724fce…` |
| `03_LESSONS/HARD_LESSONS.md` | 2227 | `413d0fc53b272d76…` |
| `03_LESSONS/REGRESSION_TESTS_SUGGESTION.md` | 3614 | `5ee95bdca545ed9d…` |
| `03_LESSONS/regression/expected_results/AAR-R001.json` | 76 | `d9a75b2d52de85d9…` |
| `03_LESSONS/regression/expected_results/AAR-R002.json` | 76 | `55ff16111add4a58…` |
| `03_LESSONS/regression/expected_results/AAR-R003.json` | 76 | `0f8059ce0289eab1…` |
| `03_LESSONS/regression/expected_results/AAR-R005.json` | 76 | `186cf3765dae6460…` |
| `03_LESSONS/regression/expected_results/AAR-R006.json` | 76 | `a89afe206b4820ef…` |
| `03_LESSONS/regression/expected_results/AAR-R007.json` | 76 | `75351e1aead4b3fd…` |
| `03_LESSONS/regression/expected_results/AAR-R008.json` | 76 | `c0763c6d302badc3…` |
| `03_LESSONS/regression/expected_results/AAR-R009.json` | 76 | `dccca152fb77f39d…` |
| `03_LESSONS/regression/expected_results/AAR-R010.json` | 76 | `3f5cc6fdd1a46103…` |
| `03_LESSONS/regression/expected_results/AAR-R026.json` | 76 | `ce560035a483ad4e…` |
| `03_LESSONS/regression/known_bad/AAR-R001_personnel_concatenated.json` | 219 | `ddb6706c6cbe054f…` |
| `03_LESSONS/regression/known_bad/AAR-R002_equipment_concatenated.json` | 291 | `51a456208d44177d…` |
| `03_LESSONS/regression/known_bad/AAR-R003_tcid_dropped.json` | 283 | `158601dce4d08fd2…` |
| `03_LESSONS/regression/known_bad/AAR-R005_control_machine_blank.json` | 158 | `aa980c384ff67f2e…` |
| `03_LESSONS/regression/known_bad/AAR-R006_structure_altered.json` | 267 | `59e74592a02140be…` |
| `03_LESSONS/regression/known_bad/AAR-R007_baseline_rebuilt.json` | 85 | `4d539f3b9336e5c3…` |
| `03_LESSONS/regression/known_bad/AAR-R008_field_mismatch.json` | 193 | `651b5930e08f495b…` |
| `03_LESSONS/regression/known_bad/AAR-R009_draft_signature_defect.json` | 180 | `d726a8df658652e8…` |
| `03_LESSONS/regression/known_bad/AAR-R010_type_coc_unaccounted.json` | 391 | `3c8bc1ca7b46f3fd…` |
| `03_LESSONS/regression/known_bad/AAR-R026_scope_expanded.json` | 172 | `0826c3ee56858928…` |
| `03_LESSONS/regression/known_good/AAR-R001_personnel_distinct.json` | 338 | `390231082d3cb2b6…` |
| `03_LESSONS/regression/known_good/AAR-R002_equipment_distinct.json` | 443 | `b2a57ace84db549f…` |
| `03_LESSONS/regression/known_good/AAR-R003_tcid_preserved.json` | 297 | `a93dc3de347f19f3…` |
| `03_LESSONS/regression/known_good/AAR-R005_control_readable.json` | 172 | `13dcdee5640f94cc…` |
| `03_LESSONS/regression/known_good/AAR-R006_structure_preserved.json` | 269 | `e22569431152097e…` |
| `03_LESSONS/regression/known_good/AAR-R007_baseline_maintained.json` | 89 | `59e04b464e00f633…` |
| `03_LESSONS/regression/known_good/AAR-R008_field_match.json` | 205 | `dd603cbb465788e5…` |
| `03_LESSONS/regression/known_good/AAR-R009_released_signature_defect.json` | 184 | `9a99124e4023f08a…` |
| `03_LESSONS/regression/known_good/AAR-R010_type_coc_preserved.json` | 449 | `e2412759e43b22fb…` |
| `03_LESSONS/regression/known_good/AAR-R026_scope_held.json` | 160 | `0161e35be6a0a836…` |
| `03_LESSONS/regression/regression_manifest.json` | 3225 | `0193ebb2155284b7…` |
| `03_LESSONS/regression/release_gate.py` | 4978 | `7ee7499eabd680d0…` |
| `03_LESSONS/regression/run_regression.py` | 3132 | `057cc1776ff5afcc…` |
| `03_LESSONS/regression/validators.py` | 11603 | `d23e3aa67e5ac435…` |
| `04_FORENSIC_ARCHIVE/README.md` | 673 | `dfc15f88cf80e1ab…` |
| `04_FORENSIC_ARCHIVE/examples/MERGED_RECORD_EXAMPLES.md` | 1311 | `e193fa77db6dc7e2…` |
| `04_FORENSIC_ARCHIVE/incidents/AAR-R025.md` | 3152 | `0e7c584ee323eabd…` |
| `04_FORENSIC_ARCHIVE/incidents/AAR-R026.md` | 2505 | `6247c0b95d2b15e1…` |
| `ENGAGEMENT_LESSONS_SUGGESTION.md` | 2420 | `e7006fa90ddd34f0…` |
| `FUTURE_AGENT_NOTES.md` | 2143 | `48ff164d1ff651c5…` |
| `README.md` | 2727 | `4b0eedece2203cc8…` |
| `SESSION_SUMMARY.md` | 4030 | `7af101d08eaefc11…` |

**53 files**, 83,993 bytes, excluding this manifest.
