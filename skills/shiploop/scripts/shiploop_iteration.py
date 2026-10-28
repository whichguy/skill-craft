"""The per-step iteration's contract: each planned step is built, tested, documented, reviewed and committed before the
next step starts (design T §8, amended by Astra's review in §9; owner 2026-10-27: "I want to build one step,
then test, improve, and document, and then build step number two ... not just do one monolithic build of all the steps").

Build order step 1 (§9.1) specifies four invariants here, as pure functions, before the navigator uses them (step 2):
- **Identity.** An iteration is (work item, plan revision, step, base). The plan revision is the accepted step plan's
  action ID; the base is the commit the iteration starts from, never a snapshot of a dirty checkout, so edits a
  send-back leaves in the checkout count as the next iteration's change instead of vanishing into its base (§9 row 5).
  A receipt made for another identity is stale.
- **Producer ownership.** Document owns the step's one Improve review, so the review sees code, tests and docs (§8.3);
  an omitted document still records a not-applicable result that owns it (§9 row 2). Commit is ShipLoop's alone.
- **Retry invalidation.** A send-back to a stage of the iteration voids that stage's receipt and every later one and
  keeps the base; a send-back to planning voids them all and ends the iteration (§9 row 5).
- **The final-tree commit invariant.** The commit stage commits only the tree the step's last gate ran on (document's
  complete, or its review's import), as the one commit on top of the iteration's base. A pending record written before the commit lets a retry recognise a
  commit that already happened, and any other commit is refused: only the commit stage commits (§9 row 3).

Build order step 2a adds what each step owes its test stage (``case_step``, ``due_cases``, ``new_cases``,
``active_commands``), derived from data ShipLoop already validates: each test-spec case names its step-plan
``criterion`` and each step lists the ``criteria`` it satisfies, so the test spec needs no field of its own (F1).

Stage IDs keep today's names (``implement`` is the design's "build"); ``commit`` is new, and ``verify`` has no place in
an iteration (§7, §8.1).  There is no knowledge stage (2b-3, option C; owner 2026-10-28, "Go with C"): document is the
step's one place to reflect, recording in the knowledge home what the step showed, so its review sees and corrects
that record with the code, tests and docs.
"""
from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from copy import deepcopy
from typing import Any, NamedTuple

STAGES = ("implement", "test", "document", "commit")
MODEL_STAGES = STAGES[:-1]
IMPROVE_OWNER = "document"
_COMMIT_ID = re.compile(r"[0-9a-f]{40}")


class Iteration(NamedTuple):
    """One step's iteration: who it is and the commit it starts from."""
    item: str        # the work item, "W1"
    plan: str        # the accepted step plan's action ID: the plan revision
    step: str        # the step's ID, "S1"
    number: int      # its position in the plan, from 1
    base: str        # the full ID of the commit the iteration starts from


class Decision(NamedTuple):
    """What the commit stage does: ``commit``, ``done`` (the commit already happened) or ``refuse``."""
    action: str
    reason: str = ""
    reopen: str | None = None    # the stage a refusal sends the work back to, when one can fix it


def commit_id(value: Any) -> str:
    """``value`` when it is a full commit ID; ValueError otherwise."""
    if not isinstance(value, str) or not _COMMIT_ID.fullmatch(value):
        raise ValueError("an iteration's base is a full commit ID, never a snapshot or a short ID: " + repr(value))
    return value


def next_stage(stage: str) -> str | None:
    """The stage after ``stage`` in an iteration, or None after commit, when the next step's iteration starts."""
    if stage not in STAGES:
        raise ValueError(repr(stage) + " is not a stage of an iteration " + repr(STAGES))
    index = STAGES.index(stage) + 1
    return STAGES[index] if index < len(STAGES) else None


def owns_improve(stage: str) -> bool:
    """Whether ``stage``'s action owns the iteration's one Improve review (document, applicable or not)."""
    return stage == IMPROVE_OWNER


def start(item: str, plan: str, steps: Sequence[Mapping[str, Any]], committed: Sequence[str],
          head: Any) -> Iteration | None:
    """The iteration of the first step ``committed`` lacks, from ``head``; None when every step is committed.

    ``committed`` lists the steps this plan revision has committed, in order: steps are committed in plan order, so it
    must be a prefix of the plan."""
    base = commit_id(head)
    ids = [str(row.get("id")) for row in steps]
    if list(committed) != ids[:len(committed)]:
        raise ValueError("committed steps " + repr(list(committed)) + " are not the start of the plan " + repr(ids))
    if len(committed) == len(ids):
        return None
    return Iteration(item, plan, ids[len(committed)], len(committed) + 1, base)


def advance(current: Iteration, commit: Any) -> str:
    """The base of the next step's iteration: the commit ``current``'s commit stage made."""
    return commit_id(commit)


def identity(current: Iteration) -> dict[str, Any]:
    """The identity a receipt of ``current`` records, and a later stage checks."""
    return current._asdict()


def stale(recorded: Mapping[str, Any] | None, current: Iteration) -> bool:
    """Whether a receipt recorded for ``recorded`` is not ``current``'s: another item, plan revision, step or base."""
    return recorded is None or dict(recorded) != identity(current)


def ends_iteration(target: str) -> bool:
    """Whether a send-back to ``target`` ends the iteration: any target outside it (planning) does."""
    return target not in MODEL_STAGES


def invalidated(done: Sequence[str], target: str) -> list[str]:
    """The receipts among ``done`` (stages of the current iteration, in order) that a send-back to ``target`` voids:
    ``target``'s and every later one inside the iteration, or all of them when it ends the iteration.  Commit is never a
    target: ShipLoop runs it, and its refusal names the stage to reopen instead."""
    if target == "commit":
        raise ValueError("commit is ShipLoop's stage, never a send-back target")
    if ends_iteration(target):
        return list(done)
    first = STAGES.index(target)
    return [stage for stage in done if STAGES.index(stage) >= first]


def after_send_back(current: Iteration, target: str) -> Iteration | None:
    """The iteration a send-back to ``target`` leaves: the same one, base kept, inside it; None when it ends, so the next
    plan revision starts its first iteration from the last commit (``start``)."""
    return None if ends_iteration(target) else current


def pending_record(current: Iteration, tree: str) -> dict[str, Any]:
    """The record the commit stage writes before it commits: the iteration, the parent it commits on and the tree the
    commit will hold."""
    return {"iteration": identity(current), "parent": current.base, "tree": tree}


def commit_decision(current: Iteration, *, head: str, head_parent: str | None, head_tree: str | None,
                    current_tree: str, gated_tree: str, pending: Mapping[str, Any] | None) -> Decision:
    """What the commit stage does, from the checkout's ``head`` (its parent and tree), the working tree's snapshot now
    (``current_tree``), the snapshot the step's last gate ran on (``gated_tree``) and a pending record, if any."""
    if pending is not None and stale(pending.get("iteration"), current):
        return Decision("refuse", "the pending commit record belongs to another iteration: " + repr(pending.get("iteration")))
    if head == current.base:
        if current_tree != gated_tree:
            return Decision("refuse", "the tree changed after the document stage's gate ran; rerun the document stage so its "
                            "gate runs on the tree to commit", "document")
        return Decision("commit")
    if (pending is not None and head_parent == current.base and pending.get("parent") == current.base
            and head_tree == pending.get("tree")):
        return Decision("done", "the commit on " + current.base[:12] + " already holds the pending tree")
    return Decision("refuse", "HEAD " + str(head)[:12] + " is not the iteration's base " + current.base[:12] + " or its "
                    "pending commit: only the commit stage commits inside an iteration")


def case_step(criterion: str, steps: Sequence[Mapping[str, Any]]) -> str:
    """The step a case proving ``criterion`` is due at: the last step, in plan order, whose ``criteria`` list it (a case
    spanning steps is due once every step it needs is built), or the plan's last step when none lists it."""
    ids = [str(row.get("id")) for row in steps]
    if not ids:
        raise ValueError("a step plan has at least one step")
    listing = [str(row.get("id")) for row in steps if criterion in (row.get("criteria") or ())]
    return listing[-1] if listing else ids[-1]


def _due(criterion: Any, steps: Sequence[Mapping[str, Any]]) -> int:
    """``case_step`` as the step's position, from 1."""
    return [str(row.get("id")) for row in steps].index(case_step(str(criterion), steps)) + 1


def _number(steps: Sequence[Mapping[str, Any]], number: Any) -> int:
    if isinstance(number, bool) or not isinstance(number, int) or not 1 <= number <= len(steps):
        raise ValueError("step number " + repr(number) + " is outside the plan's " + str(len(steps)) + " steps")
    return number


def due_cases(cases: Sequence[Mapping[str, Any]], steps: Sequence[Mapping[str, Any]], number: int) -> list[str]:
    """The case IDs step ``number`` owes: every case due at it or an earlier step, each of which must pass (GREEN)."""
    _number(steps, number)
    return [str(case.get("id")) for case in cases if _due(case.get("criterion"), steps) <= number]


def new_cases(cases: Sequence[Mapping[str, Any]], steps: Sequence[Mapping[str, Any]], number: int) -> list[str]:
    """The case IDs due at step ``number`` itself: the only ones its RED check holds to failing on the iteration's
    base, since an earlier step's cases already pass there."""
    _number(steps, number)
    return [str(case.get("id")) for case in cases if _due(case.get("criterion"), steps) == number]


def active_commands(commands: Sequence[Mapping[str, Any]], cases: Sequence[Mapping[str, Any]],
                    steps: Sequence[Mapping[str, Any]], number: int) -> list[dict[str, Any]]:
    """The recorded commands step ``number``'s test stage runs, as copies.
    - A command with ``ids`` runs from the first step one of them is due at, narrowed to the IDs due by step ``number``;
      an ID no case names is due at the last step.
    - The regression command runs at every step.
    - Any other command (a check) runs from the last step its ``criteria`` are due at, or at the last step when it
      names none.  This is what lets a check that only a later step can satisfy wait for it (a run of 2026-10-17
      collapsed a three-step plan into one step when it could not).
    How many tests each command must run per step (its floor) is build order step 3's."""
    _number(steps, number)
    due_at = {str(case.get("id")): _due(case.get("criterion"), steps) for case in cases}
    active = []
    for command in commands:
        row = deepcopy(dict(command))
        ids = command.get("ids")
        if ids:
            row["ids"] = [ident for ident in ids if due_at.get(str(ident), len(steps)) <= number]
            if not row["ids"]:
                continue
        elif command.get("suite") != "regression":
            criteria = command.get("criteria") or ()
            if (max(_due(criterion, steps) for criterion in criteria) if criteria else len(steps)) > number:
                continue
        active.append(row)
    return active
