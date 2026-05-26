"""Provider-neutral JSON generation for autonomous agents."""

from __future__ import annotations

import json
import os
from typing import Any


class LlmError(RuntimeError):
    pass


def _provider() -> str:
    return (os.getenv("LLM_PROVIDER") or "google").strip().lower()


def generate_json(
    prompt: str,
    *,
    model: str | None = None,
    response_schema: dict[str, Any] | None = None,
) -> dict[str, Any] | list[Any]:
    provider = _provider()
    if provider == "google":
        return _generate_google(prompt, model=model, response_schema=response_schema)
    if provider == "anthropic":
        return _generate_anthropic(prompt, model=model)
    raise LlmError(f"Unsupported LLM_PROVIDER: {provider}")


def _generate_google(
    prompt: str,
    *,
    model: str | None = None,
    response_schema: dict[str, Any] | None = None,
) -> dict[str, Any] | list[Any]:
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise LlmError("GEMINI_API_KEY is not set")
    try:
        from google import genai
    except ImportError as exc:
        raise LlmError("google-genai is required: pip install -e '.[autonomous]'") from exc

    client = genai.Client(api_key=api_key)
    model_name = model or os.getenv("GEMINI_MODEL", "gemini-2.5-pro")
    config: dict[str, Any] = {"response_mime_type": "application/json"}
    if response_schema:
        config["response_json_schema"] = response_schema
    response = client.models.generate_content(
        model=model_name,
        contents=prompt,
        config=config,
    )
    text = getattr(response, "text", None) or ""
    if not text.strip():
        raise LlmError("Empty response from Gemini")
    return json.loads(text)


def _generate_anthropic(prompt: str, *, model: str | None = None) -> dict[str, Any] | list[Any]:
    api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        raise LlmError("ANTHROPIC_API_KEY is not set")
    try:
        import anthropic
    except ImportError as exc:
        raise LlmError("anthropic SDK required for LLM_PROVIDER=anthropic") from exc

    client = anthropic.Anthropic(api_key=api_key)
    model_name = model or os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")
    msg = client.messages.create(
        model=model_name,
        max_tokens=8192,
        messages=[{"role": "user", "content": prompt + "\n\nRespond with JSON only."}],
    )
    text = ""
    for block in msg.content:
        if hasattr(block, "text"):
            text += block.text
    return json.loads(text)
