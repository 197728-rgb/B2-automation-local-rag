"""DocuPipe-shaped JSON -> B24 normalizer -> same 5-cell B24_RL1 fill."""

from __future__ import annotations

import json
from pathlib import Path

from b2_automation.b24_normalizer import normalize_docupipe_payload_for_b24_rl1
from b2_automation.b24_rl1_filler import fill_b24_rl1_partial, load_manifest


def run_b24_rl1_from_docupipe(
    docupipe_json: Path,
    root: Path,
    output_docx: Path,
) -> Path:
    raw = json.loads(docupipe_json.read_text(encoding="utf-8"))
    fields = normalize_docupipe_payload_for_b24_rl1(raw)
    manifest = load_manifest(root / "schemas" / "templates" / "B24_RL1.json")
    template = root / "templates" / "B24_RL1.docx"
    return fill_b24_rl1_partial(template, manifest, fields, output_docx)
