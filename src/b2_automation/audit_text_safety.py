"""Defensive text normalization for mixed PDF/DOCX/OCR audit workflows.

Environment assumptions (Windows + Office 365 + Acrobat + VM):
- Word merge-cell OOXML is fragile; never rewrite table geometry here.
- OCR and PDF export may inject hidden Unicode and misaligned column text.
- Normalization is for validation/comparison only unless explicitly applied
  in ``safe_text_patch_only`` mode (``w:t`` content patches elsewhere).
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Iterable

# Zero-width / BOM / soft hyphen / replacement / common OCR noise
_HIDDEN_UNICODE_RE = re.compile(
    r"[\u200b-\u200f\u202a-\u202e\u2060-\u2064\ufeff\u00ad\ufffd"
    r"\u0080-\u009f"
    r"]+"
)
# Isolated OCR garbage symbols often seen in tank-car audit packets
_OCR_GARBAGE_RE = re.compile(
    r"[\u2610\u2611\u2612\u2713\u2717\u25a1\u25a0]|(?:\?\?\?+)|(?:�{2,})"
)
# Malformed Unicode line/paragraph separators mistaken for field delimiters
_MALFORMED_SEPARATORS_RE = re.compile(r"[\u2028\u2029\u0085]+")
# Control chars except tab/newline/carriage return
_CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")

_DATE_TOKEN_RE = re.compile(
    r"\b(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}-\d{2}-\d{2})\b"
)
_PIPE_DELIM_RE = re.compile(r"\s*\|\s*")


@dataclass(frozen=True)
class NormalizationNote:
    code: str
    detail: str
    before_preview: str = ""
    after_preview: str = ""


@dataclass
class NormalizedText:
    original: str
    text: str
    notes: list[NormalizationNote] = field(default_factory=list)

    @property
    def changed(self) -> bool:
        return self.text != self.original


def strip_hidden_unicode(text: str) -> tuple[str, list[NormalizationNote]]:
    notes: list[NormalizationNote] = []
    out = str(text or "")
    for label, pattern in (
        ("hidden_unicode", _HIDDEN_UNICODE_RE),
        ("ocr_garbage", _OCR_GARBAGE_RE),
        ("malformed_separator", _MALFORMED_SEPARATORS_RE),
        ("control_char", _CONTROL_CHARS_RE),
    ):
        if pattern.search(out):
            cleaned = pattern.sub("", out)
            if cleaned != out:
                notes.append(
                    NormalizationNote(
                        code=label,
                        detail=f"Removed {label} characters",
                        before_preview=out[:80],
                        after_preview=cleaned[:80],
                    )
                )
                out = cleaned
    return out, notes


def normalize_whitespace_safe(text: str, *, preserve_line_breaks: bool = True) -> tuple[str, list[NormalizationNote]]:
    notes: list[NormalizationNote] = []
    out = str(text or "")
    out = out.replace("\u00a0", " ")
    out = out.replace("\r\n", "\n").replace("\r", "\n")
    if preserve_line_breaks:
        lines = out.split("\n")
        collapsed = [re.sub(r"[ \t]{2,}", " ", line).strip() for line in lines]
        out = "\n".join(collapsed)
        out = re.sub(r"\n{3,}", "\n\n", out)
    else:
        out = re.sub(r"\s+", " ", out)
    out = out.strip()
    if out != str(text or "").strip():
        notes.append(NormalizationNote(code="whitespace", detail="Collapsed duplicate whitespace safely"))
    return out, notes


def normalize_cell_text(text: str, *, preserve_line_breaks: bool = True) -> NormalizedText:
    original = str(text or "")
    notes: list[NormalizationNote] = []
    current = original
    current, n1 = strip_hidden_unicode(current)
    notes.extend(n1)
    current, n2 = normalize_whitespace_safe(current, preserve_line_breaks=preserve_line_breaks)
    notes.extend(n2)
    # NFC for stable comparisons (does not change visible meaning for Latin scripts)
    nfc = unicodedata.normalize("NFC", current)
    if nfc != current:
        notes.append(NormalizationNote(code="unicode_nfc", detail="Applied Unicode NFC normalization"))
        current = nfc
    return NormalizedText(original=original, text=current, notes=notes)


def split_pipe_delimited_values(text: str) -> list[str]:
    """Split OCR/table-export pipe clusters without treating layout as structure."""
    if "|" not in text:
        return [text.strip()] if text.strip() else []
    return [part.strip() for part in _PIPE_DELIM_RE.split(text) if part.strip()]


def count_date_tokens(text: str) -> int:
    return len(_DATE_TOKEN_RE.findall(text or ""))


def looks_like_equipment_calibration_row(headers: Iterable[str]) -> bool:
    joined = " ".join(h.lower() for h in headers)
    return (
        "equipment" in joined or "calibration" in joined or "measure" in joined
    ) and ("id" in joined or "date" in joined or "due" in joined)


def notes_to_dicts(notes: Iterable[NormalizationNote]) -> list[dict[str, str]]:
    return [
        {"code": n.code, "detail": n.detail, "before_preview": n.before_preview, "after_preview": n.after_preview}
        for n in notes
    ]
