"""Required / optional / never-write classification."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..core.models import ObligationGraph


def classify(graph: "ObligationGraph") -> dict[str, list[str]]:
    required: list[str] = []
    optional: list[str] = []
    never_write: list[str] = []
    for fid, node in graph.fields.items():
        if node.never_write:
            never_write.append(fid)
        elif node.required:
            required.append(fid)
        else:
            optional.append(fid)
    return {
        "required": sorted(required),
        "optional": sorted(optional),
        "never_write": sorted(never_write),
    }
