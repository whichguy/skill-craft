"""The answer of ``shiploop check``: would ShipLoop accept this step now? (phases B and C plan, 2026-10-28)

The check and ``complete`` run one evaluator (``shiploop_navigator._evaluate``).  A check records its answer here, yes
or no with the reason, tied to everything the gates read (``answer_key``).  ``complete`` takes a recorded yes whose key
equals the key it computes now, instead of running the gates again (``matching_yes``), and runs them when anything
changed since; so a matching yes cannot be refused, and a refusal always comes from gates run on the current files.

The key: the state revision, this package's version, the inner stage's loop contract, the result draft's bytes, the
candidate's working tree, the item's base (its lint base tree and any preparatory commit), the counted runs the
floors read (this action's own and the item's accepted ones) and the run's lint option.
"""

from __future__ import annotations

import hashlib
import os
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import shiploop_expectations as expectations
import shiploop_lint as lint
import shiploop_loop_contract as loop_contract
import shiploop_loops as loops
import shiploop_reference as reference
import shiploop_store as store
import shiploop_test_loop as test_loop

CHECK_DIR = "checks"


def answer_path(action_id: str) -> str:
    """Run-relative path of an action's latest check answer (replaced by each check)."""
    return CHECK_DIR + "/" + action_id + ".md"


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def answer_key(root: Path, state: Mapping[str, Any], action_id: str, stage: str | None, work_item: str | None,
               draft: Path, *, lint_option: str) -> dict[str, Any]:
    """Everything the gates read, as one comparable value; computed after the check's gates ran, since a test run may
    leave an untracked file, and again by ``complete`` before it takes a yes."""
    root = Path(root)
    contract = None
    if stage in loops.STAGES:
        try:
            contract = _sha(loop_contract.dumps(loops.contract(root, state, action_id)).encode("utf-8"))
        except loops.LoopError:
            contract = None
    try:
        draft_sha = _sha(Path(draft).read_bytes())
    except OSError:
        draft_sha = None
    base = lint.read_base(root, work_item) if work_item else None
    return {
        "revision": state.get("revision"),
        "version": reference.package_version(),
        "contract": contract,
        "draft": draft_sha,
        "tree": test_loop.working_tree(root, Path(str(state["repo"]))) or None,
        "base": {"tree": (base or {}).get("tree"),
                 "preparatory": expectations.preparatory_commit(root, work_item) if work_item else None},
        "floors": {"action": test_loop.action_counts(root, action_id),
                   "item": test_loop.accepted_counts(root, state, work_item) if work_item else {}},
        "lint": lint_option,
    }


def written_since(root: Path, action_id: str, started: float) -> list[str]:
    """The check records of ``action_id`` this check wrote (modified at or after ``started``), run-relative."""
    found = []
    for relative in test_loop.check_paths(action_id):
        try:
            if os.stat(Path(root) / relative).st_mtime >= started:
                found.append(relative)
        except OSError:
            continue
    return found


def record_answer(root: Path, action_id: str, stage: str | None, key: Mapping[str, Any], *, yes: bool,
                  reason: str = "", gate_lines: Sequence[str] = (), preparatory: Sequence[str] = (),
                  records: Sequence[str] = ()) -> dict[str, Any]:
    """Write the check's one answer for ``action_id`` and return it."""
    answer = {
        "schema": "shiploop-check-answer-1", "action": action_id, "stage": stage,
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),  # noqa: UP017 - Python 3.9 too
        "answer": "yes" if yes else "no", "reason": reason, "gate_lines": list(gate_lines),
        "preparatory": list(preparatory), "records": list(records), "key": dict(key),
    }
    path = Path(root) / answer_path(action_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    store.atomic_write_text(path, store.dumps(answer, "ShipLoop check answer"))
    return answer


def matching_yes(root: Path, action_id: str, key: Mapping[str, Any]) -> Mapping[str, Any] | None:
    """This action's recorded yes when its key equals ``key`` (nothing the gates read changed since), else None."""
    path = Path(root) / answer_path(action_id)
    try:
        answer = store.read_record(path) if path.is_file() else None
    except (OSError, store.StorageError):
        return None
    if (isinstance(answer, Mapping) and answer.get("answer") == "yes" and answer.get("action") == action_id
            and answer.get("key") == dict(key) and key.get("tree") and key.get("draft")):
        return answer
    return None


__all__ = ("CHECK_DIR", "answer_key", "answer_path", "matching_yes", "record_answer", "written_since")
