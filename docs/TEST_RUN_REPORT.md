# End-to-End Test Run Report

Date: 2026-05-11 (UTC)

## What was executed

- `pytest -q --basetemp .pytest-tmp`
- `PYTHONPATH=src python -m b2_automation.cli --help`
- `PYTHONPATH=src python -m b2_automation.cli demo`
- `PYTHONPATH=src python -m b2_automation.cli sample-pipeline`
- `PYTHONPATH=src python -m b2_automation.cli discover`
- `PYTHONPATH=src python -m b2_automation.cli inbox --inbox <temp>/inbox --out <temp>/run`

## Results

- Automated test suite passed (`78 passed`).
- CLI commands for help/demo/sample-pipeline/discover succeeded.
- Local inbox pipeline completed with `status: success`.
- Filled DOCX files were produced for all first-class forms:
  - `B24_RL2_filled.docx`
  - `B81_filled.docx`
  - `B89_filled.docx`
  - `B90_filled.docx`
  - `Cover_Page_filled.docx`
- Manifest showed `structure_guard_passed: true` and no blocked forms.

## Environment note

- `pip install -e '.[dev]'` failed in this environment due unavailable package index access (proxy tunnel 403).
- Existing environment already had sufficient dependencies to run tests and CLI validation.
