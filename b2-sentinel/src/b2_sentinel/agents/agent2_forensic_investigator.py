"""Agent 2 - The Forensic Investigator.

Inputs: ObligationGraph + inbox
Runs: Wave 1 collect -> Wave 2 normalize -> Wave 3 targeted -> Wave 4 contamination
Outputs: EvidenceLedger + missing_evidence list + alias_resolution map
Thinks: 'This field looks blank not because the form failed, but because the
        source package lacks PITP metadata and the previous extractor missed
        a car_number alias bridge.'
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..core.models import (
    EvidenceLedger,
    EvidenceLedgerEntry,
    ObligationGraph,
    SourceChunk,
)
from ..innovations.alias_brain import AliasBrain
from ..layer2_evidence_hunter.evidence_ledger import build_ledger
from ..layer2_evidence_hunter.wave1_collect import wave1_collect
from ..layer2_evidence_hunter.wave2_normalize import wave2_normalize
from ..layer2_evidence_hunter.wave3_targeted import wave3_targeted
from ..layer2_evidence_hunter.wave4_contamination import wave4_contamination


@dataclass
class ForensicInvestigatorOutput:
    chunks: list[SourceChunk]
    entries: dict[str, EvidenceLedgerEntry]
    ledger: EvidenceLedger
    missing_field_ids: list[str]
    alias_resolution: dict[str, str | None]


def run_forensic_investigator(
    *,
    graph: ObligationGraph,
    inbox: Path,
    alias_brain: AliasBrain | None = None,
) -> ForensicInvestigatorOutput:
    alias_brain = alias_brain or AliasBrain.from_disk()
    chunks, _cognitive_extractions = wave1_collect(inbox, graph=graph)
    entries = wave2_normalize(chunks, graph, alias_brain=alias_brain)
    entries = wave3_targeted(chunks, graph, entries)
    entries = wave4_contamination(graph, entries, chunks)

    ledger = build_ledger(graph.form_id, entries, chunks)
    missing = [
        fid for fid, e in entries.items()
        if graph.fields[fid].required
        and graph.fields[fid].completion_blocker_if_missing
        and (e.candidate_value is None or e.decision in ("missing", "out_of_scope"))
    ]
    alias_resolution = {fid: e.alias_used for fid, e in entries.items()}

    return ForensicInvestigatorOutput(
        chunks=chunks,
        entries=entries,
        ledger=ledger,
        missing_field_ids=sorted(missing),
        alias_resolution=alias_resolution,
    )
