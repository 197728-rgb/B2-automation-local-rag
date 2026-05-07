"""Verify m1002_template_registry.json structure and (optional) files on disk."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _validate_registry_payload(data: dict) -> list[str]:
    errs: list[str] = []
    templates = data.get("templates")
    if not isinstance(templates, dict) or not templates:
        errs.append("templates must be a non-empty object")
        return errs
    legacy = data.get("legacy_to_registry") or {}
    if not isinstance(legacy, dict):
        errs.append("legacy_to_registry must be an object")
    seen_names: set[str] = set()
    for k, fn in templates.items():
        if not isinstance(fn, str) or not fn.endswith(".docx"):
            errs.append(f"bad template value for {k!r}")
        if fn in seen_names:
            errs.append(f"duplicate filename: {fn}")
        seen_names.add(fn)
    for lk, vk in legacy.items():
        if vk not in templates:
            errs.append(f"legacy {lk!r} -> {vk!r} but key not in templates")
    dk = data.get("default_registry_key")
    if dk and dk not in templates:
        errs.append(f"default_registry_key {dk!r} not in templates")
    return errs


def main() -> int:
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--json-only",
        action="store_true",
        help="Only validate registry JSON (no disk); use when OneDrive path is offline here",
    )
    args = ap.parse_args()

    reg_path = ROOT / "config" / "m1002_template_registry.json"
    data = json.loads(reg_path.read_text(encoding="utf-8"))
    templates: dict[str, str] = data["templates"]

    struct_errs = _validate_registry_payload(data)
    if struct_errs:
        for e in struct_errs:
            print("STRUCT", e)
        return 1
    print(f"registry JSON OK: {len(templates)} templates, legacy keys: {len(data.get('legacy_to_registry') or {})}")

    if args.json_only:
        from shared_core.template_registry import clear_registry_cache, resolve_form_code

        clear_registry_cache()
        for legacy in ("C5V", "C5I", "C7_C8_C10", "B89"):
            print(f"resolve {legacy} -> {resolve_form_code(legacy)}")
        return 0

    from shared_core.config import get_forms_dir, load_config
    from shared_core.template_registry import clear_registry_cache, resolve_form_code

    clear_registry_cache()
    cfg = load_config(None)
    forms_dir = get_forms_dir(cfg)

    print(f"forms_dir: {forms_dir}")
    if not forms_dir.is_dir():
        print("WARN: forms_dir is not a directory (set B2_FORMS_DIR or config/forms_dir.json).")
        print("      JSON structure already passed; re-run without --json-only on your PC with OneDrive available.")
        return 2

    missing: list[tuple[str, str]] = []
    for key, fn in templates.items():
        p = forms_dir / fn
        if not p.is_file():
            missing.append((key, fn))

    print(f"missing files: {len(missing)}")
    if missing:
        for item in missing[:10]:
            print("  MISSING", item[0], "->", item[1])
        if len(missing) > 10:
            print(f"  ... and {len(missing) - 10} more")
        return 1

    for legacy in ("C5V", "C5I", "C7_C8_C10"):
        r = resolve_form_code(legacy)
        print(f"resolve {legacy} -> {r}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
