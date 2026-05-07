"""Inbox pipeline for local-first B-2 evidence review.

The default path uses local extraction and form-scoped review packets. The old
DocuPipe/B24 RL1 path is kept only behind an explicit legacy option.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from b2_automation.b24_normalizer import normalize_docupipe_payload_for_b24_rl1
from b2_automation.b24_rl1_filler import REVIEW_REQUIRED_TEXT, load_manifest
from b2_automation.cell_evidence import decide_cell
from b2_automation.docupipe_client import process_pdf
from b2_automation.local_extraction import (
    DEFAULT_REVIEW_FORMS,
    build_form_packets,
    chunk_text,
    extract_local_document,
    normalize_review_forms,
    supported_evidence_files,
    utc_now,
    write_local_artifacts,
)
from b2_automation.ooxml_writer import patch_docx_cells

DEFAULT_REQUIRED_FIELDS = ("tco_name", "pitp_id", "car_type")
DEFAULT_LOW_CONFIDENCE_THRESHOLD = 0.70


@dataclass(frozen=True)
class InboxPipelineResult:
    run_dir: Path
    manifest_path: Path
    review_json_path: Path
    review_md_path: Path
    filled_docx_path: Path | None
    status: str


def _utc_now() -> str:
    return utc_now()


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _safe_stem(path: Path) -> str:
    return "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in path.stem)[:120]


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "y", "required"}


def _required_fields_from_manifest(manifest: dict[str, Any], fallback: tuple[str, ...]) -> tuple[str, ...]:
    required = [str(spec["field_id"]) for spec in manifest.get("cells", []) if _truthy(spec.get("required"))]
    return tuple(dict.fromkeys(required or list(fallback)))


def _load_raw_extraction(pdf: Path) -> dict[str, Any]:
    raw = process_pdf(pdf)
    if isinstance(raw, str):
        return json.loads(raw)
    if isinstance(raw, dict):
        return raw
    raise TypeError(f"DocuPipe client returned unsupported type: {type(raw)!r}")


def _field_confidences(raw: dict[str, Any]) -> dict[str, float]:
    rows = ((raw.get("result") or {}).get("field_extractions") or [])
    out: dict[str, float] = {}
    if not isinstance(rows, list):
        return out
    from b2_automation.b24_normalizer import _FIELD_KEY_TO_MANIFEST

    for row in rows:
        if not isinstance(row, dict):
            continue
        key = row.get("field_key") or row.get("normalized_key") or ""
        manifest_key = _FIELD_KEY_TO_MANIFEST.get(key)
        if not manifest_key:
            continue
        conf = row.get("confidence")
        if conf is None:
            continue
        try:
            out[manifest_key] = max(out.get(manifest_key, 0.0), float(conf))
        except (TypeError, ValueError):
            continue
    return out


def _field_sources(raw: dict[str, Any], source_file: str) -> dict[str, dict[str, Any]]:
    rows = ((raw.get("result") or {}).get("field_extractions") or [])
    out: dict[str, dict[str, Any]] = {}
    if not isinstance(rows, list):
        return out
    from b2_automation.b24_normalizer import _FIELD_KEY_TO_MANIFEST

    for row in rows:
        if not isinstance(row, dict):
            continue
        key = row.get("field_key") or row.get("normalized_key") or ""
        manifest_key = _FIELD_KEY_TO_MANIFEST.get(key)
        if not manifest_key:
            continue
        provenance = row.get("provenance") or []
        first = provenance[0] if isinstance(provenance, list) and provenance and isinstance(provenance[0], dict) else {}
        page = first.get("page_index")
        try:
            page = int(page) if page is not None else None
        except (TypeError, ValueError):
            page = None
        confidence = row.get("confidence")
        try:
            confidence = float(confidence) if confidence is not None else None
        except (TypeError, ValueError):
            confidence = None
        prior = out.get(manifest_key)
        if prior is None or (confidence or 0.0) >= (prior.get("confidence") or 0.0):
            out[manifest_key] = {"source_file": source_file, "source_page": page, "confidence": confidence, "field_key": key}
    return out


def _merge_field_values(records: list[dict[str, Any]]) -> tuple[dict[str, str], dict[str, float], dict[str, dict[str, Any]], list[dict[str, Any]]]:
    by_field: dict[str, list[dict[str, Any]]] = {}
    for rec in records:
        values = rec.get("field_values") or {}
        confs = rec.get("confidences") or {}
        sources = rec.get("sources") or {}
        for field_id, value in values.items():
            if field_id == "evidence_notes":
                continue
            if value is None or str(value).strip() == "":
                continue
            src = sources.get(field_id) or {}
            by_field.setdefault(field_id, []).append(
                {
                    "value": str(value).strip(),
                    "source_file": src.get("source_file") or rec["source_file"],
                    "source_page": src.get("source_page"),
                    "confidence": confs.get(field_id),
                }
            )

    merged: dict[str, str] = {}
    merged_confidences: dict[str, float] = {}
    merged_sources: dict[str, dict[str, Any]] = {}
    decisions: list[dict[str, Any]] = []
    for field_id, candidates in sorted(by_field.items()):
        unique_values = sorted({c["value"] for c in candidates})
        if len(unique_values) == 1:
            best = max(candidates, key=lambda x: x.get("confidence") or 0.0)
            merged[field_id] = unique_values[0]
            if best.get("confidence") is not None:
                merged_confidences[field_id] = float(best["confidence"])
            merged_sources[field_id] = {"source_file": best.get("source_file"), "source_page": best.get("source_page")}
            decisions.append({"field_id": field_id, "status": "filled", "selected_value": unique_values[0], "candidates": candidates})
        else:
            merged[field_id] = f"{REVIEW_REQUIRED_TEXT}: conflicting source values"
            decisions.append({"field_id": field_id, "status": "conflict", "selected_value": merged[field_id], "candidates": candidates})

    notes = []
    for rec in records:
        ev = (rec.get("field_values") or {}).get("evidence_notes")
        if ev:
            notes.append(f"SOURCE FILE: {rec['source_file']}\n{ev}")
    merged["evidence_notes"] = "\n\n".join(notes)
    return merged, merged_confidences, merged_sources, decisions


def _cell_role(spec: dict[str, Any]) -> str:
    fid = str(spec.get("field_id", ""))
    role = str(spec.get("cell_role") or spec.get("role") or "target").strip().lower()
    if fid == "evidence_notes" or "note" in role:
        return "notes"
    return role or "target"


def _build_cell_inventory_report(
    manifest: dict[str, Any],
    field_values: dict[str, str],
    field_confidences: dict[str, float],
    field_sources: dict[str, dict[str, Any]],
    required_fields: tuple[str, ...],
    threshold: float,
) -> list[dict[str, Any]]:
    required_set = set(required_fields)
    rows: list[dict[str, Any]] = []
    for spec in manifest.get("cells", []):
        fid = str(spec["field_id"])
        required = fid in required_set or _truthy(spec.get("required"))
        value = field_values.get(fid)
        confidence = field_confidences.get(fid)
        conflict = isinstance(value, str) and value.startswith(REVIEW_REQUIRED_TEXT)
        role = _cell_role(spec)
        decision = decide_cell(value, confidence=confidence, threshold=threshold, required=required, conflict_detected=conflict, cell_role="target" if role == "notes" else role)
        if decision == "fill":
            status = "filled"
        elif decision == "blank":
            status = "blank_optional"
        elif required and (value is None or str(value).strip() == ""):
            status = "blank_required_MISSING"
        elif conflict:
            status = "review_required_conflict"
        else:
            status = "review_required"
        src = field_sources.get(fid) or {}
        rows.append(
            {
                "field_id": fid,
                "label": spec.get("label") or spec.get("cell_label") or "",
                "table_index": int(spec["table_index"]),
                "row": int(spec["row"]),
                "col": int(spec["col"]),
                "required": required,
                "cell_role": role,
                "decision": decision,
                "status": status,
                "value": value,
                "confidence": confidence,
                "source_file": src.get("source_file"),
                "source_page": src.get("source_page"),
            }
        )
    return rows




def _inventory_status_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        key = str(row.get("status") or "unknown")
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items()))

def _write_review_md(path: Path, review: dict[str, Any]) -> None:
    lines = [
        "# B24 RL1 Review Report",
        "",
        f"Run status: **{review['status']}**",
        f"Generated: {review['generated_at']}",
        "",
        "## Inputs",
    ]
    for item in review["inputs"]:
        lines.append(f"- {item['source_file']} — {item['status']}")
    lines.extend([
        "",
        "## Cell inventory accounting",
        "",
        "| Field ID | Cell | Required | Status | Value | Confidence | Source |",
        "|---|---:|---:|---|---|---:|---|",
    ])
    for item in review.get("cell_inventory_report", []):
        cell = f"T{item['table_index']} R{item['row']} C{item['col']}"
        value = str(item.get("value") or "").replace("\n", "<br>")
        if len(value) > 160:
            value = value[:157] + "..."
        conf = "" if item.get("confidence") is None else f"{float(item['confidence']):.2f}"
        source = item.get("source_file") or ""
        if item.get("source_page") is not None:
            source = f"{source} p.{item['source_page']}"
        lines.append(f"| {item['field_id']} | {cell} | {item['required']} | {item['status']} | {value} | {conf} | {source} |")
    lines.extend(["", "## Inventory summary"])
    summary = review.get("cell_inventory_summary") or {}
    if summary:
        for key, val in summary.items():
            lines.append(f"- {key}: {val}")
    else:
        lines.append("- None")
    lines.extend(["", "## Missing required fields"])
    if review["missing_required_fields"]:
        lines.extend(f"- {x}" for x in review["missing_required_fields"])
    else:
        lines.append("- None")
    lines.extend(["", "## Low confidence fields"])
    if review["low_confidence_fields"]:
        for item in review["low_confidence_fields"]:
            lines.append(f"- {item['field_id']} ({item['confidence']}) from {item['source_file']}")
    else:
        lines.append("- None")
    lines.extend(["", "## Conflicts"])
    conflicts = [d for d in review["field_decisions"] if d["status"] == "conflict"]
    if conflicts:
        for d in conflicts:
            lines.append(f"- {d['field_id']}: {d['selected_value']}")
    else:
        lines.append("- None")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _run_local_rag_inbox_pipeline(
    *,
    inbox: Path,
    out_dir: Path,
    review_forms: tuple[str, ...] | None,
) -> InboxPipelineResult:
    inbox = inbox.resolve()
    run_dir = out_dir.resolve()
    raw_dir = run_dir / "raw"
    review_dir = run_dir / "review"
    filled_dir = run_dir / "filled"
    for p in (raw_dir, review_dir, filled_dir):
        p.mkdir(parents=True, exist_ok=True)

    inputs = supported_evidence_files(inbox)
    if not inputs:
        allowed = ", ".join((".pdf", ".txt", ".md", ".json", ".csv"))
        raise FileNotFoundError(f"No supported local evidence files found in inbox: {inbox} ({allowed})")

    forms = normalize_review_forms(review_forms)
    documents = [extract_local_document(path) for path in inputs]
    chunks_by_source = {doc.source_file: chunk_text(doc.text) for doc in documents}
    packets = build_form_packets(documents, chunks_by_source, forms)
    artifact_index = write_local_artifacts(
        raw_dir=raw_dir,
        review_dir=review_dir,
        documents=documents,
        chunks_by_source=chunks_by_source,
        packets=packets,
    )

    review_json = review_dir / "local_rag_review.json"
    review_md = review_dir / "local_rag_review.md"
    manifest_path = run_dir / "run_manifest.json"
    rag_selection_path = run_dir / "rag_selection_report.json"

    missing_context = [form for form, packet in packets.items() if not packet["retrieved_context"]]
    status = "review_required" if missing_context else "success"
    review = {
        "generated_at": _utc_now(),
        "status": status,
        "mode": "local_rag_extraction",
        "docupipe_used": False,
        "legacy_adapter_used": False,
        "forms": list(forms),
        "first_class_forms": list(DEFAULT_REVIEW_FORMS),
        "legacy_sample_forms": ["B24_RL1"],
        "inputs": [
            {
                "source_file": doc.source_file,
                "sha256": doc.sha256,
                "extraction_method": doc.extraction_method,
                "status": "extracted",
            }
            for doc in documents
        ],
        "form_packets": packets,
        "missing_context_forms": missing_context,
        "write_authority": "review only; exact approval maps are required before safe DOCX patching",
    }
    review_json.write_text(json.dumps(review, indent=2, sort_keys=True), encoding="utf-8")

    lines = [
        "# Local RAG Inbox Review",
        "",
        f"Run status: **{status}**",
        f"Generated: {review['generated_at']}",
        "",
        "## Forms",
    ]
    lines.extend(f"- {form}" for form in forms)
    lines.extend(["", "## Inputs"])
    lines.extend(f"- {item['source_file']} ({item['extraction_method']})" for item in review["inputs"])
    lines.extend(["", "## DOCX writing"])
    lines.append("- No DOCX was filled by the local review path.")
    lines.append("- Exact approval maps and the safe OOXML patcher are required before filled files are handed off.")
    review_md.write_text("\n".join(lines) + "\n", encoding="utf-8")

    rag_selection = {
        "selected_approval_map": "",
        "form_id": "",
        "form_version": "",
        "retrieved_context_used": list(artifact_index["per_form_reviews"].keys()),
        "rejected_candidates": [],
        "decision": "review_only_no_docx_fill",
        "uncertainty": "Exact per-form/version approval maps are not selected by the local inbox review step.",
    }
    rag_selection_path.write_text(json.dumps(rag_selection, indent=2, sort_keys=True), encoding="utf-8")

    run_manifest = {
        "status": status,
        "mode": "local_rag_extraction",
        "docupipe_used": False,
        "legacy_adapter_used": False,
        "ocr_engine": "local text/PDF extraction; OCR hooks only",
        "llm_runner": "not required for deterministic local review",
        "embedding_model": "lexical local retrieval",
        "vector_db": "none",
        "forms": list(forms),
        "b24_rl1_default": False,
        "review_json": str(review_json),
        "review_markdown": str(review_md),
        "rag_selection_report": str(rag_selection_path),
        "artifacts": artifact_index,
        "outputs": [str(review_json), str(review_md), str(rag_selection_path), str(artifact_index["aggregate_review_path"])],
    }
    manifest_path.write_text(json.dumps(run_manifest, indent=2, sort_keys=True), encoding="utf-8")

    return InboxPipelineResult(run_dir, manifest_path, review_json, review_md, None, status)


def run_inbox_pipeline(
    *,
    root: Path,
    inbox: Path,
    out_dir: Path,
    required_fields: tuple[str, ...] | None = None,
    low_confidence_threshold: float = DEFAULT_LOW_CONFIDENCE_THRESHOLD,
    legacy_docupipe: bool = False,
    review_forms: tuple[str, ...] | None = None,
) -> InboxPipelineResult:
    if not legacy_docupipe:
        return _run_local_rag_inbox_pipeline(inbox=inbox, out_dir=out_dir, review_forms=review_forms)

    inbox = inbox.resolve()
    out_dir = out_dir.resolve()
    run_dir = out_dir
    raw_dir = run_dir / "raw"
    filled_dir = run_dir / "filled"
    review_dir = run_dir / "review"
    failed_dir = run_dir / "failed"
    for p in (raw_dir, filled_dir, review_dir, failed_dir):
        p.mkdir(parents=True, exist_ok=True)

    pdfs = sorted(inbox.glob("*.pdf"))
    if not pdfs:
        raise FileNotFoundError(f"No PDF files found in inbox: {inbox}")

    manifest = load_manifest(root / "schemas" / "templates" / "B24_RL1.json")
    active_required_fields = tuple(required_fields) if required_fields is not None else _required_fields_from_manifest(manifest, DEFAULT_REQUIRED_FIELDS)

    records: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    for pdf in pdfs:
        started = _utc_now()
        rec: dict[str, Any] = {
            "source_file": pdf.name,
            "source_path": str(pdf),
            "sha256": _sha256(pdf),
            "started_at": started,
            "status": "unknown",
        }
        try:
            raw = _load_raw_extraction(pdf)
            raw_path = raw_dir / f"{_safe_stem(pdf)}.docupipe.json"
            raw_path.write_text(json.dumps(raw, indent=2, sort_keys=True), encoding="utf-8")
            meta_path = raw_dir / f"{_safe_stem(pdf)}.metadata.json"
            meta = {
                "source_file": pdf.name,
                "sha256": rec["sha256"],
                "submitted_at": started,
                "completed_at": _utc_now(),
                "raw_json_path": str(raw_path),
                "status": "completed",
            }
            meta_path.write_text(json.dumps(meta, indent=2, sort_keys=True), encoding="utf-8")
            rec["raw_json_path"] = str(raw_path)
            rec["metadata_path"] = str(meta_path)
            rec["field_values"] = normalize_docupipe_payload_for_b24_rl1(raw)
            rec["confidences"] = _field_confidences(raw)
            rec["sources"] = _field_sources(raw, pdf.name)
            rec["status"] = "extracted"
            records.append(rec)
        except Exception as exc:
            rec["status"] = "failed"
            rec["error"] = str(exc)
            fail_path = failed_dir / f"{_safe_stem(pdf)}.error.json"
            fail_path.write_text(json.dumps(rec, indent=2, sort_keys=True), encoding="utf-8")
            failures.append(rec)

    merged_values, merged_confidences, merged_sources, decisions = _merge_field_values(records)
    missing = [
        field
        for field in active_required_fields
        if merged_values.get(field) is None or str(merged_values.get(field)).strip() == ""
    ]
    low_confidence: list[dict[str, Any]] = []
    for field_id, conf in merged_confidences.items():
        if conf < low_confidence_threshold:
            src = merged_sources.get(field_id) or {}
            low_confidence.append(
                {
                    "field_id": field_id,
                    "confidence": conf,
                    "source_file": src.get("source_file"),
                    "source_page": src.get("source_page"),
                }
            )

    cell_inventory_report = _build_cell_inventory_report(manifest, merged_values, merged_confidences, merged_sources, active_required_fields, low_confidence_threshold)

    status = "success"
    if failures or missing or low_confidence or any(d["status"] == "conflict" for d in decisions) or any(row["status"] in {"blank_required_MISSING", "review_required", "review_required_conflict"} for row in cell_inventory_report):
        status = "review_required"

    filled_docx: Path | None = None
    if records:
        template = root / "templates" / "B24_RL1.docx"
        candidate_filled_docx = filled_dir / "B24_RL1_filled.docx"
        structure_guard_report = run_dir / "structure_guard_report.json"
        patch_outcome = patch_docx_cells(
            template,
            manifest,
            merged_values,
            candidate_filled_docx,
            field_confidences=merged_confidences,
            required_field_ids=set(active_required_fields),
            low_confidence_threshold=low_confidence_threshold,
            structure_guard_report_path=structure_guard_report,
        )
        if patch_outcome.structure_guard_passed:
            filled_docx = patch_outcome.output_docx
        else:
            filled_docx = None
            status = "review_required"

    review = {
        "generated_at": _utc_now(),
        "status": status,
        "inputs": records + failures,
        "field_decisions": decisions,
        "cell_inventory_report": cell_inventory_report,
        "cell_inventory_summary": _inventory_status_counts(cell_inventory_report),
        "required_fields": list(active_required_fields),
        "missing_required_fields": missing,
        "low_confidence_fields": low_confidence,
        "filled_docx": str(filled_docx) if filled_docx else None,
        "structure_guard_report": str(run_dir / "structure_guard_report.json") if records else None,
    }
    review_json = review_dir / "B24_RL1_review.json"
    review_md = review_dir / "B24_RL1_review.md"
    manifest_path = run_dir / "run_manifest.json"
    review_json.write_text(json.dumps(review, indent=2, sort_keys=True), encoding="utf-8")
    _write_review_md(review_md, review)
    run_manifest = {
        "status": status,
        "mode": "legacy_docupipe_b24_rl1",
        "docupipe_used": True,
        "legacy_adapter_used": True,
        "inputs": records + failures,
        "review_json": str(review_json),
        "required_fields": list(active_required_fields),
        "missing_required_fields": missing,
        "cell_inventory_summary": review["cell_inventory_summary"],
        "filled_docx": str(filled_docx) if filled_docx else None,
        "structure_guard_report": review["structure_guard_report"],
    }
    manifest_path.write_text(json.dumps(run_manifest, indent=2, sort_keys=True), encoding="utf-8")

    return InboxPipelineResult(run_dir, manifest_path, review_json, review_md, filled_docx, status)
