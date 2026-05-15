"""Gold fixture coverage for B24 OCR fallback extraction."""

from __future__ import annotations

import json
from pathlib import Path

from docx import Document

from b2_automation.inbox_pipeline import run_inbox_pipeline
from b2_automation.local_extraction import _field_suggestions


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _review(result: object) -> dict[str, object]:
    return json.loads(result.review_json_path.read_text(encoding="utf-8"))


def _docx_text(path: Path) -> str:
    doc = Document(str(path))
    parts: list[str] = []
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                if cell.text:
                    parts.append(cell.text)
    return "\n".join(parts)


def test_b24_gold_fixture_handles_staged_inbox_ocr_noise(tmp_path: Path) -> None:
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    (inbox / "b24_staged_ocr_gold.txt").write_text(
        "\n".join(
            [
                "[structured_docx_table_evidence]",
                "Estacion/ Station: Taller Mexico FTVM",
                "Tlpo de Carro/ Car Type: TANK CAR",
                "lnlclales de Carro/ Car Mark:",
                "PROBETA MUESTRA",
                "N° de Cmo /Car Number: PAWCT-824",
                "Dale Permisslon Receivad from TCO 5/20/2024",
                "Written Instructions from TCO: Confirmacion por correo electronico",
                "PITP: PITP / PC-TC-01 / A Navarre / 11/4/2021 / 0",
                "Date Approved: day where the action",
                "a): malformed OCR fragment",
                "7 TANK SPECIFICATION DOT 111A100W1",
                "8 STENCILED SPEC: DOT 111A100W1",
                "The Following Drawings Apply",
                "39 General Arrangement - D-41759 L056040A",
                "Specimen plate A51G Grado 70",
                "CERTIFICADO DE MATERIAL # AD6S",
                "Insert size 12 in X 12 In",
                "attachment_material: A36",
            ]
        ),
        encoding="utf-8",
    )

    result = run_inbox_pipeline(root=_repo_root(), inbox=inbox, out_dir=tmp_path / "run", review_forms=("B24_RL2",))

    review = _review(result)
    selected = {row["field_id"]: row["selected_value"] for row in review["form_packets"]["B24_RL2"]["field_decisions"]}
    assert selected["facility_name"] == "Taller Mexico FTVM"
    assert selected["tco_permission_date"] == "5/20/2024"
    assert selected["tco.permission_date"] == "5/20/2024"
    assert selected["car_number"] == "PAWCT-824"
    assert selected["car_mark"] == "PROBETA MUESTRA PAWCT-824"
    assert selected["tank_design_spec"] == "DOT111A100W1"
    assert selected["car.design_spec"] == "DOT111A100W1"
    assert selected["aar_form_4_2_number"] == "L056040A"
    assert selected["four_two_drawing_number"] == "D-41759"

    filled_text = _docx_text(result.filled_docx_path)
    for marker in (
        "REVIEW_REQUIRED: facility_name",
        "REVIEW_REQUIRED: tco_permission_date",
        "REVIEW_REQUIRED: tank_design_spec",
    ):
        assert marker not in filled_text
    for junk in ("day where the action", "a):", "malformed OCR fragment"):
        assert junk.lower() not in filled_text.lower()


def test_b24_gold_fixture_accepts_short_reporting_marks_like_dotx() -> None:
    item = {
        "source_file": "b24_ocr.txt",
        "chunk_id": 1,
        "score": 5,
        "text": "Car Mark: DOTX\nDate Permission Received: 5/20/2024",
        "full_text": "Car Mark: DOTX\nDate Permission Received: 5/20/2024",
        "chunk_excerpt": "Car Mark: DOTX",
    }

    suggestions = _field_suggestions([item], "B24_RL2")
    values = {(row["field_id"], row["candidate_value"]) for row in suggestions}
    assert ("car_mark", "DOTX") in values
    assert ("car.mark", "DOTX") in values
    assert ("tco_permission_date", "5/20/2024") in values
