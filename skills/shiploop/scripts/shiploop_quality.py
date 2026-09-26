"""The static-checks quality loop on the Until Loop bound to the selected Improve card.

ShipLoop authors the loop contract from its prompt catalog on the transition
into static-checks.  The bound Until Loop runtime counts iterations and ends the
loop; the host executes each iteration.  On ``complete`` ShipLoop accepts
``done`` only when the saved terminal packet matches that contract, so the
review cannot be skipped or reshaped by the executor.  Rendering reads files
and never runs Git or the runtime.
"""

from __future__ import annotations

import json
import os
import shlex
import stat
import sys
from pathlib import Path
from typing import Any, Mapping, Optional

import shiploop_lint as lint
import shiploop_navigator_v3_prompts as guidance3
import shiploop_stage_spec as stage_spec
import shiploop_standalone_improve as standalone

STAGE, = stage_spec.with_complete_run("quality-terminal")
RUBRIC_PATH = "quality/code-craft.md"


class QualityError(ValueError):
    """A static-checks result or its terminal packet does not satisfy the loop contract."""


def _need(condition: bool, message: str) -> None:
    if not condition:
        raise QualityError(message)


def contract_path(action: str) -> str:
    return "quality/" + action + "-contract.json"


def terminal_path(action: str) -> str:
    return "quality/" + action + "-terminal.json"


# The runtime, started with --receipt, writes every packet it returns to this file
# and the terminal packet before it deletes its state: nothing depends on the host
# having saved stdout before a compaction.
RECEIPT_LINE = ("Receipt (the runtime writes every packet here, the terminal one last; ShipLoop "
                "checks this file, so do not write or edit it): ")

# Every key the bound runtime puts in a packet (Until Loop 0.7.0).
_PACKET_KEYS = frozenset({
    "status", "state_file", "workspace", "work", "conditions", "progress", "context",
    "status_semantics", "last_report", "instruction", "next_argv", "done_argv", "report_schema",
    "receipt",
})
_PROGRESS_KEYS = (frozenset({"action_number", "trivial_streak", "required_trivial_reviews"}),
                  frozenset({"action_number", "trivial_streak", "required_trivial_reviews",
                             "unchanged_first_pass"}))


def _step_plan_result(root: Path, state: Mapping[str, Any], work_item: str) -> Optional[str]:
    """Absolute path of the work item's latest accepted step-plan result record, if any."""
    actions = [row["action"] for row in state.get("history", ())
               if row.get("stage") == "step-plan" and row.get("workitem") == work_item]
    return str(root / "results" / (actions[-1] + ".md")) if actions else None


def _work_title(state: Mapping[str, Any], work_item: str) -> str:
    for row in state.get("work_items", ()):
        if row.get("id") == work_item:
            return str(row.get("title") or work_item)
    return work_item


def _runtime(state: Mapping[str, Any]) -> dict[str, str]:
    """Resolve the Until Loop bound to the run's selected Improve card (reads card files only)."""
    card = state.get("improve_skill") or ""
    _need(bool(card), "no Improve card is bound to this run, so it has no bound Until Loop runtime")
    try:
        return standalone.resolve_skill(card)
    except standalone.StandaloneImproveError as exc:
        raise QualityError("the bound Until Loop runtime cannot be resolved: " + str(exc)) from exc


def build_contract(root: Path, state: Mapping[str, Any], work_item: str, action: str) -> dict[str, Any]:
    """Return the Until Loop start contract for one static-checks action.

    ``work``, both conditions and the trivial-review gate come verbatim from
    the prompt catalog; ``check_terminal`` compares the terminal packet with
    this same contract.
    """
    _need(bool(work_item) and bool(action), "a quality contract needs a work item and an action")
    root = Path(root)
    repo = str(state["repo"])
    resources = [
        {"purpose": "Code craft rubric the review applies", "locator": str(root / RUBRIC_PATH)},
        {"purpose": "change inventory: the files in scope",
         "locator": str(root / lint.inventory_path(action))},
        {"purpose": "ShipLoop lint record for this action, when lint ran",
         "locator": str(root / "lint" / (action + ".md"))},
        {"purpose": "this action's pass log: append what each iteration checked and what is left",
         "locator": str(root / "notes" / (action + ".md"))},
    ]
    step_plan = _step_plan_result(root, state, work_item)
    if step_plan is not None:
        resources.append({"purpose": "accepted step plan: criteria, focused tests and checks",
                          "locator": step_plan})
    return {
        "workspace": repo,
        "work": guidance3.QUALITY_ITERATION.strip(),
        "exit_condition": guidance3.QUALITY_EXIT_CONDITION,
        "repeat_condition": guidance3.QUALITY_REPEAT_CONDITION,
        "required_trivial_reviews": 1,
        "context": {
            "request": ("Quality loop for ShipLoop work item " + work_item + " ("
                        + _work_title(state, work_item) + "): trace, verify and improve its change "
                        "against the Code craft rubric until an iteration finds only trivial issues."),
            "scope": ("Workspace " + repo + ". Only the files in the change inventory for " + work_item
                      + ", plus tests for them. Preserve every other change."),
            "authority": ("Edit in-scope product files and tests. Do not commit, push, install or "
                          "download anything, change a check's expected result, or widen scope. "
                          "ShipLoop callbacks belong to the parent; the loop never calls them."),
            "environment": ("Run in " + repo + ". Use the focused test and static-check commands named "
                            "in the accepted step plan and the current repository; recheck them "
                            "before relying on them."),
            "resources": resources,
        },
    }


def transition_writes(root: Path, after: Mapping[str, Any], work_item: Optional[str],
                      action: Optional[str]) -> dict[str, str]:
    """Contract and rubric writes for a newly issued static-checks action."""
    if not work_item or not action:
        return {}
    contract = build_contract(Path(root), after, work_item, action)
    return {
        contract_path(action): json.dumps(contract, indent=2, sort_keys=True) + "\n",
        RUBRIC_PATH: guidance3.CODE_CRAFT,
    }


def render_lines(root: Path, state: Mapping[str, Any], work_item: str, action: str) -> list[str]:
    """Read-only packet lines: runtime, start command, packet paths and inventory."""
    root = Path(root)
    lines = ["", "Quality loop (bound Until Loop; the loop script counts iterations; there is no "
             "iteration limit):"]
    try:
        runtime = _runtime(state)
    except QualityError as exc:
        lines.append("Unavailable: " + str(exc) + ". Report outcome blocked with this reason.")
        return lines + lint.render_inventory_lines(root, action, work_item)
    contract = root / contract_path(action)
    lines += [
        "Bound Until Loop card (open it if its rules are not already in your context): " + runtime["runtime_card"],
        "Loop contract (written by ShipLoop; pass it unchanged): " + str(contract),
        "Start: " + shlex.join([sys.executable, runtime["runtime_cli"], "start",
                                 "--receipt", str(root / terminal_path(action))]) + " < "
        + shlex.quote(str(contract)),
        RECEIPT_LINE + str(root / terminal_path(action)),
    ]
    if not contract.is_file():
        lines.append("The loop contract is missing; report outcome blocked naming this path.")
    return lines + lint.render_inventory_lines(root, action, work_item)


def _read_json(path: Path, label: str) -> Any:
    try:
        metadata = path.lstat()
    except OSError as exc:
        raise QualityError(label + " is missing: " + str(path)) from exc
    _need(stat.S_ISREG(metadata.st_mode) and metadata.st_nlink == 1,
          label + " must be a regular single-link non-symlink file: " + str(path))
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        raise QualityError(label + " is not valid JSON: " + str(path)) from exc


def check_terminal(root: Path, state: Mapping[str, Any], work_item: str, action: str,
                   result: Mapping[str, Any]) -> None:
    """Refuse a static-checks result that the bound Until Loop's terminal packet does not support.

    ``done`` needs a ``complete`` packet; ``revise`` and ``blocked`` need a
    blocked ``stopped`` packet (see ``check_loop_packet``), or ``blocked`` none
    (the summary and blocked_by carry the reason).
    ``repeat`` is never valid: the loop, not the graph, repeats the review.
    The packet is compared with the contract rebuilt from ShipLoop state, not
    with the contract file, so editing that file cannot reshape the loop.
    """
    outcome = result.get("outcome") if isinstance(result, Mapping) else None
    _need(outcome in ("done", "revise", "blocked"),
          "static-checks accepts only done, revise or blocked; the bound Until Loop repeats the review, "
          "not the graph")
    if not state.get("improve_skill"):
        return  # No bound runtime: the packet directs blocked; nothing to verify.
    root = Path(root)
    path = root / terminal_path(action)
    if outcome == "blocked" and not os.path.lexists(path):
        return
    check_loop_packet(path, result, build_contract(root, state, work_item, action),
                      "quality loop", str(root / contract_path(action)))


def check_loop_packet(path: Path, result: Mapping[str, Any], expected: Mapping[str, Any],
                      label: str, contract_file: str) -> None:
    """Refuse a loop stage's result that its saved Until Loop terminal packet does not support.

    Shared by every script-enforced loop (the quality loop and the test loops).
    The packet must come from a run of ``expected`` (rebuilt from ShipLoop
    state, so editing the contract file cannot reshape the loop).  Loops have
    no iteration limit.  ``complete`` supports only ``done``; a ``blocked``
    stop supports ``revise`` (the item's goal proved wrong) or ``blocked``; a
    ``cancelled`` stop supports nothing, since a user's stop is a pause.
    """
    outcome = result.get("outcome")
    refs = result.get("evidence_refs")
    _need(isinstance(refs, list) and str(path) in refs,
          "list the saved terminal packet in evidence_refs: " + str(path))
    packet = _read_json(path, "Until Loop terminal packet")
    _need(isinstance(packet, Mapping), "the Until Loop terminal packet must be a JSON object")
    _need(set(packet) == _PACKET_KEYS,
          "the terminal packet is not a complete Until Loop packet (start the loop with the printed "
          "--receipt command; the runtime writes this file itself)")
    _need(packet.get("receipt") == str(path),
          "the terminal packet was not written by a run started with --receipt " + str(path))
    conditions, progress = packet.get("conditions"), packet.get("progress")
    _need(isinstance(conditions, Mapping) and isinstance(progress, Mapping)
          and frozenset(progress) in _PROGRESS_KEYS,
          "the Until Loop terminal packet lacks its conditions or progress")
    _need(packet.get("workspace") == expected["workspace"]
          and packet.get("work") == expected["work"]
          and conditions.get("exit") == expected["exit_condition"]
          and conditions.get("repeat") == expected["repeat_condition"]
          and progress.get("required_trivial_reviews") == expected["required_trivial_reviews"]
          and packet.get("context") == expected["context"],
          "the terminal packet is not from a run of this action's contract " + contract_file)
    status = packet.get("status")
    _need(status in ("complete", "stopped"),
          "the terminal packet must have status complete or stopped, found " + repr(status))
    state_file = packet.get("state_file")
    _need(isinstance(state_file, str) and os.path.isabs(state_file) and not os.path.lexists(state_file),
          "the terminal packet's run is still live or unnamed; a terminal transition deletes its state file")
    _need(packet.get("next_argv") is None and packet.get("done_argv") is None
          and packet.get("report_schema") is None,
          "the terminal packet still offers a callback")
    report = packet.get("last_report")
    _need(isinstance(report, Mapping), "the terminal packet has no final report")
    iterations = progress.get("action_number")
    _need(isinstance(iterations, int) and not isinstance(iterations, bool) and iterations >= 1,
          "the terminal packet has no iteration count")
    if status == "complete":
        _need(report.get("classification") == "trivial" and report.get("exit_assessment") == "satisfied",
              "a complete terminal packet needs a trivial report whose exit is satisfied")
        _need(outcome == "done", "a complete " + label + " reports outcome done")
        return
    # Loops have no iteration limit, so the contract never asks for a cancel; a
    # user's stop is ShipLoop's pause, which keeps the loop active.
    _need(report.get("continuation_assessment") != "cancelled",
          "the " + label + " was cancelled after " + str(iterations) + " iterations; it has no iteration "
          "limit. A user's stop is the packet's pause command, not a cancelled loop: start the loop again "
          "and run it until its exit condition holds")
    _need(outcome in ("blocked", "revise"),
          "a " + label + " stopped as blocked reports outcome blocked, with blocked_by, or revise when the "
          "item's goal proved wrong as planned")

__all__ = (
    "QualityError",
    "RECEIPT_LINE",
    "check_loop_packet",
    "RUBRIC_PATH",
    "STAGE",
    "build_contract",
    "check_terminal",
    "contract_path",
    "render_lines",
    "terminal_path",
    "transition_writes",
)
