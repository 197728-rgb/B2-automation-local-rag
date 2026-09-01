"""Form Writer — writeCompletedDocx from field map + validated answers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from b2_automation.autonomous_contracts import FieldPipelineResult, MachineFieldMapV1
from b2_automation.ooxml_writer import patch_docx_cells


def field_map_to_manifest(field_map: MachineFieldMapV1) -> dict[str, Any]:
    cells = []
    for req in field_map.fields:
        loc = req.form_location
        if loc.table_index is None or loc.row_index is None or loc.column_index is None:
            continue
        cells.append(
            {
                "field_id": req.id,
                "table_index": loc.table_index,
                "row": loc.row_index,
                "col": loc.column_index,
                "label": req.field_label,
                "required": req.required,
                "cell_role": "target",
            }
        )
    return {"template": Path(field_map.template_file).name, "cells": cells}


def write_completed_form(
    *,
    template_path: Path,
    field_map: MachineFieldMapV1,
    results: list[FieldPipelineResult],
    output_dir: Path,
) -> dict[str, Any]:
    """writeCompletedDocx — copy template and patch cells."""
    output_dir = Path(output_dir)
    completed_dir = output_dir / "completed"
    audit_dir = output_dir / "audit-trail"
    completed_dir.mkdir(parents=True, exist_ok=True)
    audit_dir.mkdir(parents=True, exist_ok=True)

    stem = Path(template_path).stem
    out_docx = completed_dir / f"{stem}_completed.docx"

    manifest = field_map_to_manifest(field_map)
    field_values = {r.answer.requirement_id: r.answer.text for r in results if r.answer.text}
    field_confidences = {r.answer.requirement_id: r.answer.confidence for r in results}

    guard_path = output_dir / "structure_guard_report.json"
    outcome = patch_docx_cells(
        template_path=template_path,
        manifest=manifest,
        field_values=field_values,
        output_path=out_docx,
        field_confidences=field_confidences,
        required_field_ids={req.id for req in field_map.fields if req.required},
        structure_guard_report_path=guard_path,
        approval_map=None,
        strict_approval_coverage=False,
        table_fill_audit_manifest=manifest,
    )

    write_report = {
        "template": str(template_path),
        "output_docx": str(out_docx),
        "structure_guard_passed": outcome.structure_guard_passed,
        "patched_fields": list(outcome.patched_fields),
        "errors": list(outcome.errors),
        "fields": [],
    }
    for r in results:
        loc = r.requirement.form_location
        write_report["fields"].append(
            {
                "field_id": r.requirement.id,
                "label": r.requirement.field_label,
                "write_status": "written" if r.requirement.id in outcome.patched_fields else "skipped",
                "automation_status": r.answer.automation_status,
                "fallback_applied": r.answer.fallback_applied,
                "table_index": loc.table_index,
                "row_index": loc.row_index,
                "column_index": loc.column_index,
            }
        )

    map_path = audit_dir / f"{stem}_machine_field_map.v1.json"
    answers_path = audit_dir / f"{stem}_answers.json"
    report_path = audit_dir / f"{stem}_write_report.json"
    map_path.write_text(json.dumps(field_map.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
    answers_path.write_text(
        json.dumps([r.answer.to_dict() for r in results], indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    report_path.write_text(json.dumps(write_report, indent=2, ensure_ascii=False), encoding="utf-8")

    return {
        "completed_docx": str(out_docx),
        "machine_field_map_path": str(map_path),
        "answers_path": str(answers_path),
        "write_report_path": str(report_path),
        "structure_guard_passed": outcome.structure_guard_passed,
        "write_report": write_report,
    }
