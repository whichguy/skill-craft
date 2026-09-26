"""Script-enforced test loops at test-green and regression on the bound Until Loop.

The accepted step plan records the work item's test command list
(``test_commands``).  Each command may name the test IDs it must run (``ids``)
and a minimum test count (``min_tests``).  A command that exits 0 but ran no
test, too few tests, or not its named IDs is refused (``shiploop_test_counts``):
a filter that selects nothing is not passing evidence.  At ``test-red`` ShipLoop
runs the focused commands and expects them to fail inside a test, not before any
test ran.  On the transition into ``test-green`` or ``regression``
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
import shiploop_test_counts as counts

STAGES = ("test-green", "regression")
# The expected-RED control: ShipLoop runs the focused commands and expects a test failure.
RED_STAGE = "test-red"
# Stages that can edit code after the test loops: on done ShipLoop reruns every
# recorded command (no loop).
RERUN_STAGES = ("test-refine", "static-checks", "integration-verify")
VERIFY_STAGES = STAGES + RERUN_STAGES
# Refused command runs per action before only blocked is accepted.
MAX_REFUSED_RUNS = 3
SUITES = ("focused", "regression")
COMMAND_KEYS = frozenset({"command", "suite", "ids", "min_tests"})
# Statuses that count as passing.  ``passed-uncounted`` (exit 0, output not
# recognised) is allowed only for a regression command without ids or min_tests.
PASSING = ("passed", "passed-uncounted")
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


def normalise_commands(value: Any) -> List[Dict[str, Any]]:
    """Validate a step plan's ``test_commands``.

    Each entry is ``{"command": str, "suite": focused|regression}`` plus optional
    ``ids`` (test IDs the command must visibly run) and ``min_tests`` (int >= 1).
    """
    _need(isinstance(value, list), "test_commands must be a list")
    commands: List[Dict[str, Any]] = []
    for entry in value:
        _need(isinstance(entry, Mapping) and {"command", "suite"} <= set(entry) <= COMMAND_KEYS,
              "each test command has command and suite, and optionally ids and min_tests")
        command = entry.get("command")
        _need(isinstance(command, str) and command.strip() != "" and "\n" not in command
              and "\0" not in command, "a test command must be one nonblank line")
        _need(entry.get("suite") in SUITES, "a test command's suite must be focused or regression")
        row: Dict[str, Any] = {"command": command.strip(), "suite": str(entry["suite"])}
        if "ids" in entry:
            ids = entry["ids"]
            _need(isinstance(ids, list) and ids and all(
                isinstance(item, str) and item.strip() and not any(ch.isspace() for ch in item.strip())
                for item in ids), "a test command's ids must be a nonempty list of test IDs without spaces")
            cleaned = [item.strip() for item in ids]
            _need(len(set(cleaned)) == len(cleaned), "a test command's ids must not repeat")
            row["ids"] = cleaned
        if "min_tests" in entry:
            minimum = entry["min_tests"]
            _need(isinstance(minimum, int) and not isinstance(minimum, bool) and minimum >= 1,
                  "a test command's min_tests must be an integer of at least 1")
            row["min_tests"] = minimum
        commands.append(row)
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

    test-green and test-red run the focused commands; every other stage runs
    every command.
    """
    _action, result = _step_plan(state, work_item)
    if "test_commands" not in result:
        return [], ""
    commands = [dict(row) for row in result["test_commands"]
                if stage not in ("test-green", RED_STAGE) or row["suite"] == "focused"]
    if commands:
        return commands, ""
    return [], str(result.get("test_commands_na") or ("the accepted step plan lists no focused command"
                                                       if result["test_commands"] else ""))


def _listing(row: Mapping[str, Any]) -> str:
    """One command as packets show it, with the IDs and minimum ShipLoop checks."""
    text = "[" + row["suite"] + "] " + row["command"]
    if row.get("ids"):
        text += " (must run: " + ", ".join(row["ids"]) + ")"
    if row.get("min_tests"):
        text += " (at least " + str(row["min_tests"]) + " tests)"
    return text


def _work(commands: List[Dict[str, Any]]) -> str:
    listing = "\n".join(str(number) + ". " + _listing(row) for number, row in enumerate(commands, 1))
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
            "Bound Until Loop card (open it if its rules are not already in your context): " + runtime["runtime_card"],
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
    lines += ["  " + str(number) + ". " + _listing(row) for number, row in enumerate(commands, 1)]
    lines.append(COUNT_RULE)
    return lines


def rerun_lines(state: Mapping[str, Any], work_item: str, stage: str) -> List[str]:
    """Packet lines for a rerun stage: the commands ShipLoop runs before accepting done."""
    commands, _reason = stage_commands(state, stage, work_item)
    if not commands:
        return []
    return (["", "Test rerun: on done, ShipLoop runs every test command the step plan recorded from "
             + str(state["repo"]) + " and refuses unless each passes (at most " + str(MAX_REFUSED_RUNS)
             + " refused runs, then only blocked):"]
            + ["  " + str(number) + ". " + _listing(row) for number, row in enumerate(commands, 1)]
            + [COUNT_RULE])


def red_lines(state: Mapping[str, Any], work_item: str) -> List[str]:
    """Packet lines for test-red: the focused commands ShipLoop runs, expecting a test failure."""
    commands, reason = stage_commands(state, RED_STAGE, work_item)
    if not commands:
        if reason:
            return ["", "Expected-RED run: no focused command to run (" + reason.rstrip(".") + ")."]
        return []
    return (["", "Expected-RED run: on done, ShipLoop runs each focused command from " + str(state["repo"])
             + " and expects it to fail inside a test: the runner must report at least one failing test,"
             " and every listed ID must appear in the output. A failure before any test runs (syntax,"
             " import, setup) is not a meaningful RED. If these tests are expected to pass already"
             " (characterisation tests), put the reason in the result's red_na; ShipLoop still runs"
             " them and requires that they ran."]
            + ["  " + str(number) + ". " + _listing(row) for number, row in enumerate(commands, 1)])


COUNT_RULE = ("A command passes only when it exits 0 and actually ran tests: ShipLoop reads the runner's summary, "
              "refuses a run of zero tests, and checks that every listed ID appears in the output. A filter "
              "that matches nothing is not evidence; running the whole suite instead of the named cases does "
              "not satisfy a listed ID. If ShipLoop cannot read a focused command's test count, it needs ids "
              "and a runner flag that prints test names (for example --verbose).")


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


def judge(row: Mapping[str, Any], code: Optional[int], output: str, *, red: bool = False) -> Dict[str, Any]:
    """Classify one finished command run from its exit code and its own output.

    Passing mode: ``passed`` needs exit 0, a recognised count of at least
    ``min_tests`` (1 by default) and every listed ID shown; a focused command
    whose count cannot be read passes only when it lists IDs and all appear.  A
    regression command without ids or min_tests may pass uncounted.  Red mode
    (test-red): ``red`` needs a non-zero exit with at least one failing test (or,
    uncounted, every listed ID shown) and no refusal for zero tests.
    """
    tally = counts.count(output, code)
    ids = list(row.get("ids") or ())
    names = counts.named(output, ids) if ids else {"shown": [], "missing": []}
    minimum = int(row.get("min_tests") or 1)
    verdict: Dict[str, Any] = {"counts": tally, "ids_missing": names["missing"]}
    if red:
        if tally is not None and tally["ran"] == 0:
            verdict["status"] = "no-tests"
        elif code == 0:
            verdict["status"] = "green"
        elif tally is not None and tally["failed"] == 0:
            verdict["status"] = "not-red"
        elif names["missing"]:
            verdict["status"] = "ids-missing"
        elif tally is None and not ids:
            verdict["status"] = "uncounted"
        else:
            verdict["status"] = "red"
        return verdict
    if code != 0:
        verdict["status"] = "no-tests" if tally is not None and tally["ran"] == 0 else "failed"
    elif tally is not None and tally["ran"] == 0:
        verdict["status"] = "no-tests"
    elif tally is not None and tally["ran"] < minimum:
        verdict["status"] = "too-few-tests"
    elif names["missing"]:
        verdict["status"] = "ids-missing"
    elif tally is not None or ids:
        verdict["status"] = "passed"
    elif row["suite"] == "regression" and "min_tests" not in row:
        verdict["status"] = "passed-uncounted"
    else:
        verdict["status"] = "uncounted"
    return verdict


def _explain(run: Mapping[str, Any]) -> str:
    """One refusal reason for a run, written for the model that has to fix it."""
    status = run["status"]
    tally = run.get("counts")
    seen = ("" if tally is None else " (" + "/".join(tally["runners"]) + " reported " + str(tally["ran"])
            + " run, " + str(tally["failed"]) + " failed)")
    ids = run.get("ids") or ()
    target = ("so the output names " + ", ".join(ids)) if ids else "so it runs this item's tests"
    if status == "no-tests":
        return ("ran no tests" + seen + ": the selection matched nothing, or the suite failed before any test "
                "ran. A run with no executed test is not evidence. Fix the filter, the test names or the setup "
                + target + "; running the whole suite instead does not satisfy this.")
    if status == "too-few-tests":
        return ("ran fewer tests than the step plan requires (at least " + str(run.get("min_tests")) + ")"
                + seen + ".")
    if status == "ids-missing":
        return ("did not show " + ", ".join(run["ids_missing"]) + " running" + seen + ". Make the command select "
                "those cases and print test names (for example --verbose).")
    if status == "uncounted":
        return ("exited " + str(run["exit"]) + ", but ShipLoop could not read how many tests it ran. Give the "
                "command ids and a runner flag that prints test names, or use a runner ShipLoop recognises.")
    if status == "green":
        return ("passed, but test-red expects the new tests to fail before implementation. If they are meant to "
                "pass already, give the reason in red_na.")
    if status == "not-red":
        return ("failed without any failing test" + seen + ": a syntax, import or setup error is not a "
                "meaningful RED. Fix the test setup so the tests run and fail on the missing behaviour.")
    if status == "timeout":
        return "timed out"
    if status == "skipped":
        return "skipped (" + str(run.get("stderr") or "the stage budget ran out") + ")"
    return "exit " + str(run["exit"])


def verify(root: Path, state: Mapping[str, Any], work_item: str, action: str, stage: str, *,
           runner: Optional[Runner] = None, env: Optional[Mapping[str, str]] = None,
           clock: Optional[Callable[[], float]] = None,
           command_timeout: float = COMMAND_TIMEOUT_SECONDS,
           budget: float = STAGE_BUDGET_SECONDS, red_na: Optional[str] = None,
           commands: Optional[List[Dict[str, Any]]] = None) -> Tuple[Dict[str, str], str]:
    """Run every command of this stage once; return (record writes, refusal text).

    An empty refusal means every command passed (``judge``).  At test-red each
    focused command must fail inside a test, unless ``red_na`` gives the reason
    the tests already pass; then they must pass and must have run.  A command
    that times out, cannot start or is skipped because the stage budget ran out
    refuses.
    """
    root = Path(root)
    if commands is None:
        commands, _reason = stage_commands(state, stage, work_item)
    if not commands:
        return {}, ""
    red = stage == RED_STAGE and not red_na
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
        run: Dict[str, Any] = {**row, "exit": code, "seconds": round(clock() - started, 3),
                               "stdout": _tail(out), "stderr": _tail(err)}
        if status == "timeout":
            run["status"] = "timeout"
        elif code is None:
            run["status"] = "failed"
        else:
            output = out.decode("utf-8", "replace") + "\n" + err.decode("utf-8", "replace")
            run.update(judge(row, code, output, red=red))
        runs.append(run)
    good = ("red",) if red else PASSING
    record = {
        "schema": SCHEMA, "action": action, "stage": stage, "work_item": work_item,
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "cwd": str(repo), "passed": all(run["status"] in good for run in runs), "runs": runs,
    }
    if stage == RED_STAGE:
        record["expect"] = "red" if red else "green (red_na: " + str(red_na) + ")"
    relative = verify_path(action, number)
    writes = {relative: store.dumps(record, "ShipLoop test-loop verification")}
    if record["passed"]:
        return writes, ""
    failing = [run for run in runs if run["status"] not in good]
    lines = ["ShipLoop test run: " + stage + " is not done. ShipLoop ran the " + str(len(runs))
             + " listed command" + ("" if len(runs) == 1 else "s") + " from " + str(repo) + " and "
             + str(len(failing)) + (" did not fail as expected:" if red else " did not pass:")]
    for run in failing:
        lines.append("- [" + run["suite"] + "] " + run["command"] + " -> " + _explain(run))
        tail = (run["stdout"] + "\n" + run["stderr"]).strip().splitlines()[-15:]
        lines += ["    | " + line for line in tail]
    attempts = ("Refused runs for this action: " + str(refused + 1) + " of " + str(MAX_REFUSED_RUNS)
                + "; after that only blocked is accepted.")
    if stage in STAGES:
        lines.append("Fix the code, start the test loop again with the packet's start command (its terminal "
                     "packet is replaced), then submit done again; or report blocked. " + attempts
                     + " Full output: " + str(root / relative) + ".")
    elif red:
        lines.append("Fix the tests or their setup (not the product code), then submit done again; or report "
                     "blocked. " + attempts + " Full output: " + str(root / relative) + ".")
    else:
        lines.append("Fix the code so every command passes (never change a check to get green), then submit "
                     "done again; or report blocked. " + attempts + " Full output: " + str(root / relative) + ".")
    return writes, "\n".join(lines)


__all__ = (
    "MAX_REFUSED_RUNS",
    "PASSING",
    "RED_STAGE",
    "RERUN_STAGES",
    "STAGES",
    "VERIFY_STAGES",
    "TestLoopError",
    "build_contract",
    "check_terminal",
    "contract_path",
    "latest_path",
    "judge",
    "normalise_commands",
    "red_lines",
    "render_lines",
    "rerun_lines",
    "stage_commands",
    "terminal_path",
    "transition_writes",
    "verify",
    "verify_path",
)
