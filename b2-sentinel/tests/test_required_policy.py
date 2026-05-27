"""Regression tests for required-cell policy hardening."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from b2_sentinel.layer1_form_brain.obligation_graph import build_obligation_graph


TARGETED_FORMS = (
    "B85",
    "C7_Removal_CoatingsLinings",
    "C7_C8_Combination_Coatings",
    "C7_C8_Combination_Linings",
    "C7_C8__C10_Combination_Coatings",
    "C7_C8__C10_Combination_Linings",
    "C7_C10_Combination_Coatings",
    "C7_C10_Combination_Linings",
    "C4aC_Closures",
    "C4aF_Fittings",
    "C4aI_Instruments",
    "C4aS_Safety_Relief_Devices",
    "C4aV_Valves",
    "C4mC_Closures",
    "C4mF_Fittings",
    "C4mH_Heater_Systems_Test_Fixture",
    "C4mI_Instruments",
    "C4mS_Safety_Relief_Devices",
    "C4mV_Valves",
    "C5H_Heater_Systems_Test_Fixture",
    "C6i_Installation_of_Service_Equipment_512026",
)


def test_targeted_forms_have_nonzero_required_obligations() -> None:
    for form_id in TARGETED_FORMS:
        graph = build_obligation_graph(form_id)
        assert graph.required_total > 0, form_id
        assert graph.required_field_ids(), form_id


def test_required_policy_promotes_expected_family_fields() -> None:
    expectations = {
        "B85": {"tank_car_tank_component", "pitp_document_name", "record_form_id"},
        "C7_Removal_CoatingsLinings": {
            "tank_car_or_lining_coating_owner_tco_l_co_name",
            "car_mark_and_number",
            "record_form_id",
        },
        "C4aC_Closures": {
            "engineering_drawing_number_traceable_to_pitp",
            "pitp_document_name",
            "record_form_id",
        },
        "C4mC_Closures": {
            "engineering_drawing_number_traceable_to_pitp",
            "pitp_document_name",
            "welder_operator_id",
        },
        "C5H_Heater_Systems_Test_Fixture": {
            "tank_car_or_service_equipment_owner_tco_seo_name",
            "service_equipment_description",
            "pitp_document_name",
            "welder_operator_id",
            "record_form_id",
        },
        "C6i_Installation_of_Service_Equipment_512026": {
            "car_initial_and_car_mark",
            "description_of_service_equipment",
            "pitp_document_name",
            "ndt_technician_id",
            "record_form_id",
        },
    }
    for form_id, field_ids in expectations.items():
        graph = build_obligation_graph(form_id)
        required = set(graph.required_field_ids())
        assert field_ids <= required


def test_generated_note_cells_remain_optional() -> None:
    for form_id in (
        "B85",
        "C7_Removal_CoatingsLinings",
        "C4aC_Closures",
        "C4mC_Closures",
        "C5H_Heater_Systems_Test_Fixture",
        "C6i_Installation_of_Service_Equipment_512026",
    ):
        graph = build_obligation_graph(form_id)
        for fid in graph.fields:
            if "additional_auditor_objective_evidence_comments_notes" in fid:
                assert fid not in graph.required_field_ids()


def test_generated_identifier_cells_remain_optional_for_c5h_and_c6i() -> None:
    for form_id in (
        "C5H_Heater_Systems_Test_Fixture",
        "C6i_Installation_of_Service_Equipment_512026",
    ):
        graph = build_obligation_graph(form_id)
        required = set(graph.required_field_ids())
        assert "id" not in required
        assert "id_2" not in required


def test_generated_duplicate_rows_are_not_promoted_without_semantic_context() -> None:
    graph = build_obligation_graph("C7_C8__C10_Combination_Coatings")
    required = set(graph.required_field_ids())

    assert "record_form_id" in required
    assert "record_form_id_2" not in required
    assert "procedure_id" in required
    assert "procedure_id_2" not in required
