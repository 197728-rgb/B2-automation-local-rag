"""canonical_evidence.json and field_traceability.json outputs; retrieval vs write authority."""

from __future__ import annotations

import json
from pathlib import Path
import pytest

from b2_automation.inbox_pipeline import run_inbox_pipeline
from b2_automation.local_semantic_retrieval import retrieve_chunks_for_form


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_canonical_and_traceability_exist_after_local_run(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = _repo_root()
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    (inbox / "evidence.txt").write_text(
        "Cover Page Facility: Acme Co\nB24 RL2 objective evidence Date: 2026-05-07\n"
        "B81 Car: XX 99999\nB89 insulation plate\nB90 Auditor: Pat\n",
        encoding="utf-8",
    )

    def _block_docupipe(_pdf: Path) -> None:
        raise AssertionError("no docupipe")

    monkeypatch.setattr("b2_automation.inbox_pipeline.process_pdf", _block_docupipe)

    run_inbox_pipeline(root=root, inbox=inbox, out_dir=tmp_path / "run")

    canonical = tmp_path / "run" / "canonical_evidence.json"
    trace = tmp_path / "run" / "field_traceability.json"
    assert canonical.is_file()
    assert trace.is_file()
    manifest = json.loads((tmp_path / "run" / "run_manifest.json").read_text(encoding="utf-8"))
    out_paths = {Path(p).name for p in manifest.get("outputs", [])}
    assert "canonical_evidence.json" in out_paths
    assert "field_traceability.json" in out_paths

    ce = json.loads(canonical.read_text(encoding="utf-8"))
    assert ce["schema"] == "canonical_evidence.v1"
    assert len(ce["fields"]) > 0

    tr = json.loads(trace.read_text(encoding="utf-8"))
    assert tr["schema"] == "field_traceability.v1"
    assert tr["retrieval_authorizes_writes"] is False
    assert len(tr["entries"]) >= 1


def test_traceability_has_approval_map_fields(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = _repo_root()
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    (inbox / "evidence.txt").write_text(
        "Cover Page Facility: Midwest\nB24 RL2 evidence Date: 2026-01-01\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "b2_automation.inbox_pipeline.process_pdf",
        lambda _pdf: (_ for _ in ()).throw(AssertionError("no docupipe")),
    )
    run_inbox_pipeline(root=root, inbox=inbox, out_dir=tmp_path / "run")

    tr = json.loads((tmp_path / "run" / "field_traceability.json").read_text(encoding="utf-8"))
    for row in tr["entries"]:
        assert "approval_map_target" in row
        assert "authorized_for_write" in row
        assert "filled" in row
        if row.get("suggested_value") or row.get("decision_state") == "FILL":
            assert isinstance(row["authorized_for_write"], bool)


def test_semantic_retrieval_mock_sklearn(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from b2_automation.local_extraction import LocalEvidenceDocument, chunk_text

    root = tmp_path
    doc = LocalEvidenceDocument(
        source_path=root / "a.txt",
        source_file="a.txt",
        sha256="x",
        extraction_method="local_text",
        text="B24 RL2 objective evidence regarding tank repair level 2 and facility scope.",
        metadata={},
    )
    chunks = chunk_text(doc.text)

    def _fake_sklearn(query: str, corpus: list[str]):
        if not corpus:
            return None
        return [max(0.05, float(i + 1) / max(len(corpus), 1)) for i in range(len(corpus))]

    monkeypatch.setattr("b2_automation.local_semantic_retrieval._sklearn_tfidf_rank", _fake_sklearn)
    rows, method = retrieve_chunks_for_form("B24_RL2", [doc], {"a.txt": chunks})
    assert method == "sklearn_tfidf"
    assert rows
    assert rows[0].get("semantic_score") is not None
    assert rows[0].get("chunk_hash")


def test_fallback_keyword_when_semantic_empty(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from b2_automation.local_extraction import LocalEvidenceDocument, chunk_text

    doc = LocalEvidenceDocument(
        source_path=tmp_path / "z.txt",
        source_file="z.txt",
        sha256="z",
        extraction_method="local_text",
        text="xxxxxxxxxxxxxxxx unrelated noise xxxxxxxx",
        metadata={},
    )
    chunks = chunk_text(doc.text)
    monkeypatch.setattr("b2_automation.local_semantic_retrieval._sklearn_tfidf_rank", lambda q, c: None)
    monkeypatch.setattr("b2_automation.local_semantic_retrieval._pure_tfidf_cosine", lambda q, c: [0.0] * len(c))

    rows, method = retrieve_chunks_for_form("B24_RL2", [doc], {"z.txt": chunks})
    assert method == "keyword_fallback"


def test_retrieval_scores_do_not_authorize_writes_in_trace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = _repo_root()
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    (inbox / "evidence.txt").write_text(
        "facility: HIGH_WEIGHT_B24_SIGNAL " * 20 + "\nB24 RL2 Date: 2099-01-01\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "b2_automation.inbox_pipeline.process_pdf",
        lambda _pdf: (_ for _ in ()).throw(AssertionError("no docupipe")),
    )
    run_inbox_pipeline(root=root, inbox=inbox, out_dir=tmp_path / "run")

    tr = json.loads((tmp_path / "run" / "field_traceability.json").read_text(encoding="utf-8"))
    assert tr["retrieval_authorizes_writes"] is False
    for row in tr["entries"]:
        if row.get("authorized_for_write") is True:
            assert row.get("decision_state") == "FILL"
            assert row.get("approval_map_target") is not None


def test_map_missing_still_emits_artifacts_with_fill_blocked(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fake_root = tmp_path / "bare"
    (fake_root / "schemas" / "maps").mkdir(parents=True)
    (fake_root / "templates").mkdir(parents=True)
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    (inbox / "evidence.txt").write_text("Cover Page Facility: X\nB24 RL2 evidence\n", encoding="utf-8")
    monkeypatch.setattr(
        "b2_automation.inbox_pipeline.process_pdf",
        lambda _pdf: (_ for _ in ()).throw(AssertionError("no docupipe")),
    )
    run_inbox_pipeline(root=fake_root, inbox=inbox, out_dir=tmp_path / "run")

    assert (tmp_path / "run" / "canonical_evidence.json").is_file()
    assert (tmp_path / "run" / "field_traceability.json").is_file()
    tr = json.loads((tmp_path / "run" / "field_traceability.json").read_text(encoding="utf-8"))
    ce = json.loads((tmp_path / "run" / "canonical_evidence.json").read_text(encoding="utf-8"))
    assert all(not row.get("filled") for row in ce["fields"] if row.get("fill_block_reason"))
    for row in tr["entries"]:
        if row.get("decision_state") == "FILL":
            assert row.get("filled") is False
            assert row.get("fill_block_reason") or not row.get("authorized_for_write")
