"""Discrete decision states for local review packets (Stage 5).

Maps retrieved suggestions to FieldDecision rows using strict DecisionState values.
"""

from __future__ import annotations

from collections import Counter
from typing import Any

from b2_automation.cell_evidence import DecisionState, FieldDecision

# Local lexical suggestions only emit discrete decisions for these retrieval keys (not CSV canonical paths).
_LOCAL_DECISION_ALLOWLIST = frozenset({"facility_name", "date", "auditor", "car_number"})


def summarize_decisions(decisions: list[FieldDecision]) -> dict[str, Any]:
    counts = Counter(d.state.value for d in decisions)
    fill_eligible = [d.field_id for d in decisions if d.state == DecisionState.FILL]
    return {
        "counts_by_state": dict(sorted(counts.items())),
        "fill_eligible_field_ids": sorted(fill_eligible),
    }


def decide_fields_for_local_packet(
    *,
    retrieved: list[dict[str, Any]],
    suggestions: list[dict[str, Any]],
    required_field_ids: tuple[str, ...],
    low_confidence_threshold: float,
) -> list[FieldDecision]:
    """Assign DecisionState per field for one form's local RAG packet."""
    by_field: dict[str, list[dict[str, Any]]] = {}
    for item in suggestions:
        by_field.setdefault(str(item["field_id"]), []).append(item)

    required_set = set(required_field_ids)
    suggestion_keys = set(by_field.keys()) & _LOCAL_DECISION_ALLOWLIST
    field_ids = sorted(required_set | suggestion_keys)
    decisions: list[FieldDecision] = []

    for field_id in field_ids:
        items = by_field.get(field_id, [])
        if not retrieved or not items:
            state = DecisionState.MISSING if field_id in required_set else DecisionState.BLANK
            decisions.append(
                FieldDecision(field_id=field_id, state=state, reason="no retrieved evidence candidate", candidates=tuple())
            )
            continue

        values = sorted({str(item.get("candidate_value") or "").strip() for item in items if str(item.get("candidate_value") or "").strip()})
        high_confidence_values = sorted(
            {
                str(item.get("candidate_value") or "").strip()
                for item in items
                if str(item.get("candidate_value") or "").strip()
                and float(item.get("confidence") or 0.0) >= low_confidence_threshold
            }
        )
        best = max(items, key=lambda item: float(item.get("confidence") or 0.0))
        best_confidence = float(best.get("confidence") or 0.0)

        if len(high_confidence_values) > 1:
            decisions.append(
                FieldDecision(
                    field_id=field_id,
                    state=DecisionState.CONFLICT,
                    selected_value=None,
                    confidence=best_confidence,
                    reason="multiple high-confidence disagreeing candidates",
                    candidates=tuple(items),
                )
            )
        elif len(values) > 1 and len(high_confidence_values) <= 1:
            decisions.append(
                FieldDecision(
                    field_id=field_id,
                    state=DecisionState.REVIEW_REQUIRED,
                    selected_value=str(best.get("candidate_value") or "").strip() or None,
                    confidence=best_confidence,
                    reason="conflicting candidate values without multiple high-confidence winners",
                    candidates=tuple(items),
                )
            )
        elif best_confidence < low_confidence_threshold:
            decisions.append(
                FieldDecision(
                    field_id=field_id,
                    state=DecisionState.LOW_CONFIDENCE,
                    selected_value=str(best.get("candidate_value") or ""),
                    confidence=best_confidence,
                    reason=f"below threshold {low_confidence_threshold:.2f}",
                    candidates=tuple(items),
                )
            )
        elif values:
            decisions.append(
                FieldDecision(
                    field_id=field_id,
                    state=DecisionState.FILL,
                    selected_value=str(best.get("candidate_value") or ""),
                    confidence=best_confidence,
                    reason="selected highest-confidence local evidence",
                    candidates=tuple(items),
                )
            )
        else:
            state = DecisionState.MISSING if field_id in required_set else DecisionState.BLANK
            decisions.append(
                FieldDecision(field_id=field_id, state=state, reason="candidate had no extracted value", candidates=tuple(items))
            )

    return decisions
