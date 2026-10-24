"""The test layers a run commits to (run-5 batch F1, F3): which harness tests each code surface at each layer, and
which test targets keep state between runs.

A product review of a live run (2026-10-24) found the right rules in the stage texts and the model leaving through
an exit each text allowed: a missing browser tool made test-strategy mark the whole UI unverified (although a missing
repository facility is prerequisite work), the step plan confirmed UI criteria by searching source, and a target that
kept the item's own classes between runs made new tests pass on the base, a risk test-strategy wrote in prose that no
later packet carried.  So test-strategy records both as result fields, the gates check their shape and the one rule
each field exists for, and the prepare, step-plan, test-spec and test packets print them as required text.

Test-strategy result::

    "surfaces": [{"surface": "<code surface>", "layer": "unit" | "component" | "e2e", "harness": "<runner, or none>",
                  "status": "available" | "prerequisite" | "unverified", "reason": "<why this status>"}]
    "targets": [{"target": "<where tests run>", "keeps_state": "yes" | "no",
                 "base_state_route": "<how a test still fails on an item's base there>"}]

``surfaces_na`` (a reason) stands in for ``surfaces`` when the run writes no code; a step plan whose paths hold code then
lists the item's own rows in ``surfaces``.  Every surface has a unit or component row, and those layers cannot be
``unverified``: a missing harness there is ``prerequisite`` work, and prepare's ``harness_runs`` shows each one running.

Step-plan criteria gain ``confirm``: ``executed`` (a recorded command runs the behaviour; a text search runs nothing),
``searched`` (a command searches text the item writes: documentation, a docstring, a listed term) or ``inspected``,
which names, in ``surface`` and ``layer``, a ``surfaces`` row whose status is ``unverified`` (no runner exists there).
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Mapping, Optional, Sequence

LAYERS = ("unit", "component", "e2e")
STATUSES = ("available", "prerequisite", "unverified")
# The layers whose missing harness is work the run can do (prepare), never a reason to leave code unverified.
BUILD_LAYERS = ("unit", "component")
CONFIRMS = ("executed", "searched", "inspected")
YES_NO = ("yes", "no")
# Programs that only read text: a command made of these (and cd) confirms no behaviour.
SEARCH_PROGRAMS = frozenset(("grep", "egrep", "fgrep", "rg", "ag", "ack", "findstr", "select-string"))
# Each field's limit, and the printed Test layers and Test targets lines together: the step-plan head carries them as
# required text below the host's output cut, so the gate keeps them short instead of the print cutting them.
FIELD_LIMITS = {"surface": 60, "harness": 80, "reason": 160, "target": 60, "base_state_route": 240}
TEXT_LIMIT = 1_200

SURFACE_TEMPLATE = {"surface": "<code surface the run writes>", "layer": "unit", "harness": "<runner>",
                    "status": "available", "reason": "<why this status; for unverified, why no runner exists there>"}
TARGET_TEMPLATE = {"target": "<where the tests run>", "keeps_state": "no",
                   "base_state_route": "<how a test still fails on an item's base there>"}
HARNESS_RUN_TEMPLATE = {"surface": "<a prerequisite row's surface>", "layer": "unit",
                        "command": "<the command that ran the harness>", "evidence": "<absolute path of its output>"}
SURFACE_SHAPE = ('{"surface": "...", "layer": "unit" | "component" | "e2e", "harness": "<runner, or none>", '
                 '"status": "available" | "prerequisite" | "unverified", "reason": "..."}')
TARGET_SHAPE = ('{"target": "...", "keeps_state": "yes" | "no", "base_state_route": "<a clean target, a destructive '
                'or ordered deploy, or an inventory check; \\"n/a\\" when keeps_state is no>"}')
HARNESS_RUN_SHAPE = '{"surface": "...", "layer": "...", "command": "...", "evidence": "<absolute path>"}'


class LayerError(ValueError):
    """A test-layer field that is malformed or breaks its rule; the message names the field, its shape and the fix."""


def _need(condition: bool, message: str) -> None:
    if not condition:
        raise LayerError(message)


def _text(value: Any, where: str, limit: Optional[int] = None) -> str:
    _need(isinstance(value, str) and bool(value.strip()), where + " must be nonblank text")
    text = " ".join(value.split())
    _need(not (text.startswith("<") and text.endswith(">")), where + " still holds the template placeholder " + text
          + ": write the real value")
    _need(limit is None or len(text) <= limit, where + " is " + str(len(text)) + " characters; keep it within "
          + str(limit) + " (the packets print it whole)")
    return text


def canonical_surfaces(value: Any) -> List[Dict[str, str]]:
    """The ``surfaces`` rows, shape-checked; the rules are ``check_surfaces``."""
    _need(isinstance(value, list), "surfaces is a list of " + SURFACE_SHAPE)
    rows = []
    for index, row in enumerate(value):
        where = "surfaces[" + str(index) + "]"
        _need(isinstance(row, Mapping) and set(row) == set(SURFACE_TEMPLATE), where + " is " + SURFACE_SHAPE)
        _need(row["layer"] in LAYERS, where + ".layer is one of " + ", ".join(LAYERS))
        _need(row["status"] in STATUSES, where + ".status is one of " + ", ".join(STATUSES))
        rows.append({key: _text(row[key], where + "." + key, FIELD_LIMITS.get(key)) for key in SURFACE_TEMPLATE})
    return rows


def check_surfaces(rows: Sequence[Mapping[str, str]]) -> None:
    """Refuse a repeated row, a surface with no unit or component row, and an unverified unit or component layer."""
    keys = [(row["surface"], row["layer"]) for row in rows]
    repeated = sorted({surface + " [" + layer + "]" for surface, layer in keys if keys.count((surface, layer)) > 1})
    _need(not repeated, "surfaces repeats " + ", ".join(repeated) + ": one row per surface and layer")
    built = {row["surface"] for row in rows if row["layer"] in BUILD_LAYERS}
    bare = sorted({row["surface"] for row in rows} - built)
    _need(not bare, "surfaces gives " + ", ".join(bare) + " no unit or component row. The code under every surface is "
          "tested below the e2e layer: add its unit or component row, status prerequisite when its harness is missing.")
    skipped = [row["surface"] + " [" + row["layer"] + "]" for row in rows
               if row["layer"] in BUILD_LAYERS and row["status"] == "unverified"]
    _need(not skipped, "surfaces marks a unit or component layer unverified: " + ", ".join(skipped) + ". A missing "
          "harness at those layers is work this run can do: set status prerequisite, name the harness in harness, and "
          "prepare sets it up. Only an e2e layer with no runner may stay unverified.")


def canonical_targets(value: Any) -> List[Dict[str, str]]:
    _need(isinstance(value, list), "targets is a list of " + TARGET_SHAPE)
    rows = []
    for index, row in enumerate(value):
        where = "targets[" + str(index) + "]"
        _need(isinstance(row, Mapping) and set(row) == set(TARGET_TEMPLATE), where + " is " + TARGET_SHAPE)
        _need(row["keeps_state"] in YES_NO, where + ".keeps_state is yes or no")
        found = {key: _text(row[key], where + "." + key, FIELD_LIMITS.get(key)) for key in TARGET_TEMPLATE}
        _need(row["keeps_state"] == "no" or found["base_state_route"].lower() not in ("n/a", "na", "none"),
              where + " keeps state between runs, so base_state_route says how a test still fails on an item's base "
              "there: a clean target, a destructive or ordered deploy, or an inventory check")
        rows.append(found)
    return rows


def check_text(surfaces: Optional[Sequence[Mapping[str, str]]], targets: Optional[Sequence[Mapping[str, str]]]) -> None:
    """Refuse layers and targets whose printed lines pass ``TEXT_LIMIT``: later heads carry them whole."""
    size = len("\n".join(packet_lines(surfaces, targets)))
    _need(size <= TEXT_LIMIT, "surfaces and targets print as " + str(size) + " characters; keep them within "
          + str(TEXT_LIMIT) + ": name broader surfaces, and shorten harness, reason and base_state_route")


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


def check_confirms(criteria: Sequence[Mapping[str, Any]], surfaces: Optional[Sequence[Mapping[str, str]]],
                   commands: Sequence[Mapping[str, Any]]) -> None:
    """Every step-plan criterion says how it is confirmed: ``executed`` by a command that runs something besides a text
    search, ``searched`` by any recorded command, ``inspected`` by naming an unverified surfaces row."""
    missing = [str(row.get("id")) for row in criteria if row.get("confirm") not in CONFIRMS]
    _need(not missing, "each criterion says confirm: \"executed\" (a recorded command runs the behaviour), \"searched\" "
          "(a command searches text the item writes) or \"inspected\" (with surface and layer: the surfaces row that "
          "has no runner); missing or other on: " + ", ".join(missing))
    no_runner = {(row["surface"], row["layer"]) for row in surfaces or () if row.get("status") == "unverified"}
    wrong = [str(row.get("id")) for row in criteria if row.get("confirm") == "inspected"
             and (str(row.get("surface") or ""), str(row.get("layer") or "")) not in no_runner]
    _need(not wrong, "criteria " + ", ".join(wrong) + " are inspected, but name no surfaces row (surface and layer) whose "
          "status is unverified (" + (", ".join(surface + " [" + layer + "]" for surface, layer in sorted(no_runner))
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


def check_harness_runs(surfaces: Optional[Sequence[Mapping[str, str]]], value: Any) -> List[Dict[str, str]]:
    """Prepare's ``harness_runs``: one entry per prerequisite surfaces row, the command that ran its harness and the
    saved output.  The caller checks that each evidence path exists."""
    _need(isinstance(value, list), "harness_runs is a list of " + HARNESS_RUN_SHAPE)
    rows = []
    for index, row in enumerate(value):
        where = "harness_runs[" + str(index) + "]"
        _need(isinstance(row, Mapping) and set(row) == set(HARNESS_RUN_TEMPLATE), where + " is " + HARNESS_RUN_SHAPE)
        rows.append({key: _text(row[key], where + "." + key) for key in HARNESS_RUN_TEMPLATE})
    wanted = [(row["surface"], row["layer"]) for row in surfaces or () if row.get("status") == "prerequisite"]
    ran = {(row["surface"], row["layer"]) for row in rows}
    unrun = [surface + " [" + layer + "]" for surface, layer in wanted if (surface, layer) not in ran]
    _need(not unrun, "harness_runs has no run for the prerequisite rows " + ", ".join(unrun) + ". Set up each harness, run "
          "it once (a test it executes, not a version or help line) and record the command and its saved output; one "
          "this run cannot set up: report blocked naming it.")
    return rows


def criterion_label(row: Mapping[str, Any]) -> str:
    """A criterion's ID with how it is confirmed, as the later packets print it: ``C2 [inspected: UI e2e]``."""
    confirm = row.get("confirm")
    if confirm == "inspected":
        return str(row.get("id")) + " [inspected: " + str(row.get("surface")) + " " + str(row.get("layer")) + "]"
    return str(row.get("id")) + (" [" + str(confirm) + "]" if confirm in CONFIRMS else "")


def packet_lines(surfaces: Optional[Sequence[Mapping[str, str]]], targets: Optional[Sequence[Mapping[str, str]]]) \
        -> List[str]:
    """The required-text lines the prepare, step-plan, test-spec and test packets print: the surfaces grouped by layer,
    harness and status (with the reason when a row is not available), then one line per target."""
    lines: List[str] = []
    groups: Dict[tuple, List[str]] = {}
    for row in sorted(surfaces or (), key=lambda row: LAYERS.index(row["layer"])):
        reason = row["reason"] if row["status"] != "available" else ""
        groups.setdefault((row["layer"], row["harness"], row["status"], reason), []).append(row["surface"])
    if groups:
        lines.append("Test layers (`surfaces`; an inspected criterion names an unverified row by surface and layer):")
        lines += ["- " + layer + " · " + harness + " · " + status + (" (" + reason + ")" if reason else "") + ": "
                  + ", ".join(names) for (layer, harness, status, reason), names in groups.items()]
    if targets:
        lines.append("Test targets (`targets`; a case on one that keeps state says in red how its base fails):")
        lines += ["- " + row["target"] + ": keeps state " + row["keeps_state"]
                  + ("; base state: " + row["base_state_route"] if row["keeps_state"] == "yes" else "")
                  for row in targets]
    return lines


__all__ = ("BUILD_LAYERS", "CONFIRMS", "FIELD_LIMITS", "HARNESS_RUN_SHAPE", "HARNESS_RUN_TEMPLATE", "LAYERS",
           "LayerError", "SEARCH_PROGRAMS", "STATUSES", "SURFACE_SHAPE", "SURFACE_TEMPLATE", "TARGET_SHAPE",
           "TARGET_TEMPLATE", "TEXT_LIMIT", "canonical_surfaces", "canonical_targets", "check_confirms",
           "check_harness_runs", "check_surfaces", "check_text", "criterion_label", "packet_lines", "search_only")
