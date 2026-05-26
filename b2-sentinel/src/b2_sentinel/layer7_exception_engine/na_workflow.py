"""Approved N/A workflow.

For each required field with no usable evidence, check whether the
form's N/A policy approves an exception. If yes, produce an
NAExceptionEntry with status='approved_na'; if no, the field stays
blocked.

The closed-loop spec is explicit: 'No silent N/A. No lazy N/A. Only
approved exception logic.'
"""
from __future__ import annotations

from ..core.models import (
    EvidenceLedgerEntry,
    NAExceptionEntry,
    ObligationGraph,
)
from .policy_loader import load_policy


def evaluate_na(
    graph: ObligationGraph,
    ledger: dict[str, EvidenceLedgerEntry],
) -> tuple[dict[str, bool], list[NAExceptionEntry]]:
    """Returns (n_a_approvals, na_log).

    n_a_approvals: {field_id: True} for every approved N/A
    na_log: full ledger entries to dump in na_exception_log.json
    """
    policy = load_policy(graph.form_id)
    approvals: dict[str, bool] = {}
    log: list[NAExceptionEntry] = []

    for fid, node in graph.fields.items():
        if not node.required:
            continue
        if not node.n_a_allowed:
            continue
        entry = ledger.get(fid)
        has_value = bool(entry and entry.candidate_value)
        if has_value:
            continue  # No need for N/A
        if fid not in policy:
            continue  # n_a_allowed by graph but no concrete approval entry yet
        pol = policy[fid]
        log.append(
            NAExceptionEntry(
                field_id=fid,
                status="approved_na",
                reason=str(pol.get("reason", "approved exception")),
                authority="approved_exception_policy",
                approved_by=str(pol.get("approved_by", "policy_reference")),
                completion_effect="not_blocking",
                policy_id=pol.get("policy_id"),
            )
        )
        approvals[fid] = True
    return approvals, log
