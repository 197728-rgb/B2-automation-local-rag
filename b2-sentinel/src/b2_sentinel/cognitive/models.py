"""Cognitive layer Pydantic schemas.

Every object the cognitive layer produces is typed, validated, and auditable.
These models flow INTO the deterministic spine as enriched input — they never
bypass the governance layer.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from ..core.status import DecisionState


class CandidateFact(BaseModel):
    """A single fact the LLM extracted from evidence text."""

    field_id: str = ""
    value: str = ""
    semantic_match: bool = False
    reasoning: str = ""
    risk: Literal["low", "medium", "high"] = "low"


class SourceFragment(BaseModel):
    """Provenance record for a piece of synthesized evidence."""

    source_file: str = ""
    page: int | None = None
    chunk_id: str | None = None
    text_excerpt: str = ""


class CognitiveExtraction(BaseModel):
    """LLM Evidence Hunter output — meaning extraction from a text chunk.

    The LLM explains what the text proves, what it does not prove, and which
    B-2 fields it may support.
    """

    source_file: str = ""
    source_text: str = ""
    meaning: str = ""
    candidate_facts: list[CandidateFact] = Field(default_factory=list)
    confidence: float = 0.0
    uncertainty: str | None = None
    form_scope_hint: str | None = None


class AmbiguityJudgment(BaseModel):
    """LLM Ambiguity Judge output — reasoning about borderline cases.

    Only produced when the deterministic decision matrix cannot safely decide
    (LOW_CONFIDENCE, CONFLICT, weak evidence, scope uncertainty).

    Defaults allow NullAdapter to return a valid (but non-promoting) judgment.
    """

    field_id: str = ""
    judgment: Literal[
        "supports_field",
        "contradicts_field",
        "ambiguous",
        "out_of_scope",
    ] = "ambiguous"
    confidence: float = 0.0
    risk: Literal["low", "medium", "high"] = "high"
    recommended_state: DecisionState = DecisionState.LOW_CONFIDENCE
    reason: str = ""
    requires_human_or_exception: bool = False


class SemanticAlias(BaseModel):
    """Semantic Alias Resolver output — 3-tier alias promotion.

    Tier 1: Static approved alias (from alias_rules/*.json) — auto-usable.
    Tier 2: Model-inferred with evidence + confidence + trace — auto-usable with audit.
    Tier 3: Model-proposed, no confirmation — log only, never write.

    Defaults allow NullAdapter to return a valid (but non-promoting) alias.
    """

    from_text: str = ""
    to_field: str = ""
    tier: Literal[1, 2, 3] = 3
    confidence: float = 0.0
    reasoning: str = ""
    auto_usable: bool = False


class SynthesizedEvidence(BaseModel):
    """Evidence Synthesizer output — multi-source fragment combination.

    Combines fragments across sources into coherent field groups while
    preserving full provenance chain.
    """

    synthesized_fact: str
    field_group: dict[str, str] = Field(default_factory=dict)
    source_fragments: list[SourceFragment] = Field(default_factory=list)
    risk: Literal["low", "medium", "high"] = "medium"
    single_source_proof: bool = False
    multi_source_synthesis: bool = True
    confidence: float = 0.0


class CritiqueFinding(BaseModel):
    """Adaptive Self-Critique output — contextual issue detection.

    The LLM re-reads the filled DOCX and asks intelligent questions about
    whether values make sense in context.
    """

    field_id: str = ""
    issue: str = ""
    severity: Literal["error", "warning", "note"] = "note"
    recommendation: str = ""
    confidence: float = 0.0
    cell_value: str | None = None
    expected_pattern: str | None = None


class CognitiveFieldObject(BaseModel):
    """The complete cognitive view of a single field decision.

    This is the enriched object that combines deterministic governance
    with cognitive reasoning — the "cognitive field object" from the spec.
    """

    field_id: str
    question_the_field_is_asking: str
    required: bool = True
    evidence_candidates: list[CandidateFact] = Field(default_factory=list)
    semantic_match: bool = False
    write_authorized_by_exact_map: bool = False
    decision: DecisionState = DecisionState.BLOCKED_NO_SOURCE
    value: str | None = None
    risk: Literal["low", "medium", "high"] = "high"
    reason: str = ""
    ambiguity_judgment: AmbiguityJudgment | None = None
    synthesis: SynthesizedEvidence | None = None
    critique_findings: list[CritiqueFinding] = Field(default_factory=list)
