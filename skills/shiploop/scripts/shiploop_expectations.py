"""Expectations: the facts a work item's steps build on, checked before the build (owner, 2026-10-10).

The step plan records ``expectations``; validate-existing has ShipLoop run their checks before anything is changed.

    expectations: [{"id": "E1", "state": "works" | "absent" | "broken", "statement": "...",
                    "steps": ["S1"], "paths": ["src/a.js"], "check": "<one shell command>", "from": "A3"}]

States:
- works: an existing thing a step changes or relies on works today;
- absent: a new thing does not exist yet and its place is free;
- broken: the request says it is broken, and the check reproduces the failure as reported.

Every check is one read-only shell command, run from the repository root, that exits 0 when the stated state holds.
That one rule covers all three states, so ShipLoop judges each check by its exit code alone.
- works: it exits 0 when the thing works (``grep -q 'export function parse' src/parse.js``).
- absent: it exits 0 when the place is free (``test ! -e src/new.js``).
- broken: it exits 0 when the failure reproduces as reported: it runs the failing thing and tests for the reported
  symptom (``node cli.js --x 2>&1 | grep -q 'TypeError: y'``), or negates a run that the report only says fails
  (``! npm test -- -t TC-3``).
A check that exits nonzero, times out or cannot start does not match its state.  So does a check that changed the
checkout: ShipLoop compares ``git status`` before and after each check.

Coverage, refused at the step-plan gate (``check_step_plan``):
- every path a step changes that exists on the item's base needs a works or broken expectation listing it in
  ``paths``, and every path that does not exist there needs an absent one;
- a works or broken expectation's paths exist on the base; an absent expectation's paths do not;
- every open plan assumption whose consumer is this item appears as an expectation's ``from``.

At validate-existing entry ShipLoop runs every check (``entry``); when all match, the navigator records the stage done
by script and issues no packet.  Otherwise the packet lists the results.  A works expectation found broken whose fix is
known and small is fixed in the working tree, touching only that expectation's paths; the model commits nothing.
On done ShipLoop reruns every check (``check_complete``), refuses a mismatch, refuses any change outside the paths of
the works expectations that did not match at entry, and returns the changed paths for the navigator to commit on
accept as one preparatory commit.

Where the checks run (``check_place``): on a first entry, in the checkout, which nothing has changed yet, so a
preparatory fix made there is checked there.  On re-entry -- the item already ran implement and the checkout holds
changes to the item's paths since its lint base, as after a revise back to step-plan -- every check runs in a temporary
detached worktree at the item's base (the lint base, moved to the preparatory commit when one was made), or an absent
expectation would fail on the item's own new files.  The entry record keeps the choice, and ``check_complete`` reruns
in the same place.  On re-entry no preparatory change is accepted: an edit in the checkout cannot change a check run
at the base.
"""

from __future__ import annotations

import fnmatch
import os
import re
import shlex
import shutil
import signal
import subprocess
import uuid
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Set, Tuple

import shiploop_item_scope as item_scope
import shiploop_lint as lint
import shiploop_store as store
import shiploop_test_loop as test_loop

STAGE = "validate-existing"
PLAN_STAGE = "step-plan"
TEST_SPEC_STAGE = "test-spec"
STATES = ("works", "absent", "broken")
# The states that cover a path present on the item's base, and those that cover a path that is not.
EXISTING_STATES = ("works", "broken")
NEW_STATES = ("absent",)
# How a revise result says the mismatch goes back to step-plan: the check is wrong (the fact holds), or the fact is
# false and the steps must change (a needed repair becomes an earlier step).
ROUTES = ("check", "steps")
KEYS = frozenset(("id", "state", "statement", "steps", "paths", "check", "from"))
SKILL_KEYS = frozenset(("name", "why", "locator"))
FAILED_KEYS = frozenset(("id", "actual", "route"))
CHECK_TIMEOUT_SECONDS = 60.0
OUTPUT_LIMIT = 64 * 1024
SCHEMA = "shiploop-expectations/v1"
# ShipLoop's knowledge home: validate-existing may record an environment fix there, and the knowledge commit owns it, so
# it is neither refused nor returned as a preparatory path.  The repository index at the root is the host's file: a change
# to it here is a stray path like any other.
KNOWLEDGE_PREFIX = "docs/shiploop/"
DONE_WHEN_PREPARATORY = "each preparatory fix touches only its expectation's paths; ShipLoop commits it on accept"
# The preparatory commit ShipLoop made for an item (the navigator writes it on accept); the test stage's base run and
# re-entry checks start from it.
PREPARATORY_COMMIT = "expectations/{item}-preparatory-commit.txt"
# Where an entry ran its checks: the checkout, or a worktree at the item base (re-entry).
PLACES = ("checkout", "base")

_ID = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{0,63}$")
# A test-spec result's cases (consumer contract 3.3, D4: no surface key; the oracle names it).
TEST_CASE_KEYS = ("id", "criterion", "requirement", "oracle", "red", "green")
_TEST_CASE_SHAPE = ('test_cases are [{"id": "TC-1", "criterion": "C1", "requirement": "R-3", "oracle": "<what observes '
                    'the behaviour>", "red": "<how it fails before the change>", "green": "<what passes after>"}]')
_SHAPE = ('expectations are [{"id": "E1", "state": "works" | "absent" | "broken", "statement": "<the fact>", '
          '"steps": ["S1"], "paths": ["<repository-relative path or glob>"], "check": "<one read-only shell command '
          'from the repository root that exits 0 when the state holds>", "from": "<open plan assumption id, '
          'optional>"}]')
_SKILL_SHAPE = ('a step\'s skills are [{"name": "<skill>", "why": "<the concrete use in this step>", "locator": '
                '"<absolute path, or repository-relative path, of its SKILL.md or card; optional>"}], or []')
# First words that write; a check is read-only.  The runtime git-status comparison is the backstop.
_WRITERS = frozenset(("rm", "rmdir", "mv", "cp", "touch", "mkdir", "tee", "chmod", "chown", "ln", "dd", "truncate",
                      "install", "sudo", "patch", "unlink", "shred"))
_PACKAGE_WRITES = {"npm": {"install", "i", "ci", "add", "uninstall", "update", "link", "publish"},
                   "yarn": {"add", "install", "remove", "upgrade"}, "pnpm": {"add", "install", "i", "remove", "update"},
                   "pip": {"install", "uninstall"}, "pip3": {"install", "uninstall"}}
_GIT_WRITES = frozenset(("add", "commit", "push", "pull", "fetch", "checkout", "switch", "restore", "reset", "stash",
                         "clean", "rm", "mv", "merge", "rebase", "apply", "am", "cherry-pick", "revert", "tag",
                         "branch", "worktree", "init", "clone", "gc", "update-index", "update-ref"))
_SEPARATORS = frozenset(("|", "||", "&&", ";", "&", "(", ")", "!"))


class ExpectationError(ValueError):
    """An expectation list, a skill list or a validate-existing result is refused."""


def _need(condition: Any, message: str) -> None:
    if not condition:
        raise ExpectationError(message)


def _text(value: Any, label: str) -> str:
    _need(isinstance(value, str) and value.strip() and "\0" not in value, label + " must be nonblank text")
    return value.strip()


# ------------------------------------------------------------------ shapes

def write_problem(command: str) -> Optional[str]:
    """Why ``command`` is not one read-only shell command, or ``None``.

    It must be one nonblank line, parse as shell words, redirect output only to /dev/null or another descriptor,
    and start no segment with a known writer (rm, mv, cp, tee, sed -i, git commit, npm install, ...).  This is a
    shape check; ``run`` also refuses a check that changed the checkout.
    """
    if not isinstance(command, str) or not command.strip() or "\n" in command or "\r" in command or "\0" in command:
        return "a check must be one nonblank line"
    try:
        lexer = shlex.shlex(command, posix=True, punctuation_chars=True)
        lexer.whitespace_split = True
        tokens = list(lexer)
    except ValueError as exc:
        return "a check must parse as one shell command (" + str(exc) + ")"
    segment_start = True
    for index, token in enumerate(tokens):
        following = tokens[index + 1] if index + 1 < len(tokens) else ""
        if ">" in token and set(token) <= set("<>&|"):
            # An output redirect: to another descriptor (>&2, 2>&1) or to /dev/null only.
            to_descriptor = token.endswith("&") and (following.isdigit() or following == "-")
            if not to_descriptor and following != "/dev/null":
                return ("a check is read-only: it may redirect output only to /dev/null or another descriptor "
                        "(found " + token + " " + following + ")")
        if token in _SEPARATORS:
            segment_start = True
            continue
        if segment_start:
            segment_start = False
            name = os.path.basename(token)
            if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*=.*", token):
                segment_start = True  # an environment assignment before the command word
                continue
            if name in _WRITERS:
                return "a check is read-only; " + name + " writes"
            if name in ("sed", "perl") and any(arg == "-i" or arg.startswith("-i") for arg in tokens[index + 1:]
                                               if arg not in _SEPARATORS):
                return "a check is read-only; " + name + " -i edits files in place"
            if name == "git" and _git_subcommand(tokens[index + 1:]) in _GIT_WRITES:
                return "a check is read-only; git " + _git_subcommand(tokens[index + 1:]) + " writes"
            if name in _PACKAGE_WRITES and following in _PACKAGE_WRITES[name]:
                return "a check is read-only; " + name + " " + following + " writes"
    return None


def _git_subcommand(args: Sequence[str]) -> str:
    skip = False
    for arg in args:
        if arg in _SEPARATORS:
            return ""
        if skip:
            skip = False
            continue
        if arg in ("-C", "-c", "--git-dir", "--work-tree"):
            skip = True
            continue
        if arg.startswith("-"):
            continue
        return arg
    return ""


def normalise_expectations(value: Any) -> List[Dict[str, Any]]:
    """The canonical ``expectations`` list of a step-plan result (shape only; ``check_step_plan`` checks coverage)."""
    _need(isinstance(value, list), "expectations must be a list; " + _SHAPE)
    rows: List[Dict[str, Any]] = []
    seen: Set[str] = set()
    for index, entry in enumerate(value):
        label = "expectations[" + str(index) + "]"
        _need(isinstance(entry, Mapping) and {"id", "state", "statement", "steps", "check"} <= set(entry) <= KEYS,
              label + " has id, state, statement, steps and check, and optionally paths and from; " + _SHAPE)
        ident = entry["id"]
        _need(isinstance(ident, str) and _ID.fullmatch(ident), label + ".id must be a short identifier such as E1")
        _need(ident not in seen, "expectation " + ident + " is listed twice")
        seen.add(ident)
        label = "expectation " + ident
        _need(entry["state"] in STATES, label + ".state must be one of " + ", ".join(STATES))
        steps = entry["steps"]
        _need(isinstance(steps, list) and steps and all(isinstance(step, str) and step.strip() for step in steps)
              and len(set(steps)) == len(steps), label + ".steps must name the step IDs that build on it")
        check = entry["check"]
        problem = write_problem(check)
        _need(problem is None, label + ": " + str(problem))
        row: Dict[str, Any] = {"id": ident, "state": entry["state"],
                               "statement": _text(entry["statement"], label + ".statement"),
                               "steps": [step.strip() for step in steps], "check": check.strip()}
        paths = entry.get("paths", [])
        _need(isinstance(paths, list), label + ".paths must be a list of repository-relative paths or globs")
        try:
            row["paths"] = item_scope.normalise_paths(paths) if paths else []
        except item_scope.ItemScopeError as exc:
            raise ExpectationError(label + ": " + str(exc)) from exc
        if "from" in entry:
            _need(isinstance(entry["from"], str) and _ID.fullmatch(entry["from"]),
                  label + ".from must be the id of an open plan assumption, such as A3")
            row["from"] = entry["from"]
        rows.append(row)
    return rows


def normalise_skills(value: Any, step: str = "") -> List[Dict[str, str]]:
    """The canonical ``skills`` list of one step (shape only; ``check_step_plan`` checks each locator exists)."""
    label = ("step " + step + " skills") if step else "skills"
    _need(isinstance(value, list), label + " must be a list; " + _SKILL_SHAPE)
    rows: List[Dict[str, str]] = []
    for entry in value:
        _need(isinstance(entry, Mapping) and {"name", "why"} <= set(entry) <= SKILL_KEYS, label + ": " + _SKILL_SHAPE)
        name = _text(entry["name"], label + " name")
        _need("\n" not in name, label + " name must be one line")
        row = {"name": name, "why": _text(entry["why"], label + " " + name + " why")}
        if "locator" in entry:
            locator = _text(entry["locator"], label + " " + name + " locator")
            _need("\n" not in locator, label + " " + name + " locator must be one path")
            row["locator"] = locator
        rows.append(row)
    names = [row["name"] for row in rows]
    _need(len(set(names)) == len(names), label + " must not repeat a skill")
    return rows


def normalise_failed_expectations(value: Any) -> List[Dict[str, str]]:
    """The canonical ``failed_expectations`` of a validate-existing revise result."""
    _need(isinstance(value, list) and value,
          'a validate-existing revise result lists failed_expectations: [{"id": "E1", "actual": "<what is true>", '
          '"route": "check" (the check is wrong; actual gives the corrected check) | "steps" (the fact is false; '
          'step-plan reshapes the steps)}]')
    rows: List[Dict[str, str]] = []
    for entry in value:
        _need(isinstance(entry, Mapping) and set(entry) == FAILED_KEYS,
              "each failed expectation is {id, actual, route}")
        _need(entry["route"] in ROUTES, "a failed expectation's route is " + " or ".join(ROUTES))
        rows.append({"id": _text(entry["id"], "a failed expectation's id"),
                     "actual": _text(entry["actual"], "failed expectation " + str(entry["id"]) + " actual"),
                     "route": entry["route"]})
    return rows


# ------------------------------------------------------------------ state readers

def _cursor(state: Mapping[str, Any]) -> Tuple[Optional[str], Optional[str]]:
    """(current work item, its current inner action id), or Nones outside an inner loop."""
    items = state.get("work_items") or ()
    index = state.get("work_index")
    if not isinstance(index, int) or not 0 <= index < len(items):
        return None, None
    item = items[index].get("id")
    loop = (state.get("inner_loops") or {}).get(item) or {}
    action = loop.get("action")
    return item, (action.get("id") if isinstance(action, Mapping) else action)


def open_assumptions(state: Mapping[str, Any], work_item: str) -> List[Mapping[str, Any]]:
    """The plan's open assumptions whose consumer is ``work_item``."""
    plan = test_loop._latest_root_result(state, "plan")
    return [row for row in plan.get("assumptions") or () if isinstance(row, Mapping)
            and row.get("disposition") == "open" and row.get("consumer") == work_item]


def _base_files(repo: Path, base: Optional[Mapping[str, Any]]) -> Optional[List[str]]:
    """Repository-relative files of the item's base tree, or ``None`` when it cannot be listed."""
    if not base or not base.get("tree") or not base.get("toplevel"):
        return None
    listed = lint._git(Path(base["toplevel"]), "ls-tree", "-r", "-z", "--name-only", base["tree"])
    if listed.returncode:
        return None
    prefix = str(base.get("prefix") or ".")
    lead = "" if prefix in (".", "") else prefix.rstrip("/") + "/"
    paths = [raw.decode("utf-8", "surrogateescape") for raw in listed.stdout.split(b"\0") if raw]
    return [path[len(lead):] for path in paths if path.startswith(lead)]


def _covers(rule: str, path: str) -> bool:
    return (path == rule or fnmatch.fnmatchcase(path, rule) or item_scope._matches(path, rule)
            or path.startswith(rule.rstrip("/") + "/"))


def _exists(repo: Path, files: Optional[Sequence[str]], rule: str) -> bool:
    """Whether a path or glob names something on the base (the base tree, or the working tree when unlisted)."""
    if files is None:
        return (repo / rule).exists() or any(repo.glob(rule)) if rule else False
    return any(_covers(rule, path) for path in files)


def _locator_exists(repo: Path, locator: str) -> bool:
    path = Path(os.path.expanduser(locator))
    return (path if path.is_absolute() else repo / path).exists()


# ------------------------------------------------------------------ gates

def check_step_plan(root: Path, state: Mapping[str, Any], result: Mapping[str, Any]) -> None:
    """Refuse a done step-plan result whose expectations, check suite or step skills are incomplete.

    ``root`` is the run directory and ``state`` the run state with this item current (its lint base is recorded at
    step-plan entry).  Refused: a missing or malformed ``expectations``; a check that is not one read-only shell
    command; an expectation naming an unknown step; an existing step path with no works or broken expectation, or a
    new one with no absent expectation; a works or broken path missing on the base, or an absent path present there;
    an open plan assumption whose consumer is this item and that no expectation cites in ``from`` (or a ``from``
    naming none of them); a non-empty ``test_commands`` without a check row or ``check_na`` (or both); a step
    without ``skills``; and a skill locator that does not exist.  Raises ExpectationError.
    """
    if not isinstance(result, Mapping) or result.get("outcome") != "done":
        return
    repo = Path(str(state["repo"]))
    work_item, _action = _cursor(state)
    _check_check_suite(result)
    steps = [step for step in result.get("steps") or () if isinstance(step, Mapping)]
    step_ids = {str(step.get("id")) for step in steps}
    for step in steps:
        _need("skills" in step, "step " + str(step.get("id")) + " must list skills (" + _SKILL_SHAPE + "): reread "
              "the host's skills and the repository's skill directory, and name one only for a concrete use")
        for skill in normalise_skills(step["skills"], str(step.get("id"))):
            _need("locator" not in skill or _locator_exists(repo, skill["locator"]),
                  "step " + str(step.get("id")) + " skill " + skill["name"] + ": locator " + skill.get("locator", "")
                  + " does not exist. Give the absolute path of its SKILL.md or card, or drop the locator.")
    _need("expectations" in result,
          "a done step-plan result must list expectations: the facts its steps build on, each with a check "
          "ShipLoop runs at validate-existing before anything changes; " + _SHAPE)
    rows = normalise_expectations(result["expectations"])
    for row in rows:
        unknown = [step for step in row["steps"] if step not in step_ids]
        _need(not unknown, "expectation " + row["id"] + " names steps the result does not list: " + ", ".join(unknown))
    base = lint.read_base(Path(root), work_item) if work_item else None
    files = _base_files(repo, base)
    where = "the item's lint base" if files is not None else "the checkout"
    for row in rows:
        for rule in row["paths"]:
            present = _exists(repo, files, rule)
            if row["state"] == "absent":
                _need(not present, "expectation " + row["id"] + " is absent, but " + rule + " exists on " + where
                      + ". An existing path needs a works or broken expectation.")
            else:
                _need(present, "expectation " + row["id"] + " is " + row["state"] + ", but " + rule
                      + " does not exist on " + where + ". A new path needs an absent expectation.")
    missing: List[str] = []
    for step in steps:
        for path in step.get("paths") or ():
            states = EXISTING_STATES if _exists(repo, files, path) else NEW_STATES
            if not any(row["state"] in states and any(_covers(rule, path) or rule == path for rule in row["paths"])
                       for row in rows):
                missing.append(path + " (step " + str(step.get("id")) + ", needs " + " or ".join(states) + ")")
    _need(not missing, "these step paths have no expectation listing them in paths: " + "; ".join(missing)
          + ". Every path a step changes that exists on " + where + " needs a works or broken expectation, and every "
          "new path an absent one.")
    if work_item:
        opened = {str(row.get("id")) for row in open_assumptions(state, work_item)}
        cited = {row["from"] for row in rows if "from" in row}
        stray = sorted(cited - opened)
        _need(not stray, "expectations cite from " + ", ".join(stray) + ", which is not an open plan assumption "
              "whose consumer is " + work_item + (" (those are " + ", ".join(sorted(opened)) + ")" if opened else ""))
        uncited = sorted(opened - cited)
        _need(not uncited, "open plan assumptions " + ", ".join(uncited) + " name " + work_item + " as consumer; "
              "add an expectation for each with \"from\": \"<assumption id>\" and a check that settles it")


def _check_check_suite(result: Mapping[str, Any]) -> None:
    """A non-empty test_commands carries a check row (lint, type or build), or check_na says why there is none."""
    commands = result.get("test_commands")
    has_check = isinstance(commands, list) and any(isinstance(row, Mapping) and row.get("suite") == "check"
                                                   for row in commands)
    reason = result.get("check_na")
    if "check_na" in result:
        _need(isinstance(reason, str) and reason.strip(), "check_na must be nonblank text: why these files have no "
              "lint, type or build command")
    if not commands:
        _need("check_na" not in result, "check_na applies only beside test commands; with none, test_commands_na "
              "gives the reason")
        return
    _need(has_check or "check_na" in result,
          "test_commands has no check row: add each lint, type and build command environment.md records for these "
          "files ({\"command\": \"...\", \"suite\": \"check\"}, judged by exit code), or give check_na with the reason "
          "there is none")
    _need(not (has_check and "check_na" in result), "test_commands has a check row, so drop check_na")


def normalise_test_cases(value: Any) -> List[Dict[str, str]]:
    """A done test-spec result's ``test_cases``: shape only (the gate, ``check_test_cases``, checks meaning).

    Each case has exactly ``TEST_CASE_KEYS``, every value non-blank text; ``id`` and ``criterion`` hold no whitespace;
    ids are unique; ``requirement`` names at least one R-<n>.  Raises ExpectationError, whose message ends with the
    route-free next step (a shape refusal cannot know whether complete or improve-complete submitted it).
    """
    import shiploop_knowledge_home as knowledge
    tail = "; then run the same command again."
    _need(isinstance(value, list), "test_cases must be a list (empty only when the item's focused commands list no "
          "IDs); " + _TEST_CASE_SHAPE + tail)
    rows: List[Dict[str, str]] = []
    for index, entry in enumerate(value):
        label = "test_cases[" + str(index) + "]"
        _need(isinstance(entry, Mapping) and set(entry) == set(TEST_CASE_KEYS),
              label + " needs exactly " + ", ".join(TEST_CASE_KEYS) + "; " + _TEST_CASE_SHAPE + tail)
        row = {}
        for key in TEST_CASE_KEYS:
            _need(isinstance(entry[key], str) and entry[key].strip() and "\0" not in entry[key],
                  label + "." + key + " must be nonblank text" + tail)
            row[key] = entry[key].strip()
        for key in ("id", "criterion"):
            _need(not any(ch.isspace() for ch in row[key]), label + "." + key + " has no spaces" + tail)
        _need(knowledge._ids(row["requirement"]), label + ".requirement names no R-<n>: name the requirement it "
              "proves, such as R-3" + tail)
        rows.append(row)
    ids = [row["id"] for row in rows]
    _need(len(set(ids)) == len(ids), "test_cases ids must be unique" + tail)
    return rows


def check_test_cases(root: Path, state: Mapping[str, Any],
                     result: Mapping[str, Any]) -> Optional[Tuple[str, str, List[str]]]:
    """Why a done test-spec result's cases do not fit this item's step plan, or None (contract 3.3; replaces the
    feature test-spec.md check).

    ``result`` is canonical.  The case IDs must equal the current item's focused command IDs in both directions (an
    earlier item's IDs no longer count); each case's criterion is a criterion of that step plan; each requirement it
    names has an entry in the living spec.  A missing key or [] is accepted when the item has no focused IDs.  Returns
    ``(fix, seed, lines)`` for the navigator's hand-off refusal: ``fix`` holds ``{result}`` where the result file goes,
    ``seed`` is the same fix for a final result still to be written, ``lines`` follow line 1.
    """
    import shiploop_knowledge_home as knowledge
    work_item, _action = _cursor(state)
    _plan_action, plan = test_loop._step_plan(state, str(work_item)) if work_item else (None, {})
    focused: List[str] = []
    for row in plan.get("test_commands") or ():
        if isinstance(row, Mapping) and row.get("suite") == "focused":
            focused += [ident for ident in row.get("ids") or () if ident not in focused]
    cases = list(result.get("test_cases") or ())
    shape = ('Shape: {"id", "criterion", "requirement", "oracle", "red", "green"}, one per ID this item\'s focused '
             'commands list. The implement, test, verify and system-test-author packets quote them.')
    if not cases:
        if not focused:
            return None
        return ("Add test_cases to {result}", "adds test_cases", [shape, "Focused IDs: " + ", ".join(focused) + "."])
    unlisted = [case["id"] for case in cases if case["id"] not in focused]
    if unlisted:
        return ("Fix the case IDs in {result}", "fixes the case IDs",
                ["Give every case an ID this item's focused commands list, or report revise so the step plan lists it.",
                 "Not listed by a focused command of " + str(work_item) + ": " + ", ".join(unlisted) + "."])
    have = {case["id"] for case in cases}
    missing = [ident for ident in focused if ident not in have]
    if missing:
        return ("Add the missing cases to {result}", "adds the cases",
                ["Add a case to test_cases for every ID this item's focused commands list. " + shape,
                 "Focused IDs with no case: " + ", ".join(missing) + "."])
    criteria = [str(row.get("id")) for row in plan.get("criteria") or () if isinstance(row, Mapping)]
    wrong = [case["id"] + " names " + case["criterion"] for case in cases if case["criterion"] not in criteria]
    if wrong:
        return ("Fix the case criteria in {result}", "fixes the criteria",
                ["Set each case's criterion to a criterion of this item's step plan.",
                 "; ".join(wrong) + "; the criteria are " + (", ".join(criteria) or "none") + "."])
    spec = Path(str(state["repo"])) / knowledge.HOME / "spec.md"
    entries = knowledge.entries(Path(str(state["repo"])), "spec.md")
    unknown = []
    for case in cases:
        absent = [ident for ident in knowledge._ids(case["requirement"]) if ident not in entries]
        if absent:
            unknown.append(case["id"] + " names " + ", ".join(absent))
    if unknown:
        return ("Fix case requirements in {result}", "fixes requirements",
                ["Set each case's requirement to R-<n> that have an entry in the living spec, " + str(spec)
                 + " (a line that starts with the ID).", "; ".join(unknown) + "."])
    return None


# ------------------------------------------------------------------ running checks

def _shell() -> List[str]:
    found = shutil.which("bash")
    return [found, "-c"] if found else ["/bin/sh", "-c"]


def _status(repo: Path) -> Optional[bytes]:
    top = lint.git_toplevel(repo)
    if top is None:
        return None
    result = lint._git(top, "status", "--porcelain=v1", "-z", "--untracked-files=all", "--", os.fspath(repo))
    return result.stdout if result.returncode == 0 else None


def _status_paths(raw: Optional[bytes]) -> Set[str]:
    return {entry.decode("utf-8", "surrogateescape")[3:] for entry in (raw or b"").split(b"\0") if len(entry) > 3}


def _summary(text: str, code: Optional[int]) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    tail = lines[-1][:200] if lines else "(no output)"
    return ("exit " + str(code) if code is not None else "no exit") + ": " + tail


def run(repo: Path, expectations: Sequence[Mapping[str, Any]], run_dir: Path, action_id: str,
        timeout: float = CHECK_TIMEOUT_SECONDS, *, tag: str = "entry") -> List[Dict[str, Any]]:
    """Run each expectation's check from ``repo`` and say whether it matches its state.

    Returns one row per expectation, in order: ``{id, state, statement, steps, paths, check, exit, summary, output,
    matches}``.  ``exit`` is the exit code (``None`` when it timed out or could not start); ``output`` is the
    run-relative path of its saved stdout and stderr (``expectations/<action>-<tag>-<id>.txt``).  A check matches
    when it exits 0 and leaves ``git status`` unchanged.  Writes only the output files.
    """
    _need(isinstance(action_id, str) and action_id, "run needs the action id")
    _need(timeout > 0, "the check timeout must be positive")
    repo = Path(repo)
    folder = Path(run_dir) / "expectations"
    folder.mkdir(parents=True, exist_ok=True)
    rows: List[Dict[str, Any]] = []
    for expectation in expectations:
        before = _status(repo)
        code: Optional[int] = None
        note = ""
        try:
            process = subprocess.Popen(_shell() + [expectation["check"]], cwd=os.fspath(repo),
                                       stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                       start_new_session=True)
            try:
                raw, _ = process.communicate(timeout=timeout)
                code = process.returncode
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except OSError:
                    process.kill()
                raw, _ = process.communicate()
                note = "the check did not finish within %.0f seconds" % timeout
        except OSError as exc:
            raw, note = b"", "the check could not start: " + str(exc)
        text = raw[:OUTPUT_LIMIT].decode("utf-8", "replace")
        changed = sorted(_status_paths(_status(repo)) ^ _status_paths(before)) if before is not None else []
        if changed:
            note = "the check changed the checkout (" + ", ".join(changed[:5]) + "); a check must be read-only"
        relative = "expectations/" + action_id + "-" + tag + "-" + str(expectation["id"]) + ".txt"
        (Path(run_dir) / relative).write_text("$ " + expectation["check"] + "\n" + text
                                              + ("\n[" + note + "]\n" if note else ""), encoding="utf-8")
        rows.append({"id": expectation["id"], "state": expectation["state"], "statement": expectation["statement"],
                     "steps": list(expectation.get("steps") or ()), "paths": list(expectation.get("paths") or ()),
                     "check": expectation["check"], "exit": code,
                     "summary": note or _summary(text, code), "output": relative,
                     "matches": code == 0 and not changed})
    return rows


def record_path(action_id: str) -> str:
    """The run-relative record of the checks run at validate-existing entry."""
    return "expectations/" + action_id + ".md"


def _plan_expectations(state: Mapping[str, Any], work_item: str) -> List[Dict[str, Any]]:
    _action, plan = test_loop._step_plan(state, work_item)
    return normalise_expectations(plan.get("expectations") or [])


def _snapshot(root: Path, repo: Path) -> Optional[Dict[str, str]]:
    """A tree of the checkout's working content now (the base for preparatory changes), or ``None``."""
    top = lint.git_toplevel(repo)
    if top is None:
        return None
    prefix = lint.scope_prefix(top, repo)
    index = Path(root) / "lint" / "tmp" / ("expect-" + uuid.uuid4().hex + ".index")
    try:
        tree = lint.snapshot_tree(top, Path(root), index, prefix=prefix)
    except lint.LintError:
        return None
    finally:
        if index.exists():
            index.unlink()
    return {"toplevel": os.fspath(top), "prefix": prefix, "tree": tree}


def preparatory_commit(root: Path, work_item: str) -> Optional[str]:
    """The preparatory-fix commit ShipLoop made for ``work_item`` at validate-existing, or None."""
    path = Path(root) / PREPARATORY_COMMIT.format(item=work_item)
    return (path.read_text(encoding="utf-8").strip() or None) if path.is_file() else None


def _item_rules(state: Mapping[str, Any], work_item: str) -> List[str]:
    """The item's paths: its accepted step plan's paths, each step's paths and each expectation's paths."""
    _action, plan = test_loop._step_plan(state, work_item)
    rules = [str(rule) for rule in plan.get("paths") or ()]
    for step in plan.get("steps") or ():
        if isinstance(step, Mapping):
            rules += [str(rule) for rule in step.get("paths") or ()]
    for row in plan.get("expectations") or ():
        if isinstance(row, Mapping):
            rules += [str(rule) for rule in row.get("paths") or ()]
    return list(dict.fromkeys(rules))


def _implemented(state: Mapping[str, Any], work_item: str) -> bool:
    return any(row.get("stage") == "implement" and row.get("workitem") == work_item
               for row in state.get("history", ()))


def check_place(root: Path, state: Mapping[str, Any], work_item: str) -> str:
    """Where validate-existing runs the item's checks now: ``checkout`` or ``base`` (see the module docstring).

    ``base`` only when the item already ran implement, its lint base is recorded, and the checkout holds changes to
    the item's paths since that base; anything unreadable keeps the checkout.
    """
    if not _implemented(state, work_item):
        return "checkout"
    base = lint.read_base(Path(root), work_item)
    changed = item_scope.changed_since(Path(root), base) if base else None
    rules = _item_rules(state, work_item)
    if not changed or not rules:
        return "checkout"
    own = [path for path in changed if not _knowledge(path) and any(_covers(rule, path) for rule in rules)]
    return "base" if own else "checkout"


def _run_at(root: Path, state: Mapping[str, Any], work_item: str, place: str, rows: Sequence[Mapping[str, Any]],
            action_id: str, tag: str) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """Run the checks in ``place``; return (rows, the base commit for ``base``).  Raises ExpectationError when the
    base worktree cannot be made."""
    repo = Path(str(state["repo"]))
    if place != "base":
        return run(repo, rows, Path(root), action_id, tag=tag), None
    base = lint.read_base(Path(root), work_item)
    _need(base is not None, "the item's lint base is not recorded, so its checks cannot run at the base")
    commit = preparatory_commit(Path(root), work_item)
    try:
        with test_loop.base_worktree(Path(root), base, commit=commit) as cwd:
            return run(Path(cwd), rows, Path(root), action_id, tag=tag), commit or str(base.get("tree"))
    except (test_loop.TestLoopError, lint.LintError, OSError) as exc:
        raise ExpectationError("ShipLoop cannot make a worktree at the item's base to run the expectation checks: "
                               + str(exc)) from exc


def entry(root: Path, state: Mapping[str, Any]) -> Tuple[Dict[str, str], bool]:
    """Run the item's expectation checks at validate-existing entry.

    Returns (record writes, whether every expectation matches).  The record (``record_path``) holds each result,
    where the checks ran (``place``: ``check_place``) and a snapshot of the checkout before any change, the base
    ``check_complete`` measures preparatory changes from.  When all match the navigator records validate-existing
    done by script and issues no packet.
    """
    work_item, action_id = _cursor(state)
    _need(work_item and action_id, "expectation checks run only inside a work item's inner loop")
    repo = Path(str(state["repo"]))
    place = check_place(Path(root), state, str(work_item))
    rows, at = _run_at(Path(root), state, str(work_item), place, _plan_expectations(state, work_item),
                       str(action_id), "entry")
    record = {"schema": SCHEMA, "work_item": work_item, "action": action_id, "place": place,
              "checkout": _snapshot(root, repo), "results": rows}
    if at:
        record["base"] = at
    return {record_path(str(action_id)): store.dumps(record, "ShipLoop expectation checks")}, all(
        row["matches"] for row in rows)


def read_record(root: Path, action_id: str) -> Optional[Dict[str, Any]]:
    path = Path(root) / record_path(action_id)
    if not path.is_file():
        return None
    record = store.read_record(path)
    return dict(record) if isinstance(record, Mapping) and record.get("schema") == SCHEMA else None


def result_lines(root: Path, state: Mapping[str, Any]) -> List[str]:
    """Packet lines: each expectation's entry result, mismatches first, with its saved output."""
    _item, action_id = _cursor(state)
    record = read_record(Path(root), str(action_id)) if action_id else None
    if not record:
        return []
    if record.get("place") == "base":
        lines = ["ShipLoop ran each expectation's check in a temporary worktree at the item's base ("
                 + str(record.get("base") or "")[:12] + "), not in " + str(state["repo"]) + ", which already holds "
                 "this item's changes; an edit in the checkout cannot change these results (each exits 0 when its "
                 "state holds):"]
    else:
        lines = ["ShipLoop ran each expectation's check from " + str(state["repo"]) + " before any change "
                 "(each exits 0 when its state holds):"]
    for row in sorted(record["results"], key=lambda row: row["matches"]):
        lines.append("  " + row["id"] + " " + row["state"] + "  " + row["statement"] + " ("
                     + ", ".join(row["steps"]) + ")  check: " + row["check"] + "  -> "
                     + ("MATCHES" if row["matches"] else "DOES NOT MATCH, " + row["summary"])
                     + "  output: " + str(Path(root) / row["output"]))
    return lines


def _knowledge(path: str) -> bool:
    return path.startswith(KNOWLEDGE_PREFIX)


def check_preparatory_changes(repo: Path, base: Optional[Mapping[str, Any]],
                              expectations: Sequence[Mapping[str, Any]], results: Sequence[Mapping[str, Any]],
                              *, run_dir: Path) -> List[str]:
    """The preparatory paths to commit, after refusing any change outside the mismatched works expectations.

    ``base`` is the checkout snapshot recorded at entry (``toplevel``, ``prefix``, ``tree``); ``results`` are the
    entry rows.  The allowed paths are those of the works expectations whose entry check did not match.  Changes
    under ShipLoop's knowledge home (an environment fix recorded in environment.md) are neither refused nor
    returned.  Raises ExpectationError naming the stray paths, or when changes cannot be read.
    """
    _need(base is None or Path(os.path.realpath(os.fspath(repo))).is_relative_to(
        os.path.realpath(str(base.get("toplevel")))), "the preparatory base is not a snapshot of this checkout")
    mismatched = {row["id"] for row in results if not row.get("matches")}
    allowed = [rule for row in expectations if row["state"] == "works" and row["id"] in mismatched
               for rule in row.get("paths") or ()]
    changed = item_scope.changed_since(Path(run_dir), base)
    if changed is None:
        _need(not allowed, "ShipLoop cannot read this checkout's changes since validate-existing began, so it cannot "
              "commit a preparatory fix. Report blocked naming the fix.")
        return []
    changed = [path for path in changed if not _knowledge(path)]
    stray = [path for path in changed if not any(_covers(rule, path) for rule in allowed)]
    _need(not stray, "validate-existing changed paths outside the paths of the works expectations that did not match "
          "(" + (", ".join(allowed) or "none") + "): " + ", ".join(stray) + ". " + DONE_WHEN_PREPARATORY[0].upper()
          + DONE_WHEN_PREPARATORY[1:] + ". Undo these changes; the item's own change belongs to implement, and a "
          "needed repair elsewhere is a revise (route steps) so step-plan adds it as an earlier step.")
    return sorted(changed)


def check_complete(root: Path, state: Mapping[str, Any], result: Mapping[str, Any], *,
                   tag: str = "complete") -> List[str]:
    """Gate validate-existing's result; return the preparatory paths the navigator commits on accept.

    done: reruns every check where the entry ran them (the record's ``place``) and refuses a mismatch, then
    ``check_preparatory_changes`` against the entry snapshot; at the base (re-entry) any change since entry is
    refused and nothing is returned.  revise: requires ``failed_expectations`` naming known expectations.  blocked:
    nothing.  ``tag`` names the saved outputs (``check-only`` for ``complete --check-only``, which commits nothing).
    Raises ExpectationError.
    """
    _need(isinstance(result, Mapping), "the result must be an object")
    work_item, action_id = _cursor(state)
    _need(work_item and action_id, "validate-existing runs only inside a work item's inner loop")
    rows = _plan_expectations(state, work_item)
    known = {row["id"] for row in rows}
    outcome = result.get("outcome")
    if outcome == "revise":
        failed = normalise_failed_expectations(result.get("failed_expectations"))
        unknown = [row["id"] for row in failed if row["id"] not in known]
        _need(not unknown, "failed_expectations name expectations the step plan does not list: " + ", ".join(unknown))
        return []
    _need("failed_expectations" not in result, "failed_expectations belong only on a revise result")
    if outcome != "done":
        return []
    repo = Path(str(state["repo"]))
    record = read_record(Path(root), str(action_id)) or {}
    place = record.get("place") if record.get("place") in PLACES else "checkout"
    rerun, _at = _run_at(Path(root), state, str(work_item), place, rows, str(action_id), tag)
    wrong = [row for row in rerun if not row["matches"]]
    _need(not wrong, "\n".join(
        ["ShipLoop reran every expectation check; these do not match their state:"]
        + ["- " + row["id"] + " " + row["state"] + ": " + row["check"] + " -> " + row["summary"] + " (output: "
           + str(Path(root) / row["output"]) + ")" for row in wrong]
        + ["Keep working until each matches, or report revise with failed_expectations [{id, actual, route}] "
           "(route check: the check is wrong; route steps: the fact is false), or blocked when the fix lies outside "
           "this run."]))
    if place == "base":
        changed = item_scope.changed_since(Path(root), record.get("checkout"))
        stray = [path for path in changed or () if not _knowledge(path)]
        _need(not stray, "validate-existing ran its checks at the item's base, because the checkout already holds "
              "this item's changes, so no preparatory change is accepted here; these paths changed since it began: "
              + ", ".join(stray) + ". Undo them; a needed repair is a revise (route steps) so step-plan adds it "
              "as an earlier step.")
        return []
    return check_preparatory_changes(repo, record.get("checkout"), rows, record.get("results") or [],
                                     run_dir=Path(root))


__all__ = ("CHECK_TIMEOUT_SECONDS", "DONE_WHEN_PREPARATORY", "EXISTING_STATES", "NEW_STATES", "PLACES",
           "PREPARATORY_COMMIT", "ROUTES", "STAGE", "STATES", "ExpectationError", "check_complete",
           "check_place", "check_preparatory_changes", "check_step_plan", "check_test_cases", "entry", "normalise_expectations", "normalise_failed_expectations", "normalise_test_cases",
           "normalise_skills", "open_assumptions", "preparatory_commit", "read_record", "record_path", "result_lines", "run",
           "write_problem")
