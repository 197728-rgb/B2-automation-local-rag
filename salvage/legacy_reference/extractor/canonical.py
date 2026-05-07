from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

META_KEYS = frozenset(
    {
        "source_file",
        "target_form",
        "pages_processed",
        "ocr_confidence",
    }
)


@dataclass
class CanonicalRecord:
    """Bible: one extracted fact with provenance (extend source_page/snippet as ingest improves)."""

    canonical_key: str
    display_value: str
    normalized_value: str
    source_file: str
    source_page: str
    source_snippet: str
    confidence: str
    ambiguity_reason: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


def flat_to_records(flat: dict[str, Any], *, source_file: str) -> list[CanonicalRecord]:
    out: list[CanonicalRecord] = []
    for k, v in flat.items():
        if k in META_KEYS or v is None:
            continue
        s = str(v).strip()
        if not s:
            continue
        snippet = s[:240] + ("..." if len(s) > 240 else "")
        out.append(
            CanonicalRecord(
                canonical_key=k,
                display_value=s,
                normalized_value=s,
                source_file=source_file,
                source_page=flat.get("pages_processed", "") or "",
                source_snippet=snippet,
                confidence=str(flat.get("ocr_confidence", "") or ""),
                ambiguity_reason="",
            )
        )
    return out


def records_to_flat(records: list[CanonicalRecord], *, meta: dict[str, Any]) -> dict[str, Any]:
    d: dict[str, Any] = {r.canonical_key: r.display_value for r in records}
    d.update(meta)
    return d
