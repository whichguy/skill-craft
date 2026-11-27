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
reflect-and-revise that replaces the future queue, leave every primary requirement in some work item's ``follows``, each ID
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
# The stages whose done result sets the work queue: plan writes it whole, reflect-and-revise may replace its future part.
QUEUE_STAGES = ("plan", "reflect-and-revise")
# Display: how many primary IDs one plan or reflect-and-revise packet lists; a spec with more says so and names where the rest are.
PRIMARY_SHOWN = 6
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


_REGRESSION_REPAIR_HINT = re.compile(r"\b(?:regression|baseline|repair|fix|broken|characteri[sz]ation)\b", re.IGNORECASE)


def _sorted_req_ids(ids: Any) -> List[str]:
    return sorted(ids, key=lambda value: int(value.split("-")[1]))


def check_spec(repo: Path, stage: str, result: Any, *, root: Optional[Path] = None,
               state: Optional[Mapping[str, Any]] = None) -> None:
    """A done spec result lists ``primary``: at least one R-<n>, each once, each with a current entry in the spec.

    On follow-on runs whose spec delta adds/modifies requirements, ``primary`` lists only those changed/added IDs
    rather than unchanged master requirements.
    """
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
    if root is not None and state is not None:
        delta = knowledge.case_delta(Path(root), state)
        if delta is not None and delta.is_follow_on:
            changed_active = set(delta.added_requirements) | set(delta.modified_requirements)
            unchanged = set(delta.unchanged_requirements)
            stale_master = [ident for ident in ids if ident in unchanged]
            if changed_active and stale_master:
                raise PrimaryError(
                    "on follow-on Case " + delta.case_id + ", primary names unchanged master requirement(s) "
                    + ", ".join(stale_master) + ". Keep primary scoped to this case's added/modified requirements ("
                    + ", ".join(_sorted_req_ids(changed_active))
                    + "); unchanged master requirements stay regression-preserved without reimplementation.")


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
    ``work_items`` (the retained queue when it gives none); at reflect-and-revise, the completed and current items and then
    the future queue it gives."""
    if stage == "plan":
        rows = result.get("work_items", state.get("work_items"))
    elif stage == "reflect-and-revise" and "work_items" in result:
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


def check_queue(state: Mapping[str, Any], stage: str, result: Any, *, root: Optional[Path] = None) -> None:
    """A done plan, or a done reflect-and-revise that replaces the future queue: each ``follows`` ID its work items give has
    an entry in the living files, every primary requirement is in the ``follows`` of some work item of the queue it
    leaves, and on follow-on runs with a spec delta every added/modified/retired requirement is owned without
    inventing reimplementation-only work items on unchanged master requirements."""
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
          "ID) in " + str(_spec_path(repo)) + " (R-) or " + str(architecture) + " (AD-): cite only IDs with an entry"
          + ("" if stage == "reflect-and-revise" else ", or write the entry first"))
    ids = primary_ids(state)
    served = followers(queue)
    if ids:
        missing = [ident for ident in ids if ident not in served]
        if missing:   # the message names missing[0], so it is built only for a refusal
            raise PrimaryError(
                "every primary requirement (spec primary) is served by a work item whose follows names it, and no work item "
                + ("of this plan" if stage == "plan" else "of the queue this result leaves (the completed and current "
                   "items, then the work_items given)") + " names " + ", ".join(missing) + ". Widen "
                + ("the work item" if stage == "plan" else "a future work item") + " that serves it (its follows and context) or "
                "add a work item that serves it, such as "
                '{"id": "W<n>", "title": "...", "follows": ["' + missing[0] + '"], "context": "..."}')
    if root is None:
        return
    delta = knowledge.case_delta(Path(root), state)
    if delta is None or not delta.is_follow_on:
        return
    changed_reqs = _sorted_req_ids(
        set(delta.added_requirements) | set(delta.modified_requirements) | set(delta.retired_requirements)
    )
    if not changed_reqs:
        return
    missing_delta = [ident for ident in changed_reqs if ident not in served]
    if missing_delta:
        raise PrimaryError(
            "Case " + delta.case_id + " changed/added/retired " + ", ".join(missing_delta)
            + ", and no work item in "
            + ("this plan" if stage == "plan" else "the queue this result leaves")
            + " lists them in follows. Widen an owning item or add one carrying "
            + missing_delta[0] + " in follows.")
    unchanged = set(delta.unchanged_requirements)
    for row in result.get("work_items") or ():
        if not isinstance(row, Mapping):
            continue
        req_follows = [ident for ident in _follows(row) if ident.startswith("R-")]
        if req_follows and all(ident in unchanged for ident in req_follows):
            label = str(row.get("title") or "") + " " + str(row.get("context") or "")
            if not _REGRESSION_REPAIR_HINT.search(label):
                wid = str(row.get("id") or "W<n>")
                raise PrimaryError(
                    "work item " + wid + " follows only unchanged master requirement(s) ("
                    + ", ".join(req_follows) + ") on follow-on Case " + delta.case_id
                    + ", which risks reimplementing existing features. Scope work items to Case "
                    + delta.case_id + "'s delta (" + ", ".join(changed_reqs)
                    + ") or explicitly mark the item as a baseline regression/repair check.")


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
    is written: plan and reflect-and-revise get them with the work items whose follows name each so far; product-acceptance
    gets them with the tests that passed for each."""
    if state.get("status") != "active" or state.get("active_improve"):
        return []
    ids = primary_ids(state)
    if stage in QUEUE_STAGES:
        if not ids:
            return []
        shown = ids[:PRIMARY_SHOWN]
        more = ("; +" + str(len(ids) - len(shown)) + " more (spec primary)") if len(ids) > len(shown) else ""
        if stage == "plan":   # one short line: the plan head has the least room, and no item exists yet to follow anything
            return ["Primary requirements (spec primary), each in a work item's follows: " + " ".join(shown) + more + "."]
        served = followers([row for row in state.get("work_items") or () if isinstance(row, Mapping)])
        return ["Primary requirements (spec primary) and the work items following each now: "
                + "; ".join(ident + " " + (", ".join(served[ident]) if served.get(ident) else "none") for ident in shown)
                + more + ". The queue you leave keeps each in some work item's follows."]
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


def case_delta_lines(root: Path, state: Mapping[str, Any], stage: str) -> List[str]:
    """Compact Case C-<n> incremental-spec block for outer/step planning and acceptance packet heads."""
    if state.get("status") != "active" or state.get("active_improve"):
        return []
    if stage not in ("test-strategy", "plan", "step-plan", "reflect-and-revise", "product-acceptance"):
        return []
    delta = knowledge.case_delta(Path(root), state)
    if delta is None:
        return []
    if not delta.is_follow_on:
        if not delta.added_requirements:
            return []
        return [
            f"Case {delta.case_id} (initial build, RUN/{knowledge.CASE_SPEC_FILE}): "
            f"all spec requirements are new ({', '.join(delta.added_requirements)})."
        ]
    mod_ids = _sorted_req_ids(delta.modified_requirements.keys())
    return [
        f"Case {delta.case_id} incremental spec (RUN/{knowledge.CASE_SPEC_FILE}; master spec KNOWLEDGE/spec.md):",
        "- Added (implement): " + (", ".join(delta.added_requirements) if delta.added_requirements else "none"),
        "- Modified (implement delta lines only; preserve existing behaviour): "
        + (", ".join(mod_ids) if mod_ids else "none"),
        "- Retired (remove/deprecate): " + (", ".join(delta.retired_requirements) if delta.retired_requirements else "none"),
        "- Unchanged master (preserve & regression-check only; DO NOT reimplement): "
        + (", ".join(delta.unchanged_requirements) if delta.unchanged_requirements else "none"),
    ]


__all__ = ("ACCEPTANCE", "FIELD", "PLACEHOLDER", "PRINTED_IDS", "PrimaryError", "QUEUE_STAGES", "STAGE", "canonical",
           "case_delta_lines", "check_queue", "check_spec", "check_unverified", "followers", "packet_lines",
           "passed_cases", "primary_ids", "queue_after")
