"""Raw OOXML DOCX cell patching with structure guard checks.

This writer updates ``word/document.xml`` inside a DOCX package without using a
Word writer or reserializing the full XML tree. It is intentionally narrow:
manifest cell references identify table/row/visual-column cells and only
existing ``w:t`` text nodes inside those cells are patched.
"""

from __future__ import annotations

import html
import json
import re
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from b2_automation.cell_evidence import DecisionState, decide_cell

REVIEW_REQUIRED_TEXT = "REVIEW_REQUIRED"
DEFAULT_LOW_CONFIDENCE_THRESHOLD = 0.70


@dataclass(frozen=True)
class PatchOutcome:
    output_docx: Path
    structure_guard_report: Path | None
    structure_guard_passed: bool
    patched_fields: tuple[str, ...]
    errors: tuple[str, ...]
    table_fill_audit: Mapping[str, Any] | None = None


def _strip_cell_plain_text(document_xml: str, cell_start: int, cell_end: int) -> str:
    segment = document_xml[cell_start:cell_end]
    pieces: list[str] = []
    for match in re.finditer(r"<w:t(?:\s[^>]*)?>(.*?)</w:t>", segment, flags=re.DOTALL):
        raw = match.group(1)
        raw = re.sub(r"<w:tab[^>]*/>", "\t", raw)
        pieces.append(html.unescape(raw))
    joined = "".join(pieces)
    return re.sub(r"\s+", " ", joined).replace("\u00a0", " ").strip()


def audit_table_fill_completeness(
    docx_path: Path,
    manifest: Mapping[str, Any],
    approval_map: Mapping[str, Any] | None,
    *,
    strict_approval_coverage: bool = True,
) -> dict[str, Any]:
    """Audit required target table cells: detect blanks after a patch (coordinate-safe)."""
    docx_path = Path(docx_path)
    errs: list[str] = []
    specs = _approved_manifest_cells(manifest, approval_map, errs, strict_coverage=strict_approval_coverage)
    with zipfile.ZipFile(docx_path, "r") as zf:
        document_xml = zf.read("word/document.xml").decode("utf-8")
    tables = _find_elements(document_xml, "w:tbl")
    rows_detail: list[dict[str, Any]] = []
    blank_required: list[str] = []
    manual_required: list[str] = []
    for spec in specs:
        if _cell_role(spec) != "target":
            continue
        if not _required_for_spec(spec, set()):
            continue
        fid = str(spec["field_id"])
        try:
            cell_start, cell_end = _cell_range_for_spec(document_xml, tables, spec)
            text = _strip_cell_plain_text(document_xml, cell_start, cell_end)
        except (IndexError, ValueError) as exc:
            rows_detail.append({"field_id": fid, "label": spec.get("label"), "status": "error", "error": str(exc)})
            blank_required.append(fid)
            continue
        if not text:
            status = "blank"
            blank_required.append(fid)
        elif REVIEW_REQUIRED_TEXT in text:
            status = "manual_marker"
            manual_required.append(fid)
        else:
            status = "filled"
        rows_detail.append(
            {
                "field_id": fid,
                "label": spec.get("label"),
                "cell_text_preview": text[:120] + ("..." if len(text) > 120 else ""),
                "status": status,
            }
        )
    return {
        "docx": str(docx_path.resolve()),
        "required_targets": rows_detail,
        "blank_required_field_ids": sorted(set(blank_required)),
        "manual_marker_required_field_ids": sorted(set(manual_required)),
        "required_targets_complete": not blank_required,
        "approval_errors": list(errs),
    }


def patch_docx_cells(
    template_path: Path,
    manifest: Mapping[str, Any],
    field_values: Mapping[str, str],
    output_path: Path,
    *,
    field_confidences: Mapping[str, float | None] | None = None,
    required_field_ids: set[str] | None = None,
    low_confidence_threshold: float = DEFAULT_LOW_CONFIDENCE_THRESHOLD,
    structure_guard_report_path: Path | None = None,
    approval_map: Mapping[str, Any] | None = None,
    strict_approval_coverage: bool = True,
    table_fill_audit_manifest: Mapping[str, Any] | None = None,
) -> PatchOutcome:
    """Patch approved manifest cells in a DOCX package.

    Missing optional values preserve the existing cell. Missing required values
    are written as review markers. Existing OOXML package parts are copied
    unchanged except for ``word/document.xml``.

    When ``table_fill_audit_manifest`` is set, post-patch completeness is
    checked against that manifest (typically the full template manifest) while
    ``manifest`` may list only the subset of cells being patched.
    """

    template_path = Path(template_path)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    structure_guard_report_path = (
        Path(structure_guard_report_path)
        if structure_guard_report_path is not None
        else output_path.parent / "structure_guard_report.json"
    )

    before_counts = count_docx_structure(template_path)
    confidences = dict(field_confidences or {})
    required_ids = set(required_field_ids or set())
    patches: list[tuple[int, int, str, str]] = []
    errors: list[str] = []
    intentional_text_node_creations = 0
    written_values: set[str] = set()

    with zipfile.ZipFile(template_path, "r") as zin:
        document_xml = zin.read("word/document.xml").decode("utf-8")

    tables = _find_elements(document_xml, "w:tbl")
    specs = _approved_manifest_cells(manifest, approval_map, errors, strict_coverage=strict_approval_coverage)
    for spec in specs:
        fid = str(spec["field_id"])
        value_present = fid in field_values
        value = field_values.get(fid)
        required = _required_for_spec(spec, required_ids)
        role = _cell_role(spec)

        if not value_present and not required:
            continue

        write_value = _value_for_write(
            fid,
            value,
            value_present=value_present,
            role=role,
            required=required,
            confidence=confidences.get(fid),
            low_confidence_threshold=low_confidence_threshold,
        )
        if write_value is None:
            continue
        written_values.add(str(write_value))

        try:
            cell_start, cell_end = _cell_range_for_spec(document_xml, tables, spec)
            text_ranges = _text_ranges(document_xml, cell_start, cell_end)
        except (IndexError, ValueError) as exc:
            if isinstance(exc, ValueError):
                try:
                    insert_at = _paragraph_text_insert_at(document_xml, cell_start, cell_end)
                except ValueError as insert_exc:
                    errors.append(f"{fid}: {insert_exc}")
                    continue
                patches.append((insert_at, insert_at, f"<w:r><w:t>{_xml_text(write_value)}</w:t></w:r>", fid))
                intentional_text_node_creations += 1
                continue
            errors.append(f"{fid}: {exc}")
            continue
        else:
            if str(spec.get("write_mode") or "").strip().lower() == "append_after_label":
                existing_text = _strip_cell_plain_text(document_xml, cell_start, cell_end)
                write_text = _append_after_label_text(existing_text, str(write_value))
            else:
                write_text = str(write_value)
            for idx, (text_start, text_end) in enumerate(text_ranges):
                patches.append((text_start, text_end, _xml_text(write_text) if idx == 0 else "", fid))

    patched_xml = document_xml
    patched_fields: list[str] = []
    for start, end, replacement, fid in sorted(patches, key=lambda item: item[0], reverse=True):
        patched_xml = patched_xml[:start] + replacement + patched_xml[end:]
        patched_fields.append(fid)
    patched_xml = _unwrap_filled_content_controls(patched_xml, written_values)

    with zipfile.ZipFile(template_path, "r") as zin, zipfile.ZipFile(
        output_path,
        "w",
        compression=zipfile.ZIP_DEFLATED,
    ) as zout:
        for info in zin.infolist():
            data = patched_xml.encode("utf-8") if info.filename == "word/document.xml" else zin.read(info.filename)
            zout.writestr(info, data)

    after_counts = count_docx_structure(output_path)
    guard = build_structure_guard(before_counts, after_counts, errors, intentional_text_node_creations)
    structure_guard_report_path.write_text(json.dumps(guard, indent=2, sort_keys=True), encoding="utf-8")
    fill_audit: Mapping[str, Any] | None = None
    if guard["pass"] and output_path.is_file():
        fill_audit = audit_table_fill_completeness(
            output_path,
            table_fill_audit_manifest if table_fill_audit_manifest is not None else manifest,
            approval_map,
            strict_approval_coverage=strict_approval_coverage,
        )
    if not guard["pass"]:
        try:
            output_path.unlink()
        except FileNotFoundError:
            pass
    return PatchOutcome(
        output_docx=output_path.resolve(),
        structure_guard_report=structure_guard_report_path.resolve(),
        structure_guard_passed=bool(guard["pass"]),
        patched_fields=tuple(reversed(patched_fields)),
        errors=tuple(errors),
        table_fill_audit=fill_audit,
    )


def count_docx_structure(docx_path: Path) -> dict[str, int]:
    with zipfile.ZipFile(docx_path, "r") as z:
        document_xml = z.read("word/document.xml").decode("utf-8")
        names = z.namelist()
    return {
        "tables": len(re.findall(r"<w:tbl(?:\s|>)", document_xml)),
        "rows": len(re.findall(r"<w:tr(?:\s|>)", document_xml)),
        "cells": len(re.findall(r"<w:tc(?:\s|>)", document_xml)),
        "gridSpan": len(re.findall(r"<w:gridSpan(?:\s|/?>)", document_xml)),
        "vMerge": len(re.findall(r"<w:vMerge(?:\s|/?>)", document_xml)),
        "text_nodes": len(re.findall(r"<w:t(?:\s[^>]*)?>", document_xml)),
        "relationships": len([name for name in names if name.endswith(".rels")]),
        "styles": len([name for name in names if name == "word/styles.xml"]),
        "headers": len([name for name in names if name.startswith("word/header")]),
        "footers": len([name for name in names if name.startswith("word/footer")]),
    }


def build_structure_guard(
    before_counts: Mapping[str, int],
    after_counts: Mapping[str, int],
    errors: list[str],
    expected_text_node_delta: int = 0,
) -> dict[str, Any]:
    deltas = {key: int(after_counts.get(key, 0)) - int(before_counts.get(key, 0)) for key in before_counts}
    stable_keys = ("tables", "rows", "cells", "gridSpan", "vMerge", "relationships", "styles", "headers", "footers")
    stable = all(deltas.get(key, 0) == 0 for key in stable_keys)
    text_nodes_delta_matches_expected = deltas.get("text_nodes", 0) == expected_text_node_delta
    return {
        "pass": stable and text_nodes_delta_matches_expected and not errors,
        "before": dict(before_counts),
        "after": dict(after_counts),
        "deltas": deltas,
        "intentional_text_node_creations": expected_text_node_delta,
        "text_nodes_delta_expected": expected_text_node_delta,
        "text_nodes_delta_actual": deltas.get("text_nodes", 0),
        "text_nodes_delta_matches_expected": text_nodes_delta_matches_expected,
        "errors": list(errors),
    }


def _value_for_write(
    fid: str,
    value: str | None,
    *,
    value_present: bool,
    role: str,
    required: bool,
    confidence: float | None,
    low_confidence_threshold: float,
) -> str | None:
    if role == "notes":
        if value_present and value is not None and str(value).strip():
            return str(value)
        if required:
            return _review_text(fid, "missing required notes")
        return None
    if not value_present:
        return _review_text(fid, "missing required value") if required else None
    decision = decide_cell(
        value,
        confidence=confidence,
        threshold=low_confidence_threshold,
        required=required,
        conflict_detected=str(value).startswith(REVIEW_REQUIRED_TEXT),
        cell_role="target",
    )
    if decision == DecisionState.BLANK:
        return ""
    if decision != DecisionState.FILL:
        reason = "requires review"
        if value is None or str(value).strip() == "":
            reason = "missing required value"
        elif confidence is not None and confidence < low_confidence_threshold:
            reason = f"low confidence {confidence:.2f}"
        elif str(value).startswith(REVIEW_REQUIRED_TEXT):
            reason = str(value)
        return _review_text(fid, reason)
    return str(value)


def _approved_manifest_cells(
    manifest: Mapping[str, Any],
    approval_map: Mapping[str, Any] | None,
    errors: list[str],
    *,
    strict_coverage: bool = True,
) -> list[Mapping[str, Any]]:
    cells = list(manifest.get("cells") or _approval_fields(approval_map).values())
    if approval_map is None:
        return cells

    approved = _approval_fields(approval_map)
    out: list[Mapping[str, Any]] = []
    for spec in cells:
        fid = str(spec.get("field_id", ""))
        approval = approved.get(fid)
        if approval is None:
            if strict_coverage:
                errors.append(f"{fid}: field is not present in exact approval map")
            continue
        if _cell_coordinates(spec) != _cell_coordinates(approval):
            errors.append(
                f"{fid}: manifest target {_cell_coordinates(spec)} does not match exact approval map {_cell_coordinates(approval)}"
            )
            continue
        out.append({**dict(approval), **dict(spec)})
    return out


def _approval_fields(approval_map: Mapping[str, Any] | None) -> dict[str, Mapping[str, Any]]:
    if approval_map is None:
        return {}
    raw = approval_map.get("fields")
    if isinstance(raw, dict):
        return {str(field_id): spec for field_id, spec in raw.items() if isinstance(spec, Mapping)}
    if isinstance(raw, list):
        return {
            str(spec.get("field_id")): spec for spec in raw if isinstance(spec, Mapping) and spec.get("field_id")
        }

    legacy_cells = approval_map.get("cells")
    if isinstance(legacy_cells, dict):
        out: dict[str, Mapping[str, Any]] = {}
        for field_id, spec in legacy_cells.items():
            if not isinstance(spec, Mapping):
                continue
            fid = str(field_id)
            merged = dict(spec)
            merged.setdefault("field_id", fid)
            out[fid] = merged
        return out

    return {}


def _cell_coordinates(spec: Mapping[str, Any]) -> tuple[int, int, int]:
    return (int(spec["table_index"]), int(spec["row"]), int(spec["col"]))


def _find_elements(xml: str, tag: str) -> list[tuple[int, int]]:
    open_pat = re.compile(rf"<{re.escape(tag)}(?:\s[^>]*)?>")
    close_pat = re.compile(rf"</{re.escape(tag)}>")
    token_pat = re.compile(rf"<{re.escape(tag)}(?:\s[^>]*)?>|</{re.escape(tag)}>")
    ranges: list[tuple[int, int]] = []
    stack: list[int] = []
    for match in token_pat.finditer(xml):
        token = match.group(0)
        if open_pat.fullmatch(token):
            stack.append(match.start())
        elif close_pat.fullmatch(token) and stack:
            start = stack.pop()
            if not stack:
                ranges.append((start, match.end()))
    return ranges


def _cell_range_for_spec(xml: str, tables: list[tuple[int, int]], spec: Mapping[str, Any]) -> tuple[int, int]:
    table_index = int(spec["table_index"])
    row_index = int(spec["row"])
    visual_col = int(spec["col"])
    try:
        table_start, table_end = tables[table_index]
    except IndexError as exc:
        raise IndexError(f"table_index {table_index} not found") from exc
    rows = _find_elements(xml[table_start:table_end], "w:tr")
    try:
        row_start_rel, row_end_rel = rows[row_index]
    except IndexError as exc:
        raise IndexError(f"row {row_index} not found in table {table_index}") from exc
    row_start = table_start + row_start_rel
    row_end = table_start + row_end_rel
    cells = _find_elements(xml[row_start:row_end], "w:tc")
    col = 0
    for cell_start_rel, cell_end_rel in cells:
        cell_start = row_start + cell_start_rel
        cell_end = row_start + cell_end_rel
        span = _grid_span(xml[cell_start:cell_end])
        if col <= visual_col < col + span:
            return cell_start, cell_end
        col += span
    raise IndexError(f"visual col {visual_col} not found in table {table_index} row {row_index}")


def _grid_span(cell_xml: str) -> int:
    match = re.search(r"<w:gridSpan\b[^>]*\bw:val=\"([0-9]+)\"", cell_xml)
    if not match:
        return 1
    return max(1, int(match.group(1)))


def _text_ranges(xml: str, cell_start: int, cell_end: int) -> list[tuple[int, int]]:
    cell_xml = xml[cell_start:cell_end]
    matches = list(re.finditer(r"<w:t(?:\s[^>]*)?>(.*?)</w:t>", cell_xml, flags=re.DOTALL))
    if not matches:
        raise ValueError("target cell has no existing w:t text node")
    return [(cell_start + match.start(1), cell_start + match.end(1)) for match in matches]


def _unwrap_filled_content_controls(xml: str, written_values: set[str]) -> str:
    """Keep filled values as ordinary visible runs instead of placeholder SDTs."""

    def visible_text_from_sdt_content(content_xml: str) -> str:
        parts: list[str] = []
        for inner in re.finditer(r"<w:t(?:\s[^>]*)?>(.*?)</w:t>", content_xml, flags=re.DOTALL):
            raw = inner.group(1)
            raw = re.sub(r"<w:tab[^>]*/>", "\t", raw)
            parts.append(html.unescape(raw))
        return "".join(parts)

    plain_values = {str(value) for value in written_values if str(value).strip()}
    if not plain_values:
        return xml

    def replace(match: re.Match[str]) -> str:
        full_sdt = match.group(0)
        content = match.group(1)
        visible_plain = visible_text_from_sdt_content(content)
        if not visible_plain.strip():
            return full_sdt
        if not any(value in visible_plain for value in plain_values):
            return full_sdt
        return re.sub(r"<w:rStyle\b[^>]*\bw:val=\"PlaceholderText\"[^>]*/>", "", content)

    return re.sub(
        r"<w:sdt(?:\s[^>]*)?>.*?<w:sdtContent>(.*?)</w:sdtContent></w:sdt>",
        replace,
        xml,
        flags=re.DOTALL,
    )


def _paragraph_text_insert_at(xml: str, cell_start: int, cell_end: int) -> int:
    cell_xml = xml[cell_start:cell_end]
    paragraph = re.search(r"<w:p(?:\s[^>]*)?>", cell_xml)
    if not paragraph:
        raise ValueError("target cell has no paragraph for minimal w:t creation")
    close = re.search(r"</w:p>", cell_xml[paragraph.end() :])
    if not close:
        raise ValueError("target cell has no paragraph close for minimal w:t creation")
    return cell_start + paragraph.end() + close.start()


def _xml_text(value: str) -> str:
    return html.escape(str(value), quote=False)


def _append_after_label_text(existing_text: str, write_value: str) -> str:
    prefix = re.sub(r"\s+", " ", existing_text).strip()
    value = re.sub(r"\s+", " ", write_value).strip()
    if not prefix:
        return value
    if not value:
        return prefix
    if prefix.endswith((":", "：")):
        return f"{prefix} {value}"
    return f"{prefix}: {value}"


def _bool_from_spec(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    return str(value).strip().lower() in {"1", "true", "yes", "y", "required"}


def _cell_role(spec: Mapping[str, Any]) -> str:
    fid = str(spec.get("field_id", ""))
    role = str(spec.get("cell_role") or spec.get("role") or "target").strip().lower()
    if fid == "evidence_notes" or "note" in role:
        return "notes"
    return role or "target"


def _required_for_spec(spec: Mapping[str, Any], required_field_ids: set[str]) -> bool:
    fid = str(spec.get("field_id", ""))
    if fid in required_field_ids:
        return True
    if "required" in spec:
        return _bool_from_spec(spec.get("required"), default=False)
    return False


def _review_text(fid: str, reason: str) -> str:
    return f"{REVIEW_REQUIRED_TEXT}: {fid} {reason}".strip()
