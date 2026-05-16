"""Remove PDFs that are fully redundant with pages indexed from *_combined.pdf masters.

A candidate PDF is deleted only when every one of its pages matches a page
fingerprint from the combined corpus (text hash prefix + grayscale pixmap hash).
"""
from __future__ import annotations

import os
import sys
import glob
import hashlib
import argparse
import fitz  # PyMuPDF


def get_page_fingerprint(page: fitz.Page) -> str:
    """
    Generates a unique identifier for a PDF page combining a text hash
    and a perceptual image hash (grayscale, 15% scale).
    """
    # 1. Text Hash (UTF-8 encode with replace to avoid errors on odd text)
    text = str(page.get_text() or "").strip().lower()
    text_hash = hashlib.sha256(text.encode('utf-8', errors='replace')).hexdigest()[:16]

    # 2. Image Hash (15% scale, grayscale, stable buffer with alpha=False)
    mat = fitz.Matrix(0.15, 0.15)
    pix = page.get_pixmap(matrix=mat, colorspace=fitz.csGRAY, alpha=False)
    img_hash = hashlib.sha256(pix.samples).hexdigest()

    return f"{text_hash}_{img_hash}"


def main():
    parser = argparse.ArgumentParser(description="Remove any PDFs that are 100% contained within *_combined.pdf files.")
    parser.add_argument("--folder", type=str, default=r".\inbox\inbox", help="Path to the inbox directory")
    parser.add_argument("--apply", action="store_true", help="Execute the deletion. If omitted, runs a dry-run.")
    args = parser.parse_args()

    inbox_path = os.path.abspath(args.folder)
    if not os.path.isdir(inbox_path):
        print(f"Error: Directory '{inbox_path}' not found.")
        sys.exit(1)

    # Find all PDFs in the directory (non-recursive)
    all_pdfs = glob.glob(os.path.join(inbox_path, "*.pdf"))

    # Corpus: Files that represent our "master" merged files
    corpus_files = [f for f in all_pdfs if "_combined" in os.path.basename(f).lower()]

    # Candidates: Everything else
    candidate_files = [f for f in all_pdfs if f not in corpus_files]

    print(f"Found {len(corpus_files)} combined master files.")
    print(f"Found {len(candidate_files)} potential subset candidates to check.\n")

    corpus_fingerprints = set()

    # Step 1: Index the corpus (combined files)
    print("Indexing master combined files...")
    for pdf_path in corpus_files:
        try:
            with fitz.open(pdf_path) as doc:
                for page in doc:
                    corpus_fingerprints.add(get_page_fingerprint(page))
        except Exception as e:
            print(f"  [!] Failed to read corpus file {os.path.basename(pdf_path)}: {e}")

    print(f"Indexed {len(corpus_fingerprints)} unique pages from combined documents.\n")

    # Step 2: Check candidates and queue for deletion
    to_delete = []
    print("Scanning candidates for full redundancy...")
    for pdf_path in candidate_files:
        try:
            with fitz.open(pdf_path) as doc:
                if len(doc) == 0:
                    continue  # Skip empty/corrupt PDFs

                is_fully_redundant = True

                # Check every page in the candidate
                for page in doc:
                    fp = get_page_fingerprint(page)
                    if fp not in corpus_fingerprints:
                        # We found a page that is NOT in the combined files!
                        # This file is not a 100% duplicate, so we keep it.
                        is_fully_redundant = False
                        break  # Stop checking this file, move to the next

                if is_fully_redundant:
                    to_delete.append((pdf_path, len(doc)))

        except Exception as e:
            print(f"  [!] Failed to read candidate file {os.path.basename(pdf_path)}: {e}")

    # Step 3: Execute Dry-Run or Apply Deletion
    print("-" * 50)
    if not to_delete:
        print("No fully redundant PDFs found. All remaining files contain unique pages.")
        return

    if args.apply:
        print(f"APPLYING DELETIONS ({len(to_delete)} files):")
        for pdf_path, page_count in to_delete:
            try:
                os.remove(pdf_path)
                print(f"  [DELETED] {os.path.basename(pdf_path)} (Matched all {page_count} pages)")
            except Exception as e:
                print(f"  [ERROR] Could not delete {os.path.basename(pdf_path)}: {e}")
    else:
        print(f"DRY RUN - The following {len(to_delete)} files WOULD be deleted:")
        for pdf_path, page_count in to_delete:
            print(f"  [MARKED] {os.path.basename(pdf_path)} (Matches all {page_count} pages in master files)")
        print("\nRun the script with --apply to permanently delete these files.")


if __name__ == "__main__":
    main()
