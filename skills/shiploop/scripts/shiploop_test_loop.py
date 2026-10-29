"""ShipLoop's own test runs: the test stage's base and candidate runs, and the reruns at document and the outer stages.

The accepted step plan records the work item's test command list (``test_commands``).  Each command may name the test
IDs it must run (``ids``) and a minimum test count (``min_tests``).  A command that exits 0 but ran no test, too few
tests, or not its named IDs is refused (``shiploop_test_counts``): a filter that selects nothing is not passing evidence.

The ``test`` stage runs after implement: the model writes the tests and, inside its Until Loop (``shiploop_loops``,
which owns the contract and the terminal check), runs every recorded command and fixes until all pass.  On ``done``
ShipLoop runs three things itself, in this order:

- ``base_check``: every focused and regression command in a temporary detached Git worktree at the item's lint base
  (``shiploop_lint.read_base``), with only this item's test files copied in.  A test ID new at this step (``new_ids``,
  not named in the result's ``red_na``) must not pass there: it must fail, or be missing because a file this item adds
  cannot be loaded.  An earlier step's cases already pass there, so a command holding only those is counted, not judged.
  The run records each command's base count, which sets the floor.
- ``loop_run``: every recorded command (focused, regression, check) on the candidate.  Each must exit 0, show every
  listed ID and run at least its floor: the larger of the base count and the most any earlier run of this action ran,
  less the tests the result's ``retired_tests`` retires that the base run showed.

- ``mutation_check`` (``shiploop_mutation``): the focused commands on single-line mutants of the item's changed
  product lines, in a temporary copy of the candidate; refused when at least one mutant ran and none was killed.  The
  base run's rule that a load failure of an added file counts as RED stays, because on new code nothing can run on
  the base; this check is what proves the tests assert real behaviour.

All three refusals count in ``refused_runs`` (one shared tally per action, shown to the model; no count stops the
work); a run that times out or cannot start refuses without counting (``UNAVAILABLE``), and ``remedy_open`` then
accepts the stage's remedy.

Commands are shell strings the step plan recorded; ShipLoop runs them with ``/bin/sh -c`` (owner decision 2026-09-25),
each bounded by its own hang guard (``COMMAND_TIMEOUT_SECONDS``); a run has no total time budget.  Rendering reads files and never runs a command.

One exception: ``release-verify`` is the stage whose done-when is "observed where consumers use it".  In an isolated
run with a completed return it runs the consumer checks in a clean copy of exactly the tree that return delivered
(never the user's checkout, never the work area); without a completed return it runs in the work area and says so
(see ``observation``).

Known limits of the base run: ignored files are not in the worktree, so only the dependency directories the platform
cards list (``shiploop_mutation.dependency_directories``) are linked in from the checkout; a command that names the
checkout by an absolute path runs there, not on the base; and an ID ShipLoop cannot read an outcome for (a reporter
that marks no pass or fail) is refused, not guessed.
"""

from __future__ import annotations

import os
import re
import shutil
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, List, Mapping, Optional, Sequence, Tuple

import shiploop_iteration as iteration
import shiploop_lint as lint
import shiploop_prompts as guidance
import shiploop_stage_spec as stage_spec
import shiploop_store as store
import shiploop_test_counts as counts
import shiploop_workspace as workspace

# The test stage: ShipLoop's candidate run of every recorded command at complete.
STAGES = stage_spec.with_complete_run("test-loop")
# Where the base run happens first (the same stage).
BASE_STAGES = stage_spec.with_complete_run("test-base")
# Stages that can edit code after the test stage: on done ShipLoop reruns every recorded command (no loop of its own).
RERUN_STAGES = stage_spec.with_complete_run("test-rerun")
# The inner rerun stage that closes a step: it reruns the step's own commands, not every one the step plan recorded.
STEP_RERUN_STAGE = "document"
VERIFY_STAGES = STAGES + RERUN_STAGES
# The stage whose inline step action runs its step plan's Proof (``step_proof``): implement.
STEP_PROOF_STAGES = stage_spec.with_complete_run("step-proof")
# focused and regression commands run tests; a check (for example a lint, type or build command) is judged by its exit
# code alone.
SUITES = ("focused", "regression", "check")
COUNTED_SUITES = ("focused", "regression")
# ``regression`` (true, on a focused row only) is what a regression row folded into a byte-identical focused one leaves
# (``normalise_commands``): the drift check at system-test still runs that command as the default suite.
# ``minimum`` (true, on a regression command or a focused row that is also the regression command) marks the minimum
# regression, which runs at every step; an unmarked regression command runs at the item's last step only (design T §9.1
# 2d, ``iteration.active_commands``).
COMMAND_KEYS = frozenset({"command", "suite", "ids", "min_tests", "criteria", "host_dependent", "regression", "target",
                          "minimum"})
# Statuses that count as passing.  ``passed-uncounted`` (exit 0, output not recognised) is allowed only for a
# regression command without ids or min_tests.
PASSING = ("passed", "passed-uncounted")
# Statuses where the command never reached a verdict about the product: it timed out or could not start.  These still
# refuse the stage -- nothing is accepted on unrun tests -- but they are not evidence that the product or its step plan
# is wrong, so they do not count in refused_runs.  A timeout is not a diagnosis: it can mean a product deadlock, a
# broken test, a slow valid suite or an external dependency, so it never asserts who must repair it.
UNAVAILABLE = ("timeout", "error")
# The hang guard of one command (it stops that command, never the run).
COMMAND_TIMEOUT_SECONDS = 600.0
TAIL_CHARS = 6000
SCHEMA = "shiploop-test-loop/v1"
BASE_SCHEMA = "shiploop-test-base/v1"
# Result fields of the test stage, validated by ``check_result_fields``.
RED_NA = "red_na"
RETIRED_TESTS = "retired_tests"

Runner = Callable[..., Tuple[str, Optional[int], bytes, bytes]]


class TestLoopError(ValueError):
    """A test-stage result or ShipLoop's own run of its commands does not satisfy the stage."""


def _need(condition: bool, message: str) -> None:
    if not condition:
        raise TestLoopError(message)


def verify_path(action: str, number: int) -> str:
    """ShipLoop's candidate (or rerun) record number ``number`` of one action."""
    return "tests/" + action + "-verify" + str(number) + ".md"


def base_path(action: str, number: int) -> str:
    """ShipLoop's base-run record number ``number`` of one test action."""
    return "tests/" + action + "-base" + str(number) + ".md"


def red_check_path(action: str) -> str:
    """The red-check report: a base run the loop asks for, replaced on each call and never counted."""
    return "tests/" + action + "-red-check.md"


def check_only_path(action: str) -> str:
    """The candidate run ``complete --check-only`` asks for: replaced on each call, never counted, never a floor."""
    return "tests/" + action + "-check-only.md"


def step_proof_path(action: str, number: int) -> str:
    """ShipLoop's run number ``number`` of an inline implement step's Proof (``step_proof``)."""
    return "tests/" + action + "-step-proof" + str(number) + ".md"


def step_proof_check_only_path(action: str) -> str:
    """The Proof run ``complete --check-only`` asks for: replaced on each call, never counted."""
    return "tests/" + action + "-step-proof-check-only.md"


def mutation_path(action: str, number: int) -> str:
    """ShipLoop's mutation-check record number ``number`` of one test action (``shiploop_mutation``)."""
    return "tests/" + action + "-mutation" + str(number) + ".md"


def mutation_check_only_path(action: str) -> str:
    """The mutation check ``complete --check-only`` asks for: replaced on each call, never counted."""
    return "tests/" + action + "-mutation-check-only.md"


# What a one-line refusal adds (the check, the step check and the test command): a live run read three validators'
# source to learn that an escaped newline inside the JSON string still makes two lines (a live run, 2026-10-19).
ONE_LINE_HINT = ("; join steps with && or ; on that line (a \\n written inside the JSON string is decoded to a "
                 "newline before this check runs, so it fails it)")


# A command whose first program checks for a file or prints a path, before any test runs (run-5 batch F2).  On the
# item's base such a guard fails on the missing file and prints its own message, which reads as RED although no test
# ran: a live run's third item (2026-10-20) and the fork's experiment E3 (2026-10-24, 1 of 4 samples under 2.8.0) both
# did it, the second with an echoed "Cannot find module" that the base run scored as a load failure.  The rule is
# the experiment's evaluator's (test/shiploop_e2e/evaluators/e3_red.py), cut to the first program the command runs.
_FILE_OPERATORS = frozenset(("-e", "-f", "-d", "-s"))
_PRINTS_A_PATH = re.compile(r"^(?:printf\s+'%s\\n'\s+\S+|echo\s+\S+\.\w+)\s*$")


def guarded(command: str) -> bool:
    """Whether ``command`` starts with a file-existence check or a printed path (F2).

    A file test is ``test``, ``[`` or ``[[`` with a file operator (``-e``, ``-f``, ``-d``, ``-s``), or ``ls`` or ``stat``;
    a ``test "$(./sum 1 2)" -eq 3`` asserts behaviour and is no guard.  The shell forms state the rule; no language's
    file API is named (ShipLoop stays generic)."""
    for segment in re.split(r"&&|\|\||[;\n]", command):
        words = segment.split()
        while words and (words[0] in ("!", "if", "then", "env") or re.match(r"^\w+=", words[0])):
            words = words[1:]
        if not words or words[0] == "cd":
            continue
        program = words[0].rsplit("/", 1)[-1]
        if program in ("test", "[", "[["):
            operands = [word for word in words[1:] if word != "!"]
            return bool(operands) and operands[0] in _FILE_OPERATORS
        return program in ("ls", "stat") or bool(_PRINTS_A_PATH.match(" ".join(words)))
    return False


def normalise_commands(value: Any) -> List[Dict[str, Any]]:
    """Validate a step plan's ``test_commands``.

    Each entry is ``{"command": str, "suite": focused|regression|check}`` plus
    optional ``ids`` (test IDs the command must visibly run), ``min_tests``
    (int >= 1), ``criteria`` (the step plan's criterion IDs it confirms),
    ``target`` (the test-strategy targets row it runs on, F3),
    ``host_dependent`` (true: its cases need a host tool, so no default suite may
    run them; see ``default_suite_drift``) and ``minimum`` (true, on a regression
    command: the minimum regression, which runs at every step).  A ``check`` is
    judged by its exit code, so it takes no ids or min_tests.

    Rows that record the same command string are folded into the first of them
    when one row can check exactly what they did (``_fold``), so ShipLoop runs
    each command once per run and the packets list it once.
    """
    _need(isinstance(value, list), "test_commands must be a list")
    commands: List[Dict[str, Any]] = []
    for entry in value:
        _need(isinstance(entry, Mapping) and {"command", "suite"} <= set(entry) <= COMMAND_KEYS,
              "each test command has command and suite, and optionally ids, min_tests and criteria")
        command = entry.get("command")
        _need(isinstance(command, str) and command.strip() != "" and "\n" not in command
              and "\0" not in command, "a test command must be one nonblank line" + ONE_LINE_HINT)
        _need(entry.get("suite") in SUITES, "a test command's suite must be focused, regression or check")
        _need(entry.get("suite") != "check" or not {"ids", "min_tests"} & set(entry),
              "a check command is judged by its exit code and takes no ids or min_tests")
        row: Dict[str, Any] = {"command": command.strip(), "suite": str(entry["suite"])}
        if "ids" in entry:
            ids = entry["ids"]
            _need(isinstance(ids, list) and ids and all(
                isinstance(item, str) and item.strip() and not any(character.isspace() for character in item.strip())
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
                isinstance(item, str) and item.strip() and not any(character.isspace() for character in item.strip())
                for item in criteria) and len(set(criteria)) == len(criteria),
                "a test command's criteria must be a nonempty list of distinct criterion IDs")
            row["criteria"] = [item.strip() for item in criteria]
        if "host_dependent" in entry:
            _need(entry["host_dependent"] is True, "a test command's host_dependent must be true when given")
            row["host_dependent"] = True
        if "regression" in entry:
            _need(entry["regression"] is True and row["suite"] == "focused",
                  "a test command's regression is true, on a focused command that is also the regression command")
            row["regression"] = True
        if "minimum" in entry:
            _need(entry["minimum"] is True and (row["suite"] == "regression" or row.get("regression") is True),
                  "a test command's minimum is true, on a regression command (or a focused command that is also the "
                  "regression command): it marks the minimum regression, which runs at every step")
            row["minimum"] = True
        if "target" in entry:
            # The test-strategy target the command runs on (run-5 batch F3); the step-plan gate checks the name.
            _need(isinstance(entry["target"], str) and entry["target"].strip() != "" and "\n" not in entry["target"],
                  "a test command's target names one test-strategy targets row")
            row["target"] = " ".join(entry["target"].split())
        commands.append(row)
    # Fold until nothing folds: one pass can make two rows foldable that were not, and the result must be canonical
    # (normalising it again changes nothing).  Each pass that changes the list shortens it.
    while True:
        folded: List[Dict[str, Any]] = []
        for row in commands:
            for index, kept in enumerate(folded):
                merged = _fold(kept, row)
                if merged is not None:
                    folded[index] = merged
                    break
            else:
                folded.append(row)
        if folded == commands:
            return commands
        commands = folded


def _fold(first: Mapping[str, Any], row: Mapping[str, Any]) -> Optional[Dict[str, Any]]:
    """``first`` and ``row`` as one row, or None when they differ or one row cannot check what both did.

    They fold when they record the same command string, host_dependent and target, and either share a suite, or one is focused
    and the other a regression row whose ids are all ids of the focused one (a regression ID is not new, so it must not
    come under the base run's rule that a focused ID fails on the base).  The one row keeps ``first``'s place, the union
    of the ids and criteria and the larger min_tests: the same output is judged against both rows' terms.  A check and
    a counted row are judged differently and never fold.  A regression row folded into a focused one leaves
    ``regression: true``, and either row's ``minimum`` stays, so the one command still runs at every step.
    """
    if first["command"] != row["command"] or first.get("host_dependent") != row.get("host_dependent") \
            or first.get("target") != row.get("target"):
        return None
    suites = {first["suite"], row["suite"]}
    if len(suites) > 1:
        if suites != {"focused", "regression"}:
            return None
        focused, regression = (first, row) if first["suite"] == "focused" else (row, first)
        if not set(regression.get("ids") or ()) <= set(focused.get("ids") or ()):
            return None
    merged: Dict[str, Any] = {"command": first["command"], "suite": "focused" if "focused" in suites else first["suite"]}
    for key in ("ids", "criteria"):
        values = list(dict.fromkeys([*(first.get(key) or ()), *(row.get(key) or ())]))
        if values:
            merged[key] = values
    minimum = max(int(first.get("min_tests") or 0), int(row.get("min_tests") or 0))
    if minimum:
        merged["min_tests"] = minimum
    if first.get("host_dependent"):
        merged["host_dependent"] = True
    if first.get("target"):
        merged["target"] = first["target"]  # where it runs decides the base run's remote rule (F3)
    if len(suites) > 1 or first.get("regression") or row.get("regression"):
        merged["regression"] = True
    if first.get("minimum") or row.get("minimum"):
        merged["minimum"] = True
    return merged


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


def stateful_targets(state: Mapping[str, Any]) -> Dict[str, str]:
    """{target: base_state_route} of each test-strategy target that keeps state between runs (run-5 batch F3)."""
    rows = _latest_root_result(state, "test-strategy").get("targets") or ()
    return {str(row["target"]): str(row.get("base_state_route") or "") for row in rows
            if isinstance(row, Mapping) and row.get("keeps_state") == "yes" and row.get("target")}


def _latest_root_result(state: Mapping[str, Any], stage: str) -> Mapping[str, Any]:
    """The latest accepted done result of a root stage, or an empty mapping."""
    for row in reversed(state.get("history", ())):
        if row.get("stage") == stage and row.get("workitem") is None and row.get("outcome") == "done":
            result = state.get("accepted", {}).get(row.get("action"))
            return result if isinstance(result, Mapping) else {}
    return {}


def stage_commands(state: Mapping[str, Any], stage: str, work_item: str) -> Tuple[List[Dict[str, Any]], str]:
    """This stage's commands and, when there are none, why.

    The outer stages run what their recording stage recorded (``OUTER_SOURCES``).  An inline implement step and its
    Improve review run only that step's Proof, the step plan's ``check`` for it (``step_command``: the implement-step
    fix plan's section 4.1); the item's commands stay with the test stage and document.  Every other item stage, and the
    ask-agent route's one implement action for every step, runs every command the latest accepted step plan recorded.
    The base run takes the focused and regression ones (``base_commands``).
    """
    if stage in STEP_PROOF_STAGES:
        step = step_command(state, work_item)
        if step is not None:
            return [step[1]], ""
    if stage in OUTER_SOURCES:
        source, field = OUTER_SOURCES[stage]
        result = _latest_root_result(state, source)
        commands = [dict(row) for row in result.get(field) or ()]
        return commands, ("" if commands else str(result.get(field + "_na") or ""))
    _action, result = _step_plan(state, work_item)
    if "test_commands" not in result:
        return [], ""
    commands = [dict(row) for row in result["test_commands"]]
    # Document reruns the commands its step's test stage ran (design T §8.2, 2b-4b); the navigator narrows them to what
    # document's own edits could affect.
    number = step_number(state, work_item) if stage in STAGES or stage == STEP_RERUN_STAGE else None
    if commands and number is not None:
        # One iteration per step (design T §8): the test stage runs what this step owes, due cases narrowed per command.
        commands = iteration.active_commands(commands, _test_cases(state, work_item), _plan_steps(result), number)
        if not commands:
            return [], (NONE_DUE + str(_plan_steps(result)[-1].get("id")))
    if commands:
        return commands, ""
    return [], str(result.get("test_commands_na") or "")


# Why a step before the last can have no command to run: its plan marks no minimum regression (minimum_na) and none of
# its cases or criteria is due yet.
NONE_DUE = ("no recorded command is due at this step: each runs from the step its cases or criteria are due at, and a "
            "regression command not marked minimum at the item's last step, ")


def held_back(state: Mapping[str, Any], work_item: str) -> Tuple[List[str], str]:
    """(the full regression commands a step before the last leaves to the item's last step, that step's ID); ([], "")
    at the last step, off the per-step route, or when every regression command is marked minimum (design T §9.1 2d)."""
    number = step_number(state, work_item)
    _action, result = _step_plan(state, work_item)
    steps = _plan_steps(result)
    if number is None or number >= len(steps):
        return [], ""
    full = [str(row["command"]) for row in result.get("test_commands") or ()
            if row.get("suite") == "regression" and not row.get("minimum")]
    return full, (str(steps[-1].get("id")) if full else "")


def _plan_steps(plan: Mapping[str, Any]) -> List[Mapping[str, Any]]:
    return [row for row in plan.get("steps") or () if isinstance(row, Mapping)]


def _test_cases(state: Mapping[str, Any], work_item: str) -> List[Mapping[str, Any]]:
    """The item's current test-spec cases: its latest accepted done test-spec result's ``test_cases``."""
    actions = [row["action"] for row in state.get("history", ())
               if row.get("stage") == "test-spec" and row.get("workitem") == work_item]
    for action in reversed(actions):
        result = state.get("accepted", {}).get(action)
        if isinstance(result, Mapping) and result.get("outcome") == "done":
            return [case for case in result.get("test_cases") or () if isinstance(case, Mapping)]
    return []


def step_number(state: Mapping[str, Any], work_item: str) -> Optional[int]:
    """The step an inline item's iteration is on once it is built (its test stage, its document and its review): how
    many steps of the latest step plan have an accepted implement done.  None on the ask-agent route (its one implement
    action builds every step), for a plan without steps, or before the first step is built."""
    if state.get("delegation") != guidance.INLINE:
        return None
    action, plan = _step_plan(state, work_item)
    steps = _plan_steps(plan) if action else []
    history = list(state.get("history", ()))
    start = max((i for i, row in enumerate(history) if row.get("action") == action), default=-1)
    built = sum(1 for row in history[start + 1:]
                if row.get("stage") == "implement" and row.get("workitem") == work_item and row.get("outcome") == "done")
    return built if steps and 1 <= built <= len(steps) else None


def step_command(state: Mapping[str, Any], work_item: str) -> Optional[Tuple[Mapping[str, Any], Dict[str, Any]]]:
    """(the step, its Proof as a ``check`` row) for the inline implement step the item is on, or None: another stage or
    route (the ask-agent action builds every step), no step left, or a step whose plan records no proof."""
    import shiploop_loops as loops  # imported where used: the loops module imports this one late

    found = loops.cursor(state)
    if found is None or found[0] not in STEP_PROOF_STAGES or found[2] != work_item:
        return None
    if loops._route(state, found[1]) != guidance.INLINE:
        return None
    step = loops.current_step(state, work_item)
    proof = step.get("proof") if step is not None else None
    if not isinstance(proof, str) or not proof.strip():
        return None
    return step, {"command": proof.strip(), "suite": "check"}


def base_commands(state: Mapping[str, Any], work_item: str) -> List[Dict[str, Any]]:
    """The focused and regression commands the base run takes, in recorded order."""
    return [row for row in stage_commands(state, STAGES[0], work_item)[0] if row["suite"] in COUNTED_SUITES]


def new_ids(state: Mapping[str, Any], work_item: str) -> List[str]:
    """Every test ID a focused command lists that this step adds: the new tests, which must not pass on the base.  At an
    inline step (design T §8) an earlier step's cases already pass on this step's base, so only the cases due at this
    step are new (``iteration.new_cases``)."""
    number = step_number(state, work_item)
    cases = _test_cases(state, work_item)
    earlier: set[str] = set()
    if number is not None:
        due = iteration.due_cases(cases, _plan_steps(_step_plan(state, work_item)[1]), number)
        earlier = set(due) - set(iteration.new_cases(cases, _plan_steps(_step_plan(state, work_item)[1]), number))
    seen: Dict[str, None] = {}
    for row in base_commands(state, work_item):
        if row["suite"] == "focused":
            for test_id in row.get("ids") or ():
                if test_id not in earlier:
                    seen[test_id] = None
    return list(seen)


def _earlier_step(state: Mapping[str, Any], work_item: str, row: Mapping[str, Any]) -> bool:
    """Whether the base run at this inline step holds a focused ``row`` only to earlier steps' cases, which already pass
    on the step's base (``iteration.earlier_command``): it is counted for the floor, not judged."""
    number = step_number(state, work_item)
    if number is None or row["suite"] != "focused":
        return False
    steps = _plan_steps(_step_plan(state, work_item)[1])
    return iteration.earlier_command(row, _test_cases(state, work_item), steps, number)


def _listing(row: Mapping[str, Any], floor: Optional[int] = None) -> str:
    """One command as packets show it, with the IDs, minimum and floor ShipLoop checks."""
    text = "[" + row["suite"] + "] " + row["command"]
    if row.get("ids"):
        text += " (must run: " + ", ".join(row["ids"]) + ")"
    if row.get("min_tests"):
        text += " (at least " + str(row["min_tests"]) + " tests)"
    if row.get("regression"):
        text += " (also recorded as regression)"
    if row.get("minimum"):
        text += " (minimum regression: every step)"
    if floor:
        text += " (floor: " + str(floor) + " tests)"
    return text


def _id_records(result: Optional[Mapping[str, Any]], key: str) -> List[Dict[str, str]]:
    """The ``[{"id", "reason"}]`` list a result carries under ``key`` (empty when absent); a bad shape raises."""
    value = (result or {}).get(key)
    if value is None:
        return []
    _need(isinstance(value, list), key + " is a list of {\"id\": \"<test ID>\", \"reason\": \"...\"}")
    rows: List[Dict[str, str]] = []
    for entry in value:
        _need(isinstance(entry, Mapping) and isinstance(entry.get("id"), str) and entry["id"].strip() != ""
              and "\n" not in entry["id"] and isinstance(entry.get("reason"), str) and entry["reason"].strip() != "",
              key + " entries each need a one-line id and a nonblank reason")
        rows.append({"id": entry["id"].strip(), "reason": entry["reason"].strip()})
    ids = [row["id"] for row in rows]
    _need(len(set(ids)) == len(ids), key + " names " + ", ".join(sorted({i for i in ids if ids.count(i) > 1}))
          + " more than once")
    return rows


def check_result_fields(state: Mapping[str, Any], work_item: str, result: Optional[Mapping[str, Any]]) -> None:
    """Refuse a test result whose ``red_na`` or ``retired_tests`` cannot apply to this item's commands.

    ``red_na: [{"id", "reason"}]`` exempts a characterisation test from the base rule: each ID must be one new at this
    step (``new_ids``), since the base run judges no other.  ``retired_tests: [{"id", "reason"}]`` lowers a floor for a
    test this item deliberately removes: its ID must not be one a focused command still lists, an earlier step's
    included.  Whether the base run showed each retired test is checked by the base run itself, the only place that can
    see it.
    """
    new = new_ids(state, work_item)
    listed = [test_id for row in base_commands(state, work_item) if row["suite"] == "focused"
              for test_id in row.get("ids") or ()]
    unknown = [row["id"] for row in _id_records(result, RED_NA) if row["id"] not in new]
    _need(not unknown, "red_na names " + ", ".join(unknown) + ", which is not a test ID new at this step"
          + (" (new: " + ", ".join(new) + ")" if new else "") + ". red_na exempts only a new test ID that passes "
          "without this change (a characterisation test, or a case a step committed before a send-back); the base run "
          "does not judge an earlier step's IDs.")
    still = [row["id"] for row in _id_records(result, RETIRED_TESTS) if row["id"] in listed]
    _need(not still, "retired_tests names " + ", ".join(still) + ", which a focused command still lists: a retired "
          "test is one this item removes, so it cannot also be a test the item must run.")


# The pass rule, the floor and the ratchet, each one line a head can afford (packet review D-12: the long forms cost the
# verify head 960 characters; every clause stays, and the refusals still quote their own long reasons).
COUNT_RULE = ("Pass: exit 0 and at least one test run (ShipLoop reads the runner's summary), with every listed ID in the "
              "output. " + guidance.ID_WORD_RULE + " A filter that matches nothing is not evidence, and the whole suite "
              "run in place of the named cases does not satisfy a listed ID. A focused command whose count ShipLoop "
              "cannot read needs ids and a runner flag that prints test names (for example --verbose; never dot or "
              "junit; a platform's runner: GUIDES/platforms/).")
# The test stage's floor (owner decision 2026-10-10, 2): the base count, raised by any earlier run of the action.
FLOOR_RULE = ("Floor of each focused and regression command: the larger of its count on the item's base (ShipLoop's base "
              "run, this item's test files copied in) and the most any earlier ShipLoop run of this action ran, less "
              "each retired_tests entry the base run showed for it. A test removed or newly skipped to pass is refused; "
              "a test this item deliberately retires goes in retired_tests (shape: duty 6) and must print its name on "
              "the base.")
BASE_RULE = ("Base run: before the candidate run, ShipLoop runs every focused and regression command on the step's "
             "base (a temporary detached worktree, with only this item's test files copied in). No test ID new at "
             "this step may pass there: each must fail because the behaviour it asserts is missing, or fail to load "
             "the code this item adds; a guard that only checks or prints a file's path is not RED. An earlier step's "
             "IDs already pass there and are not judged. A new test that passes without this change (a "
             "characterisation test, or a case a step committed before a send-back) goes in red_na (shape: duty 6). A command "
             "the platform card lists under Remote tests is not run there (its target already holds the change). A "
             "refused base run counts toward the same refused runs.")
# What the reruns after the test stage say about the floor ``accepted_counts`` sets.
RATCHET_RULE = ("Floor: each command runs at least as many tests as the most an accepted ShipLoop run of it ran for this "
                "item since its latest step plan, so a test removed or newly skipped is refused; a test that must go "
                "because the plan changed is a send-back, and the redone step plan starts the count again.")


def _floor_lines(stage: str) -> List[str]:
    """The packet line about the count floor: none at the outer stages, which are not held to one."""
    if stage in OUTER_SOURCES:
        return []
    return [FLOOR_RULE if stage in STAGES else RATCHET_RULE]


def rule_lines(state: Mapping[str, Any], work_item: str, stage: str) -> List[str]:
    """How ShipLoop judges the listed commands: printed in the full packet, below the head (``loop_lines``)."""
    if not stage_commands(state, stage, work_item)[0]:
        return []
    return [COUNT_RULE] + _floor_lines(stage) + ([BASE_RULE] if stage in BASE_STAGES else [])


def loop_lines(root: Path, state: Mapping[str, Any], work_item: str, action: str, stage: str = "",
               cli: Optional[str] = None) -> List[str]:
    """What the test packet adds to the Until Loop argument's command list: where the commands run, each floor by
    the argument's numbering, the red-check command and, once a run was refused, the count of refused runs (never
    the cap).

    The command text, IDs and minimums are printed once, in the argument (``shiploop_loops.command_listing``).  The
    floor shown is what ShipLoop knows when the packet renders: the latest passed base run and any earlier run of
    this action; before the first base run it says the base run sets it.  ``cli`` is the ShipLoop command prefix the
    navigator prints (for example ``python3 <abs>/shiploop``); without it the red-check line is left out.  The Until
    Loop block is rendered by ``shiploop_loops.invoke_lines``, not here.
    """
    root = Path(root)
    stage = stage or STAGES[0]
    commands, reason = stage_commands(state, stage, work_item)
    lines = [""]
    if not commands:
        if reason:
            lines.append("No command to run: " + reason.rstrip(".") + ". Report done with that reason; ShipLoop has "
                         "nothing to run.")
        else:
            lines.append("The accepted step plan recorded no test_commands. Report outcome send-back so the step plan "
                         "records them.")
        return lines
    known = floors(root, state, work_item, action, None)
    based = _latest_base(root, action, passed=True) is not None
    head = ("Where and floors: ShipLoop runs each recorded command in the Until Loop argument above from "
            + str(state["repo"]) + " before accepting done; ")
    shown = [(number, row["suite"] in COUNTED_SUITES, known.get(row["command"]))
             for number, row in enumerate(commands, 1)]
    if any(floor for _number, _counted, floor in shown):
        lines.append(head + ("floors from the base run" if based else "floors known so far; the base run at done "
                             "sets the rest") + ", by the argument's numbering:")
        lines += ["  " + str(number) + ". " + ("at least " + str(floor) + " tests" if floor
                                               else "floor set by the base run at done" if counted
                                               else "no floor (judged by its exit code)")
                  for number, counted, floor in shown]
    else:
        lines.append(head + "the base run at done sets each floor.")
    full, last = held_back(state, work_item) if stage in STAGES else ([], "")
    if full:
        lines.append("The full regression runs at the item's last step, " + last + ": "
                     + ", ".join("`" + command + "`" for command in full) + ".")
    if cli:
        lines.append("  red-check: " + cli + " red-check --run-dir=" + str(root) + " --action=" + action
                     + " (runs the base check now; it does not count toward the refused runs)")
    refused = refused_runs(root, action)
    if refused:
        lines.append(refused_note(refused, stage) + " A run that times out or cannot start refuses without counting.")
    return lines


def observation(root: Path, state: Mapping[str, Any], stage: str) -> Optional[Dict[str, Any]]:
    """Where this stage's recorded commands observe the product, or None for a stage with no such question.

    Only ``release-verify`` asks (its done-when is "observed where consumers use it"); every other stage runs
    in the work area as before.  ``where`` is ``in-place`` (no isolated workspace: the checkout), ``returned-result``
    (a completed return is recorded: a clean copy of the tree it delivered, with the receipt's facts), ``work-area``
    (an isolated run with no completed return: release-verify can precede the return and cannot make it, so it runs
    in the work area and is labelled, never refused) or ``unknown`` (the return state cannot be read now; ``reason``
    says why).  Never raises: the packet shows it, and ``verify`` turns ``unknown`` into a could-not-run attempt
    rather than silently falling back to the work area.
    """
    if stage != "release-verify":
        return None
    if state.get("execution_mode") != "navigator-worktree":
        return {"where": "in-place"}
    try:
        found = workspace.returned_result(Path(root).parent)
    except (workspace.WorkspaceError, OSError, KeyError, TypeError) as exc:
        return {"where": "unknown", "reason": str(exc)}
    if found is None:
        return {"where": "work-area", "reason": "no completed return is recorded"}
    return {"where": "returned-result", **found}


def _where(observed: Optional[Mapping[str, Any]], repo: Any) -> str:
    """The place a stage's commands run, in the words the packet, the refusal and the handoff line share."""
    where = (observed or {}).get("where")
    if where == "returned-result":
        return ("a clean copy of the result returned to " + str(observed["source"]) + " (" + str(observed["kind"])
                + " at " + str(observed["head"])[:12] + "; receipt " + str(observed["receipt"]) + "), made fresh at "
                + str(observed["copy"]) + " on each done")
    if where == "work-area":
        return "the work area " + str(repo)
    if where == "unknown":
        return "a place not currently known (the return state cannot be read: " + str(observed["reason"]) + ")"
    return str(repo)


def _copy_refusal(observed: Mapping[str, Any]) -> str:
    """The reply to a release-verify command that failed in the returned-result copy, and the one exit the stage has."""
    ahead = ("The work area is ahead of the return now (its HEAD is not the returned head "
             + str(observed["head"])[:12] + "), so a commit made after the return is the likely cause. "
             if observed.get("ahead") else "")
    return ("The copy at " + str(observed["copy"]) + " holds exactly the returned tree and is kept so you can reproduce "
            "there. A check that passes in the work area and fails here usually means one of: a path the return plan "
            "excluded (" + str(observed["plan"]) + "); an ignored or unmanaged file the check needs (installed "
            "dependencies, build output, local configuration); or a commit made after the return, which the copy does "
            "not hold. " + ahead + "This stage cannot edit the commands or return. Report outcome add-work with one "
            "corrective work item whose context names the failing command and its cause, so release returns the fix "
            "and release-verify observes it (an excluded path: the return plan must keep it; an ignored or unmanaged "
            "file: the check must bring it, for example by installing it first; a later commit: release must return "
            "it again). If the cause is not about what was delivered (a busy port, a missing tool), fix it and submit "
            "done again.")


def _place_reply(stage: str, refused: int) -> str:
    """The reply when the place the commands were to run in could not be made or read: no command started."""
    remedy = _remedy(stage)
    return ("No command started, so nothing here says anything about the product: this attempt "
            + _not_counted(refused) + ". Nothing is accepted on unrun tests. The cause is the return state or the copy "
            "path named above, not this item's code, test or fixture: repair what it names (a lock another ShipLoop "
            "command holds, a path ShipLoop asks you to remove) and submit done again"
            + ("; if it cannot be repaired, report " + remedy + " with the corrective work_items the outer loop must "
               "run (ShipLoop's own record of this attempt is the evidence)" if remedy else "")
            + ". Report blocked only for what the user, an access grant or an outside dependency must supply.")


def rerun_lines(root: Path, state: Mapping[str, Any], work_item: str, stage: str) -> List[str]:
    """Packet lines for a rerun stage: the commands ShipLoop runs before accepting done.

    ``root`` is the run directory; at ``release-verify`` the line names where the commands run (``observation``),
    computed afresh at every render, and the note under the list says what that place does and does not hold.
    """
    commands, _reason = stage_commands(state, stage, work_item)
    if not commands:
        return []
    # The outer stages rerun commands another stage recorded, and have no step plan.
    recorded_by = OUTER_SOURCES[stage][0] if stage in OUTER_SOURCES else "the step plan"
    observed = observation(root, state, stage)
    where = observed["where"] if observed else ""
    notes = {
        "returned-result": "Where they run: the copy holds exactly the returned tree, so it has no Git history, nothing "
                           "the return plan excluded and no ignored or unmanaged file (installed dependencies, build "
                           "output). A command that names the checkout by an absolute path runs there, not in the copy.",
        "work-area": "Where they run: no completed return is recorded, so these commands run in the work area and do "
                     "not observe the user's checkout; the handoff reports that.",
        "unknown": "Where they run: the return state cannot be read now, so done is refused without counting until it "
                   "can be; retry done then, or report add-work if it cannot be repaired.",
    }
    what = ("reruns what your edits since this stage began could affect, out of the commands its step's test stage "
            "ran (none after no edit, the check commands after a documentation edit, all of them after a code or test "
            "edit), from " if stage == STEP_RERUN_STAGE else
            "runs every test command " + recorded_by + " recorded from ")
    return (["", "Test rerun: on done, ShipLoop " + what
             + _where(observed, state["repo"]) + " and refuses unless each passes (if it keeps refusing, "
             + _remedy_sentence(stage) + "; a command that times out or cannot start refuses the stage without "
             "counting):"]
            + ["  " + str(number) + ". " + _listing(row) for number, row in enumerate(commands, 1)]
            + [COUNT_RULE] + _floor_lines(stage) + ([notes[where]] if where in notes else []))


def observed_lines(root: Path, state: Mapping[str, Any]) -> List[str]:
    """Handoff packet line: where release-verify's consumer checks last ran, from ShipLoop's own test record.

    A cleared handoff model cannot know it, and a run that never observed the user's checkout must say so.  Handoff
    follows release-verify in every run, so the line is always printed once release-verify is accepted: from the
    ``observed`` key every release-verify test record carries (a record without it, or none where release-plan
    recorded commands, is a defect and raises), or, when release-plan recorded no consumer check and so ShipLoop
    wrote no record, as the statement that none ran with the plan's own reason.
    """
    action = next((row.get("action") for row in reversed(state.get("history", ()))
                   if row.get("stage") == "release-verify" and row.get("workitem") is None
                   and row.get("outcome") == "done"), None)
    if action is None:
        return []
    commands, reason = stage_commands(state, "release-verify", "")
    if not commands:
        return ["Consumer checks (release-verify) did not run: release-plan recorded no consumer check"
                + (" (" + reason.rstrip(".") + ")." if reason else ".")]
    path = Path(root) / verify_path(str(action), _verify_count(root, str(action)))
    observed = store.read_record(path)["observed"]
    line = "Consumer checks (release-verify) ran in " + _where(observed, state["repo"]) + "."
    if observed.get("where") == "work-area":
        line += (" No completed return was recorded then, so they did not observe the user's checkout: list that as a "
                 "limit.")
    return [line + " Record: " + str(path) + "."]


def _tail(data: bytes) -> str:
    text = data.decode("utf-8", "replace")
    return text if len(text) <= TAIL_CHARS else "[... " + str(len(text) - TAIL_CHARS) + " chars]\n" + text[-TAIL_CHARS:]


def judge(row: Mapping[str, Any], code: Optional[int], output: str) -> Dict[str, Any]:
    """Classify one finished candidate run from its exit code and its own output.

    ``passed`` needs exit 0, a recognised count of at least ``min_tests`` (1 by default) and every listed ID shown; a
    focused command whose count cannot be read passes only when it lists IDs and all appear.  A regression command
    without ids or min_tests may pass uncounted.  A check is judged by its exit code, but a runner summary in its output
    must show a test ran.  Exit zero does not win over a reporter-recognised failure: a wrapper or build step that
    swallows a runner's nonzero status still fails when the output's own tally or a listed ID's own outcome says so.
    """
    tally = counts.count(output, code)
    ids = list(row.get("ids") or ())
    masked_failure = code == 0 and (
        (tally is not None and tally["failed"] > 0)
        or any(outcome == "failed" for outcome in counts.outcomes(output, ids).values())
    )
    if row.get("suite") == "check":
        # A runner recorded as a check must not pass by running nothing (a release-verify `node --test` did so with
        # counts null).
        if code == 0 and tally is not None and tally["ran"] == 0:
            return {"counts": tally, "ids_missing": [], "status": "no-tests"}
        if masked_failure:
            return {"counts": tally, "ids_missing": [], "status": "failed"}
        return {"counts": tally, "ids_missing": [], "status": "passed" if code == 0 else "failed"}
    names = counts.named(output, ids) if ids else {"shown": [], "missing": []}
    minimum = int(row.get("min_tests") or 1)
    verdict: Dict[str, Any] = {"counts": tally, "ids_missing": names["missing"]}
    if names.get("inside"):
        verdict["ids_inside"] = names["inside"]
    if code != 0:
        verdict["status"] = "no-tests" if tally is not None and tally["ran"] == 0 else "failed"
    elif tally is not None and tally["ran"] == 0:
        verdict["status"] = "no-tests"
    elif tally is not None and tally["ran"] < minimum:
        verdict["status"] = "too-few-tests"
    elif names["missing"]:
        verdict["status"] = "ids-missing"
    elif masked_failure:
        verdict["status"] = "failed"
    elif tally is not None or ids:
        verdict["status"] = "passed"
    elif row["suite"] == "regression" and "min_tests" not in row:
        verdict["status"] = "passed-uncounted"
    else:
        verdict["status"] = "uncounted"
    return verdict


def _explain(run: Mapping[str, Any], stage: str = "") -> str:
    """One refusal reason for a run, written for the model that has to fix it.

    ``stage`` is the stage that ran the command.  The OUTER stages run commands that an earlier stage recorded
    (``OUTER_SOURCES``) and cannot edit them, so a reply that tells them to change the command has no way out.
    """
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
    if status == DRIFT_STATUS:
        return ("is the project's default suite, and its output shows the host-dependent case"
                + ("s " if len(run.get("host_dependent_ids_shown") or ()) > 1 else " ")
                + ", ".join(run.get("host_dependent_ids_shown") or ())
                + ", which the system tests mark as needing a host tool. A plain run of the default suite must pass on a "
                "host without that tool: give each such case its own opt-in command or make it skip unless an opt-in "
                "setting is present, in the test files (the recorded commands cannot change at this stage), then submit "
                "done again.")
    if status == "too-few-tests":
        floor = int(run.get("accepted_ran") or 0)
        if floor > int(run.get("min_tests") or 0):
            if stage in STAGES:
                exit_ = ("Restore the tests that were removed or now skip. A test this item deliberately retires goes "
                         "in the result's retired_tests with its reason; ShipLoop lowers the floor only for a retired "
                         "test the base run showed for this command.")
            else:
                exit_ = ("Restore the tests that were removed or now skip. A test that must go because the plan changed "
                         "is a send-back: report send-back naming what was removed and why, and the redone step plan starts "
                         "the count again.")
            return ("ran fewer tests than its floor (at least " + str(floor) + ": " + str(run.get("floor_from")
                    or "an earlier run of this command that ShipLoop accepted for this item") + ")" + seen + ". "
                    + exit_)
        return ("ran fewer tests than the step plan requires (at least " + str(run.get("min_tests")) + ")"
                + seen + ".")
    if status == "ids-missing":
        inside = run.get("ids_inside") or {}
        apart = [test_id for test_id in run["ids_missing"] if test_id not in inside]
        reason = ""
        if inside:
            first = next(iter(inside))
            reason = ("did not show " + ", ".join(inside) + " as a whole word" + seen + ". " + guidance.ID_WORD_RULE
                      + " " + first + " appears only inside: " + inside[first] + ". Title each test so its listed "
                      "ID stands alone.")
        if apart:
            reason += (" Also " if reason else "") + ("did not show " + ", ".join(apart) + " running"
                      + ("" if reason else seen) + ". Make the command select those cases and print test names "
                      "(for example --verbose).")
        return reason
    if status == "uncounted":
        unread = "exited " + str(run["exit"]) + ", but ShipLoop could not read how many tests it ran. "
        if stage in OUTER_SOURCES:
            source, field = OUTER_SOURCES[stage]
            return (unread + source + " recorded this command and " + stage + " cannot edit it. A command that is "
                    "not a test runner (a shell pipeline, a grep, a probe) belongs in suite `check`, judged by its "
                    "exit code. Report outcome add-work now, with one corrective work item: a new id, a title, and a "
                    "context that names this command and says to record it as suite check in " + field
                    + ". The outer stages then run again, and " + source + " records it.")
        return (unread + "Give the command ids and a runner flag that prints test names (for example --verbose; never "
                "a dot or junit reporter), use a runner ShipLoop reads (" + counts.RUNNERS + "), or, for a command "
                "that is not a test runner, record it as suite `check`.")
    if status == "timeout":
        return ("timed out, so it reached no verdict about the product. This is not a diagnosis: it can mean a "
                "deadlock, a broken test, a suite too slow for the per-command timeout or an external dependency.")
    if status == "error":
        detail = ((run.get("stderr") or "").strip().splitlines() or ["no detail"])[-1]
        return ("could not start: " + detail
                + ". The command never ran, so this says nothing about the product.")
    if status == "failed" and run["exit"] == 0:
        return ("exited 0, but" + seen + " shows a reporter-recognised failure: a wrapper or build step swallowed "
                "the runner's own nonzero exit. Fix the failing case; make the command exit nonzero on failure or "
                "stop swallowing its exit code.")
    return "exit " + str(run["exit"])


# ---------------------------------------------------------------- records, the refused-run tally and the floor

def _count(root: Path, action: str, path: Callable[[str, int], str]) -> int:
    number = 0
    while (Path(root) / path(action, number + 1)).exists():
        number += 1
    return number


def _verify_count(root: Path, action: str) -> int:
    """How many ShipLoop candidate (or rerun) records this action has."""
    return _count(root, action, verify_path)


def _base_count(root: Path, action: str) -> int:
    """How many ShipLoop base-run records this action has."""
    return _count(root, action, base_path)


def _mutation_count(root: Path, action: str) -> int:
    """How many ShipLoop mutation-check records this action has."""
    return _count(root, action, mutation_path)


def _records(root: Path, action: str) -> Iterator[Tuple[str, Any]]:
    """Every counted record of this action (candidate, base, then mutation), as (kind, record); unreadable ones as
    None."""
    for kind, path, total in (("verify", verify_path, _verify_count(root, action)),
                              ("base", base_path, _base_count(root, action)),
                              ("mutation", mutation_path, _mutation_count(root, action))):
        for number in range(1, total + 1):
            try:
                yield kind, store.read_record(Path(root) / path(action, number))
            except (OSError, store.StorageError):
                yield kind, None


def _latest_base(root: Path, action: str, *, passed: bool = False) -> Optional[Mapping[str, Any]]:
    """This action's latest base record (the latest passed one with ``passed``), or None."""
    for number in range(_base_count(root, action), 0, -1):
        record = store.read_record(Path(root) / base_path(action, number))
        if isinstance(record, Mapping) and (record.get("passed") or not passed):
            return record
    return None


def red_unobserved(root: Path, state: Mapping[str, Any], work_items: Sequence[str]) -> List[Tuple[str, str]]:
    """(work item, command) for each focused command its test stage's latest base run left out as remote (run-5 batch
    I2): the target already held the change, so no failure on the old code was ever seen, and the candidate run is that
    command's only evidence."""
    found: List[Tuple[str, str]] = []
    for work_item in work_items:
        actions = [row["action"] for row in state.get("history", ())
                   if row.get("stage") == STAGES[0] and row.get("workitem") == work_item]
        base = _latest_base(root, actions[-1]) if actions else None
        for run in (base or {}).get("runs") or ():
            if isinstance(run, Mapping) and run.get("status") == "remote" and run.get("suite") == "focused":
                found.append((work_item, str(run.get("command"))))
    return found


def refused_runs(root: Path, action: str) -> int:
    """How many of this action's ShipLoop runs (base and candidate) the product failed.

    An attempt whose only non-passing commands were unavailable (``UNAVAILABLE``: timed out or could not start) is
    not evidence against the product, so it does not count here.  It still refused its stage at the time.
    """
    refused = 0
    for _kind, record in _records(root, action):
        if not isinstance(record, Mapping):
            refused += 1
        elif not record.get("passed") and record.get("disposition") != "could-not-run":
            refused += 1
    return refused


def latest_attempt_could_not_run(root: Path, action: str) -> bool:
    """Whether ShipLoop's own latest run for this action (base or candidate) never reached a verdict.

    Each record carries ``attempt``, one sequence shared by both kinds, so the latest is the one with the highest.
    """
    latest: Optional[Mapping[str, Any]] = None
    for _kind, record in _records(root, action):
        if isinstance(record, Mapping) and (latest is None or int(record.get("attempt") or 0)
                                            >= int(latest.get("attempt") or 0)):
            latest = record
    return latest is not None and latest.get("disposition") == "could-not-run"


def remedy_open(root: Path, action: str) -> bool:
    """Whether ShipLoop's own record entitles this action to its stage's remedy outcome.

    ``send-back`` (INNER) or ``add-work`` (OUTER) is accepted without a stopped Until Loop receipt when ShipLoop's own latest
    run never reached a verdict: the refusal names that outcome as the route out, so it must be accepted.  No count of
    refused runs opens it (owner 2026-10-24: no run caps).  An ordinary ``done`` still needs a complete loop packet.
    """
    return latest_attempt_could_not_run(root, action)


def _next_attempt(root: Path, action: str) -> int:
    return _verify_count(root, action) + _base_count(root, action) + _mutation_count(root, action) + 1


def accepted_counts(root: Path, state: Mapping[str, Any], work_item: str) -> Dict[str, int]:
    """Per command, the most tests any run ShipLoop accepted for this work item has run since its latest step plan.

    Read from the item's ``tests/<action>-verify<N>.md`` records, so no state key holds it: the passed records of the
    actions accepted after the item's latest accepted step plan (the history is append-only, so a revised step plan
    starts the count again), and in them the runs ShipLoop accepted whose output it could count.  Empty for the outer
    stages and the end-of-work review (``work_item`` is empty).  An action ShipLoop has not accepted yet is not in the
    history, so its record sets no floor here (``action_counts`` reads it).
    """
    plan, _result = _step_plan(state, work_item)
    if not work_item or plan is None:
        return {}
    history = list(state.get("history", ()))
    first = max(i for i, row in enumerate(history) if row.get("action") == plan) + 1
    most: Dict[str, int] = {}
    for action in dict.fromkeys(row.get("action") for row in history[first:] if row.get("workitem") == work_item):
        for number in range(1, _verify_count(root, str(action)) + 1):
            record = store.read_record(Path(root) / verify_path(str(action), number))
            if not isinstance(record, Mapping) or not record.get("passed"):
                continue
            _most(most, record)
    return most


def _most(most: Dict[str, int], record: Mapping[str, Any]) -> None:
    for run in record.get("runs") or ():
        ran = (run.get("counts") or {}).get("ran")
        if run.get("status") == "passed" and isinstance(ran, int):
            most[run["command"]] = max(most.get(run["command"], 0), ran)


def action_counts(root: Path, action: str) -> Dict[str, int]:
    """Per command, the most tests any earlier candidate run of this action ran in a run of that command that passed.

    Every record counts, refused ones too: a command that passed with 50 tests in an attempt another command failed may
    not run 45 in the next.
    """
    most: Dict[str, int] = {}
    for number in range(1, _verify_count(root, action) + 1):
        record = store.read_record(Path(root) / verify_path(action, number))
        if isinstance(record, Mapping):
            _most(most, record)
    return most


def floor_detail(root: Path, state: Mapping[str, Any], work_item: str, action: str,
                 result: Optional[Mapping[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """Per focused and regression command, its floor and where it comes from (the test stage's rule).

    ``floor = max(base count - retired shown, earlier runs - retired seen)``: the base count is the latest passed base
    run's count for the command, less the result's ``retired_tests`` that run showed for it (a deleted test file still
    runs on the base; a test removed from a changed test file is already gone there, because the changed file is copied
    in); the earlier runs are this action's own (``action_counts``) and any run accepted for the item since its step
    plan (``accepted_counts``), less every retired test the base run saw (``retired_seen``), since a candidate record
    cannot say which command ran it.  A command with no number from any source has no floor.
    """
    root = Path(root)
    base = _latest_base(root, action, passed=True) or {}
    base_runs = {run.get("command"): run for run in base.get("runs") or ()}
    earlier = accepted_counts(root, state, work_item)
    for command, ran in action_counts(root, action).items():
        earlier[command] = max(earlier.get(command, 0), ran)
    retired = [row["id"] for row in _id_records(result, RETIRED_TESTS)]
    detail: Dict[str, Dict[str, Any]] = {}
    for row in base_commands(state, work_item):
        command = row["command"]
        run = base_runs.get(command) or {}
        base_ran = (run.get("counts") or {}).get("ran") if isinstance(run.get("counts"), Mapping) else None
        before = earlier.get(command)
        gone = [test_id for test_id in retired if test_id in (run.get("retired_shown") or ())]
        seen = [test_id for test_id in retired if test_id in (base.get("retired_seen") or ())]
        # The base term drops the retired tests this command showed on the base; the earlier-run term cannot tell
        # which command ran a retired test, so it drops every retired test the base run saw (a bounded leak).
        terms = [value for value in (isinstance(base_ran, int) and base_ran - len(gone),
                                     isinstance(before, int) and before - len(seen)) if value is not False]
        floor = max(max(terms, default=0), 0)
        if floor:
            parts = []
            if isinstance(base_ran, int):
                parts.append(str(base_ran) + " on the base")
            if isinstance(before, int):
                parts.append(str(before) + " in an earlier run")
            text = "the larger of " + " and ".join(parts) if len(parts) > 1 else parts[0]
            if gone or seen:
                text += ", less the retired " + ", ".join(dict.fromkeys(gone + seen))
            detail[command] = {"floor": floor, "from": text}
    return detail


def floors(root: Path, state: Mapping[str, Any], work_item: str, action: str,
           result: Optional[Mapping[str, Any]]) -> Dict[str, int]:
    """Per command, the test stage's floor (``floor_detail`` without the explanation)."""
    return {command: row["floor"] for command, row in floor_detail(root, state, work_item, action, result).items()}


def _disposition(runs: List[Dict[str, Any]], good: Tuple[str, ...]) -> str:
    """One attempt's verdict: ``passed``, ``failed`` or ``could-not-run`` (a gate that did nothing is ``skipped``,
    which ``_base_run`` and the mutation check set themselves).

    A real failing check beside a timeout is still ``failed``: an unavailable command never erases a verdict another
    command did reach.  ``/bin/sh -c`` reports a command it cannot find or execute as exit 127 or 126, which is judged
    like any other non-zero exit (a failure), so ``error`` means only that the process itself could not be spawned.
    """
    if all(run["status"] in good for run in runs):
        return "passed"
    if any(run["status"] not in good and run["status"] not in UNAVAILABLE for run in runs):
        return "failed"
    return "could-not-run"


def _remedy(stage: str) -> str:
    """The outcome this stage offers when its own runs keep refusing, from the stage contract.

    INNER stages take the item back to its step plan (``send-back``); the OUTER ``system-test`` and ``release-verify``
    take corrective work items (``add-work``): their runs refused, so the product, not their plan, is what failed.  They
    also accept send-back since S1.5, for a wrong plan, which a refused run does not show; add-work is checked first.
    ``verify`` is also called with a label that is not a graph stage -- the navigator's ``end-of-work review`` gate --
    which has no remedy outcome and must not raise here.
    """
    row = stage_spec.STAGE_SPEC.get(stage)
    if row is None:
        return ""
    for candidate in ("add-work", "send-back"):
        if candidate in row.outcomes:
            return candidate
    return ""


def _has_loop_packet(stage: str) -> bool:
    """Whether the stage's send-back otherwise needs a stopped Until Loop receipt (every inner stage runs one)."""
    return stage in stage_spec.INNER


def _remedy_sentence(stage: str) -> str:
    """What the packet says the stage's remedy outcome does, in the stage's own terms."""
    remedy = _remedy(stage)
    if remedy == "send-back":
        return "the item goes back to its step plan (send-back)"
    if remedy == "add-work":
        return "the outer loop takes corrective work items (add-work)"
    return "keep fixing until every command passes (no count of refused runs stops this action)"


# What the model reads about the tally of refused runs: the count so far.  No count stops the work (owner 2026-10-24:
# no run caps); the tally is evidence for the model's own judgement of when the stage's remedy fits.
REFUSED_TALLY = "base, candidate and mutation runs together"


def refused_note(refused: int, stage: str) -> str:
    """The refused-run tally a refusal or the test packet prints: the count, what it counts, the stage's route out.

    ``refused`` is the number of runs the product has failed so far, this refusal included.
    """
    return ("Refused runs for this action so far: " + str(refused) + " (" + REFUSED_TALLY + "); if they keep coming, "
            + _remedy_sentence(stage) + ".")


def _not_counted(refused: int) -> str:
    """The clause for an attempt that does not count as a refused run, with the count so far when there is one."""
    return "does not count as a refused run" + (" (refused so far: " + str(refused) + ")" if refused else "")


def _unavailable_sentence(stage: str, refused: int, command_timeout: float) -> str:
    """The reply to an attempt in which no command reached a verdict: it does not count, so name the routes out."""
    remedy = _remedy(stage)
    return ("No command reached a verdict about the product, so this attempt " + _not_counted(refused)
            + ". Nothing is accepted on unrun tests. "
            + "A command that hangs or fails to start because of this item's own code, test or fixture is yours to "
            "fix here and is not a blocker"
            + ("; if the recorded command is itself wrong or too slow to fit (" + str(int(command_timeout))
               + " seconds each), report " + remedy
               + " rather than retrying it"
               + (", with the corrective work_items the outer loop must run" if remedy == "add-work" else "")
               + (" (ShipLoop's own record of this attempt is the evidence, so no new loop packet is needed)"
                  if _has_loop_packet(stage) else "")
               if remedy else "")
            + ". Report blocked only for what the user, an access grant or an outside dependency must supply.")


DRIFT_STATUS = "host-dependent-in-default-suite"


def default_suite_drift(state: Mapping[str, Any], rows: List[Dict[str, Any]], run_one: Callable[[str], Optional[Tuple[int, str]]]
                        ) -> List[Dict[str, Any]]:
    """Run the accepted regression commands and report any host-dependent id they show.

    A system row marked ``host_dependent`` names cases that need a host tool (a browser, a device, an account).  The
    project's default suite must pass without that tool, so none of those ids may be shown, run or failed, by a
    regression command.  ``run_one(command)`` returns ``(exit, output)`` or ``None`` when the command did not start.
    """
    marked = [test_id for row in rows if row.get("host_dependent") for test_id in row.get("ids") or ()]
    if not marked:
        return []
    seen: List[str] = []
    drift: List[Dict[str, Any]] = []
    for item in state.get("work_items", ()):
        _action, result = _step_plan(state, str(item.get("id")))
        for row in result.get("test_commands") or ():
            if not (row["suite"] == "regression" or row.get("regression")) or row["command"] in seen:
                continue
            seen.append(row["command"])
            ran = run_one(row["command"])
            if ran is None:
                continue
            code, output = ran
            shown = counts.named(output, marked)["shown"]
            drift.append({**row, "exit": code, "seconds": 0.0, "stdout": _tail(output.encode()), "stderr": "",
                          "host_dependent_ids_shown": shown, "status": DRIFT_STATUS if shown else "passed"})
    return drift


def _run_command(runner: Runner, command: str, cwd: Path, timeout: float, environment: Mapping[str, str],
                 clock: Callable[[], float]) -> Tuple[Dict[str, Any], str]:
    """Run one recorded command; return the run fields (status set only when unavailable or exitless) and its output."""
    started = clock()
    try:
        status, code, out, err = runner(["/bin/sh", "-c", command], cwd, timeout, input_bytes=b"", env=environment)
    except OSError as exc:
        status, code, out, err = "error", None, b"", (type(exc).__name__ + ": " + str(exc)).encode()
    run: Dict[str, Any] = {"exit": code, "seconds": round(clock() - started, 3), "stdout": _tail(out),
                           "stderr": _tail(err)}
    if status in UNAVAILABLE:
        # Keep the runner's own unavailable status, including the "error" an OSError set above: it exits with no code,
        # so it must not be judged as a test failure.
        run["status"] = status
    elif code is None:
        run["status"] = "failed"
    return run, out.decode("utf-8", "replace") + "\n" + err.decode("utf-8", "replace")


def _tree(root: Path, repo: Path) -> str:
    """The repository's working content as a Git tree (tracked plus untracked, never ignored, without the run directory
    or ShipLoop's runtime files: ``lint.snapshot_tree``), or "" when there is none (not a Git checkout, Git failed)."""
    index = Path(root) / "lint" / "tmp" / ("test-reuse-" + os.urandom(8).hex() + ".index")
    try:
        top = lint.git_toplevel(repo)
        if top is None:
            return ""
        return lint.snapshot_tree(top, Path(root), index, prefix=lint.scope_prefix(top, repo))
    except (lint.LintError, OSError):
        return ""
    finally:
        if index.exists():
            index.unlink()


def _reused(root: Path, action: str, stage: str, work_item: str, commands: Sequence[Mapping[str, Any]], repo: Path,
            held: Mapping[str, Mapping[str, Any]]) -> Optional[Tuple[List[Dict[str, Any]], Dict[str, Any]]]:
    """The runs of this action's passed check-only record, held to today's floors, when ``complete`` takes them instead
    of running every command again (owner decision D5, 2026-10-17); else None.

    It takes them when that record passed at this stage and item, lists exactly ``commands``, and the repository's
    working content (``_tree``) is now a tree the check-only run started on or left.  A run the floor now refuses is
    not taken: the commands run again, so a refusal always comes from a run made now.  Returns (runs, the ``reused``
    entry the counted record carries: which check-only record and the tree).
    """
    path = Path(root) / check_only_path(action)
    if not path.is_file():
        return None
    try:
        record = store.read_record(path)
    except (OSError, store.StorageError):
        return None
    if not (isinstance(record, Mapping) and record.get("passed") is True and record.get("stage") == stage
            and record.get("work_item") == work_item and record.get("commands") == list(commands)
            and record.get("trees")):
        return None
    tree = _tree(root, repo)
    if not tree or tree not in record["trees"]:
        return None
    runs: List[Dict[str, Any]] = []
    for run in record.get("runs") or ():
        run = {key: value for key, value in run.items() if key not in ("accepted_ran", "floor_from")}
        floor = held.get(run.get("command"))
        if floor:
            run["accepted_ran"] = floor["floor"]
            run["floor_from"] = floor["from"]
            if run.get("status") == "passed" and run.get("counts") and run["counts"]["ran"] < floor["floor"]:
                return None
        runs.append(run)
    return runs, {"path": check_only_path(action), "created_at": record.get("created_at"), "tree": tree}


def reuse_note(root: Path, action: str) -> str:
    """What ``complete --check-only`` prints about its test run when the real ``complete`` can take it (``_reused``),
    else ""."""
    path = Path(root) / check_only_path(action)
    try:
        record = store.read_record(path) if path.is_file() else None
    except (OSError, store.StorageError):
        return ""
    if not (isinstance(record, Mapping) and record.get("passed") is True and record.get("trees")):
        return ""
    return ("That complete takes this test run (" + str(path) + ") instead of running the commands again while the "
            "tree and the recorded commands stay as they are now; any edit makes it run them again.")


def verify(root: Path, state: Mapping[str, Any], work_item: str, action: str, stage: str, *,
           runner: Optional[Runner] = None, env: Optional[Mapping[str, str]] = None,
           clock: Optional[Callable[[], float]] = None,
           command_timeout: float = COMMAND_TIMEOUT_SECONDS,
           commands: Optional[List[Dict[str, Any]]] = None,
           result: Optional[Mapping[str, Any]] = None, count: bool = True) -> Tuple[Dict[str, str], str]:
    """Run every command of this stage once on the candidate; return (record writes, refusal text).

    An empty refusal means every command passed (``judge``).  At the test stage each focused and regression command is
    also held to its floor (``floor_detail``, which reads ``result``'s retired_tests); at the item's rerun stage (document)
    to the most any accepted run of it ran since the step plan (``accepted_counts``); the outer stages and the
    end-of-work review to none.  A command that times out or cannot start refuses the stage, but the attempt is
    recorded ``could-not-run`` and does not count in ``refused_runs``.  ``command_timeout`` bounds each command; every
    command runs, with no total time budget.

    ``count=False`` (``complete --check-only``) runs the same commands and judgement and writes ``check_only_path``
    instead of a numbered record, so the run never counts as a refused run or sets a floor.
    Where the commands run in the repository (every stage but release-verify, whose place can change with a return), it
    also records the command list and the working trees the run started on and left; a counted run (``complete``) then
    takes a passed check-only run whose command list and tree are unchanged instead of running again (``_reused``), and
    its record says so under ``reused``.
    """
    root = Path(root)
    if commands is None:
        commands, _reason = stage_commands(state, stage, work_item)
    if not commands:
        return {}, ""
    refused = refused_runs(root, action)
    number = _verify_count(root, action) + 1
    runner = runner or lint.run_argv
    clock = clock or time.monotonic
    repo = Path(str(state["repo"]))
    environment = dict(os.environ if env is None else env)
    cwd, failure = repo, ""
    observed = observation(root, state, stage)
    if observed and observed["where"] == "returned-result":
        try:
            copy = workspace.export_returned_result(Path(root).parent)
            cwd = Path(copy["path"])
            observed = {"where": "returned-result", **{key: value for key, value in copy.items() if key != "path"}}
            # No parent repository above the copy is discoverable: a command's `git` must not reach the user's tree.
            environment["GIT_CEILING_DIRECTORIES"] = os.pathsep.join(
                part for part in (str(cwd.parent), environment.get("GIT_CEILING_DIRECTORIES", "")) if part)
        except workspace.WorkspaceError as exc:
            failure = str(exc)
    elif observed and observed["where"] == "unknown":
        failure = str(observed["reason"])
    if stage in STAGES:
        held = floor_detail(root, state, work_item, action, result)
    elif stage in OUTER_SOURCES or not work_item:
        held = {}
    else:
        held = {command: {"floor": ran, "from": "an earlier run of this command that ShipLoop accepted for this item"}
                for command, ran in accepted_counts(root, state, work_item).items()}
    reused = _reused(root, action, stage, work_item, commands, repo, held) if count and observed is None else None
    if reused is not None:
        record = {
            "schema": SCHEMA, "action": action, "stage": stage, "work_item": work_item,
            "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "cwd": str(cwd), "passed": True, "disposition": "passed", "runs": reused[0],
            "attempt": _next_attempt(root, action), "reused": reused[1],
        }
        return {verify_path(action, number): store.dumps(record, "ShipLoop test-loop verification")}, ""
    trees = [_tree(root, repo)] if not count and observed is None else []
    runs: List[Dict[str, Any]] = []
    for row in commands:
        if failure:
            # The place the commands were to run in cannot be made or read: no command started, which says nothing about
            # the product (could-not-run), and is never answered by running in the work area instead.
            runs.append({**row, "status": "error", "exit": None, "seconds": 0.0, "stdout": "", "stderr": failure})
            continue
        fields, output = _run_command(runner, row["command"], cwd, command_timeout, environment, clock)
        run: Dict[str, Any] = {**row, **fields}
        if "status" not in run:
            run.update(judge(row, run["exit"], output))
            floor = held.get(row["command"])
            if floor:
                run["accepted_ran"] = floor["floor"]
                run["floor_from"] = floor["from"]
                if run["status"] == "passed" and run["counts"] and run["counts"]["ran"] < floor["floor"]:
                    run["status"] = "too-few-tests"
        runs.append(run)
    if stage == "system-test":
        def run_one(command: str) -> Optional[Tuple[int, str]]:
            """Run one command under its hang guard; returns (exit code, combined output), or None when it cannot
            start.
            """
            try:
                _status, code, out, err = runner(["/bin/sh", "-c", command], repo, command_timeout,
                                                 input_bytes=b"", env=environment)
            except OSError:
                return None
            return (code if code is not None else -1), out.decode("utf-8", "replace") + "\n" + err.decode("utf-8", "replace")
        runs += default_suite_drift(state, commands, run_one)
    disposition = _disposition(runs, PASSING)
    record = {
        "schema": SCHEMA, "action": action, "stage": stage, "work_item": work_item,
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "cwd": str(cwd), "passed": disposition == "passed", "disposition": disposition,
        "runs": runs,
    }
    if count:
        record["attempt"] = _next_attempt(root, action)
    else:
        record["counted"] = False
        if trees:
            # What a later ``complete`` compares before it takes this run (``_reused``): the trees it started on and
            # left (a command may write an untracked file; the model may remove one) and the exact command list.
            record["commands"] = [dict(row) for row in commands]
            record["trees"] = [tree for tree in dict.fromkeys([*trees, _tree(root, repo)]) if tree]
    if observed is not None:
        record["observed"] = observed
    relative = verify_path(action, number) if count else check_only_path(action)
    writes = {relative: store.dumps(record, "ShipLoop test-loop verification")}
    if record["passed"]:
        return writes, ""
    failing = [run for run in runs if run["status"] not in PASSING]
    listed = str(len(runs)) + " listed command" + ("" if len(runs) == 1 else "s")
    if failure:
        # The place was never made or read, so no command ran anywhere: do not say they ran "from" it.
        lines = ["ShipLoop test run: " + stage + " is not done. ShipLoop could not start the " + listed
                 + ", so none ran:"]
    else:
        lines = ["ShipLoop test run: " + stage + " is not done. ShipLoop ran the " + listed + " from "
                 + _where(observed, repo) + " and " + str(len(failing)) + " did not pass:"]
    for run in failing:
        lines.append("- [" + run["suite"] + "] " + run["command"] + " -> " + _explain(run, stage))
        tail = (run["stdout"] + "\n" + run["stderr"]).strip().splitlines()[-15:]
        lines += ["    | " + line for line in tail]
    if failure:
        lines.append(_place_reply(stage, refused) + " Full output: " + str(root / relative) + ".")
        return writes, "\n".join(lines)
    if not count:
        attempts = "This check-only run does not count toward the refused runs."
    elif disposition == "could-not-run":
        attempts = _unavailable_sentence(stage, refused, command_timeout)
    else:
        attempts = refused_note(refused + 1, stage)
    if stage in STAGES:
        lines.append("Fix the code (or a test, for an independent reason you record), start the Until Loop again with "
                     "the packet's start command (its receipt is replaced), then submit done again. " + attempts
                     + " Full output: " + str(root / relative) + ".")
    elif stage in OUTER_SOURCES and all(run["status"] == "uncounted" for run in failing):
        # Nothing here is a product failure: the recorded command itself cannot be counted, and only an add-work
        # reaches the stage that records it, so a "fix the code" line would send the model the wrong way.
        lines.append("Report add-work as named above, not done: no change to the code makes a recorded command "
                     "countable. Refused runs for this action so far: " + str(refused + 1) + " (" + REFUSED_TALLY
                     + "); add-work does not wait for them. Full output: " + str(root / relative) + ".")
    elif observed is not None and observed["where"] == "returned-result" and disposition == "failed":
        # The generic reply ("fix the code") has no way out here: this stage cannot edit the commands or return.
        lines.append(_copy_refusal(observed) + " " + attempts + " Full output: " + str(root / relative) + ".")
    else:
        lines.append("Fix the code so every command passes (never change a check to get green), then submit "
                     "done again. " + attempts + " Full output: " + str(root / relative) + ".")
    return writes, "\n".join(lines)


def _write(root: Path, writes: Mapping[str, str]) -> None:
    for relative, text in writes.items():
        store.atomic_write_text(Path(root) / relative, text)


def loop_run(root: Path, state: Mapping[str, Any], work_item: str, action_id: str,
             result: Optional[Mapping[str, Any]] = None, *, count: bool = True, **options: Any) -> List[str]:
    """The test stage's candidate run: every recorded command once, held to its floor; raises ``TestLoopError``.

    Writes ShipLoop's record (``tests/<action>-verify<N>.md``) either way and returns one summary line per command.
    ``result`` is the submitted test result (its ``retired_tests`` lower a floor).  ``count=False`` is the
    non-counting run ``complete --check-only`` makes: the same judgement, recorded at ``check_only_path`` and never
    counted as a refused run (see ``verify``).  ``options`` pass through to ``verify`` (runner, env, clock,
    command_timeout).
    """
    writes, refusal = verify(root, state, work_item, action_id, STAGES[0], result=result, count=count, **options)
    _write(root, writes)
    _need(not refusal, refusal)
    lines: List[str] = []
    if count:
        number = _verify_count(root, action_id)
        path = verify_path(action_id, number) if number else ""
    else:
        path = check_only_path(action_id)
    if path and (Path(root) / path).is_file():
        record = store.read_record(Path(root) / path)
        if record.get("reused"):
            lines.append("candidate: reused the passed check-only run of " + str(record["reused"]["created_at"])
                         + " (" + str(record["reused"]["path"]) + "): the tree and the recorded commands are unchanged")
        for run in record.get("runs") or ():
            tally = run.get("counts") or {}
            lines.append("candidate: [" + run["suite"] + "] " + run["command"] + " -> " + run["status"]
                         + (" (" + str(tally.get("ran")) + " ran" + (", floor " + str(run["accepted_ran"])
                                                                    if run.get("accepted_ran") else "") + ")"
                            if tally else ""))
    return lines


# ---------------------------------------------------------------- the step Proof (inline implement, unit W2-A)

def _proof_records(root: Path, action: str) -> List[Tuple[str, Mapping[str, Any]]]:
    """(run-relative path, record) of this action's readable Proof records: the check-only one, then the numbered ones."""
    found: List[Tuple[str, Mapping[str, Any]]] = []
    paths = [step_proof_check_only_path(action)] + [step_proof_path(action, n)
                                                     for n in range(1, _count(root, action, step_proof_path) + 1)]
    for relative in paths:
        try:
            record = store.read_record(Path(root) / relative) if (Path(root) / relative).is_file() else None
        except (OSError, store.StorageError):
            record = None
        if isinstance(record, Mapping):
            found.append((relative, record))
    return found


def step_proof(root: Path, state: Mapping[str, Any], work_item: str, action: str, *, count: bool = True,
               phase: str = "complete", runner: Optional[Runner] = None, env: Optional[Mapping[str, str]] = None,
               clock: Optional[Callable[[], float]] = None, command_timeout: float = COMMAND_TIMEOUT_SECONDS) -> Tuple[Dict[str, str], str, List[str]]:
    """Run the inline implement step's Proof on the candidate; return (record writes, refusal body, summary lines).

    The Proof is the step plan's ``check`` for the step (``step_command``), judged as a check (``judge``: exit 0, and a
    runner summary that shows no test ran is no pass), with the test loop's timeout and capture.  Its record
    (``step_proof_path``, or ``step_proof_check_only_path`` for ``count=False``) is bound to the action, the step, the
    command and the candidate: the working trees the run started on and left (``_tree``).  A passed record of this
    action for the same step and command whose trees include today's is taken instead of running again, so an
    unchanged candidate reuses its receipt; at complete that writes a numbered record that says so, and at the Improve
    import (``phase`` "improve-import") nothing is written.  An empty refusal means the Proof passed.  A step with no
    check is refused: the step plan gate requires one, so only a run positioned another way lacks it.
    """
    root = Path(root)
    found = step_command(state, work_item)
    if found is None:
        return {}, ("ShipLoop step proof: the step this action builds records no check (its Proof) in the accepted step "
                    "plan, so ShipLoop cannot confirm it. Report send-back so the step plan records one."), []
    step, row = found
    step_id = str(step.get("id"))
    repo = Path(str(state["repo"]))
    tree = _tree(root, repo)
    number = _count(root, action, step_proof_path) + 1
    matched = next(((relative, record) for relative, record in reversed(_proof_records(root, action))
                    if record.get("passed") is True and record.get("step") == step_id
                    and record.get("command") == row["command"] and tree and tree in (record.get("trees") or ())),
                   None) if count else None
    created = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    if matched is not None:
        line = ("step-proof: reused the passed " + ("check-only run" if "check-only" in matched[0] else "run") + " of "
                + str(matched[1].get("created_at")) + " (" + matched[0] + "): the candidate is unchanged")
        if phase != "complete":
            return {}, "", [line]
        record = {"schema": SCHEMA, "kind": "step-proof", "action": action, "stage": STEP_PROOF_STAGES[0],
                  "work_item": work_item, "step": step_id, "command": row["command"], "phase": phase,
                  "created_at": created, "cwd": str(repo), "passed": True, "disposition": "passed",
                  "runs": list(matched[1].get("runs") or ()), "trees": [tree],
                  "reused": {"path": matched[0], "created_at": matched[1].get("created_at"), "tree": tree}}
        return {step_proof_path(action, number): store.dumps(record, "ShipLoop step proof")}, "", [line]
    runner = runner or lint.run_argv
    clock = clock or time.monotonic
    environment = dict(os.environ if env is None else env)
    fields, output = _run_command(runner, row["command"], repo, command_timeout, environment, clock)
    run: Dict[str, Any] = {**row, **fields}
    if "status" not in run:
        run.update(judge(row, run["exit"], output))
    disposition = _disposition([run], PASSING)
    record = {"schema": SCHEMA, "kind": "step-proof", "action": action, "stage": STEP_PROOF_STAGES[0],
              "work_item": work_item, "step": step_id, "command": row["command"], "phase": phase,
              "created_at": created, "cwd": str(repo), "passed": disposition == "passed", "disposition": disposition,
              "runs": [run], "trees": [found_tree for found_tree in dict.fromkeys([tree, _tree(root, repo)]) if found_tree]}
    if not count:
        record["counted"] = False
    relative = step_proof_path(action, number) if count else step_proof_check_only_path(action)
    writes = {relative: store.dumps(record, "ShipLoop step proof")}
    summary = ["step-proof: [check] " + row["command"] + " -> " + run["status"]]
    if record["passed"]:
        return writes, "", summary
    tail = (str(run.get("stdout") or "") + "\n" + str(run.get("stderr") or "")).strip().splitlines()[-15:]
    headline = ("the review changed step " + step_id + " and its Proof did not pass, so the step is not accepted"
                if phase == "improve-import" else
                "step " + step_id + "'s Proof did not pass, so its " + STEP_PROOF_STAGES[0] + " is not done")
    lines = ["ShipLoop step proof: " + headline + ". ShipLoop ran it from " + str(repo) + ":",
             "- " + row["command"] + " -> " + _explain(run, STEP_PROOF_STAGES[0]),
             *("    | " + line for line in tail),
             "Full output: " + str(root / relative) + "."]
    return writes, "\n".join(lines), summary


# ---------------------------------------------------------------- the base run (test stage, before the candidate run)

def _item_changes(root: Path, base: Mapping[str, Any]) -> List[Tuple[str, str]]:
    """(status, toplevel-relative path) for each path the item changed since its lint base, under its prefix."""
    top = Path(base["toplevel"])
    prefix = str(base.get("prefix") or ".")
    index = Path(root) / "lint" / "tmp" / ("test-base-" + os.urandom(8).hex() + ".index")
    try:
        current = lint.snapshot_tree(top, Path(root), index, prefix=prefix)
    finally:
        if index.exists():
            index.unlink()
    listed = lint._git(top, "diff-tree", "-r", "-z", "--no-renames", "--name-status", str(base["tree"]), current)
    _need(listed.returncode == 0, "cannot diff the item base against the working tree: "
          + listed.stderr.decode("utf-8", "replace").strip())
    fields = [field.decode("utf-8", "surrogateescape") for field in listed.stdout.split(b"\0") if field]
    lead = "" if prefix in (".", "") else prefix.rstrip("/") + "/"
    return [(fields[i][:1], fields[i + 1]) for i in range(0, len(fields) - 1, 2)
            if fields[i + 1].startswith(lead) and not lint._runtime_path(fields[i + 1])]


def _relative(path: str, base: Mapping[str, Any]) -> str:
    prefix = str(base.get("prefix") or ".")
    lead = "" if prefix in (".", "") else prefix.rstrip("/") + "/"
    return path[len(lead):]


def _at_commit(base: Mapping[str, Any], commit: str) -> Dict[str, Any]:
    """The lint base moved to ``commit`` (a preparatory-fix commit that landed before implement): its tree and head."""
    resolved = lint._git(Path(base["toplevel"]), "rev-parse", "--verify", "-q", commit + "^{commit}")
    tree = lint._git(Path(base["toplevel"]), "rev-parse", "--verify", "-q", commit + "^{tree}")
    _need(resolved.returncode == 0 and tree.returncode == 0, "the base commit " + commit + " is not a commit here")
    return {**base, "commit": resolved.stdout.decode("ascii").strip(), "head": resolved.stdout.decode("ascii").strip(),
            "tree": tree.stdout.decode("ascii").strip()}


class _BaseTree:
    """A temporary detached worktree at the lint base tree, with the item's test files copied in; removed on exit.

    Entering yields the directory that stands for the repository (the worktree, or its prefix within it).
    """

    def __init__(self, root: Path, base: Mapping[str, Any], tests: Sequence[str]) -> None:
        self.top = Path(base["toplevel"])
        self.base = base
        self.tests = list(tests)
        self.temp = Path(tempfile.mkdtemp(prefix="shiploop-test-base-"))
        self.tree = self.temp / "base"
        self.added = False

    def __enter__(self) -> Path:
        try:
            return self._make()
        except BaseException:
            self.__exit__()
            raise

    def _make(self) -> Path:
        """Create the temporary detached git worktree at ``self.tree`` for the lint base, copy the item's test
        files into it, and return the directory that stands for the repository. When the base has no ``commit``
        it first makes a dangling commit of the base ``tree`` with a fixed ShipLoop identity. It sets
        ``self.added`` and symlinks each dependency directory a platform card lists that is a directory in the
        checkout and not already present in the returned directory. Raises ``TestLoopError`` if the commit or worktree
        cannot be made; the file copies and git calls can also raise ``OSError`` or ``lint.LintError``.
        """
        import shiploop_mutation as mutation  # imports this module: resolved at call time

        identity = {"GIT_AUTHOR_NAME": "ShipLoop", "GIT_AUTHOR_EMAIL": "shiploop@localhost",
                    "GIT_COMMITTER_NAME": "ShipLoop", "GIT_COMMITTER_EMAIL": "shiploop@localhost"}
        commit = str(self.base.get("commit") or "")
        if not commit:
            # The lint base is a tree (tracked plus untracked content), not a commit: make a dangling one for it.
            parent = ["-p", str(self.base["head"])] if self.base.get("head") else []
            made = lint._git(self.top, "commit-tree", str(self.base["tree"]), *parent, "-m",
                             "ShipLoop item base (temporary)", env=identity)
            _need(made.returncode == 0, "cannot make a commit of the item base tree: "
                  + made.stderr.decode("utf-8", "replace").strip())
            commit = made.stdout.decode("ascii", "replace").strip()
        added = lint._git(self.top, "worktree", "add", "--detach", "--quiet", os.fspath(self.tree), commit)
        _need(added.returncode == 0, "cannot add a temporary worktree at the item base: "
              + added.stderr.decode("utf-8", "replace").strip())
        self.added = True
        for path in self.tests:
            source, target = self.top / path, self.tree / path
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.is_symlink() or target.is_file():
                target.unlink()
            shutil.copy2(os.fspath(source), os.fspath(target), follow_symlinks=False)
        prefix = str(self.base.get("prefix") or ".")
        cwd = self.tree if prefix in (".", "") else self.tree / prefix
        checkout = self.top if prefix in (".", "") else self.top / prefix
        for name in mutation.dependency_directories():
            if (checkout / name).is_dir() and not os.path.lexists(cwd / name):
                (cwd / name).symlink_to(checkout / name, target_is_directory=True)
        return cwd

    def __exit__(self, *_exc: Any) -> None:
        try:
            if self.added:
                lint._git(self.top, "worktree", "remove", "--force", os.fspath(self.tree))
        finally:
            shutil.rmtree(self.temp, ignore_errors=True)
            lint._git(self.top, "worktree", "prune")


def base_worktree(root: Path, base: Mapping[str, Any], *, commit: Optional[str] = None,
                  copies: Sequence[str] = ()) -> _BaseTree:
    """A context manager: a temporary detached worktree at an item's lint base, removed on exit.

    ``base`` is ``shiploop_lint.read_base``'s record; ``commit`` moves it to a later commit (a preparatory fix).
    ``copies`` are toplevel-relative files copied in from the checkout.  Entering yields the directory that stands
    for the repository; it raises ``TestLoopError`` when the worktree cannot be made.  Shared by the test stage's
    base run and validate-existing's re-entry checks.
    """
    return _BaseTree(root, _at_commit(base, commit) if commit else base, copies)


def _retired_removed(base: Mapping[str, Any], changes: Sequence[Tuple[str, str]], retired: Sequence[str],
                     item_scope: Any) -> List[str]:
    """The retired IDs written (as a word) in a changed or deleted test file on the base, and in none of them now."""
    if not retired:
        return []
    top = Path(base["toplevel"])
    before, after = [], []
    for status, path in changes:
        if status not in ("M", "D", "T") or item_scope.classify(_relative(path, base)) != "test":
            continue
        shown = lint._git(top, "cat-file", "blob", str(base["tree"]) + ":" + path)
        if shown.returncode == 0:
            before.append(shown.stdout.decode("utf-8", "replace"))
        if status != "D" and (top / path).is_file():
            after.append((top / path).read_text(encoding="utf-8", errors="replace"))
    found = []
    for test_id in retired:
        pattern = re.compile(r"(?<![\w-])" + re.escape(test_id) + r"(?![\w])")
        if any(pattern.search(text) for text in before) and not any(pattern.search(text) for text in after):
            found.append(test_id)
    return found


def _load_names(path: str) -> List[str]:
    """The ways a load failure can name a file: its path, the path without extension, its name, its dotted module."""
    stem, ext = os.path.splitext(path)
    names = [path, os.path.basename(path)]
    if ext:
        names.append(stem)
    if ext == ".py":
        parts = stem.split("/")
        if parts[-1] == "__init__":
            parts = parts[:-1]
        names += ["'" + ".".join(parts[i:]) + "'" for i in range(len(parts))]
        names += ['"' + ".".join(parts[i:]) + '"' for i in range(len(parts))]
    return [name for name in names if len(name.strip("'\"")) >= 2]


def _added_named(output: str, added: Sequence[str]) -> List[str]:
    """The added paths a run's output names (a load failure of a file this item adds).

    A line that is only a path does not count: a command that prints an added file's path and then fails on a
    file-exists guard reported no load failure, yet read as RED (a live run, 2026-10-20: ``printf '%s\\n' <new file> &&
    test -f <new file> && ...`` stood in for the item's tests).  A real loader names the file inside its error line."""
    lines = [line for line in output.splitlines() if not re.fullmatch(r"\S+", line.strip())]
    text = "\n".join(lines)
    found = []
    for path in added:
        for name in _load_names(path):
            pattern = (re.escape(name) if name[:1] in "'\"" else r"(?<![\w.-])" + re.escape(name) + r"(?![\w-])")
            if re.search(pattern, text):
                found.append(path)
                break
    return found


def _judge_base(row: Mapping[str, Any], code: Optional[int], output: str, exempt: Sequence[str],
                retired: Sequence[str], added: Sequence[str], earlier_step: bool = False) -> Dict[str, Any]:
    """Classify one base run: a focused command's new IDs must not pass; every command is counted for the floor.

    ``status`` is ``red`` (accepted), ``counted`` (a regression command, or with ``earlier_step`` a focused command
    holding only earlier steps' cases, which pass on this step's base: only its count matters), ``passes-on-base``
    (a new ID passed, or a focused command without ids exited 0 with no reporter-recognised failure in its tally),
    ``unread`` (a new ID is named but no line says how it ended) or ``not-run`` (a new ID is missing and no load
    failure names a file the item adds).
    """
    tally = counts.count(output, code)
    verdict: Dict[str, Any] = {"counts": tally}
    if retired:
        verdict["retired_shown"] = counts.named(output, list(retired))["shown"]
    if row["suite"] != "focused" or earlier_step:
        verdict["status"] = "counted"
        if earlier_step:
            verdict["earlier_step"] = True
        return verdict
    ids = [test_id for test_id in row.get("ids") or () if test_id not in exempt]
    if not row.get("ids"):
        masked_failure = code == 0 and tally is not None and tally["failed"] > 0
        verdict["status"] = "red" if code != 0 or masked_failure else "passes-on-base"
        return verdict
    per_id = counts.outcomes(output, ids)
    verdict["id_outcomes"] = per_id
    # A load failure that names a file this item adds counts as RED: the tests come after the build, so on new code
    # nothing can run on the base.  That proves nothing about the assertions; the mutation check on the candidate
    # (``mutation_check``) is what proves the tests assert real behaviour.
    loads = _added_named(output, added) if code != 0 else []
    if loads:
        verdict["load_failure_names"] = loads
    passing = [test_id for test_id, outcome in per_id.items() if outcome == "passed"]
    unread = [test_id for test_id, outcome in per_id.items() if outcome == "shown"]
    unrun = [test_id for test_id, outcome in per_id.items() if outcome == "missing"] if not loads else []
    if passing:
        verdict.update(status="passes-on-base", ids_passing=passing)
    elif unread:
        verdict.update(status="unread", ids_unread=unread)
    elif unrun:
        verdict.update(status="not-run", ids_unrun=unrun)
    else:
        verdict["status"] = "red"
    return verdict


# ``remote``: a command that tests a deployed target (a platform card lists it under Remote tests) is not run on the
# base, so it has no base verdict and no base count (its floor then comes from the earlier runs).
BASE_GOOD = ("red", "counted", "remote")


def _remote_base(row: Mapping[str, Any], stateful: Optional[Mapping[str, str]] = None) -> Optional[Dict[str, Any]]:
    """The base-run row of a command that tests a deployed target, or None for one that runs on the checkout.

    On the base such a command would test the target, which already holds this item's change (an earlier step deployed
    it), so a new test passes there for no fault of its own; running it would also deploy the base's files to the
    target.  A live run (2026-10-20) took a send-back for exactly that.  The candidate runs still judge it."""
    import shiploop_mutation as mutation  # imports this module: resolved at call time

    target = row.get("target")
    if target and target in (stateful or {}):
        # A test-strategy target that keeps state holds the item's change too, whatever platform it is (F3).
        return {**row, "status": "remote", "exit": None, "seconds": 0.0, "stdout": "", "stderr": "",
                "reason": ("runs on " + str(target) + ", which keeps state between runs (test-strategy targets; base "
                           "state: " + (stateful or {})[target] + "), so it already holds this item's change; not run "
                           "on the base")}
    hit = mutation.remote_card(row["command"])
    if hit is None:
        return None
    card, prefix = hit
    return {**row, "status": "remote", "exit": None, "seconds": 0.0, "stdout": "", "stderr": "",
            "reason": ("tests a deployed target (platforms/" + card + ".md lists `" + prefix + "` under Remote tests), "
                       "which already holds this item's change; not run on the base")}


def _explain_base(run: Mapping[str, Any]) -> str:
    status = run["status"]
    if status == "passes-on-base":
        if run.get("ids_passing"):
            return ("passed " + ", ".join(run["ids_passing"]) + " on the item's base, without this item's change: "
                    "such a test does not detect the change. Make it assert the behaviour the test spec defines "
                    "(which the base lacks); if it must pass already (a characterisation test, or a case a step committed "
                    "before a send-back), name it in the result's red_na with the reason. A command that names the checkout by an absolute path runs the "
                    "candidate, not the base: use a path relative to the repository.")
        return ("exited 0 on the item's base: no test failed without this item's change. List the case IDs it must run "
                "so ShipLoop can judge each one, and make the tests assert the behaviour the change adds.")
    if status == "unread":
        return ("named " + ", ".join(run["ids_unread"]) + " on the base, but no output line says whether it passed or "
                "failed. Use a reporter that marks each test's outcome on the line that names it; the stack's platform "
                "card under references/platforms/ names a readable one.")
    if status == "not-run":
        # The exit code and whether anything printed are facts the record holds; the output's last lines follow this
        # explanation.  Neither says why: a command that never started and one that asserted ahead of its first print
        # look the same here.
        printed = (str(run.get("stdout") or "") + str(run.get("stderr") or "")).strip()
        exited = ("" if run.get("exit") is None
                  else "exited " + str(run["exit"]) + ("" if printed else " and printed nothing") + ": it ")
        return (exited + "did not run " + ", ".join(run["ids_unrun"]) + " on the base, and no load failure in its "
                "output names a file this item adds. A new test must fail on the base because the behaviour it asserts "
                "is missing (a load error for code this item adds counts); a guard that only checks or prints a file's "
                "path is not that failure, so assert the behaviour instead. A command that fails before it prints (an "
                "assert or exception ahead of the print) shows no ID: make it print the ID and its outcome on every "
                "exit.")
    return _explain(run)


def _base_run(root: Path, state: Mapping[str, Any], work_item: str, action: str,
              result: Optional[Mapping[str, Any]], *, base_commit: Optional[str] = None,
              runner: Optional[Runner] = None,
              env: Optional[Mapping[str, str]] = None, clock: Optional[Callable[[], float]] = None,
              command_timeout: float = COMMAND_TIMEOUT_SECONDS) -> Tuple[Dict[str, Any], str]:
    """Run the focused and regression commands on the item's base; return (record, refusal text)."""
    root = Path(root)
    commands = base_commands(state, work_item)
    exempt = [row["id"] for row in _id_records(result, RED_NA)]
    retired = [row["id"] for row in _id_records(result, RETIRED_TESTS)]
    # RED holds only this step's new cases (design T §9 row 4): an earlier step's cases already pass on this step's base,
    # which is what they should do, so the base run does not judge them (``new_ids``), and a command holding only those
    # cases, with or without IDs, is counted (``_earlier_step``).
    new = set(new_ids(state, work_item))
    earlier = [test_id for row in commands if row["suite"] == "focused" for test_id in row.get("ids") or ()
               if test_id not in new]
    record: Dict[str, Any] = {
        "schema": BASE_SCHEMA, "action": action, "stage": STAGES[0], "work_item": work_item,
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "red_na": exempt, "retired_tests": retired, "runs": [],
        **({"earlier_steps": earlier} if earlier else {}),
    }
    base = lint.read_base(root, work_item)
    if base is not None and base_commit:
        base = _at_commit(base, base_commit)
    if not commands or base is None:
        # The gate did nothing: say so in the record's disposition (``passed`` stays true, so every reader of ``passed``
        # behaves as before) rather than file the same word a real proof files.
        record.update(passed=True, disposition="skipped",
                      skipped=("no focused or regression command" if not commands
                               else "no item base was recorded (not a Git checkout, or the base was not captured)"))
        return record, ""
    record.update(base_tree=base.get("tree"), base_head=base.get("head"), base_commit=base.get("commit"))
    changes = _item_changes(root, base)
    import shiploop_item_scope as item_scope  # imports this module: resolved at call time

    tests = [path for status, path in changes if status in ("A", "M", "T")
             and item_scope.classify(_relative(path, base)) == "test"]
    added = [_relative(path, base) for status, path in changes if status == "A" and path not in tests]
    record.update(test_files=[_relative(path, base) for path in tests], added_files=added)
    removed = _retired_removed(base, changes, retired, item_scope)
    runner = runner or lint.run_argv
    clock = clock or time.monotonic
    environment = dict(os.environ if env is None else env)
    runs: List[Dict[str, Any]] = []
    failure = ""
    try:
        with _BaseTree(root, base, tests) as cwd:
            record["cwd"] = str(cwd)
            stateful = stateful_targets(state)
            for row in commands:
                remote = _remote_base(row, stateful)
                if remote is not None:
                    runs.append(remote)
                    continue
                fields, output = _run_command(runner, row["command"], cwd, command_timeout, environment, clock)
                run = {**row, **fields}
                if "status" not in run:
                    run.update(_judge_base(row, run["exit"], output, [*exempt, *earlier], retired, added,
                                           _earlier_step(state, work_item, row)))
                runs.append(run)
    except (TestLoopError, lint.LintError, OSError) as exc:
        failure = str(exc)
        runs = [{**row, "status": "error", "exit": None, "seconds": 0.0, "stdout": "", "stderr": failure}
                for row in commands]
    record["runs"] = runs
    if runs and all(run["status"] == "remote" for run in runs):
        # Nothing ran: the gate did nothing, so the record says skipped, as the mutation check does for the same case.
        record.update(passed=True, disposition="skipped", skipped="every command " + runs[0]["reason"])
        return record, ""
    problems = []
    seen = [test_id for test_id in retired
            if any(test_id in (run.get("retired_shown") or ()) for run in runs) or test_id in removed]
    record["retired_seen"] = seen
    unseen = [test_id for test_id in retired if test_id not in seen]
    if unseen and not failure and all(run["status"] not in UNAVAILABLE for run in runs):
        problems.append("retired_tests names " + ", ".join(unseen) + ", which ShipLoop cannot see removed: no base run "
                        "showed it, and no test file this item changed or deleted held it on the base and not now. "
                        "Give its name as the runner prints it (and make the command print test names), or as it is "
                        "written in the test file it was removed from.")
    disposition = _disposition(runs, BASE_GOOD)
    if problems and disposition == "passed":
        disposition = "failed"
    record.update(passed=disposition == "passed", disposition=disposition)
    if record["passed"]:
        return record, ""
    failing = [run for run in runs if run["status"] not in BASE_GOOD]
    lines = ["ShipLoop base run: test is not done. ShipLoop ran " + str(len(runs)) + " focused and regression "
             "command" + ("" if len(runs) == 1 else "s") + " on the item's base (lint base "
             + str(base.get("tree"))[:12] + ", with this item's " + str(len(tests)) + " test file"
             + ("" if len(tests) == 1 else "s") + " copied in)" + (": " + failure if failure else "") + ":"]
    for run in failing:
        lines.append("- [" + run["suite"] + "] " + run["command"] + " -> " + _explain_base(run))
        tail = (run["stdout"] + "\n" + run["stderr"]).strip().splitlines()[-15:]
        lines += ["    | " + line for line in tail]
    lines += ["- " + problem for problem in problems]
    return record, "\n".join(lines)


def base_check(root: Path, state: Mapping[str, Any], work_item: str, action_id: str,
               result: Optional[Mapping[str, Any]] = None, *, base_commit: Optional[str] = None,
               **options: Any) -> List[str]:
    """The test stage's base run at complete; raises ``TestLoopError`` with the refusal.

    Checks ``result``'s red_na and retired_tests first (``check_result_fields``), then runs every focused and
    regression command in a temporary detached worktree at the item's lint base with only this item's test files
    copied in.  Refused: a new test ID passes there and red_na does not name it, a new ID's outcome cannot be read, a
    new ID did not run and no load failure names a file the item adds, or a retired test that no base run showed.  The
    record ``tests/<action>-base<N>.md`` holds each command's base count (the floor's base term) and counts in
    ``refused_runs`` with the candidate runs.  Returns one summary line per command.  ``options`` pass through
    (runner, env, clock, command_timeout).
    """
    root = Path(root)
    check_result_fields(state, work_item, result)
    refused = refused_runs(root, action_id)
    record, refusal = _base_run(root, state, work_item, action_id, result, base_commit=base_commit, **options)
    record["attempt"] = _next_attempt(root, action_id)
    relative = base_path(action_id, _base_count(root, action_id) + 1)
    store.atomic_write_text(root / relative, store.dumps(record, "ShipLoop test base run"))
    if refusal:
        if record["disposition"] == "could-not-run":
            tail = _unavailable_sentence(STAGES[0], refused, options.get("command_timeout", COMMAND_TIMEOUT_SECONDS))
        else:
            tail = refused_note(refused + 1, STAGES[0])
        raise TestLoopError(refusal + "\nFix the tests (or red_na / retired_tests), start the Until Loop again, then "
                            "submit done again. " + tail + " Full output: " + str(root / relative) + ".")
    return _base_summary(record)


def _base_summary(record: Mapping[str, Any]) -> List[str]:
    if record.get("skipped"):
        return ["base: skipped (" + str(record["skipped"]) + ")"]
    lines = []
    for run in record.get("runs") or ():
        tally = run.get("counts") or {}
        lines.append("base: [" + run["suite"] + "] " + run["command"] + " -> " + run["status"]
                     + (" (earlier steps' cases)" if run.get("earlier_step") else "")
                     + (" (" + str(tally.get("ran")) + " ran)" if tally else ""))
    return lines


def mutation_check(root: Path, state: Mapping[str, Any], work_item: str, action_id: str,
                   result: Optional[Mapping[str, Any]] = None, *, count: bool = True, **options: Any) -> List[str]:
    """The test stage's mutation check after ``loop_run`` passed (``shiploop_mutation.mutation_check``).

    Raises ``TestLoopError`` when at least one mutant of the item's changed product lines ran and the focused commands
    killed none.  ``options`` pass through (base_commit, runner, env, clock).
    """
    import shiploop_mutation as mutation  # imports this module: resolved at call time

    return mutation.mutation_check(root, state, work_item, action_id, result, count=count, **options)


def red_check(root: Path, state: Mapping[str, Any], work_item: str, action_id: str,
              result: Optional[Mapping[str, Any]] = None, *, base_commit: Optional[str] = None,
              **options: Any) -> Tuple[bool, List[str]]:
    """The loop's own view of the base rule: run the base check now, never counted; return (would pass, report lines).

    Writes ``tests/<action>-red-check.md`` (replaced each call).  ``result`` may carry the red_na and retired_tests the
    model intends to submit; without it, every test ID new at this step must fail on the base.
    """
    root = Path(root)
    try:
        check_result_fields(state, work_item, result)
    except TestLoopError as exc:
        return False, [str(exc)]
    record, refusal = _base_run(root, state, work_item, action_id, result, base_commit=base_commit, **options)
    store.atomic_write_text(root / red_check_path(action_id), store.dumps(record, "ShipLoop red-check (not counted)"))
    lines = _base_summary(record)
    if refusal:
        lines += refusal.splitlines()
    lines.append("Full output: " + str(root / red_check_path(action_id)) + " (not counted toward the refused runs).")
    return not refusal, lines


__all__ = (
    "BASE_RULE",
    "BASE_STAGES",
    "COUNT_RULE",
    "FLOOR_RULE",
    "PASSING",
    "RATCHET_RULE",
    "REFUSED_TALLY",
    "RERUN_STAGES",
    "STAGES",
    "STEP_PROOF_STAGES",
    "UNAVAILABLE",
    "STEP_RERUN_STAGE",
    "VERIFY_STAGES",
    "TestLoopError",
    "accepted_counts",
    "action_counts",
    "base_check",
    "base_commands",
    "base_path",
    "base_worktree",
    "check_only_path",
    "check_result_fields",
    "default_suite_drift",
    "floor_detail",
    "floors",
    "judge",
    "latest_attempt_could_not_run",
    "loop_lines",
    "loop_run",
    "mutation_check",
    "mutation_check_only_path",
    "mutation_path",
    "new_ids",
    "normalise_commands",
    "observation",
    "observed_lines",
    "red_check",
    "red_check_path",
    "refused_note",
    "refused_runs",
    "remedy_open",
    "rerun_lines",
    "reuse_note",
    "rule_lines",
    "stage_commands",
    "step_command",
    "step_proof",
    "step_proof_check_only_path",
    "step_proof_path",
    "verify",
    "verify_path",
)
