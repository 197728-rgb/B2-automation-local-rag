"""Deterministic checks that turn failure classes in 03_ERROR_LEDGER.md into failures.

Each check names the class it prevents. A class with no check is governed by rule only;
a check with no class does not belong here.

No customer data: fixtures use neutral placeholders (Rule 1, Rule 24).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, asdict
from typing import Any

# Controlled vocabularies. A value outside its vocabulary is how a merged record is
# detected: two valid values concatenated are not a valid value.
QUALIFICATION_LEVELS = {"I", "II", "III"}
METHODS = {"UT", "UTT", "MT", "PT", "VT", "RT", "ET", "LT", "HLT"}
DISPOSITIONS = {"POPULATED_VERIFIED", "BLANK_UNSUPPORTED", "WITHHELD_FLAGGED_DISCREPANCY"}
# Rule 3 vocabulary. Synonyms are accepted because mode is matched by meaning; an
# unrecognized mode is a defect, not a default.
MODE_ALIASES = {
    "NEW_WORK": "NEW_WORK", "NEW_FILL": "NEW_WORK", "NEW_AUDIT_WORK": "NEW_WORK",
    "REWORK": "REWORK", "CORRECTION": "REWORK", "MAINTENANCE": "REWORK",
    "ROLLOVER": "REWORK",
    "FINAL_REVIEW": "FINAL_REVIEW", "REVIEW": "FINAL_REVIEW",
}
# The mode that starts from a clean blank.
BLANK_START_MODES = {"NEW_WORK"}
# Reasons that permit rebuilding from blank during rework (Rule 3, exception clause).
REBUILD_EXCEPTIONS = {"corrupted", "wrong_form_version", "structure_damaged",
                      "regeneration_required"}
RECORD_TYPES = {"PROCEDURE", "FORM", "QUALIFICATION"}

# Values that must never enter reusable knowledge (Rule 1). Patterns, not literals.
CUSTOMER_DATA_PATTERNS = (
    ("facility name", re.compile(r"\b(?:Facility|Customer|Owner)\s*(?:Name)?\s*[:=]", re.I)),
    ("personnel name", re.compile(r"\b(?:Technician|Inspector|Welder|Auditor)\s*(?:Name)?\s*[:=]", re.I)),
    ("car mark", re.compile(r"\b[A-Z]{3,5}\s+\d{3,6}\b")),
    ("completed form", re.compile(r"\bFILLED_[A-Za-z0-9]")),
)

_NAME_PARTICLES = re.compile(r"\b(Mc|Mac|O'|De|Di|Van|Von|La|Le)[A-Z]", re.I)
_GLUED = re.compile(r"[a-z.][A-Z]")
# A leaf key segment naming a position rather than a meaning (Rule 7).
_POSITIONAL_SEGMENT = re.compile(r"^(?:r|row|p|pg|page|t|tbl|table|c|col|cell)[\s._-]*\d+$", re.I)


@dataclass(frozen=True)
class Finding:
    error: str
    check: str
    location: str
    detail: str

    def as_dict(self) -> dict[str, str]:
        return asdict(self)


def _glued(value: str) -> bool:
    return bool(value) and bool(_GLUED.search(_NAME_PARTICLES.sub("", value)))


def _split(value: str, vocabulary: set[str]) -> list[str]:
    parts, rest = [], value.strip().upper()
    while rest:
        for size in range(min(len(rest), 4), 0, -1):
            if rest[:size] in vocabulary:
                parts.append(rest[:size]); rest = rest[size:]; break
        else:
            return []
    return parts if len(parts) > 1 else []


def normalize_mode(value: Any) -> str:
    """`NEW WORK`, `new-work`, and `NEW_FILL` all resolve to the same mode (Rule 3)."""
    return re.sub(r"[\s\-/]+", "_", str(value).strip().upper())


# --- Identity -------------------------------------------------------------------

def check_personnel_rows(record):
    """E-013 — one person per logical row."""
    out = []
    for row in [r for r in record.get("rows", []) if r.get("kind") == "personnel"]:
        where = f"{row.get('table','personnel')} row {row.get('row','?')}"
        cells = row.get("cells", {})
        if _glued(str(cells.get("name", ""))):
            out.append(Finding("E-013", "check_personnel_rows", where,
                               "name cell holds two glued identities"))
        level = str(cells.get("level", "")).strip()
        if level and level not in QUALIFICATION_LEVELS:
            merged = _split(level, QUALIFICATION_LEVELS)
            out.append(Finding("E-013", "check_personnel_rows", where,
                               f"level {level!r} is two levels merged ({' + '.join(merged)})"
                               if merged else f"level {level!r} is outside the controlled set"))
        method = str(cells.get("method", "")).strip()
        if method and method not in METHODS:
            merged = _split(method, METHODS)
            out.append(Finding("E-013", "check_personnel_rows", where,
                               f"method {method!r} is two methods merged ({' + '.join(merged)})"
                               if merged else f"method {method!r} is outside the controlled set"))
    return out


def check_equipment_rows(record):
    """E-013 — one instrument or calibration per logical row."""
    out = []
    for row in [r for r in record.get("rows", []) if r.get("kind") == "equipment"]:
        where = f"{row.get('table','equipment')} row {row.get('row','?')}"
        for field in ("equipment_name", "equipment_id", "function"):
            if _glued(str(row.get("cells", {}).get(field, ""))):
                out.append(Finding("E-013", "check_equipment_rows", where,
                                   f"{field} holds two glued records"))
    return out


def check_record_type_separation(record):
    """E-010 — a shared identifier does not merge record types."""
    seen, out = {}, []
    for item in record.get("records", []):
        key = (item.get("identifier"), str(item.get("type", "")).upper())
        if str(item.get("type", "")).upper() not in RECORD_TYPES:
            out.append(Finding("E-010", "check_record_type_separation",
                               str(item.get("identifier")),
                               f"record type {item.get('type')!r} is not a distinct known type"))
        seen.setdefault(item.get("identifier"), set()).add(key[1])
    for identifier, types in seen.items():
        if len(types) == 1 and record.get("expected_types", {}).get(identifier, 1) > 1:
            out.append(Finding("E-010", "check_record_type_separation", str(identifier),
                               "one identifier resolved to a single type where several were expected"))
    return out


def check_qape_leaf_identity(record):
    """E-011 — a printed section number is not a unique leaf key."""
    out, by_printed = [], {}
    for leaf in record.get("qape_leaves", []):
        key = str(leaf.get("leaf_key", ""))
        positional = [seg for seg in re.split(r"[|/]", key)
                      if _POSITIONAL_SEGMENT.match(seg.strip())]
        if positional:
            out.append(Finding("E-011", "check_qape_leaf_identity", key,
                               f"leaf key carries position {positional} as identity"))
        by_printed.setdefault(leaf.get("printed_section"), []).append(leaf)
    for printed, leaves in by_printed.items():
        if len(leaves) > 1 and len({l.get("leaf_key") for l in leaves}) < len(leaves):
            out.append(Finding("E-011", "check_qape_leaf_identity", str(printed),
                               "repeated printed section resolves to fewer composite keys than leaves"))
    return out


def check_exact_identity_matching(record):
    """E-012 — substring containment is not identity."""
    return [Finding("E-012", "check_exact_identity_matching", str(m.get("query")),
                    f"matched {m.get('matched')!r} by {m.get('method')}")
            for m in record.get("identity_matches", [])
            if str(m.get("method", "")).lower() == "substring"]


def check_coordinate_provenance(record):
    """E-014 — coordinates are derived per run, never carried in."""
    return [Finding("E-014", "check_coordinate_provenance", str(c.get("field", "?")),
                    "physical coordinate sourced from a prior run")
            for c in record.get("coordinates", [])
            if str(c.get("source", "")).lower() == "prior_run"]


def check_field_mapping_authority(record):
    """E-014 - position is never a field's durable identity (Rule 4)."""
    out = []
    positional = {"page", "table", "row", "column", "cell", "index"}
    required = {"form_version", "section", "label"}
    for m in record.get("field_mappings", []):
        key = str(m.get("field", "?"))
        keyed_by = {str(k).strip().lower() for k in m.get("keyed_by", [])}
        if keyed_by & positional:
            out.append(Finding("E-014", "check_field_mapping_authority", key,
                               "reusable mapping keyed by "
                               f"{sorted(keyed_by & positional)}, which is position, not identity"))
        elif not required <= keyed_by:
            out.append(Finding("E-014", "check_field_mapping_authority", key,
                               f"identity is missing {sorted(required - keyed_by)}"))
        if str(m.get("coordinate_source", "current_run")).lower() != "current_run":
            out.append(Finding("E-014", "check_field_mapping_authority", key,
                               "coordinates carried in from "
                               f"{m.get('coordinate_source')!r}"))
        # Rule 16: an approved exact-version map carries its own authority; a map derived
        # this run is permitted only once validated against the current controlled form.
        if (str(m.get("map_source", "approved")).lower() == "run_derived"
                and not m.get("validated_against_form")):
            out.append(Finding("E-002", "check_field_mapping_authority", key,
                               "run-derived map used without validation against the "
                               "current controlled form"))
    return out


def check_rework_baseline(record):
    """E-019 - rework continues from the working form, not a fresh blank (Rule 3)."""
    mode = MODE_ALIASES.get(normalize_mode(record.get("mode", "")))
    if mode != "REWORK":
        return []
    out = []
    if str(record.get("started_from", "")).lower() == "blank":
        reason = str(record.get("rebuild_reason", "")).strip().lower()
        if reason not in REBUILD_EXCEPTIONS:
            out.append(Finding("E-019", "check_rework_baseline", "started_from",
                               "rework restarted from a clean blank with no qualifying "
                               f"exception (reason: {record.get('rebuild_reason') or 'none given'})"))
    lost = [str(v.get("key", "?")) for v in record.get("preserved_values", [])
            if v.get("was_correct") and not str(v.get("target_value", "")).strip()]
    if lost:
        out.append(Finding("E-019", "check_rework_baseline", ", ".join(lost),
                           "correct existing values were lost during rework"))
    return out


def check_comparison_identity(record):
    """E-015 — a comparison is between one semantic field and itself."""
    return [Finding("E-015", "check_comparison_identity", str(c.get("id", "?")),
                    f"compared {c.get('source_field')!r} against {c.get('target_field')!r}")
            for c in record.get("comparisons", [])
            if c.get("source_field") and c.get("target_field")
            and c["source_field"] != c["target_field"]]


# --- Completeness ---------------------------------------------------------------

def check_two_way_completeness(record):
    """E-016, E-017 — every required identity carries an explicit, honest disposition."""
    out = []
    for d in record.get("dispositions", []):
        key = d.get("key", "?")
        state = str(d.get("disposition", "")).strip().upper()
        if not state or state in {"UNACCOUNTED", "UNEVALUATED"}:
            out.append(Finding("E-016", "check_two_way_completeness", key,
                               "required identity has no disposition"))
        elif state not in DISPOSITIONS:
            out.append(Finding("E-016", "check_two_way_completeness", key,
                               f"disposition {state!r} is outside {sorted(DISPOSITIONS)}"))
        elif state == "POPULATED_VERIFIED" and not str(d.get("target_value", "")).strip():
            out.append(Finding("E-017", "check_two_way_completeness", key,
                               "claimed POPULATED_VERIFIED while the destination is blank"))
        elif state == "BLANK_UNSUPPORTED" and str(d.get("target_value", "")).strip():
            out.append(Finding("E-016", "check_two_way_completeness", key,
                               "claimed BLANK_UNSUPPORTED while the destination is populated"))
    return out


def check_conflict_preservation(record):
    """E-018 — a conflict or low-confidence value never collapses into a blank or a fill."""
    out = []
    for d in record.get("dispositions", []):
        state = str(d.get("disposition", "")).strip().upper()
        if d.get("sources_disagree") and state != "WITHHELD_FLAGGED_DISCREPANCY":
            out.append(Finding("E-018", "check_conflict_preservation", d.get("key", "?"),
                               f"sources disagree but disposition is {state!r}"))
        if d.get("low_confidence") and state == "POPULATED_VERIFIED":
            out.append(Finding("E-018", "check_conflict_preservation", d.get("key", "?"),
                               "low-confidence candidate promoted to POPULATED_VERIFIED"))
    return out


def check_candidate_admissibility(record):
    """E-003, E-004, E-005 — a candidate passes a typed check, and fallbacks are disclosed."""
    out = []
    shapes = {"date": re.compile(r"^\d{1,2}[/\-.]\d{1,2}[/\-.]\d{2,4}$|^\d{4}-\d{2}-\d{2}$"),
              "identifier": re.compile(r"^[A-Za-z0-9][A-Za-z0-9\-_/]{1,}$")}
    for c in record.get("candidates", []):
        if not c.get("accepted"):
            continue
        shape = shapes.get(str(c.get("type", "")).lower())
        value = str(c.get("value", ""))
        if shape and not shape.match(value.strip()):
            out.append(Finding("E-003", "check_candidate_admissibility", c.get("key", "?"),
                               f"accepted {value!r} which is not a valid {c.get('type')}"))
        if c.get("via_fallback") and not c.get("fallback_recorded"):
            out.append(Finding("E-005", "check_candidate_admissibility", c.get("key", "?"),
                               "value arrived through an undisclosed fallback"))
    return out


def check_absence_claims(record):
    """E-006, E-007 — absence follows exhaustion, and never a broken environment."""
    out = []
    for a in record.get("absence_claims", []):
        if not a.get("environment_ok", True):
            out.append(Finding("E-007", "check_absence_claims", a.get("key", "?"),
                               "absence concluded while the environment was degraded"))
        elif len(a.get("surfaces_searched", [])) < 2:
            out.append(Finding("E-006", "check_absence_claims", a.get("key", "?"),
                               "absence concluded after a single search path"))
    return out


def check_event_proof(record):
    """E-008 — a register entry is not proof that an event occurred."""
    return [Finding("E-008", "check_event_proof", e.get("key", "?"),
                    "event asserted on register or master-list support alone")
            for e in record.get("event_claims", [])
            if e.get("asserted") and str(e.get("support", "")).lower() == "master_list"]


# --- Output fidelity ------------------------------------------------------------

def check_machine_readability(record):
    """E-025 — what a reader sees and what an extractor reads must agree."""
    out = []
    for f in record.get("fields", []):
        visible, machine = str(f.get("visible", "")).strip(), str(f.get("machine", "")).strip()
        if visible and not machine:
            out.append(Finding("E-025", "check_machine_readability", f.get("key", "?"),
                               "visible value extracts as blank"))
        elif visible and machine and visible != machine:
            out.append(Finding("E-025", "check_machine_readability", f.get("key", "?"),
                               "visible and extracted values differ"))
    return out


def check_protected_structure(record):
    """E-026, E-027 — protected structure survives, and formatting rides the write."""
    out, s = [], record.get("structure", {})
    for dimension in ("sections", "tables", "rows", "columns", "merges", "headers",
                      "footers", "content_controls"):
        before, after = s.get(f"{dimension}_before"), s.get(f"{dimension}_after")
        if before is not None and after is not None and before != after:
            out.append(Finding("E-027", "check_protected_structure", dimension,
                               f"{dimension} changed from {before} to {after}"))
    if s.get("document_wide_formatting_pass"):
        out.append(Finding("E-026", "check_protected_structure", "formatting",
                           "a formatting pass ran after the write"))
    if s.get("tail_valid") is False:
        out.append(Finding("E-027", "check_protected_structure", "tail",
                           "document tail is not valid"))
    return out


def check_document_status(record):
    """E-030 — completion expectations follow document status."""
    status = str(record.get("document_status", "")).strip().upper()
    return [Finding("E-030", "check_document_status", f.get("location", "?"),
                    "signature blank reported as a defect on a DRAFT document")
            for f in record.get("reported_findings", [])
            if f.get("type") == "SIGNATURE_BLANK" and status == "DRAFT"]


# --- Mode and knowledge integrity -----------------------------------------------

def check_mode_and_baseline(record):
    """E-019, E-036 — mode is matched by meaning, and a baseline is not rebuilt."""
    raw = record.get("mode", "")
    mode = normalize_mode(raw)
    if not mode:
        return [Finding("E-019", "check_mode_and_baseline", "mode", "no job mode declared")]
    resolved = MODE_ALIASES.get(mode)
    if resolved is None:
        return [Finding("E-036", "check_mode_and_baseline", "mode",
                        f"mode {raw!r} is unrecognized and cannot be checked")]
    if resolved in BLANK_START_MODES and record.get("accepted_baseline_exists"):
        return [Finding("E-019", "check_mode_and_baseline", "mode",
                        f"{raw!r} chosen while an accepted working form already exists")]
    return []


def check_customer_data_firewall(record):
    """E-043, E-044 — customer facts never enter reusable knowledge."""
    out = []
    for label, pattern in CUSTOMER_DATA_PATTERNS:
        found = pattern.search(str(record.get("knowledge_update", "")))
        if found:
            out.append(Finding("E-044", "check_customer_data_firewall", "knowledge_update",
                               f"contains {label}: {found.group(0)!r}"))
    if record.get("snapshot_source") == "filesystem_walk":
        out.append(Finding("E-043", "check_customer_data_firewall", "snapshot_source",
                           "snapshot enumerated the filesystem instead of the governed file list"))
    return out


def check_scope_discipline(record):
    """E-045 — nothing is delivered that the request did not ask for."""
    requested = {str(i).strip().lower() for i in record.get("requested_scope", [])}
    if not requested:
        return []
    return [Finding("E-045", "check_scope_discipline", str(i),
                    "delivered outside the requested scope")
            for i in record.get("delivered", [])
            if str(i).strip().lower() not in requested]


ALL_CHECKS = (
    check_mode_and_baseline, check_personnel_rows, check_equipment_rows,
    check_record_type_separation, check_qape_leaf_identity, check_exact_identity_matching,
    check_coordinate_provenance, check_field_mapping_authority, check_rework_baseline,
    check_comparison_identity, check_two_way_completeness,
    check_conflict_preservation, check_candidate_admissibility, check_absence_claims,
    check_event_proof, check_machine_readability, check_protected_structure,
    check_document_status, check_customer_data_firewall, check_scope_discipline,
)


def run_all(record: dict[str, Any]) -> list[Finding]:
    out: list[Finding] = []
    for check in ALL_CHECKS:
        out.extend(check(record))
    return out
