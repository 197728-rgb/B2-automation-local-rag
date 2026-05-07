"""
Stage-1 keyword / regex row harvesters for PROCEDURES, FORMS, MTE, EMPLOYEE, NDT sheets.
Conservative passes over block text — not full NLP.
"""

from __future__ import annotations

import re
from typing import Any

from .register_parsers import (
    merge_nonempty,
    parse_document_form_meta,
    parse_employee_function_training_detail,
    parse_measure_and_test_equipment_detail,
    parse_ndt_technician_qualifications,
)


def harvest_procedures(blocks: list[dict], source_path: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    doc_re = re.compile(
        r"(controlled|document\s*no\.?|revision|rev\.|procedure|standard|specification)",
        re.I,
    )
    for b in blocks:
        text = b.get("text", "") or ""
        if not text or not doc_re.search(text):
            continue
        m = re.search(r"(document\s*no\.?|doc\.?\s*no\.?|procedure)\s*[:\s#]*([A-Za-z0-9./\-]+)", text, re.I)
        doc_num = m.group(2) if m else ""
        rev_m = re.search(r"(?:revision|rev\.?)\s*[:\s]*([A-Za-z0-9./\-]+)", text, re.I)
        revision = rev_m.group(1) if rev_m else ""
        row = {
            "procedure_name": text[:120],
            "procedure_id": doc_num,
            "approver": "",
            "date_approved": "",
            "rev": revision,
        }
        merge_nonempty(row, parse_document_form_meta(text))
        rows.append(row)
    return rows[:200]


def harvest_forms(blocks: list[dict], source_path: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    form_re = re.compile(r"\b(form|m-1002|aar\s*form|exhibit\s*b-2|4-2)\b", re.I)
    for b in blocks:
        text = b.get("text", "") or ""
        if not text or not form_re.search(text):
            continue
        fn = re.search(r"(?:form|aar)\s*(?:no\.?|number)?\s*[:\s#]*([A-Za-z0-9./\-]+)", text, re.I)
        form_num = fn.group(1) if fn else ""
        row = {
            "form_name": text[:120],
            "form_id": form_num,
            "approver": "",
            "date_approved": "",
            "rev": "",
        }
        merge_nonempty(row, parse_document_form_meta(text))
        rows.append(row)
    return rows[:200]


def harvest_measure_and_test_equipment(blocks: list[dict], source_path: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    keys = re.compile(
        r"\b(calibration|gauge|equipment|serial|model|transducer|welding\s+machine)\b",
        re.I,
    )
    for b in blocks:
        text = b.get("text", "") or ""
        if not text or not keys.search(text):
            continue
        cal_m = re.search(r"calibration\s+date\s*[:\s]+(\S+)", text, re.I)
        due_m = re.search(r"calibration\s+due\s*[:\s]+(\S+)", text, re.I)
        row = {
            "measure_and_test_equipment": text[:100],
            "id": "",
            "function_performed": "",
            "calibration_date": cal_m.group(1) if cal_m else "",
            "calibration_due": due_m.group(1) if due_m else "",
        }
        merge_nonempty(row, parse_measure_and_test_equipment_detail(text))
        if not row["measure_and_test_equipment"] and row.get("id"):
            row["measure_and_test_equipment"] = text[:100]
    return rows[:200]


def harvest_employee_function_training(blocks: list[dict], source_path: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    keys = re.compile(r"\b(function\s+performed|personnel|training|qualified|inspector)\b", re.I)
    for b in blocks:
        text = b.get("text", "") or ""
        if not text or not keys.search(text):
            continue
        row = {
            "employee_name": "",
            "function_performed": "",
            "date_received": "",
            "function_training_date": "",
        }
        merge_nonempty(row, parse_employee_function_training_detail(text))
        rows.append(row)
    return rows[:200]


def harvest_ndt_technician_qualifications(blocks: list[dict], source_path: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    keys = re.compile(r"\b(certification|visual\s+acuity|ndt\s+level|qualified|ndt\s+method)\b", re.I)
    for b in blocks:
        text = b.get("text", "") or ""
        if not text or not keys.search(text):
            continue
        row = {
            "ndt_technician_id": "",
            "level_qualified": "",
            "ndt_methods": "",
            "date_qualified": "",
            "qualification_expiration_date": "",
            "date_of_visual_acuity_exam": "",
            "due_date_visual_acuity_exam": "",
        }
        merge_nonempty(row, parse_ndt_technician_qualifications(text))
        rows.append(row)
    return rows[:200]


# Backward-compatible aliases (import sites)
def harvest_document_register(blocks: list[dict], source_path: str) -> list[dict[str, Any]]:
    return harvest_procedures(blocks, source_path)


def harvest_form_register(blocks: list[dict], source_path: str) -> list[dict[str, Any]]:
    return harvest_forms(blocks, source_path)


def harvest_equipment_register(blocks: list[dict], source_path: str) -> list[dict[str, Any]]:
    return harvest_measure_and_test_equipment(blocks, source_path)


def harvest_employee_functions(blocks: list[dict], source_path: str) -> list[dict[str, Any]]:
    return harvest_employee_function_training(blocks, source_path)


def harvest_employee_certifications(blocks: list[dict], source_path: str) -> list[dict[str, Any]]:
    return harvest_ndt_technician_qualifications(blocks, source_path)
