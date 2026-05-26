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
from b2_automation.autonomous_pipeline import run_autonomous_pipeline
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
    paths = result.filled_docx_paths
    if paths:
        if len(paths) == 1:
            print(f"Filled DOCX (1 this run): {paths[0]}")
        else:
            print(f"Filled DOCX ({len(paths)} this run):")
            for p in paths:
                print(f"  {p}")
    else:
        print("Filled DOCX: none produced this run.")
        if result.status == "review_required":
            print(
                "hint: review_required - evidence did not reach safe FILL for every required field; "
                "scoped *_filled.docx from earlier runs were cleared before this run."
            )
    return 0 if result.status in {"success", "review_required"} else 1


def _cmd_validate_audit(args: argparse.Namespace) -> int:
    from b2_automation.audit_validation import validate_audit_docx, write_validation_summary

    docx = Path(args.docx).resolve()
    if not docx.is_file():
        print(f"error: DOCX not found: {docx}", file=sys.stderr)
        return 2
    root = Path(args.root).resolve() if args.root else resolve_project_root()
    ref = Path(args.reference_template).resolve() if args.reference_template else None
    before = Path(args.before).resolve() if args.before else None
    out_json = Path(args.out_json).resolve() if args.out_json else docx.with_suffix(".validation.json")
    out_md = Path(args.out_md).resolve() if args.out_md else docx.with_suffix(".validation.md")
    report = validate_audit_docx(
        docx,
        form_id=args.form_id,
        project_root=root,
        reference_template=ref,
        before_patch_path=before,
        safe_text_patch_only=True,
    )
    write_validation_summary(report, json_path=out_json, md_path=out_md)
    summary = report.summary_dict()
    print(f"Validation JSON: {out_json}")
    print(f"Validation MD: {out_md}")
    print(f"Pass: {summary.get('pass')}")
    print(
        "Counts: "
        f"boundary={summary.get('cell_boundary_issues')} "
        f"dates={summary.get('date_format_issues')} "
        f"drift={summary.get('fingerprint_drift_tables')} "
        f"layout={summary.get('layout_integrity_warnings')}"
    )
    return 0 if summary.get("pass") else 1


def _cmd_fingerprint_template(args: argparse.Namespace) -> int:
    from b2_automation.table_fingerprint import write_fingerprint_schema

    docx = Path(args.docx).resolve()
    if not docx.is_file():
        print(f"error: DOCX not found: {docx}", file=sys.stderr)
        return 2
    root = Path(args.root).resolve() if args.root else resolve_project_root()
    out = root / "schemas" / "fingerprints" / f"{args.form_id}.json"
    write_fingerprint_schema(docx, args.form_id, out)
    print(f"Wrote fingerprint schema: {out}")
    return 0


def _cmd_run_autonomous(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve() if args.root else resolve_project_root()
    inbox = Path(args.inbox).resolve()
    out = Path(args.out).resolve()
    if not inbox.is_dir():
        print(f"error: inbox not found: {inbox}", file=sys.stderr)
        return 2
    try:
        result = run_autonomous_pipeline(
            root=root,
            inbox=inbox,
            out_dir=out,
            templates=tuple(args.templates) if args.templates else None,
            use_llm_analyst=not args.no_llm,
            persist_sqlite=not args.no_sqlite,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"error: autonomous pipeline failed: {exc}", file=sys.stderr)
        return 2
    print(f"Status: {result.status}")
    print(f"Run manifest: {result.manifest_path}")
    print(f"Fields processed: {result.field_count}")
    if result.completed_forms:
        print(f"Completed DOCX ({len(result.completed_forms)}):")
        for p in result.completed_forms:
            print(f"  {p}")
    return 0 if result.status in {"completed", "completed_with_warnings"} else 1


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

    ra = sub.add_parser(
        "run-autonomous",
        help="SPEC-1 autonomous pipeline: analyzeDocxForm -> gatherEvidence -> synthesizeAnswer -> validateAnswer -> writeCompletedDocx",
    )
    ra.add_argument("--root", type=str, default=None, help="Project root (default: auto-detect)")
    ra.add_argument("--inbox", type=str, default="inbox", help="Source evidence folder")
    ra.add_argument("--out", type=str, default="outputs/autonomous_run", help="Output run folder")
    ra.add_argument(
        "--templates",
        nargs="+",
        default=None,
        help="Form IDs to process (default: B24_RL2 B81 B89 B90 Cover_Page)",
    )
    ra.add_argument("--no-llm", action="store_true", help="Analyst uses deterministic structure only (no Gemini)")
    ra.add_argument("--no-sqlite", action="store_true", help="Skip SQLite run store")
    ra.set_defaults(func=_cmd_run_autonomous)

    va = sub.add_parser(
        "validate-audit",
        help="Defensive validation for filled Exhibit B-2 DOCX (normalization, fingerprints, boundaries; no geometry repair)",
    )
    va.add_argument("docx", type=str, help="Path to filled or source DOCX")
    va.add_argument("--form-id", type=str, default=None, help="Form id (e.g. B89, Cover_Page); inferred from filename if omitted")
    va.add_argument("--root", type=str, default=None, help="Project root for schemas/fingerprints (default: auto-detect)")
    va.add_argument("--reference-template", type=str, default=None, help="Blank template DOCX for fingerprint comparison")
    va.add_argument("--before", type=str, default=None, help="Pre-patch DOCX for safe_text_patch_only structure guard")
    va.add_argument("--out-json", type=str, default=None, help="Write validation JSON (default: alongside DOCX)")
    va.add_argument("--out-md", type=str, default=None, help="Write validation Markdown summary")
    va.set_defaults(func=_cmd_validate_audit)

    fg = sub.add_parser(
        "fingerprint-template",
        help="Generate schemas/fingerprints/{form_id}.json from a reference template DOCX",
    )
    fg.add_argument("docx", type=str, help="Reference template DOCX")
    fg.add_argument("--form-id", type=str, required=True, help="Form id for fingerprint schema")
    fg.add_argument("--root", type=str, default=None, help="Project root (default: auto-detect)")
    fg.set_defaults(func=_cmd_fingerprint_template)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
