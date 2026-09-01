# Knowledge Archive Gap Analysis — KNOWLAGE1.6 vs `src/b2_automation`

**Analysis date:** 2026-09-01
**Reference method package:** `KNOWLAGE1.6`, revised edition (27 files; archive integrity and 41/41 executable controls independently verified — see §9)
**Code under analysis:** `src/b2_automation` @ `ebd8ae8` (8,549 lines, 33 modules; 136 tests pass, 2 skipped)

This document maps the canonical audit method — 17 active rules (`R-*`), 19 release gates (`G-*`),
the seven-state disposition vocabulary, and the 41 executable controls (`T-43`–`T-83`) — against the
controls the code actually enforces today. It is a read-only assessment. No pipeline behavior was changed.

Per `R-13` / `G-16` this document is customer-neutral: failure classes are cited by ID, never by
facility, personnel, or audit identity.

---

## 1. Executive summary

The codebase is strongest exactly where the method is hardest to retrofit, and absent exactly where
the method does its blocking.

**Write authorization (`G-08`) and protected structure (`G-11`) are genuinely implemented** — exact
per-form/version approval maps, duplicate-coordinate and duplicate-physical-cell rejection, an OOXML
structure guard that discards output on failure, and per-field provenance in `field_traceability.json`.
That is a real, working separation of retrieval from write authority (`R-17`), and it is more than most
of the reference runs demonstrated.

**What is missing is the entire disposition and completeness layer.** The code has no generation mode,
no baseline, no reconciliation ledger, no source-exhaustion proof, no supported-blank counter, no
value-level readback, no page rendering, and no QAPE scope at all. Its terminal state is `success`,
which `G-18` forbids.

**One path bypasses even the implemented controls.** The completed-reference handoff copies a prior
form verbatim as the current deliverable on a filename substring match, skipping approval maps and
passing a structure guard that compares the file to its own copy (D-4). Fixing that is the single
highest-value change in this document.

### Gate scoreboard

| Status | Count | Gates |
|---|---:|---|
| Implemented | 2 | `G-08`, `G-11` |
| Partial | 7 | `G-02`, `G-04`, `G-07`, `G-14`, `G-15`, `G-16`, `G-17` |
| Absent | 9 | `G-01`, `G-03`, `G-05`, `G-06`, `G-09`, `G-10`, `G-12`, `G-13`, `G-19` |
| Actively violated | 1 | `G-18` |

### Executable control coverage

| Suite | Controls | Represented in `tests/` |
|---|---:|---:|
| `T-43`–`T-83` (archive) | 41 | **0** |
| Repo pytest suite | 136 | n/a — tests current code behavior, not the defect catalog |

The repo's 136 tests are healthy and CI-wired (`.github/workflows/ci.yml`, push + PR, Python 3.11/3.12).
They are not the same thing as the archive's defect catalog: none of the 35 known-bad fixtures exist here,
so no `T-*` class is proven to fail-closed on the production path.

### Vocabulary mismatch

The method's seven dispositions and the code's six decision states are disjoint in meaning, not merely
in spelling. Nothing in `src/` emits `PRESERVE_VERIFIED`, `UPDATE_VERIFIED`, `WRITE_VERIFIED`,
`CLEAR_NO_CURRENT_SUPPORT`, `NOT_APPLICABLE_VERIFIED`, `WITHHELD_CONFLICT`, or `UNRESOLVED`
(grep across `src/` and `tests/`: zero occurrences).

---

## 2. Four demonstrated defects

Each was reproduced against the installed package, not inferred from reading.

### D-1 — A current-evidence conflict is silently resolved into a written value

`decide_fields_for_local_packet` never emits `CONFLICT`. Two contradicting candidates for one required
identity field produce a `FILL`:

```text
STATE          : FILL
SELECTED VALUE : AAAX 000111          <- one of two contradicting candidates
REASON         : auto-filled best candidate; conflicting extracted values require reviewer verification
SUMMARY        : {'counts_by_state': {'FILL': 1}, 'human_review_field_ids': ['car_number']}
REVIEW LISTS   : {'missing_fields': [], 'conflicts': [], ...}
```

The value is written to the DOCX; the run's `conflicts` list is empty; `decision_summary` reports only
`FILL: 1`. The single surviving trace is `human_review_field_ids`, derived by substring-matching the word
"conflict" in a free-text reason string (`decision_engine.py:20-27`).

Violates `R-08`, `G-07`; fails `T-18`, `T-46`.
Source: `decision_engine.py:118-120`.

### D-2 — Four of six decision states are unreachable on the production path

`DecisionState` defines `REVIEW_REQUIRED`, `MISSING`, `CONFLICT`, `LOW_CONFIDENCE`
(`cell_evidence.py:9-15`), and `_derive_review_lists` (`local_extraction.py:1218-1249`) reads all four to
populate `missing_fields`, `conflicts`, `review_required_fields`, and `low_confidence_fields` in every
form packet. But the only producer feeding it — `decide_fields_for_local_packet` — emits **only `FILL` and
`BLANK`**. Those four review lists are therefore structurally always empty in a real run, while appearing
in `local_rag_review.json` as if they were evaluated.

`decide_cell` (`cell_evidence.py:96`) *can* return `CONFLICT`, but its sole production caller passes
`conflict_detected=str(value).startswith(REVIEW_REQUIRED_TEXT)` (`ooxml_writer.py:304`) — true only when
the value is already a review marker. Conflict is not detected there either.

This is a dead-control path: the reporting surface implies review coverage the engine cannot produce.
Fails `T-33` (balanced counts, wrong field).

### D-3 — Evidence in a subdirectory is dropped from the corpus without a warning

```text
FILES ON DISK IN INBOX TREE:      FILES STAGED FOR EXTRACTION:
    subfolder/nested_evidence.txt     toplevel.txt
    toplevel.txt
```

`_stage_inbox_evidence` iterates one level and skips non-files (`inbox_pipeline.py:141-147`). Zips are
recursed; directories are not. The skipped file never appears in `inputs[]`, no warning is emitted, and
the run can still finish `status: success`.

This is documented behavior in `AGENTS.md` ("put files at the **top level** of the inbox folder, or add
`.zip` archives"), so the defect is not the non-recursion — it is that the corpus boundary is **silent**.
A completion status is issued over an unmeasured evidence universe.

Violates `R-03`, `G-03`; fails `T-69`, `T-74`.

### D-4 — A prior completed form is shipped verbatim as the current deliverable, on a filename match

**Most severe of the four.** When an inbox `.docx` filename contains a reference marker plus a form
token, the pipeline copies that file byte-for-byte to `<form>_filled.docx` and reports it as produced
(`inbox_pipeline.py:1457-1479`). Qualification is filename substring matching only
(`_completed_reference_form_from_name`, `inbox_pipeline.py:398-412`) — the file's *content* is never
examined:

```text
form claimed, from filename alone : B89
structure guard pass              : True   <- source compared to its own copy
non-zero structural deltas        : none
deliverable is byte-identical     : True
dispositions recorded             : patched_fields=['completed_reference_docx'], manual_fields=[]
```

Three separate controls are bypassed at once:

- **Approval maps are not consulted.** The `G-08` write-authorization layer — the codebase's strongest
  control — is skipped entirely for that form.
- **The structure guard is vacuous.** `before_counts` and `after_counts` are computed from the source and
  from a copy of that same source, so `pass: True` is guaranteed and proves nothing.
- **No dispositions exist.** `patched_fields` is the literal placeholder `["completed_reference_docx"]`;
  `manual_fields` is empty, so the run reports `status: success` for a form that received zero
  current-evidence reconciliation.

A filename is used as authority for a current deliverable, which `R-03` prohibits by name
(*"a … filename … may assist discovery but cannot independently authorize a current value"*), and
substring matching is used as identity, which `R-05` prohibits.

Violates `R-03`, `R-05`, `R-07`, `R-08`, `G-06`, `G-08`; fails `T-23`, `T-41`, `T-51`.
This is `CF-01` (no-op completion presented as work) compounded with `CF-04` (prior artifact becomes
current authority) — the two failure modes the reference comparison ranked as lowest production value.

---

## 3. Gate-by-gate mapping

| Gate | Status | What exists | What is missing |
|---|---|---|---|
| `G-01` Job contract | **Absent** | `run_manifest.json` records `mode: "local_rag_extraction"` (a pipeline mode), template, evidence root, run dir | No generation mode. `NEW_FILL` / `ROLLOVER` / `MAINTENANCE` / `REBUILD` appear nowhere in `src/`. No baseline declaration, no seed-disqualification reason |
| `G-02` Source protection | **Partial** | `inputs[].sha256` per evidence file; `current_doc_index` maps source → digest; templates are read-only by construction (writes land in `outputs/filled/`) | Hash captured once at extraction. No post-run re-hash, no pre/post equality assertion, no template/master hash record |
| `G-03` Workspace index and exhaustion | **Absent** | Files enumerated and extracted; every input stamped `status: "extracted"` (`inbox_pipeline.py:1690`) | `"extracted"` is inventory, not review. No role classification, no terminal substantive-review disposition, no `indexed == reviewed` equality, no unevaluated list. Corpus boundary silent (see D-3) |
| `G-04` Current-form discovery | **Partial** | `discover.py` + `scripts/discover_template_tables.py`; `schemas/maps/*.json` field registry; `table_fingerprint.py` header-drift detection | Registry is coordinate-keyed and pre-baked, not re-derived per run from the current controlled form. No conditional/alternative-path parsing |
| `G-05` Identity resolution | **Absent** | Field-level `field_id` keys; label-token compatibility heuristics (`_label_value_is_compatible`, `_best_value_for_label`) | No composite identity. No `record_type` / `record_key` / `occurrence_key`; no person-method-scope tuple; no equipment-class + unique-ID tuple. Row binding is label/value scanning |
| `G-06` Baseline reconciliation | **Absent** | — | No baseline concept at all. Each run fills a clean template; `_clear_scoped_filled_docx` wipes prior output. No reconciliation ledger |
| `G-07` Two-way completeness | **Partial** | `field_traceability.json` is a real per-field provenance ledger: suggested vs selected value, decision state, source file/page, chunk id + hash, excerpt, `approval_map_target`, `authorized_for_write`, `filled`, `fill_block_reason` | No supported-blank counter, no unsupported-populated counter, no blocking dispositions (see D-1), no absence-search record, no `CLEAR_NO_CURRENT_SUPPORT` |
| `G-08` Write authorization | **Implemented** | Exact per-form/version approval maps required; `form_id` and `form_version` match enforced; duplicate-coordinate and duplicate-physical-cell rejection; only manifest cells patched; nearest/generic maps refused | Value-side authority is weaker than location-side authority (D-1). **The completed-reference passthrough bypasses this gate entirely** (D-4) |
| `G-09` Semantic preservation | **Absent** | `verify_safe_text_patch_only` compares structure counts and expected text-node delta | No value-level readback. Zero hits for readback/reopen/verify-written across `src/`. Intended value is never compared to the written value. No `required_fact_set` derivation |
| `G-10` Machine controls | **Absent** | SDT content is unwrapped for visibility (`ooxml_writer.py:442-465`) | No control-state readback. Checkbox/dropdown/date machine state never compared to visible text. `count_docx_structure` does not count `w:sdt` |
| `G-11` Protected structure | **Implemented** | `count_docx_structure` + `build_structure_guard` over tables, rows, cells, `gridSpan`, `vMerge`, relationships, styles, headers, footers, plus expected text-node delta; failure discards the output (`discarded_structure_guard_failed`); `cell_boundary_validation`; fingerprint drift | `w:sdt`, `w:sectPr`, `w:fldChar` uncounted; no document-tail / orphan-spacer check (`T-29`); **guard is vacuous on the completed-reference path** (D-4) |
| `G-12` Rendered pages | **Absent** | `visual_export_checks` emits `pdf_export_hint`: *"Manual: export PDF in Acrobat/Word and confirm cell alignment visually"* | No rendering, no page images, no per-page findings. `T-40` (clipped middle page) uncatchable |
| `G-13` Cross-document consistency | **Absent** | Run-level required fields propagate across forms (`_run_level_required_suggestions`, `_merge_label_evidence`) | Propagation is not reconciliation. No cross-document conflict detection, no scope-leakage check |
| `G-14` Cold-start repeatability | **Partial (de facto)** | Deterministic by design: local TF-IDF/keyword retrieval, `_deterministic_confidence`, no LLM required; CI runs cold on two Python versions | No explicit gate asserting that a cold start reproduces the same semantic decisions; no dependency-completeness check (`T-36`) |
| `G-15` Regression suite | **Partial** | 136 tests, CI on push and PR, compileall + CLI smoke | None of `T-43`–`T-83` represented. `release_gate.py` is not invoked by any production entry point — the archive's own warning applies: *"Passing an isolated test is insufficient when the production entry point does not invoke the gate"* |
| `G-16` Knowledge firewall | **Partial** | `.gitignore` excludes `inputs/`, `outputs/`, `.env`, `.venv/` | Convention only. No automated scan for customer identifiers in committed artifacts (`T-38`, `T-60`) |
| `G-17` Package identity | **Partial** | `run_manifest.json` lists outputs; `_clear_scoped_filled_docx` prevents stale filled duplicates | No integrity hash over the handoff package; no canonical-package selection; no duplicate-package reporting |
| `G-18` Acceptance boundary | **Violated** | — | Inbox path terminates at `success` / `review_required` (`inbox_pipeline.py:1672`). Autonomous path terminates at `completed` / `completed_with_warnings` / `failed_with_fallback` (`autonomous_pipeline.py:154`). `validation_gate.py:39` states: *"Always returns a final answer — never blocks for human review."* `AGENTS.md` makes `Status: success` the handoff criterion. `READY_FOR_HUMAN_REVIEW` / `HUMAN_PENDING` appear nowhere |
| `G-19` QA Program Manual source | **Absent (whole scope)** | QAM text is opportunistically mined for one Cover-page procedure table | **Zero QAPE support in the codebase** — case-insensitive grep for `qape` across `src/`: no hits. No required-source lock, no QAM hash/revision record, no Manual/Compliance predicates |

---

## 4. Rules delta — where code and method disagree by design

Most rule gaps follow from the gate gaps above. Three deserve separate attention.

### 4.1 `R-05` (no position-based field authority) vs the approval-map architecture — **decision required**

`R-05` forbids page/table/row/column/cell index as *durable* identity and requires resolution through
`controlled form/version → section → exact field label → semantic meaning → entity identity → control owner`,
with the physical target derived per run. `T-01`, `T-52`, and `T-62` enforce this.

The repo does the opposite on purpose. `approval_maps.py:3`: *"Exact coordinate authorization only:
manifest cells must match approval `fields` entry `table_index` / `row` / `col` per `field_id`."*
`AGENTS.md` mandates it: *"Do not use generic, similar, nearest, or latest approval maps"*, *"Do not
hard-code guessed DOCX table indexes."*

This is a real architectural conflict, not an oversight, and the repo's position is defensible. The
mitigations are substantive: maps are pinned to `form_version`, header fingerprints are checked for
drift, and duplicate coordinates and duplicate physical cells are rejected at load. The method's own
failure register also records the opposite failure mode — `CF-07`, where absence of an exact map became
a blanket refusal to write.

The two positions can be reconciled without abandoning either: keep coordinates as the *authorization*
mechanism, and add a semantic key alongside each `field_id` that must independently resolve to the same
physical cell on the current template before the write is authorized. Coordinates then stop being the
sole identity and become a checkable second opinion. **This is the one item that needs an owner decision
before implementation.**

### 4.2 `R-10` (formatting contract) — not implemented

The method specifies B-2 entered values as Arial 10 centered, QAPE narrative and Objective Evidence as
Arial 9 left-aligned, selections centered. `ooxml_writer.py` contains no font, size, or alignment
application — values are patched into existing runs and inherit whatever properties are already there.
`T-31` (writer creates a new run in an empty approved cell → approved run properties applied) fails.

### 4.3 `R-14` (candidate admissibility) — the strongest partial

Genuinely present and worth preserving: `_label_value_is_compatible`, `_value_looks_like_date`,
`_value_looks_like_design_spec`, `_sanitize_map_values_against_labels`, plus the targeted hardening in
git history (B89 equipment OCR junk blocking, strict TCO permission-date handling, PITP fallback).
This is a working `T-47` analogue. What it lacks is the recorded fallback/degraded-extraction path that
`R-14` also requires.

---

## 5. Disposition vocabulary

| Method disposition | Meaning | Code equivalent |
|---|---|---|
| `PRESERVE_VERIFIED` | Baseline value confirmed by current evidence | none — no baseline |
| `UPDATE_VERIFIED` | Baseline value changed on current evidence | none — no baseline |
| `WRITE_VERIFIED` | New target populated with current support | `FILL` (no support proof) |
| `CLEAR_NO_CURRENT_SUPPORT` | Cleared after proven source exhaustion | none |
| `NOT_APPLICABLE_VERIFIED` | Form alternative proven inapplicable | none |
| `WITHHELD_CONFLICT` | Current sources disagree — **blocking** | `CONFLICT` defined, never emitted (D-1, D-2) |
| `UNRESOLVED` | Search incomplete or identity ambiguous — **blocking** | `MISSING` defined, never emitted (D-2) |

Code-side states with no method equivalent: `BLANK` (conflates "not applicable", "no support", and "not
evaluated" — the method requires these to be distinct), `LOW_CONFIDENCE` and `REVIEW_REQUIRED` (defined,
never emitted).

The critical asymmetry: **the method's two blocking dispositions are precisely the two the code cannot
produce.** Nothing in the current pipeline can stop a handoff.

---

## 6. Exposure to the cross-agent failure register

Failure classes from the six-run comparison, scored against this codebase:

| Class | Exposure | Basis |
|---|---|---|
| `CF-01` No-op completion | **High** | D-4 — a prior form is shipped byte-identical as the deliverable, past a self-comparing guard, with `status: success` |
| `CF-02` Refusal bias | **Low** | The pipeline is deliberately biased to produce output (`decision_engine` docstring: *"do not block an entire DOCX because a few fields need human review"*) |
| `CF-03` Evidence universe under-classified | **High** | D-3; no role classification; `"extracted"` treated as reviewed |
| `CF-04` Prior artifact as current authority | **High** | D-4 — a completed reference DOCX becomes the current deliverable on a filename match, with no reconciliation and no dispositions |
| `CF-05` Semantic source-to-field misbinding | **High** | Label-token matching is the binding mechanism; no destination-predicate / source-purpose match. This was the failure implicated in four of six reference runs |
| `CF-06` QAPE topic match as predicate proof | **N/A** | No QAPE scope |
| `CF-07` Physical-target over-dependence | **Accepted by design** | See §4.1 |
| `CF-08` Structural verification mistaken for semantic | **High** | `G-11` strong, `G-09` absent — the exact shape of this failure: a perfectly-structured wrong value passes every implemented check |
| `CF-09` Incomplete work hidden behind "correctly blank" | **High** | `BLANK` requires no support proof; no supported-blank counter |
| `CF-10` Meta-work displaces audit work | **N/A** | Agent-behavior rule, not a code control |
| `CF-11` Recency as validity proxy | **Low** | Date handling is format-normalization, not staleness judgment |
| `CF-12` Gate circularity | **High** | Every check runs on inputs the pipeline itself produced; nothing independently validates corpus completeness. D-4 is the extreme case: a guard that compares a file to its own copy |

---

## 7. Prioritized remediation

Ordered by blocking power per unit of work. Items 2–5 are additive and do not disturb the working
write-authorization and structure-guard layers; item 1 removes a path that circumvents them.

1. **Close the completed-reference passthrough (D-4).** Either require the reference DOCX to go through
   the same approval-map write path and disposition ledger as every other form, or gate it behind an
   explicit operator flag that stamps the output as an unreconciled carry-forward and forces
   `review_required`. At minimum, stop comparing the file to its own copy and stop reporting `success`
   for a form with zero dispositions. Highest severity, and self-contained.
2. **Make the corpus boundary explicit (`G-03`, D-3).** Record skipped directories and unsupported
   extensions in `run_manifest.json`; emit `indexed` vs `reviewed` counts; refuse `success` while
   `unevaluated > 0`. Smallest change with the largest honesty gain.
3. **Restore the blocking dispositions (`G-07`, D-1, D-2).** Emit `CONFLICT` from
   `decide_fields_for_local_packet` when candidate values disagree, stop writing the winner, and either
   delete the four unreachable review lists or wire them. Add supported-blank and unsupported-populated
   counters.
4. **Correct the terminal state (`G-18`).** Replace `success` with `READY_FOR_HUMAN_REVIEW` +
   `FINAL_ACCEPTANCE = HUMAN_PENDING`, and update the `AGENTS.md` handoff criterion to match. Mechanical
   change; removes the one active violation.
5. **Add value-level readback (`G-09`).** After patching, reopen the DOCX and assert each intended value
   is present at its authorized cell. Closes `T-33` and `CF-08`, and reuses the approval-map machinery
   already in place.
6. **Import the executable defect catalog (`G-15`).** Port `T-43`–`T-83` fixtures into `tests/` so each
   known-bad case fails on the production path, not in a helper.
7. **Decide the `R-05` question (§4.1)** before building semantic identity (`G-05`, `G-06`), page
   rendering (`G-12`), or QAPE scope (`G-19`) — those are project-sized and depend on the answer.

---

## 8. Revised-edition delta

The revised `KNOWLAGE1.6` folds a six-agent failure comparison into the normative layer. Every change
tightens a control this codebase already fails; none relaxes one.

| Rule / Gate | Added in the revision | Effect here |
|---|---|---|
| `R-03` / `G-03` | Reviewed role/applicability classification with rationale; the evidence universe may not be narrowed by an unreviewed classification or an unexplained exclusion | Widens D-3, and names §9's extension-based exclusion |
| `R-08` / `G-05` | `destination predicate -> source record purpose -> exact identity -> current authority`; QAPE topic or citation similarity is not predicate satisfaction | Names precisely the binding the code does not perform |
| `R-12` / `G-07` | Required report and destination identity accounting; **"Returning expected filenames or byte-identical inputs is not proof of work; a zero-change result requires a verified field-by-field justification"** | Makes **D-4 an explicit rule violation** rather than an inferred one |
| `R-14` | "A date is not stale merely because it is old" | **Not violated here** — the code has no age-based date rejection |
| `R-16` | "Record the execution order in the run log" | No execution-order record is emitted |

`G-05` is renamed *Identity and semantic-purpose resolution*; `G-07` becomes *Two-way and scope
completeness*. Two method sections are new (Semantic authority binding, Scope ledger), plus six
executable controls `T-78`-`T-83` (`E-050`-`E-054` -> `I-030`-`I-034`).

Verified independently rather than by trusting the archive's own verifier, since self-validation is the
`CF-12` gate-circularity trap the archive itself warns about:

- all 26 manifest SHA-256 digests and byte sizes recomputed: 26/26 match, no unlisted or absent files;
- `ALL_CHECKS` parsed against `def check_*`: 30 defined, 30 wired, no orphan and no ghost. The prior
  edition shipped `check_rollover_baseline` defined but omitted from `ALL_CHECKS` — silently dead on
  the production path. That class of defect is not present in this edition;
- `fixtures.json` parsed directly: 41/41 controls carry both a `known_bad` and a `known_good` half.

---

## 9. Live validation against a real workspace

The pipeline was run end to end against a real audit workspace (14 files: target forms, a controlled QA
Program Manual, facility worksheets, a scope letter, and a prior audit package). Recorded
customer-neutrally per `R-13` / `G-16`.

**Every defect in §2 reproduced on real data.** All four review lists were empty across all five forms
(`missing=0, conflicts=0, review_required=0, low_confidence=0`) across 26 decisions, every one `FILL` —
D-2 exactly as predicted. A genuine two-source conflict existed in the evidence and could not surface.

Three findings were **not** predicted by the static analysis.

### L-1 — The pipeline cannot serve an audit outside its five hard-coded forms

`ALLOWED_REVIEW_FORMS = DEFAULT_REVIEW_FORMS = ("B24_RL2", "B81", "B89", "B90", "Cover_Page")`
(`local_extraction.py:28-29`). The workspace's audit scope was two different activity codes. The run
produced five filled DOCX for forms outside that scope and **zero** for the two inside it. Templates for
the in-scope codes exist in `templates/`; no approval maps do, so there is no write authority for them.
This is a `G-07` scope-completeness failure of the strongest kind: the required report identities cannot
be produced at all.

### L-2 — Silent exclusion by file extension, independent of D-3

D-3 covers subdirectories. The live run exposed a second narrowing path: the workspace's scope-defining
document was an image, and `LOCAL_EVIDENCE_EXTENSIONS` (`local_extraction.py:30`) contains no image
type. It was dropped with no record — `skipped_review_required: []`, and `run_manifest.json` carries no
key naming skipped, excluded, or unsupported inputs. 14 files in, 13 in the corpus, and nothing in the
artifacts says which one is missing or why.

Directory nesting compounds it. Pointed at the workspace as delivered, the pipeline found **zero of 14**
files. That case errors out only because the corpus is *entirely* empty; a partially-matching layout
yields a truncated corpus and a `success`-eligible run.

### L-3 — A prior-year artifact authorized a current value

A Cover-page field was written from a document in the prior audit package at confidence 0.87 — a prior
audit package became current authority with no reconciliation step (`R-03`, `CF-04`). Separately, the
customer's own working form was present in the inbox and so was ingested *as evidence*, letting
administrative values be label-matched out of it into the output template. Some were independently
corroborated by other evidence; at least one was not.

`L-1` and `L-2` fall under gates already scored Absent in §3, but they raise the practical severity: a
run against a real workspace can silently narrow its own evidence universe *and* deliver forms for the
wrong audit scope, while reporting a status an operator reads as normal.

---

## 10. Scope note

This analysis covers method-to-code control coverage. It does not assess the correctness of any audit
output, and no gate result here substitutes for current-evidence reconciliation, document readback,
every-page inspection, or human acceptance.
