"""Self-Critique Loop (Innovation #6).

After writing, the agent re-ingests its own output and asks:
    Did I write what I intended?
    Did Word display the value visibly?
    Did content controls hide anything?
    Did any replacement hit the wrong duplicate?
    Did required blanks remain?
    Did completion status match the evidence?

Cognitive integration: after deterministic checks pass, the Adaptive
Self-Critique Judge reasons contextually about whether values make sense.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from ..cognitive.config import get_cognitive_config
from ..cognitive.self_critique import critique_form
from ..core.models import (
    CompletionReport,
    FieldDecision,
    ObligationGraph,
)
from ..core.status import DecisionState
from .visible_text import cell_visible_text


def self_critique(
    *,
    graph: ObligationGraph,
    decisions: dict[str, FieldDecision],
    filled_path: Path,
    completion: CompletionReport,
) -> dict[str, Any]:
    visible = cell_visible_text(filled_path)
    findings: list[dict[str, Any]] = []

    for fid, decision in decisions.items():
        node = graph.fields[fid]
        coord = (node.table_index, node.row, node.col)
        cell_text = visible.get(coord, "")

        if decision.state is DecisionState.FILL and decision.value:
            if decision.value not in cell_text:
                findings.append({
                    "field_id": fid,
                    "issue": "value_invisible",
                    "expected": decision.value,
                    "visible": cell_text[:120],
                })
            elif "<<REVIEW_REQUIRED>>" in cell_text:
                findings.append({
                    "field_id": fid,
                    "issue": "marker_overlap",
                    "visible": cell_text[:120],
                })
        if decision.state is DecisionState.APPROVED_NA and "N/A" not in cell_text:
            findings.append({
                "field_id": fid,
                "issue": "approved_na_not_visible",
                "visible": cell_text[:120],
            })
        if decision.state is DecisionState.REVIEW_REQUIRED and "<<REVIEW_REQUIRED>>" not in cell_text:
            findings.append({
                "field_id": fid,
                "issue": "review_marker_missing",
                "visible": cell_text[:120],
            })

    # Cognitive self-critique: contextual reasoning about filled values
    cognitive_findings: list[dict[str, Any]] = []
    config = get_cognitive_config()
    if config.is_component_enabled("self_critique"):
        filled_fields = [
            (graph.fields[fid], decision, visible.get(
                (graph.fields[fid].table_index, graph.fields[fid].row, graph.fields[fid].col), ""
            ))
            for fid, decision in decisions.items()
            if decision.state is DecisionState.FILL and decision.value
        ]
        if filled_fields:
            critique_results = critique_form(filled_fields, form_id=graph.form_id)
            for cr in critique_results:
                cognitive_findings.append({
                    "field_id": cr.field_id,
                    "issue": cr.issue,
                    "severity": cr.severity,
                    "recommendation": cr.recommendation,
                    "confidence": cr.confidence,
                    "source": "cognitive_self_critique",
                })
                if cr.severity == "error":
                    findings.append({
                        "field_id": cr.field_id,
                        "issue": f"cognitive_critique: {cr.issue}",
                        "visible": cr.cell_value or "",
                    })

    completion_consistent = (
        completion.required_blocked == 0 and not findings
    ) == completion.overall_passed_completion

    return {
        "findings": findings,
        "cognitive_findings": cognitive_findings,
        "completion_consistent": completion_consistent,
        "passed": not findings and completion_consistent,
    }
