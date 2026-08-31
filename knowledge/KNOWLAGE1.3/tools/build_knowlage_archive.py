#!/usr/bin/env python3
"""Build KNOWLAGE1.3.zip and regenerate its manifests.

Packs the knowledge documents, the project source snapshot, the git-history snapshot,
and the retained memory snapshots into a single archive, then writes MANIFEST.md and
PACK_MANIFEST.json from what was actually packed.

Usage:
    python tools/build_knowlage_archive.py [--repo PATH] [--out PATH] [--skip-source]

The pack directory is inferred from this file's location, so the script can be run from
anywhere.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import zipfile
from datetime import date
from pathlib import Path

PACK_ROOT = Path(__file__).resolve().parent.parent
PACK_NAME = PACK_ROOT.name
VERSION = "1.3"

# The source snapshot is built from git-tracked files only, so everything .gitignore
# already keeps out of the repository -- .env, inputs/, outputs/, .venv/, caches -- is
# excluded by construction rather than by a hand-maintained list that drifts.
# These two sets remove what git DOES track but permanent knowledge must not hold.

# Build state and dependency trees: reproducible from source, useless as knowledge.
EXCLUDED_DIRS = {"node_modules", "__pycache__", "knowledge"}
EXCLUDED_SUFFIXES = {".pyc", ".pyo"}

# Completed forms and evidence-shaped fixtures. The pack's permanent-knowledge boundary
# bars completed facility forms, facility names, and personnel records; a test fixture is
# still a completed form once the archive is loaded as reference material.
EVIDENCE_EXCLUSION_GLOBS = (
    "**/FILLED_*",                                   # completed B-2 forms + validation reports
    "tests/fixtures/dlga_*",                         # TCO name, approver, PITP id, dates
    "**/test-data/sources/*",                        # facility profile, personnel roster
)

# Enforcement for the boundary claim in README.md and KNOWLEDGE_SOURCES_INDEX.md.
# Scanned over data files in the staged snapshot; a hit aborts the build.
#
# Scope note: .py files are deliberately not scanned. Reporting marks appear there as
# regex alternations and illustrative docstrings (industry-wide marks, not facility
# records), so scanning them would fail the build on legitimate source.
EVIDENCE_SCAN_SUFFIXES = {".json", ".txt", ".md", ".csv", ".docx", ".xlsx", ".pdf"}
EVIDENCE_MARKERS = (
    # Completed-form naming. Case-sensitive: the fixtures use FILLED_, while prose about
    # a "filled_templates/" output folder is not a completed form.
    re.compile(r"\bFILLED_"),
    re.compile(r"\bMidwest Tank Rail\b", re.I),
    re.compile(r"\bFacility Name:", re.I),
    # A car mark is a reporting mark followed by a car number. Requiring digits keeps
    # schema identifiers such as "PAWCT-B24" from reading as equipment records.
    re.compile(r"\b(?:PAWCT|DBUX|GATX|UTLX|SHPX|TILX|UTBC)\s+\d{3,6}\b"),
)


# Knowledge documents, in the order they appear in MANIFEST.md.
KNOWLEDGE_DOCS = [
    "README.md",
    "SESSION_SUMMARY.md",
    "ERROR_LEDGER.md",
    "HARD_LESSONS.md",
    "DURABLE_FIXES.md",
    "FAILED_ASSUMPTIONS.md",
    "DO_NOT_REPEAT.md",
    "ENGAGEMENT_LESSONS_SUGGESTION.md",
    "AAR_AUDIT_REPORT_PLAYBOOK.md",
    "FIELD_AUTHORITY_AND_COMPLETENESS.md",
    "VALIDATION_AND_REGRESSION.md",
    "KNOWLEDGE_SOURCES_INDEX.md",
    "GOOGLE_DRIVE_UPDATE_SUGGESTIONS.md",
    "CHANGELOG_FROM_KNOWLAGE_1_2.md",
    "FUTURE_AGENT_NOTES.md",
]


def is_excluded(path: Path) -> bool:
    """Build state that never belongs in the pack, wherever it appears."""
    for part in path.parts:
        if part in EXCLUDED_DIRS:
            return True
    return path.suffix in EXCLUDED_SUFFIXES


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def is_evidence(rel: Path) -> bool:
    """Completed forms and evidence-shaped fixtures, barred by the pack's boundary."""
    return any(rel.match(pattern) for pattern in EVIDENCE_EXCLUSION_GLOBS)


def tracked_files(repo: Path) -> list[Path]:
    """Git-tracked paths only, so .gitignore decides what is local state.

    This is what keeps .env, inputs/, and outputs/ out of the snapshot: they are ignored
    by the repository, so git never lists them and the walk never sees them.
    """
    result = subprocess.run(
        ["git", "ls-files", "-z"], cwd=repo, capture_output=True, text=True, check=True
    )
    return [Path(name) for name in result.stdout.split("\0") if name]


def scan_for_evidence(root: Path) -> list[str]:
    """Check the staged snapshot against the boundary claim. Returns offending paths."""
    generated = {root / "MANIFEST.md", root / "PACK_MANIFEST.json"}
    hits = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in EVIDENCE_SCAN_SUFFIXES:
            continue
        if path in generated:
            continue
        rel = path.relative_to(root)
        if any(marker.search(path.name) for marker in EVIDENCE_MARKERS):
            hits.append(f"{rel} (filename)")
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for marker in EVIDENCE_MARKERS:
            found = marker.search(text)
            if found:
                hits.append(f"{rel} (contains {found.group(0)!r})")
                break
    return hits


def snapshot_source(repo: Path, dest: Path) -> tuple[int, int]:
    """Copy git-tracked project source, minus build state and evidence-shaped files."""
    if dest.exists():
        shutil.rmtree(dest)
    copied = skipped = 0
    for rel in tracked_files(repo):
        if is_excluded(rel):
            continue
        if is_evidence(rel):
            skipped += 1
            continue
        src = repo / rel
        if not src.is_file():
            continue
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, target)
        copied += 1
    return copied, skipped


def snapshot_git_history(repo: Path, dest: Path) -> None:
    """Record commit history and branch state as text."""
    dest.mkdir(parents=True, exist_ok=True)
    commands = {
        "commit-log.txt": ["git", "log", "--pretty=format:%h %ad %an%n    %s", "--date=short"],
        "branches.txt": ["git", "branch", "-a", "-v"],
        "head.txt": ["git", "rev-parse", "HEAD"],
        "file-count.txt": ["git", "ls-files"],
    }
    for filename, command in commands.items():
        try:
            output = subprocess.run(
                command, cwd=repo, capture_output=True, text=True, check=True
            ).stdout
        except (subprocess.CalledProcessError, FileNotFoundError) as exc:
            output = f"(unavailable: {exc})\n"
        if filename == "file-count.txt":
            # The tracked-file listing names the fixtures the snapshot excludes; drop
            # those lines so the listing describes what the pack actually carries.
            output = "\n".join(
                line for line in output.splitlines() if not is_evidence(Path(line))
            ) + "\n"
        (dest / filename).write_text(output, encoding="utf-8")


def packed_files(root: Path) -> list[Path]:
    """Every file to be packed, manifests excluded (they describe the rest)."""
    manifests = {root / "MANIFEST.md", root / "PACK_MANIFEST.json"}
    return sorted(
        path
        for path in root.rglob("*")
        if path.is_file() and path not in manifests and not is_excluded(path.relative_to(root))
    )


def write_manifests(root: Path, files: list[Path]) -> None:
    records = [
        {
            "file": str(path.relative_to(root)).replace("\\", "/"),
            "bytes": path.stat().st_size,
            "sha256": sha256_of(path),
        }
        for path in files
    ]
    by_name = {record["file"]: record for record in records}

    total_bytes = sum(record["bytes"] for record in records)
    lines = [
        f"# Manifest — {PACK_NAME}",
        "",
        "Generated by `tools/build_knowlage_archive.py`. Do not hand-edit.",
        "",
        f"Version: {VERSION} · Built: {date.today().isoformat()} · "
        f"Files: {len(records)} · Bytes: {total_bytes:,}",
        "",
        "## Knowledge documents",
        "",
        "| File | Bytes | SHA-256 |",
        "|---|---:|---|",
    ]
    missing = [name for name in KNOWLEDGE_DOCS if name not in by_name]
    if missing:
        raise SystemExit(
            "refusing to build: required knowledge documents are missing from the pack: "
            + ", ".join(missing)
            + "\nThe pack's governing contents are not optional; a partial instruction set "
            "must not ship with a valid-looking manifest."
        )
    for name in KNOWLEDGE_DOCS:
        record = by_name[name]
        lines.append(f"| `{name}` | {record['bytes']} | `{record['sha256']}` |")

    listed = set(KNOWLEDGE_DOCS)
    others = [r for r in records if r["file"] not in listed]
    top_level = [r for r in others if "/" not in r["file"]]
    memory = [r for r in others if r["file"].startswith("memory/")]
    tools = [r for r in others if r["file"].startswith("tools/")]
    source = [r for r in others if r["file"].startswith("source/")]

    for title, group in (
        ("Other top-level files", top_level),
        ("Retained memory", memory),
        ("Build tooling", tools),
    ):
        if not group:
            continue
        lines += ["", f"## {title}", "", "| File | Bytes | SHA-256 |", "|---|---:|---|"]
        lines += [f"| `{r['file']}` | {r['bytes']} | `{r['sha256']}` |" for r in group]

    if source:
        source_bytes = sum(r["bytes"] for r in source)
        lines += [
            "",
            "## Source snapshot",
            "",
            f"`source/` holds {len(source)} files, {source_bytes:,} bytes. "
            "Per-file hashes are in `PACK_MANIFEST.json`.",
        ]

    lines.append("")
    (root / "MANIFEST.md").write_text("\n".join(lines), encoding="utf-8")

    (root / "PACK_MANIFEST.json").write_text(
        json.dumps(
            {
                "package": PACK_NAME,
                "version": VERSION,
                "built": date.today().isoformat(),
                "purpose": "repeatable AAR B-2 / QAPE audit method knowledge, with project source and memory snapshots",
                "file_count": len(records),
                "total_bytes": total_bytes,
                "files": records,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def build_zip(root: Path, out_path: Path) -> None:
    files = packed_files(root) + [root / "MANIFEST.md", root / "PACK_MANIFEST.json"]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(set(files)):
            archive.write(path, f"{PACK_NAME}/{path.relative_to(root)}")


def looks_like_checkout(path: Path) -> bool:
    """A real project checkout, not an extraction directory."""
    return (path / ".git").exists() and (path / "pyproject.toml").is_file()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=None,
                        help="Project repository root to snapshot (default: the checkout "
                             "containing this pack, when there is one)")
    parser.add_argument("--out", type=Path, default=PACK_ROOT.parent / f"KNOWLAGE{VERSION}.zip",
                        help="Archive path to write")
    parser.add_argument("--skip-source", action="store_true",
                        help="Reuse the existing source snapshot instead of re-copying")
    args = parser.parse_args()

    # Resolve the repository before touching anything. Run from an extracted archive
    # rather than a checkout, the old default pointed at the extraction directory --
    # which would delete the bundled snapshot and then pack unrelated files in its place.
    repo = args.repo
    if repo is None:
        candidate = PACK_ROOT.parent.parent
        if looks_like_checkout(candidate):
            repo = candidate

    if not args.skip_source:
        if repo is None:
            raise SystemExit(
                "refusing to build: no project checkout found at "
                f"{PACK_ROOT.parent.parent}.\n"
                "This pack appears to be running outside its repository (an extracted "
                "archive, for example). Pass --repo PATH to point at a checkout, or "
                "--skip-source to keep the bundled source/ snapshot as it is."
            )
        if not looks_like_checkout(repo):
            raise SystemExit(f"refusing to build: {repo} is not a project checkout")
        copied, skipped = snapshot_source(repo, PACK_ROOT / "source" / "repo")
        snapshot_git_history(repo, PACK_ROOT / "source" / "git-history")
        print(f"source snapshot: {copied} tracked files from {repo} "
              f"({skipped} evidence-bearing files excluded)")

    # Enforce the boundary claim instead of asserting it.
    hits = scan_for_evidence(PACK_ROOT)
    if hits:
        listed = "\n  ".join(hits[:20])
        more = f"\n  ... and {len(hits) - 20} more" if len(hits) > 20 else ""
        raise SystemExit(
            "refusing to build: evidence-bearing content found in the pack.\n"
            "The permanent-knowledge boundary bars completed forms, facility names, and "
            "personnel records; loading this archive into a later audit would be the "
            f"contamination path the pack exists to stop.\n  {listed}{more}"
        )
    print("evidence scan: clean")

    files = packed_files(PACK_ROOT)
    write_manifests(PACK_ROOT, files)
    build_zip(PACK_ROOT, args.out)
    print(f"manifests: {len(files)} files hashed")
    print(f"archive:   {args.out} ({args.out.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
