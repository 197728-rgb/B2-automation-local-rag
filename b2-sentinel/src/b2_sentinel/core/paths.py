"""Project paths for B2 SENTINEL.

Resolves the repo root by walking up from this file until we see pyproject.toml.
All other paths are anchored to that root, so the package works from any CWD.
"""
from __future__ import annotations

from pathlib import Path


def _find_repo_root(start: Path) -> Path:
    cur = start.resolve()
    for parent in [cur, *cur.parents]:
        if (parent / "pyproject.toml").exists():
            return parent
    raise RuntimeError(f"Could not locate b2-sentinel repo root from {start}")


REPO_ROOT: Path = _find_repo_root(Path(__file__))

TEMPLATES_DIR: Path = REPO_ROOT / "templates"
SCHEMAS_DIR: Path = REPO_ROOT / "schemas"
MAPS_DIR: Path = SCHEMAS_DIR / "maps"
TEMPLATE_MANIFESTS_DIR: Path = SCHEMAS_DIR / "templates"
ACTIVITY_SCHEMAS_DIR: Path = SCHEMAS_DIR / "activity_2026"
OBLIGATION_GRAPHS_DIR: Path = SCHEMAS_DIR / "obligation_graphs"
ALIAS_RULES_DIR: Path = SCHEMAS_DIR / "alias_rules"
NA_POLICY_DIR: Path = SCHEMAS_DIR / "na_policy"
CONTRACTS_DIR: Path = SCHEMAS_DIR / "contracts"

INBOX_DIR: Path = REPO_ROOT / "inbox"
PRIOR_PACKET_DIR: Path = INBOX_DIR / "prior_b2_packet"
OUTBOX_DIR: Path = REPO_ROOT / "outbox"
LOGS_DIR: Path = REPO_ROOT / "logs"
ERRORS_DIR: Path = REPO_ROOT / "errors"
# Backward-compatible alias: internal audit artifacts now live in logs/.
OUTPUTS_DIR: Path = LOGS_DIR

def discover_template_forms() -> tuple[str, ...]:
    """Return every DOCX template stem, sorted.

    The default run target is now all wired templates, not the original
    five-form pilot set.
    """
    if not TEMPLATES_DIR.exists():
        return ()
    return tuple(sorted(p.stem for p in TEMPLATES_DIR.glob("*.docx")))


ACTIVE_FORMS: tuple[str, ...] = discover_template_forms()


def output_run_dir(run_id: str) -> Path:
    return OUTPUTS_DIR / run_id


def form_template_path(form_id: str) -> Path:
    return TEMPLATES_DIR / f"{form_id}.docx"


def form_map_path(form_id: str) -> Path:
    return MAPS_DIR / f"{form_id}.json"


def form_manifest_path(form_id: str) -> Path:
    return TEMPLATE_MANIFESTS_DIR / f"{form_id}.json"


def form_obligation_graph_path(form_id: str) -> Path:
    return OBLIGATION_GRAPHS_DIR / f"{form_id}.json"
