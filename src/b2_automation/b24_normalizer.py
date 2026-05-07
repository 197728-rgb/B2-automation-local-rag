"""Map realistic DocuPipe-style B-2 extraction JSON to B24_RL1 manifest field_ids."""

from __future__ import annotations

from typing import Any

# DocuPipe / extraction service keys -> manifest field_id (TABLE 0 cell map)
_FIELD_KEY_TO_MANIFEST: dict[str, str] = {
    "TankCarOwnerName": "tco_name",
    "tank_car_owner": "tco_name",
    "PermissionInstructionDate": "tco_permission_date",
    "tco_permission_received": "tco_permission_date",
    "TCOWrittenInstructions": "tco_written_instructions",
    "tco_written_instructions": "tco_written_instructions",
    "PITPDocumentTitle": "pitp_document_name",
    "pitp_title": "pitp_document_name",
    "PITPIdentifier": "pitp_id",
    "pitp_id": "pitp_id",
    "PITPApprovedBy": "pitp_approved_by",
    "pitp_approved_by": "pitp_approved_by",
    "PITPApprovalDate": "pitp_date_approved",
    "pitp_approval_date": "pitp_date_approved",
    "PITPRevision": "pitp_rev",
    "pitp_rev": "pitp_rev",
    "CarMarking": "car_mark",
    "car_mark_number": "car_mark",
    "TankDesignSpec": "tank_design_spec",
    "tank_design_spec": "tank_design_spec",
    "CarType": "car_type",
    "car_type": "car_type",
    "AARForm42Number": "aar_form_4_2_number",
    "aar_form_42": "aar_form_4_2_number",
    "DrawingNumber42": "four_two_drawing_number",
    "four_two_drawing_number": "four_two_drawing_number",
    "DrawingRevision42": "four_two_drawing_revision",
    "four_two_drawing_revision": "four_two_drawing_revision",
    "TestPlateTankMaterial": "test_plate_tank_material",
    "test_plate_tank_material": "test_plate_tank_material",
    "TestPlateTankMTR": "test_plate_tank_mtr",
    "test_plate_mtr_number": "test_plate_tank_mtr",
    "AttachmentMaterial": "attachment_material",
    "attachment_material_description": "attachment_material",
}

# Distinct manifest field_ids reachable from at least one DocuPipe field_key / normalized_key.
DOCUPIPE_MAPPED_B24_RL1_FIELD_IDS: frozenset[str] = frozenset(_FIELD_KEY_TO_MANIFEST.values())

# Manifest field_ids that are never populated from a single field_extraction row.
# Each entry must stay in sync with schemas/templates/B24_RL1.json (see template map coverage tests).
B24_RL1_MANUAL_OR_SYNTHETIC_FIELDS: dict[str, str] = {
    "evidence_notes": (
        "Synthesized in normalize_docupipe_payload_for_b24_rl1 from all mapped "
        "field_extractions (confidence + provenance), not one DocuPipe field_key."
    ),
}


def _format_provenance(prov: list[dict[str, Any]]) -> str:
    if not prov:
        return "source: (none)"
    parts: list[str] = []
    for p in prov:
        pg = p.get("page_index")
        reg = p.get("region", "")
        if pg is not None:
            parts.append(f"page_index={pg}" + (f", region={reg}" if reg else ""))
    return "source: " + "; ".join(parts) if parts else "source: (none)"


def normalize_docupipe_payload_for_b24_rl1(raw: dict[str, Any]) -> dict[str, str]:
    """
    Read `result.field_extractions[]` from a DocuPipe-like payload and return
    the flat string map expected by `fill_b24_rl1_partial` (manifest field_ids).
    """
    result = raw.get("result") or {}
    rows = result.get("field_extractions") or []
    if not isinstance(rows, list):
        rows = []

    out: dict[str, str] = {}
    evidence_lines: list[str] = []

    for row in rows:
        if not isinstance(row, dict):
            continue
        fk = row.get("field_key") or ""
        nk = row.get("normalized_key") or ""
        manifest_id = _FIELD_KEY_TO_MANIFEST.get(fk) or _FIELD_KEY_TO_MANIFEST.get(nk)
        if not manifest_id:
            continue
        val = str(row.get("value", "")).strip()
        out[manifest_id] = val
        conf = row.get("confidence")
        prov = row.get("provenance") or []
        if not isinstance(prov, list):
            prov = []
        conf_s = f"{float(conf):.2f}" if conf is not None else "n/a"
        evidence_lines.append(
            f"{fk}: value={val!r}; confidence={conf_s}; {_format_provenance(prov)}"
        )

    out["evidence_notes"] = (
        "DocuPipe extraction audit trail (field_key, confidence, source).\n"
        + "\n".join(evidence_lines)
    )
    return out
