"""Discrete decision states for local review packets (Stage 5).

Maps retrieved suggestions to FieldDecision rows using strict DecisionState values.
"""

from __future__ import annotations

from collections import Counter
from typing import Any

from b2_automation.cell_evidence import DecisionState, FieldDecision

REVIEW_REQUIRED_TEXT = "REVIEW_REQUIRED"


def summarize_decisions(decisions: list[FieldDecision]) -> dict[str, Any]:
    counts = Counter(d.state.value for d in decisions)
    fill_eligible = [d.field_id for d in decisions if d.state == DecisionState.FILL]
    human_review = [
        d.field_id
        for d in decisions
        if str(d.selected_value or "").startswith(REVIEW_REQUIRED_TEXT)
        or "review" in str(d.reason or "").lower()
        or "conflict" in str(d.reason or "").lower()
        or "missing" in str(d.reason or "").lower()
    ]
    return {
        "counts_by_state": dict(sorted(counts.items())),
        "fill_eligible_field_ids": sorted(fill_eligible),
        "human_review_field_ids": sorted(set(human_review)),
    }


def _best_candidate(items: list[dict[str, Any]]) -> dict[str, Any]:
    return max(
        items,
        key=lambda item: (
            float(item.get("confidence") or 0.0),
            float(item.get("retrieval_score") or item.get("score") or 0.0),
            len(str(item.get("candidate_value") or "").strip()),
        ),
    )


def _review_marker(field_id: str, reason: str) -> str:
    return f"{REVIEW_REQUIRED_TEXT}: {field_id} {reason}".strip()


def decide_fields_for_local_packet(
    *,
    retrieved: list[dict[str, Any]],
    suggestions: list[dict[str, Any]],
    required_field_ids: tuple[str, ...],
    low_confidence_threshold: float,
) -> list[FieldDecision]:
    """Assign DecisionState per field for one form's local RAG packet.

    Operational policy: do not block an entire DOCX because a few fields need
    human review. When evidence exists, select the best extracted value and mark
    the reason for reviewer attention. When a required value is missing, emit a
    visible REVIEW_REQUIRED marker so the output DOCX is still produced and the
    remaining manual work is obvious.
    """
    by_field: dict[str, list[dict[str, Any]]] = {}
    for item in suggestions:
        by_field.setdefault(str(item["field_id"]), []).append(item)

    required_set = set(required_field_ids)
    suggestion_keys = set(by_field.keys())
    field_ids = sorted(required_set | suggestion_keys)
    decisions: list[FieldDecision] = []

    for field_id in field_ids:
        items = by_field.get(field_id, [])
        if not retrieved or not items:
            if field_id in required_set:
                decisions.append(
                    FieldDecision(
                        field_id=field_id,
                        state=DecisionState.FILL,
                        selected_value=_review_marker(field_id, "missing retrieved evidence candidate"),
                        confidence=1.0,
                        reason="missing required evidence; visible marker inserted for human completion",
                        candidates=tuple(),
                    )
                )
            else:
                decisions.append(
                    FieldDecision(field_id=field_id, state=DecisionState.BLANK, reason="no retrieved evidence candidate", candidates=tuple())
                )
            continue

        values = sorted({str(item.get("candidate_value") or "").strip() for item in items if str(item.get("candidate_value") or "").strip()})
        best = _best_candidate(items)
        best_value = str(best.get("candidate_value") or "").strip()
        best_confidence = float(best.get("confidence") or 0.0)

        if not values or not best_value:
            if field_id in required_set:
                decisions.append(
                    FieldDecision(
                        field_id=field_id,
                        state=DecisionState.FILL,
                        selected_value=_review_marker(field_id, "candidate had no extracted value"),
                        confidence=1.0,
                        reason="missing required extracted value; visible marker inserted for human completion",
                        candidates=tuple(items),
                    )
                )
            else:
                decisions.append(
                    FieldDecision(field_id=field_id, state=DecisionState.BLANK, reason="candidate had no extracted value", candidates=tuple(items))
                )
            continue

        reason = "selected highest-confidence local evidence"
        effective_confidence = best_confidence
        if len(values) > 1:
            reason = "auto-filled best candidate; conflicting extracted values require reviewer verification"
            effective_confidence = max(best_confidence, low_confidence_threshold)
        elif best_confidence < low_confidence_threshold:
            reason = f"auto-filled low-confidence candidate below threshold {low_confidence_threshold:.2f}; reviewer verification required"
            effective_confidence = low_confidence_threshold

        decisions.append(
            FieldDecision(
                field_id=field_id,
                state=DecisionState.FILL,
                selected_value=best_value,
                confidence=effective_confidence,
                reason=reason,
                candidates=tuple(items),
            )
        )

    return decisions
