"""Cognitive Ambiguity Judge — borderline case reasoning.

Only activates when the deterministic decision matrix cannot safely decide:
- Evidence confidence below threshold
- Partial match but unclear meaning
- Conflicting sources
- Field intent mismatch
- Source-scope uncertainty

The judgment feeds BACK into the deterministic matrix — it does not override it.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from .adapter import get_adapter
from .config import get_cognitive_config
from .models import AmbiguityJudgment
from .prompts import AMBIGUITY_JUDGE_SYSTEM, AMBIGUITY_JUDGE_USER

if TYPE_CHECKING:
    from ..core.models import EvidenceLedgerEntry, FieldNode

from ..core.status import DecisionState


def judge_ambiguity(
    node: "FieldNode",
    entry: "EvidenceLedgerEntry | None",
    *,
    problem: str,
) -> AmbiguityJudgment | None:
    """Ask the LLM to reason about a borderline field decision.

    Returns None when cognitive layer is disabled (deterministic fallback).
    Returns AmbiguityJudgment when the LLM provides reasoning.
    """
    config = get_cognitive_config()
    if not config.is_component_enabled("ambiguity_judge"):
        return None

    if entry is None:
        return None

    field_intent = (
        f"This field ({node.label}) captures: "
        + ", ".join(node.expansion_search_terms[:5])
        if node.expansion_search_terms
        else f"This field captures: {node.label}"
    )

    user_prompt = AMBIGUITY_JUDGE_USER.format(
        field_id=node.field_id,
        field_label=node.label,
        field_intent=field_intent,
        required="yes" if node.required else "no",
        candidate_value=entry.candidate_value or "<none>",
        source_file=entry.source_file or "<unknown>",
        source_text=entry.source_text or entry.candidate_value or "",
        current_confidence=entry.confidence,
        problem_description=problem,
        schema_name=AmbiguityJudgment.__name__,
    )

    adapter = get_adapter()
    judgment = adapter.reason(AMBIGUITY_JUDGE_SYSTEM, user_prompt, AmbiguityJudgment)

    if not judgment.field_id:
        judgment.field_id = node.field_id

    return judgment


def should_escalate(confidence: float) -> bool:
    """Determine if a field's confidence warrants LLM judgment.

    With the expanded trigger policy, any confidence below the threshold
    triggers escalation. The threshold defaults to 0.75 (raised from 0.6)
    to catch borderline cases that need semantic reasoning.
    """
    config = get_cognitive_config()
    if not config.enabled:
        return False
    return confidence < config.ambiguity_threshold


def should_escalate_conflict(entry: "EvidenceLedgerEntry | None") -> bool:
    """Always escalate conflicts to the judge when cognitive is enabled.

    Conflicts are the primary use case for the ambiguity judge — the LLM
    can determine which candidate is semantically correct regardless of
    the confidence score.
    """
    config = get_cognitive_config()
    if not config.enabled:
        return False
    if not config.is_component_enabled("ambiguity_judge"):
        return False
    return entry is not None and entry.decision == "conflict"


def should_escalate_multi_candidate(entry: "EvidenceLedgerEntry | None") -> bool:
    """Escalate when alternates exist, even if no hard conflict was declared.

    Multi-candidate fields that weren't marked as conflict (e.g., demoted
    to weak by scope filtering) still benefit from LLM ranking.
    """
    config = get_cognitive_config()
    if not config.enabled:
        return False
    if not config.is_component_enabled("ambiguity_judge"):
        return False
    return entry is not None and len(entry.alternates) > 0
