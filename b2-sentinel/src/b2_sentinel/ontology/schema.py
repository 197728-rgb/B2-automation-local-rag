"""Ontology schema - canonical field definitions and cross-form bindings.

A CanonicalField is a real-world fact that may appear across many forms.
Each instance (FieldBinding) links a form-specific field_id to its canonical
entity, enabling consistency checks and shared evidence across a packet.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class FieldBinding(BaseModel):
    """One form-specific field_id bound to a canonical entity."""

    form_id: str
    field_id: str
    label: str = ""


class ConsistencyRule(BaseModel):
    """How to enforce consistency for this canonical field across forms."""

    mode: Literal["exact_match", "prefix_match", "contains", "ignore"] = "exact_match"
    tolerance: str | None = None


class RolloverPolicy(BaseModel):
    """How this field behaves across time (prior packet -> current packet)."""

    mode: Literal["safe_if_same_car", "always_refresh", "carry_forward", "manual_only"] = "safe_if_same_car"
    condition: str | None = None


class CanonicalField(BaseModel):
    """A single real-world fact that appears across multiple forms.

    This is the unit of cross-form intelligence. When B89 says UTLX 213220
    and B90 says UTLX 213320, the ontology detects the inconsistency because
    both are bound to the same canonical_id.
    """

    canonical_id: str
    display_name: str
    description: str = ""
    category: Literal[
        "car_identity",
        "owner_identity",
        "procedure",
        "personnel",
        "equipment",
        "material",
        "facility",
        "record",
        "measurement",
        "date",
        "other",
    ] = "other"

    bindings: list[FieldBinding] = Field(default_factory=list)
    semantic_variants: list[str] = Field(default_factory=list)
    consistency: ConsistencyRule = Field(default_factory=ConsistencyRule)
    rollover: RolloverPolicy = Field(default_factory=RolloverPolicy)
    cross_form_consistency_required: bool = True


class FieldOntology(BaseModel):
    """The complete global field ontology for B2 SENTINEL."""

    version: str = "1.0.0"
    generated_from: str = "approval_maps"
    canonical_fields: dict[str, CanonicalField] = Field(default_factory=dict)

    def fields_for_form(self, form_id: str) -> list[tuple[str, FieldBinding]]:
        """Return all (canonical_id, binding) pairs for a given form."""
        out = []
        for cid, cf in self.canonical_fields.items():
            for b in cf.bindings:
                if b.form_id == form_id:
                    out.append((cid, b))
        return out

    def canonical_for_field(self, form_id: str, field_id: str) -> CanonicalField | None:
        """Find the canonical entity for a specific form field."""
        for cf in self.canonical_fields.values():
            for b in cf.bindings:
                if b.form_id == form_id and b.field_id == field_id:
                    return cf
        return None
