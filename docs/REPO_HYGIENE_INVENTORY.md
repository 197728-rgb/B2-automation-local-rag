# Repository hygiene inventory (classification)

Grouped summary for cleanup decisions. Applies to branch state at hygiene pass time.

## Generated artifacts → IGNORE-IN-GIT / DELETE locally

| Path | Action | Reason |
|------|--------|--------|
| `.pytest-tmp/`, `.pytest-stage56/` | IGNORE-IN-GIT | pytest `--basetemp` output; never committed |
| `.pytest_cache/` | IGNORE-IN-GIT | pytest cache |
| `.pytest_tmp/`, `.pytest_tmp_*`, `.pytest_tmp_root/` | IGNORE-IN-GIT, DELETE if present locally | ephemeral test roots |
| `outputs/` | IGNORE-IN-GIT | CLI default run output (AGENTS.md) |
| `htmlcov/`, `.coverage*` | IGNORE-IN-GIT | coverage |
| `pytest-cache-files-*/` | DELETE if present locally | orphaned pytest temp clones |
| `__pycache__/`, `*.pyc` | IGNORE-IN-GIT, DELETE locally | bytecode |

## Caches / editor noise → IGNORE-IN-GIT (scoped)

| Path | Action | Reason |
|------|--------|--------|
| `.cursor/**` except `!.cursor/rules/**` | IGNORE-IN-GIT | Local Cursor churn; tracked rules retained via negated patterns |
| `.vscode/**` except `!.vscode/tasks.json` | IGNORE-IN-GIT | Local settings; intentional `tasks.json` stays tracked |
| `.ruff_cache/` | IGNORE-IN-GIT | already listed |

## DocuPipe-shaped fixtures → KEEP

| Path | Action | Reason |
|------|--------|--------|
| `samples/docupipe/*.json` | KEEP | Optional fixtures for experiments or `sample-pipeline` |

## Salvage reference → KEEP

| Path | Action | Reason |
|------|--------|--------|
| `salvage/**` | KEEP | AGENTS.md: reference-only old tool material |

## Duplicates / parallel map files → KEEP (low cost)

| Path | Action | Reason |
|------|--------|--------|
| `schemas/maps/*.approval_map.json` | KEEP | Parallel to canonical `*.json`; loader prefers canonical; useful diff |

## Optional reference data → KEEP

| Path | Action | Reason |
|------|--------|--------|
| `schemas/activity_2026_cleaned/` | KEEP | Not imported by code; small JSON review artifacts |

## Production / first-class → KEEP

- `src/b2_automation/**` (except nothing removed)
- `schemas/maps/{B24_RL2,B81,B89,B90,Cover_Page}.json`
- `schemas/templates/{B24_RL2,B81,B89,B90,Cover_Page}.json`
- `templates/*.docx` (first-class + `Cover_Page`)
- `tests/**`, `mapping/cell_inventory.csv`, `scripts/**`, `.github/**`

## Inbox samples → KEEP

- `inbox/evidence.txt` — multi-form smoke text
- `inbox/evidence_sample.txt` — minimal line sample

No scratch-only files removed (both are intentional).
