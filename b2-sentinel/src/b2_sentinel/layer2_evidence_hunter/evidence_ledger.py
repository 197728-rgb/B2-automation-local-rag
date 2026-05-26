"""Evidence Ledger writer - assembles the per-form ledger artifact."""
from __future__ import annotations

from ..core.models import EvidenceLedger, EvidenceLedgerEntry, SourceChunk


def build_ledger(
    form_id: str,
    entries: dict[str, EvidenceLedgerEntry],
    chunks: list[SourceChunk],
) -> EvidenceLedger:
    sources = sorted({c.source_file for c in chunks})
    return EvidenceLedger(form_id=form_id, entries=entries, source_index=sources)
