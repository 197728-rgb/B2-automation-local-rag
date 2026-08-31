# AAR-R025 — A published absence claim with nothing enforcing it

Date: 2026-08-31 · Surfaced by: automated PR review on PR #53 · Severity: high

## Observed

The KNOWLAGE 1.3 knowledge pack stated, in two places:

> Confirmed absent from this archive: no facility name, personnel identifier, car mark,
> calibration date, finding, or completed form.

> The archive was scanned for facility identifiers before packing; none are present.

The archive contained 11 evidence-bearing files:

- three completed B-2 forms and their validation reports
  (`b2-sentinel/tests/fixtures/FILLED_*`);
- a fixture carrying a TCO name, an approver name, a PITP identifier, and dates
  (`tests/fixtures/dlga_*`);
- a facility profile and an NDT personnel roster
  (`tools/autonomous-audit-pipeline/test-data/sources/*`).

The pack's own boundary bars completed facility forms from permanent knowledge. Loading
the archive as reference material in a later audit was exactly the contamination path the
pack existed to prevent.

## Root cause

The "scan" behind the claim checked **path patterns** — `inbox/`, `outputs/`, `.env`,
`node_modules` — and never checked **content**. It was written to confirm the expected
answer rather than to look for the failure. The claim was then published as verified.

Two contributing conditions:

1. The snapshot walked the filesystem rather than the tracked file list, so what belonged
   in the pack was decided by a hand-maintained exclusion list instead of by the
   repository's own ignore rules. In a working audit checkout the same walk would have
   copied `.env` and `inputs/`.
2. Nothing could fail. The claim lived only in prose.

## Generalized lesson

A completeness or absence claim is worth exactly as much as the check that can falsify it.
Documentation asserting a property, with no mechanism that fails when the property is
false, is a statement of intent presented as a result.

## Durable fix

- Source the snapshot from `git ls-files`, so ignored local state is out of scope by
  construction (F-37 / `RELEASE_RULES` §1).
- Exclude completed forms and evidence-shaped fixtures explicitly.
- Scan the staged pack before packing; **refuse to build** on a hit.
- State the scan's limits rather than implying total coverage: `.py` files are not
  scanned, because reporting marks appear there in regex alternations and illustrative
  docstrings, and the claim is narrowed to match.

## Verification

The gate was run against the contaminated pack **before** being trusted, and rejected it,
naming all 11 files. The rebuilt archive was then re-verified with an independent scanner
written separately from the gate: no hits.

## Why this incident founded the system

Every other incident in the ledger was a mistake inside an audit. This one was a mistake
in the mechanism meant to prevent mistakes — a lesson that had been documented, reviewed,
published, and was still false.

It is the reason the release gate exists, the reason every control ships with a known-bad
case that must fail, and the reason `RELEASE_RULES` §1 is the first release rule.
