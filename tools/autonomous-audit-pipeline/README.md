# Autonomous audit pipeline (TypeScript reference)

TypeScript reference implementation for **SPEC-1** (`docs/SPEC-1-LOCAL-MVP.md`). Production DOCX writes and inbox batching use Python:

```bash
b2 run-autonomous --inbox ./inbox --out ./outputs/autonomous_run
```

## Pipeline

`analyzeDocxForm` → `gatherEvidence` → `synthesizeAnswer` → `validateAnswer` → `writeCompletedDocx`

## Setup

```powershell
cd tools/autonomous-audit-pipeline
copy .env.example .env
# set GEMINI_API_KEY
npm install
npm run build
```

## Run (single form)

```powershell
npx tsx src/mainPipeline.ts test-data/blank-form.docx test-data/sources outputs --mock
```

Without `GEMINI_API_KEY`, the CLI auto-enables `--mock` (deterministic field map + source snippets). With a key in `.env`, omit `--mock` for full Gemini stages.

**Smoke test assets:** `test-data/blank-form.docx`, `test-data/sources/*.md`, `test-data/available-schemas.json`.

Outputs under `<output>/completed/` and `<output>/audit-trail/`:

- `completed/<stem>_completed.docx`
- `audit-trail/<stem>_pipeline_audit_trail.json`
- `audit-trail/<stem>_machine_field_map.v1.json`

Regenerate the blank form:

```powershell
python scripts/create-blank-form-docx.py
```

## Contracts

- Types: `src/schemas.ts`
- JSON Schema (canonical): `../../schemas/contracts/machineFieldMap.v1.schema.json`
- Fallback text aligned with Python: `Not verified in provided source documents.`

## Scaffold script

Regenerate base config:

```powershell
..\..\scripts\setup-autonomous-audit-pipeline.ps1
```

Source modules are maintained in `src/`; the script updates `package.json`, `tsconfig.json`, and `.env.example` only.
