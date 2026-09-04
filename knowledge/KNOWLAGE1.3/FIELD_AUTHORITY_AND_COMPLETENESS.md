# Field Authority and Completeness

The mechanics of addressing a field, authorizing its value, and proving nothing was lost.

This file owns **the semantic key, the authority matrix, the disposition set, the identity
keys, and the high-risk field list**. The sequence that uses them is in
`AAR_AUDIT_REPORT_PLAYBOOK.md`.

---

## 1. Semantic key

Every destination is addressed by meaning, never by remembered position.

```text
Form | ActivityCodeOrElement | Section | FieldLabel | EntityKey | Applicability | RevisionState
```

- `Form` — controlled title as printed on the document.
- `ActivityCodeOrElement` — the B-2 activity code and variant, or the QAPE element.
- `Section` — the section heading as printed.
- `FieldLabel` — the exact label text, not a paraphrase.
- `EntityKey` — required for repeating rows; see §4.
- `Applicability` — applicable, conditionally applicable, or not used in this demonstration.
- `RevisionState` — the form revision or effective date this key was resolved against.

A physical coordinate may be recorded *after* the semantic key resolves. It expires with
that document instance and is never reused as an input.

## 2. Authority matrix

For each destination fact, record before any value is eligible:

| Element | Meaning |
|---|---|
| Destination | The semantic key from §1 |
| Admissible sources | The source classes that may prove *this* fact |
| Entity identity | The exact person, item, procedure, or record concerned |
| Applicability basis | Why the field applies or does not |
| Effective context | The revision, approval, or validity window that must hold |

A source is admissible for a fact or it is not. Being relevant, adjacent, recent, or
supplied in the same folder does not confer admissibility.

## 3. Disposition set

Every relevant target field and every populated baseline fact ends in exactly one state.

| Disposition | Meaning |
|---|---|
| `CONFIRMED_VALUE` | An admissible source proves this value |
| `PRESERVE_BASELINE` | An existing value remains supported and undisproven |
| `CONTROLLED_BLANK` | Blank is correct by scope or form logic, and the rule is cited |
| `AUTHORIZED_NA` | N/A is permitted here by the form or governing rule, and the rule is cited |
| `WITHHOLD_CONFLICT` | Admissible sources disagree; the conflict is recorded, not resolved by preference |
| `UNVERIFIABLE` | Required evidence not found after source exhaustion; the surfaces searched are listed |

### Two-way completeness

**Direction A — source and baseline → output.** Every populated fact ends as preserved,
updated from stronger current evidence, withheld for conflict, authorized N/A, or
explicitly reported unplaceable. No fact simply disappears.

**Direction B — output → evidence.** Every relevant field ends as a supported value, a
preserved supported value, a controlled blank, an authorized N/A, a withheld conflict, or
a reported unverifiable. No field is silently invented or silently skipped.

Each direction catches what the other misses; running one is not running the check.

## 4. Identity keys for repeating rows

One identity, one row. Concatenation destroys the separability the table exists for.

| Record type | Identity key components |
|---|---|
| Personnel | Name or personnel ID; qualification or certification number; method and level where the row distinguishes them |
| Equipment | Equipment type; ID or serial; function performed; calibration record identity where the row distinguishes them |
| NDT technician | Technician ID; level qualified; method; qualification and acuity validity dates |
| Procedure / record | Procedure or form number; revision; approval or effective state |
| Material | Material specification; heat, batch, or lot ID; status indicator |

Two records that share every component are one record. Two that differ in any component
are two rows.

## 5. Conditional sections

A section present on a blank form may be applicable, conditionally applicable, or unused
in the observed demonstration.

Do not populate a section because it exists. Do not delete a controlled section because it
is unused. Use `CONTROLLED_BLANK` or `AUTHORIZED_NA` per §3, with the rule cited.

## 6. Evidence families

Program-level evidence and technical-demonstration evidence answer different questions and
are not interchangeable in either direction. Documented-system evidence can support a
manual determination; a compliance or implementation determination needs evidence of the
act itself. Each citation is labelled with the family it satisfies.

## 7. High-risk field checklist

Inspected explicitly on every run, whether or not the run expects them to change:

- owner permission and written instructions
- demonstration type or classification
- design-control classification / Type COC
- personnel and qualification records
- equipment and calibration records
- NDT approver identifiers and qualification validity
- TCID entries: revision, type, entry, work description
- traceability and marking
- auditor objective-evidence notes and comments
- signature and attestation state

These are the fields that have actually gone missing (E-018 through E-022). Presence of
this list in the run record is the proof for F-15.
