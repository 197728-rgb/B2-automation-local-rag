# KNOWLAGE 1.3 — Repeatable AAR B-2 / QAPE Audit Knowledge Pack

Version: 1.3
Built: 2026-08-31
Supersedes: `CLAUDE_KNOWLEDGE_REPEATABILITY_FIXED` (referred to below as 1.2)

## What this pack is

Method memory for producing **AAR M-1002 Exhibit B-2 and QAPE audit reports repeatably**,
regardless of activity code, exhibit count, audited element set, facility, tooling, or year.

It answers one question: *what has to be true before a value is written into a controlled
audit form, and what has to be proven before that form is handed off?*

## What this pack is not

- It is not audit evidence. It contains no facility names, personnel, equipment IDs,
  car marks, dates, findings, or completed forms.
- It is not a cell map. It contains no remembered table/row/cell coordinates.
- It is not a runtime dependency. Nothing in an audit run may require this pack to be
  present, and nothing here may be treated as authority over a current controlled form.

## Contents map

Each file owns exactly one axis. No fact is stated in two files (see *Non-duplication rule*).

### Governing knowledge (adopted)

| File | Owns | ID space |
|---|---|---|
| `ERROR_LEDGER.md` | Failure mechanisms actually observed, and where | `E-###` |
| `DURABLE_FIXES.md` | The control that defeats each mechanism, and its proof artifact | `F-##` |
| `HARD_LESSONS.md` | The generalizable principle behind the controls | `L-##` |
| `FAILED_ASSUMPTIONS.md` | Beliefs that were held and proved false, and what is true instead | `A-##` |
| `DO_NOT_REPEAT.md` | Run-ordered refusal gates: when to stop and what unblocks it | `G-#` |
| `AAR_AUDIT_REPORT_PLAYBOOK.md` | The phase-by-phase procedure | Phases 0–8 |
| `FIELD_AUTHORITY_AND_COMPLETENESS.md` | Semantic keys, authority, dispositions, row identity | — |
| `VALIDATION_AND_REGRESSION.md` | Known-bad / known-good cases that exercise the controls | `R-##` |

### Provenance and proposals (not yet adopted)

| File | Owns |
|---|---|
| `KNOWLEDGE_SOURCES_INDEX.md` | Every source ingested, what was copied vs referenced, precedence, reconciled source conflicts |
| `SESSION_SUMMARY.md` | What this build session did, and the limits of what it could reach |
| `CHANGELOG_FROM_KNOWLAGE_1_2.md` | Delta from version 1.2 |
| `GOOGLE_DRIVE_UPDATE_SUGGESTIONS.md` | Proposed Google Drive knowledge-store changes, by file ID |
| `ENGAGEMENT_LESSONS_SUGGESTION.md` | Proposed promotions into durable engagement/assistant guidance |
| `FUTURE_AGENT_NOTES.md` | Startup sequence and how to extend this pack |
| `MANIFEST.md` / `PACK_MANIFEST.json` | File list, byte counts, SHA-256 |
| `tools/build_knowlage_archive.py` | Rebuilds this archive and regenerates both manifests |

### Snapshots

| Path | Contents |
|---|---|
| `source/repo/` | Project source snapshot: `B2-automation-local-rag` (and nested `b2-sentinel`) |
| `source/git-history/` | Commit log and branch state at build time |
| `memory/` | Retained historical memory: the B2S platform skill guide, the Google Drive knowledge index, and the B-2 master field schema |

## Precedence

When two statements in this archive appear to conflict, resolve in this order:

1. The **current controlled form or governing requirement** supplied with the live audit.
2. **Governing knowledge** files in the table above.
3. **Proposal** files — these describe changes that have *not* been adopted and never
   override governing knowledge.
4. **Snapshots** under `source/` and `memory/` — these are historical inputs, frozen at
   build time. They record what a tool or document said, not what must be done.

A snapshot that disagrees with governing knowledge is a stale snapshot, not an exception.

## Non-duplication rule

A fact appears in exactly one file, under exactly one ID. Every other file that needs it
cites the ID instead of restating it. This is what keeps the pack from drifting into
self-contradiction as it grows.

When adding knowledge, ask which axis it belongs to:
*what went wrong* (E) · *what prevents it* (F) · *why it generalizes* (L) ·
*what was wrongly believed* (A) · *when to refuse to continue* (G) ·
*what test proves it* (R). If it fits two, it is stated at the wrong altitude — split it.

## Permanent knowledge boundary

Permanent knowledge may hold: blank controlled B-2 and QAPE forms, requirement and
guidance documents, revision notices, work aids, writer/reviewer instructions, form
identity references, and this pack.

Permanent knowledge may never hold: completed facility forms, or any facility name,
person, equipment ID, car mark, date, procedure, record, or finding.

Every audit starts in a new session and receives only that audit's evidence.

## Startup

See `FUTURE_AGENT_NOTES.md`.
