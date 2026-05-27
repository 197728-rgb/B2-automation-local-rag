"""Outbox publisher for final PDF-only handoff files.

Contract:
- outbox contains final filled B-2 PDFs only.
- logs contain JSON/MD/DOCX/internal audit artifacts.
- errors contain runtime failures.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Iterable


def reset_outbox(outbox_dir: Path) -> None:
    """Clear the visible handoff outbox for the current run."""
    outbox_dir.mkdir(parents=True, exist_ok=True)
    for child in outbox_dir.iterdir():
        if child.is_file() or child.is_symlink():
            child.unlink(missing_ok=True)
        elif child.is_dir():
            shutil.rmtree(child)


def export_docx_to_pdf(docx_path: Path, pdf_path: Path) -> Path:
    """Export a DOCX to PDF using the best local converter.

    LibreOffice/soffice is preferred for headless environments. On Windows,
    Microsoft Word COM is used as a fallback when LibreOffice is unavailable.
    Raises RuntimeError if no converter is available or the PDF is not produced.
    """
    docx_path = docx_path.resolve()
    pdf_path = pdf_path.resolve()
    if not docx_path.exists():
        raise FileNotFoundError(f"DOCX not found for PDF export: {docx_path}")
    pdf_path.parent.mkdir(parents=True, exist_ok=True)

    exe = shutil.which("soffice") or shutil.which("libreoffice")
    if exe is not None:
        _export_docx_to_pdf_with_libreoffice(exe, docx_path, pdf_path)
    elif os.name == "nt":
        _export_docx_to_pdf_with_word(docx_path, pdf_path)
    else:
        raise RuntimeError(
            "No DOCX to PDF converter available. Install LibreOffice/soffice "
            "or run on Windows with Microsoft Word available."
        )

    if not pdf_path.exists() or pdf_path.stat().st_size == 0:
        raise RuntimeError(f"PDF export did not create a usable file: {pdf_path}")
    return pdf_path


def _export_docx_to_pdf_with_libreoffice(exe: str, docx_path: Path, pdf_path: Path) -> None:
    with tempfile.TemporaryDirectory(prefix="b2_sentinel_pdf_") as tmp:
        tmp_dir = Path(tmp)
        cmd = [
            exe,
            "--headless",
            "--convert-to",
            "pdf",
            "--outdir",
            str(tmp_dir),
            str(docx_path),
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        produced = tmp_dir / f"{docx_path.stem}.pdf"
        if proc.returncode != 0 or not produced.exists() or produced.stat().st_size == 0:
            raise RuntimeError(
                "DOCX to PDF export failed: "
                f"returncode={proc.returncode}; stdout={proc.stdout.strip()}; stderr={proc.stderr.strip()}"
            )
        shutil.copy2(produced, pdf_path)


def _export_docx_to_pdf_with_word(docx_path: Path, pdf_path: Path) -> None:
    try:
        import pythoncom  # type: ignore
        import win32com.client  # type: ignore
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(
            "Microsoft Word PDF export requires pywin32 when LibreOffice/soffice is unavailable"
        ) from exc

    word = None
    doc = None
    try:
        pythoncom.CoInitialize()
        word = win32com.client.DispatchEx("Word.Application")
        word.Visible = False
        word.DisplayAlerts = 0
        doc = word.Documents.Open(
            str(docx_path),
            ConfirmConversions=False,
            ReadOnly=True,
            AddToRecentFiles=False,
            Visible=False,
        )
        doc.ExportAsFixedFormat(
            OutputFileName=str(pdf_path),
            ExportFormat=17,  # wdExportFormatPDF
            OpenAfterExport=False,
        )
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"Microsoft Word DOCX to PDF export failed: {exc}") from exc
    finally:
        if doc is not None:
            try:
                doc.Close(False)
            except Exception:
                pass
        if word is not None:
            try:
                word.Quit()
            except Exception:
                pass
        try:
            pythoncom.CoUninitialize()
        except Exception:
            pass


def merge_pdfs(pdf_paths: Iterable[Path], output_path: Path) -> Path:
    """Merge PDFs into a single final packet using PyMuPDF."""
    paths = [p.resolve() for p in pdf_paths]
    if not paths:
        raise ValueError("No PDFs supplied for packet merge")
    for path in paths:
        if not path.exists() or path.stat().st_size == 0:
            raise FileNotFoundError(f"Cannot merge missing/empty PDF: {path}")

    try:
        import fitz  # PyMuPDF
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError("PyMuPDF is required to merge final B-2 packet PDFs") from exc

    output_path = output_path.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    merged = fitz.open()
    try:
        for path in paths:
            with fitz.open(str(path)) as src:
                merged.insert_pdf(src)
        merged.save(str(output_path))
    finally:
        merged.close()

    if not output_path.exists() or output_path.stat().st_size == 0:
        raise RuntimeError(f"Merged packet PDF was not created: {output_path}")
    return output_path


def write_error_artifact(errors_dir: Path, run_id: str, form_id: str, message: str) -> Path:
    """Write runtime failures away from outbox/logs."""
    target = errors_dir / run_id / form_id / "error.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps({"run_id": run_id, "form_id": form_id, "error": message}, indent=2),
        encoding="utf-8",
    )
    return target
