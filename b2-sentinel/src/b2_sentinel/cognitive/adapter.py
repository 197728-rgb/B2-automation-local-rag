"""Pluggable LLM adapter interface.

Every cognitive component calls this adapter to reason. The adapter is the only
point where external LLM API calls happen. Providers must degrade gracefully to
empty/default structured models when packages, keys, endpoints, permissions, or
API calls are unavailable. The deterministic system must remain runnable without
paid APIs or provider SDKs installed.
"""
from __future__ import annotations

import os
import sys
from abc import ABC, abstractmethod
from typing import TypeVar

from pydantic import BaseModel

from .config import CognitiveConfig, get_cognitive_config

T = TypeVar("T", bound=BaseModel)


def _default(schema: type[T]) -> T:
    return schema.model_validate({})


def _warn(message: str) -> None:
    print(f"WARNING: {message}", file=sys.stderr)


class LLMAdapter(ABC):
    """Abstract base for all LLM providers."""

    def __init__(self, config: CognitiveConfig) -> None:
        self.config = config

    @abstractmethod
    def reason(self, system: str, user: str, schema: type[T]) -> T:
        """Send prompt, parse structured response into Pydantic model."""

    @abstractmethod
    def reason_batch(self, system: str, users: list[str], schema: type[T]) -> list[T]:
        """Batch reasoning for cost efficiency."""


class NullAdapter(LLMAdapter):
    """Returns empty/default models. Used when cognitive layer is disabled."""

    def reason(self, system: str, user: str, schema: type[T]) -> T:
        return _default(schema)

    def reason_batch(self, system: str, users: list[str], schema: type[T]) -> list[T]:
        return [_default(schema) for _ in users]


class OpenAIAdapter(LLMAdapter):
    """OpenAI API adapter using structured outputs with graceful fallback."""

    def __init__(self, config: CognitiveConfig) -> None:
        super().__init__(config)
        self._client = None
        self._unavailable = False
        self._api_failed = False

    def _get_client(self):
        if self._unavailable or self._api_failed:
            return None
        if self._client is None:
            try:
                from openai import OpenAI
            except ImportError:
                _warn("openai package not installed. OpenAI adapter degraded to deterministic mode.")
                self._unavailable = True
                return None
            api_key = os.environ.get(self.config.api_key_env, "")
            if not api_key:
                _warn(f"{self.config.api_key_env} not set. OpenAI adapter degraded to deterministic mode.")
                self._unavailable = True
                return None
            kwargs = {"api_key": api_key}
            if self.config.api_base_url:
                kwargs["base_url"] = self.config.api_base_url
            try:
                self._client = OpenAI(**kwargs)
            except Exception as exc:  # noqa: BLE001
                _warn(f"OpenAI client initialization failed ({type(exc).__name__}). Degraded to deterministic mode.")
                self._unavailable = True
                return None
        return self._client

    def reason(self, system: str, user: str, schema: type[T]) -> T:
        client = self._get_client()
        if client is None:
            return _default(schema)
        try:
            response = client.chat.completions.create(
                model=self.config.model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": schema.__name__,
                        "schema": schema.model_json_schema(),
                        "strict": True,
                    },
                },
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
            )
            raw = response.choices[0].message.content
            return schema.model_validate_json(raw)
        except Exception as exc:  # noqa: BLE001
            _warn(f"OpenAI API call failed ({type(exc).__name__}). Disabling adapter for remainder of run.")
            self._api_failed = True
            return _default(schema)

    def reason_batch(self, system: str, users: list[str], schema: type[T]) -> list[T]:
        if self._unavailable or self._api_failed:
            return [_default(schema) for _ in users]
        return [self.reason(system, user, schema) for user in users]


class AzureOpenAIAdapter(LLMAdapter):
    """Azure OpenAI adapter using endpoint + deployment + api-version.

    Config mapping:
      config.api_base_url       -> azure_endpoint
      config.model              -> deployment name
      config.azure_api_version  -> API version
    """

    def __init__(self, config: CognitiveConfig) -> None:
        super().__init__(config)
        self._client = None
        self._unavailable = False
        self._api_failed = False

    def _get_client(self):
        if self._unavailable or self._api_failed:
            return None
        if self._client is None:
            try:
                from openai import AzureOpenAI
            except ImportError:
                _warn("openai package not installed. Azure OpenAI adapter degraded to deterministic mode.")
                self._unavailable = True
                return None
            api_key = os.environ.get(self.config.api_key_env, "")
            if not api_key:
                _warn(f"{self.config.api_key_env} not set. Azure OpenAI adapter degraded to deterministic mode.")
                self._unavailable = True
                return None
            if not self.config.api_base_url:
                _warn("Azure OpenAI api_base_url not set. Azure adapter degraded to deterministic mode.")
                self._unavailable = True
                return None
            try:
                self._client = AzureOpenAI(
                    api_key=api_key,
                    azure_endpoint=self.config.api_base_url,
                    api_version=self.config.azure_api_version or "2024-08-01-preview",
                )
            except Exception as exc:  # noqa: BLE001
                _warn(f"Azure OpenAI client initialization failed ({type(exc).__name__}). Degraded to deterministic mode.")
                self._unavailable = True
                return None
        return self._client

    def reason(self, system: str, user: str, schema: type[T]) -> T:
        client = self._get_client()
        if client is None:
            return _default(schema)
        try:
            response = client.chat.completions.create(
                model=self.config.model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": schema.__name__,
                        "schema": schema.model_json_schema(),
                        "strict": True,
                    },
                },
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
            )
            raw = response.choices[0].message.content
            return schema.model_validate_json(raw)
        except Exception as exc:  # noqa: BLE001
            _warn(f"Azure OpenAI API call failed ({type(exc).__name__}). Disabling adapter for remainder of run.")
            self._api_failed = True
            return _default(schema)

    def reason_batch(self, system: str, users: list[str], schema: type[T]) -> list[T]:
        if self._unavailable or self._api_failed:
            return [_default(schema) for _ in users]
        return [self.reason(system, user, schema) for user in users]


class AnthropicAdapter(LLMAdapter):
    """Anthropic Claude adapter using tool_use for structured output."""

    def __init__(self, config: CognitiveConfig) -> None:
        super().__init__(config)
        self._client = None
        self._unavailable = False
        self._api_failed = False

    def _get_client(self):
        if self._unavailable or self._api_failed:
            return None
        if self._client is None:
            try:
                from anthropic import Anthropic
            except ImportError:
                _warn("anthropic package not installed. Anthropic adapter degraded to deterministic mode.")
                self._unavailable = True
                return None
            api_key = os.environ.get(self.config.api_key_env, "")
            if not api_key:
                _warn(f"{self.config.api_key_env} not set. Anthropic adapter degraded to deterministic mode.")
                self._unavailable = True
                return None
            try:
                self._client = Anthropic(api_key=api_key)
            except Exception as exc:  # noqa: BLE001
                _warn(f"Anthropic client initialization failed ({type(exc).__name__}). Degraded to deterministic mode.")
                self._unavailable = True
                return None
        return self._client

    def reason(self, system: str, user: str, schema: type[T]) -> T:
        client = self._get_client()
        if client is None:
            return _default(schema)
        try:
            response = client.messages.create(
                model=self.config.model,
                system=system,
                messages=[{"role": "user", "content": user}],
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
                tools=[{
                    "name": "structured_output",
                    "description": "Return structured JSON matching the schema",
                    "input_schema": schema.model_json_schema(),
                }],
                tool_choice={"type": "tool", "name": "structured_output"},
            )
            for block in response.content:
                if getattr(block, "type", None) == "tool_use":
                    return schema.model_validate(block.input)
        except Exception as exc:  # noqa: BLE001
            _warn(f"Anthropic API call failed ({type(exc).__name__}). Disabling adapter for remainder of run.")
            self._api_failed = True
        return _default(schema)

    def reason_batch(self, system: str, users: list[str], schema: type[T]) -> list[T]:
        if self._unavailable or self._api_failed:
            return [_default(schema) for _ in users]
        return [self.reason(system, user, schema) for user in users]


_ADAPTER_REGISTRY: dict[str, type[LLMAdapter]] = {
    "null": NullAdapter,
    "openai": OpenAIAdapter,
    "azure": AzureOpenAIAdapter,
    "anthropic": AnthropicAdapter,
}


def create_adapter(config: CognitiveConfig | None = None) -> LLMAdapter:
    config = config or get_cognitive_config()
    if not config.enabled:
        return NullAdapter(config)
    adapter_cls = _ADAPTER_REGISTRY.get(config.adapter, NullAdapter)
    try:
        return adapter_cls(config)
    except Exception as exc:  # noqa: BLE001
        _warn(f"{config.adapter} adapter failed to initialize ({type(exc).__name__}). Using NullAdapter.")
        return NullAdapter(config)


_GLOBAL_ADAPTER: LLMAdapter | None = None


def get_adapter() -> LLMAdapter:
    global _GLOBAL_ADAPTER
    if _GLOBAL_ADAPTER is None:
        _GLOBAL_ADAPTER = create_adapter()
    return _GLOBAL_ADAPTER


def set_adapter(adapter: LLMAdapter) -> None:
    global _GLOBAL_ADAPTER
    _GLOBAL_ADAPTER = adapter
