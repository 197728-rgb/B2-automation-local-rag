"""Ontology builder - auto-generates the global field ontology from approval maps.

Scans all 49 approval maps, identifies fields that appear in multiple forms,
clusters them into canonical entities based on field_id and label similarity,
and assigns category/consistency/rollover policies.
"""
from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path

from ..core.paths import MAPS_DIR, SCHEMAS_DIR
from .schema import (
    CanonicalField,
    ConsistencyRule,
    FieldBinding,
    FieldOntology,
    RolloverPolicy,
)

ONTOLOGY_PATH = SCHEMAS_DIR / "field_ontology.json"

_CATEGORY_PATTERNS: list[tuple[str, str]] = [
    (r"car_mark|car_number|tank_car_id", "car_identity"),
    (r"design_spec|stencil_spec|tank_car_design", "car_identity"),
    (r"aar_form|aar_no", "car_identity"),
    (r"safety_system", "car_identity"),
    (r"tco|tank_car_owner|owner_name|equipment_owner|coating_owner|lining_owner", "owner_identity"),
    (r"pitp|procedure|wps_traceable|ndt_procedure", "procedure"),
    (r"personnel|technician|welder|auditor|inspector|designee", "personnel"),
    (r"measure.*equipment|calibration|gauge", "equipment"),
    (r"material|plate_material|electrode|insulation|jacket|lining|coating", "material"),
    (r"station_stencil|facility|location_in_facility", "facility"),
    (r"record_form|drawing_number|engineering_drawing", "record"),
    (r"size|thickness|length|dimension|patch_plate", "measurement"),
    (r"date|expiration|due_date|calibration_due", "date"),
]

_IDENTITY_FIELDS = frozenset({
    "car_mark_and_number",
    "tank_car_design_specification",
    "stencil_specification",
    "aar_form_4_2_aar_no",
    "reference_aar_form_4_2_aar_no",
    "safety_system_type",
    "pitp_document_name",
    "pitp_id",
    "station_stencil",
    "tank_car_owner_tco_name",
    "tank_car_or_service_equipment_owner_tco_seo_name",
    "tank_car_or_lining_coating_owner_tco_l_co_name",
})


def _categorize(field_id: str) -> str:
    fid_lower = field_id.lower()
    for pattern, category in _CATEGORY_PATTERNS:
        if re.search(pattern, fid_lower):
            return category
    return "other"


def _normalize_canonical_id(field_id: str) -> str:
    """Strip trailing _N suffixes to group repeated table fields."""
    return re.sub(r"_(\d+)$", "", field_id)


def _consistency_for(canonical_id: str, category: str) -> ConsistencyRule:
    if category in ("car_identity", "owner_identity"):
        return ConsistencyRule(mode="exact_match")
    if category == "procedure":
        return ConsistencyRule(mode="exact_match")
    if category in ("personnel", "date"):
        return ConsistencyRule(mode="ignore")
    return ConsistencyRule(mode="exact_match")


def _rollover_for(canonical_id: str, category: str) -> RolloverPolicy:
    if category == "car_identity":
        return RolloverPolicy(mode="safe_if_same_car")
    if category == "owner_identity":
        return RolloverPolicy(mode="safe_if_same_car")
    if category == "procedure":
        return RolloverPolicy(mode="carry_forward")
    if category == "facility":
        return RolloverPolicy(mode="carry_forward")
    if category in ("personnel", "date", "measurement"):
        return RolloverPolicy(mode="always_refresh")
    return RolloverPolicy(mode="manual_only")


def _display_name(field_id: str, labels: set[str]) -> str:
    """Pick the best display name from available labels."""
    if labels:
        longest = max(labels, key=len)
        return longest
    return field_id.replace("_", " ").title()


def build_ontology() -> FieldOntology:
    """Scan all approval maps and generate the global field ontology."""
    field_forms: dict[str, list[tuple[str, str]]] = defaultdict(list)
    field_labels: dict[str, set[str]] = defaultdict(set)

    for map_file in sorted(MAPS_DIR.glob("*.json")):
        form_id = map_file.stem
        try:
            data = json.loads(map_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        fields = data.get("fields", {})
        for fid, fdata in fields.items():
            canonical_id = _normalize_canonical_id(fid)
            field_forms[canonical_id].append((form_id, fid))
            label = fdata.get("label", "")
            if label:
                field_labels[canonical_id].add(label)

    canonical_fields: dict[str, CanonicalField] = {}

    for canonical_id, instances in field_forms.items():
        if len(instances) < 2:
            continue

        labels = field_labels.get(canonical_id, set())
        category = _categorize(canonical_id)
        base_fid = _normalize_canonical_id(canonical_id)
        is_identity = base_fid in _IDENTITY_FIELDS

        bindings = [
            FieldBinding(form_id=form_id, field_id=fid, label=next(iter(labels), ""))
            for form_id, fid in instances
        ]

        semantic_variants = sorted(labels) if labels else []

        cf = CanonicalField(
            canonical_id=canonical_id,
            display_name=_display_name(canonical_id, labels),
            description=f"Appears in {len(instances)} forms",
            category=category,
            bindings=bindings,
            semantic_variants=semantic_variants,
            consistency=_consistency_for(canonical_id, category),
            rollover=_rollover_for(canonical_id, category),
            cross_form_consistency_required=is_identity or category in ("car_identity", "owner_identity"),
        )
        canonical_fields[canonical_id] = cf

    return FieldOntology(
        version="1.0.0",
        generated_from=f"{len(list(MAPS_DIR.glob('*.json')))} approval maps",
        canonical_fields=canonical_fields,
    )


def save_ontology(ontology: FieldOntology, path: Path | None = None) -> Path:
    """Persist the ontology to disk."""
    out = path or ONTOLOGY_PATH
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(ontology.model_dump_json(indent=2), encoding="utf-8")
    return out


def load_ontology(path: Path | None = None) -> FieldOntology:
    """Load the ontology from disk, or build fresh if missing."""
    p = path or ONTOLOGY_PATH
    if p.exists():
        data = json.loads(p.read_text(encoding="utf-8"))
        return FieldOntology.model_validate(data)
    return build_ontology()
