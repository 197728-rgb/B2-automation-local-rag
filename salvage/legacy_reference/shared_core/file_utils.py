from __future__ import annotations
from pathlib import Path
import hashlib
import json
import re
from typing import Iterable, Iterator, List
from PIL import Image
from pdf2image import convert_from_path
from pypdf import PdfReader

try:
    from pdfminer.high_level import extract_text as pdf_extract_text
except Exception:
    pdf_extract_text = None

def ensure_dir(path: str | Path) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p

def save_json(path: str | Path, data: dict) -> None:
    path = Path(path)
    ensure_dir(path.parent)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def slugify(name: str) -> str:
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("_")
    return name or "document"

def file_md5(path: str | Path) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def get_pdf_page_count(pdf_path: str | Path) -> int:
    reader = PdfReader(str(pdf_path))
    return len(reader.pages)

def extract_pdf_text_fast(pdf_path: str | Path) -> str:
    if pdf_extract_text is None:
        return ""
    try:
        return pdf_extract_text(str(pdf_path)) or ""
    except Exception:
        return ""

def pdf_has_meaningful_text(pdf_path: str | Path, threshold: int = 80) -> bool:
    text = extract_pdf_text_fast(pdf_path)
    alnum = sum(ch.isalnum() for ch in text)
    return alnum >= threshold

def adaptive_dpi_for_pdf(pdf_path: str | Path) -> int:
    text = extract_pdf_text_fast(pdf_path)
    text_len = len(text.strip())
    if text_len > 3000:
        return 200
    if text_len > 800:
        return 250
    return 300

def iter_pdf_image_chunks(pdf_path: str | Path, dpi: int, chunk_size: int = 5) -> Iterator[list[Image.Image]]:
    total = get_pdf_page_count(pdf_path)
    for start in range(1, total + 1, chunk_size):
        end = min(start + chunk_size - 1, total)
        images = convert_from_path(str(pdf_path), dpi=dpi, first_page=start, last_page=end)
        yield images

def normalize_ws(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()

def normalize_label(text: str) -> str:
    text = normalize_ws((text or "").replace("\n", " "))
    text = text.lower()
    text = re.sub(r"[^a-z0-9%/()#&+ -]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text
