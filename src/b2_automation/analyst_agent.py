"""Analyst Agent — blank form → machine_field_map.v1."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from b2_automation.autonomous_contracts import (
    MAPPING_CONFIDENCE_MIN,
    AuditRequirement,
    FormLocation,
    MachineFieldMapSummary,
    MachineFieldMapV1,
)
from b2_automation.docx_structure import (
    DocxStructure,
    extract_docx_structure,
    extract_mammoth_html,
    load_template_manifest_cells,
)
from b2_automation.llm_client import LlmError, generate_json
from b2_automation.local_extraction import utc_now
from b2_automation.paths import resolve_project_root
from b2_automation.schema_catalog import infer_schema_path, load_available_schemas


def _infer_field_type(label: str) -> str:
    lower = label.lower()
    if re.search(r"\bdate\b", lower):
        return "date"
    if re.search(r"\b(number|no\.|#|qty|count|amps|volts)\b", lower):
        return "number"
    if re.search(r"\b(yes|no|applicable|n/a)\b", lower):
        return "boolean"
    return "narrative"


def _field_id(index: int, manifest_field_id: str | None) -> str:
    if manifest_field_id:
        return manifest_field_id
    return f"field_{index:03d}"


def _requirements_from_structure(
    structure: DocxStructure,
    catalog: list[dict[str, Any]],
    form_id: str,
    manifest_cells: list[dict[str, Any]],
) -> list[AuditRequirement]:
    """Deterministic fallback from blank cells + manifest alignment."""
    manifest_by_coord: dict[tuple[int, int, int], dict[str, Any]] = {}
    for cell in manifest_cells:
        key = (int(cell["table_index"]), int(cell["row"]), int(cell["col"]))
        manifest_by_coord[key] = cell

    requirements: list[AuditRequirement] = []
    seen_coords: set[tuple[int, int, int]] = set()
    idx = 0

    for cell in structure.blank_cells:
        coord = (cell.table_index, cell.row_index, cell.column_index)
        if coord in seen_coords:
            continue
        seen_coords.add(coord)
        manifest = manifest_by_coord.get(coord)
        idx += 1
        label = (manifest or {}).get("label") or cell.label_text or cell.nearby_header or f"Table {cell.table_index} Row {cell.row_index}"
        field_id = _field_id(idx, (manifest or {}).get("field_id"))
        schema_path, map_conf = infer_schema_path(label, catalog, form_id)
        required = bool((manifest or {}).get("required", True))
        mapping_confidence = map_conf if schema_path else 0.0
        can_auto_fill = mapping_confidence >= MAPPING_CONFIDENCE_MIN
        requirements.append(
            AuditRequirement(
                id=field_id,
                field_label=label,
                field_type=_infer_field_type(label),  # type: ignore[arg-type]
                form_location=FormLocation(
                    document_type="docx",
                    table_index=cell.table_index,
                    row_index=cell.row_index,
                    column_index=cell.column_index,
                    nearby_header=cell.nearby_header,
                    cell_path=f"table[{cell.table_index}]/row[{cell.row_index}]/col[{cell.column_index}]",
                ),
                contextual_intent=f"Capture audit evidence for: {label}",
                search_directive=f"Find evidence supporting '{label}' for form {form_id}",
                required_evidence_type="text",  # type: ignore[arg-type]
                required=required,
                docupipe_schema_id=f"{form_id}_2026" if schema_path else None,
                mapped_schema_path=schema_path,
                mapping_confidence=mapping_confidence,
                can_auto_fill=can_auto_fill,
                fallback_behavior="fill_not_verified" if required else "leave_blank",  # type: ignore[arg-type]
            )
        )

    if not requirements and manifest_cells:
        for cell in manifest_cells:
            idx += 1
            label = str(cell.get("label") or cell.get("field_id"))
            schema_path, map_conf = infer_schema_path(label, catalog, form_id)
            requirements.append(
                AuditRequirement(
                    id=str(cell.get("field_id") or _field_id(idx, None)),
                    field_label=label,
                    field_type=_infer_field_type(label),  # type: ignore[arg-type]
                    form_location=FormLocation(
                        document_type="docx",
                        table_index=int(cell["table_index"]),
                        row_index=int(cell["row"]),
                        column_index=int(cell["col"]),
                        nearby_header="",
                        cell_path=f"table[{cell['table_index']}]/row[{cell['row']}]/col[{cell['col']}]",
                    ),
                    contextual_intent=f"Capture audit evidence for: {label}",
                    search_directive=f"Find evidence supporting '{label}'",
                    required_evidence_type="text",  # type: ignore[arg-type]
                    required=bool(cell.get("required", True)),
                    mapped_schema_path=schema_path,
                    mapping_confidence=map_conf,
                    can_auto_fill=map_conf >= MAPPING_CONFIDENCE_MIN,
                    fallback_behavior="fill_not_verified",  # type: ignore[arg-type]
                )
            )
    return requirements


def _validate_requirements(reqs: list[AuditRequirement], structure: DocxStructure) -> list[str]:
    errors: list[str] = []
    for req in reqs:
        loc = req.form_location
        if loc.table_index is None or loc.row_index is None or loc.column_index is None:
            errors.append(f"{req.id}: missing table coordinates")
            continue
        ti, ri, ci = loc.table_index, loc.row_index, loc.column_index
        if ti >= structure.table_count:
            errors.append(f"{req.id}: table_index {ti} out of range")
    return errors


def _summarize(fields: list[AuditRequirement]) -> MachineFieldMapSummary:
    auto = sum(1 for f in fields if f.can_auto_fill)
    low = sum(1 for f in fields if f.mapping_confidence < MAPPING_CONFIDENCE_MIN)
    fallback = sum(1 for f in fields if f.fallback_behavior != "leave_blank")
    return MachineFieldMapSummary(
        detected_field_count=len(fields),
        auto_fillable_field_count=auto,
        low_confidence_field_count=low,
        fallback_field_count=fallback,
    )


def _llm_enrich_requirements(
    structure: DocxStructure,
    catalog: list[dict[str, Any]],
    html: str,
    form_id: str,
) -> list[AuditRequirement] | None:
    schema_path = Path(resolve_project_root()) / "schemas" / "contracts" / "machineFieldMap.v1.schema.json"
    response_schema = None
    if schema_path.is_file():
        response_schema = json.loads(schema_path.read_text(encoding="utf-8"))

    prompt = f"""You are an expert compliance auditor analyzing a blank audit form.

Form ID: {form_id}
Structure summary: {json.dumps(structure.to_summary_dict())}
Available DocuPipe schema paths: {json.dumps(catalog, indent=2)[:8000]}

HTML context (semantic only — use structure summary for coordinates):
{html[:60000]}

Return machine_field_map.v1 JSON with fields array. Each field MUST include valid tableIndex, rowIndex, columnIndex for docx write locations.
Infer contextualIntent and searchDirective for each field. Map mappedSchemaPath to catalog paths when possible.
"""
    try:
        raw = generate_json(prompt, response_schema=response_schema)
    except LlmError:
        return None
    if isinstance(raw, dict) and raw.get("fields"):
        fields = [AuditRequirement.from_dict(item) for item in raw["fields"]]
        return fields
    return None


def analyze_blank_form(
    blank_form_path: Path,
    *,
    root: Path | None = None,
    form_id: str | None = None,
    activity_code: str | None = None,
    use_llm: bool = True,
) -> MachineFieldMapV1:
    """Primary analyzeDocxForm entry — Analyst Agent."""
    root = root or resolve_project_root()
    blank_form_path = Path(blank_form_path).resolve()
    stem = blank_form_path.stem.replace(" ", "_").replace("(", "").replace(")", "")
    resolved_form_id = form_id or stem.replace(".docx", "")
    if "B24" in resolved_form_id.upper():
        resolved_form_id = "B24_RL2"

    structure = extract_docx_structure(blank_form_path)
    catalog = load_available_schemas(root, (resolved_form_id,))
    manifest_cells = load_template_manifest_cells(root, resolved_form_id)

    fields: list[AuditRequirement] | None = None
    if use_llm:
        try:
            html = extract_mammoth_html(blank_form_path)
            fields = _llm_enrich_requirements(structure, catalog, html, resolved_form_id)
            if fields:
                errors = _validate_requirements(fields, structure)
                if errors:
                    retry_prompt = f"Fix these validation errors and return corrected machine_field_map.v1:\n{errors}"
                    try:
                        raw2 = generate_json(retry_prompt)
                        if isinstance(raw2, dict) and raw2.get("fields"):
                            fields = [AuditRequirement.from_dict(item) for item in raw2["fields"]]
                    except LlmError:
                        fields = None
        except (LlmError, RuntimeError):
            fields = None

    if not fields:
        fields = _requirements_from_structure(structure, catalog, resolved_form_id, manifest_cells)

    errors = _validate_requirements(fields, structure)
    if errors and not manifest_cells:
        fields = _requirements_from_structure(structure, catalog, resolved_form_id, manifest_cells)

    return MachineFieldMapV1(
        template_file=str(blank_form_path),
        generated_at=utc_now(),
        fields=fields,
        summary=_summarize(fields),
        activity_code=activity_code or resolved_form_id,
    )


def analyze_docx_form(docx_path: str | Path, available_schemas: list[dict[str, Any]] | None = None) -> MachineFieldMapV1:
    """Compatibility alias matching SPEC TypeScript signature."""
    import os

    root = resolve_project_root()
    use_llm = bool(os.getenv("GEMINI_API_KEY") or os.getenv("ANTHROPIC_API_KEY"))
    return analyze_blank_form(Path(docx_path), root=root, use_llm=use_llm)
