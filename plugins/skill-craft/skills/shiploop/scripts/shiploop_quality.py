"""Verify's review inputs: the Code craft rubric file and the change inventory.

The static-checks quality loop became verify's stage loop (2026-10-10, 17 -> 8
inner stages).  Its contract, invoke block and terminal check now belong to
``shiploop_loops`` with every other inner stage's; this module keeps what only
verify's review reads: the rubric file ShipLoop writes on entry to verify, and
the change-inventory lines its packet prints.

The loop helpers the test loop still imports through this module
(``check_loop_packet``, ``start_command``, ``condition_lines`` and the receipt
lines) are the same objects as in ``shiploop_loops``: one implementation.
Rendering reads files and never runs Git or the runtime.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

import shiploop_lint as lint
import shiploop_loops as loops
import shiploop_prompts as guidance
import shiploop_stage_spec as stage_spec

STAGE, = stage_spec.with_entry_run("change-inventory")
RUBRIC_PATH = loops.RUBRIC_PATH



def rubric_writes() -> dict[str, str]:
    """Run-relative path -> text of the Code craft rubric verify's review applies (written on entry to verify)."""
    return {RUBRIC_PATH: guidance.CODE_CRAFT}


def inventory_lines(root: Path, state: Mapping[str, Any], work_item: str, action: str) -> list[str]:
    """Read-only packet lines: the change inventory verify's review covers."""
    return lint.render_inventory_lines(Path(root), action, work_item)


__all__ = (
    "QualityError",
    "RECEIPT_LINE",
    "RECEIPT_REF_LINE",
    "RESUME_LINE",
    "RUBRIC_PATH",
    "STAGE",
    "check_loop_packet",
    "condition_lines",
    "inventory_lines",
    "rubric_writes",
    "start_command",
)
