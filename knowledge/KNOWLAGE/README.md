# KNOWLAGE — CONSOLIDATED ACTIVE KNOWLEDGE

Documentation-only, customer-neutral knowledge package for repeatable AAR B-2 / QAPE work.

## Governing principle

The customer-data firewall, `01_ACTIVE_RULES.md` Rule 1, governs everything here. It is
stated there and referenced, not restated.

## File ownership

Each concept has one authoritative home, so retrieval returns one answer rather than
several wordings of it.

| File | Authoritative purpose |
|---|---|
| `01_ACTIVE_RULES.md` | Rules that always govern |
| `02_B2_QAPE_PLAYBOOK.md` | Step-by-step operating method |
| `03_ERROR_LEDGER.md` | Generalized failure classes, root causes, governing controls |
| `04_REGRESSION_AND_RELEASE_GATES.md` | Recurrence-prevention tests and release criteria |
| `05_FORENSIC_NOTES.md` | Historical reasoning only; never current authority |
| `README.md` | Package scope, boundaries, file ownership |
| `MANIFEST.md` | File inventory and integrity hashes |
| `regression/` | The executable form of `04`: controls that fail |

## Data boundary

This package must not contain:

- customer or facility names;
- personnel names;
- customer identifiers;
- prior-audit identities;
- exact values copied from B-2 / QAPE records;
- customer-specific procedures, drawings, reports, certificates, equipment, revisions,
  dates, calibration data, or conclusions;
- customer-specific file paths or filenames.

Current audit facts belong only in the current engagement workspace.

Regression fixtures use neutral placeholders (`TECH_A`, `INSTRUMENT_A`, `ID_A`) precisely
so that a test can exercise a failure class without importing an incident.

One deliberate exception: the firewall test (`R-18`) must contain text *shaped* like a
violation in order to detect one. Its fixture uses `PLACEHOLDER_FACILITY` and a synthetic
mark that belongs to no real registry. These are pattern shapes, not customer facts, and
this is the only place in the package where such a shape appears.

## Scope of application

Nothing here is specific to one B-2 activity code, one QAPE element, one facility, one
tool, or one year. If a rule cannot be applied without knowing the activity code in
advance, the rule is written wrong.

## Retrieval rule

Use `01_ACTIVE_RULES.md` and `02_B2_QAPE_PLAYBOOK.md` for day-to-day work. Consult
`03_ERROR_LEDGER.md` and `05_FORENSIC_NOTES.md` only to understand failure classes. Use
`04_REGRESSION_AND_RELEASE_GATES.md` and `regression/` for verification and release.
