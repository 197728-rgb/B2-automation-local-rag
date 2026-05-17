# Codebase issue triage: actionable tasks

This review identifies one concrete task each for a typo/miswording fix, a bug fix, a docs discrepancy, and a test improvement.

## 1) Typo / miswording task
- **Area:** Retrieval fallback description.
- **Evidence:** The module docstring in `src/b2_automation/local_semantic_retrieval.py` says fallback occurs when the corpus is empty, while the implementation in `retrieve_chunks_for_form()` falls back when semantic scores are empty or non-positive.
- **Task:** Update the docstring wording to match runtime behavior (fallback when semantic ranking provides no usable signal).

## 2) Bug fix task
- **Area:** CLI review form parsing.
- **Evidence:** `normalize_review_forms()` in `src/b2_automation/local_extraction.py` splits only on commas, so a single token like `"B81 B89"` is treated as one unknown form instead of two valid forms.
- **Task:** Support both comma and whitespace separators while preserving deduplication and strict validation of allowed form IDs.

## 3) Comment/documentation discrepancy task
- **Area:** Output artifact expectations.
- **Evidence:** `README.md` lists `raw/*.ocr.json` as expected output artifacts, but the default local-first extraction/reporting flow emphasizes metadata/chunks/retrieval artifacts and does not clearly guarantee OCR JSON for every run.
- **Task:** Reconcile README output examples with actual default output behavior (either update docs to reflect current outputs or intentionally guarantee OCR artifact generation and document when it appears).

## 4) Test improvement task
- **Area:** CLI input coverage.
- **Evidence:** `tests/test_cli.py` validates comma-separated `--review-forms` inputs but lacks explicit coverage for whitespace-only and mixed separators.
- **Task:** Add parameterized tests for `"B81,B89"`, `"B81 B89"`, and `"B81, B89"` to lock in accepted parsing behavior and prevent regressions.
