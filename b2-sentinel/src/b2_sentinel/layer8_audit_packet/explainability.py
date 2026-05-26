"""Per-field auditor-grade explainability sentences.

Spec example:
    car.mark was filled with UTLX 213220 because the value was extracted
    from URBC 2025.pdf page 2, matched the car_number pattern, bridged
    through the approved car_number -> car.mark alias, and the B89
    exact approval map authorized the target cell.

    pitp.id remains REVIEW_REQUIRED because no PITP ID, procedure ID,
    or inspection test plan identifier was found in the evidence
    package. This is a completion blocker, not a structure failure.
"""
from __future__ import annotations

from ..core.models import (
    EvidenceLedgerEntry,
    FieldDecision,
    FieldNode,
)
from ..core.status import DecisionState


def explain(
    *,
    form_id: str,
    node: FieldNode,
    decision: FieldDecision,
    entry: EvidenceLedgerEntry | None,
) -> str:
    fid = node.field_id
    if decision.state is DecisionState.FILL and entry and decision.value:
        alias_phrase = f", bridged through the approved {entry.alias_used} -> {fid} alias" if entry.alias_used else ""
        page_phrase = f" page {entry.page}" if entry.page else ""
        return (
            f"{fid} was filled with {decision.value!r} because the value was extracted from "
            f"{entry.source_file}{page_phrase}{alias_phrase}, "
            f"and the {form_id} exact approval map authorized the target cell."
        )
    if decision.state is DecisionState.APPROVED_NA:
        return (
            f"{fid} was marked N/A because no evidence was found and the form's approved "
            f"N/A exception policy permits this exception. This is not a completion blocker."
        )
    if decision.state is DecisionState.REVIEW_REQUIRED:
        return (
            f"{fid} remains REVIEW_REQUIRED because no extracted value matched "
            f"the obligation graph for this required field. This is a completion blocker, "
            f"not a structure failure."
        )
    if decision.state is DecisionState.CONFLICT:
        alts = ", ".join(a.get("value", "?") for a in (entry.alternates if entry else []))
        return (
            f"{fid} is a CONFLICT: multiple distinct candidate values found ({alts}). "
            f"The Writer refuses to pick; manual disambiguation required."
        )
    if decision.state is DecisionState.LOW_CONFIDENCE:
        return (
            f"{fid} is LOW_CONFIDENCE: evidence was found but write-confidence is below threshold. "
            f"Refusing to fill without human review."
        )
    if decision.state is DecisionState.BLOCKED_NO_SOURCE:
        return (
            f"{fid} is BLOCKED_NO_SOURCE: required, no evidence in scope, no approved N/A. "
            f"This is a hard completion blocker."
        )
    if decision.state is DecisionState.BLOCKED_UNAUTHORIZED:
        return (
            f"{fid} is BLOCKED_UNAUTHORIZED: a candidate value exists, but the exact approval map "
            f"does not authorize writes to this cell. SENTINEL refuses on principle."
        )
    if decision.state is DecisionState.OPTIONAL_BLANK:
        return f"{fid} was left blank because it is optional and no evidence was found."
    return f"{fid} state={decision.state.value}: {decision.reason}"
