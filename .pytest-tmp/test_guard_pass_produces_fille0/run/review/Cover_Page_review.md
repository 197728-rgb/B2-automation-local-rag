# Cover_Page Local Evidence Review

Write authority: none; exact approval_map.json is required before DOCX patching

## Decision states (discrete)

Counts by state:
- **FILL**: 4

Fill-eligible field IDs (FILL only):
auditor, car_number, date, facility_name

## Field decisions
- **auditor** — `FILL` — value='Casey' conf=0.87 — selected highest-confidence local evidence
- **car_number** — `FILL` — value='DOTX 123456' conf=0.95 — selected highest-confidence local evidence
- **date** — `FILL` — value='2026-05-07' conf=0.95 — selected highest-confidence local evidence
- **facility_name** — `FILL` — value='Midwest Tank Rail Inc B24 RL2 objective evidence Date: 2026-05-07 B81 stub sill' conf=0.95 — selected highest-confidence local evidence

## Sources
- evidence.txt

## Retrieved context
- evidence.txt chunk 1 score 250: Cover Page Facility: Midwest Tank Rail Inc B24 RL2 objective evidence Date: 2026-05-07 B81 stub sill evidence Car: DOTX 123456 B89 insulation test plate B90 RLS return to service Auditor: Casey

## Field suggestions
- facility_name: Midwest Tank Rail Inc B24 RL2 objective evidence Date: 2026-05-07 B81 stub sill (evidence.txt chunk 1)
- auditor: Casey (evidence.txt chunk 1)
- date: 2026-05-07 (evidence.txt chunk 1)
- car_number: DOTX 123456 (evidence.txt chunk 1)

## Review required (ambiguous disagreements)
- None

## Missing fields
- None

## Conflicts
- None

## Low confidence fields
- None
