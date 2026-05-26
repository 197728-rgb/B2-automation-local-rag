# SPEC-1 Local MVP Operational Status

Canonical **operational** description for the autonomous evidence-to-DOCX pipeline in **B2-automation-local-rag** (personal laptop / Cursor). This document is the short source of truth for how to run and what paths to expect.

**Full personal specification (design + requirements + status):** [SPEC-1-PERSONAL.md](SPEC-1-PERSONAL.md)

For the default local-first inbox path (approval maps + review artifacts), see [README.md](../README.md) and [`.cursor/rules/local-automation.mdc`](../.cursor/rules/local-automation.mdc).

---

## Status

**SPEC-1 MVP is fully implemented, tested, and deployable** as an autonomous evidence-to-DOCX engine. v1.1 items below are enhancements, not prerequisites for deployment.

| Dimension | State |
|-----------|--------|
| Architecture | Complete |
| Production code | Complete |
| Testing | 132 passing tests |
| Documentation | This file + README + AGENTS.md |
| Persistence | JSON audit trail; optional SQLite |
| Autonomous execution | `b2 run-autonomous` |
| TypeScript reference | `tools/autonomous-audit-pipeline/` |

Last verified test run:

```text
132 passed in 22.88s
```

---

## Entry point

```powershell
pip install -e ".[autonomous]"
b2 run-autonomous --inbox .\inbox --out .\outputs\autonomous_run
```

| Flag | Effect |
|------|--------|
| `--no-llm` | Analyst uses deterministic blank-cell + manifest mapping; no Gemini/Anthropic calls (CI, air-gapped, cost-free runs). |
| `--no-sqlite` | Skip `autonomous.db`; JSON audit trail still written. |
| `--templates B24_RL2 B81 ...` | Subset of forms (default: all `DEFAULT_REVIEW_FORMS`). |

Optional: set `GEMINI_API_KEY` (and `LLM_PROVIDER=google`) for richer Analyst/Writer behavior. Not required with `--no-llm`.

Implementation: [`src/b2_automation/cli.py`](../src/b2_automation/cli.py) (`run-autonomous` subcommand).

---

## Pipeline (five stages)

```text
analyzeDocxForm
  -> gatherEvidence
  -> synthesizeAnswer
  -> validateAnswer
  -> writeCompletedDocx
```

Orchestration: [`src/b2_automation/autonomous_pipeline.py`](../src/b2_automation/autonomous_pipeline.py).

| Stage | Python modules |
|-------|----------------|
| analyzeDocxForm | [`analyst_agent.py`](../src/b2_automation/analyst_agent.py), [`docx_structure.py`](../src/b2_automation/docx_structure.py), [`schema_catalog.py`](../src/b2_automation/schema_catalog.py) |
| gatherEvidence | [`investigator_agent.py`](../src/b2_automation/investigator_agent.py) (local extraction + retrieval) |
| synthesizeAnswer | [`writer_agent.py`](../src/b2_automation/writer_agent.py) |
| validateAnswer | [`validation_gate.py`](../src/b2_automation/validation_gate.py) (deterministic only) |
| writeCompletedDocx | [`form_writer.py`](../src/b2_automation/form_writer.py) → [`ooxml_writer.patch_docx_cells`](../src/b2_automation/ooxml_writer.py) |

TypeScript reference (contract parity): [`tools/autonomous-audit-pipeline/`](../tools/autonomous-audit-pipeline/).

---

## Write authority

Autonomous runs use **`machine_field_map.v1`** as the sole write authority—not hand-maintained `schemas/maps/*.json` approval maps.

- Contract types: [`autonomous_contracts.py`](../src/b2_automation/autonomous_contracts.py)
- JSON Schema: [`schemas/contracts/machineFieldMap.v1.schema.json`](../schemas/contracts/machineFieldMap.v1.schema.json)
- DOCX coordinates come from **python-docx** ([`docx_structure.py`](../src/b2_automation/docx_structure.py)); Mammoth HTML is semantic context only for optional LLM Analyst calls.

`patch_docx_cells` is invoked with `approval_map=None` and `strict_approval_coverage=False`. Structure guard ([`build_structure_guard`](../src/b2_automation/ooxml_writer.py)) still runs before treating output as structurally safe.

---

## Output layout (authoritative)

Per form processed, under `--out` (e.g. `outputs/autonomous_run/`):

```text
outputs/autonomous_run/
  <form_id>/
    completed/
      <template_stem>_completed.docx
    audit-trail/
      <stem>_machine_field_map.v1.json
      <stem>_evidence.json
      <stem>_answers.json
      <stem>_write_report.json
    structure_guard_report.json          # when produced for that form run
  run_manifest.json                      # run-level status + metadata
  autonomous.db                          # only if SQLite enabled (default on)
```

**Not** produced in autonomous mode:

- `review.json`
- `review.md`
- Human-review-only handoff artifacts

Run terminal status values: `completed`, `completed_with_warnings`, or `failed_with_fallback`—not `review_required`.

Benchmark helper (manifest summary only): [`scripts/benchmark_autonomous.py`](../scripts/benchmark_autonomous.py).

---

## Batch behavior

`run-autonomous` already processes multiple templates unattended:

- Iterates [`DEFAULT_REVIEW_FORMS`](../src/b2_automation/local_extraction.py) (`B24_RL2`, `B81`, `B89`, `B90`, `Cover_Page`)
- Resolves matching `.docx` under `templates/`
- Skips forms with no template file (no hard failure)

---

## Deployment requirements

1. **Blank templates** in `templates/` (e.g. `B24 (RL2).docx` / `B24_RL2.docx` per repo layout).
2. **Evidence** in `--inbox` (PDF, TXT, DOCX, etc.—see `LOCAL_EVIDENCE_EXTENSIONS`).
3. **Optional** `GEMINI_API_KEY` unless using `--no-llm`.

---

## Autonomous vs local inbox

| | Local inbox (`b2 inbox`) | Autonomous (`b2 run-autonomous`) |
|--|--------------------------|----------------------------------|
| Write authority | Exact `schemas/maps/*.json` | `machine_field_map.v1` |
| Field discovery | Approval maps + `b2 discover` | Analyst Agent |
| Missing evidence | `REVIEW_REQUIRED` markers in DOCX | Fallback text; no review gate |
| Artifacts | `review.json`, `review.md`, packets | `audit-trail/*.json`, `run_manifest.json` |
| DocuPipe | Not default | Optional accelerator |

---

## MVP boundaries

### In scope (shipped)

- Autonomous end-to-end form completion
- Local RAG evidence retrieval
- Deterministic validation and fallback
- DOCX OOXML patching
- JSON audit trail + optional SQLite ([`run_store.py`](../src/b2_automation/run_store.py))
- Multi-template batch via `run-autonomous`
- TypeScript reference pipeline

### Out of scope (v1.1+ roadmap—not blockers)

- Gold benchmark datasets and acceptance-metric automation
- Per-stage token and cost telemetry
- Template fingerprinting / layout-change detection
- Confidence dashboard
- Excel forms
- External regulator or customer submission
- Multi-tenant deployment

---

## Tests

```powershell
.\.venv\Scripts\python.exe -m pytest -q --basetemp .pytest-tmp
```

Autonomous-specific: [`tests/test_autonomous_pipeline.py`](../tests/test_autonomous_pipeline.py) (contracts, Analyst, Investigator, Writer, validation, E2E DOCX patch).

---

## Related docs

- [SPEC-1-PERSONAL.md](SPEC-1-PERSONAL.md) — full personal SPEC (background, requirements, method, milestones)
- [README.md](../README.md) — install and quick start
- [AGENTS.md](../AGENTS.md) — agent guardrails including autonomous mode
- [`.cursor/rules/local-automation.mdc`](../.cursor/rules/local-automation.mdc) — Cursor rules (local inbox + autonomous exception)

---

## Version note

This document describes the **local MVP** as implemented in-repo. Release labeling (v1.0 / v1.1) is product packaging; the codebase capability above constitutes deployable SPEC-1 MVP regardless of tag name.
