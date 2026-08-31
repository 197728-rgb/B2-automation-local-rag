# Knowledge Sources Index

Provenance for everything in this pack: what was read, what was copied, what was only
referenced, and how conflicts between sources were resolved.

This file owns **where knowledge came from and which source wins**. It states no method.

---

## 1. Sources ingested

| Code | Source | Reached how | In this archive |
|---|---|---|---|
| `REPO` | `197728-rgb/B2-automation-local-rag` working tree, branch `claude/knowlage-archive-creation-zzl9ay` | Local checkout | Copied to `source/repo/` (exclusions in §2) |
| `REPO` | Git history: 139 commits, branch and tag state | `git log` | Copied to `source/git-history/` |
| `REPO` | Nested `b2-sentinel/` governed cognitive layer, incl. `GOVERNANCE.md` and 2026 activity schemas | Local checkout | Inside `source/repo/b2-sentinel/` |
| `DOCS` | `README.md`, `AGENTS.md`, `VERIFICATION.md`, `.cursor/rules/local-automation.mdc`, `docs/*.md` | Local checkout | Inside `source/repo/` |
| `SKILL` | B2S Enterprise Compliance Platform skill guide — platform map, SOP 0–10, activity codes, error catalogue, Best Tools Bundle | Session skill store | Copied to `memory/b2s-platform-SKILL.md` |
| `DRIVE` | Google Drive knowledge store, `other/` and `zip/` folders | Drive search and read | Indexed to `memory/drive/DRIVE_KNOWLEDGE_INDEX.md`; one document copied (§2) |
| `PRIOR` | `CLAUDE_KNOWLEDGE_REPEATABILITY_FIXED` (version 1.2), supplied as the worked example | Uploaded archive | **Not copied.** Absorbed and superseded; delta in `CHANGELOG_FROM_KNOWLAGE_1_2.md` |
| `SESSION` | This build session | — | `SESSION_SUMMARY.md` |

## 2. Copy versus reference

**Copied in full:** project source; git history as text; the B2S platform skill guide; the
B-2 master field schema from Drive (`memory/drive/B-2_Master_Schema.json`) — a blank data
dictionary of field names and label aliases, carrying no facility data.

**Referenced by ID only, not copied:**

- Drive engine and tool sources (`b2s_rollover_engine.py` and its variants,
  `b2s_field_aggregator.py`, `b2s_template_filler.py`, `b2s_enterprise_gui.py`, Colab
  notebooks, PowerShell and batch launchers). These are sibling-project source, indexed in
  `memory/drive/DRIVE_KNOWLEDGE_INDEX.md` with their file IDs.
- Compiled bytecode (`*.pyc`) in Drive. Build output, not knowledge.

**Deliberately excluded, and why:**

- All audit run artifacts in Drive — evidence packets, review markdown, `*.ocr.json`,
  `*.chunks.json`, `*.metadata.json`, structure-guard reports, and the site evidence
  archives. These are facility evidence and are barred from permanent knowledge by the
  boundary in `README.md`.
- `.git/`, `node_modules/`, `__pycache__/`, caches, and pytest temp roots from the repo.
  Build and dependency state, reproducible from source.
- `inbox/` and `outputs/` — gitignored at source; they hold live evidence and run output.

**Confirmed absent from this archive:** no facility name, personnel identifier, car mark,
equipment ID, calibration date, finding, or completed form. The DOCX files under
`source/repo/templates/` are blank controlled forms, which the boundary permits.

## 3. Precedence between sources

Beyond the pack-level precedence in `README.md`, these source-specific rules apply:

1. A **current controlled form supplied with the live audit** outranks every schema, map,
   alias list, and template snapshot in this archive, without exception.
2. Between `REPO` and `SKILL`: they describe **two different products** —
   `B2-automation-local-rag` (local-first RAG and OOXML patching) and the B2S Enterprise
   Compliance Platform (GUI, SOP 0–10, per-run directories). Neither governs the other.
   Method knowledge in this pack is drawn from both and governs both.
3. Between `REPO` and `DRIVE`: the repository is canonical for anything that exists in
   both. Drive copies are snapshots and may be behind.
4. Between this pack and `PRIOR` (1.2): this pack supersedes it entirely. Both should not
   be loaded together.

## 4. Reconciled source conflicts

Real disagreements found between sources, and their resolution. Each is recorded here once
so that no downstream file has to carry the ambiguity.

| # | The disagreement | Resolution |
|---|---|---|
| C-1 | Write authority: `AGENTS.md` and the Cursor rules state that only exact approval maps may authorize a DOCX write; `docs/SPEC-1-LOCAL-MVP.md` states that autonomous runs use `machine_field_map.v1` with `approval_map=None` | Not a contradiction but an undeclared **mode split**. Exact approval maps govern the `b2 inbox` path; `machine_field_map.v1` governs the `b2 run-autonomous` path. The structure guard is a hard blocker on both. Neither mode may borrow the other's authority. This is the case that produced E-039 and F-29 |
| C-2 | Filled-output location: `README.md` says filled outputs live under `<out>/filled/` and warns against a repo-wide `outputs/filled/`; `AGENTS.md` names `outputs\filled\` as the canonical handoff folder | Both describe the same rule at different `--out` values. The location is always `<out>/filled/`; `AGENTS.md` is describing the specific case `--out .\outputs`. The path-relative form is canonical |
| C-3 | Review gating: the local inbox path emits `review.json` / `review.md` and can end `review_required`; the autonomous path emits neither and never ends `review_required` | Mode-scoped, per C-1. Terminal statuses do not transfer between modes |
| C-4 | Baseline commit: `7adc4f2` was once treated as the good filled-DOCX reference, while `c43e215` is the stated minimum baseline | `c43e215` and later supersede it. `7adc4f2` can leave values inside placeholder or content controls, which is E-023 |
| C-5 | Registry selection inside `SOP.zip`: a bare `field_registry.json` sits beside `SOP_00_*` files | The `SOP_00_` prefixed files are canonical; the bare file is superseded, per the archive's own supersession notice. This is E-041 |
| C-6 | Six copies of `B24_RL2_evidence_packet.json` and six of `B24_RL2_review.md` in Drive, at six different sizes; four divergent `b2s_rollover_engine.py` copies; four `B2 Master Schema` documents plus two `B-2 Master Schema` documents | No canonical marker exists on any of them, so none can be selected safely. Treated as unresolved at source; remediation proposed in `GOOGLE_DRIVE_UPDATE_SUGGESTIONS.md`. This is E-040 |
| C-7 | Template naming: `templates/` holds both full controlled filenames (`M-1002 Exhibit B-2 Activity Code B24 (RL2) - (5-1-2026).docx`) and short aliases (`B24_RL2.docx`, `B24 (RL2).docx`) | The full controlled filename carries the form identity and revision date and is canonical. Short aliases are convenience handles for code and must never be the source of form identity. This is E-040 |
