"""
B-2 validation workbook: section codes for preview and sheet categories for B2_FIELD_MAP.
"""

from __future__ import annotations

# Exhibit-style section hints for B2_PREVIEW (extend per template as needed).
B2_SECTION_CODE: dict[str, str] = {
    "aar_form_no": "B89",
    "owner_name": "B1",
    "car_mark": "B2",
    "tank_spec": "B3",
    "procedure_id": "PROCEDURES",
    "record_form_id": "FORMS",
    "equipment_type": "MTE",
    "equipment_id": "MTE",
    "calibration_date": "MTE",
    "calibration_due": "MTE",
    "ndt_technician_id": "NDT",
    "date_qualified": "NDT",
}


def sheet_category_for_field(field: str) -> str:
    procedures = {
        "procedure_id",
        "pitp_doc_name",
        "pitp_id",
    }
    forms = {"aar_form_no", "record_form_id"}
    mte = {"equipment_type", "equipment_id", "calibration_date", "calibration_due"}
    emp = {"personnel_id", "function_performed", "training_date"}
    ndt = {
        "ndt_technician_id",
        "ndt_level",
        "ndt_method",
        "date_qualified",
        "qualification_expiration_date",
        "visual_acuity_date",
        "visual_acuity_due",
    }
    if field in procedures:
        return "PROCEDURES"
    if field in forms:
        return "FORMS"
    if field in mte:
        return "MEASURE_AND_TEST_EQUIPMENT"
    if field in emp:
        return "EMPLOYEE_FUNCTION_TRAINING"
    if field in ndt:
        return "NDT_TECHNICIAN_QUALIFICATIONS"
    return "B-2 field"
