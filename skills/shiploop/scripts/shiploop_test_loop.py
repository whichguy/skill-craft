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
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Tuple

import shiploop_lint as lint
import shiploop_loop_contract as loop_contract
import shiploop_prompts as guidance
import shiploop_quality as quality
import shiploop_stage_spec as stage_spec
import shiploop_store as store
import shiploop_test_counts as counts

STAGES = stage_spec.with_complete_run("test-loop")
# The expected-RED control: ShipLoop runs the focused commands and expects a test failure.
RED_STAGE, = stage_spec.with_complete_run("test-red")
# Stages that can edit code after the test loops: on done ShipLoop reruns every
# recorded command (no loop).
RERUN_STAGES = stage_spec.with_complete_run("test-rerun")
VERIFY_STAGES = STAGES + RERUN_STAGES
# Product failures per action before done is no longer accepted (then the stage's own
# remedy outcome, or blocked).  Attempts that only failed to run do not count: see
# UNAVAILABLE and refused_runs.
MAX_REFUSED_RUNS = 7
# focused and regression commands run tests; a check (for example a search that a
# document names a required term) is judged by its exit code alone.
SUITES = ("focused", "regression", "check")
COMMAND_KEYS = frozenset({"command", "suite", "ids", "min_tests", "criteria"})
# Statuses that count as passing.  ``passed-uncounted`` (exit 0, output not
# recognised) is allowed only for a regression command without ids or min_tests.
PASSING = ("passed", "passed-uncounted")
# Statuses where the command never reached a verdict about the product: it timed
# out, could not start, or was skipped because the invocation's budget ran out.
# These still refuse the stage -- nothing is accepted on unrun tests -- but they
# are not evidence that the product or its step plan is wrong, so they do not
# count toward MAX_REFUSED_RUNS.  A timeout is not a diagnosis: it can mean a
# product deadlock, a broken test, a slow valid suite or an external dependency,
# so it never asserts who must repair it.
UNAVAILABLE = ("timeout", "skipped", "error")
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


def terminal_path(action: str) -> str:
    return "tests/" + action + "-terminal.json"


def verify_path(action: str, number: int) -> str:
    return "tests/" + action + "-verify" + str(number) + ".md"


def normalise_commands(value: Any) -> List[Dict[str, Any]]:
    """Validate a step plan's ``test_commands``.

    Each entry is ``{"command": str, "suite": focused|regression|check}`` plus
    optional ``ids`` (test IDs the command must visibly run), ``min_tests``
    (int >= 1) and ``criteria`` (the step plan's criterion IDs it confirms).  A
    ``check`` is judged by its exit code, so it takes no ids or min_tests.
    """
    _need(isinstance(value, list), "test_commands must be a list")
    commands: List[Dict[str, Any]] = []
    for entry in value:
        _need(isinstance(entry, Mapping) and {"command", "suite"} <= set(entry) <= COMMAND_KEYS,
              "each test command has command and suite, and optionally ids, min_tests and criteria")
        command = entry.get("command")
        _need(isinstance(command, str) and command.strip() != "" and "\n" not in command
              and "\0" not in command, "a test command must be one nonblank line")
        _need(entry.get("suite") in SUITES, "a test command's suite must be focused, regression or check")
        _need(entry.get("suite") != "check" or not {"ids", "min_tests"} & set(entry),
              "a check command is judged by its exit code and takes no ids or min_tests")
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
        if "criteria" in entry:
            criteria = entry["criteria"]
            _need(isinstance(criteria, list) and criteria and all(
                isinstance(item, str) and item.strip() and not any(ch.isspace() for ch in item.strip())
                for item in criteria) and len(set(criteria)) == len(criteria),
                "a test command's criteria must be a nonempty list of distinct criterion IDs")
            row["criteria"] = [item.strip() for item in criteria]
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


# OUTER stages whose done reruns commands another stage recorded:
# stage -> (recording stage, result field).
OUTER_SOURCES = {
    "system-test": ("system-test-author", "system_commands"),
    "release-verify": ("release-plan", "consumer_checks"),
}


def _latest_root_result(state: Mapping[str, Any], stage: str) -> Mapping[str, Any]:
    """The latest accepted done result of a root stage, or an empty mapping."""
    for row in reversed(state.get("history", ())):
        if row.get("stage") == stage and row.get("workitem") is None and row.get("outcome") == "done":
            result = state.get("accepted", {}).get(row.get("action"))
            return result if isinstance(result, Mapping) else {}
    return {}


def stage_commands(state: Mapping[str, Any], stage: str, work_item: str) -> Tuple[List[Dict[str, str]], str]:
    """This stage's commands and, when there are none, why.

    test-green and test-red run the focused commands; every other stage runs
    every command.
    """
    if stage in OUTER_SOURCES:
        source, field = OUTER_SOURCES[stage]
        result = _latest_root_result(state, source)
        commands = [dict(row) for row in result.get(field) or ()]
        return commands, ("" if commands else str(result.get(field + "_na") or ""))
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
    return guidance.TEST_ITERATION + "Test command list:\n" + listing + "\n"


def _contract(repo: str, title: str, work_item: str, stage: str, work: str,
              resources: List[Dict[str, str]]) -> Dict[str, Any]:
    return loop_contract.contract(
        workspace=repo,
        work=work,
        exit_condition=guidance.TEST_EXIT_CONDITION,
        repeat_condition=guidance.TEST_REPEAT_CONDITION,
        required_trivial_reviews=1,
        request=("Test loop (" + stage + ") for ShipLoop work item " + work_item + " ("
                 + title + "): run its test command list and fix "
                 "the code until every command exits 0."),
        scope=("Workspace " + repo + ". The files in " + work_item + "'s change and their tests. "
               "Preserve every other change."),
        authority=("Edit in-scope product code and tests. Never change a check's expected result "
                   "to get green. Do not commit, push, install or download anything. ShipLoop "
                   "callbacks belong to the parent; the loop never calls them."),
        environment="Run every command from " + repo + ".",
        resources=resources,
    )


def build_contract(root: Path, state: Mapping[str, Any], work_item: str, action: str,
                   stage: str) -> Dict[str, Any]:
    """Return the Until Loop start contract for one test-green or regression action."""
    _need(stage in STAGES, "no test loop runs at " + stage)
    commands, _reason = stage_commands(state, stage, work_item)
    _need(bool(commands), "the accepted step plan lists no command for the " + stage + " test loop")
    root = Path(root)
    repo = str(state["repo"])
    step_action, _result = _step_plan(state, work_item)
    return _contract(
        repo, quality._work_title(state, work_item), work_item, stage, _work(commands),
        [{"purpose": "accepted step plan: test_commands and completion criteria",
          "locator": str(root / "results" / (str(step_action) + ".md"))},
         {"purpose": "this action's pass log: append what each iteration checked and what is left",
          "locator": str(root / "notes" / (action + ".md"))}])


def listing_problem(rows: Sequence[Mapping[str, Any]]) -> Optional[str]:
    """Why a submitted command list could never fit a test-loop contract, or None when it fits.

    The contract is written at a transition, where nothing can be refused, so the list is checked where the
    model submits it. Paths and the title are costed generously; every command is counted (the regression
    stage lists them all, a superset of the focused list).
    """
    try:
        listing = _work([dict(row) for row in rows])
    except (KeyError, TypeError):
        return None  # a malformed row is refused by the shape check
    path = "/" + "x" * 300
    resources = [{"purpose": "accepted step plan: test_commands and completion criteria", "locator": path},
                 {"purpose": "this action's pass log: append what each iteration checked and what is left",
                  "locator": path}]
    empty = loop_contract.compact_bytes(_contract(path, "t" * 200, "W" * 8, "regression", _work([]), resources))
    full = loop_contract.compact_bytes(_contract(path, "t" * 200, "W" * 8, "regression", listing, resources))
    if full <= loop_contract.CONTRACT_BUDGET:
        return None
    room = loop_contract.CONTRACT_BUDGET - empty
    return (f"the test command list renders to {full - empty:,} bytes, but the test loop's contract holds only about "
            f"{room:,} bytes of it (the Until Loop keeps its whole state in {loop_contract.STATE_LIMIT:,} bytes and "
            "needs room for its first report): shorten the ids lists, drop duplicate commands, or split this work "
            "item into smaller steps")


def transition_writes(root: Path, after: Mapping[str, Any], work_item: Optional[str],
                      action: Optional[str], stage: str) -> Dict[str, str]:
    """The contract write for a newly issued test-loop action (none when the stage has no command)."""
    if not work_item or not action or stage not in STAGES:
        return {}
    commands, _reason = stage_commands(after, stage, work_item)
    if not commands:
        return {}
    contract = build_contract(Path(root), after, work_item, action, stage)
    return {contract_path(action): loop_contract.dumps(contract)}


def render_lines(root: Path, state: Mapping[str, Any], work_item: str, action: str, stage: str) -> List[str]:
    """Read-only packet lines: runtime, start command, packet paths and the command list."""
    root = Path(root)
    commands, reason = stage_commands(state, stage, work_item)
    lines = ["", "Test loop (bound Until Loop; the loop script counts iterations; there is no "
             "iteration limit):"]
    if not commands:
        if reason:
            lines.append("No command to run: " + reason.rstrip(".") + ". Report done with that reason; there is no "
                         "loop to run.")
        else:
            lines.append("The accepted step plan recorded no test_commands. Report outcome revise so "
                         "the step plan records them.")
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
            "Start: " + shlex.join([sys.executable, runtime["runtime_cli"], "start",
                                     "--receipt", str(root / terminal_path(action))]) + " < "
            + shlex.quote(str(contract)),
            quality.RECEIPT_LINE + str(root / terminal_path(action)),
        ]
        if (root / terminal_path(action)).exists():
            lines.append(quality.RESUME_LINE)
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
             + " refused runs, then " + _remedy_sentence(stage) + "; a command that times out, cannot "
             "start or is skipped on budget refuses the stage without counting):"]
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
    _need(outcome in ("done", "revise", "blocked"),
          stage + " accepts only done, revise or blocked; the bound Until Loop repeats the tests, not the graph")
    if outcome == "blocked":
        return  # Blocked needs blocked_by (user, access, external), checked by the navigator.
    commands, reason = stage_commands(state, stage, work_item)
    if not commands:
        _need(outcome == "revise" or bool(reason),
              "the accepted step plan recorded no test_commands; report revise so the step plan records them")
        return
    if outcome == "revise" and refused_runs(root, action) >= MAX_REFUSED_RUNS:
        return  # ShipLoop's own runs already failed MAX_REFUSED_RUNS times.
    if not state.get("improve_skill"):
        return
    root = Path(root)
    path = root / terminal_path(action)
    if outcome == "blocked" and not os.path.lexists(path):
        return
    try:
        quality.check_loop_packet(path, result, build_contract(root, state, work_item, action, stage),
                                  "test loop", str(root / contract_path(action)))
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
    if row.get("suite") == "check" and not red:
        return {"counts": None, "ids_missing": [], "status": "passed" if code == 0 else "failed"}
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
        return ("timed out, so it reached no verdict about the product. This is not a diagnosis: it can mean a "
                "deadlock, a broken test, a suite too slow for this budget or an external dependency.")
    if status == "skipped":
        return "skipped (" + str(run.get("stderr") or "the stage budget ran out") + ")"
    if status == "error":
        detail = ((run.get("stderr") or "").strip().splitlines() or ["no detail"])[-1]
        return ("could not start: " + detail
                + ". The command never ran, so this says nothing about the product.")
    return "exit " + str(run["exit"])


def _verify_count(root: Path, action: str) -> int:
    """How many ShipLoop test-run records this action has."""
    number = 0
    while (Path(root) / verify_path(action, number + 1)).exists():
        number += 1
    return number


def _disposition(runs: List[Dict[str, Any]], good: Tuple[str, ...]) -> str:
    """One attempt's verdict: ``passed``, ``failed`` or ``could-not-run``.

    A real failing check beside a timeout is still ``failed``: an unavailable
    command never erases a verdict another command did reach.
    """
    if all(run["status"] in good for run in runs):
        return "passed"
    if any(run["status"] not in good and run["status"] not in UNAVAILABLE for run in runs):
        return "failed"
    return "could-not-run"


def _remedy(stage: str) -> str:
    """The outcome this stage offers when its own runs keep refusing, from the stage contract.

    INNER verify stages take the item back to its step plan (``revise``).  The
    OUTER ``system-test`` and ``release-verify`` have no step plan to revise and
    take corrective work items instead (``replan``), which the navigator requires
    with the result.

    ``verify`` is also called with a label that is not a graph stage at all --
    the navigator's ``end-of-work review`` gate -- which has no remedy outcome
    and must not raise here.
    """
    row = stage_spec.STAGE_SPEC.get(stage)
    if row is None:
        return ""
    for candidate in ("revise", "replan"):
        if candidate in row.outcomes:
            return candidate
    return ""


def _remedy_sentence(stage: str) -> str:
    """What the packet says the stage's remedy outcome does, in the stage's own terms."""
    remedy = _remedy(stage)
    if remedy == "revise":
        return "the item goes back to its step plan (revise)"
    if remedy == "replan":
        return "the outer loop takes corrective work items (replan)"
    return "the stage reports blocked"


def refused_runs(root: Path, action: str) -> int:
    """How many of this action's ShipLoop test runs the product failed.

    An attempt whose only non-passing commands were unavailable (``UNAVAILABLE``:
    timed out, could not start, skipped on budget) is not evidence against the
    product, so it does not count here.  It still refused its stage at the time.
    A record written before the disposition field existed counts as a failure,
    which is what it meant then.
    """
    refused = 0
    for number in range(1, _verify_count(root, action) + 1):
        prior = store.read_record(Path(root) / verify_path(action, number))
        if not isinstance(prior, Mapping):
            refused += 1
            continue
        if prior.get("passed") or prior.get("disposition") == "could-not-run":
            continue
        refused += 1
    return refused


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
    that times out, cannot start or is skipped because the invocation's budget
    ran out refuses the stage, but the attempt is recorded ``could-not-run`` and
    does not count toward ``MAX_REFUSED_RUNS``: see ``_disposition``.  ``budget``
    and ``command_timeout`` bound this one invocation, not the stage's total time.
    """
    root = Path(root)
    if commands is None:
        commands, _reason = stage_commands(state, stage, work_item)
    if not commands:
        return {}, ""
    red = stage == RED_STAGE and not red_na
    refused = refused_runs(root, action)
    number = _verify_count(root, action) + 1
    if refused >= MAX_REFUSED_RUNS:
        remedy = _remedy(stage)
        instruction = ("Report outcome " + remedy + ", naming the failing command from "
                       + str(root / verify_path(action, number - 1))
                       + (", so the step plan is revised" if remedy == "revise"
                          else ", with the corrective work_items the outer loop must run")
                       + "; report ") if remedy else "Report "
        return {}, ("ShipLoop test run: " + stage + " was refused " + str(refused) + " times; done is no longer "
                    "accepted for this action. " + instruction + "blocked only if the user, an access grant "
                    "or an outside dependency must unblock it.")
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
        if status in UNAVAILABLE:
            # Keep the runner's own unavailable status, including the "error" an
            # OSError set above: it exits with no code, so the next branch would
            # otherwise record a spawn failure as a test failure.
            run["status"] = status
        elif code is None:
            run["status"] = "failed"
        else:
            output = out.decode("utf-8", "replace") + "\n" + err.decode("utf-8", "replace")
            run.update(judge(row, code, output, red=red))
        runs.append(run)
    good = ("red",) if red else PASSING
    disposition = _disposition(runs, good)
    record = {
        "schema": SCHEMA, "action": action, "stage": stage, "work_item": work_item,
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "cwd": str(repo), "passed": disposition == "passed", "disposition": disposition,
        "runs": runs,
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
    if disposition == "could-not-run":
        # This attempt does not spend one of the refused runs, so the gate that would
        # otherwise force the stage's remedy cannot fire on it.  Name the routes out
        # explicitly instead, or a command that always hangs has none.
        remedy = _remedy(stage)
        attempts = ("No command reached a verdict about the product, so this attempt does not count toward "
                    "the " + str(MAX_REFUSED_RUNS) + " refused runs (still at " + str(refused) + "). Nothing is "
                    "accepted on unrun tests. A command that hangs or fails to start because of this item's "
                    "own code, test or fixture is yours to fix here and is not a blocker"
                    + ("; if the recorded command or its budget is itself wrong, report " + remedy
                       + " rather than retrying it" if remedy else "")
                    + ". Report blocked only for what the user, an access grant or an outside dependency "
                      "must supply.")
    else:
        attempts = ("Refused runs for this action: " + str(refused + 1) + " of " + str(MAX_REFUSED_RUNS)
                    + "; after that " + _remedy_sentence(stage) + ".")
    if stage in STAGES:
        lines.append("Fix the code, start the test loop again with the packet's start command (its terminal "
                     "packet is replaced), then submit done again. " + attempts
                     + " Full output: " + str(root / relative) + ".")
    elif red:
        lines.append("Fix the tests or their setup (not the product code), then submit done again. " + attempts + " Full output: " + str(root / relative) + ".")
    else:
        lines.append("Fix the code so every command passes (never change a check to get green), then submit "
                     "done again. " + attempts + " Full output: " + str(root / relative) + ".")
    return writes, "\n".join(lines)


__all__ = (
    "MAX_REFUSED_RUNS",
    "PASSING",
    "RED_STAGE",
    "RERUN_STAGES",
    "STAGES",
    "UNAVAILABLE",
    "VERIFY_STAGES",
    "TestLoopError",
    "build_contract",
    "check_terminal",
    "contract_path",
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
