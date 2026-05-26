"""Tests for the Cognitive Orchestration Layer.

Tests cover:
- NullAdapter returns defaults (graceful degradation)
- Cognitive models validate correctly
- Evidence Hunter returns empty when disabled
- Ambiguity Judge returns None when disabled
- Alias Resolver returns None when disabled
- Synthesizer returns None when disabled
- Self-Critique returns empty when disabled
- Full pipeline runs identically with cognitive disabled
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from b2_sentinel.cognitive.adapter import NullAdapter, create_adapter, set_adapter
from b2_sentinel.cognitive.config import CognitiveConfig, set_cognitive_config
from b2_sentinel.cognitive.models import (
    AmbiguityJudgment,
    CandidateFact,
    CognitiveExtraction,
    CritiqueFinding,
    SemanticAlias,
    SourceFragment,
    SynthesizedEvidence,
)
from b2_sentinel.core.status import DecisionState


class TestCognitiveModels:
    def test_candidate_fact_validates(self):
        fact = CandidateFact(
            field_id="car.mark",
            value="UTLX 12345",
            semantic_match=True,
            reasoning="Text explicitly states car initial and number",
            risk="low",
        )
        assert fact.field_id == "car.mark"
        assert fact.semantic_match is True

    def test_cognitive_extraction_validates(self):
        ext = CognitiveExtraction(
            source_file="test.pdf",
            source_text="Some text about car UTLX 12345",
            meaning="Identifies tank car reporting mark",
            candidate_facts=[
                CandidateFact(
                    field_id="car.mark",
                    value="UTLX 12345",
                    semantic_match=True,
                    reasoning="explicit",
                    risk="low",
                )
            ],
            confidence=0.92,
        )
        assert ext.confidence == 0.92
        assert len(ext.candidate_facts) == 1

    def test_ambiguity_judgment_validates(self):
        j = AmbiguityJudgment(
            field_id="pitp.approved_by",
            judgment="ambiguous",
            confidence=0.6,
            risk="medium",
            recommended_state=DecisionState.LOW_CONFIDENCE,
            reason="Name appears near PITP but not as approving authority",
            requires_human_or_exception=True,
        )
        assert j.judgment == "ambiguous"
        assert j.requires_human_or_exception is True

    def test_semantic_alias_validates(self):
        alias = SemanticAlias(
            from_text="Owner authorization memo",
            to_field="tco.instructions",
            tier=2,
            confidence=0.85,
            reasoning="Semantically equivalent to tank car owner instructions",
            auto_usable=True,
        )
        assert alias.tier == 2
        assert alias.auto_usable is True

    def test_tier3_not_auto_usable(self):
        alias = SemanticAlias(
            from_text="Repair notes",
            to_field="tco.instructions",
            tier=3,
            confidence=0.4,
            reasoning="Possible match but too uncertain",
            auto_usable=False,
        )
        assert alias.auto_usable is False

    def test_synthesized_evidence_validates(self):
        synth = SynthesizedEvidence(
            synthesized_fact="RES-041 Rev I approved by J. Riggs on 9/26/2025",
            field_group={
                "procedure.id": "RES-041",
                "procedure.rev": "I",
                "procedure.approved_by": "J. Riggs",
            },
            source_fragments=[
                SourceFragment(
                    source_file="procedure_list.pdf",
                    page=2,
                    text_excerpt="Procedure RES-041 Rev I",
                ),
                SourceFragment(
                    source_file="approval_log.xlsx",
                    page=None,
                    chunk_id="row-14",
                    text_excerpt="Approved by J. Riggs",
                ),
            ],
            risk="medium",
            single_source_proof=False,
            multi_source_synthesis=True,
            confidence=0.78,
        )
        assert synth.multi_source_synthesis is True
        assert len(synth.source_fragments) == 2

    def test_critique_finding_validates(self):
        finding = CritiqueFinding(
            field_id="procedure.approved_date",
            issue="Value looks like a revision number, not a date",
            severity="error",
            recommendation="Verify this is actually a date, not revision I",
            confidence=0.88,
            cell_value="I",
        )
        assert finding.severity == "error"


class TestNullAdapter:
    def test_null_adapter_returns_defaults(self):
        config = CognitiveConfig(enabled=False, adapter="null")
        adapter = NullAdapter(config)
        result = adapter.reason("system", "user", CognitiveExtraction)
        assert isinstance(result, CognitiveExtraction)
        assert result.meaning == ""
        assert result.confidence == 0.0

    def test_null_adapter_batch(self):
        config = CognitiveConfig(enabled=False, adapter="null")
        adapter = NullAdapter(config)
        results = adapter.reason_batch("system", ["u1", "u2", "u3"], CognitiveExtraction)
        assert len(results) == 3

    def test_create_adapter_null_default(self):
        config = CognitiveConfig(enabled=False, adapter="null")
        adapter = create_adapter(config)
        assert isinstance(adapter, NullAdapter)


class TestGracefulDegradation:
    """When cognitive is disabled, all components return empty/None."""

    def setup_method(self):
        self._config = CognitiveConfig(enabled=False)
        set_cognitive_config(self._config)
        set_adapter(NullAdapter(self._config))

    def test_evidence_hunter_returns_empty(self):
        from b2_sentinel.cognitive.evidence_hunter import extract_meaning
        from b2_sentinel.core.models import ObligationGraph

        graph = ObligationGraph(
            form_id="B89", form_version="2026",
            template_path="t.docx", fields={},
        )
        result = extract_meaning(
            "some text", source_file="f.pdf", form_id="B89", graph=graph
        )
        assert result.meaning == ""
        assert result.confidence == 0.0

    def test_ambiguity_judge_returns_none(self):
        from b2_sentinel.cognitive.ambiguity_judge import judge_ambiguity
        from b2_sentinel.core.models import EvidenceLedgerEntry, FieldNode

        node = FieldNode(
            field_id="test", label="Test", table_index=0, row=0, col=0,
        )
        entry = EvidenceLedgerEntry(field_id="test", decision="weak")
        result = judge_ambiguity(node, entry, problem="test")
        assert result is None

    def test_alias_resolver_returns_none(self):
        from b2_sentinel.cognitive.alias_resolver import resolve_semantic_alias
        from b2_sentinel.core.models import ObligationGraph

        graph = ObligationGraph(
            form_id="B89", form_version="2026",
            template_path="t.docx", fields={},
        )
        result = resolve_semantic_alias(
            "unknown", context_text="ctx", form_id="B89", graph=graph
        )
        assert result is None

    def test_synthesizer_returns_none(self):
        from b2_sentinel.cognitive.synthesizer import synthesize_evidence

        result = synthesize_evidence(
            [{"text": "a"}, {"text": "b"}],
            target_fields=["f1"],
            form_id="B89",
        )
        assert result is None

    def test_self_critique_returns_empty(self):
        from b2_sentinel.cognitive.self_critique import critique_field
        from b2_sentinel.core.models import ConfidenceBundle, FieldDecision, FieldNode
        from b2_sentinel.core.status import WriteAuthority

        node = FieldNode(
            field_id="test", label="Test", table_index=0, row=0, col=0,
        )
        decision = FieldDecision(
            field_id="test", state=DecisionState.FILL,
            value="val", reason="test",
            confidence=ConfidenceBundle(),
            write_authority=WriteAuthority.EXACT_APPROVAL_MAP,
        )
        result = critique_field(node, decision, cell_value="val", form_id="B89")
        assert result == []


class TestDecisionMatrixWithCognitiveDisabled:
    """Decision matrix still works correctly with cognitive layer disabled."""

    def setup_method(self):
        config = CognitiveConfig(enabled=False)
        set_cognitive_config(config)
        set_adapter(NullAdapter(config))

    def test_conflict_stays_conflict(self):
        from b2_sentinel.core.models import EvidenceLedgerEntry, FieldNode
        from b2_sentinel.layer3_decision_engine.decide import decide_field

        node = FieldNode(
            field_id="test", label="Test", table_index=0, row=0, col=0,
            required=True,
        )
        entry = EvidenceLedgerEntry(
            field_id="test", candidate_value="A",
            decision="conflict", confidence=0.5,
            alternates=[{"value": "B", "source": "other.pdf"}],
        )
        result = decide_field(node, entry, n_a_approved=False)
        assert result.state == DecisionState.CONFLICT

    def test_weak_stays_low_confidence(self):
        from b2_sentinel.core.models import EvidenceLedgerEntry, FieldNode
        from b2_sentinel.layer3_decision_engine.decide import decide_field

        node = FieldNode(
            field_id="test", label="Test", table_index=0, row=0, col=0,
            required=True,
        )
        entry = EvidenceLedgerEntry(
            field_id="test", candidate_value=None,
            decision="weak", confidence=0.3,
        )
        result = decide_field(node, entry, n_a_approved=False)
        assert result.state == DecisionState.LOW_CONFIDENCE
