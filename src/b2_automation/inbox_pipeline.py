"""Inbox pipeline for local-first B-2 evidence review."""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from b2_automation.approval_maps import ApprovalBundle, load_exact_approval_bundle_checked
from b2_automation.evidence_outputs import (
    build_canonical_evidence_document,
    build_field_traceability_document,
)
from b2_automation.cell_evidence import DecisionState, parse_decision_state
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

DEFAULT_LOW_CONFIDENCE_THRESHOLD = 0.70


def _retrieval_summary(packets: dict[str, dict[str, Any]], forms: tuple[str, ...]) -> str:
    modes = sorted({str(packets.get(f, {}).get("retrieval_method") or "unknown") for f in forms})
    return "local semantic ranking: " + ", ".join(modes) + " (evidence-only; does not authorize writes)"


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


def _field_values_from_packet(packet: dict[str, Any]) -> tuple[dict[str, str], dict[str, float]]:
    values: dict[str, str] = {}
    confidences: dict[str, float] = {}
    for decision in packet.get("field_decisions", []):
        if parse_decision_state(decision.get("state")) != DecisionState.FILL:
            continue
        value = decision.get("selected_value")
        if value is None or str(value).strip() == "":
            continue
        field_id = str(decision["field_id"])
        values[field_id] = str(value).strip()
        if decision.get("confidence") is not None:
            confidences[field_id] = float(decision["confidence"])
    return values, confidences


def _manifest_cells_for_fill(bundle: ApprovalBundle, values: Mapping[str, str]) -> dict[str, Any]:
    """Include only manifest rows for FILL keys that exist in the exact approval map."""
    raw_fields = bundle.approval_map.get("fields") or {}
    approved_ids = {str(k) for k in raw_fields.keys()} if isinstance(raw_fields, dict) else set()
    cells: list[dict[str, Any]] = []
    for spec in bundle.manifest.get("cells") or []:
        fid = str(spec.get("field_id", ""))
        if fid not in values or fid not in approved_ids:
            continue
        cells.append(spec)
    return {**dict(bundle.manifest), "cells": cells}


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
            "errors": list(load_result.errors),
        }
        if not values:
            results.append(result)
            continue
        if bundle is None:
            result["status"] = "skipped_missing_exact_approval_map"
            results.append(result)
            continue
        if not bundle.template_path.is_file():
            result["status"] = "skipped_missing_template"
            results.append(result)
            continue

        fill_manifest = _manifest_cells_for_fill(bundle, values)
        if not fill_manifest.get("cells"):
            result["status"] = "skipped_no_matching_manifest_cells"
            result["errors"] = [
                "FILL field_ids must appear in manifest cells and in approval map fields with exact coordinates.",
            ]
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
            guard_payload: dict[str, Any] = {}
            if guard_path.is_file():
                guard_payload = json.loads(guard_path.read_text(encoding="utf-8"))
            result["failure_reason"] = "structure_guard_failed"
            result["structure_guard_errors"] = list(guard_payload.get("errors") or [])
            result["pass"] = guard_payload.get("pass")
        results.append(result)

    attempted = [item for item in results if item.get("attempted")]
    aggregate = {
        "pass": all(bool(item.get("structure_guard_passed")) for item in attempted) if attempted else True,
        "forms": results,
    }
    (run_dir / "structure_guard_report.json").write_text(json.dumps(aggregate, indent=2, sort_keys=True), encoding="utf-8")
    return results


def _run_local_rag_inbox_pipeline(
    *,
    root: Path,
    inbox: Path,
    out_dir: Path,
    review_forms: tuple[str, ...] | None,
    low_confidence_threshold: float,
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
    packets = build_form_packets(
        documents,
        chunks_by_source,
        forms,
        low_confidence_threshold=low_confidence_threshold,
    )
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
    docx_results = _write_local_filled_docx(
        root=root,
        run_dir=run_dir,
        filled_dir=filled_dir,
        packets=packets,
        low_confidence_threshold=low_confidence_threshold,
    )
    canonical_path = run_dir / "canonical_evidence.json"
    trace_path = run_dir / "field_traceability.json"
    canonical_path.write_text(
        json.dumps(
            build_canonical_evidence_document(forms=forms, packets=packets, docx_results=docx_results, root=root),
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    trace_path.write_text(
        json.dumps(
            build_field_traceability_document(forms=forms, packets=packets, docx_results=docx_results, root=root),
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    failed_docx = [item for item in docx_results if item.get("attempted") and not item.get("structure_guard_passed")]
    review_states = {
        decision.get("state")
        for packet in packets.values()
        for decision in packet.get("field_decisions", [])
        if decision.get("state")
        in {
            DecisionState.MISSING.value,
            DecisionState.CONFLICT.value,
            DecisionState.LOW_CONFIDENCE.value,
            DecisionState.REVIEW_REQUIRED.value,
        }
    }
    status = "review_required" if missing_context or failed_docx or review_states else "success"
    review = {
        "generated_at": _utc_now(),
        "status": status,
        "mode": "local_rag_extraction",
        "docupipe_used": False,
        "legacy_adapter_used": False,
        "forms": list(forms),
        "production_scope_forms": list(DEFAULT_REVIEW_FORMS),
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
        "decision_summary_by_form": {fid: packets[fid].get("decision_summary") for fid in forms},
        "write_authority": "exact approval maps required; only FILL decisions are passed to DOCX patching",
        "docx_generation": docx_results,
        "structure_guard_failed_forms": [
            item["form_id"] for item in docx_results if item.get("attempted") and not item.get("structure_guard_passed")
        ],
        "structure_guard_discard_detail": [
            {
                "form_id": item["form_id"],
                "failure_reason": item.get("failure_reason"),
                "structure_guard_errors": item.get("structure_guard_errors"),
            }
            for item in docx_results
            if item.get("failure_reason") == "structure_guard_failed"
        ],
        "approval_map_and_fill_errors": [
            {"form_id": item["form_id"], "errors": list(item.get("errors") or [])}
            for item in docx_results
            if item.get("errors")
        ],
        "canonical_evidence": str(canonical_path),
        "field_traceability": str(trace_path),
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
    if docx_results:
        for item in docx_results:
            lines.append(f"- {item['form_id']}: {item['status']}")
        discarded = [item for item in docx_results if item.get("failure_reason") == "structure_guard_failed"]
        if discarded:
            lines.extend(["", "## DOCX structure guard failures (filled output discarded)"])
            for item in discarded:
                lines.append(f"- **{item['form_id']}**: structure guard did not pass; candidate DOCX removed.")
                errs = item.get("structure_guard_errors") or []
                for msg in errs[:8]:
                    lines.append(f"  - {msg}")
    else:
        lines.append("- No DOCX generation attempted.")
    lines.append("- RAG evidence did not authorize write locations; exact approval maps did.")
    review_md.write_text("\n".join(lines) + "\n", encoding="utf-8")

    rag_selection = {
        "selected_approval_maps": [item.get("approval_map") for item in docx_results if item.get("approval_map")],
        "form_id": "",
        "form_version": "",
        "retrieved_context_used": list(artifact_index["per_form_reviews"].keys()),
        "rejected_candidates": [],
        "decision": "exact_maps_only_fill_decisions",
        "uncertainty": "Forms without exact approval maps or templates are skipped.",
    }
    rag_selection_path.write_text(json.dumps(rag_selection, indent=2, sort_keys=True), encoding="utf-8")

    guard_summary = json.loads((run_dir / "structure_guard_report.json").read_text(encoding="utf-8"))

    run_manifest = {
        "status": status,
        "mode": "local_rag_extraction",
        "docupipe_used": False,
        "legacy_adapter_used": False,
        "ocr_engine": "local text/PDF extraction; OCR hooks only",
        "llm_runner": "not required for deterministic local review",
        "embedding_model": _retrieval_summary(packets, forms),
        "vector_db": "none; local TF-IDF / keyword (no cloud index)",
        "forms": list(forms),
        "review_json": str(review_json),
        "review_markdown": str(review_md),
        "rag_selection_report": str(rag_selection_path),
        "docx_generation": docx_results,
        "structure_guard_failed_forms": [
            item["form_id"] for item in docx_results if item.get("attempted") and not item.get("structure_guard_passed")
        ],
        "structure_guard_report": str(run_dir / "structure_guard_report.json"),
        "structure_guard_passed": bool(guard_summary.get("pass")),
        "artifacts": artifact_index,
        "outputs": [
            str(canonical_path),
            str(trace_path),
            str(review_json),
            str(review_md),
            str(rag_selection_path),
            str(artifact_index["aggregate_review_path"]),
        ]
        + [str(item["filled_docx"]) for item in docx_results if item.get("filled_docx")],
    }
    manifest_path.write_text(json.dumps(run_manifest, indent=2, sort_keys=True), encoding="utf-8")

    first_filled = next((Path(str(item["filled_docx"])) for item in docx_results if item.get("filled_docx")), None)
    return InboxPipelineResult(run_dir, manifest_path, review_json, review_md, first_filled, status)


def run_inbox_pipeline(
    *,
    root: Path,
    inbox: Path,
    out_dir: Path,
    low_confidence_threshold: float = DEFAULT_LOW_CONFIDENCE_THRESHOLD,
    review_forms: tuple[str, ...] | None = None,
) -> InboxPipelineResult:
    return _run_local_rag_inbox_pipeline(
        root=root,
        inbox=inbox,
        out_dir=out_dir,
        review_forms=review_forms,
        low_confidence_threshold=low_confidence_threshold,
    )
