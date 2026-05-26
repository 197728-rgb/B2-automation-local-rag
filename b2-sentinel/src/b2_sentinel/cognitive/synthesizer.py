"""Cognitive Evidence Synthesizer — multi-source fragment combination.

Many fields are not proven by one sentence. They require combining fragments
from multiple sources while preserving full provenance chain.

The synthesizer is called when individual chunks are insufficient but related
fragments exist across sources.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

from .adapter import get_adapter
from .config import get_cognitive_config
from .models import SourceFragment, SynthesizedEvidence
from .prompts import SYNTHESIZER_SYSTEM, SYNTHESIZER_USER

if TYPE_CHECKING:
    from ..core.models import CognitiveExtraction


class _SynthesisResponse(BaseModel):
    """Schema the LLM returns for synthesis."""

    synthesized_fact: str = ""
    field_group: dict[str, str] = Field(default_factory=dict)
    risk: str = "medium"
    single_source_proof: bool = False
    multi_source_synthesis: bool = True
    confidence: float = 0.0


def synthesize_evidence(
    fragments: list[dict],
    *,
    target_fields: list[str],
    form_id: str,
) -> SynthesizedEvidence | None:
    """Combine multiple evidence fragments into a coherent field group.

    Each fragment dict should have: source_file, page, chunk_id, text.
    Returns None when cognitive layer is disabled or insufficient fragments.
    """
    config = get_cognitive_config()
    if not config.is_component_enabled("synthesizer"):
        return None

    if len(fragments) < config.synthesis_min_fragments:
        return None

    fragments_text = "\n\n".join(
        f"Fragment {i+1} (from {f.get('source_file', '?')}, page {f.get('page', '?')}):\n"
        f"{f.get('text', '')[:800]}"
        for i, f in enumerate(fragments)
    )

    field_group_str = ", ".join(target_fields)

    user_prompt = SYNTHESIZER_USER.format(
        field_group=field_group_str,
        form_id=form_id,
        fragments_text=fragments_text,
        schema_name=_SynthesisResponse.__name__,
    )

    adapter = get_adapter()
    response = adapter.reason(SYNTHESIZER_SYSTEM, user_prompt, _SynthesisResponse)

    source_frags = [
        SourceFragment(
            source_file=f.get("source_file", ""),
            page=f.get("page"),
            chunk_id=f.get("chunk_id"),
            text_excerpt=f.get("text", "")[:200],
        )
        for f in fragments
    ]

    risk = response.risk if response.risk in ("low", "medium", "high") else "medium"

    return SynthesizedEvidence(
        synthesized_fact=response.synthesized_fact,
        field_group=response.field_group,
        source_fragments=source_frags,
        risk=risk,
        single_source_proof=response.single_source_proof,
        multi_source_synthesis=response.multi_source_synthesis,
        confidence=response.confidence,
    )
