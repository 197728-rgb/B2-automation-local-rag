"""Map DocuPipe-style extraction JSON into a flat B2 draft record."""

from __future__ import annotations

from typing import Any


def normalize_docupipe_payload(raw: dict[str, Any]) -> dict[str, Any]:
    """
    Accept a minimal DocuPipe-like payload and return a flat dict suitable
    for report assembly (values + optional confidence per field).
    """
    out: dict[str, Any] = {
        "schema_id": raw.get("schema_id", ""),
        "status": raw.get("status", ""),
        "document_id": raw.get("document_id", ""),
    }
    fields = raw.get("fields") or {}
    if not isinstance(fields, dict):
        return out

    for key, meta in fields.items():
        if isinstance(meta, dict):
            out[key] = meta.get("value", "")
            if "confidence" in meta and meta["confidence"] is not None:
                out[f"{key}_confidence"] = meta["confidence"]
            if meta.get("sources"):
                out[f"{key}_sources"] = meta["sources"]
        else:
            out[key] = meta
    return out
