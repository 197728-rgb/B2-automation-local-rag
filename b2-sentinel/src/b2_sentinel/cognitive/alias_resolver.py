"""Cognitive Semantic Alias Resolver — 3-tier alias promotion.

Tier 1: Static approved alias (from alias_rules/*.json) — auto-usable.
Tier 2: Model-inferred with evidence + confidence + trace — auto-usable with audit.
Tier 3: Model-proposed, no confirmation — log only, never write.

The resolver is called AFTER static alias lookup fails. It asks the LLM
whether an unknown label is semantically equivalent to a known field.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

from .adapter import get_adapter
from .config import get_cognitive_config
from .models import SemanticAlias
from .prompts import ALIAS_RESOLVER_SYSTEM, ALIAS_RESOLVER_USER

if TYPE_CHECKING:
    from ..core.models import ObligationGraph


def resolve_semantic_alias(
    unknown_label: str,
    *,
    context_text: str,
    form_id: str,
    graph: "ObligationGraph",
) -> SemanticAlias | None:
    """Ask the LLM to resolve an unknown label to a known field.

    Returns None when cognitive layer is disabled.
    Returns SemanticAlias with tier, confidence, and reasoning.
    """
    config = get_cognitive_config()
    if not config.is_component_enabled("alias_resolver"):
        return None

    field_list = "\n".join(
        f"  {fid}: {node.label}"
        for fid, node in graph.fields.items()
    )

    user_prompt = ALIAS_RESOLVER_USER.format(
        unknown_label=unknown_label,
        context_text=context_text[:1000],
        form_id=form_id,
        field_list=field_list,
        schema_name=SemanticAlias.__name__,
    )

    adapter = get_adapter()
    alias = adapter.reason(ALIAS_RESOLVER_SYSTEM, user_prompt, SemanticAlias)

    if not alias.from_text:
        alias.from_text = unknown_label

    alias.auto_usable = alias.tier <= config.alias_promotion_auto_max
    return alias


def log_proposed_alias(alias: SemanticAlias, output_dir: Path) -> None:
    """Log a tier-3 proposed alias for human review."""
    proposals_path = output_dir / "proposed_aliases.json"
    existing: list[dict] = []
    if proposals_path.exists():
        try:
            existing = json.loads(proposals_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            existing = []

    existing.append(alias.model_dump())
    proposals_path.write_text(
        json.dumps(existing, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
