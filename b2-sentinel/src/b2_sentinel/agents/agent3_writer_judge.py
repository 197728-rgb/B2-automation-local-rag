"""Agent 3 - The Controlled Writer / Judge.

Inputs: ObligationGraph + EvidenceLedger
Runs Layer 7 (N/A workflow) -> Layer 3 (decisions) -> Layer 4 (write) ->
     Layer 5 (structure guard) -> Layer 6 (completion judge + self-critique)
Outputs: filled DOCX path + decisions + structure report + completion report
         + na_log + manual_corrections (empty by default) + self_critique
Thinks: 'I can write this value because the evidence supports it and the
        exact approval map authorizes the target cell. I cannot close the
        job because 4 required fields remain no-source blockers.'

If structure guard fails, the filled DOCX is discarded.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from ..core.models import (
    CompletionReport,
    EvidenceLedger,
    FieldDecision,
    ManualCorrectionEntry,
    NAExceptionEntry,
    ObligationGraph,
    StructureGuardReport,
)
from ..core.status import FinalStatus
from ..layer3_decision_engine.decide import decide_form
from ..layer4_controlled_writer.ooxml_writer import patch_docx
from ..layer4_controlled_writer.patch_planner import plan_writes
from ..layer5_structure_guard.guard import run_structure_guard
from ..layer6_completion_judge.judge import judge_completion
from ..layer6_completion_judge.self_critique import self_critique
from ..layer7_exception_engine.na_workflow import evaluate_na


@dataclass
class WriterJudgeOutput:
    filled_path: Path | None
    decisions: dict[str, FieldDecision]
    na_log: list[NAExceptionEntry]
    manual_corrections: list[ManualCorrectionEntry]
    structure_report: StructureGuardReport
    completion_report: CompletionReport
    self_critique: dict
    patch_results: dict[str, list[str]] = field(default_factory=dict)


def run_writer_judge(
    *,
    graph: ObligationGraph,
    ledger: EvidenceLedger,
    template_path: Path,
    output_filled_path: Path,
) -> WriterJudgeOutput:
    n_a_approvals, na_log = evaluate_na(graph, ledger.entries)

    decisions = decide_form(graph, ledger.entries, n_a_approvals=n_a_approvals)

    plan = plan_writes(graph, decisions)
    patch_results = patch_docx(template_path, output_filled_path, plan)

    structure_report = run_structure_guard(
        form_id=graph.form_id,
        blank_path=template_path,
        filled_path=output_filled_path,
    )

    if not structure_report.structure_guard_passed:
        # Discard the broken output, keep the report
        try:
            output_filled_path.unlink(missing_ok=True)
        except OSError:
            pass
        completion = CompletionReport(
            form_id=graph.form_id,
            overall_passed_format=False,
            overall_passed_completion=False,
            overall_passed=False,
            final_status=FinalStatus.FAILED_STRUCTURE_GUARD,
            required_total=sum(1 for n in graph.fields.values() if n.required and not n.never_write),
            required_filled=0,
            required_blocked=sum(1 for n in graph.fields.values() if n.required and not n.never_write),
            review_required_count=0,
            conflict_count=0,
            low_confidence_count=0,
            approved_na_count=0,
            blocked_no_source_count=0,
            blocked_unauthorized_count=0,
            blockers=["structure guard failed"],
            notes=list(structure_report.notes),
        )
        return WriterJudgeOutput(
            filled_path=None,
            decisions=decisions,
            na_log=na_log,
            manual_corrections=[],
            structure_report=structure_report,
            completion_report=completion,
            self_critique={"findings": [{"issue": "structure_guard_failed"}], "passed": False, "completion_consistent": True},
            patch_results=patch_results,
        )

    completion = judge_completion(
        graph=graph,
        decisions=decisions,
        filled_path=output_filled_path,
        structure_report=structure_report,
    )
    critique = self_critique(
        graph=graph,
        decisions=decisions,
        filled_path=output_filled_path,
        completion=completion,
    )

    return WriterJudgeOutput(
        filled_path=output_filled_path,
        decisions=decisions,
        na_log=na_log,
        manual_corrections=[],
        structure_report=structure_report,
        completion_report=completion,
        self_critique=critique,
        patch_results=patch_results,
    )
