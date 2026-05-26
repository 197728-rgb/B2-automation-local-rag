---
description: 
alwaysApply: true
---

# AGENTS.md

## Project overview

B2-automation is a local Association of American Railroads audit evidence review tool.

The default pipeline is local-first:

```text
local OCR/text extraction
-> local retrieval
-> per-form evidence packets
-> review reports
-> exact approval maps
-> safe raw OOXML DOCX patching
```

DocuPipe is not part of the normal workflow. Keep `docupipe_client.py` only for optional scripted extraction tests or experiments.

## Autonomous mode (`b2 run-autonomous`)

SPEC-1 end-to-end pipeline uses `machine_field_map.v1` as write authority (not approval maps). No `review.json` / `review.md` in autonomous runs. **Canonical ops doc:** `docs/SPEC-1-LOCAL-MVP.md`. **Full personal spec:** `docs/SPEC-1-PERSONAL.md`. Code: `src/b2_automation/autonomous_pipeline.py`, `tools/autonomous-audit-pipeline/`.

## First-class form scope

Treat these forms equally:

- `B24_RL2`
- `B81`
- `B89`
- `B90`
- `Cover_Page`

## Build rules

- Do not require paid APIs for normal tests, demos, or inbox review.
- Do not let RAG authorize DOCX write locations.
- Use exact per-form/version approval maps for DOCX writes.
- Do not use generic, similar, nearest, or latest approval maps.
- Do not hard-code guessed DOCX table indexes.
- Preserve DOCX table formatting.
- Prefer raw OOXML byte patching for production DOCX writes.
- Do not hand off filled DOCX output unless `structure_guard_report.json` passes.
- Always write review JSON and Markdown for missing, conflicting, and low-confidence evidence.
- Keep raw extraction, chunk, retrieval, and metadata artifacts for traceability.
- Keep `inputs/`, `outputs/`, `.env`, and `.venv/` out of git.
- **Inbox evidence:** put `.pdf`, `.txt`, `.docx`, and other supported types at the **top level** of the inbox folder, or add **`.zip`** archives whose *members* use those extensions. The pipeline unpacks each zip into `<out>/staged_inbox` before extraction (nested zips are supported up to an internal depth limit).

## Current filled-DOCX baseline

- Treat `c43e215` (`Make filled DOCX values visibly readable`) or any later `main` commit containing it as the minimum baseline for handoff-quality filled DOCX output.
- Do not use `7adc4f2` alone as the "good filled templates" reference. That commit can write values into DOCX XML while leaving some values inside Word placeholder/content controls, which can make table cells look blank in Word.
- The current local handoff workflow is:

```powershell
.\.venv\Scripts\b2.exe inbox --inbox .\inbox --out .\outputs
```

- The canonical current filled templates are the five `*_filled.docx` files in:

```text
C:\Projects\B2-automation-local-rag\outputs\filled\
```

- A good handoff run must report `Status: success`, `Filled DOCX (5 this run)`, passing structure guards, and no required visible table-cell blanks for `B24_RL2`, `B81`, `B89`, `B90`, and `Cover_Page`.

## Development environment

Python 3.12 preferred.

Windows setup:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

## Key commands

| Task | Windows |
|---|---|
| Run tests | `.\.venv\Scripts\python.exe -m pytest -q --basetemp .pytest-tmp` |
| CLI version | `.\.venv\Scripts\b2.exe --version` |
| CLI help | `.\.venv\Scripts\b2.exe inbox --help` |
| Current filled B2 handoff | `.\.venv\Scripts\b2.exe inbox --inbox .\inbox --out .\outputs` |
| Named/debug inbox review | `.\.venv\Scripts\b2.exe inbox --inbox .\inbox --out .\outputs\local_rag_run` |
| Table maps | `.\.venv\Scripts\b2.exe discover` |

## Project layout

- `src/` main source package
- `tests/` pytest test suite
- `scripts/` runnable utilities
- `inputs/` scanned evidence inputs, gitignored
- `outputs/` generated artifacts, gitignored
- `templates/` DOCX form templates
- `schemas/` template maps and extraction schemas

## Cursor Cloud specific instructions

On Linux/Cloud VMs the venv and CLI live under `.venv/bin/` (not `.venv/Scripts/`).

| Task | Command |
|---|---|
| Run tests | `.venv/bin/python -m pytest -q` |
| CLI version | `.venv/bin/b2 --version` |
| CLI help | `.venv/bin/b2 inbox --help` |
| Local inbox review | `.venv/bin/b2 inbox --inbox ./inbox --out ./outputs/local_rag_run` |
| Table maps | `.venv/bin/b2 discover` |
| Demo output | `.venv/bin/b2 demo` |

- No database, Docker, or external services are required. The entire tool is a local CLI.
- Tesseract OCR is optional; text-based files (.txt, .md, .json, .csv) and text-layer PDFs work without it. Only scanned/image PDFs need the `tesseract` system binary.
- The update script creates `.venv` and installs `.[dev]` automatically. After that, all `b2` and `pytest` commands are available immediately.
- `outputs/` and `inbox/` are gitignored; create them as needed for testing.
