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

`B24_RL1` remains legacy/sample coverage only.

## Install locally

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\b2.exe --help
```

## Run the local inbox command

```powershell
New-Item -ItemType Directory -Force .\inbox | Out-Null
# Put .pdf, .txt, .md, .json, or .csv evidence files in .\inbox
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

The local inbox command is review-first. It does not fill DOCX files unless an exact per-form/version approval map and safe raw OOXML patch step are added for that form.

## Legacy DocuPipe adapter

DocuPipe is not part of the default workflow. Use it only when explicitly required:

```powershell
$env:B2_DOCUPIPE_STUB="1"
$env:B2_DOCUPIPE_FIXTURE=(Resolve-Path .\samples\docupipe\realistic_b24_response.json)
.\.venv\Scripts\b2.exe inbox --legacy-docupipe --inbox .\inbox --out .\outputs\legacy_docupipe_run
```

Live DocuPipe mode never falls back to fixture data. Missing credentials fail immediately.

## Other commands

```powershell
.\.venv\Scripts\b2.exe discover
.\.venv\Scripts\b2.exe demo
.\.venv\Scripts\b2.exe sample-pipeline
.\.venv\Scripts\b2.exe fill-b24-rl1-sample
.\.venv\Scripts\b2.exe fill-b24-rl1-from-docupipe
```

## Safety rules

- Local retrieval may suggest evidence values and cite sources.
- Retrieval cannot authorize writable DOCX cells.
- Only exact approval maps can authorize DOCX writes.
- Do not use generic, nearest, latest, or similar approval maps.
- Do not hand off a filled DOCX unless `structure_guard_report.json` passes.
- Keep conflicts, missing values, and low-confidence values in review artifacts.
- Keep raw extraction and metadata artifacts for traceability.
- DocuPipe is legacy-only and must be explicitly requested.
