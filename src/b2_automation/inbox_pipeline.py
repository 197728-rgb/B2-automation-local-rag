"""Inbox pipeline for local-first B-2 evidence review."""

from __future__ import annotations

import json
import re
import shutil
import zipfile
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Mapping
from xml.etree import ElementTree as ET

from b2_automation.approval_maps import ApprovalBundle, load_exact_approval_bundle_checked
from b2_automation.evidence_assistant import build_delta_report, build_role_views, enrich_chunk_metadata, ensure_clause_map_db, write_eval_seed
from b2_automation.evidence_outputs import build_canonical_evidence_document, build_field_traceability_document
from b2_automation.local_extraction import (
    DEFAULT_REVIEW_FORMS,
    LocalEvidenceDocument,
    build_form_packets,
    chunk_text,
    extract_local_document,
    normalize_review_forms,
    supported_evidence_files,
    utc_now,
    write_local_artifacts,
)
from b2_automation.ooxml_writer import patch_docx_cells

DEFAULT_LOW_CONFIDENCE_THRESHOLD = 0.70
REVIEW_REQUIRED_TEXT = "REVIEW_REQUIRED"
DOCX_TABLE_MARKER = "[structured_docx_table_evidence]"
WORD_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
LABEL_WORDS = (
    "name",
    "date",
    "permission",
    "instruction",
    "car",
    "mark",
    "number",
    "spec",
    "stencil",
    "form",
    "drawing",
    "revision",
    "description",
    "material",
    "id",
    "status",
    "function",
    "training",
    "procedure",
    "approved",
    "record",
    "result",
    "equipment",
    "calibration",
    "location",
    "temperature",
    "method",
    "observed",
    "pitp",
)


@dataclass(frozen=True)
class InboxPipelineResult:
    run_dir: Path
    manifest_path: Path
    review_json_path: Path
    review_md_path: Path
    filled_docx_path: Path | None
    filled_docx_paths: tuple[Path, ...]
    status: str


def _utc_now() -> str:
    return utc_now()


def _retrieval_summary(packets: dict[str, dict[str, Any]], forms: tuple[str, ...]) -> str:
    modes = sorted({str(packets.get(f, {}).get("retrieval_method") or "unknown") for f in forms})
    return "local semantic ranking: " + ", ".join(modes) + " (evidence-only; exact maps authorize writes)"


def _clear_scoped_filled_docx(filled_dir: Path, forms: tuple[str, ...]) -> None:
    for form in forms:
        try:
            (filled_dir / f"{form}_filled.docx").unlink()
        except FileNotFoundError:
            pass


def _augment_docx_table_evidence(documents: list[LocalEvidenceDocument]) -> list[LocalEvidenceDocument]:
    """Append row-paired DOCX table evidence so filled B-2 examples become usable RAG input."""
    augmented: list[LocalEvidenceDocument] = []
    for doc in documents:
        if doc.source_path.suffix.lower() != ".docx":
            augmented.append(doc)
            continue
        structured = _read_docx_table_pairs(doc.source_path)
        if not structured:
            augmented.append(doc)
            continue
        metadata = dict(doc.metadata or {})
        metadata["docx_table_structured_evidence"] = True
        metadata["docx_table_structured_characters"] = len(structured)
        augmented.append(
            replace(
                doc,
                text=(str(doc.text or "") + "\n\n" + DOCX_TABLE_MARKER + "\n" + structured).strip(),
                metadata=metadata,
            )
        )
    return augmented


def _read_docx_table_pairs(path: Path) -> str:
    try:
        with zipfile.ZipFile(path) as zf:
            root = ET.fromstring(zf.read("word/document.xml"))
    except OSError:
        return ""
    except (zipfile.BadZipFile, KeyError, ET.ParseError):
        return ""
    out: list[str] = []
    seen: set[str] = set()
    for table_index, table in enumerate(root.iter(f"{WORD_NS}tbl")):
        rows = [_table_row_cells(row) for row in table.iter(f"{WORD_NS}tr")]
        for row_index, cells in enumerate(rows):
            compact = _collapse_adjacent_duplicates(cells)
            row_text = " | ".join(cell for cell in compact if cell)
            _emit_unique(out, seen, f"table_{table_index}_row_{row_index}: {row_text}")
        for labels, values in zip(rows, rows[1:]):
            if not _looks_like_label_row(labels) or _looks_like_label_row(values):
                continue
            for label, value in zip(labels, values):
                label = _clean_cell(label)
                value = _clean_cell(value)
                if not label or not value or label == value or _looks_like_label(value):
                    continue
                _emit_unique(out, seen, f"{label}: {value}")
    return "\n".join(out)


def _table_row_cells(row: ET.Element) -> list[str]:
    cells: list[str] = []
    for cell in row.iter(f"{WORD_NS}tc"):
        text = _clean_cell(" ".join(node.text or "" for node in cell.iter(f"{WORD_NS}t")))
        span = 1
        grid_span = next(cell.iter(f"{WORD_NS}gridSpan"), None)
        if grid_span is not None:
            try:
                span = max(1, int(grid_span.attrib.get(f"{WORD_NS}val", "1")))
            except ValueError:
                span = 1
        cells.extend([text] * span)
    return cells


def _looks_like_label_row(cells: list[str]) -> bool:
    nonblank = [_clean_cell(cell) for cell in cells if _clean_cell(cell)]
    if not nonblank or len({cell.lower() for cell in nonblank}) == 1:
        return False
    label_hits = sum(1 for cell in nonblank if _looks_like_label(cell))
    value_hits = sum(1 for cell in nonblank if _looks_like_value(cell))
    return label_hits >= max(1, len(nonblank) // 3) and label_hits >= value_hits


def _looks_like_label(text: str) -> bool:
    lower = _clean_cell(text).lower()
    if not lower:
        return False
    return lower.endswith(":") or any(word in lower for word in LABEL_WORDS) or (lower.upper() == lower and len(lower.split()) <= 8)


def _looks_like_value(text: str) -> bool:
    cleaned = _clean_cell(text)
    if not cleaned:
        return False
    if re.search(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b|\b[A-Z]{2,6}\s*[- ]?\d{3,8}\b", cleaned):
        return True
    if re.search(r"\b\d+(?:\.\d+)?\s*(?:psi|psig|f|mils?|in|%)\b", cleaned, flags=re.IGNORECASE):
        return True
    return bool(re.search(r"[a-z]", cleaned) and len(cleaned.split()) <= 12)


def _collapse_adjacent_duplicates(cells: list[str]) -> list[str]:
    out: list[str] = []
    last = None
    for cell in cells:
        if cell and cell != last:
            out.append(cell)
        last = cell
    return out


def _clean_cell(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "").replace("\u00a0", " ")).strip(" |")


def _emit_unique(out: list[str], seen: set[str], line: str) -> None:
    line = _clean_cell(line)
    if line and line not in seen:
        seen.add(line)
        out.append(line)


def _field_values_from_packet(packet: dict[str, Any]) -> tuple[dict[str, str], dict[str, float]]:
    values: dict[str, str] = {}
    confidences: dict[str, float] = {}
    for decision in packet.get("field_decisions", []):
        value = decision.get("selected_value")
        if value is None or str(value).strip() == "":
            continue
        field_id = str(decision["field_id"])
        state = str(decision.get("state") or "")
        if state not in {"FILL", "REVIEW_REQUIRED", "LOW_CONFIDENCE"}:
            continue
        values[field_id] = str(value).strip()
        confidences[field_id] = float(decision.get("confidence") or 1.0)
    return values, confidences


def _manifest_cells_for_fill(bundle: ApprovalBundle, values: Mapping[str, str]) -> dict[str, Any]:
    raw_fields = bundle.approval_map.get("fields") or {}
    approved_ids = {str(k) for k in raw_fields.keys()} if isinstance(raw_fields, dict) else set()
    cells = [
        spec
        for spec in bundle.manifest.get("cells") or []
        if str(spec.get("field_id", "")) in values and str(spec.get("field_id", "")) in approved_ids
    ]
    return {**dict(bundle.manifest), "cells": cells}


def _marker(field_id: str, reason: str) -> str:
    return f"{REVIEW_REQUIRED_TEXT}: {field_id} {reason}".strip()


def _add_missing_required_map_markers(bundle: ApprovalBundle, values: dict[str, str], confidences: dict[str, float]) -> list[str]:
    fields = bundle.approval_map.get("fields") or {}
    if not isinstance(fields, Mapping):
        return []
    manual: list[str] = []
    for field_id, spec in fields.items():
        if not isinstance(spec, Mapping) or not bool(spec.get("required")):
            continue
        fid = str(field_id)
        if str(values.get(fid) or "").strip():
            continue
        values[fid] = _marker(fid, "needs manual completion")
        confidences[fid] = 1.0
        manual.append(fid)
    return sorted(manual)


def _manual_fields(values: Mapping[str, str]) -> list[str]:
    return sorted(fid for fid, value in values.items() if str(value).startswith(REVIEW_REQUIRED_TEXT))


def _write_local_filled_docx(
    *,
    root: Path,
    run_dir: Path,
    filled_dir: Path,
    packets: dict[str, dict[str, Any]],
    low_confidence_threshold: float,
) -> list[dict[str, Any]]:
    work_dir = run_dir / "patch_work"
    guard_dir = run_dir / "structure_guard_reports"
    work_dir.mkdir(parents=True, exist_ok=True)
    guard_dir.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, Any]] = []

    for form, packet in packets.items():
        values, confidences = _field_values_from_packet(packet)
        load_result = load_exact_approval_bundle_checked(root, form)
        bundle = load_result.bundle
        result: dict[str, Any] = {
            "form_id": form,
            "attempted": False,
            "status": "skipped_no_fill_decisions",
            "approval_map": str(bundle.map_path) if bundle else None,
            "template": str(bundle.template_path) if bundle and bundle.template_path.is_file() else None,
            "filled_docx": None,
            "structure_guard_report": None,
            "structure_guard_passed": False,
            "patched_fields": [],
            "manual_fields": [],
            "errors": list(load_result.errors),
        }
        if bundle is None:
            result["status"] = "skipped_missing_exact_approval_map"
            results.append(result)
            continue
        if not bundle.template_path.is_file():
            result["status"] = "skipped_missing_template"
            results.append(result)
            continue

        _add_missing_required_map_markers(bundle, values, confidences)
        result["manual_fields"] = _manual_fields(values)
        if not values:
            results.append(result)
            continue

        fill_manifest = _manifest_cells_for_fill(bundle, values)
        if not fill_manifest.get("cells"):
            result["status"] = "skipped_no_matching_manifest_cells"
            result["errors"] = result["errors"] + ["No selected field IDs matched exact map cells."]
            results.append(result)
            continue

        candidate_docx = work_dir / f"{form}_candidate.docx"
        final_docx = filled_dir / f"{form}_filled.docx"
        guard_path = guard_dir / f"{form}_structure_guard_report.json"
        outcome = patch_docx_cells(
            bundle.template_path,
            fill_manifest,
            values,
            candidate_docx,
            field_confidences=confidences,
            required_field_ids=set(),
            low_confidence_threshold=low_confidence_threshold,
            structure_guard_report_path=guard_path,
            approval_map=bundle.approval_map,
        )
        result.update(
            {
                "attempted": True,
                "status": "filled" if outcome.structure_guard_passed else "discarded_structure_guard_failed",
                "structure_guard_report": str(outcome.structure_guard_report) if outcome.structure_guard_report else None,
                "structure_guard_passed": outcome.structure_guard_passed,
                "patched_fields": list(outcome.patched_fields),
                "manual_fields": sorted(set(result["manual_fields"]) & set(outcome.patched_fields)),
                "errors": list(outcome.errors),
            }
        )
        if outcome.structure_guard_passed:
            final_docx.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(candidate_docx), final_docx)
            result["filled_docx"] = str(final_docx)
        else:
            try:
                candidate_docx.unlink()
            except FileNotFoundError:
                pass
            guard_payload = json.loads(guard_path.read_text(encoding="utf-8")) if guard_path.is_file() else {}
            result["failure_reason"] = "structure_guard_failed"
            result["structure_guard_errors"] = list(guard_payload.get("errors") or [])
        results.append(result)

    attempted = [item for item in results if item.get("attempted")]
    aggregate = {"pass": all(bool(item.get("structure_guard_passed")) for item in attempted) if attempted else True, "forms": results}
    (run_dir / "structure_guard_report.json").write_text(json.dumps(aggregate, indent=2, sort_keys=True), encoding="utf-8")
    return results


def _run_local_rag_inbox_pipeline(*, root: Path, inbox: Path, out_dir: Path, review_forms: tuple[str, ...] | None, low_confidence_threshold: float) -> InboxPipelineResult:
    inbox = inbox.resolve()
    run_dir = out_dir.resolve()
    raw_dir = run_dir / "raw"
    review_dir = run_dir / "review"
    filled_dir = run_dir / "filled"
    for p in (raw_dir, review_dir, filled_dir):
        p.mkdir(parents=True, exist_ok=True)

    inputs = supported_evidence_files(inbox)
    if not inputs:
        raise FileNotFoundError(f"No supported local evidence files found in inbox: {inbox}")

    forms = normalize_review_forms(review_forms)
    _clear_scoped_filled_docx(filled_dir, forms)
    documents = _augment_docx_table_evidence([extract_local_document(path) for path in inputs])
    chunks_by_source = {}
    for doc in documents:
        chunks_by_source[doc.source_file] = [
            enrich_chunk_metadata(
                source_file=doc.source_file,
                source_sha256=doc.sha256,
                extracted_at=str(doc.metadata.get("extracted_at") or ""),
                chunk=chunk,
            )
            for chunk in chunk_text(doc.text)
        ]

    packets = build_form_packets(documents, chunks_by_source, forms, low_confidence_threshold=low_confidence_threshold)
    artifact_index = write_local_artifacts(raw_dir=raw_dir, review_dir=review_dir, documents=documents, chunks_by_source=chunks_by_source, packets=packets)

    current_doc_index = {doc.source_file: doc.sha256 for doc in documents}
    index_path = review_dir / "document_index.json"
    previous_doc_index = json.loads(index_path.read_text(encoding="utf-8")) if index_path.is_file() else {}
    (review_dir / "delta_report.json").write_text(json.dumps(build_delta_report(previous_index=previous_doc_index, current_index=current_doc_index), indent=2, sort_keys=True), encoding="utf-8")
    index_path.write_text(json.dumps(current_doc_index, indent=2, sort_keys=True), encoding="utf-8")
    ensure_clause_map_db(review_dir / "regulation_clause_map.sqlite")
    write_eval_seed(review_dir / "evaluation_seed.json")

    review_json = review_dir / "local_rag_review.json"
    review_md = review_dir / "local_rag_review.md"
    manifest_path = run_dir / "run_manifest.json"
    rag_selection_path = run_dir / "rag_selection_report.json"

    missing_context = [form for form, packet in packets.items() if not packet["retrieved_context"]]
    docx_results = _write_local_filled_docx(root=root, run_dir=run_dir, filled_dir=filled_dir, packets=packets, low_confidence_threshold=low_confidence_threshold)
    failed_docx = [item for item in docx_results if item.get("attempted") and not item.get("structure_guard_passed")]
    manual_fields = {str(item["form_id"]): list(item.get("manual_fields") or []) for item in docx_results if item.get("manual_fields")}
    status = "review_required" if missing_context or failed_docx or manual_fields else "success"

    canonical_path = run_dir / "canonical_evidence.json"
    trace_path = run_dir / "field_traceability.json"
    canonical_doc = build_canonical_evidence_document(forms=forms, packets=packets, docx_results=docx_results, root=root)
    trace_doc = build_field_traceability_document(forms=forms, packets=packets, docx_results=docx_results, root=root)
    canonical_path.write_text(json.dumps(canonical_doc, indent=2, sort_keys=True), encoding="utf-8")
    trace_path.write_text(json.dumps(trace_doc, indent=2, sort_keys=True), encoding="utf-8")
    (review_dir / "role_views.json").write_text(json.dumps(build_role_views(canonical=canonical_doc, run_logs=artifact_index), indent=2, sort_keys=True), encoding="utf-8")

    review = {
        "generated_at": _utc_now(),
        "status": status,
        "mode": "local_rag_extraction",
        "docupipe_used": False,
        "legacy_adapter_used": False,
        "forms": list(forms),
        "production_scope_forms": list(DEFAULT_REVIEW_FORMS),
        "inputs": [{"source_file": d.source_file, "sha256": d.sha256, "extraction_method": d.extraction_method, "status": "extracted"} for d in documents],
        "form_packets": packets,
        "missing_context_forms": missing_context,
        "decision_summary_by_form": {fid: packets[fid].get("decision_summary") for fid in forms},
        "write_authority": "exact approval maps required; best extracted values and visible manual markers are passed to DOCX patching",
        "docx_generation": docx_results,
        "review_blocked_forms": [],
        "blocking_review_reasons": {},
        "manual_fields": manual_fields,
        "skipped_review_required": [],
        "structure_guard_failed_forms": [item["form_id"] for item in failed_docx],
        "approval_map_and_fill_errors": [{"form_id": item["form_id"], "errors": list(item.get("errors") or [])} for item in docx_results if item.get("errors")],
        "canonical_evidence": str(canonical_path),
        "field_traceability": str(trace_path),
    }
    review_json.write_text(json.dumps(review, indent=2, sort_keys=True), encoding="utf-8")

    lines = ["# Local RAG Inbox Review", "", f"Run status: **{status}**", f"Generated: {review['generated_at']}", "", "## DOCX writing"]
    for item in docx_results:
        manual = item.get("manual_fields") or []
        suffix = f" ({len(manual)} manual fields)" if manual else ""
        lines.append(f"- {item['form_id']}: {item['status']}{suffix}")
    review_md.write_text("\n".join(lines) + "\n", encoding="utf-8")

    rag_selection = {
        "selected_approval_maps": [item.get("approval_map") for item in docx_results if item.get("approval_map")],
        "retrieved_context_used": list(artifact_index["per_form_reviews"].keys()),
        "decision": "best_extracted_values_plus_manual_markers",
        "uncertainty": "Remaining unresolved mapped fields are visible REVIEW_REQUIRED markers in the DOCX.",
    }
    rag_selection_path.write_text(json.dumps(rag_selection, indent=2, sort_keys=True), encoding="utf-8")

    guard_summary_path = run_dir / "structure_guard_report.json"
    guard_summary = json.loads(guard_summary_path.read_text(encoding="utf-8")) if guard_summary_path.is_file() else {"pass": False}
    outputs = [str(canonical_path), str(trace_path), str(review_json), str(review_md), str(rag_selection_path), str(artifact_index["aggregate_review_path"])]
    outputs += [str(item["filled_docx"]) for item in docx_results if item.get("filled_docx")]
    run_manifest = {
        "status": status,
        "mode": "local_rag_extraction",
        "docupipe_used": False,
        "legacy_adapter_used": False,
        "ocr_engine": "local text/PDF extraction with OCR fallback for scanned PDFs",
        "llm_runner": "not required for deterministic local review",
        "embedding_model": _retrieval_summary(packets, forms),
        "vector_db": "none; local TF-IDF / keyword",
        "forms": list(forms),
        "review_json": str(review_json),
        "review_markdown": str(review_md),
        "rag_selection_report": str(rag_selection_path),
        "docx_generation": docx_results,
        "review_blocked_forms": [],
        "blocking_review_reasons": {},
        "manual_fields": manual_fields,
        "skipped_review_required": [],
        "structure_guard_failed_forms": [item["form_id"] for item in failed_docx],
        "structure_guard_report": str(guard_summary_path),
        "structure_guard_passed": bool(guard_summary.get("pass")),
        "artifacts": artifact_index,
        "outputs": outputs,
    }
    manifest_path.write_text(json.dumps(run_manifest, indent=2, sort_keys=True), encoding="utf-8")

    filled_paths = tuple(Path(str(item["filled_docx"])) for item in docx_results if item.get("filled_docx"))
    first_filled = filled_paths[0] if filled_paths else None
    return InboxPipelineResult(run_dir, manifest_path, review_json, review_md, first_filled, filled_paths, status)


def run_inbox_pipeline(*, root: Path, inbox: Path, out_dir: Path, low_confidence_threshold: float = DEFAULT_LOW_CONFIDENCE_THRESHOLD, review_forms: tuple[str, ...] | None = None) -> InboxPipelineResult:
    return _run_local_rag_inbox_pipeline(root=root, inbox=inbox, out_dir=out_dir, review_forms=review_forms, low_confidence_threshold=low_confidence_threshold)
