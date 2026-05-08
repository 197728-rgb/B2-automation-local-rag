"""Cell-level evidence model for table-driven B-2 forms."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Literal

class DecisionState(str, Enum):
    FILL = "FILL"
    BLANK = "BLANK"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    MISSING = "MISSING"
    CONFLICT = "CONFLICT"
    LOW_CONFIDENCE = "LOW_CONFIDENCE"


def parse_decision_state(raw: str | None) -> DecisionState | None:
    """Parse a serialized decision state string (strict; no fuzzy matching)."""
    if raw is None:
        return None
    s = str(raw).strip()
    if not s:
        return None
    try:
        return DecisionState(s)
    except ValueError:
        return None


Decision = DecisionState
CellRole = Literal[
    "target",
    "label",
    "section_header",
    "instruction",
    "static_text",
    "dropdown",
    "notes",
    "duplicate_merge",
    "spacer",
    "footer",
    "unknown",
]


@dataclass(frozen=True)
class EvidenceCell:
    """Single Word table cell mapped to one audit evidence requirement.

    The key unit is not field-name -> value. It is:

        table -> row -> evidence requirement -> fill cell
    """

    form: str
    section: str
    table_index: int
    row_index: int
    col_index: int
    row_label: str
    cell_label: str
    canonical_path: str
    value: str | None = None
    confidence: float | None = None
    source_document: str | None = None
    source_page: int | None = None
    decision: Decision = DecisionState.BLANK
    is_target: bool = False
    cell_role: CellRole = "unknown"
    required: bool = False
    rule: str = ""
    source_evidence: str = ""
    notes: str = ""

    def to_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["decision"] = self.decision.value
        return data


@dataclass(frozen=True)
class FieldDecision:
    field_id: str
    state: DecisionState
    selected_value: str | None = None
    confidence: float | None = None
    reason: str = ""
    candidates: tuple[dict[str, Any], ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "field_id": self.field_id,
            "state": self.state.value,
            "selected_value": self.selected_value,
            "confidence": self.confidence,
            "reason": self.reason,
            "candidates": list(self.candidates),
        }


def decide_cell(
    value: str | None,
    *,
    confidence: float | None,
    threshold: float,
    required: bool = False,
    conflict_detected: bool = False,
    cell_role: CellRole = "target",
) -> Decision:
    """Return the allowed decision for a mapped evidence cell.

    Rules:
    - required + missing => MISSING
    - optional + missing => BLANK
    - conflict => CONFLICT
    - low confidence => LOW_CONFIDENCE
    - notes cells are reviewed unless explicitly supported by upstream aggregation
    - otherwise => FILL
    """

    missing = value is None or str(value).strip() == ""
    if missing:
        return DecisionState.MISSING if required else DecisionState.BLANK
    if conflict_detected:
        return DecisionState.CONFLICT
    if confidence is not None and confidence < threshold:
        return DecisionState.LOW_CONFIDENCE
    if cell_role == "notes":
        return DecisionState.REVIEW_REQUIRED
    return DecisionState.FILL
