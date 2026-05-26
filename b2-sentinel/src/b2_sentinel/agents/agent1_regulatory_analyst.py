"""Agent 1 - The Regulatory Analyst.

Inputs: form_id (and version)
Reads: blank DOCX + exact approval map + N/A policy + activity schema
Outputs: ObligationGraph + Write Authority Matrix + Completion Blocker Policy
Thinks: 'They are asking for X because rule Y requires evidence Z, and field A
        cannot be completed unless source B exists.'
"""
from __future__ import annotations

from dataclasses import dataclass

from ..core.models import ObligationGraph
from ..innovations.alias_brain import AliasBrain
from ..layer1_form_brain.obligation_graph import build_obligation_graph
from ..layer1_form_brain.write_authority import write_authority_matrix


@dataclass
class RegulatoryAnalystOutput:
    obligation_graph: ObligationGraph
    write_authority_matrix: dict[str, dict[str, object]]
    completion_blocker_field_ids: list[str]


def run_regulatory_analyst(form_id: str, *, form_version: str = "2026") -> RegulatoryAnalystOutput:
    alias_brain = AliasBrain.from_disk()
    aliases_for_form: dict[str, list[str]] = {}
    for rule in alias_brain.all_rules():
        if rule.forms and form_id not in rule.forms:
            continue
        aliases_for_form.setdefault(rule.to_field, []).append(rule.from_key)

    graph = build_obligation_graph(
        form_id,
        form_version=form_version,
        aliases_for_form=aliases_for_form,
    )
    matrix = write_authority_matrix_for(graph)
    blockers = [fid for fid, n in graph.fields.items() if n.completion_blocker_if_missing]
    return RegulatoryAnalystOutput(
        obligation_graph=graph,
        write_authority_matrix=matrix,
        completion_blocker_field_ids=sorted(blockers),
    )


def write_authority_matrix_for(graph: ObligationGraph) -> dict[str, dict[str, object]]:
    out: dict[str, dict[str, object]] = {}
    for fid, node in graph.fields.items():
        out[fid] = {
            "field_id": fid,
            "table_index": node.table_index,
            "row": node.row,
            "col": node.col,
            "required": node.required,
            "cell_role": node.cell_role,
            "label": node.label,
            "write_mode": node.write_mode,
            "authority": node.write_authority.value,
            "n_a_allowed": node.n_a_allowed,
            "completion_blocker_if_missing": node.completion_blocker_if_missing,
        }
    return out
