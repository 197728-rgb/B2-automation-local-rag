"""Regression tests for strict TCO permission date extraction (no unrelated dates)."""

from __future__ import annotations

from b2_automation.local_extraction import _field_suggestions


def _values_for(item: dict, form: str, field: str) -> set[str]:
    return {row["candidate_value"] for row in _field_suggestions([item], form) if row["field_id"] == field}


def test_tco_permission_date_positive_noisy_ocr() -> None:
    """Labeled permission-received line wins over unrelated dates in noisy OCR."""
    text = """
    OCR noise date 01/01/1999 junk
    Inspection Date: 03/04/2018
    Site calibration due 12-15-2022
    Dale Permisslon Receivad from TCO 5/20/2024
    Another random 11/11/2030 timestamp
    """
    item = {
        "source_file": "packet.txt",
        "chunk_id": 1,
        "score": 5,
        "text": text,
        "full_text": text,
        "chunk_excerpt": text[:200],
    }
    vals = _values_for(item, "B24_RL2", "tco_permission_date")
    assert "5/20/2024" in vals
    assert "01/01/1999" not in vals
    assert "03/04/2018" not in vals
    assert "12-15-2022" not in vals


def test_tco_permission_date_negative_unrelated_dates_only() -> None:
    """Generic inspection / visit dates must not populate TCO permission date."""
    text = """
    Facility: Midwest Shop
    Estacion/ Station: Taller Mexico FTVM
    Inspection Date: 01/15/2020
    Site Visit Date: 03/01/2021
    Audit closing 2022-06-30
    Tank Car Owner (TCO) Name: EXAMPLE RAIL
    """
    item = {
        "source_file": "packet.txt",
        "chunk_id": 1,
        "score": 5,
        "text": text,
        "full_text": text,
        "chunk_excerpt": text[:200],
    }
    vals = _values_for(item, "B24_RL2", "tco_permission_date")
    assert vals == set()


def test_station_facility_not_used_for_tco_name() -> None:
    """Station line fills facility only; TCO name must come from TCO label."""
    text = """
    Estacion/ Station: Taller Mexico FTVM
    Tank Car Owner (TCO) Name: CIT GROUP
    """
    item = {
        "source_file": "packet.txt",
        "chunk_id": 1,
        "score": 5,
        "text": text,
        "full_text": text,
        "chunk_excerpt": text[:200],
    }
    suggestions = _field_suggestions([item], "B81")
    by_field = {row["field_id"]: row["candidate_value"] for row in suggestions}
    assert by_field.get("tco.name") == "CIT GROUP"
    assert by_field.get("facility_name") == "Taller Mexico FTVM"


def test_certificate_applicant_does_not_override_labeled_tco_name() -> None:
    """Trinity-style certificate applicant must not win when Tank Car Owner label is present."""
    text = """
    APPLICATION FOR APPROVAL AND CERTIFICATE OF CONSTRUCTION
    TRI NITY INDUSTRIES, INC filler noise
    Tank Car Owner (TCO) Name: CIT
    Date Permission Received from TCO: 5/20/2024
    """
    item = {
        "source_file": "packet.txt",
        "chunk_id": 1,
        "score": 5,
        "text": text,
        "full_text": text,
        "chunk_excerpt": text[:200],
    }
    names = _values_for(item, "B24_RL2", "tco.name")
    assert "CIT" in names
    assert not any("TRINITY" in (n or "").upper() for n in names)


def test_certificate_committee_date_does_not_override_permission_line() -> None:
    """Certificate committee approval date must not populate TCO permission when label cues exist."""
    text = """
    APPLICATION FOR APPROVAL AND CERTIFICATE OF CONSTRUCTION
    APPROVAL - AAR Tank Car Committee January 18, 2013
    Dale Permisslon Receivad from TCO 5/20/2024
    """
    item = {
        "source_file": "packet.txt",
        "chunk_id": 1,
        "score": 5,
        "text": text,
        "full_text": text,
        "chunk_excerpt": text[:200],
    }
    dates = _values_for(item, "B24_RL2", "tco_permission_date")
    assert "5/20/2024" in dates
    assert "2013-01-18" not in dates


def test_certificate_applicant_alone_does_not_fill_tco_name() -> None:
    """AAR certificate applicant is not evidence for Tank Car Owner."""
    text = """
    APPLICATION FOR APPROVAL AND CERTIFICATE OF CONSTRUCTION
    TRI NITY INDUSTRIES, INC filler noise
    APPROVAL - AAR Tank Car Committee January 18, 2013 approved.
    """
    item = {
        "source_file": "packet.txt",
        "chunk_id": 1,
        "score": 5,
        "text": text,
        "full_text": text,
        "chunk_excerpt": text[:200],
    }
    names = _values_for(item, "B24_RL2", "tco.name")
    dates = _values_for(item, "B24_RL2", "tco_permission_date")
    assert not any("TRINITY" in (n or "").upper() for n in names)
    assert "2013-01-18" not in dates


def test_bare_control_plan_id_does_not_become_pitp_document_name() -> None:
    """A bare PC-TC id is the PITP id; the document name remains PITP."""
    text = "Plan de control PC-TC-01 Alondra Navarro c-4--nov---21 Primera edicion"
    item = {
        "source_file": "packet.txt",
        "chunk_id": 1,
        "score": 5,
        "text": text,
        "full_text": text,
        "chunk_excerpt": text[:200],
    }
    suggestions = _field_suggestions([item], "B24_RL2")
    by_field = {row["field_id"]: row["candidate_value"] for row in suggestions}
    assert by_field["pitp_id"] == "PC-TC-01"
    assert by_field["pitp_document_name"] == "PITP"


def test_b90_car_identity_prefers_b90_code_from_multi_code_inventory() -> None:
    """A generic inventory list must not make B90 choose the first B24 specimen code."""
    text = """
    GQAP preservation evidence
    Identificacion como sigue: codigos asignados: PAWCT-B24, PAWCT-B90, PAWCT-RLJ
    """
    item = {
        "source_file": "GQAP-2.16_PRESERVACION.txt",
        "chunk_id": 1,
        "score": 9,
        "text": text,
        "full_text": text,
        "chunk_excerpt": text[:200],
    }
    vals = _values_for(item, "B90", "car.mark")
    assert "PAWCT-B90" in vals
    assert "PAWCT-B24" not in vals
