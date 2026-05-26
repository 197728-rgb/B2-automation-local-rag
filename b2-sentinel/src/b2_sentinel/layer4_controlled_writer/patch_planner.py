"""Patch Planner.

Translates a dict[field_id -> FieldDecision] into a PatchPlan that the
OOXML writer can apply. Only FILL and APPROVED_NA become writes; all
other states become 'blocked' entries so Layer 6 can audit them.
"""
from __future__ import annotations

from ..core.models import (
    FieldDecision,
    ObligationGraph,
    PatchInstruction,
    PatchPlan,
)
from ..core.status import DecisionState, WriteAuthority


def plan_writes(
    graph: ObligationGraph,
    decisions: dict[str, FieldDecision],
) -> PatchPlan:
    writes: list[PatchInstruction] = []
    n_a_inserts: list[PatchInstruction] = []
    blocked: list[FieldDecision] = []

    for fid, decision in decisions.items():
        node = graph.fields[fid]
        if decision.state is DecisionState.FILL and decision.value is not None:
            writes.append(
                PatchInstruction(
                    field_id=fid,
                    table_index=node.table_index,
                    row=node.row,
                    col=node.col,
                    value=decision.value,
                    write_mode=node.write_mode,
                    label_text=node.label,
                    authorized=decision.write_authority is WriteAuthority.EXACT_APPROVAL_MAP,
                )
            )
        elif decision.state is DecisionState.APPROVED_NA:
            n_a_inserts.append(
                PatchInstruction(
                    field_id=fid,
                    table_index=node.table_index,
                    row=node.row,
                    col=node.col,
                    value="N/A",
                    write_mode=node.write_mode,
                    label_text=node.label,
                    authorized=decision.write_authority is WriteAuthority.APPROVED_NA_INSERTION,
                )
            )
        elif decision.state is DecisionState.REVIEW_REQUIRED:
            writes.append(
                PatchInstruction(
                    field_id=fid,
                    table_index=node.table_index,
                    row=node.row,
                    col=node.col,
                    value="<<REVIEW_REQUIRED>>",
                    write_mode=node.write_mode,
                    label_text=node.label,
                    authorized=True,
                    write_authority=WriteAuthority.REVIEW_MARKER_INSERTION,
                )
            )
            blocked.append(decision)
        elif decision.state is DecisionState.OPTIONAL_BLANK:
            continue
        else:
            blocked.append(decision)

    return PatchPlan(form_id=graph.form_id, writes=writes, blocked=blocked, n_a_inserts=n_a_inserts)
