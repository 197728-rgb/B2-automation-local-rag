"""Innovation 3 - the Semantic Alias Brain.

Governed directional aliases. Every alias has a direction so we never use a
write_bridge alias as a read-only lookup or vice versa.

Alias rules live in `schemas/alias_rules/*.json`. Each file is a list of
AliasRule entries; the Brain merges them all at construction time.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from ..core.models import AliasRule
from ..core.paths import ALIAS_RULES_DIR


class AliasBrain:
    """Governed alias resolution."""

    def __init__(self, rules: list[AliasRule] | None = None) -> None:
        self._rules: list[AliasRule] = rules or []
        self._by_target: dict[str, list[AliasRule]] = {}
        for rule in self._rules:
            self._by_target.setdefault(rule.to_field, []).append(rule)

    @classmethod
    def from_disk(cls, directory: Path = ALIAS_RULES_DIR) -> "AliasBrain":
        rules: list[AliasRule] = []
        if directory.exists():
            for path in sorted(directory.glob("*.json")):
                with path.open(encoding="utf-8") as fh:
                    data = json.load(fh)
                if isinstance(data, dict):
                    items = data.get("rules", [])
                else:
                    items = data
                for raw in items:
                    rules.append(AliasRule.model_validate(raw))
        return cls(rules)

    def aliases_for(self, target_field: str, form_id: str | None = None) -> Iterable[AliasRule]:
        for rule in self._by_target.get(target_field, []):
            if rule.forms and form_id and form_id not in rule.forms:
                continue
            yield rule

    def all_rules(self) -> list[AliasRule]:
        return list(self._rules)

    def is_authorized_for_write(self, alias: str, target_field: str, form_id: str) -> bool:
        for rule in self.aliases_for(target_field, form_id):
            if rule.from_key == alias and rule.direction == "write_bridge":
                return True
        return False
