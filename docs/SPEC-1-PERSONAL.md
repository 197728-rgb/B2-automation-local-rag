# SPEC-1 Personal Autonomous Auditor Form Completion Pipeline

Full specification for a **personal, local** AI-assisted audit form workflow on the owner's laptop with Cursor and [`B2-automation-local-rag`](../README.md).

**Quick operational status (canonical):** [SPEC-1-LOCAL-MVP.md](SPEC-1-LOCAL-MVP.md)

This document is the design + implementation record. It is **not** framed as public SaaS, enterprise deployment, or commercial production.

---

## Background

Organizations performing audits often need to complete complex forms using evidence scattered across source PDFs, reports, tables, Word documents, and supporting files. Traditional keyword search or simple extraction is insufficient because audit templates may contain merged headers, nested table structures, implicit questions, and fields whose meaning depends on surrounding context.

The uploaded M-1002 Exhibit B-2 package is primarily DOCX-based rather than PDF-only. The C10 repair-of-interior-coatings template includes narrative instructions plus multiple structured tables, including equipment owner permission, design control, materials, documents, personnel, NDT personnel, measurement/test equipment, and quality records.

The system is a **personal, local** AI-assisted workflow. It analyzes a blank audit template, finds supporting evidence, synthesizes answers, validates outputs, and writes the completed form **without manual approval during normal operation**.

Five core stages:

1. **Analyst Agent** — blank form layout, requirements, field locations, DocuPipe schema mapping, search directives.
2. **Investigator Agent** — semantic evidence search with citations.
3. **Writer Agent** — professional audit-form answers.
4. **Validation Gate** — deterministic confidence, citation, formatting, fallback rules.
5. **Form Writer** — completed DOCX + machine-readable audit trail.

When evidence is weak, missing, contradictory, or mapping confidence is low, the system applies **deterministic fallbacks**—not human review stops.

---

## Requirements

### Must Have

- Blank audit forms: DOCX (first-class), PDF, or page image arrays.
- DOCX table extraction: merged cells, labels, units, instructions, blank cells.
- **`machine_field_map.v1`** replaces/supplements `b2 discover` `*_table_map.txt`.
- Per field: write location, intent, `mappedSchemaPath`, answer type, confidence, fallback, `canAutoFill`.
- Evidence folder (PDF + DOCX); semantic search (not keyword-only).
- Professional answers + citations + confidence for every field.
- Automatic validation (schema, citations, units, coordinates, thresholds).
- **No** manual approval or review prompts in normal runs.
- Completed output copy + JSON audit trail.

### Should Have

- Evidence metadata (source, page/section, snippet, authority score).
- Narrative / number / date / boolean / table answer types.
- Low-confidence flagged in metadata; run still completes.
- Document cache between runs.
- Configurable source authority on conflicts.
- TypeScript reference + Python local implementation.

### Could Have

- Excel forms; dashboard; batch all M-1002 templates; PDF export; external submission (later).

### Won't Have (MVP)

- External regulator/customer portal submission.
- Legal/regulatory certification beyond evidence-backed output.
- Multi-user workflow or required human-review artifacts.

---

## Method

### Pipeline contract

```text
analyzeDocxForm
  -> gatherEvidence
  -> synthesizeAnswer
  -> validateAnswer
  -> writeCompletedDocx
```

**Write authority:** `machine_field_map.v1` + validated answers (not static approval maps in autonomous mode).

### TypeScript reference modules

`tools/autonomous-audit-pipeline/`:

1. `docxFormExtractor.ts`
2. `analystAgent.ts`
3. `investigatorAgent.ts`
4. `writerAgent.ts`
5. `validationGate.ts`
6. `formWriter.ts`
7. `mainPipeline.ts`
8. `llmClient.ts` (provider-neutral: Gemini, Claude, …)

**DOCX coordinates:** OpenXML / `python-docx` authoritative; Mammoth HTML semantic-only for optional LLM Analyst.

### Core data contracts

See [`schemas/contracts/machineFieldMap.v1.schema.json`](../schemas/contracts/machineFieldMap.v1.schema.json) and [`src/b2_automation/autonomous_contracts.py`](../src/b2_automation/autonomous_contracts.py).

Key types: `AuditRequirement`, `MachineFieldMapV1`, `EvidenceBundle`, `EvidenceItem`, `SynthesizedAnswer`, `AutomationStatus`.

### Python local mapping

| Stage | Python |
|-------|--------|
| analyzeDocxForm | `analyst_agent.py`, `docx_structure.py`, `schema_catalog.py` |
| gatherEvidence | `investigator_agent.py` + `local_extraction` |
| synthesizeAnswer | `writer_agent.py` |
| validateAnswer | `validation_gate.py` |
| writeCompletedDocx | `form_writer.py` → `patch_docx_cells` |

**Command:**

```bash
pip install -e ".[autonomous]"
b2 run-autonomous --inbox ./inbox --out ./outputs/autonomous_run
```

**Autonomous rules:**

- `machine_field_map.v1` is write authority.
- No final `REVIEW_REQUIRED` markers.
- Terminal status: `completed`, `completed_with_warnings`, or `failed_with_fallback`.
- See [`.cursor/rules/local-automation.mdc`](../.cursor/rules/local-automation.mdc) autonomous section.

### Validation gate (deterministic)

| Condition | Action | Status |
|-----------|--------|--------|
| High confidence + citations | Fill normally | `completed` |
| Medium confidence | Fill + metadata | `completed_with_low_confidence` |
| Missing evidence | `Not verified in provided source documents.` | `completed_with_missing_evidence` |
| Contradiction | Authority/recency wins | `completed_with_conflict_resolution` |
| Model failure | Fallback text | `failed_with_fallback` |
| Low mapping confidence | Honor `canAutoFill` / `fallbackBehavior` | per policy |
| Required numeric, no value | `N/A - not verified...` or blank | per policy |

---

## Current implementation status (canonical)

The repo contains a **fully implemented** autonomous MVP for personal laptop + Cursor use.

| Item | State |
|------|--------|
| `b2 run-autonomous` | Implemented |
| `machine_field_map.v1` write authority | Implemented |
| Five-stage pipeline | [`autonomous_pipeline.py`](../src/b2_automation/autonomous_pipeline.py) |
| Tests | **132 passed** |
| Ops quick reference | [SPEC-1-LOCAL-MVP.md](SPEC-1-LOCAL-MVP.md) |

### Authoritative output layout

Per template under `--out`:

```text
outputs/autonomous_run/
  <form_id>/
    completed/<stem>_completed.docx
    audit-trail/<stem>_machine_field_map.v1.json
    audit-trail/<stem>_evidence.json
    audit-trail/<stem>_answers.json
    audit-trail/<stem>_write_report.json
  run_manifest.json
  autonomous.db                    # optional; --no-sqlite to skip
```

**Not produced:** `review.json`, `review.md`.

### CLI flags

- `--no-llm` — deterministic Analyst; no API key required.
- `--no-sqlite` — JSON only.
- `--templates B24_RL2 B81` — subset of forms.

### Batch behavior

Iterates `DEFAULT_REVIEW_FORMS`; processes matching `templates/*.docx`; skips missing templates.

### Modules

| Module | Role |
|--------|------|
| `autonomous_contracts.py` | SPEC contracts |
| `schema_catalog.py` | DocuPipe paths |
| `docx_structure.py` | Authoritative coordinates |
| `analyst_agent.py` | `machine_field_map.v1` |
| `investigator_agent.py` | Local RAG evidence |
| `writer_agent.py` | Answers (no review markers) |
| `validation_gate.py` | Deterministic fallback |
| `form_writer.py` | OOXML patch |
| `autonomous_pipeline.py` | Orchestrator |
| `run_store.py` | Optional SQLite |

### MVP boundaries

**In scope:** autonomous completion, RAG, fallback, DOCX write, audit trail, batch, TS reference.

**v1.1+ (not blockers):** gold benchmarks, token/cost telemetry, template fingerprinting, dashboard, Excel, external submission.

---

## Milestones

| # | Milestone | Status |
|---|-----------|--------|
| M1 | Scaffold (types, schema, llmClient) | Done |
| M2 | DOCX extraction | Done |
| M3 | `machine_field_map.v1` | Done |
| M4 | Analyst on M-1002 samples | Done |
| M5 | Evidence extraction | Done |
| M6 | `EvidenceBundle` | Done |
| M7 | `SynthesizedAnswer` | Done |
| M8 | Validation gate | Done |
| M9 | Completed DOCX | Done |
| M10 | Batch `run-autonomous` | Done |

---

## Gathering results (evaluation)

Metrics for local benchmark datasets (gold data for **testing only**, not production gates):

- Field detection recall (target ≥ 90%)
- Schema mapping accuracy (≥ 85%)
- Write-location accuracy (≥ 95%)
- Citation accuracy (≥ 85%)
- Autonomous completion rate (≥ 95%)
- DOCX write success (≥ 95%)
- Low-evidence fields: 100% fallback, no fabricated claims

Helper: [`scripts/benchmark_autonomous.py`](../scripts/benchmark_autonomous.py).

---

## Recommended v1.1 priorities

1. Gold benchmark dataset per activity code.
2. Per-stage token and cost telemetry.
3. Template fingerprinting.
4. Confidence dashboard.
5. Expanded metrics reporting.

---

## Personal use note

This spec is for the owner's **personal laptop workflow** with Cursor and `B2-automation-local-rag`. Enhancements above are optional; the MVP is usable locally today.

---

## Related documentation

- [SPEC-1-LOCAL-MVP.md](SPEC-1-LOCAL-MVP.md) — operational source of truth (short)
- [README.md](../README.md) — install and commands
- [AGENTS.md](../AGENTS.md) — agent guardrails
- [tools/autonomous-audit-pipeline/](../tools/autonomous-audit-pipeline/) — TypeScript reference
