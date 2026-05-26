"""Five-axis confidence: retrieval, extraction, authorization, write, completion.

This is the spec's Innovation #4: 'Confidence Is Not Completion'. A field
can be highly confident on retrieval and zero-authorized for write.
"""
from __future__ import annotations

from ..core.models import (
    ConfidenceBundle,
    EvidenceLedgerEntry,
    FieldNode,
)
from ..core.status import WriteAuthority


_CONFLICT_LOW_CONFIDENCE_THRESHOLD = 0.6


def compute_confidence(
    node: FieldNode,
    entry: EvidenceLedgerEntry | None,
    *,
    write_authority: WriteAuthority,
    n_a_approved: bool,
) -> ConfidenceBundle:
    retrieval = entry.confidence if entry else 0.0
    extraction = retrieval * 0.95 if entry and entry.candidate_value else 0.0
    authorization = 1.0 if write_authority is WriteAuthority.EXACT_APPROVAL_MAP else 0.0
    write = (
        min(extraction, authorization)
        if entry and entry.candidate_value and authorization > 0
        else 0.0
    )
    if n_a_approved and write == 0.0:
        write = 0.99  # NA insertion is itself a valid write
    completion = 0.0
    if entry and entry.candidate_value and write > 0.0:
        completion = min(write, 0.95)
    elif n_a_approved:
        completion = 0.99
    return ConfidenceBundle(
        retrieval=round(retrieval, 4),
        extraction=round(extraction, 4),
        authorization=round(authorization, 4),
        write=round(write, 4),
        completion=round(completion, 4),
    )


def is_low_confidence(c: ConfidenceBundle) -> bool:
    return 0 < c.write < _CONFLICT_LOW_CONFIDENCE_THRESHOLD
