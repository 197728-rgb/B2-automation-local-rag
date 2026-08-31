# Durable Fixes

The fix behind each rule, and **the artifact that proves it is in place**. A fix with no
proof is an intention.

Rules are in `01_ACTIVE_RULES/ACTIVE_RULES.md` and not restated. Incidents are in
`ERROR_LEDGER.md`.

| Rule | Fix in practice | Minimum proof in the run record |
|---|---|---|
| AR-01 | Mode and baseline declared before evidence is read | Run record names the mode and the exact baseline file |
| AR-02 | Accepted completed form selected as baseline; rebuild requires a stated reason | Baseline selection recorded with its reason |
| AR-03 | Per-field authority matrix; one canonical copy per reference subject | Every value links to an admissible source and location; canonical marker on each reference set |
| AR-04 | Fields and elements enumerated from the document in hand | Discovered field list carries the controlled title and revision |
| AR-05 | Semantic key resolved before coordinates; coordinates re-derived per run | Every write cites its semantic key; structure report dated this run |
| AR-06 | One entity per row, identity keys declared | Row-to-entity table with a distinct key per row |
| AR-07 | Two-way completeness ledger; source exhaustion before absence; environment preflight | No unresolved entry in either direction; searched surfaces listed; preflight recorded at run start |
| AR-08 | Write authorized only by an exact versioned map; noise gate before eligibility; fallbacks disclosed | Authorization names the map and version; rejected candidates recorded with the rule that rejected them |
| AR-09 | Merge owner resolved; geometry compared before and after | Write report names the owning cell; structure identical outside authorized cells |
| AR-10 | Formatting bound into the write operation | Write report shows per-write formatting; no document-wide pass logged |
| AR-11 | Semantic readback, machine extraction readback, full-page render review | Extraction matches intended values; every page inspected, tail pages included |
| AR-12 | Gate run on the delivered artifact; regression suite green; delivery allowlist checked | Gate output against the shipped file; suite result; delivery listing matches allowlist |

## Two fixes that apply to this archive itself

**Snapshots source from the tracked file list.** What a repository already ignores is out
of scope by construction, not by a hand-maintained exclusion list that drifts.
*Proof:* file list derived from `git ls-files`.

**Every published claim ships with a check demonstrated failing.** Run the failing case
before trusting the control.
*Proof:* the check exists, runs in the build, and has been shown to reject a violating
input. See `04_FORENSIC_ARCHIVE/incidents/AAR-R025.md`.
