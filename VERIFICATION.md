# Verification Report

Historical verification notes for the uploaded `B2-automation-local-rag-main.zip`.

Current validation: run the commands in the repo README / CI (pytest, `b2 --version`, `b2 inbox --help`, and a small local inbox dry run). Test counts change as the suite grows.

## Example results (snapshot)

```text
Install: passed
Tests: (run `pytest -q` for current count)
Version: b2 0.1.0
Inbox help: passed
Local inbox run: passed
```

## Default `b2 inbox` Behavior

```text
DocuPipe is NOT default
Default forms:
B24_RL2
B81
B89
B90
Cover_Page
```

## Local Run Outputs

```text
run_manifest.json
rag_selection_report.json
raw/*.ocr.json
raw/*.metadata.json
raw/*.chunks.json
raw/local_rag_retrieval.json
review/local_rag_review.json
review/local_rag_review.md
review/B24_RL2_evidence_packet.json
review/B81_evidence_packet.json
review/B89_evidence_packet.json
review/B90_evidence_packet.json
review/Cover_Page_evidence_packet.json
review/*_review.md
```

## Command Equivalent

```powershell
gh repo clone 197728-rgb/B2-automation-local-rag
cd B2-automation-local-rag

python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest -q --basetemp .pytest-tmp
.\.venv\Scripts\b2.exe --version
.\.venv\Scripts\b2.exe inbox --help
```

## Status

```text
Local-RAG baseline: verified
DocuPipe default dependency: removed
All-form review path: working
DOCX fill handoff: correctly blocked until approval maps / structure guard pass
```
