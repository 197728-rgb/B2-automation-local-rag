"""Tests for the Semantic Alias Brain innovation."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from b2_sentinel.core.models import AliasRule
from b2_sentinel.innovations.alias_brain import AliasBrain


def _brain() -> AliasBrain:
    rules = [
        AliasRule.model_validate({
            "from": "car_number",
            "to": "car.mark",
            "direction": "write_bridge",
            "forms": ["B81", "B89", "B90"],
            "risk": "low",
            "authority": "approved_alias_rule",
        }),
        AliasRule.model_validate({
            "from": "tank_car_number",
            "to": "car.mark",
            "direction": "write_bridge",
            "forms": ["B81", "B89"],
            "risk": "low",
            "authority": "approved_alias_rule",
        }),
        AliasRule.model_validate({
            "from": "facility_name",
            "to": "tco.name",
            "direction": "read_only",
            "forms": [],
            "risk": "medium",
            "authority": "approved_alias_rule",
        }),
    ]
    return AliasBrain(rules)


class TestAliasBrain:
    def test_aliases_for_target(self):
        brain = _brain()
        aliases = list(brain.aliases_for("car.mark", form_id="B89"))
        assert len(aliases) == 2
        from_keys = {a.from_key for a in aliases}
        assert "car_number" in from_keys
        assert "tank_car_number" in from_keys

    def test_form_scope_filter(self):
        brain = _brain()
        aliases_b89 = list(brain.aliases_for("car.mark", form_id="B89"))
        aliases_b90 = list(brain.aliases_for("car.mark", form_id="B90"))
        assert len(aliases_b89) == 2
        assert len(aliases_b90) == 1  # tank_car_number is B81+B89 only

    def test_no_aliases_for_unknown_target(self):
        brain = _brain()
        aliases = list(brain.aliases_for("unknown.field", form_id="B89"))
        assert len(aliases) == 0

    def test_is_authorized_for_write_bridge(self):
        brain = _brain()
        assert brain.is_authorized_for_write("car_number", "car.mark", "B89") is True

    def test_read_only_not_authorized_for_write(self):
        brain = _brain()
        assert brain.is_authorized_for_write("facility_name", "tco.name", "B89") is False

    def test_wrong_form_not_authorized(self):
        brain = _brain()
        assert brain.is_authorized_for_write("tank_car_number", "car.mark", "B90") is False

    def test_from_disk_loads(self):
        brain = AliasBrain.from_disk()
        rules = brain.all_rules()
        assert isinstance(rules, list)
        if rules:
            assert all(isinstance(r, AliasRule) for r in rules)
