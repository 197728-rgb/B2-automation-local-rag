"""The Decision Matrix - the core SENTINEL rule engine.

For every field in the obligation graph, given the evidence ledger entry
and the N/A policy, return a FieldDecision in exactly one of eight states.

Spec table:

| Evidence | Map authorizes | Required | N-A approved | State |
|---|---|---|---|---|
| yes      | yes            | any      | n/a          | FILL |
| yes      | no             | any      | n/a          | BLOCKED_UNAUTHORIZED |
| no       | yes            | yes      | yes          | APPROVED_NA |
| no       | yes            | yes      | no           | BLOCKED_NO_SOURCE |
| no       | yes            | no       | n/a          | OPTIONAL_BLANK |
| weak     | yes            | yes      | n/a          | LOW_CONFIDENCE |
| multiple | yes            | any      | n/a          | CONFLICT |
| no       | yes            | yes      | manual ok    | REVIEW_REQUIRED |

Layer 4 may only write fields whose state is in WRITABLE_STATES.

Cognitive integration: before returning LOW_CONFIDENCE or CONFLICT, the
Ambiguity Judge is consulted (when enabled). Its judgment may promote a
field to FILL or confirm blocking — but it never bypasses write authority.
"""
from __future__ import annotations

from ..cognitive.ambiguity_judge import (
    judge_ambiguity,
    should_escalate,
    should_escalate_conflict,
    should_escalate_multi_candidate,
)
from ..core.models import (
    EvidenceLedgerEntry,
    FieldDecision,
    FieldNode,
    ObligationGraph,
)
from ..core.status import DecisionState, WriteAuthority
from .confidence import compute_confidence, is_low_confidence
from .value_sanity import is_value_plausible


def decide_field(
    node: FieldNode,
    entry: EvidenceLedgerEntry | None,
    *,
    n_a_approved: bool = False,
    review_marker_allowed: bool = True,
) -> FieldDecision:
    """Pure function: obligation + evidence -> state."""
    write_auth = node.write_authority

    if node.never_write:
        return _decision(
            node, DecisionState.OPTIONAL_BLANK,
            "Never-write field; left untouched.",
            entry, n_a_approved, write_auth=WriteAuthority.UNAUTHORIZED,
        )

    has_value = bool(entry and entry.candidate_value)
    is_conflict = bool(entry and entry.decision == "conflict")
    is_weak = bool(entry and entry.decision == "weak")
    is_out_of_scope = bool(entry and entry.decision == "out_of_scope")
    map_authorizes = write_auth is WriteAuthority.EXACT_APPROVAL_MAP

    # 1. Conflict trumps - even if a value is present, refuse to pick
    #    Cognitive: ALWAYS escalate conflicts to the ambiguity judge when enabled.
    #    The judge determines which candidate is semantically correct.
    if is_conflict and map_authorizes:
        if not node.required:
            return _decision(
                node, DecisionState.OPTIONAL_BLANK,
                "Optional field; conflicting candidates found, so left blank.",
                entry, n_a_approved, write_auth=write_auth,
            )
        if should_escalate_conflict(entry):
            judgment = judge_ambiguity(node, entry, problem="conflicting_sources")
            if judgment and judgment.judgment == "supports_field" and judgment.confidence >= 0.8:
                if not is_value_plausible(node.field_id, entry.candidate_value):
                    return _decision(
                        node, DecisionState.LOW_CONFIDENCE,
                        f"Cognitive judge resolved conflict but value failed sanity gate.",
                        entry, n_a_approved, write_auth=write_auth,
                    )
                confidence = compute_confidence(node, entry, write_authority=write_auth, n_a_approved=False)
                return _decision(
                    node, DecisionState.FILL,
                    f"Conflict resolved by cognitive judge: {judgment.reason}",
                    entry, n_a_approved, write_auth=write_auth,
                )
        return _decision(
            node, DecisionState.CONFLICT,
            f"Multiple distinct values in evidence: {_alt_summary(entry)}",
            entry, n_a_approved, write_auth=write_auth,
        )

    # 2. Found value + map authorizes -> FILL (or LOW_CONFIDENCE if weak)
    if has_value and map_authorizes and not is_weak:
        if not is_value_plausible(node.field_id, entry.candidate_value):
            if not node.required:
                return _decision(
                    node, DecisionState.OPTIONAL_BLANK,
                    "Optional field; implausible candidate found, so left blank.",
                    entry, n_a_approved, write_auth=write_auth,
                )
            return _decision(
                node, DecisionState.LOW_CONFIDENCE,
                f"Value failed sanity gate: '{entry.candidate_value[:40]}...' is not a plausible value for {node.field_id}.",
                entry, n_a_approved, write_auth=write_auth,
            )
        confidence = compute_confidence(node, entry, write_authority=write_auth, n_a_approved=False)
        if is_low_confidence(confidence):
            # Multi-candidate fields get escalated to judge even if not conflict
            if should_escalate_multi_candidate(entry):
                judgment = judge_ambiguity(node, entry, problem="low_confidence_multi_candidate")
                if judgment and judgment.judgment == "supports_field" and judgment.confidence >= 0.75:
                    return _decision(
                        node, DecisionState.FILL,
                        f"Low-confidence promoted by cognitive judge: {judgment.reason}",
                        entry, n_a_approved, write_auth=write_auth,
                    )
            return _decision(
                node, DecisionState.LOW_CONFIDENCE,
                f"Evidence value '{entry.candidate_value}' present but write-confidence too low ({confidence.write}).",
                entry, n_a_approved, write_auth=write_auth,
            )
        return _decision(
            node, DecisionState.FILL,
            f"Authorized fill from {entry.source_file} (chunk {entry.chunk_id}).",
            entry, n_a_approved, write_auth=write_auth,
        )

    # 3. Found value but map does NOT authorize -> BLOCKED_UNAUTHORIZED
    if has_value and not map_authorizes:
        return _decision(
            node, DecisionState.BLOCKED_UNAUTHORIZED,
            "Evidence found but no exact approval-map authorization for this cell.",
            entry, n_a_approved, write_auth=WriteAuthority.UNAUTHORIZED,
        )

    # 4. Weak / no value cases
    #    Cognitive: ask the Ambiguity Judge if the weak evidence actually supports the field.
    #    With expanded triggers, always escalate weak evidence when cognitive is enabled.
    if is_weak and not node.required:
        return _decision(
            node, DecisionState.OPTIONAL_BLANK,
            "Optional field; weak candidate found, so left blank.",
            entry, n_a_approved, write_auth=write_auth,
        )

    if is_weak and node.required:
        if should_escalate(entry.confidence if entry else 0.0) or should_escalate_multi_candidate(entry):
            judgment = judge_ambiguity(node, entry, problem="weak_evidence")
            if judgment and judgment.judgment == "supports_field" and judgment.confidence >= 0.75:
                if not is_value_plausible(node.field_id, entry.candidate_value):
                    return _decision(
                        node, DecisionState.LOW_CONFIDENCE,
                        f"Cognitive judge supports but value failed sanity gate.",
                        entry, n_a_approved, write_auth=write_auth,
                    )
                confidence = compute_confidence(node, entry, write_authority=write_auth, n_a_approved=False)
                return _decision(
                    node, DecisionState.FILL,
                    f"Weak evidence promoted by cognitive judge: {judgment.reason}",
                    entry, n_a_approved, write_auth=write_auth,
                )
        return _decision(
            node, DecisionState.LOW_CONFIDENCE,
            "Targeted-search hint found but no extracted value.",
            entry, n_a_approved, write_auth=write_auth,
        )

    if is_out_of_scope:
        if not node.required:
            return _decision(
                node, DecisionState.OPTIONAL_BLANK,
                "Optional field; only out-of-scope candidates found, so left blank.",
                entry, n_a_approved, write_auth=write_auth,
            )
        return _decision(
            node, DecisionState.BLOCKED_NO_SOURCE,
            "Only out-of-scope candidates found (cross-form contamination).",
            entry, n_a_approved, write_auth=write_auth,
        )

    # 5. No value, required, N/A approved -> APPROVED_NA
    if not has_value and node.required and n_a_approved:
        return _decision(
            node, DecisionState.APPROVED_NA,
            "No evidence found; approved N/A exception applied.",
            entry, n_a_approved, write_auth=WriteAuthority.APPROVED_NA_INSERTION,
        )

    # 6. No value, required, no N/A
    if not has_value and node.required:
        if review_marker_allowed:
            return _decision(
                node, DecisionState.REVIEW_REQUIRED,
                "Required field with no evidence and no approved N/A; manual review marker emitted.",
                entry, n_a_approved, write_auth=WriteAuthority.UNAUTHORIZED,
            )
        return _decision(
            node, DecisionState.BLOCKED_NO_SOURCE,
            "Required field with no evidence; review markers disabled by policy.",
            entry, n_a_approved, write_auth=WriteAuthority.UNAUTHORIZED,
        )

    # 7. No value, optional
    return _decision(
        node, DecisionState.OPTIONAL_BLANK,
        "Optional field; left blank.",
        entry, n_a_approved, write_auth=write_auth,
    )


def _decision(
    node: FieldNode,
    state: DecisionState,
    reason: str,
    entry: EvidenceLedgerEntry | None,
    n_a_approved: bool,
    *,
    write_auth: WriteAuthority,
) -> FieldDecision:
    confidence = compute_confidence(
        node, entry, write_authority=write_auth, n_a_approved=n_a_approved,
    )
    value = entry.candidate_value if entry and state in {DecisionState.FILL, DecisionState.LOW_CONFIDENCE} else None
    return FieldDecision(
        field_id=node.field_id,
        state=state,
        value=value,
        reason=reason,
        confidence=confidence,
        evidence_ref=entry,
        write_authority=write_auth,
    )


def _alt_summary(entry: EvidenceLedgerEntry | None) -> str:
    if not entry:
        return ""
    primary = entry.candidate_value or "<none>"
    alts = ", ".join(a.get("value", "?") for a in entry.alternates)
    return f"primary={primary!r}; alternates=[{alts}]"


def decide_form(
    graph: ObligationGraph,
    ledger: dict[str, EvidenceLedgerEntry],
    *,
    n_a_approvals: dict[str, bool] | None = None,
) -> dict[str, FieldDecision]:
    n_a_approvals = n_a_approvals or {}
    out: dict[str, FieldDecision] = {}
    for fid, node in graph.fields.items():
        entry = ledger.get(fid)
        out[fid] = decide_field(
            node,
            entry,
            n_a_approved=n_a_approvals.get(fid, False),
        )
    return out
