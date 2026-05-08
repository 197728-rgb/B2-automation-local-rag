"""First-class evidence artifacts: canonical summary and field-level traceability.

Retrieval/RAG may suggest values only. Approval maps alone authorize write targets.
This module never infers coordinates from retrieval scores.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from b2_automation.approval_maps import load_exact_approval_bundle_checked
from b2_automation.cell_evidence import DecisionState


def _reviewer_status(state: str) -> str:
    return {
        DecisionState.FILL.value: "ok",
        DecisionState.BLANK.value: "blank_optional",
        DecisionState.MISSING.value: "missing",
        DecisionState.CONFLICT.value: "conflict",
        DecisionState.LOW_CONFIDENCE.value: "low_confidence",
        DecisionState.REVIEW_REQUIRED.value: "review_required",
    }.get(state, "unknown")


def _candidate_values_from_decision(dec: dict[str, Any]) -> list[str]:
    vals: set[str] = set()
    for c in dec.get("candidates") or []:
        v = str(c.get("candidate_value") or "").strip()
        if v:
            vals.add(v)
    return sorted(vals)


def _provenance_summary(dec: dict[str, Any]) -> str:
    parts: list[str] = []
    for c in dec.get("candidates") or []:
        src = str(c.get("source_file") or "")
        page = c.get("source_page")
        chunk_id = c.get("chunk_id")
        if src:
            s = src
            if page is not None:
                s += f" p.{page}"
            if chunk_id is not None:
                s += f" chunk={chunk_id}"
            parts.append(s)
    return "; ".join(sorted(set(parts))) if parts else ""


def _build_trace_entries_for_form(
    form_id: str,
    packet: dict[str, Any],
    approval_fields: dict[str, Any] | None,
    template_name: str | None,
    docx_row: dict[str, Any] | None,
    patched: set[str],
) -> list[dict[str, Any]]:
    """One trace row per suggestion candidate, plus synthetic rows for decisions with no candidates."""
    entries: list[dict[str, Any]] = []
    decisions_by_field: dict[str, dict[str, Any]] = {}
    for dec in packet.get("field_decisions", []):
        decisions_by_field[str(dec["field_id"])] = dec

    seen_pairs: set[tuple[str, str, int | str]] = set()
    for sug in packet.get("field_suggestions", []):
        fid = str(sug.get("field_id") or "")
        dec = decisions_by_field.get(fid, {})
        state = str(dec.get("state") or "")
        appr = approval_fields.get(fid) if approval_fields else None
        approval_map_target: dict[str, Any] | None = None
        if isinstance(appr, dict):
            approval_map_target = {
                "template": template_name,
                "table_index": appr.get("table_index"),
                "row": appr.get("row"),
                "col": appr.get("col"),
            }

        authorized = bool(appr and state == DecisionState.FILL.value)
        chunk_id = sug.get("chunk_id")
        pair = (fid, str(sug.get("candidate_value")), chunk_id if chunk_id is not None else -1)
        if pair in seen_pairs:
            continue
        seen_pairs.add(pair)

        filled = bool((fid in patched) and state == DecisionState.FILL.value)
        block = _fill_block_reason(
            state=state,
            authorized=authorized,
            docx_row=docx_row,
            fid=fid,
            had_map=bool(approval_fields),
        )
        entries.append(
            {
                "form_id": form_id,
                "field_id": fid,
                "suggested_value": str(sug.get("candidate_value") or ""),
                "selected_value": dec.get("selected_value"),
                "decision_state": state,
                "source_file": sug.get("source_file"),
                "source_page": sug.get("source_page"),
                "chunk_id": chunk_id,
                "chunk_hash": sug.get("chunk_hash"),
                "chunk_excerpt": sug.get("chunk_excerpt") or _excerpt_from_retrieval(packet, fid, chunk_id),
                "retrieval_score": sug.get("retrieval_score") if sug.get("retrieval_score") is not None else sug.get("score"),
                "confidence": sug.get("confidence") if sug.get("confidence") is not None else dec.get("confidence"),
                "reviewer_status": _reviewer_status(state),
                "approval_map_target": approval_map_target,
                "authorized_for_write": authorized,
                "filled": filled,
                "fill_block_reason": None if filled else block,
            }
        )

    for fid, dec in decisions_by_field.items():
        if any(str(s.get("field_id")) == fid for s in packet.get("field_suggestions", [])):
            continue
        state = str(dec.get("state") or "")
        appr = approval_fields.get(fid) if approval_fields else None
        approval_map_target: dict[str, Any] | None = None
        if isinstance(appr, dict):
            approval_map_target = {
                "template": template_name,
                "table_index": appr.get("table_index"),
                "row": appr.get("row"),
                "col": appr.get("col"),
            }
        authorized = bool(appr and state == DecisionState.FILL.value)
        filled = bool((fid in patched) and state == DecisionState.FILL.value)
        block = _fill_block_reason(
            state=state,
            authorized=authorized,
            docx_row=docx_row,
            fid=fid,
            had_map=bool(approval_fields),
        )
        entries.append(
            {
                "form_id": form_id,
                "field_id": fid,
                "suggested_value": None,
                "selected_value": dec.get("selected_value"),
                "decision_state": state,
                "source_file": None,
                "source_page": None,
                "chunk_id": None,
                "chunk_hash": None,
                "chunk_excerpt": None,
                "retrieval_score": None,
                "confidence": dec.get("confidence"),
                "reviewer_status": _reviewer_status(state),
                "approval_map_target": approval_map_target,
                "authorized_for_write": authorized,
                "filled": filled,
                "fill_block_reason": None if filled else block,
            }
        )

    return entries


def _excerpt_from_retrieval(packet: dict[str, Any], field_id: str, chunk_id: Any) -> str | None:
    if chunk_id is None:
        return None
    for row in packet.get("retrieved_context", []) or []:
        if int(row.get("chunk_id") or -1) == int(chunk_id):
            return str(row.get("chunk_excerpt") or row.get("text") or "")[:500] or None
    return None


def _fill_block_reason(
    *,
    state: str,
    authorized: bool,
    docx_row: dict[str, Any] | None,
    fid: str,
    had_map: bool,
) -> str | None:
    if state != DecisionState.FILL.value:
        return f"decision_not_fill:{state}"
    if not had_map:
        return "no_exact_approval_map"
    if not authorized:
        return "field_not_in_approval_map"
    if not docx_row:
        return "docx_not_attempted"
    st = str(docx_row.get("status") or "")
    if st == "skipped_missing_exact_approval_map":
        return "skipped_missing_exact_approval_map"
    if st == "skipped_missing_template":
        return "skipped_missing_template"
    if st == "skipped_no_matching_manifest_cells":
        return "skipped_no_matching_manifest_cells"
    if st == "discarded_structure_guard_failed":
        return "structure_guard_failed"
    if st == "skipped_no_fill_decisions":
        return "skipped_no_fill_decisions"
    if docx_row.get("structure_guard_passed") is False:
        return "structure_guard_failed"
    if fid not in (docx_row.get("patched_fields") or []):
        return "field_not_patched"
    return None


def build_canonical_evidence_document(
    *,
    forms: tuple[str, ...],
    packets: dict[str, dict[str, Any]],
    docx_results: list[dict[str, Any]],
    root: Path,
) -> dict[str, Any]:
    """Deterministic per-field canonical rows for all review forms."""
    docx_by_form = {str(r["form_id"]): r for r in docx_results}
    fields_out: list[dict[str, Any]] = []

    for form_id in forms:
        packet = packets[form_id]
        drow = docx_by_form.get(form_id)
        bundle_result = load_exact_approval_bundle_checked(root, form_id)
        approval_fields = bundle_result.bundle.approval_map.get("fields") if bundle_result.bundle else None
        if not isinstance(approval_fields, dict):
            approval_fields = None
        template_name = None
        if bundle_result.bundle and bundle_result.bundle.template_path.is_file():
            template_name = bundle_result.bundle.template_path.name

        patched: set[str] = set()
        if drow and drow.get("patched_fields"):
            patched = set(str(x) for x in drow["patched_fields"])

        for dec in packet.get("field_decisions", []):
            fid = str(dec["field_id"])
            state = str(dec.get("state") or "")
            appr = approval_fields.get(fid) if approval_fields else None
            authorized = bool(appr and state == DecisionState.FILL.value)
            filled = fid in patched and state == DecisionState.FILL.value
            block = _fill_block_reason(
                state=state,
                authorized=authorized,
                docx_row=drow,
                fid=fid,
                had_map=bool(approval_fields),
            )
            if filled:
                block = None

            fields_out.append(
                {
                    "form_id": form_id,
                    "field_id": fid,
                    "candidate_values": _candidate_values_from_decision(dec),
                    "selected_value": dec.get("selected_value"),
                    "decision_state": state,
                    "confidence": dec.get("confidence"),
                    "reviewer_status": _reviewer_status(state),
                    "provenance_summary": _provenance_summary(dec),
                    "filled": filled,
                    "fill_block_reason": block,
                }
            )

    return {
        "schema": "canonical_evidence.v1",
        "fields": fields_out,
    }


def build_field_traceability_document(
    *,
    forms: tuple[str, ...],
    packets: dict[str, dict[str, Any]],
    docx_results: list[dict[str, Any]],
    root: Path,
) -> dict[str, Any]:
    """Per-suggestion and per-field lineage; retrieval never authorizes writes."""
    docx_by_form = {str(r["form_id"]): r for r in docx_results}
    entries: list[dict[str, Any]] = []

    for form_id in forms:
        packet = packets[form_id]
        drow = docx_by_form.get(form_id)
        bundle_result = load_exact_approval_bundle_checked(root, form_id)
        approval_fields = bundle_result.bundle.approval_map.get("fields") if bundle_result.bundle else None
        if not isinstance(approval_fields, dict):
            approval_fields = None
        template_name = None
        if bundle_result.bundle and bundle_result.bundle.template_path.is_file():
            template_name = bundle_result.bundle.template_path.name

        patched: set[str] = set()
        if drow and drow.get("patched_fields"):
            patched = set(str(x) for x in drow["patched_fields"])

        # Enrich suggestions with chunk_hash from retrieved_context
        chunk_by_id: dict[tuple[str, int], dict[str, Any]] = {}
        for row in packet.get("retrieved_context", []) or []:
            key = (str(row["source_file"]), int(row["chunk_id"]))
            chunk_by_id[key] = row

        enriched_suggestions: list[dict[str, Any]] = []
        for sug in packet.get("field_suggestions", []):
            s = dict(sug)
            key = (str(sug.get("source_file") or ""), int(sug.get("chunk_id") or 0))
            ctx = chunk_by_id.get(key)
            if ctx:
                if s.get("chunk_hash") is None:
                    s["chunk_hash"] = ctx.get("chunk_hash")
                if s.get("chunk_excerpt") is None:
                    s["chunk_excerpt"] = ctx.get("chunk_excerpt") or ctx.get("text")
            enriched_suggestions.append(s)

        pkt2 = {**packet, "field_suggestions": enriched_suggestions}
        entries.extend(
            _build_trace_entries_for_form(
                form_id,
                pkt2,
                approval_fields,
                template_name,
                drow,
                patched,
            )
        )

    return {
        "schema": "field_traceability.v1",
        "entries": entries,
        "retrieval_authorizes_writes": False,
    }


def build_legacy_b24_rl1_packet_from_review(review: Mapping[str, Any]) -> dict[str, Any]:
    """Shape a local-inbox-compatible packet from legacy DocuPipe cell inventory."""
    inv = review.get("cell_inventory_report") or []
    field_decisions: list[dict[str, Any]] = []
    for row in inv:
        if not isinstance(row, Mapping):
            continue
        field_decisions.append(
            {
                "field_id": str(row.get("field_id") or ""),
                "state": str(row.get("decision") or "BLANK"),
                "selected_value": row.get("value"),
                "confidence": row.get("confidence"),
                "reason": "",
                "candidates": [],
            }
        )
    return {
        "form_id": "B24_RL1",
        "field_decisions": field_decisions,
        "field_suggestions": [],
        "retrieved_context": [],
        "write_authority": "none; legacy DocuPipe path (B24_RL1 sample)",
    }


def build_legacy_docx_results(
    *,
    records: list[dict[str, Any]],
    template_path: Path | None,
    structure_guard_report_path: Path | None,
    filled_docx: Path | None,
    patch_attempted: bool,
    structure_guard_passed: bool | None,
    patched_fields: tuple[str, ...],
    patch_errors: tuple[str, ...],
) -> list[dict[str, Any]]:
    """Single-row docx_generation list for legacy B24_RL1 runs (no exact approval map)."""
    sgr = str(structure_guard_report_path) if structure_guard_report_path else None
    tpl = str(template_path) if template_path and template_path.is_file() else None
    if not records:
        return [
            {
                "form_id": "B24_RL1",
                "attempted": False,
                "status": "skipped_no_extracted_records",
                "approval_map": None,
                "template": tpl,
                "filled_docx": None,
                "structure_guard_report": sgr,
                "structure_guard_passed": False,
                "patched_fields": [],
                "errors": [],
            }
        ]
    if not patch_attempted:
        return [
            {
                "form_id": "B24_RL1",
                "attempted": False,
                "status": "skipped_no_patch",
                "approval_map": None,
                "template": tpl,
                "filled_docx": None,
                "structure_guard_report": sgr,
                "structure_guard_passed": False,
                "patched_fields": [],
                "errors": list(patch_errors),
            }
        ]
    filled = str(filled_docx) if filled_docx else None
    status = "filled" if structure_guard_passed and filled else "discarded_structure_guard_failed"
    failure_reason = None
    structure_guard_errors: list[str] = []
    if not structure_guard_passed:
        failure_reason = "structure_guard_failed"
        structure_guard_errors = list(patch_errors)
    row: dict[str, Any] = {
        "form_id": "B24_RL1",
        "attempted": True,
        "status": status,
        "approval_map": None,
        "template": tpl,
        "filled_docx": filled,
        "structure_guard_report": sgr,
        "structure_guard_passed": bool(structure_guard_passed),
        "patched_fields": list(patched_fields),
        "errors": list(patch_errors),
    }
    if failure_reason:
        row["failure_reason"] = failure_reason
        row["structure_guard_errors"] = structure_guard_errors
    return [row]
