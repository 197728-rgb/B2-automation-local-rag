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

DocuPipe is not part of the normal workflow. Keep `docupipe_client.py` only as a legacy adapter behind an explicit `--legacy-docupipe` option.

## First-class form scope

Treat these forms equally:

- `B24_RL2`
- `B81`
- `B89`
- `B90`
- `Cover_Page`

`B24_RL1` is legacy/sample only. Do not design new default behavior around B24 RL1.

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
| Legacy DocuPipe path | `.\.venv\Scripts\b2.exe inbox --legacy-docupipe --inbox .\inbox --out .\outputs\legacy_docupipe_run` |
| Table maps | `.\.venv\Scripts\b2.exe discover` |
| Legacy sample fill | `.\.venv\Scripts\b2.exe fill-b24-rl1-sample` |

## Project layout

- `src/` main source package
- `tests/` pytest test suite
- `scripts/` runnable utilities
- `inputs/` scanned evidence inputs, gitignored
- `outputs/` generated artifacts, gitignored
- `templates/` DOCX form templates
- `schemas/` template maps and extraction schemas
- `salvage/` old-tool reference material only
