"""Shared form-scoped retrieval keywords (local-only; no side effects)."""

from __future__ import annotations

FORM_KEYWORDS: dict[str, tuple[str, ...]] = {
    "B24_RL2": (
        "b24",
        "b-24",
        "rl2",
        "repair level 2",
        "objective evidence",
        "tank car owner",
        "tco",
        "permission received",
        "written instructions",
        "pitp",
        "car mark",
        "car number",
        "design spec",
        "stencil spec",
        "aar form 4-2",
        "drawing number",
    ),
    "B81": ("b81", "b-81", "b81/b24", "stub sill", "only"),
    "B89": ("b89", "b-89", "insulation", "test plate"),
    "B90": ("b90", "b-90", "rls", "release", "return to service"),
    "Cover_Page": ("cover", "cover page", "aar", "audit", "facility", "company"),
}
