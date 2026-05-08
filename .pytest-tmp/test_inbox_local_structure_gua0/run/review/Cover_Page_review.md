# Cover_Page Local Evidence Review

Write authority: none; exact approval_map.json is required before DOCX patching

## Decision states (discrete)

Counts by state:
- **FILL**: 3

Fill-eligible field IDs (FILL only):
car_number, date, facility_name

## Field decisions
- **car_number** — `FILL` — value='DOTX 123456' conf=0.95 — selected highest-confidence local evidence
- **date** — `FILL` — value='2026-05-07' conf=0.95 — selected highest-confidence local evidence
- **facility_name** — `FILL` — value='Midwest Tank Rail Inc B24 RL2 objective evidence Date: 2026-05-07 B81 stub sill' conf=0.95 — selected highest-confidence local evidence

## Sources
- packet_one.txt

## Retrieved context
- packet_one.txt chunk 1 score 294: Cover Page Facility: Midwest Tank Rail Inc B24 RL2 objective evidence Date: 2026-05-07 B81 stub sill evidence Car: DOTX 123456

## Field suggestions
- facility_name: Midwest Tank Rail Inc B24 RL2 objective evidence Date: 2026-05-07 B81 stub sill (packet_one.txt chunk 1)
- date: 2026-05-07 (packet_one.txt chunk 1)
- car_number: DOTX 123456 (packet_one.txt chunk 1)

## Review required (ambiguous disagreements)
- None

## Missing fields
- None

## Conflicts
- None

## Low confidence fields
- None
