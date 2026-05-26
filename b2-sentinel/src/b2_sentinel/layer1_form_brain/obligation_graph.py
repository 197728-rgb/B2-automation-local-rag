"""Form Obligation Graph builder - the heart of Layer 1.

Reads the exact approval map for a form, augments each field with SENTINEL
metadata (evidence_required, n_a_allowed, completion_blocker_if_missing,
write_authority, aliases, expansion_search_terms), then emits an
ObligationGraph that downstream layers treat as the form's contract.
"""
from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path
from typing import Any

from ..core.models import (
    ApprovalMap,
    FieldNode,
    ObligationGraph,
)
from ..core.paths import (
    OBLIGATION_GRAPHS_DIR,
    form_obligation_graph_path,
    form_template_path,
)
from ..core.status import WriteAuthority
from .completion_policy import load_na_policy
from .write_authority import load_exact_approval_map


# Field-id patterns that drive default SENTINEL flags. The closed-loop spec
# names these directly in the example obligation graph for B89.
_KNOWN_NA_ELIGIBLE: frozenset[str] = frozenset({
    "test_fixture.weld.length",
    "test_fixture.patch_plate.size",
    "facility_workforce_size",
})

_DEFAULT_EXPANSION_TERMS: dict[str, list[str]] = {
    "tco.name": [
        "Tank Car Owner",
        "TCO Name",
        "Owner Name",
        "Equipment Owner",
    ],
    "tco.instructions": [
        "Written Instructions",
        "TCO instructions",
        "writtenInstructionsFromTCO",
        "Written Instructions from TCO",
    ],
    "tco.permission_date": [
        "Date Permission Received",
        "TCO permission date",
        "datePermissionReceived",
    ],
    "pitp.id": [
        "PITP ID",
        "Pitp Id",
        "Production Inspection Test Plan",
        "Procedure ID",
        "Procedure Id",
    ],
    "pitp.name": [
        "PITP Document Name",
        "Pitp Document Name",
        "Procedure Name",
    ],
    "car.mark": [
        "Car Mark",
        "Car Mark And Number",
        "car number",
        "tank car number",
    ],
    "aar.form_4_2.number": [
        "AAR Form 4-2",
        "AAR No.",
        "Aar Form42 Number",
        "Aar Form Number",
        "Form 4-2 (AAR No.)",
    ],
    "test_fixture.patch_plate.size": [
        "Patch Plate Size",
        "Observed Size of Patch Plate",
        "Size of Patch Plate",
    ],
    "materials.insulation.spec": [
        "Insulation Material",
        "insulation spec",
    ],
    "materials.jacket.spec": [
        "Jacket Material",
        "jacket spec",
    ],
}


def structure_fingerprint(template_path: Path) -> str:
    """SHA-256 of word/document.xml inside the DOCX, used as a structural id."""
    if not template_path.exists():
        return ""
    with zipfile.ZipFile(template_path) as zf:
        try:
            data = zf.read("word/document.xml")
        except KeyError:
            return ""
    return hashlib.sha256(data).hexdigest()


def build_obligation_graph(
    form_id: str,
    *,
    form_version: str = "2026",
    aliases_for_form: dict[str, list[str]] | None = None,
    expansion_overrides: dict[str, list[str]] | None = None,
) -> ObligationGraph:
    """Build an obligation graph for one form."""
    am = load_exact_approval_map(form_id, form_version=form_version)
    na_policy = load_na_policy(form_id)
    aliases_for_form = aliases_for_form or {}
    expansion_overrides = expansion_overrides or {}

    nodes: dict[str, FieldNode] = {}
    required_total = optional_total = never_write_total = 0

    for fid, raw_field in am.fields.items():
        # Pull what's in the approval map
        write_mode = getattr(raw_field, "write_mode", "replace") or "replace"
        if write_mode not in ("replace", "append_after_label"):
            write_mode = "replace"

        cell_role_raw = getattr(raw_field, "cell_role", "target") or "target"
        if cell_role_raw not in ("target", "label", "notes", "header"):
            cell_role_raw = "target"

        required = bool(raw_field.required)
        n_a_allowed = fid in na_policy or fid in _KNOWN_NA_ELIGIBLE
        evidence_required = required  # default
        completion_blocker = required and not n_a_allowed
        never_write = cell_role_raw in ("label", "header")

        node = FieldNode(
            field_id=fid,
            label=raw_field.label,
            table_index=raw_field.table_index,
            row=raw_field.row,
            col=raw_field.col,
            cell_role=cell_role_raw,  # type: ignore[arg-type]
            write_mode=write_mode,  # type: ignore[arg-type]
            required=required,
            optional=not required,
            n_a_allowed=n_a_allowed,
            evidence_required=evidence_required,
            completion_blocker_if_missing=completion_blocker,
            write_authority=WriteAuthority.EXACT_APPROVAL_MAP,
            never_write=never_write,
            aliases=list(aliases_for_form.get(fid, [])),
            preferred_evidence_keys=_preferred_keys_for(fid, raw_field.label),
            expansion_search_terms=expansion_overrides.get(
                fid, _DEFAULT_EXPANSION_TERMS.get(fid, _expansion_from_label(raw_field.label))
            ),
        )
        nodes[fid] = node
        if never_write:
            never_write_total += 1
        elif required:
            required_total += 1
        else:
            optional_total += 1

    template_path = form_template_path(form_id)
    fp = structure_fingerprint(template_path) if template_path.exists() else None

    return ObligationGraph(
        form_id=form_id,
        form_version=form_version,
        template_path=str(template_path),
        structure_fingerprint=fp,
        fields=nodes,
        required_total=required_total,
        optional_total=optional_total,
        never_write_total=never_write_total,
    )


def _preferred_keys_for(field_id: str, label: str) -> list[str]:
    keys = {field_id, label.lower()}
    keys.add(field_id.replace(".", "_"))
    keys.add(field_id.replace(".", " "))
    return sorted(k for k in keys if k)


def _expansion_from_label(label: str) -> list[str]:
    base = label.strip()
    return [base, base.lower()]


def save_obligation_graph(graph: ObligationGraph, *, dest: Path | None = None) -> Path:
    OBLIGATION_GRAPHS_DIR.mkdir(parents=True, exist_ok=True)
    out = dest or form_obligation_graph_path(graph.form_id)
    payload = json.loads(graph.model_dump_json())
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return out


def load_obligation_graph(form_id: str) -> ObligationGraph:
    path = form_obligation_graph_path(form_id)
    if not path.exists():
        return build_obligation_graph(form_id)
    with path.open(encoding="utf-8") as fh:
        data = json.load(fh)
    return ObligationGraph.model_validate(data)
