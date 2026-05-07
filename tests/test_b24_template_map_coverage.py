"""B24_RL1 manifest vs DocuPipe normalizer: no silent drift between JSON map and code."""

from __future__ import annotations

import json
from pathlib import Path

from b2_automation.b24_normalizer import (
    B24_RL1_MANUAL_OR_SYNTHETIC_FIELDS,
    DOCUPIPE_MAPPED_B24_RL1_FIELD_IDS,
    _FIELD_KEY_TO_MANIFEST,
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _b24_manifest_field_ids() -> set[str]:
    path = _repo_root() / "schemas" / "templates" / "B24_RL1.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    return {c["field_id"] for c in data["cells"]}


def test_every_manifest_field_id_is_mapped_or_explicitly_manual() -> None:
    manifest_ids = _b24_manifest_field_ids()
    missing: list[str] = []
    for fid in sorted(manifest_ids):
        if fid in DOCUPIPE_MAPPED_B24_RL1_FIELD_IDS:
            continue
        reason = B24_RL1_MANUAL_OR_SYNTHETIC_FIELDS.get(fid, "").strip()
        if len(reason) < 20:
            missing.append(
                f"{fid!r}: add a DocuPipe key in _FIELD_KEY_TO_MANIFEST or a "
                f"non-trivial reason in B24_RL1_MANUAL_OR_SYNTHETIC_FIELDS (got {reason!r})"
            )
    assert not missing, "Unaccounted B24_RL1 manifest field_ids:\n" + "\n".join(missing)


def test_normalizer_only_targets_manifest_field_ids() -> None:
    manifest_ids = _b24_manifest_field_ids()
    orphans = sorted(DOCUPIPE_MAPPED_B24_RL1_FIELD_IDS - manifest_ids)
    assert not orphans, (
        "DocuPipe map points at manifest field_ids missing from B24_RL1.json: "
        + ", ".join(orphans)
    )


def test_manual_field_ids_exist_in_manifest() -> None:
    manifest_ids = _b24_manifest_field_ids()
    extra = sorted(set(B24_RL1_MANUAL_OR_SYNTHETIC_FIELDS) - manifest_ids)
    assert not extra, (
        "B24_RL1_MANUAL_OR_SYNTHETIC_FIELDS lists field_ids not in manifest: " + ", ".join(extra)
    )


def test_each_docupipe_key_maps_to_known_manifest_cell() -> None:
    """Every extraction key resolves to a field_id present in the manifest JSON."""
    manifest_ids = _b24_manifest_field_ids()
    bad: list[str] = []
    for key, target in sorted(_FIELD_KEY_TO_MANIFEST.items()):
        if target not in manifest_ids:
            bad.append(f"{key!r} -> {target!r} (missing from B24_RL1.json cells)")
    assert not bad, "Invalid DocuPipe key targets:\n" + "\n".join(bad)
