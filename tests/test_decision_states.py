from b2_automation.cell_evidence import DecisionState, decide_cell


def test_decide_cell_missing_required_is_missing_state() -> None:
    assert decide_cell("", confidence=None, threshold=0.7, required=True) == DecisionState.MISSING


def test_decide_cell_conflict_has_priority() -> None:
    assert decide_cell("abc", confidence=0.95, threshold=0.7, required=True, conflict_detected=True) == DecisionState.CONFLICT


def test_decide_cell_low_confidence_state() -> None:
    assert decide_cell("abc", confidence=0.5, threshold=0.7, required=False) == DecisionState.LOW_CONFIDENCE

