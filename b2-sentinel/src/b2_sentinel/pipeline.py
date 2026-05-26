"""Top-level SENTINEL pipeline.

Runs Agent 1 -> Agent 2 -> Agent 3 for one form, then writes the full
audit packet via Layer 8. Supports rollover comparison and run delta.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .agents.agent1_regulatory_analyst import run_regulatory_analyst
from .agents.agent2_forensic_investigator import run_forensic_investigator
from .agents.agent3_writer_judge import run_writer_judge
from .core.paths import (
    INBOX_DIR,
    OUTPUTS_DIR,
    PRIOR_PACKET_DIR,
    form_template_path,
)
from .core.status import FinalStatus
from .innovations.evidence_debt import compute_debt
from .innovations.rollover_memory import evaluate_rollover
from .innovations.run_delta import compute_run_delta, find_previous_report
from .layer8_audit_packet.generator import write_packet


@dataclass
class FormPipelineResult:
    form_id: str
    final_status: FinalStatus
    overall_passed: bool
    artifacts: dict[str, str]
    out_dir: Path


def run_form(
    form_id: str,
    *,
    run_id: str,
    inbox: Path = INBOX_DIR,
    outputs_dir: Path = OUTPUTS_DIR,
    form_version: str = "2026",
) -> FormPipelineResult:
    template = form_template_path(form_id)
    if not template.exists():
        raise FileNotFoundError(f"Template not found for form {form_id}: {template}")

    out_dir = outputs_dir / run_id / form_id
    filled_path = out_dir / f"{form_id}_filled.docx"

    # Agent 1 - Regulatory Analyst
    a1 = run_regulatory_analyst(form_id, form_version=form_version)
    graph = a1.obligation_graph

    # Agent 2 - Forensic Investigator
    a2 = run_forensic_investigator(graph=graph, inbox=inbox)

    # Agent 3 - Controlled Writer / Judge (Layers 4, 5, 6, 7)
    a3 = run_writer_judge(
        graph=graph,
        ledger=a2.ledger,
        template_path=template,
        output_filled_path=filled_path,
    )

    # Innovations
    debt = compute_debt(graph, a2.ledger, a3.decisions)

    prior_packet = _find_prior_packet_for(form_id)
    rollover_entries = evaluate_rollover(
        graph=graph,
        new_ledger=a2.ledger,
        prior_filled_path=prior_packet,
    )

    prev_report = find_previous_report(form_id, outputs_dir, run_id)
    delta = compute_run_delta(current=a3.completion_report, previous_path=prev_report)

    # Layer 8 packet
    artifacts = write_packet(
        out_dir=out_dir,
        graph=graph,
        ledger=a2.ledger,
        decisions=a3.decisions,
        structure_report=a3.structure_report,
        completion=a3.completion_report,
        na_log=a3.na_log,
        manual_corrections=a3.manual_corrections,
        debt_entries=debt,
        rollover_entries=rollover_entries,
        run_delta=delta,
        filled_docx_path=a3.filled_path,
    )

    return FormPipelineResult(
        form_id=form_id,
        final_status=a3.completion_report.final_status,
        overall_passed=a3.completion_report.overall_passed,
        artifacts=artifacts,
        out_dir=out_dir,
    )


def _find_prior_packet_for(form_id: str) -> Path | None:
    if not PRIOR_PACKET_DIR.exists():
        return None
    matches: list[Path] = []
    for p in PRIOR_PACKET_DIR.glob("*.docx"):
        name = p.stem.upper()
        target = form_id.upper().replace("_RL2", "").replace("_PAGE", " PAGE")
        if target in name or form_id.upper() in name:
            matches.append(p)
    if not matches:
        return None
    matches.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return matches[0]
