"""The test layers a run commits to (run-5 batch F1, F3): which harness tests each part of the code the run writes at
each layer, and which test targets keep state between runs.

A product review of a live run (2026-10-24) found the right rules in the stage texts and the model leaving through
an exit each text allowed: a missing browser tool made test-strategy mark the whole UI unverified (although a missing
repository facility is prerequisite work), the step plan confirmed UI criteria by searching source, and a target that
kept the item's own classes between runs made new tests pass on the base, a risk test-strategy wrote in prose that no
later packet carried.  So test-strategy records both as result fields, the gates check their shape and the one rule
each field exists for, and the prepare, step-plan, test-spec and test packets print them as required text.

Test-strategy result::

    "test_layers": [{"code": "<a module, component or page>", "layer": "unit" | "component" | "e2e",
                     "harness": "<runner, or none>", "status": "available" | "prerequisite" | "unverified",
                     "reason": "<why this status>"}]
    "targets": [{"target": "<where tests run>", "keeps_state": "yes" | "no",
                 "base_state_route": "<how a test still fails on an item's base there>"}]

``test_layers_na`` (a reason) stands in for ``test_layers`` when the run writes no code; a step plan whose paths hold
code then lists the item's own rows in ``test_layers``.  Every ``code`` has a unit or component row, and those layers
cannot be ``unverified``: a missing harness there is ``prerequisite`` work, and prepare's ``harness_runs`` shows each
one running.  ("Surface" stays the stage texts' word for where a requirement is observed; the rows name code.)

Step-plan criteria gain ``confirm``: ``executed`` (a recorded command runs the behaviour; a text search runs nothing),
``searched`` (a command searches text the item writes: documentation, a docstring, a listed term) or ``inspected``,
which names, in ``code`` and ``layer``, a ``test_layers`` row whose status is ``unverified`` (no runner exists there).
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Mapping, Optional, Sequence

import shiploop_test_counts as counts

LAYERS = ("unit", "component", "e2e")
STATUSES = ("available", "prerequisite", "unverified")
# The layers whose missing harness is work the run can do (prepare), never a reason to leave code unverified.
BUILD_LAYERS = ("unit", "component")
CONFIRMS = ("executed", "searched", "inspected")
YES_NO = ("yes", "no")
# Programs that only read text: a command made of these (and cd) confirms no behaviour.
SEARCH_PROGRAMS = frozenset(("grep", "egrep", "fgrep", "rg", "ag", "ack", "findstr", "select-string"))
# The print budget of the Test layers and Test targets lines together: the step-plan head carries them as required text
# below the host's output cut.  No gate refuses longer ones (owner, 2026-10-28, plan F2): past the budget a packet prints
# the lines that fit and names the run file that holds them all (shiploop_navigator._layer_lines, shiploop_fields).
LINES_PRINT = 1_200

ROW_TEMPLATE = {"code": "<code the run writes: a module, component or page>", "layer": "unit", "harness": "<runner>",
                "status": "available", "reason": "<why this status; for unverified, why no runner exists there>"}
TARGET_TEMPLATE = {"target": "<where the tests run>", "keeps_state": "no",
                   "base_state_route": "<how a test still fails on an item's base there>"}
HARNESS_RUN_TEMPLATE = {"code": "<a prerequisite row's code>", "layer": "unit",
                        "command": "<the command that ran the harness>", "evidence": "<absolute path of its output>"}
ROW_SHAPE = ('{"code": "...", "layer": "unit" | "component" | "e2e", "harness": "<runner, or none>", '
             '"status": "available" | "prerequisite" | "unverified", "reason": "..."}')
TARGET_SHAPE = ('{"target": "...", "keeps_state": "yes" | "no", "base_state_route": "<a clean target, a destructive '
                'or ordered deploy, or an inventory check; \\"n/a\\" when keeps_state is no>"}')
HARNESS_RUN_SHAPE = '{"code": "...", "layer": "...", "command": "...", "evidence": "<absolute path>"}'


class LayerError(ValueError):
    """A test-layer field that is malformed or breaks its rule; the message names the field, its shape and the fix."""


def _need(condition: bool, message: str) -> None:
    if not condition:
        raise LayerError(message)


def _text(value: Any, where: str) -> str:
    _need(isinstance(value, str) and bool(value.strip()), where + " must be nonblank text")
    text = " ".join(value.split())
    _need(not (text.startswith("<") and text.endswith(">")), where + " still holds the template placeholder " + text
          + ": write the real value")
    return text


def canonical_rows(value: Any) -> List[Dict[str, str]]:
    """The ``test_layers`` rows, shape-checked; the rules are ``check_rows``."""
    _need(isinstance(value, list), "test_layers is a list of " + ROW_SHAPE)
    rows = []
    for index, row in enumerate(value):
        where = "test_layers[" + str(index) + "]"
        _need(isinstance(row, Mapping) and set(row) == set(ROW_TEMPLATE), where + " is " + ROW_SHAPE)
        _need(row["layer"] in LAYERS, where + ".layer is one of " + ", ".join(LAYERS))
        _need(row["status"] in STATUSES, where + ".status is one of " + ", ".join(STATUSES))
        rows.append({key: _text(row[key], where + "." + key) for key in ROW_TEMPLATE})
    return rows


def check_rows(rows: Sequence[Mapping[str, str]]) -> None:
    """Refuse a repeated row, code with no unit or component row, and an unverified unit or component layer."""
    keys = [(row["code"], row["layer"]) for row in rows]
    repeated = sorted({code + " [" + layer + "]" for code, layer in keys if keys.count((code, layer)) > 1})
    _need(not repeated, "test_layers repeats " + ", ".join(repeated) + ": one row per code and layer")
    built = {row["code"] for row in rows if row["layer"] in BUILD_LAYERS}
    bare = sorted({row["code"] for row in rows} - built)
    _need(not bare, "test_layers gives " + ", ".join(bare) + " no unit or component row. All code the run writes is "
          "tested below the e2e layer: add its unit or component row, status prerequisite when its harness is missing.")
    skipped = [row["code"] + " [" + row["layer"] + "]" for row in rows
               if row["layer"] in BUILD_LAYERS and row["status"] == "unverified"]
    _need(not skipped, "test_layers marks a unit or component layer unverified: " + ", ".join(skipped) + ". A missing "
          "harness at those layers is work this run can do: set status prerequisite, name the harness in harness, and "
          "prepare sets it up. Only an e2e layer with no runner may stay unverified.")


def canonical_targets(value: Any) -> List[Dict[str, str]]:
    _need(isinstance(value, list), "targets is a list of " + TARGET_SHAPE)
    rows = []
    for index, row in enumerate(value):
        where = "targets[" + str(index) + "]"
        _need(isinstance(row, Mapping) and set(row) == set(TARGET_TEMPLATE), where + " is " + TARGET_SHAPE)
        _need(row["keeps_state"] in YES_NO, where + ".keeps_state is yes or no")
        found = {key: _text(row[key], where + "." + key) for key in TARGET_TEMPLATE}
        _need(row["keeps_state"] == "no" or found["base_state_route"].lower() not in ("n/a", "na", "none"),
              where + " keeps state between runs, so base_state_route says how a test still fails on an item's base "
              "there: a clean target, a destructive or ordered deploy, or an inventory check")
        rows.append(found)
    return rows


def search_only(command: str) -> bool:
    """Whether every program ``command`` runs only searches text (``grep`` and its kin, besides ``cd``)."""
    programs = []
    for segment in re.split(r"&&|\|\||[;|\n]", command):
        words = segment.split()
        while words and (words[0] in ("!", "env", "command", "exec", "time") or re.match(r"^\w+=", words[0])):
            words = words[1:]
        if words and words[0] != "cd":
            programs.append(words[0].rsplit("/", 1)[-1].lower())
    return bool(programs) and all(program in SEARCH_PROGRAMS for program in programs)


def check_confirms(criteria: Sequence[Mapping[str, Any]], rows: Optional[Sequence[Mapping[str, str]]],
                   commands: Sequence[Mapping[str, Any]]) -> None:
    """Every step-plan criterion says how it is confirmed: ``executed`` by a command that runs something besides a text
    search, ``searched`` by any recorded command, ``inspected`` by naming an unverified test_layers row."""
    missing = [str(row.get("id")) for row in criteria if row.get("confirm") not in CONFIRMS]
    _need(not missing, "each criterion says confirm: \"executed\" (a recorded command runs the behaviour), \"searched\" "
          "(a command searches text the item writes) or \"inspected\" (with code and layer: the test_layers row that "
          "has no runner); missing or other on: " + ", ".join(missing))
    no_runner = {(row["code"], row["layer"]) for row in rows or () if row.get("status") == "unverified"}
    wrong = [str(row.get("id")) for row in criteria if row.get("confirm") == "inspected"
             and (str(row.get("code") or ""), str(row.get("layer") or "")) not in no_runner]
    _need(not wrong, "criteria " + ", ".join(wrong) + " are inspected, but name no test_layers row (code and layer) whose "
          "status is unverified (" + (", ".join(code + " [" + layer + "]" for code, layer in sorted(no_runner))
                                      or "the run recorded none") + "). Behaviour a runner can execute is confirmed by "
          "executing it: set confirm executed and give it a command that runs it and observes the result.")
    naming = {str(row.get("id")): [str(command.get("command") or "") for command in commands
                                   if str(row.get("id")) in (command.get("criteria") or ())] for row in criteria}
    # A criterion no command names is the coverage gate's refusal, not this one.
    searched = [str(row.get("id")) for row in criteria if row.get("confirm") == "executed"
                and naming[str(row.get("id"))] and all(search_only(command) for command in naming[str(row.get("id"))])]
    _need(not searched, "criteria " + ", ".join(searched) + " are executed, but every command naming them only searches "
          "text, which runs no behaviour. Name a command that runs the code and observes the result; a criterion "
          "about text the item writes (documentation, a docstring) is confirm searched.")


def check_harness_runs(rows: Optional[Sequence[Mapping[str, str]]], value: Any) -> List[Dict[str, str]]:
    """Prepare's ``harness_runs``: one entry per prerequisite test_layers row, the command that ran its harness and the
    saved output.  The caller checks that each evidence path exists."""
    _need(isinstance(value, list), "harness_runs is a list of " + HARNESS_RUN_SHAPE)
    runs = []
    for index, row in enumerate(value):
        where = "harness_runs[" + str(index) + "]"
        _need(isinstance(row, Mapping) and set(row) == set(HARNESS_RUN_TEMPLATE), where + " is " + HARNESS_RUN_SHAPE)
        runs.append({key: _text(row[key], where + "." + key) for key in HARNESS_RUN_TEMPLATE})
    wanted = [(row["code"], row["layer"]) for row in rows or () if row.get("status") == "prerequisite"]
    ran = {(run["code"], run["layer"]) for run in runs}
    unrun = [code + " [" + layer + "]" for code, layer in wanted if (code, layer) not in ran]
    _need(not unrun, "harness_runs has no run for the prerequisite rows " + ", ".join(unrun) + ". Set up each harness, run "
          "it once (a test it executes, not a version or help line) and record the command and its saved output; one "
          "this run cannot set up: report blocked naming it.")
    return runs


def check_harness_output(run: Mapping[str, str], output: str) -> None:
    """A harness_runs entry's saved output shows at least one test running, read by the runner readers the test stage
    uses (``shiploop_test_counts``).  Run 5a's evidence was a browser page that said it was not the component under
    test, and a file-exists check accepted it."""
    label = run["code"] + " [" + run["layer"] + "]"
    seen = counts.count(output, None)
    _need(seen is not None, "harness_runs evidence " + run["evidence"] + " for " + label + " shows no test run ShipLoop "
          "can read. Save the runner's own output of one test it ran, summary line included (runners ShipLoop reads: "
          + counts.RUNNERS + "; the stack's platform card under references/platforms/ names a readable reporter). A "
          "page, a probe, a listing or a version line is not a test run. A harness this run cannot run so: report "
          "blocked naming it.")
    _need(seen["ran"] >= 1, "harness_runs evidence " + run["evidence"] + " for " + label + " ran no test (the runner "
          "selected none). Run one test with the harness and save that output.")


def criterion_label(row: Mapping[str, Any]) -> str:
    """A criterion's ID with how it is confirmed, as the later packets print it: ``C2 [inspected: board UI e2e]``."""
    confirm = row.get("confirm")
    if confirm == "inspected":
        return str(row.get("id")) + " [inspected: " + str(row.get("code")) + " " + str(row.get("layer")) + "]"
    return str(row.get("id")) + (" [" + str(confirm) + "]" if confirm in CONFIRMS else "")


def packet_lines(rows: Optional[Sequence[Mapping[str, str]]], targets: Optional[Sequence[Mapping[str, str]]]) \
        -> List[str]:
    """The required-text lines the prepare, step-plan, test-spec and test packets print: the rows grouped by layer,
    harness and status (with the reason when a row is not available), then one line per target."""
    lines: List[str] = []
    groups: Dict[tuple, List[str]] = {}
    for row in sorted(rows or (), key=lambda row: LAYERS.index(row["layer"])):
        reason = row["reason"] if row["status"] != "available" else ""
        groups.setdefault((row["layer"], row["harness"], row["status"], reason), []).append(row["code"])
    if groups:
        lines.append("Test layers (`test_layers`; an inspected criterion names an unverified row by code and layer):")
        lines += ["- " + layer + " · " + harness + " · " + status + (" (" + reason + ")" if reason else "") + ": "
                  + ", ".join(names) for (layer, harness, status, reason), names in groups.items()]
    if targets:
        lines.append("Test targets (`targets`; a case on one that keeps state says in red how its base fails):")
        lines += ["- " + row["target"] + ": keeps state " + row["keeps_state"]
                  + ("; base state: " + row["base_state_route"] if row["keeps_state"] == "yes" else "")
                  for row in targets]
    return lines


__all__ = ("BUILD_LAYERS", "CONFIRMS", "HARNESS_RUN_SHAPE", "HARNESS_RUN_TEMPLATE", "LAYERS", "LINES_PRINT",
           "LayerError", "ROW_SHAPE", "ROW_TEMPLATE", "SEARCH_PROGRAMS", "STATUSES", "TARGET_SHAPE", "TARGET_TEMPLATE",
           "canonical_rows", "canonical_targets", "check_confirms", "check_harness_output",
           "check_harness_runs", "check_rows", "criterion_label", "packet_lines", "search_only")
