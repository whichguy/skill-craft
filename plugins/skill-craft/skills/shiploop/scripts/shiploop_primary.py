"""The request's primary requirements, and the lower-layer check of an outcome no executed check observed (run-5
batch F6).

A live run (2026-10-24) let product-acceptance accept the request's main outcome for a person on source words and
deferred assumptions: nothing executed showed it.  The owner's answer is structure, not prose:

- the spec stage's result lists, in ``primary``, the requirements (R-<n>) that carry the request's primary outcomes:
  what the user asked for directly.  A script cannot infer primacy, so the model records it once, where it writes the
  requirements, and the gate checks that each ID has a current entry in the living spec;
- every ``unverified`` row of product-acceptance names its ``requirement`` and its ``lower_layer_check``: the executed
  check below the e2e layer that shows the outcome's logic works;
- a row whose requirement is primary is accepted only when its ``lower_layer_check`` is the ID of a test that ShipLoop
  ran and saw pass, in a test case for that requirement.  A row whose requirement is not primary may give the reason
  no such check exists instead;
- the refusal's exit is add-work, with a corrective work item that adds the missing lower-layer test.

TS1 (2026-10-26, docs/shiploop-judgement-stage-checks-proposal-2026-10-26.md section 0) checks the trace where it is
made.  At the last work item's done test-spec, every primary requirement has a test case naming it in some item's current
test-spec, or a ``suite_requirements`` row: a requirement that a recorded command's own run observes rather than one
case (a test suite, "the tests run with node --test"; a deploy; a check), naming one of the run's recorded test commands.
A run whose step plans record no test command (documentation only) is not checked: it has no executed test to trace.  A
replay of the eight saved runs since ``primary`` exists found three such requirements and one primary requirement no
case named.  The owner widened the wording from "about the tests themselves" on 2026-10-27: a run's recorded deploy
or check can observe a structural requirement no single case does.

Where "ran and saw pass" comes from: ShipLoop's own test records, ``tests/<action>-verify<N>.md``, of the accepted
inner actions (the test stage's candidate run and verify's rerun).  A record that passed, a run in it whose status is
``passed``, and the IDs that run lists.  Which requirement a test serves comes from the current test-spec results'
``test_cases``.  The outer stages' records (system-test, release-verify) do not count: they observe at the e2e layer.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

import shiploop_knowledge_home as knowledge
import shiploop_planning_revision as planning_revision
import shiploop_stage_spec as stage_spec
import shiploop_store as store
import shiploop_test_loop as test_loop

STAGE = "spec"
FIELD = "primary"
ACCEPTANCE = "product-acceptance"
TEST_SPEC = "test-spec"
SUITE_FIELD = "suite_requirements"
# The template's one entry, which states the bar; a text wrapped in angle brackets is a placeholder.
PLACEHOLDER = "<R-<n> that carries an outcome the user asked for directly>"
_REQUIREMENT = re.compile(r"^R-\d+$")
# How many passed test IDs the product-acceptance packet names per primary requirement (a hint: the gate takes any).
PRINTED_IDS = 8


class PrimaryError(ValueError):
    """A primary list or an unverified row that breaks its rule; the message names the field and the fix."""


def _need(condition: bool, message: str) -> None:
    if not condition:
        raise PrimaryError(message)


def canonical(value: Any) -> List[str]:
    """The stored ``primary``: a list of nonblank texts (shape only, so a saved result always loads)."""
    _need(isinstance(value, list) and all(isinstance(ident, str) and ident.strip() for ident in value),
          'primary is a list of the R-<n> that carry the request\'s primary outcomes, such as ["R-1"]')
    return [ident.strip() for ident in value]


def canonical_suite(value: Any) -> List[Dict[str, str]]:
    """The stored ``suite_requirements``: rows ``{"requirement": "R-<n>", "command": "<a recorded test command>"}``, each
    requirement once (shape only; ``check_test_spec`` checks the requirement and the command against the run)."""
    shape = ('suite_requirements is a list of {"requirement": "R-<n>", "command": "<one of the run\'s recorded test '
             'commands>"}: a requirement that command\'s own recorded run observes (a test suite, a deploy or a check)')
    _need(isinstance(value, list), shape)
    rows: List[Dict[str, str]] = []
    for row in value:
        _need(isinstance(row, Mapping) and set(row) == {"requirement", "command"}
              and all(isinstance(row[key], str) and row[key].strip() for key in row), shape)
        rows.append({"requirement": row["requirement"].strip(), "command": row["command"].strip()})
    bad = [row["requirement"] for row in rows if not _REQUIREMENT.fullmatch(row["requirement"])]
    _need(not bad, "suite_requirements names " + ", ".join(bad) + ": one requirement ID per row, R-<n>")
    named = [row["requirement"] for row in rows]
    _need(len(set(named)) == len(named), "suite_requirements lists a requirement twice: one row per R-<n>")
    return rows


def _spec_path(repo: Path) -> Path:
    return Path(repo) / knowledge.HOME / "spec.md"


def check_spec(repo: Path, stage: str, result: Any) -> None:
    """A done spec result lists ``primary``: at least one R-<n>, each once, each with a current entry in the spec."""
    if stage != STAGE or not isinstance(result, Mapping) or result.get("outcome") != "done":
        return
    spec = _spec_path(repo)
    _need(FIELD in result, 'a done spec result lists primary: the R-<n> that carry the request\'s primary outcomes, '
          'what the user asked for directly, such as ["R-1"]; product-acceptance accepts an unverified one only with '
          "a lower-layer test that passed")
    ids = canonical(result[FIELD])
    _need(bool(ids), "primary lists at least one R-<n>: every request asks for something directly")
    placeholders = [ident for ident in ids if ident.startswith("<") and ident.endswith(">")]
    _need(not placeholders, "primary still holds the template placeholder: write the R-<n> of each primary outcome")
    malformed = [ident for ident in ids if not _REQUIREMENT.fullmatch(ident)]
    _need(not malformed, "primary names " + ", ".join(malformed) + ": list requirement IDs only, R-<n>")
    _need(len(set(ids)) == len(ids), "primary lists an ID twice: list each R-<n> once")
    held = knowledge.entries(Path(repo), "spec.md")
    missing = [ident for ident in ids if ident not in held or held[ident].retired]
    _need(not missing, "primary names " + ", ".join(missing) + ", with no current entry in " + str(spec) + ": write "
          "each as R-<n> under ## Requirements, or drop it from primary")


def primary_ids(state: Mapping[str, Any]) -> Optional[List[str]]:
    """The current spec result's ``primary``; None when the spec result records none."""
    action = planning_revision.current_actions(state).get((None, STAGE))
    result = (state.get("accepted") or {}).get(action) if action else None
    value = result.get(FIELD) if isinstance(result, Mapping) else None
    return [str(ident) for ident in value] if isinstance(value, list) else None


def _passed_ids(root: Path, state: Mapping[str, Any]) -> set:
    """Every test ID a passed run in ShipLoop's own test records of an accepted inner action shows passing."""
    found: set = set()
    actions = dict.fromkeys(str(row.get("action")) for row in state.get("history") or ()
                            if isinstance(row, Mapping) and row.get("outcome") == "done" and row.get("workitem"))
    for action in actions:
        number = 1
        while (Path(root) / test_loop.verify_path(action, number)).is_file():
            try:
                record = store.read_record(Path(root) / test_loop.verify_path(action, number))
            except (OSError, store.StorageError):
                record = None
            number += 1
            if not isinstance(record, Mapping) or not record.get("passed"):
                continue
            for run in record.get("runs") or ():
                if isinstance(run, Mapping) and run.get("status") == "passed":
                    missing = {str(ident) for ident in run.get("ids_missing") or ()}
                    found |= {str(ident) for ident in run.get("ids") or () if str(ident) not in missing}
    return found


def passed_cases(root: Path, state: Mapping[str, Any]) -> Dict[str, List[str]]:
    """Per requirement, the test IDs of its current test cases that ShipLoop's test runs saw pass, in case order."""
    passed = _passed_ids(root, state)
    current = planning_revision.current_actions(state)
    accepted = state.get("accepted") or {}
    found: Dict[str, List[str]] = {}
    for item in state.get("work_items") or ():
        action = current.get((str(item.get("id")), "test-spec")) if isinstance(item, Mapping) else None
        result = accepted.get(action) if action else None
        for case in (result.get("test_cases") or ()) if isinstance(result, Mapping) else ():
            ident = str(case.get("id")) if isinstance(case, Mapping) else ""
            if ident not in passed:
                continue
            for requirement in knowledge.requirement_ids(str(case.get("requirement") or "")):
                names = found.setdefault(requirement, [])
                if ident not in names:
                    names.append(ident)
    return found


def _current_item(state: Mapping[str, Any]) -> Optional[str]:
    items, index = state.get("work_items") or [], state.get("work_index")
    return str(items[index].get("id")) if isinstance(index, int) and 0 <= index < len(items) else None


def _is_last_item(state: Mapping[str, Any]) -> bool:
    index = state.get("work_index")
    return isinstance(index, int) and index + 1 >= len(state.get("work_items") or [])


def _current_result(state: Mapping[str, Any], item: str, stage: str) -> Optional[Mapping[str, Any]]:
    action = planning_revision.current_actions(state).get((item, stage))
    result = (state.get("accepted") or {}).get(action) if action else None
    return result if isinstance(result, Mapping) else None


def _recorded_commands(state: Mapping[str, Any]) -> List[str]:
    """Every test command the run's current step plans record, in item order, each once."""
    commands: List[str] = []
    for item in state.get("work_items") or ():
        result = _current_result(state, str(item.get("id")), "step-plan") if isinstance(item, Mapping) else None
        for row in (result.get("test_commands") or ()) if result else ():
            command = str(row.get("command") or "").strip() if isinstance(row, Mapping) else ""
            if command and command not in commands:
                commands.append(command)
    return commands


def test_spec_coverage(state: Mapping[str, Any], submitted: Optional[Mapping[str, Any]] = None) -> Dict[str, List[str]]:
    """Per requirement, the case IDs (or ``suite: <command>``) that name it across the items' current test-spec
    results; ``submitted`` stands in for the current item's test-spec."""
    found: Dict[str, List[str]] = {}
    current = _current_item(state)
    for item in state.get("work_items") or ():
        ident = str(item.get("id")) if isinstance(item, Mapping) else ""
        result = submitted if submitted is not None and ident == current else _current_result(state, ident, TEST_SPEC)
        if not result:
            continue
        for case in result.get("test_cases") or ():
            if isinstance(case, Mapping):
                for requirement in knowledge.requirement_ids(str(case.get("requirement") or "")):
                    found.setdefault(requirement, []).append(str(case.get("id")))
        for row in result.get(SUITE_FIELD) or ():
            if isinstance(row, Mapping):
                found.setdefault(str(row.get("requirement")), []).append("suite: " + str(row.get("command")))
    return found


def check_test_spec(state: Mapping[str, Any], stage: str, result: Any) -> None:
    """TS1: a done test-spec's ``suite_requirements`` name current requirements and recorded test commands; at the last
    work item, every primary requirement has a case naming it, or a suite row (see the module docstring)."""
    if stage != TEST_SPEC or not isinstance(result, Mapping) or result.get("outcome") != "done":
        return
    repo = Path(str(state["repo"]))
    rows = canonical_suite(result[SUITE_FIELD]) if SUITE_FIELD in result else []
    if rows:
        held = knowledge.entries(repo, "spec.md")
        commands = _recorded_commands(state)
        for row in rows:
            _need(row["requirement"] in held and not held[row["requirement"]].retired,
                  "suite_requirements: " + row["requirement"] + " has no current entry in " + str(_spec_path(repo)))
            _need(row["command"] in commands,
                  "suite_requirements: " + row["command"] + " is not one of this run's recorded test commands ("
                  + (", ".join(commands) or "none: the step plans record no test_commands") + "): name the command "
                  "whose recorded run observes " + row["requirement"])
    ids = primary_ids(state)
    # A run whose step plans record no test command (documentation only, every one test_commands_na) has no executed
    # test to trace and no command a suite row could name: its acceptance stays product-acceptance's judgement.
    if not ids or not _is_last_item(state) or not _recorded_commands(state):
        return
    covered = test_spec_coverage(state, result)
    missing = [ident for ident in ids if not covered.get(ident)]
    if missing:   # the message names missing[0], so it is built only for a refusal
        raise PrimaryError(
            "every primary requirement (spec primary) needs a test case naming it in some work item's test-spec, and this "
            "is the last work item's. Missing: " + ", ".join(missing) + ". Add a case whose requirement names it; or, when "
            "a recorded command's own run observes it rather than one case (a test suite, a deploy or a check, such as "
            "\"the tests run with node --test\"), add " + SUITE_FIELD + ': [{"requirement": "' + missing[0]
            + '", "command": "<one of: ' + (", ".join(_recorded_commands(state)) or "the step plans' test_commands")
            + '>"}]: that command\'s recorded run observes it.')


def _listed(ids: List[str]) -> str:
    shown = ", ".join(ids[:PRINTED_IDS])
    return shown + (" and " + str(len(ids) - PRINTED_IDS) + " more" if len(ids) > PRINTED_IDS else "")


def check_unverified(root: Path, state: Mapping[str, Any], stage: str, result: Any) -> None:
    """A done product-acceptance result's ``unverified`` rows: each requirement has a current entry in the spec, and
    a primary requirement's ``lower_layer_check`` is a test ID ShipLoop's test runs passed in a case for it.

    The shape (the exact fields, placeholders, the due stage) is ``shiploop_unverified.check_submitted``'s, run first.
    """
    if stage != ACCEPTANCE or not isinstance(result, Mapping) or result.get("outcome") != "done":
        return
    rows = [row for row in result.get("unverified") or () if isinstance(row, Mapping)]
    if not rows:
        return
    repo = Path(str(state["repo"]))
    held = knowledge.entries(repo, "spec.md")
    for index, row in enumerate(rows):
        ident = str(row.get("requirement") or "").strip()
        _need(ident in held and not held[ident].retired,
              "unverified[" + str(index) + "].requirement " + ident + " has no current entry in " + str(_spec_path(repo))
              + ": name the R-<n> whose acceptance lines the outcome maps to (current: "
              + (", ".join(sorted((key for key, entry in held.items() if not entry.retired),
                                  key=lambda key: int(key.split("-")[1]))) or "none") + ")")
    primary = set(primary_ids(state) or ())
    passed = passed_cases(root, state)
    for index, row in enumerate(rows):
        requirement = str(row.get("requirement") or "").strip()
        if requirement not in primary:
            continue
        check = str(row.get("lower_layer_check") or "").strip()
        found = passed.get(requirement, [])
        _need(check in found,
              "unverified[" + str(index) + "] is an outcome of " + requirement + ", a primary requirement (spec "
              "primary), and its lower_layer_check names no test that ShipLoop's test runs passed in a case for "
              + requirement + " (" + ("passed: " + _listed(found) if found else "none has passed")
              + "). Set lower_layer_check to one of those IDs; when no unit or component test shows " + requirement
              + "'s logic, report add-work with one corrective work item that adds it: " + stage_spec.ADD_WORK_SHAPE)


def packet_lines(root: Path, state: Mapping[str, Any], stage: str) -> List[str]:
    """The required lines of two stages, so each gate's rule is read before the result is written: the last work item's
    test-spec gets the spec's primary requirements with the cases naming each so far (TS1); product-acceptance gets them
    with the tests that passed for each."""
    if state.get("status") != "active" or state.get("active_improve"):
        return []
    if stage == TEST_SPEC:
        ids = primary_ids(state)
        if not ids or not _is_last_item(state) or not _recorded_commands(state):
            return []
        covered = test_spec_coverage(state)
        return (["Primary requirements (spec primary): this is the last work item, so every one needs a test case naming "
                 "it in some work item's test-spec, or a " + SUITE_FIELD + ' row {"requirement": "R-<n>", "command": '
                 '"<a recorded test command>"} when that command\'s own run observes it (a test suite, a deploy or a '
                 'check). The cases so far:']
                + ["- " + ident + ": " + (_listed(covered[ident]) if covered.get(ident) else "no case yet")
                   for ident in ids])
    if stage != ACCEPTANCE:
        return []
    ids = primary_ids(state)
    if not ids:
        return ["Primary requirements: the spec result records none (spec primary), so no unverified row needs a "
                "passed lower-layer test."]
    passed = passed_cases(root, state)
    return (["Primary requirements (spec primary): an unverified row for one is accepted only when its "
             "lower_layer_check is a test ID below, which ShipLoop's test runs passed in a case for it; else add-work "
             "adds that unit or component test:"]
            + ["- " + ident + ": " + (_listed(passed[ident]) if passed.get(ident) else "none passed") for ident in ids])


__all__ = ("ACCEPTANCE", "FIELD", "PLACEHOLDER", "PRINTED_IDS", "PrimaryError", "STAGE", "SUITE_FIELD", "TEST_SPEC",
           "canonical", "canonical_suite", "check_spec", "check_test_spec", "check_unverified", "packet_lines",
           "passed_cases", "primary_ids", "test_spec_coverage")
