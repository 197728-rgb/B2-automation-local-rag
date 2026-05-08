"""DocuPipe-shaped JSON -> B24 normalizer -> OOXML fill (shared B24_RL2.docx template, RL1 manifest)."""

from __future__ import annotations

import json
from pathlib import Path

from b2_automation.b24_normalizer import normalize_docupipe_payload_for_b24_rl1
from b2_automation.b24_rl1_filler import load_manifest
from b2_automation.ooxml_writer import patch_docx_cells
from b2_automation.paths import B24_SHARED_TEMPLATE_DOCX


def run_b24_rl1_from_docupipe(
    docupipe_json: Path,
    root: Path,
    output_docx: Path,
) -> Path:
    raw = json.loads(docupipe_json.read_text(encoding="utf-8"))
    fields = normalize_docupipe_payload_for_b24_rl1(raw)
    manifest = load_manifest(root / "schemas" / "templates" / "B24_RL1.json")
    template = root / "templates" / B24_SHARED_TEMPLATE_DOCX
    outcome = patch_docx_cells(template, manifest, fields, output_docx)
    if not outcome.structure_guard_passed:
        raise RuntimeError(f"OOXML structure guard failed: {outcome.structure_guard_report}")
    return outcome.output_docx
