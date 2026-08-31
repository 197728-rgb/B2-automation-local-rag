# ID Crosswalk

The 1.3 pack used one ID space per axis (`E-` mechanism, `F-` control, `L-` principle,
`A-` assumption, `R-` test). Version 2.0 uses a single permanent incident ID, `AAR-R###`,
that tests, gates, and forensic records all reference.

Both spaces are live: `AAR-R###` is the incident, and the `E-`/`F-` identifiers still key
the knowledge files that explain it. This table is the join.

| Incident | 1.3 mechanism | 1.3 control | Test |
|---|---|---|---|
| AAR-R001 | E-006 | F-08 | TEST-B81-001 |
| AAR-R002 | E-007 | F-08 | TEST-B81-002 |
| AAR-R003 | E-021 | F-15, F-16 | TEST-B24-003 |
| AAR-R004 | E-018 | F-15, F-16 | TEST-B24-010 |
| AAR-R005 | E-024 | F-18 | TEST-DOCX-005 |
| AAR-R006 | E-025, E-026 | F-19, F-20 | TEST-DOCX-006 |
| AAR-R007 | E-001 | F-01 | TEST-CORE-007 |
| AAR-R008 | E-008 | F-05 | TEST-CORE-008 |
| AAR-R009 | E-033 | F-23 | TEST-QAPE-009 |
| AAR-R010 | E-020 | F-16 | TEST-B24-010 |
| AAR-R011 | E-011 | F-10 | — |
| AAR-R012 | E-012 | F-11 | — |
| AAR-R013 | E-014 | F-12 | — |
| AAR-R014 | E-015 | F-13 | — |
| AAR-R015 | E-016, E-017 | F-14 | — |
| AAR-R016 | E-023 | F-17 | — |
| AAR-R017 | E-027 | F-20 | — |
| AAR-R018 | E-029 | F-21 | — |
| AAR-R019 | E-028 | F-04 | — |
| AAR-R020 | E-031, E-032 | F-22 | — |
| AAR-R021 | E-035 | F-25 | — |
| AAR-R022 | E-036 | F-26 | — |
| AAR-R023 | E-040, E-041 | F-30 | — |
| AAR-R024 | E-043 | F-32 | — |
| AAR-R025 | E-049 | F-36 | — |

Mechanisms in the 1.3 ledger with no `AAR-R###` row (E-002 through E-005, E-009, E-010,
E-013, E-019, E-022, E-030, E-034, E-037 through E-039, E-042, E-044 through E-048, E-050)
remain recorded knowledge. They have not been promoted to incident IDs because they have
not recurred in this program of work — promotion is driven by recurrence, per
`../tools/LESSON_PROMOTION.md`, not by wanting a complete-looking table.
