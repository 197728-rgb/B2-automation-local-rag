"""Audit Packet Generator - emits the complete final packet for one form.

Artifacts produced under outputs/<run_id>/<form_id>/:
    <form_id>_filled.docx
    review.json, review.md
    field_traceability.json
    source_evidence_index.json
    missing_required_fields.json
    conflicts.json
    low_confidence.json
    structure_guard_report.json
    completion_report.json
    manual_correction_log.json
    na_exception_log.json
    evidence_debt_ledger.json
    rollover_decisions.json   (only when prior packet provided)
    run_delta.json            (only when previous run found)
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..core.models import (
    CompletionReport,
    EvidenceDebtEntry,
    EvidenceLedger,
    FieldDecision,
    FieldTraceability,
    ManualCorrectionEntry,
    NAExceptionEntry,
    ObligationGraph,
    RolloverEntry,
    RunDelta,
    StructureGuardReport,
)
from ..core.status import DecisionState
from .explainability import explain


def write_packet(
    *,
    out_dir: Path,
    graph: ObligationGraph,
    ledger: EvidenceLedger,
    decisions: dict[str, FieldDecision],
    structure_report: StructureGuardReport,
    completion: CompletionReport,
    na_log: list[NAExceptionEntry],
    manual_corrections: list[ManualCorrectionEntry],
    debt_entries: list[EvidenceDebtEntry],
    rollover_entries: list[RolloverEntry],
    run_delta: RunDelta | None,
    filled_docx_path: Path | None,
) -> dict[str, str]:
    """Returns {artifact_name: relative_path}."""
    out_dir.mkdir(parents=True, exist_ok=True)
    artifacts: dict[str, str] = {}

    # Field traceability (also drives review.md)
    traceability: list[FieldTraceability] = []
    for fid, decision in decisions.items():
        node = graph.fields[fid]
        entry = decision.evidence_ref
        sentence = explain(form_id=graph.form_id, node=node, decision=decision, entry=entry)
        decision.explainability = sentence
        traceability.append(
            FieldTraceability(
                field_id=fid,
                final_state=decision.state,
                value=decision.value,
                source_file=entry.source_file if entry else None,
                page=entry.page if entry else None,
                chunk_id=entry.chunk_id if entry else None,
                confidence=decision.confidence,
                write_authority=decision.write_authority,
                explainability=sentence,
            )
        )

    artifacts["field_traceability.json"] = _write_json(
        out_dir / "field_traceability.json",
        {"form_id": graph.form_id, "fields": [t.model_dump(mode="json") for t in traceability]},
    )

    artifacts["review.json"] = _write_json(
        out_dir / "review.json",
        {
            "form_id": graph.form_id,
            "decisions": {fid: d.model_dump(mode="json") for fid, d in decisions.items()},
        },
    )

    artifacts["review.md"] = _write_text(
        out_dir / "review.md",
        _render_review_md(graph, decisions, completion, traceability),
    )

    artifacts["source_evidence_index.json"] = _write_json(
        out_dir / "source_evidence_index.json",
        {"form_id": graph.form_id, "sources": ledger.source_index},
    )

    missing = [
        fid for fid, d in decisions.items()
        if d.state in (DecisionState.BLOCKED_NO_SOURCE, DecisionState.REVIEW_REQUIRED)
        and graph.fields[fid].required
    ]
    artifacts["missing_required_fields.json"] = _write_json(
        out_dir / "missing_required_fields.json",
        {"form_id": graph.form_id, "fields": missing, "count": len(missing)},
    )

    conflicts = [
        {"field_id": fid, "decision": decisions[fid].model_dump(mode="json")}
        for fid in decisions if decisions[fid].state is DecisionState.CONFLICT
    ]
    artifacts["conflicts.json"] = _write_json(
        out_dir / "conflicts.json",
        {"form_id": graph.form_id, "conflicts": conflicts, "count": len(conflicts)},
    )

    low_conf = [
        {"field_id": fid, "decision": decisions[fid].model_dump(mode="json")}
        for fid in decisions if decisions[fid].state is DecisionState.LOW_CONFIDENCE
    ]
    artifacts["low_confidence.json"] = _write_json(
        out_dir / "low_confidence.json",
        {"form_id": graph.form_id, "low_confidence": low_conf, "count": len(low_conf)},
    )

    artifacts["structure_guard_report.json"] = _write_json(
        out_dir / "structure_guard_report.json",
        structure_report.model_dump(mode="json"),
    )

    artifacts["completion_report.json"] = _write_json(
        out_dir / "completion_report.json",
        completion.model_dump(mode="json"),
    )

    artifacts["manual_correction_log.json"] = _write_json(
        out_dir / "manual_correction_log.json",
        {"form_id": graph.form_id, "entries": [c.model_dump(mode="json") for c in manual_corrections]},
    )

    artifacts["na_exception_log.json"] = _write_json(
        out_dir / "na_exception_log.json",
        {"form_id": graph.form_id, "entries": [e.model_dump(mode="json") for e in na_log]},
    )

    artifacts["evidence_debt_ledger.json"] = _write_json(
        out_dir / "evidence_debt_ledger.json",
        {"form_id": graph.form_id, "entries": [d.model_dump(mode="json") for d in debt_entries]},
    )

    if rollover_entries:
        artifacts["rollover_decisions.json"] = _write_json(
            out_dir / "rollover_decisions.json",
            {"form_id": graph.form_id, "entries": [r.model_dump(mode="json") for r in rollover_entries]},
        )

    if run_delta is not None:
        artifacts["run_delta.json"] = _write_json(
            out_dir / "run_delta.json",
            run_delta.model_dump(mode="json"),
        )

    if filled_docx_path is not None and filled_docx_path.exists():
        artifacts[filled_docx_path.name] = str(filled_docx_path.name)

    return artifacts


def _write_json(path: Path, data: Any) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
    return path.name


def _write_text(path: Path, text: str) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path.name


def _render_review_md(
    graph: ObligationGraph,
    decisions: dict[str, FieldDecision],
    completion: CompletionReport,
    traceability: list[FieldTraceability],
) -> str:
    lines: list[str] = []
    lines.append(f"# B2 SENTINEL Review - {graph.form_id}")
    lines.append("")
    lines.append(f"- **Final status**: `{completion.final_status.value}`")
    lines.append(f"- **Overall passed**: {completion.overall_passed}")
    lines.append(f"- **Format passed**: {completion.overall_passed_format}")
    lines.append(f"- **Completion passed**: {completion.overall_passed_completion}")
    lines.append(f"- Required total: {completion.required_total} | filled: {completion.required_filled} | blocked: {completion.required_blocked}")
    lines.append(f"- REVIEW_REQUIRED: {completion.review_required_count} | CONFLICT: {completion.conflict_count} | LOW_CONFIDENCE: {completion.low_confidence_count}")
    lines.append(f"- BLOCKED_NO_SOURCE: {completion.blocked_no_source_count} | BLOCKED_UNAUTHORIZED: {completion.blocked_unauthorized_count} | APPROVED_NA: {completion.approved_na_count}")
    lines.append("")
    lines.append("## Per-field Findings")
    for t in traceability:
        lines.append(f"- **{t.field_id}** [`{t.final_state.value}`] - {t.explainability}")
    if completion.blockers:
        lines.append("")
        lines.append("## Blockers")
        for b in completion.blockers:
            lines.append(f"- {b}")
    return "\n".join(lines) + "\n"
