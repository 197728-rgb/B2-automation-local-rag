# B2 Automation Local RAG

Local AAR audit evidence review for B-2 DOCX objective evidence forms.

The default workflow does not require paid APIs or DocuPipe credentials.

## Default pipeline

```text
inbox local files
-> local text/PDF extraction
-> local retrieval and form-scoped evidence packets
-> review JSON and Markdown
-> rag_selection_report.json
-> exact approval maps
-> safe raw OOXML DOCX patching when maps are available
```

First-class review forms:

- `B24_RL2`
- `B81`
- `B89`
- `B90`
- `Cover_Page`

## Install locally

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\b2.exe --help
```

For scanned/image PDFs, install the Tesseract OCR engine on Windows and make sure `tesseract.exe` is on `PATH`. The Python OCR dependencies are installed with the project, but the OCR engine itself is a system dependency.

## Verified source handoff

A clean source handoff archive is complete when it contains the project source, tests, schemas/maps, templates, scripts, docs, and workflow files, but excludes local/runtime state such as `.git/`, `.venv/`, `inbox/`, `outputs/`, `.env*`, and pytest temp folders. A verified handoff should install from a fresh extraction, report `b2 0.1.0`, pass the full pytest suite, and run `b2 inbox` against a local inbox to generate the five filled DOCX files for `B24_RL2`, `B81`, `B89`, `B90`, and `Cover_Page`.

`inbox/` is intentionally gitignored. Each user supplies their own evidence files locally; PDF and ZIP evidence in `inbox/` is supported at runtime but is not part of the source handoff.

## Run the local inbox command

```powershell
New-Item -ItemType Directory -Force .\inbox | Out-Null
# Put .pdf, .zip, .txt, .md, .json, or .csv evidence files in .\inbox
.\.venv\Scripts\b2.exe inbox --inbox .\inbox --out .\outputs\local_rag_run
```

Expected outputs:

```text
outputs/local_rag_run/run_manifest.json
outputs/local_rag_run/rag_selection_report.json
outputs/local_rag_run/raw/*.ocr.json
outputs/local_rag_run/raw/*.metadata.json
outputs/local_rag_run/raw/*.chunks.json
outputs/local_rag_run/raw/local_rag_retrieval.json
outputs/local_rag_run/review/local_rag_review.json
outputs/local_rag_run/review/local_rag_review.md
outputs/local_rag_run/review/*_evidence_packet.json
outputs/local_rag_run/review/*_review.md
```

The inbox command **fills the best extracted value** per approved cell and inserts **`REVIEW_REQUIRED:` text markers** into the DOCX for required map fields that still lack evidence. The run is **`review_required`** when those **manual markers** remain (see `manual_fields` in `run_manifest.json`) or when the **structure guard** fails; it is **`success`** only when there are no manual follow-ups and the guard passes. Filled outputs live under **`<out>/filled/`** (for example `outputs/local_rag_run/filled/`), not a repo-wide `outputs/filled/` folder.

## Autonomous pipeline (SPEC-1)

**Operational source of truth:** [docs/SPEC-1-LOCAL-MVP.md](docs/SPEC-1-LOCAL-MVP.md) · **Full personal spec:** [docs/SPEC-1-PERSONAL.md](docs/SPEC-1-PERSONAL.md)

Fully autonomous form completion without human-review gates:

```text
analyzeDocxForm -> gatherEvidence -> synthesizeAnswer -> validateAnswer -> writeCompletedDocx
```

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[autonomous]"
$env:GEMINI_API_KEY = "your-key"   # optional; use --no-llm for deterministic Analyst only
.\.venv\Scripts\b2.exe run-autonomous --inbox .\inbox --out .\outputs\autonomous_run
```

Outputs under `outputs/autonomous_run/`:

- `completed/*_completed.docx`
- `audit-trail/*_machine_field_map.v1.json`, `*_evidence.json`, `*_answers.json`, `*_write_report.json`
- `run_manifest.json` (status: `completed`, `completed_with_warnings`, or `failed_with_fallback`)

TypeScript reference implementation: `tools/autonomous-audit-pipeline/`.

## Other commands

```powershell
.\.venv\Scripts\b2.exe discover
.\.venv\Scripts\b2.exe demo
.\.venv\Scripts\b2.exe sample-pipeline
```

## Safety rules

- Local retrieval may suggest evidence values and cite sources.
- Retrieval cannot authorize writable DOCX cells.
- Only exact approval maps can authorize DOCX writes.
- Do not use generic, nearest, latest, or similar approval maps.
- Do not hand off a filled DOCX unless `structure_guard_report.json` passes.
- Keep conflicts, missing values, and low-confidence values in review artifacts.
- Keep raw extraction and metadata artifacts for traceability.
