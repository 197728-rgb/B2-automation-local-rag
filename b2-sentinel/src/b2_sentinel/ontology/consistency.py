"""Cross-form consistency enforcement.

After a multi-form run completes, the consistency checker examines all
filled values for canonical fields that require cross-form agreement.
Detects and reports any discrepancies.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from .schema import CanonicalField, FieldOntology


@dataclass
class ConsistencyViolation:
    """A detected inconsistency across forms for a canonical field."""

    canonical_id: str
    display_name: str
    category: str
    forms_and_values: dict[str, str]
    severity: str = "error"
    message: str = ""


@dataclass
class ConsistencyReport:
    """Result of cross-form consistency check for a packet."""

    run_id: str
    forms_checked: list[str]
    canonical_fields_checked: int = 0
    violations: list[ConsistencyViolation] = field(default_factory=list)
    passed: bool = True

    def to_dict(self) -> dict:
        return {
            "run_id": self.run_id,
            "forms_checked": self.forms_checked,
            "canonical_fields_checked": self.canonical_fields_checked,
            "violations_count": len(self.violations),
            "passed": self.passed,
            "violations": [
                {
                    "canonical_id": v.canonical_id,
                    "display_name": v.display_name,
                    "category": v.category,
                    "severity": v.severity,
                    "forms_and_values": v.forms_and_values,
                    "message": v.message,
                }
                for v in self.violations
            ],
        }


def check_packet_consistency(
    ontology: FieldOntology,
    run_dir: Path,
    forms: list[str],
) -> ConsistencyReport:
    """Check all filled values across forms for cross-form consistency.

    Reads review.json from each form's output directory, extracts filled
    values, and compares them across forms for canonical fields that
    require consistency.
    """
    form_values: dict[str, dict[str, str]] = {}

    for form_id in forms:
        form_dir = run_dir / form_id
        review_path = form_dir / "review.json"
        if not review_path.exists():
            continue
        try:
            review = json.loads(review_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue

        decisions = review.get("decisions", {})
        values: dict[str, str] = {}
        for fid, dec in decisions.items():
            if dec.get("state") == "FILL" and dec.get("value"):
                values[fid] = str(dec["value"])
        form_values[form_id] = values

    report = ConsistencyReport(
        run_id=run_dir.name,
        forms_checked=list(form_values.keys()),
    )

    checked = 0
    for cid, cf in ontology.canonical_fields.items():
        if not cf.cross_form_consistency_required:
            continue
        if cf.consistency.mode == "ignore":
            continue

        values_by_form: dict[str, str] = {}
        for binding in cf.bindings:
            if binding.form_id not in form_values:
                continue
            fv = form_values[binding.form_id]
            val = fv.get(binding.field_id)
            if val:
                values_by_form[binding.form_id] = val

        if len(values_by_form) < 2:
            continue

        checked += 1
        unique_values = set(values_by_form.values())

        if cf.consistency.mode == "exact_match":
            if len(unique_values) > 1:
                report.violations.append(ConsistencyViolation(
                    canonical_id=cid,
                    display_name=cf.display_name,
                    category=cf.category,
                    forms_and_values=values_by_form,
                    severity="error",
                    message=f"Inconsistent values across {len(values_by_form)} forms: {unique_values}",
                ))
        elif cf.consistency.mode == "prefix_match":
            normalized = {v.split()[0].upper() for v in unique_values}
            if len(normalized) > 1:
                report.violations.append(ConsistencyViolation(
                    canonical_id=cid,
                    display_name=cf.display_name,
                    category=cf.category,
                    forms_and_values=values_by_form,
                    severity="warning",
                    message=f"Prefix mismatch across forms: {normalized}",
                ))
        elif cf.consistency.mode == "contains":
            base_val = next(iter(unique_values))
            for v in unique_values:
                if base_val not in v and v not in base_val:
                    report.violations.append(ConsistencyViolation(
                        canonical_id=cid,
                        display_name=cf.display_name,
                        category=cf.category,
                        forms_and_values=values_by_form,
                        severity="warning",
                        message=f"Values don't contain each other: {unique_values}",
                    ))
                    break

    report.canonical_fields_checked = checked
    report.passed = len(report.violations) == 0
    return report


def write_consistency_report(report: ConsistencyReport, path: Path) -> None:
    """Write the consistency report to disk."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")
