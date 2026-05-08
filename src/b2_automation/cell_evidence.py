"""Cell-level evidence model for table-driven B-2 forms."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Literal

Decision = Literal["fill", "blank", "review"]
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
    decision: Decision = "blank"
    is_target: bool = False
    cell_role: CellRole = "unknown"
    required: bool = False
    rule: str = ""
    source_evidence: str = ""
    notes: str = ""

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def decide_cell(
    value: str | None,
    *,
    confidence: float | None,
    threshold: float,
    required: bool = False,
    conflict_detected: bool = False,
    cell_role: CellRole = "target",
) -> DecisionState:
    """Return the allowed decision for a mapped evidence cell.

    Rules:
    - required + missing => review
    - optional + missing => blank
    - conflict => review
    - low confidence => review
    - notes cells are reviewed unless explicitly supported by upstream aggregation
    - otherwise => fill
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
class DecisionState(StrEnum):
    FILL = "FILL"
    BLANK = "BLANK"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    MISSING = "MISSING"
    CONFLICT = "CONFLICT"
    LOW_CONFIDENCE = "LOW_CONFIDENCE"


def state_to_decision(state: DecisionState) -> Decision:
    if state == DecisionState.FILL:
        return "fill"
    if state == DecisionState.BLANK:
        return "blank"
    return "review"
