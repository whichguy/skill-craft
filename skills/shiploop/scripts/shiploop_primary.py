"""The request's primary requirements: the work items that serve them, and the lower-layer check of an outcome no
executed check observed (run-5 batch F6).

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

Coverage of the primary requirements is a property of the plan (F3 of docs/shiploop-planning-speed-and-caps-plan-
2026-10-28.md; owner, 2026-10-28: a test covers "the primary requirements for that particular stage of the build").
Each work item names in ``follows`` the R-<n> it serves and the AD-<n> it follows.  A done plan, and a done
carry-forward that replaces the future queue, leave every primary requirement in some work item's ``follows``, each ID
there with an entry in the living files; the exit is to widen a work item or add one.  A test-spec stays relative to its
step: one case per ID its step plan's focused commands list.  This replaces TS1 (2026-10-26), which asked the last work
item's test-spec for a case naming every primary requirement: in the D7 follow-on run (ticket-escalation, 2026-10-28)
it refused that test-spec for R-20 (existing behaviour and tests preserved), which no ID of the step's focused commands
served, and asked it to add a case.

Where "ran and saw pass" comes from: ShipLoop's own test records, ``tests/<action>-verify<N>.md``, of the accepted
inner actions (the test stage's candidate run and document's rerun).  A record that passed, a run in it whose status is
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
# The stages whose done result sets the work queue: plan writes it whole, carry-forward may replace its future part.
QUEUE_STAGES = ("plan", "carry-forward")
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


def _follows(row: Any) -> List[str]:
    value = row.get("follows") if isinstance(row, Mapping) else None
    return [str(ident) for ident in value] if isinstance(value, list) else []


def queue_after(state: Mapping[str, Any], stage: str, result: Mapping[str, Any]) -> Optional[List[Mapping[str, Any]]]:
    """The work queue a done ``result`` at ``stage`` leaves, or None when it leaves the queue as it was: at plan, its
    ``work_items`` (the retained queue when it gives none); at carry-forward, the completed and current items and then
    the future queue it gives."""
    if stage == "plan":
        rows = result.get("work_items", state.get("work_items"))
    elif stage == "carry-forward" and "work_items" in result:
        index = state.get("work_index")
        kept = list(state.get("work_items") or ())[: index + 1] if isinstance(index, int) else []
        rows = [*kept, *(result.get("work_items") or ())]
    else:
        return None
    return [row for row in rows or () if isinstance(row, Mapping)]


def followers(queue: List[Mapping[str, Any]]) -> Dict[str, List[str]]:
    """Per R-<n> or AD-<n>, the IDs of the work items whose ``follows`` names it, in queue order."""
    found: Dict[str, List[str]] = {}
    for row in queue:
        for ident in _follows(row):
            found.setdefault(ident, []).append(str(row.get("id")))
    return found


def check_queue(state: Mapping[str, Any], stage: str, result: Any) -> None:
    """A done plan, or a done carry-forward that replaces the future queue: each ``follows`` ID its work items give has
    an entry in the living files, and every primary requirement is in the ``follows`` of some work item of the queue it
    leaves (see the module docstring)."""
    if stage not in QUEUE_STAGES or not isinstance(result, Mapping) or result.get("outcome") != "done":
        return
    queue = queue_after(state, stage, result)
    if queue is None:
        return
    repo = Path(str(state["repo"]))
    architecture = repo / knowledge.HOME / knowledge.ARCHITECTURE
    known = {**knowledge.entries(repo, "spec.md"), **knowledge.entries(repo, knowledge.ARCHITECTURE)}
    absent = list(dict.fromkeys(ident for row in result.get("work_items") or () for ident in _follows(row)
                                if ident not in known))
    _need(not absent, "work_items follows names " + ", ".join(absent) + ", with no entry (a line that starts with the "
          "ID) in " + str(_spec_path(repo)) + " (R-) or " + str(architecture) + " (AD-): cite only IDs with an entry, "
          "or write the entry first")
    ids = primary_ids(state)
    if not ids:
        return
    served = followers(queue)
    missing = [ident for ident in ids if ident not in served]
    if missing:   # the message names missing[0], so it is built only for a refusal
        raise PrimaryError(
            "every primary requirement (spec primary) is served by a work item whose follows names it, and no work item "
            + ("of this plan" if stage == "plan" else "of the queue this result leaves (the completed and current "
               "items, then the work_items given)") + " names " + ", ".join(missing) + ". Widen the work item that "
            "serves it (its follows and context) or add a work item that serves it, such as "
            '{"id": "W<n>", "title": "...", "follows": ["' + missing[0] + '"], "context": "..."}')


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
    """The required lines of the stages whose gate reads the primary requirements, so the rule is read before the result
    is written: plan and carry-forward get them with the work items whose follows name each so far; product-acceptance
    gets them with the tests that passed for each."""
    if state.get("status") != "active" or state.get("active_improve"):
        return []
    ids = primary_ids(state)
    if stage in QUEUE_STAGES:
        if not ids:
            return []
        served = followers([row for row in state.get("work_items") or () if isinstance(row, Mapping)])
        head = ("Primary requirements (spec primary): each must be in the follows of a work item that serves it; "
                "ShipLoop refuses a queue that leaves one out. The work items naming each now:")
        return [head, *("- " + ident + ": " + (", ".join(served[ident]) if served.get(ident) else "none")
                        for ident in ids)]
    if stage != ACCEPTANCE:
        return []
    if not ids:
        return ["Primary requirements: the spec result records none (spec primary), so no unverified row needs a "
                "passed lower-layer test."]
    passed = passed_cases(root, state)
    return (["Primary requirements (spec primary): an unverified row for one is accepted only when its "
             "lower_layer_check is a test ID below, which ShipLoop's test runs passed in a case for it; else add-work "
             "adds that unit or component test:"]
            + ["- " + ident + ": " + (_listed(passed[ident]) if passed.get(ident) else "none passed") for ident in ids])


__all__ = ("ACCEPTANCE", "FIELD", "PLACEHOLDER", "PRINTED_IDS", "PrimaryError", "QUEUE_STAGES", "STAGE", "canonical",
           "check_queue", "check_spec", "check_unverified", "followers", "packet_lines", "passed_cases", "primary_ids",
           "queue_after")
