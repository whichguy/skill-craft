"""Script-enforced test loops at test-green and regression on the bound Until Loop.

The accepted step plan records the work item's test command list
(``test_commands``).  On the transition into ``test-green`` or ``regression``
ShipLoop writes an Until Loop contract whose work embeds that exact list; the
host runs the loop (run every command, fix the code, rerun) and saves its
terminal packet.  On ``complete`` ShipLoop accepts ``done`` only when the
terminal packet matches the contract rebuilt from run state and, after that,
every listed command exits 0 when ShipLoop runs it itself.  ``blocked`` is
always accepted; ``repeat`` never is, because the loop, not the graph, repeats.

Commands are shell strings the step plan recorded; ShipLoop runs them with
``/bin/sh -c`` in the run's repository (owner decision 2026-09-25), bounded per
command and per stage.  Rendering reads files and never runs a command.
"""

from __future__ import annotations

import json
import os
import shlex
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional, Tuple

import shiploop_lint as lint
import shiploop_navigator_v3_prompts as guidance3
import shiploop_quality as quality
import shiploop_store as store

STAGES = ("test-green", "regression")
# Stages that can edit code after the test loops: on done ShipLoop reruns every
# recorded command (no loop).
RERUN_STAGES = ("test-refine", "static-checks", "integration-verify")
VERIFY_STAGES = STAGES + RERUN_STAGES
# Refused command runs per action before only blocked is accepted.
MAX_REFUSED_RUNS = 3
SUITES = ("focused", "regression")
COMMAND_TIMEOUT_SECONDS = 600.0
STAGE_BUDGET_SECONDS = 1800.0
TAIL_CHARS = 6000
SCHEMA = "shiploop-test-loop/v1"

Runner = Callable[..., Tuple[str, Optional[int], bytes, bytes]]


class TestLoopError(ValueError):
    """A test-loop result, its terminal packet or its command rerun does not satisfy the loop."""


def _need(condition: bool, message: str) -> None:
    if not condition:
        raise TestLoopError(message)


def contract_path(action: str) -> str:
    return "tests/" + action + "-contract.json"


def latest_path(action: str) -> str:
    return "tests/" + action + "-latest.json"


def terminal_path(action: str) -> str:
    return "tests/" + action + "-terminal.json"


def verify_path(action: str, number: int) -> str:
    return "tests/" + action + "-verify" + str(number) + ".md"


def normalise_commands(value: Any) -> List[Dict[str, str]]:
    """Validate a step plan's ``test_commands``: ``[{"command": str, "suite": focused|regression}]``."""
    _need(isinstance(value, list), "test_commands must be a list")
    commands: List[Dict[str, str]] = []
    for entry in value:
        _need(isinstance(entry, Mapping) and set(entry) == {"command", "suite"},
              "each test command must contain exactly command and suite")
        command = entry.get("command")
        _need(isinstance(command, str) and command.strip() != "" and "\n" not in command
              and "\0" not in command, "a test command must be one nonblank line")
        _need(entry.get("suite") in SUITES, "a test command's suite must be focused or regression")
        commands.append({"command": command.strip(), "suite": str(entry["suite"])})
    return commands


def _step_plan(state: Mapping[str, Any], work_item: str) -> Tuple[Optional[str], Mapping[str, Any]]:
    """The work item's latest accepted step-plan action and its result."""
    actions = [row["action"] for row in state.get("history", ())
               if row.get("stage") == "step-plan" and row.get("workitem") == work_item]
    for action in reversed(actions):
        result = state.get("accepted", {}).get(action)
        if isinstance(result, Mapping) and result.get("outcome") == "done":
            return action, result
    return None, {}


def stage_commands(state: Mapping[str, Any], stage: str, work_item: str) -> Tuple[List[Dict[str, str]], str]:
    """This stage's commands and, when there are none, why.

    test-green runs the focused commands; every other stage runs every command.
    """
    _action, result = _step_plan(state, work_item)
    if "test_commands" not in result:
        return [], ""
    commands = [dict(row) for row in result["test_commands"]
                if stage != "test-green" or row["suite"] == "focused"]
    if commands:
        return commands, ""
    return [], str(result.get("test_commands_na") or ("the accepted step plan lists no focused command"
                                                       if result["test_commands"] else ""))


def _work(commands: List[Dict[str, str]]) -> str:
    listing = "\n".join(str(number) + ". [" + row["suite"] + "] " + row["command"]
                        for number, row in enumerate(commands, 1))
    return guidance3.TEST_ITERATION + "Test command list:\n" + listing + "\n"


def build_contract(root: Path, state: Mapping[str, Any], work_item: str, action: str,
                   stage: str) -> Dict[str, Any]:
    """Return the Until Loop start contract for one test-green or regression action."""
    _need(stage in STAGES, "no test loop runs at " + stage)
    commands, _reason = stage_commands(state, stage, work_item)
    _need(bool(commands), "the accepted step plan lists no command for the " + stage + " test loop")
    root = Path(root)
    repo = str(state["repo"])
    step_action, _result = _step_plan(state, work_item)
    return {
        "workspace": repo,
        "work": _work(commands),
        "exit_condition": guidance3.TEST_EXIT_CONDITION,
        "repeat_condition": guidance3.TEST_REPEAT_CONDITION,
        "required_trivial_reviews": 1,
        "context": {
            "request": ("Test loop (" + stage + ") for ShipLoop work item " + work_item + " ("
                        + quality._work_title(state, work_item) + "): run its test command list and fix "
                        "the code until every command exits 0."),
            "scope": ("Workspace " + repo + ". The files in " + work_item + "'s change and their tests. "
                      "Preserve every other change."),
            "authority": ("Edit in-scope product code and tests. Never change a check's expected result "
                          "to get green. Do not commit, push, install or download anything. ShipLoop "
                          "callbacks belong to the parent; the loop never calls them."),
            "environment": "Run every command from " + repo + ".",
            "resources": [{"purpose": "accepted step plan: test_commands and completion criteria",
                           "locator": str(root / "results" / (str(step_action) + ".md"))}],
        },
    }


def transition_writes(root: Path, after: Mapping[str, Any], work_item: Optional[str],
                      action: Optional[str], stage: str) -> Dict[str, str]:
    """The contract write for a newly issued test-loop action (none when the stage has no command)."""
    if not work_item or not action or stage not in STAGES:
        return {}
    commands, _reason = stage_commands(after, stage, work_item)
    if not commands:
        return {}
    contract = build_contract(Path(root), after, work_item, action, stage)
    return {contract_path(action): json.dumps(contract, indent=2, sort_keys=True) + "\n"}


def render_lines(root: Path, state: Mapping[str, Any], work_item: str, action: str, stage: str) -> List[str]:
    """Read-only packet lines: runtime, start command, packet paths and the command list."""
    root = Path(root)
    commands, reason = stage_commands(state, stage, work_item)
    lines = ["", "Test loop (bound Until Loop; the loop script counts iterations, at most "
             + str(guidance3.TEST_LOOP_LIMIT) + "):"]
    if not commands:
        if reason:
            lines.append("No command to run: " + reason.rstrip(".") + ". Report done with that reason; there is no "
                         "loop to run.")
        else:
            lines.append("The accepted step plan recorded no test_commands. Report outcome blocked so "
                         "the step plan can be revised.")
        return lines
    try:
        runtime = quality._runtime(state)
    except quality.QualityError as exc:
        lines.append("Unavailable: " + str(exc) + ". Run the listed commands yourself until they pass; "
                     "ShipLoop still runs them before accepting done.")
        runtime = None
    if runtime is not None:
        contract = root / contract_path(action)
        lines += [
            "Bound Until Loop card (read in full once per context): " + runtime["runtime_card"],
            "Loop contract (written by ShipLoop; pass it unchanged): " + str(contract),
            "Start: " + shlex.join([sys.executable, runtime["runtime_cli"], "start"]) + " < "
            + shlex.quote(str(contract)),
            "Save every returned packet (stdout) to: " + str(root / latest_path(action)),
            "Save the terminal packet (stdout) to: " + str(root / terminal_path(action)),
        ]
        if not contract.is_file():
            lines.append("The loop contract is missing; report outcome blocked naming this path.")
    lines.append("Test command list (ShipLoop runs each one from " + str(state["repo"])
                 + " before accepting done):")
    lines += ["  " + str(number) + ". [" + row["suite"] + "] " + row["command"]
              for number, row in enumerate(commands, 1)]
    return lines


def rerun_lines(state: Mapping[str, Any], work_item: str, stage: str) -> List[str]:
    """Packet lines for a rerun stage: the commands ShipLoop runs before accepting done."""
    commands, _reason = stage_commands(state, stage, work_item)
    if not commands:
        return []
    return (["", "Test rerun: on done, ShipLoop runs every test command the step plan recorded from "
             + str(state["repo"]) + " and refuses unless each exits 0 (at most " + str(MAX_REFUSED_RUNS)
             + " refused runs, then only blocked):"]
            + ["  " + str(number) + ". [" + row["suite"] + "] " + row["command"]
               for number, row in enumerate(commands, 1)])


def check_terminal(root: Path, state: Mapping[str, Any], work_item: str, action: str, stage: str,
                   result: Mapping[str, Any]) -> None:
    """Refuse a test-loop result that its saved Until Loop terminal packet does not support.

    ``repeat`` is never valid.  A stage without commands, a run without a
    bound runtime, and ``blocked`` without a saved packet carry no packet to
    check; the command rerun still applies to ``done``.
    """
    outcome = result.get("outcome") if isinstance(result, Mapping) else None
    _need(outcome in ("done", "blocked"),
          stage + " accepts only done or blocked; the bound Until Loop repeats the tests, not the graph")
    if outcome == "blocked":
        return  # Always accepted: giving up honestly never needs a matching packet.
    commands, reason = stage_commands(state, stage, work_item)
    if not commands:
        _need(outcome == "blocked" or bool(reason),
              "the accepted step plan recorded no test_commands; report blocked so it can be revised")
        return
    if not state.get("improve_skill"):
        return
    root = Path(root)
    path = root / terminal_path(action)
    if outcome == "blocked" and not os.path.lexists(path):
        return
    try:
        quality.check_loop_packet(path, result, build_contract(root, state, work_item, action, stage),
                                  guidance3.TEST_LOOP_LIMIT, "test loop", str(root / contract_path(action)))
    except quality.QualityError as exc:
        raise TestLoopError(str(exc)) from exc


def _tail(data: bytes) -> str:
    text = data.decode("utf-8", "replace")
    return text if len(text) <= TAIL_CHARS else "[... " + str(len(text) - TAIL_CHARS) + " chars]\n" + text[-TAIL_CHARS:]


def verify(root: Path, state: Mapping[str, Any], work_item: str, action: str, stage: str, *,
           runner: Optional[Runner] = None, env: Optional[Mapping[str, str]] = None,
           clock: Optional[Callable[[], float]] = None,
           command_timeout: float = COMMAND_TIMEOUT_SECONDS,
           budget: float = STAGE_BUDGET_SECONDS) -> Tuple[Dict[str, str], str]:
    """Run every command of this stage once; return (record writes, refusal text).

    An empty refusal means every command exited 0.  A command that fails, times
    out, cannot start or is skipped because the stage budget ran out refuses.
    """
    root = Path(root)
    commands, _reason = stage_commands(state, stage, work_item)
    if not commands:
        return {}, ""
    refused = 0
    number = 1
    while (root / verify_path(action, number)).exists():
        prior = store.read_record(root / verify_path(action, number))
        refused += 0 if isinstance(prior, Mapping) and prior.get("passed") else 1
        number += 1
    if refused >= MAX_REFUSED_RUNS:
        return {}, ("ShipLoop test run: " + stage + " was refused " + str(refused) + " times; done is no longer "
                    "accepted for this action. Report outcome blocked, naming the failing command from "
                    + str(root / verify_path(action, number - 1)) + ", so the step plan can be revised.")
    runner = runner or lint.run_argv
    clock = clock or time.monotonic
    repo = Path(str(state["repo"]))
    environment = dict(os.environ if env is None else env)
    deadline = clock() + budget
    runs: List[Dict[str, Any]] = []
    for row in commands:
        left = deadline - clock()
        if left <= 1.0:
            runs.append({**row, "status": "skipped", "exit": None, "seconds": 0.0, "stdout": "",
                         "stderr": "the " + str(int(budget)) + "-second stage budget ran out"})
            continue
        started = clock()
        try:
            status, code, out, err = runner(["/bin/sh", "-c", row["command"]], repo,
                                            min(command_timeout, left), input_bytes=b"", env=environment)
        except OSError as exc:
            status, code, out, err = "error", None, b"", (type(exc).__name__ + ": " + str(exc)).encode()
        runs.append({**row, "status": "timeout" if status == "timeout" else ("passed" if code == 0 else "failed"),
                     "exit": code, "seconds": round(clock() - started, 3),
                     "stdout": _tail(out), "stderr": _tail(err)})
    record = {
        "schema": SCHEMA, "action": action, "stage": stage, "work_item": work_item,
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "cwd": str(repo), "passed": all(run["status"] == "passed" for run in runs), "runs": runs,
    }
    relative = verify_path(action, number)
    writes = {relative: store.dumps(record, "ShipLoop test-loop verification")}
    if record["passed"]:
        return writes, ""
    failing = [run for run in runs if run["status"] != "passed"]
    lines = ["ShipLoop test loop: " + stage + " is not done. ShipLoop ran the " + str(len(runs))
             + " listed command" + ("" if len(runs) == 1 else "s") + " from " + str(repo) + " and "
             + str(len(failing)) + " did not pass:"]
    for run in failing:
        outcome = ("timed out" if run["status"] == "timeout" else "skipped" if run["status"] == "skipped"
                   else "exit " + str(run["exit"]))
        lines.append("- [" + run["suite"] + "] " + run["command"] + " -> " + outcome)
        tail = (run["stdout"] + "\n" + run["stderr"]).strip().splitlines()[-15:]
        lines += ["    | " + line for line in tail]
    attempts = ("Refused runs for this action: " + str(refused + 1) + " of " + str(MAX_REFUSED_RUNS)
                + "; after that only blocked is accepted.")
    if stage in STAGES:
        lines.append("Fix the code, start the test loop again with the packet's start command (its terminal "
                     "packet is replaced), then submit done again; or report blocked. " + attempts
                     + " Full output: " + str(root / relative) + ".")
    else:
        lines.append("Fix the code so every command passes (never change a check to get green), then submit "
                     "done again; or report blocked. " + attempts + " Full output: " + str(root / relative) + ".")
    return writes, "\n".join(lines)


__all__ = (
    "MAX_REFUSED_RUNS",
    "RERUN_STAGES",
    "STAGES",
    "VERIFY_STAGES",
    "TestLoopError",
    "build_contract",
    "check_terminal",
    "contract_path",
    "latest_path",
    "normalise_commands",
    "render_lines",
    "rerun_lines",
    "stage_commands",
    "terminal_path",
    "transition_writes",
    "verify",
    "verify_path",
)
