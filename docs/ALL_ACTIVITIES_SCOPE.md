# All Activities Scope Rule

The audit automation scope covers every required activity form equally.

Required forms:

- B24
- B81
- B89
- B90
- Cover

Production rule:

```text
Evidence is always scoped by form and activity.
```

Canonical branches must stay separate:

```text
B24.*
B81.*
B89.*
B90.*
Cover.*
```

Examples:

```text
B24.welding
B81.ndt
B89.welding
B90.welding
Cover.audit_metadata
```

Shared evidence may be referenced by more than one form only when the source evidence clearly supports each form.

Review reports must be generated per form and as a master review.

Overall completion requires every required form to pass its own required-evidence, conflict, confidence, and formatting checks.

Current common evidence groups across forms:

- TCO authorization
- PITP traceability
- design control
- materials
- welding
- NDT
- equipment calibration
- personnel qualification
- inspection records
- TCID records
- audit metadata
