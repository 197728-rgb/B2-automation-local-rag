# B2 SENTINEL — Closed-Loop Compliance Intelligence System

A deterministic, rule-driven Python system that processes B-2 form compliance for tank car inspection and qualification. It understands forms, hunts evidence in waves, writes only authorized cells, validates itself independently, accounts for every blocker, and **refuses fake completion**.

## 60-Second Quickstart

```bash
pip install -r requirements.txt
python run.py
```

That's it. The system processes all 5 active forms against `inbox/`, writes filled DOCX and audit artifacts to `outputs/<timestamp>/`.

### Target a single form

```bash
python run.py run --form B89
```

### Discover available forms

```bash
python run.py discover
```

### Re-run the Completion Judge on a previous output

```bash
python run.py judge outputs/<run_id>/B89
```

---

## Architecture — 8 Layers, 3 Agents, 7 Innovations

```
┌─────────────────────────────────────────────────────────┐
│  Agent 1: Regulatory Analyst                            │
│  ┌─────────────────────────────────────────────────┐    │
│  │ Layer 1: Form Brain                             │    │
│  │ Obligation Graph + Write Authority + Completion │    │
│  └─────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────┐
│  Agent 2: Forensic Investigator                         │
│  ┌─────────────────────────────────────────────────┐    │
│  │ Layer 2: Evidence Hunter                        │    │
│  │ Wave 1: Collect → Wave 2: Normalize →           │    │
│  │ Wave 3: Targeted → Wave 4: Contamination Defense│    │
│  └─────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────┐
│  Agent 3: Controlled Writer / Judge                     │
│  ┌──────────┐ ┌──────────┐ ┌───────────┐ ┌─────────┐  │
│  │ Layer 3  │ │ Layer 4  │ │ Layer 5   │ │ Layer 6 │  │
│  │ Decision │→│ Writer   │→│ Structure │→│ Judge   │  │
│  │ Engine   │ │ (OOXML)  │ │ Guard     │ │         │  │
│  └──────────┘ └──────────┘ └───────────┘ └─────────┘  │
│  ┌───────────────────────┐                              │
│  │ Layer 7: N/A Engine   │                              │
│  └───────────────────────┘                              │
└─────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────┐
│  Layer 8: Audit Packet Generator                        │
│  15 artifacts per form + run manifest                   │
└─────────────────────────────────────────────────────────┘
```

### The 8-State Decision Matrix

| Evidence | Map authorizes | Required | N/A approved | State |
|---|---|---|---|---|
| yes | yes | any | n/a | `FILL` |
| yes | no | any | n/a | `BLOCKED_UNAUTHORIZED` |
| no | yes | yes | yes | `APPROVED_NA` |
| no | yes | yes | no | `BLOCKED_NO_SOURCE` |
| no | yes | no | n/a | `OPTIONAL_BLANK` |
| weak | yes | yes | n/a | `LOW_CONFIDENCE` |
| multiple | yes | any | n/a | `CONFLICT` |
| no | yes | yes | manual ok | `REVIEW_REQUIRED` |

### 7 Innovations

1. **Evidence Debt Accounting** — every blocker gets a resolution path
2. **Rollover Memory** — compares prior B-2 packet values for safe reuse
3. **Semantic Alias Brain** — governed, directional field aliases
4. **5-Axis Confidence** — retrieval, extraction, authorization, write, completion
5. **Auditor-Grade Explainability** — per-field plain-English rationale
6. **Self-Critique Loop** — re-reads its own output and catches discrepancies
7. **Run-to-Run Intelligence** — tracks progress across multiple executions

---

## Cognitive Layer Boundary

LLMs may:

- interpret evidence meaning
- propose semantic aliases
- judge ambiguity
- synthesize source fragments
- critique completed outputs

LLMs may not:

- authorize DOCX write locations
- bypass approval maps
- mark N/A without policy
- override the structure guard
- declare completion without validator pass

Default mode is deterministic-only (`cognitive.enabled: false`, `adapter: "null"`). Enable the cognitive layer explicitly with `--cognitive` or by changing `b2-sentinel.yaml`. Missing provider SDKs, keys, endpoints, or API failures degrade to deterministic mode instead of crashing the run.

---

## What It Refuses To Do

This is the core promise:

- **Never writes an unauthorized cell.** Only exact approval-map coordinates are writable.
- **Never silently marks N/A.** Only approved exception policy justifies N/A.
- **Never claims completion when blocked.** If any required field lacks evidence or authorization, the report says so.
- **Never corrupts document structure.** The Structure Guard discards any DOCX that lost tables, rows, or cells.
- **Never fills from wrong-form evidence.** Cross-form contamination defense quarantines out-of-scope data.
- **Never hides a conflict.** Multiple values for one field triggers CONFLICT state, not silent pick.

---

## Output Artifacts

Each run produces `outputs/<run_id>/<form_id>/` (15 artifacts per form) plus a top-level `run_manifest.json`:

| File | Description |
|---|---|
| `<form>_filled.docx` | Filled form (only authorized cells) |
| `review.json` / `review.md` | Human-readable review |
| `field_traceability.json` | Field → source → page → chunk → confidence |
| `source_evidence_index.json` | All source files processed |
| `missing_required_fields.json` | Fields still unfilled |
| `conflicts.json` | Fields with multiple competing values |
| `low_confidence.json` | Fields below write-confidence threshold |
| `structure_guard_report.json` | Blank vs filled structural comparison |
| `completion_report.json` | Final pass/fail with format + completion bits |
| `manual_correction_log.json` | Any controlled text replacements |
| `na_exception_log.json` | Approved N/A exceptions with policy refs |
| `evidence_debt_ledger.json` | Blocking fields + resolution paths |
| `rollover_decisions.json` | Prior-value reuse classifications |
| `run_delta.json` | Progress vs previous run |

Top-level: `outputs/<run_id>/run_manifest.json` — all form statuses + artifact paths.

---

## How To Extend

### Add a new form

1. Drop the blank DOCX template into `templates/<FORM_ID>.docx`
2. Create approval map: `schemas/maps/<FORM_ID>.json`
3. (Optional) Add N/A policy: `schemas/na_policy/<FORM_ID>.json`
4. Add form ID to `ACTIVE_FORMS` in `src/b2_sentinel/core/paths.py`
5. Run: `python run.py run --form <FORM_ID>`

### Add an alias rule

Edit `schemas/alias_rules/global_aliases.json` and add:

```json
{
  "from": "your_alias_name",
  "to": "target.field_id",
  "direction": "write_bridge",
  "forms": ["B89", "B81"],
  "risk": "low",
  "authority": "approved_alias_rule"
}
```

### Approve an N/A exception

Edit `schemas/na_policy/<FORM_ID>.json`:

```json
{
  "field_id_here": {
    "reason": "Clear rationale why this field is N/A",
    "policy_id": "NA-FORM-FIELD-001",
    "approved_by": "approved_exception_policy"
  }
}
```

---

## Project Structure

```
b2-sentinel/
├── src/b2_sentinel/
│   ├── core/              # Pydantic models, enums, paths
│   ├── layer1_form_brain/ # Obligation graph, write authority
│   ├── layer2_evidence_hunter/ # 4-wave evidence pipeline
│   ├── layer3_decision_engine/ # 8-state decision matrix
│   ├── layer4_controlled_writer/ # OOXML patcher
│   ├── layer5_structure_guard/  # Document integrity check
│   ├── layer6_completion_judge/ # Independent validation
│   ├── layer7_exception_engine/ # N/A workflow
│   ├── layer8_audit_packet/     # 15 audit artifacts
│   ├── innovations/       # Debt, rollover, aliases, run delta
│   ├── agents/            # 3 orchestrator agents
│   ├── pipeline.py        # Top-level orchestrator
│   └── cli.py             # CLI commands
├── templates/             # Blank DOCX forms
├── schemas/               # Approval maps, alias rules, N/A policy
├── inbox/                 # Evidence files (PDFs, JSONs)
├── outputs/               # Generated at runtime
└── tests/                 # pytest suite
```

---

## Running Tests

```bash
pip install -r requirements.txt
pytest -q
```

---

## Requirements

- Python 3.10+
- Dependencies: pydantic, lxml, pdfplumber, PyMuPDF, python-docx, scikit-learn, click, rich, jsonschema

All specified in `requirements.txt` with pinned versions.
