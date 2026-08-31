# Session Summary

Build of the consolidated KNOWLAGE archive · 2026-08-31

## Sources actually used

Only what was reachable in this session. Nothing below is claimed on trust.

| Source | Reached how | Used for |
|---|---|---|
| `B2-automation-local-rag` working tree | Local checkout, 487 tracked files | Governance, guardrails, architecture, spec, hygiene and triage docs |
| Git history, 141 commits | `git log` | Real incidents: content-control fill, stale approval-map cells, OCR noise, revert churn |
| Nested `b2-sentinel` layer | Local checkout | `GOVERNANCE.md` LLM-boundary rules, activity schemas |
| B2S platform skill guide | Session skill store | SOP 0–10 pipeline, activity codes, operational failure catalogue |
| Google Drive `other/` and `zip/` | Drive search and read | Field schema, duplicate-copy findings, evidence/knowledge separation problem |
| Prior pack 1.2 (`CLAUDE_KNOWLEDGE_REPEATABILITY_FIXED`) | Uploaded archive, read in full | Rollover failure set: dropped owner instructions, Type COC, TCID, merged rows |
| Pack 1.3 and the v2 system | Built earlier this session | Incident IDs, executable controls, release gate |
| Automated PR review findings | GitHub PR #53 | AAR-R025 — the evidence-contamination incident |

## Sources I could not access

Stated plainly rather than implied:

- **Chat transcripts and archived sessions.** No conversation export exists in this
  environment. What is captured instead is their durable residue: committed code and
  history, the documents those sessions produced, the persistent skill guide, the Drive
  store, and pack 1.2 — itself a distillation of an earlier engagement. Anything discussed
  in a prior session but never written down is **not** in this archive.
- **Drive audit ZIPs** (`B2 Site AAR Audit Part 1.zip`, `B2 Site Information.zip`) — not
  opened. They are facility evidence and barred by AR-03 from permanent knowledge.
- **The original engagement behind pack 1.2** — no longer reachable. Its incidents are
  carried forward on the strength of that pack's own record, not re-verified.
- **Checker outputs from live audits** (UTCT/QAPE rejections) — described in pack 1.2 and
  in the request, but the raw checker reports were not available to read. Incidents
  derived from them are recorded at the level of detail the sources supported.

## What was reconciled

Seven conflicts between sources. Six resolved, one unresolved — detail in `MANIFEST.md`.

The largest: **write authority**. `AGENTS.md` and the Cursor rules state that only exact
approval maps may authorize a DOCX write; `SPEC-1-LOCAL-MVP.md` states autonomous runs use
`machine_field_map.v1` with no approval map. Not a contradiction but an undeclared mode
split, now stated once in AR-08.

## Deduplication

Pack 1.2 stated the personnel-row rule in three files. Pack 1.3 split content across six ID
spaces; the v2 system added a seventh and a crosswalk to join them. This archive uses three
spaces — `AR-##` rules, `AAR-R###` incidents, `TEST-###` tests — with one authoritative
home per rule. Full list of removals in `MANIFEST.md`.

## Verification performed

- Regression suite run: 10 controls, both halves each.
- Release gate exercised in both directions: clean run SHIPs, contaminated run blocks with
  the correct counters.
- Every `AR-`, `AAR-R`, and `TEST-` reference resolves to a definition.
- No rule stated in two files.
- Archive scanned for facility identifiers outside `04_FORENSIC_ARCHIVE/`.
- ZIP re-opened and verified after creation.

## Honest limits

- **16 of 26 incidents are `RULE ONLY`** — a rule exists, but nothing fails if it recurs.
  Six are worth building and are listed in `REGRESSION_TESTS_SUGGESTION.md`; the rest
  resist a mechanical test, and a check pretending otherwise would be worse than the gap.
- **The gate depends on an honest run record.** It reads what a run reports. A pipeline
  that does not emit a run record is not gated by it.
- **One unresolved conflict** remains, recorded rather than guessed.
