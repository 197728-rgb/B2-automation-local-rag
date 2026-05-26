"""Cognitive Evidence Hunter — meaning extraction from text.

The LLM reads raw text and explains what it proves, what it does not prove,
and which B-2 fields it may support. The deterministic layer then consumes
these structured extractions as enriched input.

When disabled, returns empty extractions and the system falls back to
keyword/TF-IDF matching.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

from .adapter import get_adapter
from .config import get_cognitive_config
from .models import CandidateFact, CognitiveExtraction
from .prompts import EVIDENCE_HUNTER_SYSTEM, EVIDENCE_HUNTER_USER

if TYPE_CHECKING:
    from ..core.models import FieldNode, ObligationGraph


class _ExtractionResponse(BaseModel):
    """Schema the LLM returns — parsed into CognitiveExtraction."""

    meaning: str = ""
    candidate_facts: list[CandidateFact] = Field(default_factory=list)
    confidence: float = 0.0
    uncertainty: str | None = None
    form_scope_hint: str | None = None


def extract_meaning(
    chunk_text: str,
    *,
    source_file: str,
    page: int | None = None,
    form_id: str,
    graph: "ObligationGraph",
) -> CognitiveExtraction:
    """Run cognitive meaning extraction on a single text chunk.

    Returns CognitiveExtraction with candidate facts mapped to field IDs.
    When cognitive layer is disabled, returns an empty extraction.
    """
    config = get_cognitive_config()
    if not config.is_component_enabled("evidence_hunter"):
        return CognitiveExtraction(
            source_file=source_file,
            source_text=chunk_text[:500],
            meaning="",
            confidence=0.0,
        )

    field_list = "\n".join(
        f"  {fid}: {node.label}"
        for fid, node in graph.fields.items()
    )

    user_prompt = EVIDENCE_HUNTER_USER.format(
        form_id=form_id,
        field_list=field_list,
        source_file=source_file,
        page=page or "unknown",
        chunk_text=chunk_text[:3000],
        schema_name=_ExtractionResponse.__name__,
    )

    adapter = get_adapter()
    response = adapter.reason(EVIDENCE_HUNTER_SYSTEM, user_prompt, _ExtractionResponse)

    return CognitiveExtraction(
        source_file=source_file,
        source_text=chunk_text[:500],
        meaning=response.meaning,
        candidate_facts=response.candidate_facts,
        confidence=response.confidence,
        uncertainty=response.uncertainty,
        form_scope_hint=response.form_scope_hint,
    )


def extract_meaning_batch(
    chunks: list[dict],
    *,
    form_id: str,
    graph: "ObligationGraph",
) -> list[CognitiveExtraction]:
    """Batch extraction for multiple chunks.

    Each dict in chunks should have: text, source_file, page (optional).
    """
    config = get_cognitive_config()
    if not config.is_component_enabled("evidence_hunter"):
        return [
            CognitiveExtraction(
                source_file=c.get("source_file", ""),
                source_text=c.get("text", "")[:500],
                meaning="",
                confidence=0.0,
            )
            for c in chunks
        ]

    field_list = "\n".join(
        f"  {fid}: {node.label}"
        for fid, node in graph.fields.items()
    )

    prompts = []
    for c in chunks:
        prompts.append(EVIDENCE_HUNTER_USER.format(
            form_id=form_id,
            field_list=field_list,
            source_file=c.get("source_file", ""),
            page=c.get("page", "unknown"),
            chunk_text=c.get("text", "")[:3000],
            schema_name=_ExtractionResponse.__name__,
        ))

    adapter = get_adapter()
    responses = adapter.reason_batch(EVIDENCE_HUNTER_SYSTEM, prompts, _ExtractionResponse)

    results = []
    for c, resp in zip(chunks, responses):
        results.append(CognitiveExtraction(
            source_file=c.get("source_file", ""),
            source_text=c.get("text", "")[:500],
            meaning=resp.meaning,
            candidate_facts=resp.candidate_facts,
            confidence=resp.confidence,
            uncertainty=resp.uncertainty,
            form_scope_hint=resp.form_scope_hint,
        ))
    return results
