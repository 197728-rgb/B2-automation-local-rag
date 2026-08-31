"""Deterministic checks that convert AAR incidents into failures.

Each validator takes a run record (see `schema.md`) and returns findings. A finding is
an objective defect, not a warning: any finding blocks delivery.

Every validator names the incident it protects against. If a validator has no incident,
it does not belong here; if an incident has no validator, it is not yet prevented.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, asdict
from typing import Any, Iterable

# Controlled vocabularies. A value outside its vocabulary is a defect, and it is also how
# concatenation is caught: "IIII" and "UTTVT" are not levels or methods, they are two
# values glued together.
NDT_LEVELS = {"I", "II", "III"}
NDT_METHODS = {"UT", "UTT", "MT", "PT", "VT", "RT", "ET", "LT", "HLT"}
TCID_REQUIRED_COLUMNS = ("revision", "record_type", "entry_type")
TERMINAL_DISPOSITIONS = {
    "CONFIRMED_VALUE", "PRESERVE_BASELINE", "CONTROLLED_BLANK",
    "AUTHORIZED_NA", "WITHHOLD_CONFLICT", "UNVERIFIABLE",
}

# Name particles that legitimately contain an internal capital, so they are not evidence
# of two records glued together.
_NAME_PARTICLES = re.compile(r"\b(Mc|Mac|O'|De|Di|Van|Von|La|Le)[A-Z]", re.I)
_GLUED_BOUNDARY = re.compile(r"[a-z.][A-Z]")


@dataclass(frozen=True)
class Finding:
    incident: str          # AAR-R### this defect is an instance of
    check: str             # validator that produced it
    location: str          # where in the run record
    detail: str            # what is wrong, concretely

    def as_dict(self) -> dict[str, str]:
        return asdict(self)


def _looks_concatenated(value: str) -> bool:
    """True when a single-valued cell appears to hold two records glued together."""
    if not value:
        return False
    stripped = _NAME_PARTICLES.sub("", value)
    return bool(_GLUED_BOUNDARY.search(stripped))


def _split_candidates(value: str, vocabulary: set[str]) -> list[str]:
    """Greedily split a glued value into vocabulary terms, e.g. UTTVT -> [UTT, VT]."""
    parts: list[str] = []
    rest = value.strip().upper()
    while rest:
        for size in range(min(len(rest), 4), 0, -1):
            head = rest[:size]
            if head in vocabulary:
                parts.append(head)
                rest = rest[size:]
                break
        else:
            return []
    return parts if len(parts) > 1 else []


def check_personnel_row_identity(record: dict[str, Any]) -> list[Finding]:
    """AAR-R001 - two personnel identities must never share one logical row."""
    findings = []
    for row in _rows(record, "personnel"):
        where = f"{row.get('table', 'personnel')} row {row.get('row', '?')}"
        cells = row.get("cells", {})

        name = str(cells.get("name", ""))
        if _looks_concatenated(name):
            findings.append(Finding(
                "AAR-R001", "check_personnel_row_identity", where,
                f"name cell {name!r} contains two glued identities",
            ))

        level = str(cells.get("level", "")).strip()
        if level and level not in NDT_LEVELS:
            split = _split_candidates(level, NDT_LEVELS)
            detail = (f"level {level!r} is two levels merged ({' + '.join(split)})"
                      if split else f"level {level!r} is not one of {sorted(NDT_LEVELS)}")
            findings.append(Finding("AAR-R001", "check_personnel_row_identity", where, detail))

        method = str(cells.get("method", "")).strip()
        if method and method not in NDT_METHODS:
            split = _split_candidates(method, NDT_METHODS)
            detail = (f"method {method!r} is two methods merged ({' + '.join(split)})"
                      if split else f"method {method!r} is not a recognized NDT method")
            findings.append(Finding("AAR-R001", "check_personnel_row_identity", where, detail))
    return findings


def check_equipment_row_identity(record: dict[str, Any]) -> list[Finding]:
    """AAR-R002 - two equipment or calibration records must never share one row."""
    findings = []
    for row in _rows(record, "equipment"):
        where = f"{row.get('table', 'equipment')} row {row.get('row', '?')}"
        for field in ("equipment_name", "equipment_id", "function"):
            value = str(row.get("cells", {}).get(field, ""))
            if _looks_concatenated(value):
                findings.append(Finding(
                    "AAR-R002", "check_equipment_row_identity", where,
                    f"{field} cell {value!r} contains two glued records",
                ))
    return findings


def check_tcid_completeness(record: dict[str, Any]) -> list[Finding]:
    """AAR-R003 - a TCID entry present in the baseline keeps every required column."""
    findings = []
    for entry in record.get("tcid_entries", []):
        where = f"tcid entry {entry.get('id', '?')}"
        baseline = entry.get("baseline", {})
        target = entry.get("target", {})
        for column in TCID_REQUIRED_COLUMNS:
            had = str(baseline.get(column, "")).strip()
            now = str(target.get(column, "")).strip()
            if had and not now:
                findings.append(Finding(
                    "AAR-R003", "check_tcid_completeness", where,
                    f"{column} was {had!r} in the baseline and is empty in the target",
                ))
    return findings


def check_machine_readability(record: dict[str, Any]) -> list[Finding]:
    """AAR-R005 - what a reader sees must equal what an extractor reads."""
    findings = []
    for field in record.get("fields", []):
        visible = str(field.get("visible", "")).strip()
        machine = str(field.get("machine", "")).strip()
        if visible and not machine:
            findings.append(Finding(
                "AAR-R005", "check_machine_readability", field.get("key", "?"),
                f"visible value {visible!r} extracts as blank",
            ))
        elif visible and machine and visible != machine:
            findings.append(Finding(
                "AAR-R005", "check_machine_readability", field.get("key", "?"),
                f"visible {visible!r} does not match extracted {machine!r}",
            ))
    return findings


def check_two_way_completeness(record: dict[str, Any]) -> list[Finding]:
    """AAR-R004 / AAR-R010 - every populated baseline fact gets an explicit disposition."""
    findings = []
    for fact in record.get("source_facts", []):
        key = fact.get("key", "?")
        disposition = str(fact.get("disposition", "")).strip().upper()
        if not disposition or disposition == "UNACCOUNTED":
            findings.append(Finding(
                fact.get("incident", "AAR-R010"), "check_two_way_completeness", key,
                f"populated baseline fact {fact.get('value', '')!r} has no disposition",
            ))
        elif disposition not in TERMINAL_DISPOSITIONS:
            findings.append(Finding(
                fact.get("incident", "AAR-R010"), "check_two_way_completeness", key,
                f"disposition {disposition!r} is not one of {sorted(TERMINAL_DISPOSITIONS)}",
            ))
        elif disposition in {"PRESERVE_BASELINE", "CONFIRMED_VALUE"}:
            # A fact claimed preserved must actually be present in the target.
            if str(fact.get("value", "")).strip() and not str(fact.get("target_value", "")).strip():
                findings.append(Finding(
                    fact.get("incident", "AAR-R010"), "check_two_way_completeness", key,
                    f"claimed {disposition} but the target value is blank",
                ))
    return findings


def check_structure_preserved(record: dict[str, Any]) -> list[Finding]:
    """AAR-R006 - protected template geometry survives the write unchanged."""
    findings = []
    structure = record.get("structure", {})
    for dimension in ("tables", "rows", "columns", "merges"):
        before = structure.get(f"{dimension}_before")
        after = structure.get(f"{dimension}_after")
        if before is not None and after is not None and before != after:
            findings.append(Finding(
                "AAR-R006", "check_structure_preserved", f"structure.{dimension}",
                f"{dimension} changed from {before} to {after}",
            ))
    if structure.get("document_wide_formatting_pass"):
        findings.append(Finding(
            "AAR-R006", "check_structure_preserved", "structure",
            "a document-wide or changed-cell formatting pass ran after the write",
        ))
    return findings


def check_baseline_selection(record: dict[str, Any]) -> list[Finding]:
    """AAR-R007 - an accepted completed current form is not rebuilt from a blank."""
    findings = []
    mode = str(record.get("mode", "")).strip().upper()
    if not mode:
        return [Finding("AAR-R007", "check_baseline_selection", "mode",
                        "no job mode declared")]
    if mode == "NEW_FILL" and record.get("accepted_baseline_exists"):
        findings.append(Finding(
            "AAR-R007", "check_baseline_selection", "mode",
            "NEW_FILL chosen while an accepted completed current form exists",
        ))
    return findings


def check_draft_status(record: dict[str, Any]) -> list[Finding]:
    """AAR-R009 - a draft signature blank is not a final-release defect."""
    findings = []
    status = str(record.get("document_status", "")).strip().upper()
    for finding in record.get("reported_findings", []):
        if finding.get("type") == "SIGNATURE_BLANK" and status == "DRAFT":
            findings.append(Finding(
                "AAR-R009", "check_draft_status", finding.get("location", "?"),
                "signature blank reported as a defect on a DRAFT document",
            ))
    return findings


def check_field_comparison_identity(record: dict[str, Any]) -> list[Finding]:
    """AAR-R008 - a comparison must be between the same semantic field."""
    findings = []
    for comparison in record.get("comparisons", []):
        left, right = comparison.get("source_field"), comparison.get("target_field")
        if left and right and left != right:
            findings.append(Finding(
                "AAR-R008", "check_field_comparison_identity",
                comparison.get("id", "?"),
                f"compared {left!r} against {right!r}, which are different fields",
            ))
    return findings


def check_scope_discipline(record: dict[str, Any]) -> list[Finding]:
    """AAR-R026 - nothing is delivered that the request did not ask for."""
    requested = {str(item).strip().lower() for item in record.get("requested_scope", [])}
    if not requested:
        return []
    return [
        Finding("AAR-R026", "check_scope_discipline", str(item),
                f"delivered {item!r}, which was not in the requested scope")
        for item in record.get("delivered", [])
        if str(item).strip().lower() not in requested
    ]


ALL_CHECKS = (
    check_scope_discipline,
    check_baseline_selection,
    check_personnel_row_identity,
    check_equipment_row_identity,
    check_tcid_completeness,
    check_two_way_completeness,
    check_machine_readability,
    check_structure_preserved,
    check_field_comparison_identity,
    check_draft_status,
)


def _rows(record: dict[str, Any], kind: str) -> Iterable[dict[str, Any]]:
    return [row for row in record.get("rows", []) if row.get("kind") == kind]


def run_all(record: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []
    for check in ALL_CHECKS:
        findings.extend(check(record))
    return findings
