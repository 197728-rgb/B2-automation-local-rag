"""One-off: verify Karen filenames and emit m1002_template_registry.json. Run from b2_form_automation."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KAREN = Path(
    r"C:\Users\rodrigul\OneDrive - Transportation Technology Center, Inc\2026 BOE DOC\Karen's B-2s"
)

pairs = [
    ("A19", "M-1002 Exhibit B-2 Activity Code A19 - (4-1-2024).docx"),
    ("A19C", "M-1002 Exhibit B-2 Activity Code A19c - (4-1-2024).docx"),
    ("B24_RL1", "M-1002 Exhibit B-2 Activity Code B24 (RL1) - (4-1-2024).docx"),
    ("B24_RL2", "M-1002 Exhibit B-2 Activity Code B24 (RL2) - (4-1-2024).docx"),
    ("B24_RLC", "M-1002 Exhibit B-2 Activity Code B24 (RLC) - (4-1-2024).docx"),
    ("B78", "M-1002 Exhibit B-2 Activity Code B78 - (4-1-2024).docx"),
    ("B81_MULTI", "M-1002 Exhibit B-2 Activity Code B81 (A19, B78, B82, & B24) - (4-1-2024).docx"),
    ("B81_B24", "M-1002 Exhibit B-2 Activity Code B81 (B24 only) - (4-1-2024).docx"),
    ("B82", "M-1002 Exhibit B-2 Activity Code B82 - (4-1-2024).docx"),
    ("B85", "M-1002 Exhibit B-2 Activity Code B85 - (4-1-2024).docx"),
    ("B89_TEST_PLATE", "M-1002 Exhibit B-2 Activity Code B89 (Insulation Inspection on Test Plate) - (4-1-2024).docx"),
    ("B89_TANK_CAR", "M-1002 Exhibit B-2 Activity Code B89 (On Tank Car) - (4-1-2024).docx"),
    ("B90_RLS", "M-1002 Exhibit B-2 Activity Code B90 (RLS) - (4-1-2024).docx"),
    ("C10_COAT", "M-1002 Exhibit B-2 Activity Code C10 (Repair of Interior Coatings) - (4-1-2024).docx"),
    ("C10_LIN", "M-1002 Exhibit B-2 Activity Code C10 (Repair of Interior Linings) - (4-1-2024).docx"),
    ("C4A_C", "M-1002 Exhibit B-2 Activity Code C4a(C) (Closures) - (4-1-2024).docx"),
    ("C4A_F", "M-1002 Exhibit B-2 Activity Code C4a(F) (Fittings) - (4-1-2024).docx"),
    ("C4A_I", "M-1002 Exhibit B-2 Activity Code C4a(I) (Instruments) - (4-1-2024).docx"),
    ("C4A_S", "M-1002 Exhibit B-2 Activity Code C4a(S) (Safety Relief Devices) - (4-1-2024).docx"),
    ("C4A_V", "M-1002 Exhibit B-2 Activity Code C4a(V) (Valves) - (4-1-2024).docx"),
    ("C4M_C", "M-1002 Exhibit B-2 Activity Code C4m(C) (Closures) - (4-1-2024).docx"),
    ("C4M_F", "M-1002 Exhibit B-2 Activity Code C4m(F) (Fittings) - (4-1-2024).docx"),
    ("C4M_H", "M-1002 Exhibit B-2 Activity Code C4m(H) (Heater Systems) (Test Fixture) - (4-1-2024).docx"),
    ("C4M_I", "M-1002 Exhibit B-2 Activity Code C4m(I) (Instruments) - (4-1-2024).docx"),
    ("C4M_S", "M-1002 Exhibit B-2 Activity Code C4m(S) (Safety Relief Devices) - (4-1-2024).docx"),
    ("C4M_V", "M-1002 Exhibit B-2 Activity Code C4m(V) (Valves) - (4-1-2024).docx"),
    ("C5_C", "M-1002 Exhibit B-2 Activity Code C5(C) (Closures) - (4-1-2024).docx"),
    ("C5_F", "M-1002 Exhibit B-2 Activity Code C5(F) (Fittings) - (4-1-2024).docx"),
    ("C5_H", "M-1002 Exhibit B-2 Activity Code C5(H) (Heater Systems) (Test Fixture) - (4-1-2024).docx"),
    ("C5_I", "M-1002 Exhibit B-2 Activity Code C5(I) (Instruments) - (4-1-2024).docx"),
    ("C5_S", "M-1002 Exhibit B-2 Activity Code C5(S) (Safety Relief Devices) (4-1-2024).docx"),
    ("C5_V", "M-1002 Exhibit B-2 Activity Code C5(V) (Valves) (4-1-2024).docx"),
    ("C6I", "M-1002 Exhibit B-2 Activity Code C6i (Installation of Service Equipment) (4-1-2024).docx"),
    ("C6R", "M-1002 Exhibit B-2 Activity Code C6r (R&R Service Equipment with Modification)( 4-1-2024).docx"),
    ("C7", "M-1002 Exhibit B-2 Activity Code C7 (Removal Coatings-Linings) - (4-1-2024).docx"),
    ("C7_C10_COAT", "M-1002 Exhibit B-2 Activity Code C7 & C10 (Combination) (Coatings) - (4-1-2024).docx"),
    ("C7_C10_LIN", "M-1002 Exhibit B-2 Activity Code C7 & C10 (Combination) (Linings) - (4-1-2024).docx"),
    ("C7_C8_COAT", "M-1002 Exhibit B-2 Activity Code C7 & C8 (Combination) (Coatings) - (4-1-2024).docx"),
    ("C7_C8_LIN", "M-1002 Exhibit B-2 Activity Code C7 & C8 (Combination) (Linings) - (4-1-2024).docx"),
    ("C7_C8_C10_COAT", "M-1002 Exhibit B-2 Activity Code C7, C8, C10 (Combination) (Coatings) - (4-1-2024).docx"),
    ("C7_C8_C10_LIN", "M-1002 Exhibit B-2 Activity Code C7, C8, C10 (Combination) (Linings) - (4-1-2024).docx"),
    ("C8_COAT", "M-1002 Exhibit B-2 Activity Code C8 (Application of Interior Coatings) - (4-1-2024).docx"),
    ("C8_LIN", "M-1002 Exhibit B-2 Activity Code C8 (Application of Interior Linings) - (4-13-2024).docx"),
    ("C8_C10_COAT", "M-1002 Exhibit B-2 Activity Code C8 & C10 (Combination) (Coatings)(4-1-2024).docx"),
    ("C8_C10_LIN", "M-1002 Exhibit B-2 Activity Code C8 & C10 (Combination) (Linings) - (4-1-2024).docx"),
    ("C9_COAT", "M-1002 Exhibit B-2 Activity Code C9 (Qualification of Interior Coatings) - (4-1-2024).docx"),
    ("C9_LIN", "M-1002 Exhibit B-2 Activity Code C9 (Qualification of Interior Linings) - (4-1-2024).docx"),
    ("COVER_SHEET", "M-1002 Exhibit B-2 Cover Sheet - (4-1-2024).docx"),
]


def main() -> None:
    missing = [fn for _, fn in pairs if not (KAREN / fn).is_file()]
    if missing:
        raise SystemExit(f"Missing {len(missing)} files under {KAREN}:\n" + "\n".join(missing[:5]))
    obj = {
        "version": 1,
        "description": "M-1002 B-2 blanks; filenames match Karen B-2s library. Point forms_dir at that folder or copy into forms/templates.",
        "templates": {k: v for k, v in pairs},
        "legacy_to_registry": {
            "C5I": "C5_I",
            "C5S": "C5_S",
            "C5V": "C5_V",
            "C6R": "C6R",
            "B89": "B89_TANK_CAR",
            "C7": "C7",
            "C8": "C8_COAT",
            "C10": "C10_COAT",
            "C7_C8_C10": "C7_C8_C10_COAT",
        },
        "default_registry_key": "C5_V",
    }
    out = ROOT / "config" / "m1002_template_registry.json"
    out.write_text(json.dumps(obj, indent=2), encoding="utf-8")
    print("OK", len(pairs), "->", out)


if __name__ == "__main__":
    main()
