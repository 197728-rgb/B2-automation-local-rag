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
| Local inbox review | `.\.venv\Scripts\b2.exe inbox --inbox .\inbox --out .\outputs\local_rag_run` |
| Table maps | `.\.venv\Scripts\b2.exe discover` |

## Project layout

- `src/` main source package
- `tests/` pytest test suite
- `scripts/` runnable utilities
- `inputs/` scanned evidence inputs, gitignored
- `outputs/` generated artifacts, gitignored
- `templates/` DOCX form templates
- `schemas/` template maps and extraction schemas
- `salvage/` old-tool reference material only

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
