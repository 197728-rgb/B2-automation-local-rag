from b2_automation.local_extraction import _field_suggestions


def _item(text: str) -> dict[str, object]:
    return {
        "text": text,
        "full_text": text,
        "source_file": "b24_ocr_fixture.txt",
        "chunk_id": "c1",
        "score": 1,
    }


def test_b24_extraction_handles_split_labels_permission_wording_and_junk() -> None:
    text = "\n".join(
        [
            "Car Mark",
            "PAWCT",
            "Car Number: PAWCT-824",
            "TANK SPECIFICATION DOT 111A100W1",
            "Permission Received from TCO",
            "TCO Permission Date: 5/20/2024",
            "Date Approved: day where the action",
            "a)",
        ]
    )

    suggestions = _field_suggestions([_item(text)], form="B24_RL2")
    by_field = {row["field_id"]: row["candidate_value"] for row in suggestions}

    assert by_field["car_mark"].startswith("PAWCT")
    assert by_field["car_number"] == "PAWCT-824"
    assert by_field["tco_permission_date"] == "5/20/2024"
    assert all("day where the action" not in str(v).lower() for v in by_field.values())
    assert all(str(v).strip().lower() != "a)" for v in by_field.values())
