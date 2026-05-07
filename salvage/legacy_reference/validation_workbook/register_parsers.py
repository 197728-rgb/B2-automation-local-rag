"""
Stage-2 column parsers for register rows (regex / line heuristics).

Fills human-review columns on PROCEDURES / FORMS / MTE / EMPLOYEE / NDT sheets where text allows.
"""

from __future__ import annotations

import re
from typing import Any

_DATE_TOKEN = re.compile(
    r"(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|[A-Za-z]{3,9}\s+\d{1,2},?\s+\d{4}|\d{4}[/-]\d{1,2}[/-]\d{1,2})"
)


def _first_date(text: str) -> str:
    m = _DATE_TOKEN.search(text or "")
    return m.group(0).strip() if m else ""


def _clean_label_value(s: str, max_len: int = 240) -> str:
    s = re.sub(r"\s+", " ", (s or "").strip())
    return s[:max_len] if s else ""


def parse_document_form_meta(text: str) -> dict[str, str]:
    """Approver, approval date, revision for procedures/forms rows."""
    t = text or ""
    out: dict[str, str] = {"approver": "", "date_approved": "", "rev": ""}

    for pat in (
        r"approved\s+by\s*[:\s]+([^\n\r]{2,120})",
        r"management\s+representative\s*\(?\s*print\s+name\s*\)?\s*[:\s]+([^\n\r]{2,120})",
        r"signature\s*[:\s]+([A-Za-z][^\n\r]{2,80})",
    ):
        m = re.search(pat, t, re.I)
        if m and not out["approver"]:
            out["approver"] = _clean_label_value(m.group(1))
            break

    for pat in (
        r"approval\s+date\s*[:\s]+(\S[^\n\r]{4,40})",
        r"date\s+approved\s*[:\s]+(\S[^\n\r]{4,40})",
        r"approved\s*[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
    ):
        m = re.search(pat, t, re.I)
        if m and not out["date_approved"]:
            out["date_approved"] = _clean_label_value(m.group(1), 40)
            break
    if not out["date_approved"]:
        low = t.lower()
        for key in ("approval", "approved", "date approved"):
            idx = low.find(key)
            if idx >= 0:
                chunk = t[idx : idx + 100]
                d = _first_date(chunk)
                if d:
                    out["date_approved"] = d
                    break

    for pat in (
        r"(?:^|\s)(?:revision|rev\.?)\s*[:\s#]+([A-Za-z0-9./\-]{1,32})",
        r"rev\s*[:\s]+([A-Za-z0-9./\-]+)",
    ):
        m = re.search(pat, t, re.I)
        if m and not out["rev"]:
            out["rev"] = m.group(1).strip()
            break

    return out


def parse_measure_and_test_equipment_detail(text: str) -> dict[str, str]:
    """ID, function, equipment description line."""
    t = text or ""
    out: dict[str, str] = {
        "measure_and_test_equipment": "",
        "id": "",
        "function_performed": "",
    }

    for pat in (
        r"(?:equipment|gauge|instrument)\s+id\s*[:\s#]+([A-Za-z0-9\-]{2,40})",
        r"serial\s*(?:no\.?|number)\s*[:\s]+([A-Za-z0-9\-]{3,40})",
        r"\bid\s*[:\s]+([A-Za-z0-9\-]{2,30})\b",
    ):
        m = re.search(pat, t, re.I)
        if m and not out["id"]:
            out["id"] = m.group(1).strip()
            break

    tm = re.search(
        r"(?:equipment\s+type|measure\s+and\s+test|type)\s*[:\s]+([A-Za-z0-9\s\-./]{3,100})",
        t,
        re.I,
    )
    if tm:
        out["measure_and_test_equipment"] = _clean_label_value(tm.group(1), 100)

    fm = re.search(r"function\s+performed\s*[:\s]+([^\n\r]{2,120})", t, re.I)
    if fm:
        out["function_performed"] = _clean_label_value(fm.group(1))

    return out


def parse_employee_function_training_detail(text: str) -> dict[str, str]:
    t = text or ""
    out: dict[str, str] = {
        "employee_name": "",
        "function_performed": "",
        "date_received": "",
        "function_training_date": "",
    }

    nm = re.search(
        r"(?:employee|inspector|personnel|name)\s*[:\s]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,4})",
        t,
    )
    if nm:
        out["employee_name"] = nm.group(1).strip()

    fm = re.search(r"function\s+performed\s*[:\s]+([^\n\r]{2,160})", t, re.I)
    if fm:
        out["function_performed"] = _clean_label_value(fm.group(1))

    dm = re.search(
        r"date\s+received\s+(?:function\s+)?(?:specific\s+)?training\s*[:\s]+(\S[^\n]{4,40})",
        t,
        re.I,
    )
    if dm:
        out["date_received"] = _clean_label_value(dm.group(1), 40)

    tm = re.search(r"(?:training|qualification|function)\s+date\s*[:\s]+(\S[^\n]{4,40})", t, re.I)
    if tm:
        out["function_training_date"] = _clean_label_value(tm.group(1), 40)

    return out


def parse_ndt_technician_qualifications(text: str) -> dict[str, str]:
    t = text or ""
    out: dict[str, str] = {
        "ndt_technician_id": "",
        "level_qualified": "",
        "ndt_methods": "",
        "date_qualified": "",
        "qualification_expiration_date": "",
        "date_of_visual_acuity_exam": "",
        "due_date_visual_acuity_exam": "",
    }

    emp = re.search(r"\b(EMP[- ]?\d+)\b", t, re.I)
    if emp:
        out["ndt_technician_id"] = emp.group(1).replace(" ", "-").upper()

    if not out["ndt_technician_id"]:
        nm = re.search(
            r"(?:ndt\s+technician|technician)\s+id\s*[:\s]+([A-Za-z0-9\-]{2,32})",
            t,
            re.I,
        )
        if nm:
            out["ndt_technician_id"] = nm.group(1).strip()

    rom = re.search(r"\b(III|II|I)\b", t)
    if rom:
        out["level_qualified"] = rom.group(1)

    methods = re.search(
        r"ndt\s+method(?:s)?\s*[:\s]+([A-Za-z0-9\s,;/]{2,80})",
        t,
        re.I,
    )
    if methods:
        out["ndt_methods"] = _clean_label_value(methods.group(1), 80)
    else:
        m_compact = re.findall(r"\b(PT|MT|UT|VT|ET|RT|LT)\b", t, re.I)
        if m_compact:
            out["ndt_methods"] = "; ".join(sorted({x.upper() for x in m_compact}))

    for label, key in (
        (r"date\s+qualified\s*[:\s]+(\S[^\n]{4,40})", "date_qualified"),
        (r"qualification\s+expiration\s*[:\s]+(\S[^\n]{4,40})", "qualification_expiration_date"),
        (r"visual\s+acuity\s+date\s*[:\s]+(\S[^\n]{4,40})", "date_of_visual_acuity_exam"),
    ):
        m = re.search(label, t, re.I)
        if m and not out[key]:
            out[key] = _clean_label_value(m.group(1), 40)
    for label in (
        r"due\s+date\s+visual\s+acuity\s*[:\s]+(\S[^\n]{4,40})",
        r"visual\s+acuity\s+(?:expiration|due)\s*[:\s]+(\S[^\n]{4,40})",
    ):
        m = re.search(label, t, re.I)
        if m and not out["due_date_visual_acuity_exam"]:
            out["due_date_visual_acuity_exam"] = _clean_label_value(m.group(1), 40)

    return out


def merge_nonempty(base: dict[str, Any], extra: dict[str, str]) -> None:
    for k, v in extra.items():
        if k in base and (base[k] == "" or base[k] is None) and v:
            base[k] = v
