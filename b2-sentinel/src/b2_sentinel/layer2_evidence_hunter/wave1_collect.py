"""Wave 1 - read all sources.

Pure plumbing: walk the inbox and produce SourceChunks via extractors.

Cognitive integration: when enabled, each chunk is passed through the LLM
Evidence Hunter for meaning extraction. The extracted CognitiveExtraction
objects are attached as metadata for downstream waves.
"""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from ..cognitive.config import get_cognitive_config
from ..cognitive.evidence_hunter import extract_meaning_batch
from ..core.models import SourceChunk
from .extractors import collect_inbox

if TYPE_CHECKING:
    from ..cognitive.models import CognitiveExtraction
    from ..core.models import ObligationGraph


def wave1_collect(
    inbox: Path,
    *,
    graph: "ObligationGraph | None" = None,
) -> tuple[list[SourceChunk], list["CognitiveExtraction"]]:
    """Collect chunks and optionally enrich with cognitive meaning extraction.

    Returns (chunks, cognitive_extractions). When cognitive is disabled,
    cognitive_extractions is an empty list.
    """
    chunks = collect_inbox(inbox)

    config = get_cognitive_config()
    if not config.is_component_enabled("evidence_hunter") or graph is None:
        return chunks, []

    batch = [
        {"text": c.text, "source_file": c.source_file, "page": c.page}
        for c in chunks
    ]
    extractions = extract_meaning_batch(
        batch,
        form_id=graph.form_id,
        graph=graph,
    )
    return chunks, extractions
