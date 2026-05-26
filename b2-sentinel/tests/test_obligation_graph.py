"""Tests for Layer 1: Form Obligation Graph builder."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from b2_sentinel.core.models import ApprovalMap, ObligationGraph
from b2_sentinel.core.paths import MAPS_DIR as SCHEMAS_MAPS


class TestObligationGraph:
    def test_b89_map_loads(self):
        map_path = SCHEMAS_MAPS / "B89.json"
        if not map_path.exists():
            return
        raw = json.loads(map_path.read_text(encoding="utf-8"))
        amap = ApprovalMap.model_validate(raw)
        assert amap.form_id == "B89"
        assert amap.form_version == "2026"
        assert len(amap.fields) > 0

    def test_obligation_graph_classifies_fields(self):
        from b2_sentinel.layer1_form_brain.obligation_graph import build_obligation_graph

        map_path = SCHEMAS_MAPS / "B89.json"
        if not map_path.exists():
            return
        graph = build_obligation_graph("B89")
        assert isinstance(graph, ObligationGraph)
        assert graph.form_id == "B89"
        assert graph.required_total >= 0
        required_ids = graph.required_field_ids()
        assert isinstance(required_ids, list)

    def test_obligation_graph_field_node_attributes(self):
        from b2_sentinel.layer1_form_brain.obligation_graph import build_obligation_graph

        map_path = SCHEMAS_MAPS / "B89.json"
        if not map_path.exists():
            return
        graph = build_obligation_graph("B89")
        for fid, node in graph.fields.items():
            assert node.field_id == fid
            assert node.table_index >= 0
            assert node.row >= 0
            assert node.col >= 0
