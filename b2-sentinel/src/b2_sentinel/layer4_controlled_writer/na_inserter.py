"""Approved N/A text insertion - the only sanctioned way to leave a required cell blank."""
from __future__ import annotations

from ..core.models import (
    FieldNode,
    NAExceptionEntry,
    PatchInstruction,
)
from ..core.status import WriteAuthority


def n_a_instruction(node: FieldNode, exception: NAExceptionEntry) -> PatchInstruction:
    if exception.status != "approved_na":
        raise ValueError(
            f"NAExceptionEntry for {node.field_id} is not approved (status={exception.status})"
        )
    return PatchInstruction(
        field_id=node.field_id,
        table_index=node.table_index,
        row=node.row,
        col=node.col,
        value="N/A",
        write_mode=node.write_mode,
        label_text=node.label,
        authorized=True,  # authority is APPROVED_NA_INSERTION via policy
    )
