# B2 SENTINEL v2 — Final Verification Manifest

**Build date:** 2026-05-26
**Version:** 1.1.0 (ontology + required-policy + PDF outbox + write authority)

## Test Results

| Check | Result |
|-------|--------|
| `pytest` (full suite) | **64 passed** |
| Template wiring validator | **49 / 49 OK** |
| B85 required_total | **61** (structure guard passed) |
| C5H_Heater_Systems_Test_Fixture required_total | **116** (structure guard passed) |
| C6i_Installation_of_Service_Equipment_512026 required_total | **100** (structure guard passed) |
| Invalid form `B19` | **Rejected** before output creation |
| Short code `C5H` | **Rejected** with suggestion: C5H_Heater_Systems_Test_Fixture |
| Short code `C6I` | **Rejected** with suggestion: C6i_Installation_of_Service_Equipment_512026 |
| B89 run (success) | **Passed** — DOCX filled, all audit artifacts in logs/ |
| PDF-only outbox contract | **Enforced** — empty outbox when PDF export unavailable |
| Errors separation | **Confirmed** — runtime errors written to errors/ only |
| Cross-form ontology | **Operational** — detects value inconsistencies across forms |

## Output Contract

```
outbox/                     → final filled B-2 PDFs only
logs/<run_id>/<form_id>/    → DOCX + all audit/traceability artifacts
errors/<run_id>/<form_id>/  → runtime failure records
```

### PDF behavior

- Successful form → `outbox/<form>_filled.pdf`
- Failed/blocked form → not published to outbox
- Complete package (all selected + Cover_Page succeed) → `outbox/B2_COMPLETE_PACKET.pdf`

## Architecture Layers

1. **Layer 1 — Form Brain**: Obligation graph, approval maps, alias brain, required-cell policy, write authority
2. **Layer 2 — Evidence Hunter**: Wave 1 (collect), Wave 2 (normalize + alias resolve), Wave 3 (targeted extract)
3. **Layer 3 — Decision Engine**: Conflict resolution, value-type sanity gate, confidence scoring
4. **Layer 4 — Fill Engine**: DOCX cell writing with structure guard
5. **Layer 5 — Cognitive Orchestration**: Pluggable LLM adapters (Anthropic, OpenAI, Azure) with graceful degradation
6. **Layer 6 — Global Field Ontology**: Canonical field registry, cross-form consistency enforcement
7. **Layer 7 — Required Policy**: Activity-based required-cell obligations, honest completion scoring
8. **Layer 8 — Audit Packet**: Run manifest, PDF outbox, logs/errors separation, complete packet merge

## How to Run

```bash
# Install
pip install -e .

# Full pipeline (deterministic mode)
python run.py --no-cognitive run

# Single form
python run.py --no-cognitive run --form B89

# With cognitive layer (requires API key in b2-sentinel.yaml)
python run.py run

# Tests
pytest

# Ontology stats
python run.py ontology --stats

# Template wiring validation
python scripts/validate_template_wiring.py
```

## Requirements

- Python 3.10+
- LibreOffice/soffice (for PDF export)
- PyMuPDF (for PDF merge into complete packet)
- Optional: `pip install -e ".[cognitive]"` for LLM adapters

## Exclusions from this archive

- `outputs/`, `logs/`, `errors/`, `outbox/` (generated run artifacts)
- `__pycache__/`, `.pytest_cache/`
- `.env*` files
- Temporary debug scripts (`extract_diagnostic.py`, `verify_extraction.py`, `_check.py`)
