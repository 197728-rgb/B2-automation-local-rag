"""Wave 4 - cross-form contamination defense.

Per the spec:
    Did this value come from the correct form scope?
    Is this B89 evidence being used in B81?
    Is this C6r evidence being used in B89?
    Is this a global facility value or form-specific value?

If a chunk's scope_hint disagrees with the current form, AND the field is
form-specific (not a global facility field like Cover_Page station code),
mark the entry as 'out_of_scope' and clear the candidate value.

Additionally, "multi-scope files" (files that produce chunks with 2+ different
non-None scope hints) get their None-scoped entries demoted to weak confidence
since those chunks likely contain data from other cars/forms.
"""
from __future__ import annotations

from collections import defaultdict

from ..core.models import (
    EvidenceLedgerEntry,
    ObligationGraph,
    SourceChunk,
)


GLOBAL_FACILITY_FIELDS: frozenset[str] = frozenset({
    "station_stencil_code",
    "facility_workforce_size",
    "audit_type",
    "open_meeting_date",
    "closing_meeting_date",
    "lead_auditor",
})


def _identify_multi_scope_files(chunks: list[SourceChunk]) -> set[str]:
    """Find files that produced chunks with 2+ different non-None scope hints."""
    scopes_by_file: dict[str, set[str]] = defaultdict(set)
    for chunk in chunks:
        if chunk.scope_hint is not None:
            scopes_by_file[chunk.source_file].add(chunk.scope_hint)
    return {f for f, scopes in scopes_by_file.items() if len(scopes) >= 2}


def wave4_contamination(
    graph: ObligationGraph,
    ledger: dict[str, EvidenceLedgerEntry],
    chunks: list[SourceChunk] | None = None,
) -> dict[str, EvidenceLedgerEntry]:
    form_id = graph.form_id
    multi_scope_files = _identify_multi_scope_files(chunks) if chunks else set()

    for fid, entry in ledger.items():
        if entry.candidate_value is None:
            continue
        if fid in GLOBAL_FACILITY_FIELDS:
            continue
        scope = entry.scope
        if scope is None:
            if entry.source_type == "json":
                continue
            if entry.source_file in multi_scope_files:
                entry.confidence = min(entry.confidence, 0.5)
                if entry.decision == "usable":
                    entry.decision = "weak"
            else:
                entry.confidence = min(entry.confidence, 0.85)
            continue
        if scope == form_id:
            continue
        entry.alternates.insert(
            0,
            {
                "value": entry.candidate_value,
                "source_file": entry.source_file,
                "scope_seen": scope,
                "rejected_reason": "cross_form_contamination",
            },
        )
        entry.candidate_value = None
        entry.confidence = 0.0
        entry.decision = "out_of_scope"
        entry.wave_found_in = 4
    return ledger
