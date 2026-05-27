"""CLI form-selection validation tests."""
from __future__ import annotations

import sys
from pathlib import Path

from click.testing import CliRunner

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import b2_sentinel.cli as cli_module
from b2_sentinel.layer1_form_brain.write_authority import validate_supported_forms


def test_cli_rejects_unsupported_form_before_run(monkeypatch, tmp_path: Path) -> None:
    def fail_if_called(*args, **kwargs):  # noqa: ANN002, ANN003
        raise AssertionError("audit run should not start for unsupported forms")

    monkeypatch.setattr(cli_module, "run_form", fail_if_called)
    monkeypatch.setattr(cli_module, "reset_outbox", fail_if_called)

    result = CliRunner().invoke(
        cli_module.cli,
        [
            "run",
            "--form",
            "B19",
            "--inbox",
            str(tmp_path / "inbox"),
            "--output",
            str(tmp_path / "outputs"),
        ],
    )

    assert result.exit_code == 2, result.output
    assert "Unsupported form id(s): B19." in result.output
    assert "nearest/latest/similar fallbacks are disabled" in result.output
    assert not (tmp_path / "outputs").exists()


def test_cli_rejects_short_codes_with_exact_form_suggestions(monkeypatch, tmp_path: Path) -> None:
    def fail_if_called(*args, **kwargs):  # noqa: ANN002, ANN003
        raise AssertionError("audit run should not start for short form ids")

    monkeypatch.setattr(cli_module, "run_form", fail_if_called)
    monkeypatch.setattr(cli_module, "reset_outbox", fail_if_called)

    result = CliRunner().invoke(
        cli_module.cli,
        [
            "run",
            "--form",
            "C5H",
            "--form",
            "C6I",
            "--inbox",
            str(tmp_path / "inbox"),
            "--output",
            str(tmp_path / "outputs"),
        ],
    )

    assert result.exit_code == 2, result.output
    assert "C5H -> C5H_Heater_Systems_Test_Fixture" in result.output
    assert "C6I -> C6i_Installation_of_Service_Equipment_512026" in result.output
    assert not (tmp_path / "outputs").exists()


def test_exact_c5h_and_c6i_form_ids_are_supported() -> None:
    selected = validate_supported_forms(
        [
            "C5H_Heater_Systems_Test_Fixture",
            "C6i_Installation_of_Service_Equipment_512026",
        ]
    )

    assert selected == [
        "C5H_Heater_Systems_Test_Fixture",
        "C6i_Installation_of_Service_Equipment_512026",
    ]
