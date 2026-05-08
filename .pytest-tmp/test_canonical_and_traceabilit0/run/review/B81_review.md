# B81 Local Evidence Review

Write authority: none; exact approval_map.json is required before DOCX patching

## Decision states (discrete)

Counts by state:
- **FILL**: 4

Fill-eligible field IDs (FILL only):
auditor, car_number, date, facility_name

## Field decisions
- **auditor** — `FILL` — value='Pat' conf=0.87 — selected highest-confidence local evidence
- **car_number** — `FILL` — value='XX 99999' conf=0.95 — selected highest-confidence local evidence
- **date** — `FILL` — value='2026-05-07' conf=0.95 — selected highest-confidence local evidence
- **facility_name** — `FILL` — value='Acme Co B24 RL2 objective evidence Date: 2026-05-07 B81 Car: XX 99999 B89 insula' conf=0.95 — selected highest-confidence local evidence

## Sources
- evidence.txt

## Retrieved context
- evidence.txt chunk 1 score 192: Cover Page Facility: Acme Co B24 RL2 objective evidence Date: 2026-05-07 B81 Car: XX 99999 B89 insulation plate B90 Auditor: Pat

## Field suggestions
- facility_name: Acme Co B24 RL2 objective evidence Date: 2026-05-07 B81 Car: XX 99999 B89 insula (evidence.txt chunk 1)
- auditor: Pat (evidence.txt chunk 1)
- date: 2026-05-07 (evidence.txt chunk 1)
- car_number: XX 99999 (evidence.txt chunk 1)

## Review required (ambiguous disagreements)
- None

## Missing fields
- None

## Conflicts
- None

## Low confidence fields
- None
