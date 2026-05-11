# Codebase issue triage: actionable tasks with evidence

## Task 1 — Typo/miswording fix
- **Type:** Typo / wording correction
- **Evidence:** Retrieval module docstring says fallback happens only when the corpus is empty, but implementation falls back whenever semantic scores are missing or non-positive.
  - Wording location: `src/b2_automation/local_semantic_retrieval.py` module docstring (`"falls back ... if the corpus is empty"`).
  - Behavior location: `retrieve_chunks_for_form()` falls back on `if not semantic_scores or all(s <= 0.0 for s in semantic_scores):`.
- **Proposed task:** Update the docstring to describe the real behavior (fallback when semantic scoring yields no usable signal), not only the empty-corpus case.

## Task 2 — Bug fix
- **Type:** Functional bug
- **Evidence:** `normalize_review_forms()` supports comma-separated values inside one token, but whitespace-separated values inside one token are rejected.
  - Parsing code splits only by comma in `src/b2_automation/local_extraction.py`.
  - The CLI can pass a single token like `"B81 B89"`, which becomes an unknown form.
- **Proposed task:** Accept both comma and whitespace separators in normalization (while retaining validation and dedupe semantics).

## Task 3 — Comment/docs discrepancy fix
- **Type:** Documentation discrepancy
- **Evidence:** README “Expected outputs” includes `raw/*.ocr.json`, while local extraction logic emphasizes local text/PDF extraction and emits metadata/chunks/retrieval artifacts.
  - Docs location: `README.md` expected outputs list.
  - Implementation references: `src/b2_automation/local_extraction.py` and local inbox review outputs in `src/b2_automation/inbox_pipeline.py`.
- **Proposed task:** Reconcile README with actual default local outputs, or explicitly implement guaranteed OCR artifact emission and test it.

## Task 4 — Test improvement
- **Type:** Test coverage improvement
- **Evidence:** `tests/test_cli.py` has coverage for comma-separated `--review-forms` only; it does not test whitespace-only or mixed separators.
- **Proposed task:** Add parameterized cases for `"B81,B89"`, `"B81 B89"`, and `"B81, B89"`, asserting successful parse and stable command behavior.

## Repo state note (from reviewer comment)
- In this checkout, no `origin` remote is configured, so “behind origin/main by 7” cannot be verified or resolved here.
- Current branch appears clean in this environment (`git status -sb` reports only `## work`).
