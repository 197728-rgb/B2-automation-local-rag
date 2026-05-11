"""Command-line entrypoint for b2-automation."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from b2_automation import __version__
from b2_automation.demo import run_demo
from b2_automation.discover import run_discovery
from b2_automation.inbox_pipeline import run_inbox_pipeline
from b2_automation.local_extraction import ALLOWED_REVIEW_FORMS, DEFAULT_REVIEW_FORMS
from b2_automation.paths import resolve_project_root
from b2_automation.sample_pipeline import run_sample_pipeline


def _cmd_discover(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve() if args.root else resolve_project_root()
    if not (root / "templates").is_dir():
        print(
            f"error: no templates/ under {root}\n"
            "  Set B2_PROJECT_ROOT or run from the repo root after `pip install -e .`",
            file=sys.stderr,
        )
        return 2
    written = run_discovery(root=root)
    if not written:
        print(f"No .docx files in {root / 'templates'}")
        return 0
    for p in written:
        print(f"Wrote {p}")
    return 0


def _cmd_demo(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve() if args.root else resolve_project_root()
    docx_path, json_path = run_demo(root=root)
    print(f"Created DOCX: {docx_path}")
    print(f"Created review JSON: {json_path}")
    return 0


def _cmd_sample_pipeline(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve() if args.root else resolve_project_root()
    inp = Path(args.input).resolve() if args.input else root / "samples/docupipe/minimal_docupipe_response.json"
    out = Path(args.out).resolve() if args.out else root / "outputs/sample_from_docupipe.docx"
    if not inp.is_file():
        print(f"error: input JSON not found: {inp}", file=sys.stderr)
        return 2
    run_sample_pipeline(inp, out)
    print(f"Wrote {out}")
    return 0


def _cmd_inbox(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve() if args.root else resolve_project_root()
    inbox = Path(args.inbox).resolve()
    out = Path(args.out).resolve()
    try:
        result = run_inbox_pipeline(
            root=root,
            inbox=inbox,
            out_dir=out,
            low_confidence_threshold=float(args.low_confidence_threshold),
            review_forms=tuple(args.review_forms),
        )
    except ValueError as exc:
        valid = ", ".join(ALLOWED_REVIEW_FORMS)
        print(f"error: inbox pipeline failed: {exc}", file=sys.stderr)
        print(f"hint: valid --review-forms choices are: {valid}", file=sys.stderr)
        return 2
    except Exception as exc:  # noqa: BLE001 - CLI must return clean error
        print(f"error: inbox pipeline failed: {exc}", file=sys.stderr)
        return 2
    print(f"Status: {result.status}")
    print(f"Run manifest: {result.manifest_path}")
    print(f"Review JSON: {result.review_json_path}")
    print(f"Review MD: {result.review_md_path}")
    if result.filled_docx_path:
        print(f"Filled DOCX: {result.filled_docx_path}")
    return 0 if result.status in {"success", "review_required"} else 1


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="b2",
        description="B2-automation: local evidence review and safe B-2 DOCX preparation.",
    )
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = p.add_subparsers(dest="command", required=True)

    d = sub.add_parser("discover", help="Write outputs/*_table_map.txt for each templates/*.docx")
    d.add_argument("--root", type=str, default=None, help="Project root (default: auto-detect)")
    d.set_defaults(func=_cmd_discover)

    m = sub.add_parser("demo", help="Write sample DOCX + review JSON under outputs/")
    m.add_argument("--root", type=str, default=None, help="Project root (default: auto-detect)")
    m.set_defaults(func=_cmd_demo)

    sp = sub.add_parser("sample-pipeline", help="DocuPipe-style JSON fixture -> normalizer -> sample DOCX under outputs/")
    sp.add_argument("--root", type=str, default=None, help="Project root (default: auto-detect)")
    sp.add_argument("--input", type=str, default=None, help="Path to DocuPipe-style JSON")
    sp.add_argument("--out", type=str, default=None, help="Output DOCX path")
    sp.set_defaults(func=_cmd_sample_pipeline)

    ib = sub.add_parser("inbox", help="Run local evidence extraction/review for B24 RL2, B81, B89, B90, and Cover Page")
    ib.add_argument("--root", type=str, default=None, help="Project root (default: auto-detect)")
    ib.add_argument("--inbox", type=str, default="inbox", help="Folder containing local evidence files")
    ib.add_argument("--out", type=str, default="outputs/inbox_run", help="Output run folder")
    ib.add_argument("--low-confidence-threshold", type=float, default=0.70, help="Review threshold for extraction confidence")
    ib.add_argument(
        "--review-forms",
        nargs="+",
        default=list(DEFAULT_REVIEW_FORMS),
        help="First-class forms to review (default: B24_RL2 B81 B89 B90 Cover_Page).",
    )
    ib.set_defaults(func=_cmd_inbox)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
