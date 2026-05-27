"""Value-type sanity gate.

Before allowing a FILL, check that the extracted value is plausible for the
field's expected type. A 50-word paragraph is not a valid car mark, a size
measurement, or a date.

The gate infers expected value characteristics from field_id naming conventions
since FieldNode doesn't carry an explicit value_type.
"""
from __future__ import annotations

import re

_MAX_SHORT_STRING = 60
_MAX_MEDIUM_STRING = 120

_DATE_FIELDS = re.compile(
    r"date|_date$|^date_", re.I
)
_NUMERIC_FIELDS = re.compile(
    r"size|thickness|diameter|length|width|height|weight|capacity|pressure|"
    r"number$|_number$|\.number$|count|quantity|gauge", re.I
)
_ID_FIELDS = re.compile(
    r"\.id$|_id$|^id\.|\.mark$|\.code$|stencil|spec$|revision$|drawing", re.I
)
_NAME_FIELDS = re.compile(
    r"\.name$|_name$|^name\.", re.I
)

_SENTENCE_INDICATORS = re.compile(
    r"\b(paragraph|section|shall|must|required|pursuant|accordance|"
    r"demonstration|regarding|appendix)\b", re.I
)
_EMBEDDED_LABEL_RE = re.compile(r"\b\d+\.\s+[A-Za-z][A-Za-z0-9 /#&().\-]{2,60}:\s*")
_DATE_VALUE_RE = re.compile(
    r"^\s*(?:\d{1,2}/\d{1,2}/\d{2,4}|\d{4}-\d{2}-\d{2})(?:\s+\d{1,2}:\d{2}(?:\s*[AP]M)?)?\s*$",
    re.I,
)


def is_value_plausible(field_id: str, value: str) -> bool:
    """Return True if the value shape is plausible for this field type.

    Returns False (fails sanity) when the value looks like regulatory
    boilerplate or a paragraph rather than a concrete field value.
    """
    if not value:
        return True

    vlen = len(value)
    if _EMBEDDED_LABEL_RE.search(value):
        return False

    if _DATE_FIELDS.search(field_id):
        return vlen <= _MAX_SHORT_STRING and bool(_DATE_VALUE_RE.match(value))

    if _NUMERIC_FIELDS.search(field_id):
        return vlen <= _MAX_SHORT_STRING and bool(re.search(r"\d", value))

    if _ID_FIELDS.search(field_id):
        return vlen <= _MAX_SHORT_STRING

    if _NAME_FIELDS.search(field_id):
        return vlen <= _MAX_SHORT_STRING

    # For any field: if the value exceeds medium length AND contains
    # regulatory/boilerplate language, it's almost certainly extraction noise.
    if vlen > _MAX_MEDIUM_STRING and _SENTENCE_INDICATORS.search(value):
        return False

    # General length cap for any compliance field — real values are concise.
    if vlen > _MAX_MEDIUM_STRING:
        return False

    return True
