"""Innovation 1 - Evidence Debt Accounting.

Every missing field becomes debt with: type, blocking flag,
recommended source, search terms, resolution paths.
"""
from __future__ import annotations

from ..core.models import (
    EvidenceDebtEntry,
    EvidenceLedger,
    FieldDecision,
    ObligationGraph,
)
from ..core.status import DecisionState


def compute_debt(
    graph: ObligationGraph,
    ledger: EvidenceLedger,
    decisions: dict[str, FieldDecision],
) -> list[EvidenceDebtEntry]:
    debt: list[EvidenceDebtEntry] = []
    for fid, decision in decisions.items():
        node = graph.fields[fid]
        if decision.state in {DecisionState.FILL, DecisionState.OPTIONAL_BLANK, DecisionState.APPROVED_NA}:
            continue

        debt_type = _debt_type_for(decision.state)
        if debt_type is None:
            continue
        recommended = _recommend_source(node, decision)
        debt.append(
            EvidenceDebtEntry(
                field_id=fid,
                debt_type=debt_type,
                blocking=node.required and decision.state in {
                    DecisionState.BLOCKED_NO_SOURCE,
                    DecisionState.REVIEW_REQUIRED,
                    DecisionState.CONFLICT,
                    DecisionState.LOW_CONFIDENCE,
                    DecisionState.BLOCKED_UNAUTHORIZED,
                },
                recommended_source=recommended,
                search_terms=list(node.expansion_search_terms),
                resolution_paths=_resolution_paths_for(decision.state),
            )
        )
    return debt


def _debt_type_for(state: DecisionState) -> str | None:
    if state in {DecisionState.BLOCKED_NO_SOURCE, DecisionState.REVIEW_REQUIRED}:
        return "missing_source"
    if state in {DecisionState.LOW_CONFIDENCE, DecisionState.CONFLICT}:
        return "weak_source"
    if state is DecisionState.BLOCKED_UNAUTHORIZED:
        return "out_of_scope_source"
    return None


def _recommend_source(node, decision) -> str:
    if "pitp" in node.field_id:
        return "PITP / inspection-test-plan procedure document"
    if "aar" in node.field_id:
        return "AAR Form 4-2 registration document"
    if "tco" in node.field_id and "instructions" in node.field_id:
        return "Tank Car Owner written instructions / permission letter"
    if "car." in node.field_id:
        return "Tank car URBC / certification document"
    if "facility" in node.field_id or "audit" in node.field_id:
        return "Audit cover sheet / station QA package"
    return f"Source document containing {node.label}"


def _resolution_paths_for(state: DecisionState) -> list[str]:
    if state is DecisionState.BLOCKED_UNAUTHORIZED:
        return ["update approval map", "remove field", "approved exception"]
    if state in {DecisionState.CONFLICT}:
        return ["disambiguate evidence", "remove conflicting source", "approved exception"]
    if state in {DecisionState.LOW_CONFIDENCE}:
        return ["provide stronger evidence", "manual confirmation"]
    return ["provide source", "approved exception"]
