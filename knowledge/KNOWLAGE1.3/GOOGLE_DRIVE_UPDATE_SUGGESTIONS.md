# Google Drive Update Suggestions

Proposed changes to the Google Drive knowledge store. **Nothing here has been applied.**
This is a proposal register; it does not govern anything (see precedence in `README.md`).

Observations are as of 2026-08-31 against the account's `other/` (`1535QGr_rvw0PuPSdE0rEIX4o0TYhSZ1k`)
and `zip/` (`1uMk9A0LGsU3pvwYNjS3XzHduIZxztaAy`) folders. Drive file IDs are given so each
action is unambiguous.

---

## D-1 — Separate permanent reference from audit evidence (highest value)

**Observed.** One flat folder holds blank schemas and guidance beside live audit run
output: `B24_RL2_evidence_packet.json` (six copies), `B24_RL2_review.md` (six copies),
`b24_email_confirmation.{ocr,chunks,metadata}.json`, `b24_alias_noise.*`,
`b24_prose_noise.*`, `b24_staged_ocr_gold.*`, `B24_RL2_structure_guard_report.json`, and
in `zip/`: `B2 Site AAR Audit Part 1.zip` (`1jB6Auytm5x7AZp8B6tQn_-cxAwleNs5v`, 45 MB) and
`B2 Site Information.zip` (`1VySH4lhfZKEurG0FJ4cH6ViG1hrR_NTY`).

**Why it matters.** Anything reachable from a permanent knowledge folder can be pulled
into a later session as if it were reference material. That is the mechanism behind E-002,
and it is also how another facility's numbers end up in a form (E-010).

**Proposed.**

```text
B2-Knowledge/            permanent, safe to load in any session
  forms-blank/           current controlled blank B-2 and QAPE forms
  schemas/               field schemas, alias maps, activity schemas
  guidance/              requirements, work aids, writer/reviewer instructions
  method/                this pack
B2-Audits/               NOT permanent knowledge; per-audit, never loaded as reference
  <audit-id>/            evidence, run artifacts, completed forms
B2-Archive/              superseded material, retained for history only
```

Move every `*_evidence_packet.json`, `*_review.md`, `*.ocr.json`, `*.chunks.json`,
`*.metadata.json`, `*_structure_guard_report.json`, and both site ZIPs into `B2-Audits/`.

---

## D-2 — Establish one canonical copy per subject

**Observed.** Same-named documents with no marker saying which is current:

| Subject | Copies | File IDs |
|---|---:|---|
| `B2 Master Schema` | 4 | `1LdoQP8l6KD8hZypG4MR1gRvJIJpIrW6QaotQ7of3vMA`, `1GHSZyR8oAX5JNZIhmIqbw9R3ymVHzxEZL11MwTQBQvw`, `13GlWyDxtifDVFV9e3_2-Cc0QPN0flCJX9G13DI-fnmM`, `1MFdM4x_-gEcblHXrSJxsFlD36NeH5cmN3ioiodFBAGo` |
| `B-2 Master Schema` | 2 | `1fZeREz3-8G0QhoYcaADQhEeOBuBQdkiVAhlvM5AoiqE`, `1iZ4X_KyoFxkoRjiMB2rk-LxXkyREHDMPz1R9xOzo6JE` |
| `b2s_rollover_engine.py` | 4, at four different sizes | `1GqN3kyfsxmo9nbQIGTgx0xE_dJ-T3dFU` (15,081 B), `16rA6sq3leGNO7sJRssYf_fuq7H5MFhUa` (14,092 B), `1D7eEC8yX0obk3pAua8wSF14muzi6WItc` (13,881 B), `1dJGvN31Bmg2Tp1rtZbArwAqQBfgylFi_` (10,656 B) |
| `B24_RL2_evidence_packet.json` | 6, sizes 32 KB – 66 KB | `1t7PeqR2Fa9k5EVqj_Vm2kGdYhjmUCgQv`, `1Ve5KoqpQxiFQXoCmLt_MTMSAvs6eWnN5`, `1JViwYHtSliFLocAxGp1R0a-AeMkawxDP`, `1tO4ZFLYQs-4ehgmuXoILgvb-7UKSoeTj`, `1xD6grrFvtPX5iPs48D2hLrGBbW7RjZ41`, `1BfgDYKfgsHNTpQnPoJ4fTTztv-wVLVx_` |
| `B24_RL2_review.md` | 6 | `1dpdqLjoD4y4SdpiCsh4wuFPxIdUY2Xue`, `1kTmhc2zH0AKYgE9Vr8RFbkOGZyFvLgkk`, `116Sj6BhhnxbgqItwM4K3PKK0qwVwPC4U`, `1istvbza6gwoOgQCgT_9Banb3RFkZsFAq`, `1x9K-blS9wgiPTyEdbbadZkM9zv28wzYS`, `12zvn3Hai9YyK7bT5h8Nrv_A8IeoqW5U8` |

The four `b2s_rollover_engine.py` copies differ in size by up to 4.4 KB, so they are
different behavior, not different names for one thing.

**Why it matters.** Near-duplicates agree until one is edited. After that the next reader
picks by accident, which is E-040 — and E-041 is the same failure inside `SOP.zip`.

**Proposed.** For each set: pick one canonical file, rename it with a version and
effective date (`B-2_Master_Schema_v<N>_<YYYY-MM-DD>`), move the rest to `B2-Archive/`
with `SUPERSEDED_` prefixed to each title, and add a short `CANONICAL.md` in each folder
naming the current file and its ID. Confirm each duplicate's content before archiving —
where four copies differ in size, one of them may hold the only copy of something.

---

## D-3 — Remove build output from the knowledge store

**Observed.** `b2_filler.cpython-313.pyc` (`1-Gwjf5N_03wFEi0POr6l3875ucdfphxz`),
`b2_form_filler.cpython-313.pyc` (`1qIQ3ofd80xDchvUgA2yvipJnBPRWhl08`),
`b2s_rollover_engine.cpython-311.pyc` (`1b1Gpp7xIKvU0qzuKFdLfzy87IS-n2-w6`), and
`b2_automation.egg-info-PKG-INFO` (`1SRWyXwnFc_oUouIPrvg_oZAg-sVWOwDP`).

**Why it matters.** Bytecode cannot be read, reviewed, or diffed, and it pins a Python
version. It is unusable as knowledge and misleading as a backup.

**Proposed.** Delete, once the corresponding `.py` source is confirmed present.

---

## D-4 — Mark sibling-project source as source, not method

**Observed.** Engine and tool files sit beside schemas and guidance:
`b2s_enterprise_gui.py` (`1Xz0dE5ex9oILhcMSmcU4Xc4l8mBLb5oJ`), `b2s_field_aggregator.py`
(`1tVBSJRm4rGm2e_f3VGAJpm8haSQXxrJF`), `b2s_template_filler.py`
(`1jWslb4JrDkEZ3F5qojrnKO-7mHttti5X`), `b2_contract.py` (`1NBxYu1Ps7EqUUwlZdqobCriEn6gvKNqk`),
`universal_b2_parser.py` (`14ZTVj3zooEuf2J6aL9m_lnU29y4NhiPp`), `run_b2s_pipeline.py`
(`16WvCe4DuEaYZDyl7OFX7Lqbjbr9Y7_Ys`), `b2s_universal_engine.py`
(`16YaKPC5RtPN4QPRiIsluy-GaaPVF46Lh`, 88 bytes — likely a stub), plus
`RUN_B2S_ENGINE.bat`, `START_B2_FILLER.bat`, and the Colab notebooks
`Fill B2 Templates` (`1eZG1sLV4lch51TstuGN_5fd4_zescWsR`) and `QAPE Fill Runner`
(`1p04AAbqMPJq2pNl7Z3WBePDc34l8Qegq`).

**Why it matters.** Code read as method knowledge reintroduces the assumptions it happens
to encode — including hard-coded field lists and fixed geometry, which is A-01 and E-003.

**Proposed.** Move to `B2-Knowledge/reference-source/` with a folder note stating that
these are historical implementations for comparison only, and that the repository is
canonical for anything present in both (precedence rule 3 in `KNOWLEDGE_SOURCES_INDEX.md`).
Check the 88-byte `b2s_universal_engine.py`: if it is a stub, delete it rather than leave
it as a plausible-looking entry point.

---

## D-5 — Add a canonical activity/element index

**Observed.** `aar-m1002-b2s-activities.schema.json`
(`1WXFGHqrsJkWE5tlnx-scVvcR26FlFJoH`), `field_schema_b2s.json`
(`1qb8k59DvEKccGpW1Kq-o3gOEWS6S8Ls7`), `Advanced B24 Mapping`
(`1wG1-ZiTl1hIqX4Xuz7XqiEYUbwN7D7sP2W_zV7pqZ1g`), and `B24.json`
(`1MsvroCO3Y9Xj6HgiOxD1_6nnEt77mpXM`, 27 bytes) cover overlapping ground with no index.

**Why it matters.** Without a discovery index, each session re-derives what already exists,
which is E-047; and a 27-byte `B24.json` is indistinguishable from a real map until opened.

**Proposed.** One `FORM_INDEX.md` in `B2-Knowledge/schemas/`, one row per current form:
controlled title, activity code and variant, effective date, major section names, and
whether the form contains repeating rows or content controls.

**Constraint on this index.** It is for discovery only. It must not record table, row, or
cell coordinates — a stored cell map is E-003, and it is exactly what went stale in
`a72a16e` when template merges changed.

---

## D-6 — Keep the copy-paste table document out of the fill path

**Observed.** `B2 Audit Tables for Copy-Pasting`
(`1tGMHa664effaQ276SUsGBkyOspLSSHnF2CfM5CNQ-mE`, 37 KB).

**Why it matters.** A copy-paste source encourages transcription from a stale snapshot
instead of from the current controlled form (A-03), and pasted table content can carry
formatting into a controlled document outside a governed write (E-025).

**Proposed.** Keep it, in `B2-Archive/`, labelled a visual benchmark. Values are read from
the current controlled form and current evidence; never from this document.

---

## Suggested order

D-1 first — it is the only one that removes a live evidence-leakage path. Then D-2, which
makes every remaining reference unambiguous. D-3 and D-4 are cleanup. D-5 and D-6 are
improvements, safe to defer.
