"""Cognitive layer configuration.

Loaded from b2-sentinel.yaml, environment variables, or defaults.
When cognitive.enabled is False, the entire layer is a no-op and the system
runs in pure deterministic mode.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class CognitiveConfig:
    enabled: bool = False
    adapter: str = "null"
    model: str = "gpt-4o"
    api_key_env: str = "B2_SENTINEL_LLM_API_KEY"
    api_base_url: str | None = None
    azure_api_version: str = "2024-08-01-preview"
    max_tokens: int = 4096
    temperature: float = 0.1

    evidence_hunter_enabled: bool = True
    ambiguity_judge_enabled: bool = True
    alias_resolver_enabled: bool = True
    synthesizer_enabled: bool = True
    self_critique_enabled: bool = True

    ambiguity_threshold: float = 0.75
    alias_promotion_auto_max: int = 2
    synthesis_min_fragments: int = 2
    critique_severity_fail_threshold: str = "error"

    @classmethod
    def from_yaml(cls, path: Path) -> "CognitiveConfig":
        if not path.exists():
            return cls()
        with path.open(encoding="utf-8") as fh:
            raw = yaml.safe_load(fh) or {}
        cognitive_section = raw.get("cognitive", {})
        return cls(**{k: v for k, v in cognitive_section.items() if k in cls.__dataclass_fields__})

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CognitiveConfig":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    def is_component_enabled(self, component: str) -> bool:
        if not self.enabled:
            return False
        return getattr(self, f"{component}_enabled", False)


_GLOBAL_CONFIG: CognitiveConfig | None = None


def get_cognitive_config() -> CognitiveConfig:
    global _GLOBAL_CONFIG
    if _GLOBAL_CONFIG is None:
        _GLOBAL_CONFIG = CognitiveConfig()
    return _GLOBAL_CONFIG


def set_cognitive_config(config: CognitiveConfig) -> None:
    global _GLOBAL_CONFIG
    _GLOBAL_CONFIG = config


def load_cognitive_config(yaml_path: Path) -> CognitiveConfig:
    config = CognitiveConfig.from_yaml(yaml_path)
    set_cognitive_config(config)
    return config
