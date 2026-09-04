# Future Agent Notes

How to start a job with this pack, and how to extend it without breaking it.

This file owns **startup and maintenance**. It contains no method — that is
`AAR_AUDIT_REPORT_PLAYBOOK.md` — and no rules, which live under their IDs.

---

## Startup

1. Read `README.md` — scope, precedence, and the non-duplication rule.
2. Read `AAR_AUDIT_REPORT_PLAYBOOK.md` — the procedure end to end.
3. Lock the mode and the baseline. Gate G-1.
4. Establish scope once, from the current controlled documents. Gate G-2.
5. Keep `FIELD_AUTHORITY_AND_COMPLETENESS.md` open while mapping fields.
6. Walk `DO_NOT_REPEAT.md` in order. The gates are the run.
7. Before claiming completion, run the relevant cases from
   `VALIDATION_AND_REGRESSION.md` against the delivered artifact.

`ERROR_LEDGER.md`, `DURABLE_FIXES.md`, `HARD_LESSONS.md`, and `FAILED_ASSUMPTIONS.md` are
reference, not reading order. Go to them when a gate blocks and you need to know why.

## Behavior

- This pack is not a runtime dependency. If a job cannot proceed without it, the job is
  wrongly designed — the current controlled form and the supplied evidence are sufficient.
- Do not look for a project router, a prior KNOWLAGE archive, or a qualification flag.
  Nothing here requires them.
- Do not assume workstation paths, drive letters, or generator stage names. The snapshots
  under `source/` show one machine's layout at one moment.
- Do not carry facility evidence between sessions, in either direction.
- Treat historical examples as visual benchmarks. They are never data.

## Snapshots

`source/` and `memory/` are frozen at build time and rank last in precedence. A snapshot
that disagrees with a governing file is stale, not an exception. When a snapshot matters
to a decision, check it against the live repository or store before relying on it.

## Extending this pack

**Adding knowledge.** Decide the axis first: what went wrong (`E`), what prevents it (`F`),
why it generalizes (`L`), what was wrongly believed (`A`), when to stop (`G`), what proves
it (`R`). Add it to exactly one file, under a new ID, and cite that ID from anywhere else
it is relevant. If it seems to fit two axes, it is written at the wrong altitude — split it
until each half fits one.

**Adding a control.** A control is not complete until it has a minimum proof in
`DURABLE_FIXES.md` and at least one known-bad and one known-good case in
`VALIDATION_AND_REGRESSION.md`. A control with no failing case is an intention.

**When sources disagree.** Resolve it and record the resolution once, as a new `C-#` in
`KNOWLEDGE_SOURCES_INDEX.md`. Do not restate the ambiguity in the files that consume it.

**Adopting a proposal.** Move it out of `ENGAGEMENT_LESSONS_SUGGESTION.md` into the file
that owns its axis, and delete it from the proposal register. It must not appear in both.

**Rebuilding.** `python tools/build_knowlage_archive.py` regenerates the archive and both
manifests from the pack directory. Do not hand-edit `MANIFEST.md` or `PACK_MANIFEST.json`.

**Versioning.** Reissue the pack whole. Fragmentary patching is E-046, and the control
against it is F-35 — which applies to this pack as much as to any instruction set.
