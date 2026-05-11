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

The local inbox command is review-first when evidence is missing or guarded. When exact per-form approval maps and templates exist, it may emit filled DOCX under the run’s `filled/` directory only if the structure guard passes.

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
