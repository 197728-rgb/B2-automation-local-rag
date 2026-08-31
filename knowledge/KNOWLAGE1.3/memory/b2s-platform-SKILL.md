---
name: b2s-platform
description: >
  Expert knowledge of the B2S Enterprise Compliance Platform — a tool that reads tank car
  inspection evidence (PDFs, photos, scanned forms) and automatically fills out B-2 forms
  for AAR M-1002 / Appendix L regulatory compliance. Also covers the Best Tools Bundle:
  three standalone scripts for extracting text from any file (Tool 01), finding missing
  template fields (Tool 02), and autofilling DOCX templates from evidence (Tool 03).
  Use this skill whenever the user mentions B2S, the auditor dashboard, activity codes
  (C5V, C5S, C5I, C6R, C7, C8, C10), LAUNCH_AUDITOR, fix_platform, platform_launcher,
  evidence folders, DOCX forms, compliance validation, missing fields, autofill, extract
  everything, best tools bundle, SOP, SOP.zip, field registry, canonical fields, or any
  of the three bundle scripts. Also trigger for setup errors, crash messages, missing
  files, or questions about running, deploying, fixing, or extending the platform.
---

# B2S Enterprise Compliance Platform — Skill Guide

## What this platform does (plain English)

The B2S platform reads tank car inspection paperwork (PDFs, photos, scanned documents),
extracts the key data fields using OCR, checks them against federal railroad safety
regulations (AAR M-1002 / Appendix L), fills out the official B-2 DOCX forms, and
produces an HTML compliance report — all automatically.

The auditor just:
1. Double-clicks **LAUNCH_AUDITOR.bat** (or runs the GUI directly)
2. Points the tool at a folder of evidence files
3. Clicks **RUN AUDIT PIPELINE**
4. Gets a populated Word doc and an HTML report

---

## Project file map

```
project-root/
├── b2s_enterprise_gui.py        ← The auditor-facing dashboard (Tkinter GUI)
├── run_complete_platform.py     ← Compatibility wrapper; what the GUI imports
├── platform_launcher.py         ← Core orchestrator (concurrency-safe)
├── validation_engine.py         ← Regulatory rule checker
├── fix_platform.py              ← Auto-repair script (run this first for most errors)
├── stress_test.py               ← 100-contract concurrent test
├── LAUNCH_AUDITOR.bat           ← One-click launcher for Windows
├── CREATE_APP_ICON.bat          ← Creates desktop shortcut
├── requirements.txt             ← Python package list
├── DEPLOYMENT_GUIDE.md          ← Command-line reference
│
├── core/
│   ├── __init__.py
│   └── enhanced_multi_code_extractor.py   ← OCR + field extraction engine
│
├── pipeline/
│   ├── __init__.py
│   ├── batch_evidence_processor.py        ← Processes folders of files
│   ├── b2s_field_aggregator.py            ← Merges extracted fields across docs
│   └── b2s_template_filler.py            ← Writes data into DOCX templates
│
└── templates/
    └── *.docx                             ← Blank B-2 form templates (one per activity code)
```

---

## Activity codes and what they mean

| Code | Inspection Type               | Key Fields |
|------|-------------------------------|------------|
| C5V  | Valve test                    | gauge pressure, test medium, calibration |
| C5S  | Safety relief device test     | set pressure, STD pressure, VTP pressure |
| C5I  | Instrument / gauge test       | instrument type, calibration date/due |
| C6R  | Traceability / material certs | CID number, personnel ID |
| C7   | Coating application           | coating material, batch, surface temp |
| C8   | Coating thickness             | observed thickness, material, surface temp |
| C10  | Final coating inspection      | coating material, batch, thickness |

---

## Output folder structure (each run is isolated)

```
output_platform/runs/<timestamp>_<label>_<uuid>/
├── contracts/         ← Saved copy of the incoming data
├── extractions/       ← Raw OCR results (JSON)
├── aggregations/      ← Merged field values across documents (JSON)
├── validations/       ← Per-code compliance reports (JSON)
├── b2s_forms/         ← Completed DOCX forms (one per detected activity code)
├── reports/           ← Human-readable HTML summary
└── manifests/
    └── run_summary.json   ← Machine-readable run manifest
```

Each run gets its own folder so parallel runs never overwrite each other.

---

## SOP pipeline — the 11-stage specification

The `SOP.zip` file is the authoritative design document for the entire platform. It defines
11 Standard Operating Procedures (SOP 0–10) that map directly to the platform code. When
debugging, extending, or explaining any part of the pipeline, refer to the relevant SOP.

| SOP | Stage name | What it does | Platform code |
|-----|-----------|--------------|---------------|
| SOP 0 | System Contracts | Defines canonical field keys, JSON schemas, field registry | `SOP_00_field_registry.json`, `SOP0_field_mapping_configuration.py` |
| SOP 1 | Evidence Intake | Accepts folders/ZIPs/file lists → produces manifest | `pipeline/batch_evidence_processor.py` |
| SOP 2 | Document Normalization | Converts PDFs/images → per-page PNGs + metadata | `core/enhanced_multi_code_extractor.py` |
| SOP 3 | OCR and Text Layer | Runs OCR → plain text + word bounding boxes | `core/enhanced_multi_code_extractor.py` |
| SOP 4 | Layout / Table Structure | Detects tables, reconstructs rows/columns from word boxes | `core/enhanced_multi_code_extractor.py` |
| SOP 5 | Classification / Routing | Assigns activity code (C5V, C5S, etc.) to each document | `core/enhanced_multi_code_extractor.py` |
| SOP 6 | Information Extraction | Extracts key-value fields + repeating table records | `core/enhanced_multi_code_extractor.py` |
| SOP 7 | Aggregation | Merges extractions across docs → one fill payload per code | `pipeline/b2s_field_aggregator.py` |
| SOP 8 | DOCX Form Filling | Fills B-2 DOCX templates including multi-row tables | `pipeline/b2s_template_filler.py`, `SOP8_audit_to_b2_docx_FINAL.py` |
| SOP 9 | Validation | Checks completeness, formats, cross-field logic, compliance | `validation_engine.py` |
| SOP 10 | Orchestration | Runs SOP 1–9 in order, collects artifacts, validates outputs | `platform_launcher.py` |

### SOP 0 — the field registry

`SOP_00_field_registry.json` (inside `SOP.zip`) is the central contract all modules share.

- **85 canonical fields** — e.g. `car_mark_and_number`, `calibration_date`, `set_pressure`
- **23 canonical tables** — e.g. `component_tracking`, `defect_repair_summary`
- **185 table column keys**
- **657 template labels** mapped to canonical keys (synonyms, aliases)

Canonical keys use `snake_case`. Single fields live under `fields.<key>`. Repeating data
lives under `tables.<table_name>[].<column_key>`. Dates are ISO-format strings (`YYYY-MM-DD`).

**Integration rule:** every downstream module must output JSON that validates against SOP 0
schemas. Never rename or add canonical keys without bumping `registry_version`.

### Using SOP.zip as a registry with the bundle tools

Pass `SOP.zip` directly to Tools 02 and 03 with `--registry` for smarter field matching:

```bash
# Tool 02 — find gaps using SOP field registry
python find_missing_information_for_templates.py "C:\Evidence" "C:\Templates" \
  --output "C:\gaps" --registry "C:\path\to\SOP.zip"

# Tool 03 — autofill using SOP field registry
python autofill_templates_from_evidence.py "C:\Evidence" "C:\Templates" \
  --output "C:\filled" --registry "C:\path\to\SOP.zip"
```

The tools automatically find `field_registry.json` inside the ZIP and load all 657
label-to-canonical-key mappings as matching aliases.

### SOP supersession rule

Files inside `SOP.zip` without the `SOP_00_` prefix (e.g. bare `field_registry.json`) are
superseded versions. Always use the `SOP_00_*` prefixed files. The `SOP_00_SUPERSESSION_NOTICE.txt`
inside the zip confirms this.

---

## Compliance status meanings

| Status | Meaning |
|--------|---------|
| **COMPLIANT** | All required fields present, all regulatory checks passed |
| **REQUIRES REVIEW** | Some fields need human verification before submission |
| **NON-COMPLIANT** | One or more critical regulatory failures found |
| **INSUFFICIENT DATA** | Too little data extracted to make a determination |

---

## First-time setup (step by step for non-technical users)

### Prerequisites
1. **Python 3.10+** — download from python.org; check "Add to PATH" during install
2. **Tesseract OCR** — needed to read scanned PDFs and images
   - Windows: download installer from https://github.com/UB-Mannheim/tesseract/wiki
   - Accept defaults; install to `C:\Program Files\Tesseract-OCR\`
3. **Poppler** (optional, improves PDF handling)

### Install Python packages
Open a Command Prompt in the project folder and run:
```
pip install python-docx pillow pdfplumber pytesseract pymupdf
```
Or just double-click **LAUNCH_AUDITOR.bat** — it runs `pip install` automatically.

### Run the repair script
Before the first launch, run:
```
python fix_platform.py
```
This fixes import paths and creates required `__init__.py` files.

### Launch the dashboard
```
python b2s_enterprise_gui.py
```
Or use **LAUNCH_AUDITOR.bat** which does steps 2–3 automatically.

---

## Common errors and fixes

### `ModuleNotFoundError: No module named 'enhanced_multi_code_extractor'`
**Cause:** Import paths point to the wrong location.
**Fix:** Run `python fix_platform.py` — it patches all imports automatically.

### `ModuleNotFoundError: No module named 'run_complete_platform'`
**Cause:** Command was run from the wrong folder.
**Fix:** Make sure the terminal is in the project root (same folder as `b2s_enterprise_gui.py`).
```
cd /path/to/project
python b2s_enterprise_gui.py
```

### `ModuleNotFoundError: No module named 'docx'`
**Fix:**
```
pip install python-docx
```

### `pytesseract.pytesseract.TesseractNotFoundError`
**Cause:** Tesseract OCR is not installed or not on PATH.
**Fix:** Install Tesseract, then add its folder to Windows PATH:
- Search Windows for "Edit the system environment variables"
- Add `C:\Program Files\Tesseract-OCR\` to PATH

### `FileNotFoundError: templates/...`
**Cause:** The `templates/` folder is missing or empty.
**Fix:** Make sure the DOCX template files are in a `templates/` subfolder next to `platform_launcher.py`. One template per activity code, named like `C5V_template.docx`.

### GUI opens but "RUN AUDIT PIPELINE" produces no output
**Likely cause:** Evidence folder path contains spaces or special characters, or files are on OneDrive and not synced locally.
**Fix:** Right-click files in OneDrive → "Always keep on this device". Or copy them to a local folder first.

### `One or more selected evidence files do not exist on disk`
**Cause:** OneDrive "cloud-only" files (shown with a cloud icon) — they're not actually on disk yet.
**Fix:** Open File Explorer, right-click the evidence folder → "Always keep on this device".

### Compliance status shows INSUFFICIENT_DATA for everything
**Cause:** OCR couldn't extract recognizable fields (possibly image quality too low, or activity code not detected).
**Check:** Open `runs/<latest>/extractions/` and look at the JSON — if fields are all empty, the source document may be too blurry or in an unsupported format.

### Race condition / corrupted output when running multiple audits
**Cause:** Old platform code wrote to a shared `output/` folder.
**Fix:** `platform_launcher.py` (current version) uses per-run isolated directories. Make sure `run_complete_platform.py` delegates to `PlatformLauncher`, not the old code. Run `python fix_platform.py` if unsure.

---

## How to run from the command line (advanced)

```bash
# Standard evidence run
python platform_launcher.py --input "C:\Evidence\Job-2024-001" --output-root platform_output

# Demo run with synthetic data (no evidence files needed)
python platform_launcher.py --demo-contract

# Skip validation
python platform_launcher.py --input evidence/ --no-validation

# Skip DOCX fill
python platform_launcher.py --input evidence/ --no-fill
```

---

## How to add a new activity code

To add support for a new activity code (e.g., `C11`):

**1. Add default field set** in `platform_launcher.py` → `DEFAULT_FIELD_SETS` dict:
```python
"C11": {
    "car_mark_and_number": "UTLX 300008",
    "tank_car_design_spec": "DOT-111A100W1",
    "personnel_id": "TECH-C11-001",
    # ... add all fields for this code
},
```

**2. Add validation rules** in `validation_engine.py` → add a `_get_c11_validation_rules()` method following the same pattern as existing ones, then register it in `self.validation_rules` inside `__init__`.

**3. Add DOCX template** — place `C11_template.docx` (or equivalent) in the `templates/` folder.

**4. Register the code** in `b2s_enterprise_gui.py` → `config["activity_codes"]` list:
```python
"activity_codes": ["C5V", "C5S", "C5I", "C6R", "C7", "C8", "C10", "C11"],
```

---

## Best Tools Bundle — three standalone helper scripts

The bundle lives in three numbered folders alongside the main platform. Each script is
independent — they don't require the B2S platform to be installed, just Python and a
few packages.

```
01_extract_everything_to_extractable_text/
    extract_everything_to_extractable_text.py
02_find_missing_information_for_templates/
    find_missing_information_for_templates.py
03_autofill_templates_from_evidence/
    autofill_templates_from_evidence.py
```

---

### When to use each tool

| Situation | Use |
|-----------|-----|
| Evidence files are scanned PDFs or odd formats the main platform can't read | Tool 01 first to convert to clean text |
| You want to know which B-2 fields are still empty before running an audit | Tool 02 to get a gap report |
| You want to fill a DOCX template directly from evidence without the full B2S pipeline | Tool 03 |
| Full end-to-end automated audit with regulatory validation | Main platform (`LAUNCH_AUDITOR.bat`) |

---

### Tool 01 — Extract everything to extractable text

Converts any file or folder (PDFs, images, ZIPs, legacy formats) into clean
`.txt`, `.md`, `.json`, `.docx`, and searchable `.pdf` outputs. This is the best
first step when the main platform struggles to read a document.

**Install:**
```
pip install docling python-docx
```

**Optional (recommended for scanned PDFs):**
- Install OCRmyPDF: `pip install ocrmypdf`
- Install Java + download [Apache Tika app jar](https://tika.apache.org/download.html),
  then set: `set TIKA_APP_JAR=C:\path\to\tika-app.jar`

**Run:**
```bash
python extract_everything_to_extractable_text.py "C:\Evidence\Job-001" --output "C:\Evidence\Job-001_extracted"

# For Spanish + English scanned docs
python extract_everything_to_extractable_text.py "C:\Evidence" --output "C:\output" --lang eng+spa

# Windows drag-and-drop: drag a folder onto
drag_drop_extract_everything_to_extractable_text.bat
```

**Extraction order (automatic):** Docling → OCRmyPDF (for scanned PDFs) → Apache Tika fallback

**What it outputs (per file):**
- `content.txt` / `content.md` / `content.json` / `content.docx`
- `searchable.pdf` (if OCRmyPDF available)
- `metadata.json`

**Folder-level outputs:**
- `manifest.json` / `manifest.csv` — one row per file processed
- `summary.json` / `summary.txt` — overall stats (success rate, table counts, methods used)

---

### Tool 02 — Find missing information for templates

Compares evidence documents against templates (DOCX, PDF, or text-based) and produces
a report listing every required field that couldn't be matched in the evidence. Use this
before filling forms to understand what information is still needed.

**Install:**
```
pip install python-docx pymupdf
```

**Run:**
```bash
python find_missing_information_for_templates.py "C:\Evidence" "C:\Templates" --output "C:\missing_info_output"

# With a SOP/B2 field registry for smarter matching
python find_missing_information_for_templates.py "C:\Evidence" "C:\Templates" --output "C:\output" --registry "C:\SOP.zip"

# Multiple registries
python find_missing_information_for_templates.py "C:\Evidence" "C:\Templates" --output "C:\output" --registry "C:\SOP.zip" --registry "C:\SOP_PLATFORM_V2.zip"
```

**Matching order (automatic):**
1. Registry exact match (if `--registry` provided)
2. Registry fuzzy match
3. Corpus hint (field label appears in the evidence text body)
4. Missing (couldn't match)

**Key outputs:**
- `missing_fields.csv` — the gap list (open in Excel)
- `missing_fields.json` — machine-readable version
- `match_results.json` — full match details for every required field
- `loaded_registries.json` — which registries were loaded
- `registry_alias_map.json` — all field synonyms resolved
- `summary.json` — overall match rate and counts

---

### Tool 03 — Autofill templates from evidence

Reads evidence documents, matches values to template fields, and writes filled DOCX
templates. Also outputs a missing-fields report for anything it couldn't fill.

**Install:**
```
pip install python-docx pymupdf
```

**Run:**
```bash
python autofill_templates_from_evidence.py "C:\Evidence" "C:\Templates" --output "C:\autofill_output"

# With a SOP/B2 registry for smarter field matching
python autofill_templates_from_evidence.py "C:\Evidence" "C:\Templates" --output "C:\output" --registry "C:\SOP.zip"
```

**What gets filled:**
- ✅ DOCX templates — paragraph text replacement and label-value line substitution
- ✅ TXT / MD / CSV / JSON / HTML / XML / YAML / INI / LOG — placeholder substitution
- ⚠️ PDF templates — analyzed for gaps but **not** directly written (v1 limitation); a copy is placed in output unchanged

**Key outputs:**
- `filled_templates/` — completed DOCX and text files
- `missing_fields.csv` / `missing_fields.md` — what still needs manual entry
- `match_results.json` — full field-by-field matching detail
- `autofill_results.json` — which substitutions were made per template
- `summary.json` — overall fill rate

**Note on DOCX filling:** replacement happens at paragraph text level, so complex inline
formatting (bold mid-sentence, etc.) may be simplified in filled fields. Content controls
and MERGEFIELDs are detected and reported but not written in v1.

---

### Recommended workflow for a hard evidence set

Use this sequence when evidence files are messy or the main platform isn't extracting well:

```
Step 1 → Tool 01: Convert all evidence to clean text
          python extract_everything_to_extractable_text.py "C:\Evidence" --output "C:\extracted"

Step 2 → Tool 02: Find out what's missing
          python find_missing_information_for_templates.py "C:\extracted" "C:\Templates" --output "C:\gaps" --registry "C:\SOP.zip"

Step 3 → Tool 03: Fill what can be filled automatically
          python autofill_templates_from_evidence.py "C:\extracted" "C:\Templates" --output "C:\filled" --registry "C:\SOP.zip"

Step 4 → Manually enter anything still listed in missing_fields.csv

Step 5 → Run main platform on the original evidence for full regulatory validation
          python platform_launcher.py --input "C:\Evidence" --output-root platform_output
```

---

## How to run the stress test

Verifies the platform can handle 100 concurrent audits without collisions:
```bash
python stress_test.py --count 100 --workers 24 --output-root stress_test_output
```
Results are written to `stress_test_output/stress_test_summary.json`.
Exit code 0 = all passed. Exit code 1 = failures or artifact collisions detected.

---

## Validation confidence scoring

The engine scores each run on four weighted factors:

| Factor | Weight | What it checks |
|--------|--------|----------------|
| OCR quality | 25% | How confident the OCR was during extraction |
| Field completeness | 30% | What percentage of required fields were found |
| Cross-field validation | 25% | Whether fields agree with each other (e.g., STD ≤ set pressure) |
| Regulatory compliance | 20% | Whether values meet 49 CFR / AAR M-1002 requirements |

A run needs a **combined score ≥ 0.70** and **zero critical issues** to be marked "regulatory ready."

---

## When generating corrected code

- Always preserve the existing file structure (`core/`, `pipeline/`, top-level scripts)
- Import paths must use package notation: `from core.enhanced_multi_code_extractor import ...`
- `BatchEvidenceProcessor()` takes no constructor arguments (the extractor is created internally)
- All file writes should go through `_atomic_write_json` / `_atomic_write_text` for safety
- Each run must create its own subdirectory under `output_root/runs/` — never write directly to `output/`
- When providing fix scripts, model them after `fix_platform.py` (read → patch text → write back)

---

## Tone guidance for auditor-facing responses

This platform is used by compliance auditors, not developers. When explaining errors or steps:
- Say **"evidence folder"** not "input directory"
- Say **"click Browse and select your files"** not "pass the path as a CLI argument"
- Say **"the tool couldn't read the scanned document clearly"** not "OCR confidence below threshold"
- Always give the simplest fix first (usually: run `fix_platform.py`, then re-launch)
- When sharing fixed code, also explain in one sentence *what was broken and why the fix works*
