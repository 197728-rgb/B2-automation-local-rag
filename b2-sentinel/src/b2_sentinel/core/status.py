"""SENTINEL status enums.

Two orthogonal pass-bits combine into the final status:
    overall_passed = overall_passed_format AND overall_passed_completion
"""
from __future__ import annotations

from enum import Enum


class DecisionState(str, Enum):
    """The eight per-field states from the closed-loop spec."""

    FILL = "FILL"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    LOW_CONFIDENCE = "LOW_CONFIDENCE"
    CONFLICT = "CONFLICT"
    OPTIONAL_BLANK = "OPTIONAL_BLANK"
    APPROVED_NA = "APPROVED_NA"
    BLOCKED_NO_SOURCE = "BLOCKED_NO_SOURCE"
    BLOCKED_UNAUTHORIZED = "BLOCKED_UNAUTHORIZED"


WRITABLE_STATES: frozenset[DecisionState] = frozenset({
    DecisionState.FILL,
    DecisionState.APPROVED_NA,
})

BLOCKING_STATES: frozenset[DecisionState] = frozenset({
    DecisionState.REVIEW_REQUIRED,
    DecisionState.LOW_CONFIDENCE,
    DecisionState.CONFLICT,
    DecisionState.BLOCKED_NO_SOURCE,
    DecisionState.BLOCKED_UNAUTHORIZED,
})


class FinalStatus(str, Enum):
    """Top-level outcomes from the Completion Judge."""

    SUCCESS = "success"
    BLOCKED_PENDING_NO_SOURCE_OR_NA_RESOLUTION = "blocked_pending_no_source_or_na_resolution"
    BLOCKED_PENDING_REVIEW_REQUIRED = "blocked_pending_review_required"
    FAILED_STRUCTURE_GUARD = "failed_structure_guard"
    FAILED_UNAUTHORIZED_WRITE = "failed_unauthorized_write"
    FAILED_CONFLICT_RESOLUTION = "failed_conflict_resolution"
    FAILED_LOW_CONFIDENCE_RESOLUTION = "failed_low_confidence_resolution"
    FAILED_COMPLETION = "failed_completion"
    FAILED_RUNTIME_ERROR = "failed_runtime_error"


class RolloverDecision(str, Enum):
    """Innovation 2 - Rollover Memory classification."""

    SAFE_TO_ROLL = "safe_to_roll"
    ROLL_WITH_DATE_CHECK = "roll_with_date_check"
    REQUIRES_NEW_EVIDENCE = "requires_new_evidence"
    DO_NOT_ROLL = "do_not_roll"
    OBSOLETE = "obsolete"
    CONFLICT = "conflict"


class WriteAuthority(str, Enum):
    """Layer 4 - the only allowed write paths."""

    EXACT_APPROVAL_MAP = "exact_approval_map"
    CONTROLLED_MANUAL_REPLACEMENT = "controlled_manual_replacement"
    APPROVED_NA_INSERTION = "approved_na_insertion"
    REVIEW_MARKER_INSERTION = "review_marker_insertion"
    UNAUTHORIZED = "unauthorized"
