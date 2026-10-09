#!/usr/bin/env python3
"""Export one ShipLoop E2E run as Run Review documents (see ../SCHEMA.md).

  export.py RUN_DIR [--key KEY] [--name NAME] [--order N] [--out DIR]
  export.py --defaults [--live FILE] [--page-url URL] [--out DIR]
  export.py --check FILE
  export.py --docs FILE [--out DIR]
  export.py --stages [--out DIR]

RUN_DIR is an output directory of test/shiploop_e2e/run.py. The export reads only
the run's own records (metrics.json, result.json, invocation.json and the ShipLoop
run directory) and writes only under --out (default RUN_DIR/review-export):

  docs/<collection>/<id>.json  one file per document
  writes.json                  the documents as ArtifactData `set` operations
  facts.md                     plain numbers for the reviewer
  review-export.json           every document but the packets in one compact file, to commit

A missing metrics.json, timeline.json or results/ is an error naming the file
(exit 2), never an empty export. The same input gives byte-identical output.

--check FILE validates a review bundle (the shape review-export.json has: documents
keyed by collection and id) against SCHEMA.md and the review rules in SKILL.md: every
failure is listed, one per line, naming the document (exit 2); a warning is listed and
leaves the exit 0. --docs FILE checks the same bundle, then writes its documents and
writes.json under --out (default a new temporary directory) through the writer an
export uses.

--defaults writes the starting expectations and settings. With --live FILE (the page's
expectations and config documents, saved in the shape of the committed database
snapshot) it writes the defaults over that page instead, keeping what the owner wrote
there (upgrade_docs): every page revision must already be in the defaults, documents
the defaults do not name are never written, and config/page is written only when absent or when --page-url
is given: it sets config/page.artifactUrl (a page cannot read its own URL, so publish supplies it).
--stages rewrites defaults/stages.json (or DIR/stages.json) from the stage table of the sibling shiploop skill
(skills/shiploop/scripts/shiploop_stage_spec.py), the one source of every stage's purpose, exit check and readers; a
test fails when the committed file differs from what the table yields. Run it after the engine's stage table changes.
Stdlib only; no network and no model calls.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import sys
import tempfile

SKILL_ROOT = Path(__file__).resolve().parents[1]  # scripts/export.py sits one level below the skill root
DEFAULTS = SKILL_ROOT / "defaults"
SCHEMA_ID = "run-review-export/v2"
MAX_COMPACT_BYTES = 200_000
MAX_KNOWLEDGE = 40
MAX_FAILURE_LINE = 240
MAX_FIGURE_ITEMS = 6
MAX_PACKET_TEXT = 150_000  # bytes of a packet file kept in its document; a longer file is cut at a line boundary
MAX_DOC_BYTES = 256 * 1024  # the page database's limit for one serialized document
MAX_CLIP = 200  # characters of a work item title or a step task kept in the run document
MAX_SUMMARY = 300  # characters of a visit's accepted summary kept on its stage row
EXIT_CHECKS = ("script-run", "model judgement", "review loop")
FIGURE_KINDS = ("bars",)
FIGURE_TONES = ("expected", "saw", "limit")

# Stage -> phase. The phase orders match defaults/expectations.json (phase-<order>); the stage names
# are shiploop_stage_spec.STAGES, and a test checks that every stage there is listed here once.
# carry-forward ("record lessons and revise the remaining queue") runs once per work item before
# the next get-next-work-item, so it belongs to Integrate, not System test.
PHASES = (
    ("Understand", ("intake", "discovery", "research")),
    ("Specify", ("spec", "test-strategy")),
    ("Plan", ("plan", "prepare", "get-next-work-item", "step-plan")),
    ("Build", ("test-spec", "baseline", "test-author", "test-red", "implement", "test-green", "test-refine")),
    ("Prove", ("regression", "document", "skill-assess", "skill-validate", "static-checks", "verify")),
    ("Integrate", ("integrate", "integration-verify", "carry-forward")),
    ("System test", ("system-test-author", "system-test", "product-acceptance")),
    ("Release", ("release-plan", "release-check", "release", "release-verify", "operations", "handoff")),
)
# The engine renamed select-work to get-next-work-item and refuses a saved run that carries the old name, so a new run
# never needs this table: it exists only so committed historical evidence (runs of ShipLoop 1.22.0 and earlier), the page's
# database and exports of old run directories (which this exporter still re-exports) render under either name. The first
# name of a group is canonical (the engine's; PHASES lists it); the rest are history. One group, one place: STAGE_PHASE
# below and the page's stage lookup resolve a name through it, nothing else mentions the old name.
STAGE_ALIASES = (("get-next-work-item", "select-work"),)


def stage_names(stage: str) -> tuple[str, ...]:
    """Every name `stage` goes by: its alias group, or itself alone."""
    return next((group for group in STAGE_ALIASES if stage in group), (stage,))


def _with_aliases(table: dict) -> dict:
    """`table` (stage -> value) with each alias group's other names given the value of the one it lists."""
    out = dict(table)
    for group in STAGE_ALIASES:
        found = next((table[name] for name in group if name in table), None)
        if found is not None:
            out.update({name: found for name in group})
    return out


STAGE_PHASE = _with_aliases({stage: order for order, (_, stages) in enumerate(PHASES) for stage in stages})
# The inner-loop stages ShipLoop runs after `implement` (shiploop_stage_spec.INNER; a test keeps them equal). A work item
# that has any of them accepted has left implement.
AFTER_IMPLEMENT = ("test-green", "test-refine", "regression", "document", "skill-assess", "skill-validate",
                   "static-checks", "verify", "integrate", "integration-verify", "carry-forward")
# ShipLoop run status -> the page's run status. A run whose engine says `active` but whose harness record says the host is
# over is `stopped` (see build_run): the engine cannot say that, it is not running when its host goes away.
RUN_STATUS = {"active": "active", "paused": "paused", "blocked": "blocked", "halted": "failed", "done": "done"}
# What result.json says about a host that is over, for a run whose engine still reads active: it was stopped on purpose, hit its
# deadline, crashed, or ended its turn with the resume budget spent. Not "not observed": a regrade started no host.
HARNESS_ENDED = ("stopped", "timeout", "failed", "exited")
# Upload order: what the page shows first (runs and their loops), the replicas published from defaults/, then the
# review (the arc), the findings it raises and the options that resolve them, then the packets (megabytes: their own
# upload batches, last, so the page shows the run before they arrive). Every SCHEMA collection is listed.
COLLECTION_ORDER = ("runs", "backchain", "expectations", "config", "reviews", "observations", "actions", "packets")

# ---------------------------------------------------------------- the contract, as data (SCHEMA.md)
# A field spec is (type, required). Types: "string", "number", "boolean", "iso", "any-scalar",
# ("enum", values), ("list", item), ("items", {field: spec}) for a list of objects,
# ("map", value type) for an object of values. A `?` field of an item is not required.
S, N, B, ISO = "string", "number", "boolean", "iso"
BOOL_OR_UNKNOWN = "bool-or-unknown"  # true, false or the string "unknown": a fact that may not be knowable from the records
PHASE_STATES = ("done", "running", "blocked", "stopped", "none")
VERIFY_FIELDS = {"records": (N, True), "passed": (N, True), "red": (N, False), "couldNotRun": (N, False),
                 "runs": (("items", {"status": (S, True), "ran": (N, False), "failed": (N, False), "acceptedRan": (N, False)}), False),
                 "observed": (("object", {"where": (S, False), "tree12": (S, False)}), False)}
UNVERIFIED_FIELDS = {"outcome": (S, False), "reason": (S, False), "check": (S, False), "owner": (S, False), "dueStage": (S, False)}
WORKTREE_CHECKS = {"passed": (N, True), "total": (N, True)}
# R23a. The harness's closed list of endings (test/shiploop_e2e/run.py OUTCOME_CLASSES): a record of how the run ended, never a verdict.
OUTCOME_CLASSES = ("PASS", "FAILED", "BLOCKED", "STOPPED")
MAX_OUTCOME_BASIS = 400  # characters of the harness's basis kept
MAX_IDENTITY = 80  # characters of a build string kept (a hash is 12 characters; a host build is a version)
MAX_TOOLS = 12  # tool versions kept from an observed start
MAX_OVERLAP_RUNS = 30  # sibling runs listed in the overlap; the rest are counted in `runsOmitted`
MAX_AT_STOP_CHECKS = 20  # checks listed for the product at the stop; the counts always cover every check
MAX_AT_STOP_COMMAND = 160  # characters of a check's command kept (the head)
MAX_AT_STOP_OUTPUT = 240  # characters of a failing check's output kept (the tail: the harness keeps a tail too, the error is last)
NO_REASON_RECORDED = "no reason recorded"
OUTCOME_FIELDS = {"class": (("enum", OUTCOME_CLASSES), False), "basis": (S, False)}
IDENTITY_FIELDS = {"pluginSha": (S, False), "promptSha": (S, False), "hostBuild": (S, False)}
OVERLAP_RUN = {"folder": (S, True), "case": (S, False), "hosts": (("list", S), False),
               "overlappedMin": (N, True), "startedOffsetMin": (N, True)}
ENVIRONMENT_FIELDS = {
    "tools": (("map", S), False),
    "browser": (("object", {"declared": (B, True), "probed": (B, True), "reason": (S, False), "version": (S, False),
                            "targets": (("map", S), False)}), False),
    "overlap": (("object", {"basis": (S, True), "runs": (("items", OVERLAP_RUN), True), "runsOmitted": (N, False),
                            "unreadable": (("list", S), False)}), False)}
AT_STOP_CHECK = {"command": (S, True), "pass": (B, True), "returncode": (N, False), "timedOut": (B, False), "output": (S, False)}
PRODUCT_AT_STOP_FIELDS = {
    "ran": (B, True), "reason": (S, False), "engineStatus": (S, False), "engineStage": (S, False),
    "passed": (N, False), "failed": (N, False), "timedOut": (N, False), "total": (N, False),
    "checks": (("items", AT_STOP_CHECK), False)}
LEFT_BEHIND_ITEM = {"command": (S, True), "ports": (("list", N), False),
                    "where": (("enum", ("worktree", "work", "other")), True), "endedBy": (S, False)}
SCHEMA = {
    # No expectation carries a status: how an expectation stands for a run is derived by the page from the run's
    # findings and review. `clauses` ties a criterion to the S-n clauses of test/shiploop_e2e/SPEC.md.
    "expectations": {
        "kind": (("enum", ("phase", "group", "criterion")), True),
        "order": (N, False), "title": (S, False), "short": (S, False), "text": (S, False),
        "group": (S, False), "clauses": (("list", S), False),
        "revs": (("items", {"at": (ISO, True), "from": (S, True), "to": (S, True), "reason": (S, True),
                            "obs": (S, False), "option": (S, False)}), False),
        "updatedAt": (ISO, False),
    },
    # reviews/<runKey>: Claude's reading of one run. The page derives each expectation's chip from findings plus `basis`.
    "reviews": {"summary": (("list", S), False), "basis": (("map", S), False), "reviewedAt": (ISO, False)},
    "runs": {
        "key": (S, True), "name": (S, True), "order": (N, True), "release": (S, True),
        "phases": (("list", ("enum", PHASE_STATES)), True),
        "time": (S, True), "imp": (S, True),
        # refusals, glue and failures are omitted when the harness names the counter unmeasured (a host that
        # cannot see it); `unmeasured` carries the harness's reason for each such counter. Never a zero.
        "refusals": (N, False), "glue": (N, False), "unmeasured": (("map", S), False),
        # Each of these is present only when measured; otherwise `unmeasured` holds the reason, under the same name.
        "improvePasses": (N, False), "improveMin": (N, False), "calls": (N, False), "contextPeak": (N, False),
        "contextWindow": (N, False), "compactions": (N, False),
        "wallMin": (N, False), "host": (S, False), "model": (S, False), "effort": (S, False), "case": (S, False),
        # The run's `planning_review` option as state.md recorded it, text as written ("not recorded" when the key is
        # absent: never a default), and, only for the recorded value `none`, what that means for the Improve numbers.
        "planningReview": (S, False), "improveScope": (S, False),
        "status": (("enum", ("done", "active", "paused", "blocked", "failed", "stopped")), False),
        "startedAt": (ISO, False), "endedAt": (ISO, False),
        # invoked, plugin, process, shiploop, committed and checks are booleans; worktreeChecks is {passed, total} (see _worktree_checks).
        "verdicts": (("verdicts", None), False),
        # min is null when the visit has no accept stamp, the one before it has none, the stamps run backwards, or the
        # harness seeded the visit: unknown, not 0. seeded and skipped are present only when true; improve and context
        # hold only the numbers that were measured (SCHEMA.md).
        "stages": (("items", {"stage": (S, True), "outcome": (S, True), "min": (N, False), "turns": (N, False),
                              "packetBytes": (N, False), "resultBytes": (N, False), "action": (S, False),
                              "skipped": (B, False), "seeded": (B, False), "improve": (("map", N), False),
                              "context": (("map", N), False),
                              # which work item, steps-loop pass and step a visit belongs to (SCHEMA.md); packetDoc is
                              # true only when a packets/<runKey>--<action> document was written for the visit.
                              "workitem": (S, False), "loop": (N, False), "step": (S, False),
                              "packetDoc": (B, False),
                              # the stage card (SCHEMA.md "The stage card"): the accepted summary cut at MAX_SUMMARY
                              # characters, whether results/<action>.md exists, which of the CARRIED labels the packet
                              # text carried (absent when the text was unreadable or is an Improve child's packet) and
                              # whether the packet file is the Improve child's, not the producer's.
                              "summary": (S, False), "summaryTruncated": (B, False), "resultFile": (B, False),
                              "carried": (("map", B), False), "packetImprove": (B, False),
                              # an Improve child's own packet file packets/<action>-improve.md (the layout after ShipLoop 1.22.0): its
                              # size, and true when a packets document `<runKey>--<action>-improve` was written for it.
                              "improvePacketBytes": (N, False), "improvePacketDoc": (B, False),
                              # R22b: what ShipLoop's own script checks recorded for the visit (tests/<action>-verifyN.md) and
                              # the outcomes a result left unverified, each with its owner and due stage (SCHEMA.md).
                              "verify": (("object", VERIFY_FIELDS), False),
                              "unverified": (("items", UNVERIFIED_FIELDS), False)}), False),
        # The plan's work items and how each went through the steps loop, from state.md and results/ only. Absent, with
        # a reason in `unmeasured.workItems`, when the records cannot tell; stepsPlanned and stepsExecuted are absent,
        # with a reason under their own name, when any item's steps or pairing is unknown. Never a zero for those.
        "workItems": (("items", {
            "id": (S, True), "title": (S, False), "titleTruncated": (B, False),
            "origin": (("enum", ("plan", "replan", "carry-forward")), False),
            "stepPlans": (N, True), "loops": (N, True), "revises": (N, True), "repeats": (N, True),
            "implementVisits": (("map", N), True), "stepsPlanned": (N, False), "stepsExecuted": (N, False),
            "steps": (("items", {"id": (S, True), "task": (S, True), "truncated": (B, False),
                                 "action": (S, False)}), False)}), False),
        "stepsPlanned": (N, False), "stepsExecuted": (N, False),
        "knowledge": (("map", N), False),
        "failures": (("items", {"verb": (S, True), "line": (S, True)}), False),
        "evidence": (S, False),
        # Every host that ran the run (invocation.json and each invocation-resume-*.json, first seen first): a run resumed on
        # another host has two, and its calls, context peak, window and compactions are then not a measure (see unmeasured).
        "hosts": (("items", {"host": (S, True), "model": (S, False), "effort": (S, False)}), False),
        # How the run ended, from the harness's termination record and metrics.json's unaccepted tail (SCHEMA.md "How the run
        # ended"): why a stopped run stopped (`by`), the stage the engine never accepted and what it cost, the sessions this
        # invocation ran, and the earlier invocations' terminations. Present only when there is something to say.
        "ending": (("object", {
            "by": (S, False), "stage": (S, False), "action": (S, False), "unacceptedMin": (N, False),
            "unacceptedTurns": (N, False), "packetBytes": (N, False), "packetDoc": (B, False),
            "sessions": (N, False), "resumes": (N, False),
            "earlier": (("items", {"by": (S, False), "stage": (S, False)}), False)}), False),
        # A blocked run's own words: the engine's class (`blocked_by`), its status reason, the one-line headline and, when it
        # asked, the question with its options and why no default was taken. Every member is optional.
        "blocked": (("object", {
            "by": (S, False), "reason": (S, False), "headline": (S, False), "question": (S, False),
            "options": (("list", S), False), "noDefault": (S, False)}), False),
        # The listeners the harness found under the run's folder and ended (or could not): the harness's left_behind record
        # without pids, argument lists or absolute paths. `where` is worktree, work or other.
        "leftBehind": (("object", {
            "observed": (B, True), "reason": (S, False),
            "reaped": (("items", LEFT_BEHIND_ITEM), False), "survived": (("items", LEFT_BEHIND_ITEM), False)}), False),
        # R22b. How the model used its tools and the packets (a Claude run's main thread, record only): the wrapper scripts it wrote
        # around ShipLoop and how it met the packets. Absent, with `unmeasured.toolUse`, on a host the harness does not read it from.
        "toolUse": (("object", {
            "wrappers": (("items", {"name": (S, True), "runs": (N, True)}), False),
            "packets": (("object", {"files": (N, False), "bytes": (N, False), "printed": (N, False), "printedChars": (N, False),
                                    "readWhole": (N, False), "readPartial": (N, False), "shellReads": (N, False),
                                    "shellChars": (N, False)}), False)}), False),
        # R22b. The planning window of the owner's 30-minute rule, read from metrics.json's `planning` block, not recomputed:
        # its length on the engine's clock and the host's, the stage it closed at, the Improve share and the output tokens.
        "planning": (("object", {
            "closed": (B, False), "through": (S, False), "windowMin": (N, False), "hostWindowMin": (N, False),
            "improveMin": (N, False), "children": (N, False), "outputTokens": (N, False), "reasoningPct": (N, False)}), False),
        # R23a. How the harness classed the ending (a record, never a verdict), the build under test, the machine and the other runs
        # that shared it, and the case checks run in the worktree the run never returned (information only). SCHEMA.md "The run's record".
        "outcome": (("object", OUTCOME_FIELDS), False),
        "identity": (("object", IDENTITY_FIELDS), False),
        "environment": (("object", ENVIRONMENT_FIELDS), False),
        "productAtStop": (("object", PRODUCT_AT_STOP_FIELDS), False),
    },
    "backchain": {
        "run": (S, False), "loop": (S, False), "phase": (N, False), "order": (N, False), "title": (S, False),
        "stageMin": (N, False),
        # Record-only facts about the loop (SCHEMA.md): the run's `backchain_passes` option as state.md recorded it, whether
        # the last backchain-check receipt is for the loop's final candidate (true, false or "unknown"), and the
        # trivial reviews the loop's receipt required (0 on a one-pass loop).
        "backchainPasses": (S, False), "candidateMatch": (BOOL_OR_UNKNOWN, False), "trivialRequired": (N, False),
        # R22b: true on a document for a stage that ran only `shiploop backchain-check` (no Until Loop): graph checks, no passes.
        "graphCheckOnly": (B, False),
        "segments": (("items", {"label": (S, True), "min": (N, True),
                                "kind": (("enum", ("added", "wasted", "insurance", "unclear", "neutral")), True),
                                "note": (S, True), "pass": (N, False), "change": (S, False),
                                "streak": (N, False)}), False),
        "facts": (("items", {"k": (S, True), "v": (S, True)}), False),
    },
    # observations are the page's "findings" and actions its "options"; the collection names do not change.
    "observations": {
        "phase": (N, False), "criterion": (S, False),
        "kind": (("enum", ("defect", "recovered", "decision", "noise", "added", "wasted")), False),
        # run names one run key (or `any`); `runs` lists the run keys the finding applies to and overrides `run`.
        "run": (S, False), "runs": (("list", S), False),
        "status": (("enum", ("open", "fixed", "accepted", "reexpected")), False),
        "title": (S, False), "expected": (S, False), "observed": (S, False), "evidence": (S, False),
        # how an OPEN finding hits its expectation (drives the derived chip); advice is Claude's recommendation.
        "effect": (("enum", ("broken", "bent")), False), "advice": (S, False),
        # an optional structured picture of expected versus seen numbers; never markup (see _figure_problems).
        "figure": (("figure", None), False),
        "createdAt": (ISO, False),
    },
    "actions": {
        "title": (S, False), "why": (S, False), "goal": (S, False), "criterion": (S, False),
        "status": (("enum", ("open", "planned", "built", "done")), False),
        "findings": (("list", S), False),
        "kind": (("enum", ("fix-shiploop", "fix-harness", "change-expectation", "gather-evidence", "accept")), False),
        "effort": (("enum", ("S", "M", "L")), False), "recommended": (B, False), "cost": (S, False),
        "change": (("object", {"target": (("enum", ("page", "spec")), True), "to": (S, True), "reason": (S, True)}),
                   False),
        "ref": (S, False),
    },
    # config/page and config/prompt share the collection; every field is a string.
    # config/stages is the stage catalog (defaults/stages.json, SCHEMA.md "Stage catalog"), a derived replica of the engine's table.
    "config": {"title": (S, False), "artifactUrl": (S, False), "constraints": (S, False), "closing": (S, False),
               "stages": (("items", {"stage": (S, True), "purpose": (S, True),
                                     "exitCheck": (("enum", EXIT_CHECKS), True),
                                     "completeRuns": (("list", S), False),
                                     "improve": (("enum", ("always", "last-item")), False),
                                     "planningChoice": (B, False), "reads": (("list", S), True)}), False)},
    # packets/<runKey>--<action>: the text of one visit's packet file, read by the page on demand. Never in the
    # committed review-export.json (megabytes); the run directory is the record.
    # `kind` is `improve` on the document of an Improve child's packet (id <runKey>--<action>-improve) and absent on a producer's.
    "packets": {"run": (S, True), "action": (S, True), "stage": (S, False), "bytes": (N, True),
                "shownBytes": (N, False), "sha256": (S, True), "text": (S, True), "truncated": (B, False),
                "kind": (("enum", ("improve",)), False)},
}


class ExportError(Exception):
    """A run directory the exporter cannot read faithfully; the message names what is missing."""


def _type_problem(spec, value, where: str) -> list[str]:
    if spec == S:
        return [] if isinstance(value, str) else [f"{where}: expected a string"]
    if spec == N:
        ok = isinstance(value, (int, float)) and not isinstance(value, bool)
        return [] if ok else [f"{where}: expected a number"]
    if spec == B:
        return [] if isinstance(value, bool) else [f"{where}: expected a boolean"]
    if spec == ISO:
        if isinstance(value, str):
            try:
                datetime.fromisoformat(value.replace("Z", "+00:00"))
                return []
            except ValueError:
                pass
        return [f"{where}: expected an ISO date-time string"]
    if spec == BOOL_OR_UNKNOWN:
        return [] if isinstance(value, bool) or value == "unknown" else [f'{where}: expected true, false or "unknown"']
    if spec == "any-scalar":
        return [] if isinstance(value, (str, int, float)) and not isinstance(value, bool) else [
            f"{where}: expected a string or number"]
    kind, arg = spec
    if kind == "figure":
        return _figure_problems(value, where)
    if kind == "verdicts":
        if not isinstance(value, dict):
            return [f"{where}: expected an object"]
        return [p for k, v in value.items() for p in (
            _fields_problems(WORKTREE_CHECKS, v, f"{where}.{k}") if k == "worktreeChecks" and isinstance(v, dict)
            else [f"{where}.{k}: expected an object {{passed, total}}"] if k == "worktreeChecks"
            else _type_problem(B, v, f"{where}.{k}"))]
    if kind == "object":
        if not isinstance(value, dict):
            return [f"{where}: expected an object"]
        return _fields_problems(arg, value, where)
    if kind == "enum":
        return [] if value in arg else [f"{where}: {value!r} is not one of {', '.join(arg)}"]
    if kind == "list":
        if not isinstance(value, list):
            return [f"{where}: expected an array"]
        return [p for i, item in enumerate(value) for p in _type_problem(arg, item, f"{where}[{i}]")]
    if kind == "map":
        if not isinstance(value, dict):
            return [f"{where}: expected an object"]
        return [p for k, v in value.items() for p in _type_problem(arg, v, f"{where}.{k}")]
    if kind == "items":
        if not isinstance(value, list):
            return [f"{where}: expected an array"]
        problems = []
        for i, item in enumerate(value):
            if not isinstance(item, dict):
                problems.append(f"{where}[{i}]: expected an object")
                continue
            problems += _fields_problems(arg, item, f"{where}[{i}]")
        return problems
    raise ValueError(f"unknown field spec {spec!r}")


def _figure_problems(value, where: str) -> list[str]:
    """A figure is a small structured spec the page draws, never markup: {kind: "bars", items: [{label, value,
    unit?, lowerBound?, tone?}]} with 1 to MAX_FIGURE_ITEMS items, plain-string labels and non-negative numbers."""
    if not isinstance(value, dict):
        return [f"{where}: expected an object"]
    item_fields = {"label": (S, True), "value": (N, True), "unit": (S, False), "lowerBound": (B, False),
                   "tone": (("enum", FIGURE_TONES), False)}
    problems = [f"{where}: unknown field {name!r}" for name in sorted(set(value) - {"kind", "items"})]
    problems += _fields_problems({"kind": (("enum", FIGURE_KINDS), True),
                                  "items": (("items", item_fields), True)}, value, where)
    items = value.get("items")
    if isinstance(items, list):
        if not 1 <= len(items) <= MAX_FIGURE_ITEMS:
            problems.append(f"{where}.items: expected 1 to {MAX_FIGURE_ITEMS} items, got {len(items)}")
        for i, item in enumerate(items):
            if not isinstance(item, dict):
                continue
            problems += [f"{where}.items[{i}]: unknown field {name!r}" for name in sorted(set(item) - set(item_fields))]
            number = item.get("value")
            if isinstance(number, (int, float)) and not isinstance(number, bool) \
                    and not (math.isfinite(number) and number >= 0):
                problems.append(f"{where}.items[{i}].value: expected a non-negative number")
    return problems


def _fields_problems(fields: dict, doc: dict, where: str) -> list[str]:
    problems = []
    for name, (spec, required) in fields.items():
        if name not in doc:
            if required:
                problems.append(f"{where}: missing required field {name!r}")
            continue
        if doc[name] is None and not required:
            continue  # null is the same as absent for an optional field
        problems += _type_problem(spec, doc[name], f"{where}.{name}")
    return problems


def _serialized_bytes(doc: dict) -> int:
    """The size of a document as the page database counts it: compact JSON, UTF-8."""
    return len(json.dumps(doc, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))


def validate_doc(collection: str, doc) -> list[str]:
    """SCHEMA.md's required fields and types for one document ([] when it conforms)."""
    if collection not in SCHEMA:
        return [f"unknown collection {collection!r}"]
    if not isinstance(doc, dict):
        return [f"{collection}: a document must be an object"]
    problems = _fields_problems(SCHEMA[collection], doc, collection)
    if collection == "packets" and not problems and _serialized_bytes(doc) > MAX_DOC_BYTES:
        problems.append(f"packets: the serialized document is {_serialized_bytes(doc)} bytes, over the page "
                        f"database's {MAX_DOC_BYTES} limit for one document")
    return problems


def extra_fields(collection: str, doc: dict) -> list[str]:
    """Top-level fields the contract does not name (allowed; the page ignores them)."""
    return sorted(set(doc) - set(SCHEMA.get(collection, {})))


# ---------------------------------------------------------------- reading the run

STATE_FENCE = re.compile(r"```shiploop-state\n(?P<json>.*?)\n```", re.S)
NAV_ID = re.compile(r"nav-[0-9a-f]{8,32}")


def _read_json(path: Path):
    if not path.is_file():
        raise ExportError(f"missing {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as exc:
        raise ExportError(f"cannot read {path}: {exc}") from exc


def _optional_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None
    except (OSError, UnicodeError, ValueError):
        return None


def _record(path: Path) -> dict | None:
    """The JSON in a ShipLoop Markdown record's ```shiploop-state fence (None when absent or unreadable)."""
    try:
        match = STATE_FENCE.search(path.read_text(encoding="utf-8"))
        value = json.loads(match.group("json")) if match else None
    except (OSError, UnicodeError, ValueError):
        return None
    return value if isinstance(value, dict) else None


def _when(text) -> datetime | None:
    if not isinstance(text, str):
        return None
    try:
        moment = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    return moment if moment.tzinfo else moment.replace(tzinfo=timezone.utc)


def _mtime(path: Path) -> datetime:
    return datetime.fromtimestamp(path.stat().st_mtime, timezone.utc)


def _minutes(start: datetime, end: datetime) -> float:
    return (end - start).total_seconds() / 60


def find_run_dir(out: Path, named: str | None = None) -> Path:
    """The ShipLoop run directory (state.md beside timeline.json) inside a run output directory.

    Re-implements the harness's discovery (test/shiploop_e2e/run.py grade_shiploop; this module
    may not import from test/): an external workspace root `<out>/.shiploop-runs/*/run`, or a run
    kept inside the repository under `<out>/work/.shiploop*`. The run result.json names is chosen
    when it is among them, so the export describes the run the harness graded; otherwise the
    newest state.md.
    """
    patterns = (".shiploop-runs/*/run", "work/.shiploop*", "work/.shiploop*/run", "work/.shiploop*/*/run",
                "work/.shiploop*/*/*/run")
    candidates: list[Path] = []
    for pattern in patterns:
        for path in sorted(out.glob(pattern)):
            if path.is_dir() and (path / "state.md").is_file() and path not in candidates:
                candidates.append(path)
    if not candidates:
        raise ExportError(f"no ShipLoop run directory (a state.md) under {out}/.shiploop-runs/*/run "
                          f"or {out}/work/.shiploop*")
    if named:
        for path in candidates:
            if path.resolve() == Path(named).resolve():
                return path
    return max(candidates, key=lambda p: ((p / "state.md").stat().st_mtime, str(p)))


def current_stage(state: dict) -> str | None:
    """The run's effective stage, including a work item's inner-loop stage (None when done)."""
    stage = state.get("stage")
    if stage == "inner-loop":
        try:
            item = state["work_items"][state["work_index"]]["id"]
            return state["inner_loops"][item]["stage"]
        except (KeyError, IndexError, TypeError):
            return None
    return None if stage == "done" else stage


def derive_phases(stage_phases: list[int], current: int | None, status: str | None) -> list[str]:
    """One state per phase: running, blocked or stopped for the current phase, done for any other phase the run
    reached (its reached stages are all accepted once the run has moved on), none otherwise. `status` is the ShipLoop
    status, or "stopped" for a run the harness ended while its engine still read active (build_run): its current phase is
    `stopped`, not `running` (the run is not going on) and not `blocked` (the engine did not block it)."""
    reached = set(stage_phases)
    states = []
    for order in range(len(PHASES)):
        if status == "done":
            states.append("done" if order in reached else "none")
        elif order == current:
            states.append("blocked" if status in ("blocked", "halted") else "stopped" if status == "stopped" else "running")
        else:
            states.append("done" if order in reached else "none")
    return states


def _fmt_minutes(minutes: float | None) -> str:
    if minutes is None:
        return "unknown time"
    return f"{round(minutes)} min" if minutes < 120 else f"{minutes / 60:.1f} h"


def _time_text(status: str | None, wall: float | None, accepted: int, ending: dict | None = None) -> str:
    """The run header's time: how long it ran to its last accept, by status. A stopped run also says how much unaccepted
    work came after that accept when the harness measured it (`ending.unacceptedMin`), since it is not running now."""
    if not accepted:
        return "no stage accepted yet"
    spent = _fmt_minutes(wall)
    tail = (ending or {}).get("unacceptedMin")
    stopped = f"stopped after {spent}" + (f", then {_fmt_minutes(tail)} of unaccepted work" if isinstance(tail, (int, float)) else "")
    return {"done": f"done in {spent}", "active": f"running, {spent} at snapshot", "paused": f"paused after {spent}",
            "blocked": f"blocked after {spent}", "failed": f"halted after {spent}", "stopped": stopped}.get(status, spent)


def _knowledge(checkouts: list[Path]) -> tuple[dict, Path | None]:
    """Byte sizes of docs/shiploop/** in the first checkout that has it (largest first, at most 40)."""
    for root in checkouts:
        home = root / "docs" / "shiploop"
        if home.is_dir():
            sizes = {path.relative_to(root).as_posix(): path.stat().st_size
                     for path in sorted(home.rglob("*")) if path.is_file() and not path.is_symlink()}
            top = sorted(sizes.items(), key=lambda kv: (-kv[1], kv[0]))[:MAX_KNOWLEDGE]
            return dict(top), root
    return {}, None


# ---------------------------------------------------------------- Backchain loop ledger

# Digest keys a review record may carry for the candidate before and after its pass, by layout.
INPUT_KEYS = ("candidate_input_sha256", "candidate_from_sha256", "candidate_sha256_before")
OUTPUT_KEYS = ("candidate_output_sha256", "candidate_to_sha256", "candidate_sha256_after")


def _find_key(value, keys: tuple[str, ...], depth: int = 0):
    """The first string value under any of `keys` (breadth-first by key priority, three levels deep)."""
    if not isinstance(value, dict) or depth > 3:
        return None
    for key in keys:
        if isinstance(value.get(key), str):
            return value[key]
    for child in value.values():
        found = _find_key(child, keys, depth + 1)
        if found:
            return found
    return None


def _digests(record: dict) -> tuple[str | None, str | None]:
    before, after = _find_key(record, INPUT_KEYS), _find_key(record, OUTPUT_KEYS)
    identity = record.get("candidate_identity")
    if after is None and isinstance(identity, dict) and isinstance(identity.get("sha256"), str):
        after = identity["sha256"]  # a first pass may record only the candidate it left
    return before, after


def _snapshots(loop: Path) -> dict[str, Path]:
    found = {}
    for path in sorted([*loop.glob("*candidate*.json"), *loop.glob("*/*candidate*.json")]):
        if path.is_file():
            found.setdefault(hashlib.sha256(path.read_bytes()).hexdigest(), path)
    return found


def _step_diff(old: Path, new: Path) -> str | None:
    def steps(path):
        data = json.loads(path.read_text(encoding="utf-8"))
        rows = data.get("steps") if isinstance(data, dict) else None
        if not isinstance(rows, list):
            raise ValueError("no steps")
        return {str(row.get("id")): json.dumps(row, sort_keys=True) for row in rows if isinstance(row, dict)}
    try:
        before, after = steps(old), steps(new)
    except (OSError, UnicodeError, ValueError):
        return None
    changed = sum(1 for k in before.keys() & after.keys() if before[k] != after[k])
    parts = [f"{changed} step{'s' if changed != 1 else ''} changed"] if changed else []
    for label, ids in (("added", sorted(after.keys() - before.keys())), ("removed", sorted(before.keys() - after.keys()))):
        if ids:
            parts.append(f"{label} {', '.join(ids)}" if len(ids) <= 3 else f"{len(ids)} {label}")
    return ", ".join(parts) or "other fields changed"


def _reply(path: Path | None) -> tuple[int | None, str | None]:
    """(progress.trivial_streak, last_report.classification) from the Until Loop's reply to a pass's done
    callback (JSON, possibly inside captured stdout)."""
    try:
        text = path.read_text(encoding="utf-8") if path and path.is_file() else ""
        start, end = text.find("{"), text.rfind("}")
        reply = json.loads(text[start:end + 1]) if start >= 0 else {}
    except (OSError, UnicodeError, ValueError):
        return None, None
    reply = reply if isinstance(reply, dict) else {}
    progress = reply.get("progress") if isinstance(reply.get("progress"), dict) else {}
    report = reply.get("last_report") if isinstance(reply.get("last_report"), dict) else {}
    streak = progress.get("trivial_streak")
    return (streak if isinstance(streak, int) and not isinstance(streak, bool) else None,
            report.get("classification") if isinstance(report.get("classification"), str) else None)


def _passes(loop: Path) -> tuple[str | None, list[tuple[str, Path, Path | None]]]:
    """(layout, [(number, review record, done reply)]) for the two layouts the runs keep."""
    records = loop / "review-records"
    plan = sorted(((m.group(1), p) for p in records.glob("action-*-review.json")
                   if (m := re.fullmatch(r"action-(\d+)-review\.json", p.name))), key=lambda t: int(t[0]))
    if plan:
        return "action-N-review", [(n, p, loop / "pass-reports" / f"action{int(n)}-done-packet.json") for n, p in plan]
    step = sorted(((m.group(1), p) for p in records.glob("review-*.json")
                   if (m := re.fullmatch(r"review-(\d+)\.json", p.name))), key=lambda t: int(t[0]))
    if step:
        rows = []
        for n, p in step:
            corrected = records / f"review-{n}-callback-result-corrected.stdout"
            rows.append((n, p, corrected if corrected.is_file() else records / f"review-{n}-callback-result.stdout"))
        return "review-NN", rows
    return None, []


def _loop_name(directory: str) -> str:
    if NAV_ID.fullmatch(directory):  # 1.21.0: the directory is the action id; its stage names the loop when it is known
        return directory[:12]
    if "step-plan" in directory:
        return "step-plan"
    if "plan" in directory:
        return "plan"
    return directory.removeprefix("backchain-")


NOT_RECORDED = "not recorded"
HEX64 = re.compile(r"[0-9a-f]{64}")
START_RECORDS = ("until-loop-start-input.json", "until-loop-start-contract.json")


def _start_record(run_dir: Path, loop: Path) -> Path | None:
    """The loop's frozen start record: until-loop-start-input.json (older runs), until-loop-start-contract.json beside
    the receipt (1.21.0), or notes/<action>-until-start-contract.json, the name a 1.21.0 step-plan loop used."""
    for path in (*(loop / name for name in START_RECORDS), run_dir / "notes" / f"{loop.name}-until-start-contract.json"):
        if path.is_file():
            return path
    return None


def _recorded_option(state: dict, key: str) -> str:
    """A run-level option as state.md recorded it (`backchain_passes`: one, converge or none; `planning_review`: stage or
    none): the text as written, whatever else the record holds shown as it is, and "not recorded" when the key is absent.
    Never a default."""
    value = state.get(key)
    return NOT_RECORDED if value is None else value if isinstance(value, str) else json.dumps(value)


# The one value of `planning_review` whose behaviour the page may state: no Improve child starts at the planning stages
# (`PLANNING_CHOICE_STAGES` in shiploop_stage_spec.py). `stage` is the other registered value; any other value is shown
# as written and claims nothing. The sentence is the exporter's own, printed in facts.md and kept in the run document.
PLANNING_NONE = "none"
IMPROVE_SCOPE_NONE = "planning stages skipped by design (planning_review none)"


def _digest_at(record, path: tuple[str, ...], key: str) -> str | None:
    node = record
    for step in path:
        node = node.get(step) if isinstance(node, dict) else None
    value = node.get(key) if isinstance(node, dict) else None
    return value if isinstance(value, str) and HEX64.fullmatch(value) else None


def _contract_digests(record) -> tuple[str | None, str | None]:
    """(input, output) sha256 of the candidate a Backchain review record names, by the field names of Backchain's own
    contract (skills/backchain/references/convergence.md and caller-contract.md): `convergence.candidate`, which spans
    the whole loop, then the review's `candidate`, each also under `review`. A value that is not 64 hex digits
    ("unavailable" for a new draft) is no digest."""
    paths = (("convergence", "candidate"), ("review", "convergence", "candidate"), ("candidate",), ("review", "candidate"))
    found = []
    for key in ("input_sha256", "output_sha256"):
        found.append(next((d for path in paths if (d := _digest_at(record, path, key))), None))
    return found[0], found[1]


def _record_digests(run_dir: Path, loop: Path) -> tuple[str | None, str | None]:
    """(input, output) of the newest JSON record the loop kept whose candidate names an output digest: a file in the
    loop directory or notes/<action>-*.json (the host names it; the candidate and check snapshots are not records)."""
    notes = run_dir / "notes"
    paths = [p for p in [*loop.glob("*.json"), *(notes.glob(f"{loop.name}-*.json") if notes.is_dir() else [])]
             if not p.name.startswith(("candidate-", "check-")) and p.is_file()]
    for path in sorted(paths, key=lambda p: (p.stat().st_mtime, p.name), reverse=True):
        before, after = _contract_digests(_optional_json(path))
        if after:
            return before, after
    return None, None


def _last_check(folder: Path | None) -> tuple[str, bool | None] | None:
    """(candidate_sha256, ok) of the newest shiploop-backchain-check receipt (check-*.json) in a directory, newest by file
    time and then by name; None when there is none."""
    best = None
    for path in sorted(folder.glob("check-*.json")) if folder is not None and folder.is_dir() else []:
        data = _optional_json(path)
        digest = data.get("candidate_sha256") if isinstance(data, dict) else None
        if isinstance(digest, str) and HEX64.fullmatch(digest):
            key = (path.stat().st_mtime, path.name)
            if best is None or key > best[0]:
                best = (key, digest, data.get("ok") if isinstance(data.get("ok"), bool) else None)
    return best[1:] if best else None


def _candidate_match(final: str | None, last: tuple[str, bool | None] | None) -> tuple[bool | str, str]:
    """(candidateMatch, the fact's text): whether the last check receipt is for the loop's final candidate. Unknown, with
    the reason, when either digest is missing."""
    if final and last:
        ok = {True: "ok", False: "not ok"}.get(last[1], "ok not recorded")
        if final == last[0]:
            return True, f"yes: the last check receipt ({ok}) is for the loop's final candidate {final[:12]}"
        return False, (f"no: the last check receipt ({ok}) is for {last[0][:12]}, "
                       f"the loop's final candidate is {final[:12]}")
    why = [] if last else ["no backchain-check receipt for this loop"]
    if not final:
        why.append("the loop's records carry no final candidate digest (candidate.output_sha256)")
    return "unknown", "unknown: " + "; ".join(why)


def _change(loop: Path, before: str | None, after: str | None) -> str:
    """What a pass changed, from the digests of the candidate before and after it ("unknown" when either is missing)."""
    if not (before and after):
        return "unknown"
    if before == after:
        return "none"
    snapshots = _snapshots(loop)
    diff = _step_diff(snapshots[before], snapshots[after]) if before in snapshots and after in snapshots else None
    return diff or "changed"


def _owner(loop: str, start: datetime | None, text: str, actions: list[dict]) -> dict | None:
    """The accepted action whose stage ran the loop: named in the receipt or start input, else by time."""
    def inside(action):
        return start is not None and action["from"] is not None and action["from"] <= start <= action["at"]
    tokens = list(dict.fromkeys(NAV_ID.findall(text)))
    named = [a for a in actions if any(a["id"].startswith(t) for t in tokens)]
    for pool in ([a for a in named if a["stage"] == loop and inside(a)], [a for a in named if a["stage"] == loop],
                 [a for a in named if inside(a)], named if len(named) == 1 else [],
                 [a for a in actions if a["stage"] == loop and inside(a)],
                 [a for a in actions if inside(a)]):
        if pool:
            return pool[0]
    return None


def _integer_split(raw: list[float], total: int | None) -> list[int]:
    """Round each part; when a total is given, the last part absorbs the rounding so the sum is exact
    (cumulative rounding instead if that would make it negative)."""
    parts = [round(x) for x in raw]
    if total is None:
        return parts
    parts[-1] = total - sum(parts[:-1])
    if parts[-1] < 0:
        edges, running = [0], 0.0
        for x in raw:
            running += x
            edges.append(round(running))
        edges[-1] = total
        parts = [b - a for a, b in zip(edges, edges[1:])]
    return parts


def loop_doc(run_key: str, run_dir: Path, loop: Path, actions: list[dict], order: int,
             option: str = NOT_RECORDED, stage_of: dict[str, str] | None = None) -> dict:
    """One backchain/<runKey>-<loop> document. Best effort: an unreadable layout gives segments [].

    Three layouts: the two older ones under scratch/ (per-pass review records, see _passes) and 1.21.0's
    run/backchain/<action>/, where the runtime's receipt names the pass count and the host kept no per-pass record.
    `option` is the run's backchain_passes as state.md recorded it; `stage_of` maps an action id to its stage."""
    stage_of = stage_of or {}
    name = stage_of.get(loop.name) or _loop_name(loop.name)
    by_action = NAV_ID.fullmatch(loop.name) is not None  # 1.21.0: the directory is named by the action whose stage ran the loop
    receipt_path = loop / "until-loop-receipt.json"
    receipt = _optional_json(receipt_path) or {}
    start_record = _start_record(run_dir, loop)
    layout, passes = _passes(loop)
    progress = receipt.get("progress") if isinstance(receipt.get("progress"), dict) else {}
    count = progress.get("action_number")
    count = count if isinstance(count, int) and not isinstance(count, bool) and count >= 1 else None
    if layout is None and count is not None:
        layout = "receipt"
    loop_start = _mtime(start_record) if start_record else (_mtime(passes[0][1]) if passes else None)
    text = json.dumps(receipt) + (start_record.read_text(encoding="utf-8", errors="replace") if start_record else "")
    owner = (next((a for a in actions if a["id"] == loop.name), None) if by_action
             else _owner(name, loop_start, text, actions))
    required = progress.get("required_trivial_reviews")
    required = required if isinstance(required, int) and not isinstance(required, bool) and required >= 0 else None
    passes_text = str(len(passes) if passes else count) if passes or count else "unknown"
    facts = [{"k": "Passes", "v": passes_text},
             {"k": "Final status", "v": str(receipt.get("status") or "unknown")}]
    if "trivial_streak" in progress:
        facts.append({"k": "Trivial streak",
                      "v": "no trivial-streak requirement on this loop" if required == 0
                      else f"{progress.get('trivial_streak')} of {progress.get('required_trivial_reviews', '?')} required"})
    facts.append({"k": "Backchain passes option", "v": option})
    facts.append({"k": "Receipt", "v": receipt_path.relative_to(run_dir).as_posix()})
    stage = owner["stage"] if owner else stage_of.get(loop.name)
    doc = {"run": run_key, "loop": name, "phase": STAGE_PHASE.get(stage or name, 2), "order": order,
           "title": f"{name[:1].upper()}{name[1:]} loop", "stageMin": None, "segments": [], "facts": facts,
           "backchainPasses": option}
    if required is not None:
        doc["trivialRequired"] = required

    def close(final: str | None) -> dict:
        """Record whether the last check receipt is for the loop's final candidate, then hand back the document."""
        folder = loop if by_action else (run_dir / "backchain" / owner["id"] if owner else None)
        doc["candidateMatch"], said = _candidate_match(final, _last_check(folder))
        facts.insert(next(i for i, f in enumerate(facts) if f["k"] == "Receipt"), {"k": "Candidate match", "v": said})
        return doc

    if layout is None:
        facts.append({"k": "Layout", "v": "not recognized: no review-records/action-N-review.json, "
                                          "review-records/review-NN.json or progress.action_number in the receipt"})
        return close(None)
    final = None
    rows, previous_end, previous_after = [], loop_start, None
    if layout == "receipt":
        before, final = _record_digests(run_dir, loop)
        end = _mtime(receipt_path)
        report = receipt.get("last_report") if isinstance(receipt.get("last_report"), dict) else {}
        classification, exit_assessment = report.get("classification"), report.get("exit_assessment")
        recorded = (f"The loop recorded {'it' if count == 1 else 'the last pass'} as {classification}"
                    + (f"; its exit was assessed as {exit_assessment}" if isinstance(exit_assessment, str) else "") + "."
                    if isinstance(classification, str) else "")
        if loop_start is None:
            facts.append({"k": "Timing", "v": "not recorded: no until-loop-start-contract.json beside the receipt"})
        elif count == 1:
            row = {"label": "Pass 1", "kind": "unclear", "pass": 1, "change": _change(loop, before, final),
                   "note": recorded, "raw": _minutes(loop_start, end)}
            if isinstance(progress.get("trivial_streak"), int) and not isinstance(progress.get("trivial_streak"), bool):
                row["streak"] = progress["trivial_streak"]
            rows.append(row)
        else:  # the host kept no record of each pass: the loop is one span
            rows.append({"label": f"Passes 1 to {count}", "kind": "unclear", "raw": _minutes(loop_start, end),
                         "note": f"The loop kept no per-pass record, so its {count} passes are one span. {recorded}".strip()})
        previous_end = end if rows else None
    for index, (number, path, reply) in enumerate(passes, 1):
        record = _optional_json(path) or {}
        end = _mtime(path)
        before, after = _digests(record)
        before = before or previous_after
        streak, classification = _reply(reply)
        row = {"label": f"Pass {index}", "kind": "unclear", "pass": index, "change": _change(loop, before, after),
               "note": f"The loop recorded it as {classification}." if classification else "",
               "raw": _minutes(previous_end, end) if previous_end else 0.0}
        if streak is not None:
            row["streak"] = streak
        rows.append(row)
        previous_end, previous_after = end, after or previous_after
    final = final or previous_after
    if not rows:
        return close(final)
    stage_min = None
    if owner and owner["from"] is not None and loop_start is not None and owner["from"] <= loop_start \
            and previous_end <= owner["at"]:
        stage_min = round(owner["min"])
        raw = [_minutes(owner["from"], loop_start), *(r["raw"] for r in rows), _minutes(previous_end, owner["at"])]
        split = _integer_split(raw, stage_min)
        segments = [{"label": "Before the loop", "min": split[0], "kind": "neutral",
                     "note": f"From the previous accept to the loop start ({stage} stage)."}]
        segments += [dict({k: v for k, v in r.items() if k != "raw"}, min=m) for r, m in zip(rows, split[1:-1])]
        segments.append({"label": "After the loop", "min": split[-1], "kind": "neutral",
                         "note": f"From the last pass to the {stage} stage's accept."})
        facts.append({"k": "Stage", "v": f"{stage}, {stage_min} min accept to accept"})
    else:
        split = _integer_split([r["raw"] for r in rows], None)
        segments = [dict({k: v for k, v in r.items() if k != "raw"}, min=m) for r, m in zip(rows, split)]
        facts.append({"k": "Stage", "v": f"{stage}: the loop lies outside its accept window" if owner
                      else "not matched to an accepted action"})
    doc["stageMin"], doc["segments"] = stage_min, segments
    return close(final)


def find_loops(scratch: Path) -> list[Path]:
    """Directories under scratch/ (up to three levels) that hold an until-loop-receipt.json: the layout of runs before
    1.21.0, which the committed evidence files cover."""
    found = []
    for pattern in ("*/until-loop-receipt.json", "*/*/until-loop-receipt.json", "*/*/*/until-loop-receipt.json"):
        found += [p.parent for p in sorted(scratch.glob(pattern)) if p.is_file()]
    return found


def find_backchain_loops(run_dir: Path) -> list[Path]:
    """The run/backchain/<action>/ directories (1.21.0) that hold an until-loop-receipt.json. A directory with only
    backchain-check receipts is no loop, and a loop still running has no receipt yet."""
    return [p.parent for p in sorted((run_dir / "backchain").glob("*/until-loop-receipt.json")) if p.is_file()]


def find_graph_check_dirs(run_dir: Path) -> list[Path]:
    """The run/backchain/<action>/ directories that hold `shiploop backchain-check` receipts (check-*.json) and no
    until-loop-receipt.json: a stage that checked its graph and ran no Until Loop (a one-pass option). They were read as no
    loop at all, so a run whose plan was checked read "none"."""
    return [p for p in sorted((run_dir / "backchain").glob("*")) if p.is_dir() and not (p / "until-loop-receipt.json").is_file()
            and any(p.glob("check-*.json"))]


def graph_check_doc(run_key: str, run_dir: Path, folder: Path, order: int, option: str = NOT_RECORDED,
                    stage_of: dict[str, str] | None = None) -> dict:
    """The backchain/<runKey>-<stage> document for a stage that only ran `backchain-check`: no segments, `graphCheckOnly`
    true, and a fact "graph check only: N checks, last ok (complete)" read from the newest receipt (file time, then name).
    `candidateMatch` is as for a loop: whether that receipt is for the final candidate the folder's records name, which a
    folder with no loop record never does ("unknown", with the reason)."""
    name = (stage_of or {}).get(folder.name) or _loop_name(folder.name)
    receipts = []
    for path in sorted(folder.glob("check-*.json")):
        data = _optional_json(path)
        if isinstance(data, dict):
            receipts.append(((path.stat().st_mtime, path.name), data))
    receipts.sort(key=lambda t: t[0])
    last = receipts[-1][1] if receipts else {}
    ok = {True: "ok", False: "not ok"}.get(last.get("ok"), "ok not recorded")
    completion = _text(last.get("completion"))
    final = _record_digests(run_dir, folder)[1]
    match, said = _candidate_match(final, _last_check(folder))
    checks = _count(len(receipts), "check")
    return {"run": run_key, "loop": name, "phase": STAGE_PHASE.get(name, 2), "order": order,
            "title": f"{name[:1].upper()}{name[1:]} graph check", "stageMin": None, "segments": [], "graphCheckOnly": True,
            "backchainPasses": option, "candidateMatch": match,
            "facts": [{"k": "Graph check", "v": f"graph check only: {checks}, last {ok}" + (f" ({completion})" if completion else "")},
                      {"k": "Backchain passes option", "v": option}, {"k": "Candidate match", "v": said},
                      {"k": "Receipt", "v": folder.relative_to(run_dir).as_posix() + "/" + (
                          max(folder.glob("check-*.json"), key=lambda p: (p.stat().st_mtime, p.name)).name)}]}


# ---------------------------------------------------------------- the run document

def _clean_key(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "-", text).strip("-") or "run"


def _text(value) -> str | None:
    return value if isinstance(value, str) and value.strip() else None


def _no_unmeasured_message(out: Path, status) -> str:
    """Why a metrics.json with no `unmeasured` record is refused, and how to get one."""
    why = ("metrics.json has no 'unmeasured' record: it was written before the harness recorded which counters "
           "its host cannot measure, so its refusal and glue counts would be exported as measured zeros. ")
    if status == "done":
        return why + (f"Regrade the finished run (python3 test/shiploop_e2e/run.py --resume-run {out}; a finished "
                      "run starts no host), then export it again.")
    if status == "blocked":  # run.py grades a blocked run again without resuming it as if answered (SPEC S-14)
        return why + (f"Regrade the blocked run (python3 test/shiploop_e2e/run.py --resume-run {out}; a regrade "
                      "starts no host and does not resume the run), then export it again.")
    return why + (f"This run's ShipLoop status is {status or 'unknown'}, not done or blocked, so it cannot be "
                  "regraded without a host (resuming it would start one): export it after it finishes.")


def _num(value):
    """The value when it is a number (never a boolean), else None."""
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) else None


def _improve_children(run_dir: Path) -> dict[str, dict]:
    """{child: {"passes", "min"}} for each improve/<child>/ directory; each is a number or None (unknown).

    A child is named by the id of the action whose visit started it. passes is terminal.json's
    progress.action_number. min runs from improve/<child>-bind.md to improve/<child>/receipt.md by file time, so it
    is right on the original run directory (copy one with cp -p) and unknown when either file is missing or the
    times run backwards.
    """
    root = run_dir / "improve"
    found = {}
    for child in sorted(p for p in root.iterdir() if p.is_dir()) if root.is_dir() else []:
        terminal = _optional_json(child / "terminal.json")
        progress = terminal.get("progress") if isinstance(terminal, dict) else None
        passes = progress.get("action_number") if isinstance(progress, dict) else None
        bind, receipt = root / f"{child.name}-bind.md", child / "receipt.md"
        span = _minutes(_mtime(bind), _mtime(receipt)) if bind.is_file() and receipt.is_file() else None
        found[child.name] = {"passes": passes if isinstance(passes, int) and not isinstance(passes, bool)
                             and passes >= 0 else None,
                             "min": round(span, 2) if span is not None and span >= 0 else None}
    return found


def _improve_totals(children: dict[str, dict]) -> tuple[dict, dict]:
    """({improvePasses, improveMin}, {name: reason}): a sum over a child with an unknown part is itself unknown."""
    found, why = {}, {}
    for field, key, lacks in (("improvePasses", "passes", "has no terminal.json progress.action_number"),
                              ("improveMin", "min", "lacks a bind.md or receipt.md, or its times run backwards")):
        values = [child[key] for child in children.values()]
        unknown = sum(value is None for value in values)
        if unknown:
            why[field] = f"{unknown} of {len(values)} Improve children {lacks}, so the sum is unknown"
        else:
            found[field] = round(sum(values), 2)
    return found, why


def _model_measures(metrics: dict, harness: dict[str, str]) -> tuple[dict, dict[str, str]]:
    """({calls, contextPeak, contextWindow, compactions}, unmeasured) from metrics.json.

    A measure the harness did not report is absent with its reason under the run's own name: the harness's
    `model_calls` and `window_tokens` reasons become `calls` and `contextWindow`, and a peak with no figure of its
    own takes the calls' reason. When metrics.json names none, the reason says that.
    """
    tokens = metrics.get("tokens") if isinstance(metrics.get("tokens"), dict) else {}
    why = {name: reason for name, reason in harness.items() if name not in ("model_calls", "window_tokens")}
    found = {}
    for field, source, value, floor, reason in (
            ("calls", "model_calls", metrics.get("model_calls"), 1, harness.get("model_calls")),
            ("contextPeak", "tokens.input_peak", tokens.get("input_peak"), 1, harness.get("model_calls")),
            ("contextWindow", "window_tokens", metrics.get("window_tokens"), 1, harness.get("window_tokens")),
            ("compactions", "compactions", metrics.get("compactions"), 0, harness.get("compactions"))):
        if _num(value) is not None and value >= floor:
            found[field] = value
            why.pop(field, None)
        else:
            why[field] = reason or f"metrics.json has no {source} figure and names no reason"
    return found, why


NO_VISIT_CONTEXT = ("the harness's stage rows carry no per-stage context (it reads it from Claude's per-message usage and "
                    "from a Codex run's rollouts)")
NO_VISIT_CONTEXT_GROK = ("the harness does not read per-stage context from Grok's events (it does from Claude's per-message "
                         "usage and from a Codex run's rollouts)")


def no_visit_context(host: str | None) -> str:
    """Why no visit has a context, by the host that wrote the run: Grok's events carry per-call usage but the harness
    attributes it to no stage; Claude's and Codex's rows have it, so another host (or none) gets the general sentence."""
    return NO_VISIT_CONTEXT_GROK if host == "grok" else NO_VISIT_CONTEXT


def _visit_context(metrics: dict, history: list[dict], host: str | None = None) -> tuple[list[dict | None], str | None]:
    """(context per history entry, why none is shown).

    The harness's stage rows (metrics.json `stages`) carry no action id: each is built from one history entry of
    state.md, in order, plus a trailing `incomplete` row for the stage the run stopped in. So a row belongs to the
    history entry at its position, and that entry names the action. The join is used only when the rows line up
    exactly (the same count, and the same stage and outcome at every position); otherwise no visit gets a context,
    never a guess. A context holds only the figures the harness measured: calls, peak, peakPct, compactions. A row that
    counts no model call (`calls` 0) has no context: its peak is unmeasured, and "0 calls" beside it would read as a
    measurement, as it did for the visits a host had no events for."""
    rows = metrics.get("stages")
    rows = [r for r in rows if isinstance(r, dict) and not r.get("incomplete")] if isinstance(rows, list) else []
    if not any(isinstance(r.get("context"), dict) for r in rows):
        return [None] * len(history), no_visit_context(host)
    if len(rows) != len(history) or any(
            (row.get("stage"), row.get("outcome")) != (entry.get("stage") or "?", entry.get("outcome"))
            for row, entry in zip(rows, history)):
        return [None] * len(history), (f"the harness's {len(rows)} stage rows do not line up one to one with "
                                       f"state.md's {len(history)} visits, so no row is attributed")
    found = []
    for row in rows:
        figures = row.get("context") if isinstance(row.get("context"), dict) else {}
        calls = _num(figures.get("calls"))
        if calls is not None and calls < 1:
            found.append(None)
            continue
        found.append({k: figures[k] for k in ("calls", "peak", "peakPct", "compactions")
                      if _num(figures.get(k)) is not None} or None)
    return found, None if any(found) else no_visit_context(host)


def _seeded(seeded, history: list[dict]) -> tuple[set[str], str | None]:
    """(ids of the visits the harness recorded itself, why none is marked when result.json names some).

    result.json's `seeded.skipped` lists the stages the E2E seed recorded without doing them; they are the first
    visits of the history, in order. No summary text is read.
    """
    if not seeded:
        return set(), None
    names = seeded.get("skipped") if isinstance(seeded, dict) else None
    if not isinstance(names, list) or not all(isinstance(n, str) for n in names):
        return set(), "result.json's seeded.skipped is not a list of stage names"
    first = [h.get("stage") for h in history[:len(names)]]
    if first != names:
        return set(), (f"result.json says the harness seeded {', '.join(names)}, but the first {len(names)} visits "
                       f"of state.md are {', '.join(str(s) for s in first) or 'none'}")
    return {h["action"] for h in history[:len(names)] if isinstance(h.get("action"), str)}, None


# ---------------------------------------------------------------- hosts, how the run ended, blocked, left behind (R22a)

MAX_REASON = 600  # characters of a blocked run's reason, question and why-no-default kept in the run document
STOP_FILE_PATH = re.compile(r"\S*/stop\b")  # the one path the harness's stop_cause writes: the run's stop file


def _hosts(out: Path) -> list[dict]:
    """Every host that ran this run, first seen first: invocation.json, then each invocation-resume-<host>-<time>.json by
    that time. One entry per distinct (host, model, effort): a run resumed on the same host and model has one, a run resumed
    on another has two (the harness's calls, context peak, window and compactions then mix them: build_run drops them)."""
    def resumed_at(path: Path) -> tuple[int, str]:
        tail = re.search(r"-(\d+)\.json$", path.name)
        return (int(tail.group(1)) if tail else 0, path.name)
    files = [out / "invocation.json", *sorted(out.glob("invocation-resume-*.json"), key=resumed_at)]
    found: list[dict] = []
    for path in files:
        record = _optional_json(path)
        host = _text(record.get("host")) if isinstance(record, dict) else None
        if host is None:
            continue
        entry = {"host": host, **{k: v for k in ("model", "effort") if (v := _text(record.get(k)))}}
        if entry not in found:
            found.append(entry)
    return found


def _hosts_why(hosts: list[dict]) -> str:
    """The reason a figure the harness mixes across hosts is not exported: the hosts, and that a mixed figure is no measure."""
    names = ", ".join(" ".join(h[k] for k in ("host", "model") if k in h) for h in hosts)
    return (f"{len(hosts)} hosts ran this ({names}): the harness mixes their events in one figure, so it is not a measure")


def _process_status(result: dict) -> str | None:
    """The harness's word on the host process at the end of the run: termination.process_status, else process.status
    (exited, failed, stopped, timeout, or "not observed" when the run was only regraded)."""
    termination = result.get("termination") if isinstance(result.get("termination"), dict) else {}
    process = result.get("process") if isinstance(result.get("process"), dict) else {}
    status = termination.get("process_status") or process.get("status")
    return status if isinstance(status, str) else None


def _worktree_checks(result: dict) -> dict | None:
    """How many of the checks pass in the worktree, {passed, total}: the harness runs them there when the product was not
    returned (shiploop.worktree_checks), as information next to `checks`. None when it did not. Every check passing is
    `passed` equal to `total`."""
    checks = (result.get("shiploop") or {}).get("worktree_checks") if isinstance(result.get("shiploop"), dict) else None
    if not (isinstance(checks, list) and checks and all(isinstance(c, dict) for c in checks)):
        return None
    return {"passed": sum(1 for c in checks if c.get("pass") is True), "total": len(checks)}


def _where(cwd) -> str:
    """Where a listener ran: in the worktree (the product not yet returned), in the work folder (the returned result), or
    elsewhere. Read from the path's own components, so a copied run directory classifies the same; the component nearest
    the process's own directory decides when a path holds both."""
    parts = Path(cwd).parts if isinstance(cwd, str) else ()
    return next((name for name in reversed(parts) if name in ("worktree", "work")), "other")


def _left_behind(record) -> dict | None:
    """The harness's left_behind record as the run document keeps it, or None when result.json has none (a regrade, or a
    run before the harness reaped). pid, argv and cwd are dropped: a port, a command, where and how it ended say what the
    listener was; the exporter only reads this record, it never looks at a process. A table the harness could not read
    stays `observed` false with its reason, never an empty list."""
    if not isinstance(record, dict) or not isinstance(record.get("observed"), bool):
        return None

    def entries(name: str) -> list[dict]:
        found = []
        for item in record.get(name) or []:
            if not isinstance(item, dict) or not isinstance(item.get("command"), str):
                continue
            row = {"command": Path(item["command"]).name or item["command"],
                   "where": _where(item.get("cwd"))}
            ports = [p for p in item.get("ports") or [] if isinstance(p, int) and not isinstance(p, bool)]
            if ports:
                row["ports"] = ports
            if isinstance(item.get("ended_by"), str) and item["ended_by"]:
                row["endedBy"] = item["ended_by"]
            found.append(row)
        return found
    if not record["observed"]:
        reason = _text(record.get("reason"))
        return {"observed": False, **({"reason": reason[:200]} if reason else {})}
    return {"observed": True, "reaped": entries("reaped"), "survived": entries("survived")}


def _ended_by(text, process_status) -> str | None:
    """Why the harness's last session ended, in its own words: result.json termination.resume_stop ('stopped by the stop
    file', 'terminated by SIGTERM', 'run deadline spent', 'resume budget spent (3)', ...). The stop file's absolute path is
    replaced by its name, and a host that timed out or failed says so first."""
    said = STOP_FILE_PATH.sub("the stop file", " ".join(text.split())) if isinstance(text, str) and text.strip() else ""
    host = f"host {process_status}" if process_status in ("timeout", "failed") else ""
    return "; ".join(part for part in (host, said) if part) or None


def _pending_action(state: dict) -> str | None:
    """The action id of the visit the engine had issued and not accepted (state.md `action`, or the inner loop's action of
    the current work item), or None."""
    action = state.get("action")
    if state.get("stage") == "inner-loop":
        try:
            action = state["inner_loops"][state["work_items"][state["work_index"]]["id"]]["action"]
        except (KeyError, IndexError, TypeError):
            action = None
    ident = action.get("id") if isinstance(action, dict) else None
    return ident if isinstance(ident, str) and re.fullmatch(r"[A-Za-z0-9._-]+", ident) else None


def _ending(result: dict, state: dict, metrics: dict, packets: Path, ended: bool) -> dict:
    """How the run ended, from result.json's termination record and metrics.json's unaccepted tail ({} when there is
    nothing to say: a run that finished in one session, or was only regraded).

    `by` is only for a run the harness ended (`ended`: the engine read active, the host was over). `stage` is the stage the
    engine never accepted (termination.engine_unaccepted_stage) and, from the harness's `incomplete` stage row, the
    `unacceptedMin` and `unacceptedTurns` of the work after the last accept: unknown, and so absent, when the row has no
    timing or no per-call usage. `action` and `packetBytes` name the packet that was issued for it, when the file is there.
    `sessions` and `resumes` are this invocation's; `earlier` holds the terminations of the invocations before it."""
    termination = result.get("termination") if isinstance(result.get("termination"), dict) else {}
    ending: dict = {}
    if ended:
        by = _ended_by(termination.get("resume_stop"), termination.get("process_status"))
        if by:
            ending["by"] = by
    stage = _text(termination.get("engine_unaccepted_stage"))
    tail = next((r for r in metrics.get("stages") or [] if isinstance(r, dict) and r.get("incomplete")), None)
    if stage is None and ended and tail is not None:
        stage = _text(tail.get("stage"))
    if stage:
        ending["stage"] = stage
        seconds, turns = _num((tail or {}).get("seconds")), _num((tail or {}).get("turns"))
        if seconds is not None and seconds >= 0:
            ending["unacceptedMin"] = round(seconds / 60, 1)
        if turns is not None and turns >= 0:
            ending["unacceptedTurns"] = turns
        action = _pending_action(state)
        if action and (packets / f"{action}.md").is_file():
            ending["action"], ending["packetBytes"] = action, (packets / f"{action}.md").stat().st_size
    for field in ("sessions", "resumes"):
        if _num(termination.get(field)) is not None and termination[field] >= 0:
            ending[field] = termination[field]
    earlier = []
    for item in result.get("earlier_terminations") if isinstance(result.get("earlier_terminations"), list) else []:
        if isinstance(item, dict):
            row = {k: v for k, v in (("by", _ended_by(item.get("resume_stop"), item.get("process_status"))),
                                     ("stage", _text(item.get("engine_unaccepted_stage")))) if v}
            if row:
                earlier.append(row)
    if earlier:
        ending["earlier"] = earlier
    noteworthy = ended or earlier or stage or (_num(ending.get("resumes")) or 0) >= 1
    return ending if noteworthy else {}


def _blocked(state: dict, history: list[dict], results: Path) -> dict:
    """A blocked run's own words ({} when the records say nothing): the status reason of state.md (cut at MAX_REASON), and,
    when the last visit's result is the blocked one, its `blocked_by` class, `headline` and `awaiting` (the question put to a
    person, its options and why no default was taken)."""
    found: dict = {}
    reason = _text(state.get("status_reason"))
    last = history[-1] if history else {}
    body = _result_body(results, state, last.get("action")) if last.get("outcome") == "blocked" else {}
    awaiting = body.get("awaiting") if isinstance(body.get("awaiting"), dict) else {}
    if reason is None and isinstance(body.get("summary"), str):
        reason = _text(body["summary"])
    for field, value in (("by", body.get("blocked_by")), ("headline", body.get("headline")),
                         ("question", awaiting.get("question")), ("noDefault", awaiting.get("no_default"))):
        if _text(value):
            found[field] = " ".join(value.split())[:MAX_REASON if field != "headline" else 200]
    if reason:
        found["reason"] = " ".join(reason.split())[:MAX_REASON]
    options = [" ".join(o.split())[:300] for o in awaiting.get("options") or [] if _text(o)] \
        if isinstance(awaiting.get("options"), list) else []
    if options:
        found["options"] = options
    return found


# ---------------------------------------------------------------- outcome, build, environment, product at the stop (R23a)
# All four are read from result.json only, as the merged harness records them (test/shiploop_e2e/run.py, environment.py), and none
# is a verdict. A part the harness could not observe is absent here and its reason is under its own name in `unmeasured`; a result
# from before these keys has none of them and gets no note (it is not an unobserved part, it is an older record).

ABSOLUTE_PATH = re.compile(r"(?<![\w.:/~-])(?!/dev/)(?:/[^\s/'\"`;,()<>|]+){2,}")  # two or more names after a leading slash


def _line(value, limit: int = MAX_REASON, default: str | None = None) -> str | None:
    """The text on one line cut at `limit` characters, or `default` when the value is not text."""
    return " ".join(value.split())[:limit] if _text(value) else default


def _without_paths(text: str) -> str:
    """The text on one line with each absolute path (/a/b/c) replaced by its last name: no local path leaves the exporter."""
    return ABSOLUTE_PATH.sub(lambda match: match.group(0).rsplit("/", 1)[1], " ".join(text.split()))


def _tenths(seconds) -> float | None:
    """Minutes to a tenth from a number of seconds, or None for no number. Never -0.0 (a sibling that began 0.4 s earlier began 0.0)."""
    number = _num(seconds)
    return None if number is None or not math.isfinite(number) else (round(number / 60, 1) or 0.0)


def _outcome(result: dict) -> dict | None:
    """The harness's one-word ending (result.json outcome_class) with its basis: {class?, basis?} or None when the result has neither.
    A record, never a verdict. The class is one of OUTCOME_CLASSES; null (unknown) leaves it out and the basis says why, and a class
    off the list is not trusted: it is left out and named in the basis. The stop file's path is replaced by its name."""
    cls, basis = result.get("outcome_class"), _text(result.get("outcome_basis"))
    said = _without_paths(STOP_FILE_PATH.sub("the stop file", basis))[:MAX_OUTCOME_BASIS] if basis else ""
    found: dict = {}
    if isinstance(cls, str) and cls in OUTCOME_CLASSES:
        found["class"] = cls
    elif cls is not None:
        said = f"outcome class {cls!r} is not one this export knows" + (f"; {said}" if said else "")
    if said:
        found["basis"] = said
    return found or None


IDENTITY_SOURCES = (("pluginSha", "plugin_sha256"), ("promptSha", "prompt_sha256"), ("hostBuild", "host_build"))


def _identity(result: dict) -> tuple[dict, dict[str, str]]:
    """({pluginSha, promptSha, hostBuild}, {identity.<field>: why}) from result.json versions.plugin_sha256, prompt_sha256 and host_build.
    A field is present only when it is text. One the result records as null (or not as text) is unknown, with the harness's reason
    from identity_unmeasured (the plugin hash also from versions.plugin_sha256_unmeasured); one the result has no key for is from before
    the field and says nothing. A reason kept for a field that is known (a regrade's stale note) is not copied."""
    versions = result.get("versions") if isinstance(result.get("versions"), dict) else {}
    reasons = result.get("identity_unmeasured") if isinstance(result.get("identity_unmeasured"), dict) else {}
    found, why = {}, {}
    for field, key in IDENTITY_SOURCES:
        source = versions if key == "plugin_sha256" else result
        if key not in source:
            continue
        value = source[key]
        if _text(value):
            found[field] = _line(value, MAX_IDENTITY)
            continue
        reason = _line(reasons.get(key)) or (_line(versions.get("plugin_sha256_unmeasured")) if key == "plugin_sha256" else None)
        why[f"identity.{field}"] = reason or (NO_REASON_RECORDED if value is None else "recorded as something other than text")
    return found, why


def _part_reason(part) -> str:
    """Why a part of the environment record is not an observation: the harness's reason, else that it is not a record."""
    return _line(part.get("reason") if isinstance(part, dict) else None) or (
        NO_REASON_RECORDED if isinstance(part, dict) else "the result holds no record of it")


def _browser_target(record: dict) -> str:
    """What one probed target (a file: or a loopback http: page) did, in words: the page title seen, or why not."""
    if record.get("probed") is False:
        return "not probed: " + _line(record.get("reason"), default=NO_REASON_RECORDED)
    if _text(record.get("error")):
        return "not started: " + _line(record["error"])
    if record.get("title_seen") is True:
        seconds = _num(record.get("output_s"))
        return "page title seen" + (f" in {seconds} s" if seconds is not None else "")
    ended = ("interrupted before a title appeared" if record.get("interrupted") is True else
             f"the browser exited with {record.get('returncode')}" if record.get("exited") is True else "stopped at the ceiling")
    return f"no page title ({ended})"


def _start(start: dict) -> tuple[dict, dict[str, str]]:
    """The tools and the browser record of an observed start: ({tools?, browser?}, {environment.<part>: why}). The browser binary's
    path, the probe's flags and its timings are not kept; the version and what each target did are."""
    found, why = {}, {}
    tools = start.get("tools")
    unread = start.get("unread") if isinstance(start.get("unread"), dict) else {}
    if isinstance(tools, dict):
        read = {}
        for name, version in list(tools.items())[:MAX_TOOLS]:
            if _text(version):
                read[str(name)] = _line(version, MAX_IDENTITY)
            else:
                why[f"environment.tools.{name}"] = _line(unread.get(name), default=NO_REASON_RECORDED)
        if read:
            found["tools"] = read
    else:
        why["environment.tools"] = "the start record holds no tool versions"
    browser = start.get("browser")
    if isinstance(browser, dict) and isinstance(browser.get("declared"), bool) and isinstance(browser.get("probed"), bool):
        entry = {"declared": browser["declared"], "probed": browser["probed"]}
        if _text(browser.get("reason")):
            entry["reason"] = _line(browser["reason"])
        if browser["probed"]:
            if _text(browser.get("version")):
                entry["version"] = _line(browser["version"], MAX_IDENTITY)
            else:
                why["environment.browser.version"] = _line(browser.get("version_unread"), default=NO_REASON_RECORDED)
            targets = {kind: _browser_target(browser[kind]) for kind in ("file", "http") if isinstance(browser.get(kind), dict)}
            if targets:
                entry["targets"] = targets
        found["browser"] = entry
    else:
        why["environment.browser"] = "the start record holds no browser record"
    return found, why


def _overlap(overlap: dict) -> dict | None:
    """The sibling runs whose host events overlapped this run's, from an observed overlap record: {basis, runs, runsOmitted?, unreadable?}
    with seconds as minutes to a tenth, or None when the record cannot be read. The harness's basis text is kept verbatim: it says the
    seconds are neither an upper nor a lower bound. `runs` [] is a measured none (it is not that nothing else ran). A sibling whose
    entry cannot be read, or that is past MAX_OVERLAP_RUNS, is counted in `runsOmitted`, never dropped without a count."""
    basis, items = _text(overlap.get("basis")), overlap.get("runs")
    if not basis or not isinstance(items, list):
        return None
    runs = []
    for item in items:
        if not isinstance(item, dict) or not _text(item.get("folder")):
            continue
        together, offset = _tenths(item.get("overlapped_seconds")), _tenths(item.get("started_offset_seconds"))
        if together is None or offset is None:
            continue
        row = {"folder": item["folder"]}
        if _text(item.get("case")):
            row["case"] = item["case"]
        hosts = [h for h in item.get("hosts") or [] if _text(h)] if isinstance(item.get("hosts"), list) else []
        if hosts:
            row["hosts"] = hosts
        runs.append({**row, "overlappedMin": together, "startedOffsetMin": offset})
    found: dict = {"basis": _line(basis, len(basis)), "runs": runs[:MAX_OVERLAP_RUNS]}
    if len(items) > len(found["runs"]):
        found["runsOmitted"] = len(items) - len(found["runs"])
    unreadable = [n for n in overlap.get("siblings_unreadable") or [] if _text(n)] if isinstance(overlap.get("siblings_unreadable"), list) else []
    if unreadable:
        found["unreadable"] = unreadable[:MAX_OVERLAP_RUNS]
    return found


def _environment(result: dict) -> tuple[dict, dict[str, str]]:
    """(the environment object, {} when nothing was observed; {environment.<part>: why}) from result.json environment: the start's tools and browser (only an observed start),
    and the overlap with the sibling runs (only an observed one). A part the harness did not observe (a run that was only regraded has
    no start or end) is absent with the harness's reason. `hosts_used`, `environments` and `mixed_host` are not repeated: `hosts` is
    read from the launch records already. The load average and CPU count are not kept: they are the machine at one instant, not the
    run's, and the overlap is what a reader can act on."""
    record = result.get("environment")
    if "environment" not in result:
        return {}, {}  # a result from before the record: nothing to say
    if not isinstance(record, dict):
        return {}, {"environment": "result.json environment is not a record"}
    found, why = {}, {}
    for name in ("start", "end"):
        part = record.get(name)
        if not (isinstance(part, dict) and part.get("observed") is True):
            why[f"environment.{name}"] = _part_reason(part)
        elif name == "start":
            started, started_why = _start(part)
            found.update(started)
            why.update(started_why)
    overlap = record.get("overlap")
    read = _overlap(overlap) if isinstance(overlap, dict) and overlap.get("observed") is True else None
    if read is not None:
        found["overlap"] = read
    else:
        why["environment.overlap"] = _part_reason(overlap) if not (isinstance(overlap, dict) and overlap.get("observed") is True) else (
            "the overlap record has no basis or no list of runs")
    return found, why


def _product_at_stop(result: dict) -> tuple[dict | None, dict[str, str]]:
    """The case checks run in the worktree a run never returned (result.json product_at_stop): information only, never a verdict, and
    present in result.json only for a run that did not pass. {ran, reason?, engineStatus?, engineStage?} and, when they ran, the counts
    (passed, failed, timedOut, total, always over every check) and the first MAX_AT_STOP_CHECKS checks. A check passes only when its
    `pass` is true; one that timed out is neither passed nor failed. The worktree's path is not kept, local paths are cut from the
    command and output, and a record that cannot be read is absent with a reason (a run without the key says nothing)."""
    if result.get("product_at_stop") is None:
        return None, {}
    record = result["product_at_stop"]

    def unreadable(why: str):
        return None, {"productAtStop": f"result.json product_at_stop is not readable: {why}"}
    if not isinstance(record, dict) or not isinstance(record.get("ran"), bool):
        return unreadable("it is not a record with a boolean ran")
    found: dict = {"ran": record["ran"]}
    engine = record.get("engine") if isinstance(record.get("engine"), dict) else {}
    for field, key in (("engineStatus", "status"), ("engineStage", "stage")):
        if _text(engine.get(key)) and engine[key] != "unknown":
            found[field] = _line(engine[key], MAX_IDENTITY)
    if not record["ran"]:
        if _text(record.get("reason")):
            found["reason"] = _without_paths(record["reason"])[:MAX_REASON]
        return found, {}
    items = record.get("checks")
    if not (isinstance(items, list) and items and all(isinstance(i, dict) and _text(i.get("command")) for i in items)):
        return unreadable("it says the checks ran and holds no list of checks")
    checks, passed, timed_out = [], 0, 0
    for item in items:
        stopped = item.get("timed_out") is True
        ok = item.get("pass") is True and not stopped
        passed += ok
        timed_out += stopped
        row = {"command": _without_paths(item["command"])[:MAX_AT_STOP_COMMAND], "pass": ok}
        if _num(item.get("returncode")) is not None:
            row["returncode"] = item["returncode"]
        if stopped:
            row["timedOut"] = True
        if _text(item.get("output")):
            row["output"] = _without_paths(item["output"])[-MAX_AT_STOP_OUTPUT:]
        checks.append(row)
    found.update(passed=passed, failed=len(items) - passed - timed_out, timedOut=timed_out, total=len(items),
                 checks=checks[:MAX_AT_STOP_CHECKS])
    return found, {}


def _run_record(result: dict) -> tuple[dict, dict[str, str]]:
    """({outcome?, identity?, environment?, productAtStop?}, the `unmeasured` entries of the parts that are absent) from result.json."""
    fields, why = {}, {}
    outcome = _outcome(result)
    if outcome:
        fields["outcome"] = outcome
    for name, (value, reasons) in (("identity", _identity(result)), ("environment", _environment(result)),
                                   ("productAtStop", _product_at_stop(result))):
        why.update(reasons)
        if value:
            fields[name] = value
    return fields, why


# ---------------------------------------------------------------- script checks, unverified outcomes, tool use, planning (R22b)

VERIFY_FILE = re.compile(r"(?P<action>[A-Za-z0-9._-]+)-verify(?P<n>\d+)\.md")
MAX_VERIFY_RUNS = 12  # runs of one record kept on a stage row (a record lists one per command, a handful in practice)
TREE_DIGEST = re.compile(r"[0-9a-f]{12,64}")


def _verify_by_action(tests: Path) -> tuple[dict[str, dict], int]:
    """({action id: verify block}, readable-record count missed) from `tests/<action>-verifyN.md`, the checks ShipLoop itself
    ran and recorded. A visit's block counts every record of its action (`records`, `passed`, `red`: records in which a command
    ran red, which a test-red record accepts; `couldNotRun`, only when some record never reached a verdict) and keeps the
    `runs` of the last record, the one that decided it: status, tests ran, failed and accepted. `observed` is where the last
    record that names one ran its checks (release-verify: returned-result, work-area or in-place) and the first 12 digits of the
    tree. No command, no stdout, no path is copied. A record with no readable shiploop-state fence is counted unreadable."""
    groups: dict[str, list[tuple[int, dict]]] = {}
    unreadable = 0
    for path in sorted(tests.glob("*-verify*.md")) if tests.is_dir() else []:
        named = VERIFY_FILE.fullmatch(path.name)
        if not named:
            continue
        found = _record(path)
        if found is None:
            unreadable += 1
        else:
            groups.setdefault(named["action"], []).append((int(named["n"]), found))
    blocks = {}
    for action, numbered in groups.items():
        records = [r for _, r in sorted(numbered, key=lambda t: t[0])]
        block: dict = {"records": len(records), "passed": sum(1 for r in records if r.get("passed") is True),
                       "red": sum(1 for r in records if any(isinstance(x, dict) and x.get("status") == "red"
                                                            for x in r.get("runs") or []))}
        if (never := sum(1 for r in records if r.get("disposition") == "could-not-run")):
            block["couldNotRun"] = never
        runs = []
        for entry in (records[-1].get("runs") if isinstance(records[-1].get("runs"), list) else [])[:MAX_VERIFY_RUNS]:
            if isinstance(entry, dict) and isinstance(entry.get("status"), str):
                counts = entry.get("counts") if isinstance(entry.get("counts"), dict) else {}
                runs.append({"status": entry["status"], **{name: value for name, value in (
                    ("ran", counts.get("ran")), ("failed", counts.get("failed")), ("acceptedRan", entry.get("accepted_ran")))
                    if _num(value) is not None}})
        if runs:
            block["runs"] = runs
        watched = next((r["observed"] for r in reversed(records) if isinstance(r.get("observed"), dict)), None)
        if watched is not None:
            seen = {k: v for k, v in (("where", _text(watched.get("where"))),
                                      ("tree12", watched["tree"][:12] if isinstance(watched.get("tree"), str)
                                       and TREE_DIGEST.fullmatch(watched["tree"]) else None)) if v}
            if seen:
                block["observed"] = seen
        blocks[action] = block
    return blocks, unreadable


def _unverified(body: dict) -> list[dict] | None:
    """The outcomes a result left unverified, [{outcome, reason, check, owner, dueStage}] with each text cut at MAX_SUMMARY
    characters: `[]` when the result lists none (a measured "none listed"), None when it has no `unverified` key at all."""
    raw = body.get("unverified")
    if not isinstance(raw, list):
        return None
    found = []
    for item in raw:
        if isinstance(item, dict):
            row = {field: (text.strip()[:MAX_SUMMARY] + ("\u2026" if len(text.strip()) > MAX_SUMMARY else ""))
                   for field, key in (("outcome", "outcome"), ("reason", "reason"), ("check", "check"), ("owner", "owner"),
                                      ("dueStage", "due_stage")) if (text := _text(item.get(key)))}
            if row:
                found.append(row)
    return found


NO_TOOL_USE = ("metrics.json has no tool_use record: the harness reads tool use from a Claude run's tool_use blocks only, and "
               "only for a run whose events are all Claude's")


def _tool_use(metrics: dict, hosts: list[dict]) -> tuple[dict | None, str | None]:
    """(toolUse, why it is absent) from metrics.json's `tool_use`, a record the harness writes for a Claude run's main thread.
    `wrappers` are the model-written scripts that wrap a ShipLoop command and were run (basename and number of tool calls that
    ran each; `[]` is a measured none), so glue is a lower bound where one exists. `packets` is how the model met the packet
    files: the files on disk, the ShipLoop replies that printed one, the packets it Read whole or in part, and the shell
    commands that named one. Absent members stay absent."""
    use = metrics.get("tool_use")
    if not isinstance(use, dict):
        names = ", ".join(dict.fromkeys(h["host"] for h in hosts)) or "unknown"
        return None, f"{NO_TOOL_USE} (host: {names})"
    out: dict = {}
    scripts = use.get("scratch_scripts")
    if isinstance(scripts, list):
        out["wrappers"] = sorted(({"name": Path(x["path"]).name, "runs": x["runs"]} for x in scripts
                                  if isinstance(x, dict) and x.get("wraps_shiploop") is True and isinstance(x.get("path"), str)
                                  and _num(x.get("runs")) is not None), key=lambda w: (w["name"], w["runs"]))
    packets = use.get("packets") if isinstance(use.get("packets"), dict) else {}
    disk, printed = packets.get("on_disk") if isinstance(packets.get("on_disk"), dict) else {}, \
        packets.get("printed") if isinstance(packets.get("printed"), dict) else {}
    read = packets.get("read") if isinstance(packets.get("read"), dict) else {}
    tool = [r for r in read.get("read_tool") or [] if isinstance(r, dict)] if isinstance(read.get("read_tool"), list) else None
    shell = read.get("shell") if isinstance(read.get("shell"), dict) else {}
    seen = {"files": disk.get("files"), "bytes": disk.get("bytes"), "printed": printed.get("replies"),
            "printedChars": printed.get("chars"), "shellReads": shell.get("calls"), "shellChars": shell.get("chars"),
            **({"readWhole": sum(1 for r in tool if r.get("whole") is True),
                "readPartial": sum(1 for r in tool if r.get("whole") is False)} if tool is not None else {})}
    seen = {k: v for k, v in seen.items() if _num(v) is not None}
    if seen:
        out["packets"] = seen
    return out, None


def _planning(metrics: dict) -> tuple[dict, dict[str, str]]:
    """(planning, {reason name: why}) from metrics.json's `planning` block, read as the harness wrote it (the window on the
    engine's clock and the host's, the stage it closed at, the Improve share, the output tokens), never recomputed. A member
    the block holds as None stays absent with its reason: `planning` (the window), `planningHostWindow`, `planningImprove`,
    `planningTokens`. The block's per-stage seconds equal the run's accept-to-accept minutes within 3 s (the export keeps a
    tenth of a minute), and its Improve seconds run bind to accept where `improveMin` runs bind to receipt (at most 1.2 s a
    child on the 10 runs that have the block)."""
    block = metrics.get("planning")
    if not isinstance(block, dict):
        return {}, {"planning": "metrics.json has no planning block: it was written before the harness measured the planning "
                                "window (regrade the run)"}
    window = block.get("window") if isinstance(block.get("window"), dict) else {}
    why = block.get("unmeasured") if isinstance(block.get("unmeasured"), dict) else {}
    found: dict = {}
    reasons: dict[str, str] = {}
    if isinstance(window.get("closed"), bool):
        found["closed"] = window["closed"]
    if _text(window.get("through")):
        found["through"] = window["through"]
    for field, key, reason in (("windowMin", "seconds", "planning"), ("hostWindowMin", "host_seconds", "planningHostWindow")):
        if _num(window.get(key)) is not None and window[key] >= 0:
            found[field] = round(window[key] / 60, 1)
        else:
            reasons[reason] = str(why.get("window" if reason == "planning" else "host_seconds")
                                  or "the planning block gives no figure and names no reason")
    improve = block.get("improve") if isinstance(block.get("improve"), dict) else None
    if improve is not None and _num(improve.get("seconds")) is not None and improve["seconds"] >= 0:
        found["improveMin"] = round(improve["seconds"] / 60, 1)
        if _num(improve.get("children")) is not None:
            found["children"] = improve["children"]
    else:
        reasons["planningImprove"] = str(why.get("improve") or reasons.get("planning")
                                         or "the planning block gives no Improve figure and names no reason")
    tokens = block.get("tokens") if isinstance(block.get("tokens"), dict) else {}
    if _num(tokens.get("output")) is not None and tokens["output"] > 0:
        found["outputTokens"] = tokens["output"]
        if _num(tokens.get("reasoning")) is not None and tokens["reasoning"] >= 0:
            found["reasoningPct"] = round(100 * tokens["reasoning"] / tokens["output"], 1)
    else:
        reasons["planningTokens"] = str(tokens.get("unmeasured") or "the planning block gives no token figure and names no reason")
    return found, reasons


def _clip(text: str) -> tuple[str, bool]:
    """(the first MAX_CLIP characters of a work item title or a step task, whether it was cut)."""
    return (text[:MAX_CLIP], True) if len(text) > MAX_CLIP else (text, False)


def _result_body(results: Path, state: dict, action) -> dict:
    """The accepted result of one action: results/<action>.md, else state.md's `accepted` map ({} when neither has it)."""
    record = _record(results / f"{action}.md")
    body = record.get("result") if record is not None else None
    if not isinstance(body, dict):
        accepted = state.get("accepted")
        body = accepted.get(action) if isinstance(accepted, dict) else None
    return body if isinstance(body, dict) else {}


def _plan_steps(body: dict) -> list[dict] | None:
    """The [{id, task, truncated?}] a step-plan result lists (None when it lists no readable steps)."""
    raw = body.get("steps")
    if not (isinstance(raw, list) and all(isinstance(s, dict) and isinstance(s.get("id"), str)
                                          and isinstance(s.get("task"), str) for s in raw)):
        return None
    steps = []
    for entry in raw:
        task, cut = _clip(entry["task"])
        steps.append({"id": entry["id"], "task": task, **({"truncated": True} if cut else {})})
    return steps


def _produced(history: list[dict], results: Path, state: dict) -> dict[str, str]:
    """{work item id: the stage that produced it}: `plan`, `replan` (an outer stage's corrective item) or
    `carry-forward`, from the work_items of each accepted result that carries some (the first producer wins)."""
    found: dict[str, str] = {}
    for entry in history:
        stage, outcome = entry.get("stage"), entry.get("outcome")
        origin = "replan" if outcome == "replan" else stage if stage in ("plan", "carry-forward") and outcome == "done" else None
        if origin is None:
            continue
        items = _result_body(results, state, entry.get("action")).get("work_items")
        for item in items if isinstance(items, list) else []:
            if isinstance(item, dict) and isinstance(item.get("id"), str):
                found.setdefault(item["id"], origin)
    return found


def work_items(state: dict, history: list[dict], results: Path,
               seeded_ids: set[str]) -> tuple[list[dict] | None, dict[str, str], dict[int, dict]]:
    """(the run's work items, the reason for each measure that is unknown, the marks of each history row).

    Every number comes from state.md (its work_items queue and history) and the accepted results, never from
    summary text. Per item (SCHEMA.md): `stepPlans` is the item's accepted step-plan visits of any outcome; `loops` is
    the times it went through the steps loop, 1 once it has any visit plus one per accepted `revise` (each sends it back
    to step-plan); `implementVisits` counts the item's implement visits by outcome. `steps` are the steps of the latest
    accepted (done) step plan. On the inline route ShipLoop issues one implement packet per step, in order, and only a
    done visit moves on (shiploop_navigator.implement_progress): so the k-th done implement visit after that plan
    executed step k, and an unfinished plan leaves the later steps with `action` None. A visit's mark is its work item,
    its loop and, for an implement visit, the step the packet named (the plan then in force, the steps already done).
    The records cannot tell which visit ran which step on another route, or when the counts do not line up with one
    packet per step: then the item has no `stepsExecuted` and its steps no `action`, and the reason is under
    `stepsExecuted`. `workItems` is None, with its reason, when the queue or history cannot be read or the plan visit
    was recorded by the E2E seed (the work items are then the harness's)."""
    queue = state.get("work_items")
    if not isinstance(queue, list) or not all(isinstance(q, dict) and isinstance(q.get("id"), str) for q in queue):
        return None, {"workItems": "state.md has no work_items queue of {id, title}"}, {}
    if any(h.get("stage") == "plan" and h.get("action") in seeded_ids for h in history):
        return None, {"workItems": "the plan visit was recorded by the E2E seed, so the work items are the harness's "
                                   "one synthetic item, not the model's planning"}, {}
    if any("workitem" not in h for h in history):
        return None, {"workItems": "state.md history rows carry no workitem, so visits cannot be assigned to work "
                                   "items"}, {}
    route = state.get("delegation")
    inline = route == "inline"
    why_route = ("this run's delegation is ask-agent: ShipLoop issues one implement packet for the whole step plan, so "
                 "no visit is tied to a step" if route == "ask-agent" else "state.md records no delegation route")
    produced = _produced(history, results, state)
    rows_of: dict[str, list[tuple[int, dict]]] = {}
    for index, entry in enumerate(history):
        if isinstance(entry.get("workitem"), str):
            rows_of.setdefault(entry["workitem"], []).append((index, entry))
    items, marks, unknown = [], {}, {"stepsPlanned": [], "stepsExecuted": []}
    for queued in queue:
        item_id = queued["id"]
        rows = rows_of.get(item_id, [])
        title, cut = _clip(queued["title"]) if isinstance(queued.get("title"), str) else (None, False)
        counts = {name: 0 for name in ("done", "repeat", "revise", "replan", "blocked")}
        for _, entry in rows:
            if entry.get("stage") == "implement" and entry.get("outcome") in counts:
                counts[entry["outcome"]] += 1
        revises = sum(1 for _, e in rows if e.get("outcome") == "revise")
        doc: dict = {"id": item_id, "stepPlans": sum(1 for _, e in rows if e.get("stage") == "step-plan"),
                     "loops": 1 + revises if rows else 0, "revises": revises,
                     "repeats": sum(1 for _, e in rows if e.get("outcome") == "repeat"), "implementVisits": counts}
        if title is not None:
            doc["title"] = title
        if cut:
            doc["titleTruncated"] = True
        if item_id in produced:
            doc["origin"] = produced[item_id]
        # Walk the item's visits in order: the plan in force, the implement visits done under it.
        steps, executed, loop, readable, left_implement = None, [], 1, True, False
        for index, entry in rows:
            mark = {"workitem": item_id, "loop": loop}
            stage, outcome = entry.get("stage"), entry.get("outcome")
            if stage == "step-plan" and outcome == "done":
                steps = _plan_steps(_result_body(results, state, entry.get("action")))
                readable, executed, left_implement = steps is not None, [], False
            elif steps is not None:
                left_implement = left_implement or stage in AFTER_IMPLEMENT
                if stage == "implement" and inline:
                    if len(executed) < len(steps):
                        mark["step"] = steps[len(executed)]["id"]
                    if outcome == "done":
                        executed.append(entry.get("action"))
            if outcome == "revise":
                loop += 1
            marks[index] = mark
        if steps is None and not readable:
            unknown["stepsPlanned"].append(f"{item_id}: its latest step plan lists no readable steps")
            unknown["stepsExecuted"].append(f"{item_id}: its latest step plan lists no readable steps")
        else:
            steps = steps or []
            doc["stepsPlanned"] = len(steps)
            problem = None
            if not inline:
                problem = why_route
            elif len(executed) > len(steps):
                problem = (f"{len(executed)} done implement visits follow a plan of {len(steps)} steps, so one packet "
                           "per step did not hold")
            elif len(executed) < len(steps) and left_implement:
                problem = (f"it moved past implement with {len(executed)} done implement visits for {len(steps)} steps, "
                           "so one packet per step did not hold")
            if problem:
                unknown["stepsExecuted"].append(f"{item_id}: {problem}")
            else:
                doc["stepsExecuted"] = len(executed)
            doc["steps"] = [dict(step, **({} if problem else {"action": executed[k] if k < len(executed) else None}))
                            for k, step in enumerate(steps)]
        items.append(doc)
    reasons = {name: "; ".join(why) for name, why in unknown.items() if why}
    return items, reasons, marks


# What a producer packet's text carries (the tenet: context is cleared between any two stages, so a packet restates how
# its stage operates and how it is checked). One row per label of the stage card's checklist: (label, what is looked for,
# rules). A label is found when ANY rule holds; a rule holds when every one of its groups has a pattern matching a line of
# the packet text. So a rule is a tuple of groups, a group a tuple of alternative patterns: `checked` is found by the old
# pair (the Done when list AND the Improve line) or, alone, by a 'Checked by:' line (the engine prints it under the Done
# when list from ShipLoop 0.54.0 on: every producer packet of the 11 runs on disk, ShipLoop 0.54.0 to 0.58.0, has one; the old
# pair keeps the earlier runs of the committed history readable). The patterns are the lines the navigator prints
# (_goal_lines, _first_callback_lines, _result_contract_lines, _improve_line, the run rules) and were checked against the
# packets of every run on disk, ShipLoop 1.16.1 to 1.22.0 and 0.54.0 to 0.58.0: one place to change when the engine's wording does. "not found in the packet
# text" is a statement about the text, not about what the model needed.
CARRIED = (
    ("where", "the progress line 'ShipLoop navigator | <stage> | revision N'",
     (((r"^ShipLoop navigator \| \S+ \| revision \d+",),),)),
    ("purpose", "a 'Goal:' line, or the implement packet's 'Step S1 (1 of 3)' line",
     (((r"^Goal: ", r"^Step \S+ \(\d+ of \d+\)"),),)),
    ("operates", "the 'Current stage guidance:' rules or the 'Considerations for this stage:' list",
     (((r"^Current stage guidance:", r"^Considerations for this stage:"),),)),
    ("checked", "the 'Done when (' list and the 'Improve:' line that says whether a review loop follows, or a 'Checked by:' line",
     (((r"^Done when \(",), (r"^Improve: ",)),
      ((r"^Checked by:",),))),
    ("produces", "the 'Result template:' and the 'Allowed outcomes:' line",
     (((r"^Result template:",), (r"^Allowed outcomes:",)),)),
    ("recovery", "the blocked_by sentence ('A blocked result adds blocked_by' up to 1.21.0, a 'blocked: {...}' shape line "
                 "from 1.22.0) and the sentence that a problem the run can fix itself is repaired in the stage, not blocked",
     (((r"^A blocked result adds blocked_by", r'^blocked: \{"outcome": "blocked"'),
       (r"a problem this run can fix itself is repaired in this stage, not blocked",)),)),
    ("inputs", "the 'Results this stage builds on' list",
     (((r"^Results this stage builds on",),),)),
)
CARRIED_RX = tuple((label, tuple(tuple(tuple(re.compile(rx, re.M) for rx in group) for group in rule) for rule in rules))
                   for label, _, rules in CARRIED)
# Two layouts of a visit's packet files. Old (ShipLoop 1.22.0 and earlier): one file per action, rewritten at every
# printing, so a visit that started an Improve child keeps only the child's last packet, which has this line, and the
# producer's own packet is gone; such a file is not read for labels (`packetImprove`). New: the producer's packet stays
# in packets/<action>.md and an Improve child's packets go to packets/<action>-improve.md, so the producer packet is
# intact and is what `carried` reads. A visit is told by its files: a `-improve.md` beside the producer file is the new layout.
IMPROVE_PACKET = re.compile(r"^Current action: Improve the completed ", re.M)
IMPROVE_SUFFIX = "-improve"


def carried_markers(text: str) -> dict[str, bool]:
    """{label: whether the packet text carries it} for every CARRIED label (the page prints each as a tick or a cross)."""
    return {label: any(all(any(rx.search(text) for rx in group) for group in rule) for rule in rules)
            for label, rules in CARRIED_RX}


def _packet_doc(run_key: str, action: str, stage: str, path: Path, kind: str | None = None) -> tuple[dict, str] | None:
    """(the packets/<runKey>--<action> document for one packet file, the whole file's text), or None when the file
    cannot be read as UTF-8. `kind` "improve" marks the document of an Improve child's packet file.

    `bytes` and `sha256` are the whole file's. A file over MAX_PACKET_TEXT bytes keeps its first MAX_PACKET_TEXT bytes cut
    at a line boundary (a hard cut only when that part holds no newline), and one whose document would pass the page
    database's per-document limit once serialized is cut further, 10% at a time: `truncated` is then true and
    `shownBytes` says how much text the document holds."""
    try:
        raw = path.read_bytes()
        raw.decode("utf-8")
    except (OSError, UnicodeError):
        return None
    head = raw[:MAX_PACKET_TEXT]
    if len(raw) > MAX_PACKET_TEXT and b"\n" in head:
        head = head[:head.rindex(b"\n") + 1]
    text = head.decode("utf-8", errors="ignore")
    doc = {"run": run_key, "action": action, "stage": stage, "bytes": len(raw),
           "sha256": hashlib.sha256(raw).hexdigest(), "text": text, **({"kind": kind} if kind else {})}
    while _serialized_bytes(doc) > MAX_DOC_BYTES - 1024 and doc["text"]:
        keep = doc["text"][:int(len(doc["text"]) * 0.9)]
        doc["text"] = keep[:keep.rindex("\n") + 1] if "\n" in keep else keep
    shown = len(doc["text"].encode("utf-8"))
    doc["shownBytes"] = shown
    if shown < len(raw):
        doc["truncated"] = True
    return doc, raw.decode("utf-8")


def packet_docs(run_key: str, packets: Path, stages: list[dict]) -> tuple[dict[str, dict], int]:
    """({doc id: packets document}, the packet files that could not be read) for every visit that has a packet file.
    A visit with no file (skipped, seeded or never printed) gets none. The producer file `<action>.md` gives the document
    `<runKey>--<action>` and the row's `packetDoc` true, and from the whole file's text `carried` (carried_markers). An
    Improve child's file `<action>-improve.md` (new layout) gives a second document `<runKey>--<action>-improve` with `kind`
    `improve` and the row's `improvePacketDoc` true; the producer file is then intact, so `carried` is read from it. With no
    such file (old layout) a producer file that is the Improve child's packet (it has the child's first lines) is marked
    `packetImprove` instead and no label is read from it."""
    found, unreadable = {}, 0
    for row in stages:
        action = row.get("action")
        if not isinstance(action, str) or not re.fullmatch(r"[A-Za-z0-9._-]+", action):
            continue
        new_layout = "improvePacketBytes" in row
        if "packetBytes" in row:
            read = _packet_doc(run_key, action, row["stage"], packets / f"{action}.md")
            if read is None:
                unreadable += 1
            else:
                doc, text = read
                found[f"{run_key}--{action}"] = doc
                row["packetDoc"] = True
                if not new_layout and IMPROVE_PACKET.search(text):
                    row["packetImprove"] = True  # old layout: the producer labels would read false for no fault of its own
                else:
                    row["carried"] = carried_markers(text)
        if new_layout:
            read = _packet_doc(run_key, action, row["stage"], packets / f"{action}{IMPROVE_SUFFIX}.md", "improve")
            if read is None:
                unreadable += 1
            else:
                found[f"{run_key}--{action}{IMPROVE_SUFFIX}"] = read[0]
                row["improvePacketDoc"] = True
    return found, unreadable


def build_run(out: Path, key: str | None = None, name: str | None = None,
              order: int | None = None) -> tuple[dict[str, dict[str, dict]], list[str]]:
    """({collection: {id: document}}, facts.md lines) for one run output directory."""
    out = out.expanduser().resolve()
    if not out.is_dir():
        raise ExportError(f"not a directory: {out}")
    metrics = _read_json(out / "metrics.json")
    result = _optional_json(out / "result.json") or {}
    invocation = _optional_json(out / "invocation.json") or {}
    run_dir = find_run_dir(out, (result.get("shiploop") or {}).get("run_dir"))
    timeline = _read_json(run_dir / "timeline.json")
    if not isinstance(timeline, dict) or not isinstance(timeline.get("accepted"), dict):
        raise ExportError(f"{run_dir / 'timeline.json'} has no accepted map")
    results = run_dir / "results"
    if not results.is_dir():
        raise ExportError(f"missing {results}")
    state = _record(run_dir / "state.md")
    if state is None:
        raise ExportError(f"cannot read the shiploop-state record in {run_dir / 'state.md'}")
    if not isinstance(metrics.get("unmeasured"), dict):
        raise ExportError(_no_unmeasured_message(out, state.get("status")))
    unmeasured = {str(name): str(reason) for name, reason in metrics["unmeasured"].items()}

    history = [h for h in state.get("history") or [] if isinstance(h, dict)]
    started = _when(timeline.get("started"))
    stamps = {}  # action id -> (accept moment, the stamp as written)
    for action, stamp in timeline["accepted"].items():
        moment = _when(stamp)
        if moment is None:
            raise ExportError(f"{run_dir / 'timeline.json'}: accept time {stamp!r} of {action} is not ISO")
        stamps[action] = (moment, stamp)

    # One row per accepted visit, in state.md's history order (the engine's own record; timeline.json only
    # stamps it). A visit's minutes are its accept minus the accept before it (the first from the run's start),
    # so a visit with no stamp, one right after a visit with no stamp, one whose stamp is earlier than the accept
    # before it, or one the harness seeded has unknown minutes: null, never 0 and never negative.
    seeded_ids, seeded_note = _seeded(result.get("seeded"), history)
    packets = run_dir / "packets"
    issued = packets.is_dir() and any(p.is_file() for p in packets.iterdir())  # some packet exists: absence means something
    children = _improve_children(run_dir)
    verify_blocks, verify_unreadable = _verify_by_action(run_dir / "tests")
    hosts = _hosts(out)
    visit_context, visit_context_why = _visit_context(metrics, history, _text(invocation.get("host")) or _text(result.get("host")))
    if len(hosts) > 1:  # one figure over two hosts' events: not a measure, for any visit either
        visit_context, visit_context_why = [None] * len(history), _hosts_why(hosts)
    actions, stages, phases_seen = [], [], []
    from_state, unknown, stamped = [], [], []
    previous, last_phase = started, 0
    for index, entry in enumerate(history):
        action = entry.get("action")
        record = _record(results / f"{action}.md")
        if record is not None:
            body = record.get("result") if isinstance(record.get("result"), dict) else {}
            stage, outcome = record.get("stage"), record.get("outcome") or body.get("outcome")
        else:
            stage, outcome = entry.get("stage"), entry.get("outcome")
            from_state.append(action)
        stage, outcome = str(stage or "unknown"), str(outcome or "unknown")
        if stage in STAGE_PHASE:
            last_phase = STAGE_PHASE[stage]
        else:
            unknown.append(stage)
        accepted_at = stamps.get(action)
        minutes = _minutes(previous, accepted_at[0]) if previous is not None and accepted_at else None
        if action in seeded_ids or (minutes is not None and minutes < 0):  # recorded, not done / stamps run backwards
            minutes = None
        row = {"stage": stage, "outcome": outcome, "min": None if minutes is None else round(minutes, 1)}
        if isinstance(action, str):
            row["action"] = action
        for field, path in (("packetBytes", packets / f"{action}.md"), ("improvePacketBytes", packets / f"{action}{IMPROVE_SUFFIX}.md"),
                            ("resultBytes", results / f"{action}.md")):
            if path.is_file():
                row[field] = path.stat().st_size
        if isinstance(action, str):
            row["resultFile"] = (results / f"{action}.md").is_file()  # false: the accepted result is read from state.md
        said = entry.get("summary") if isinstance(entry.get("summary"), str) else (
            body.get("summary") if record is not None and isinstance(body.get("summary"), str) else "")
        if said.strip():
            row["summary"] = said.strip()[:MAX_SUMMARY]
            if len(said.strip()) > MAX_SUMMARY:
                row["summaryTruncated"] = True
        if action in seeded_ids:
            row["seeded"] = True
        elif issued and isinstance(action, str) and "packetBytes" not in row and "improvePacketBytes" not in row:
            row["skipped"] = True  # packets were issued, and none for this visit: the engine skipped it
        figures = {k: v for k, v in (children.get(action) or {}).items() if v is not None}
        if figures:
            row["improve"] = figures
        if isinstance(action, str) and action in verify_blocks:
            row["verify"] = verify_blocks[action]
        if isinstance(action, str) and (outcomes := _unverified(_result_body(results, state, action))) is not None:
            row["unverified"] = outcomes
        if visit_context[index]:
            row["context"] = visit_context[index]
        stages.append(row)
        phases_seen.append(last_phase)
        if accepted_at:
            stamped.append(accepted_at)
            actions.append({"id": action, "stage": stage, "from": previous if minutes is not None else None,
                            "at": accepted_at[0], "min": minutes})
        previous = accepted_at[0] if accepted_at else None

    raw_status = state.get("status")
    status = RUN_STATUS.get(raw_status)
    # The engine says active while it is not running when its host goes away: result.json's termination record is the
    # harness's word that the host is over (stopped on purpose, a deadline, a crash, a spent resume budget). A regrade
    # observed no process, so it never makes a run stopped (its status reads "not observed").
    ended = status == "active" and (_process_status(result) in HARNESS_ENDED)
    if ended:
        status = "stopped"
    now = current_stage(state)
    current = None if raw_status == "done" else STAGE_PHASE.get(now, phases_seen[-1] if phases_seen else 0)
    if now and now not in STAGE_PHASE and raw_status != "done":
        unknown.append(now)
    wall = _minutes(started, stamped[-1][0]) if started and stamped else None
    ending = _ending(result, state, metrics, packets, ended)

    versions = invocation.get("versions") or result.get("versions") or {}
    host = _text(invocation.get("host")) or _text(result.get("host"))
    model = _text(invocation.get("model")) or _text(result.get("model"))
    effort = _text(invocation.get("effort")) or _text(result.get("effort"))
    case = _text(invocation.get("case")) or _text(result.get("case"))
    plugin, shiploop = _text(versions.get("plugin_version")), _text(versions.get("shiploop_version"))
    release = (f"skill-craft {plugin}, ShipLoop {shiploop}" if plugin and shiploop
               else f"skill-craft {plugin}" if plugin else f"ShipLoop {shiploop}" if shiploop else "unknown")
    first = started or (stamped[0][0] if stamped else None)
    key = _clean_key(key or "-".join([host or "unknown", model or "unknown", plugin or "unknown", case or "unknown",
                                      first.strftime("%Y%m%d") if first else "undated"]))
    name = name or (" ".join(part for part in (host, model, effort) if part) or "unknown host") + \
        (f", {case}" if case else "") + (f", release {plugin}" if plugin else "")
    order = order if order is not None else (int(first.timestamp()) if first else 0)

    failures = [f for f in metrics.get("shiploop_failures") or [] if isinstance(f, dict)]
    glue = metrics.get("model_glue") or []
    improve, improve_why = _improve_totals(children)
    measures, unmeasured = _model_measures(metrics, unmeasured)
    if len(hosts) > 1:  # calls, peak, window and compactions of one host's events mixed with another's are no measure
        for field in ("calls", "contextPeak", "contextWindow", "compactions"):
            measures.pop(field, None)
            unmeasured[field] = _hosts_why(hosts)
    unmeasured.update(improve_why)
    items, plan_why, marks = work_items(state, history, results, seeded_ids)
    unmeasured.update(plan_why)
    for index, mark in marks.items():  # one stage row per history entry, in order
        stages[index].update(mark)
    if visit_context_why:  # set only when no visit has a context
        unmeasured["visitContext"] = visit_context_why
    tool_use, why_no_tool_use = _tool_use(metrics, hosts)
    if tool_use is None:
        unmeasured["toolUse"] = why_no_tool_use
    planning, planning_why = _planning(metrics)
    unmeasured.update(planning_why)
    record_fields, record_why = _run_record(result)  # R23a: outcome, identity, environment, productAtStop
    unmeasured.update(record_why)
    checkouts = [out / "work", run_dir.parent / "worktree"]
    knowledge, knowledge_root = _knowledge(checkouts if raw_status == "done" else checkouts[::-1])

    run = {"key": key, "name": name, "order": order, "release": release,
           "phases": derive_phases(phases_seen, current, "stopped" if ended else raw_status),
           "time": _time_text(status, wall, len(stages), ending),
           "imp": _count(len(children), "child", "children") + (f", {_count(improve['improvePasses'], 'review pass')}"
                                                 if improve.get("improvePasses") else ""),
           "stages": stages, "unmeasured": unmeasured, **improve, **measures,
           "knowledge": knowledge, "evidence": str(out),
           "planningReview": _recorded_option(state, "planning_review")}
    if run["planningReview"] == PLANNING_NONE:
        # The Improve totals above are what the improve/ directories hold, measured, and stay as they are. Under none the
        # engine starts no child at the five planning stages, so those stages have none by design: the scope says so.
        run["improveScope"] = IMPROVE_SCOPE_NONE
    if items is not None:
        run["workItems"] = items
        for field in ("stepsPlanned", "stepsExecuted"):  # a sum over an unknown part is unknown
            if all(field in item for item in items):
                run[field] = sum(item[field] for item in items)
    if "shiploop_failures" not in unmeasured:  # a host that cannot see the failures reports no count, not 0
        run["refusals"] = len(failures)
        run["failures"] = [{"verb": str(f.get("verb")), "line": str(f.get("line") or "")[:MAX_FAILURE_LINE]}
                           for f in failures]
    if "model_glue" not in unmeasured:
        run["glue"] = len(glue)
    for field, value in (("host", host), ("model", model), ("effort", effort), ("case", case), ("status", status),
                         ("startedAt", timeline.get("started") if started else None)):
        if value:
            run[field] = value
    if wall is not None:
        run["wallMin"] = round(wall, 1)
    if raw_status == "done" and stamped:
        run["endedAt"] = stamped[-1][1]
    verdicts = {}
    for verdict in ("invoked", "plugin", "process", "shiploop", "committed"):
        if isinstance(result.get(verdict), dict) and isinstance(result[verdict].get("pass"), bool):
            verdicts[verdict] = result[verdict]["pass"]
    if isinstance(result.get("checks"), list) and result["checks"]:
        verdicts["checks"] = all(bool(c.get("pass")) for c in result["checks"] if isinstance(c, dict))
    unreturned = _worktree_checks(result)
    if unreturned is not None:  # the product the run never returned, checked where it is: information beside `checks`
        verdicts["worktreeChecks"] = unreturned
    if verdicts:
        run["verdicts"] = verdicts
    if hosts:
        run["hosts"] = hosts
    if tool_use is not None:
        run["toolUse"] = tool_use
    if planning:
        run["planning"] = planning
    if ending:
        run["ending"] = ending
    if raw_status == "blocked" and (blocked := _blocked(state, history, results)):
        run["blocked"] = blocked
    if (left_behind := _left_behind(result.get("left_behind"))) is not None:
        run["leftBehind"] = left_behind
    run.update(record_fields)

    packet_set, unreadable = packet_docs(key, packets, stages)
    if ending.get("action"):  # the packet issued for the stage the run never accepted: a document like any visit's
        read = _packet_doc(key, ending["action"], ending["stage"], packets / f"{ending['action']}.md")
        if read is None:
            unreadable += 1
        else:
            packet_set[f"{key}--{ending['action']}"] = read[0]
            ending["packetDoc"] = True
    docs: dict[str, dict[str, dict]] = {"runs": {key: run}, "backchain": {}, "packets": packet_set}
    loops = []
    scratch = run_dir / "scratch"
    option = _recorded_option(state, "backchain_passes")
    stage_of = {row["action"]: row["stage"] for row in stages if "action" in row}
    for loop in [*(find_loops(scratch) if scratch.is_dir() else []), *find_backchain_loops(run_dir)]:
        try:
            doc = loop_doc(key, run_dir, loop, actions, 0, option, stage_of)
        except Exception as exc:  # noqa: BLE001 - the ledger is best effort and never fails the export
            doc = {"run": key, "loop": stage_of.get(loop.name) or _loop_name(loop.name), "phase": 2, "order": 0,
                   "title": f"{stage_of.get(loop.name) or _loop_name(loop.name)} loop", "stageMin": None,
                   "segments": [], "backchainPasses": option,
                   "facts": [{"k": "Ledger", "v": f"not built: {type(exc).__name__}: {exc}"}]}
        start = _start_record(run_dir, loop) or loop / "until-loop-receipt.json"
        loops.append(((start.stat().st_mtime if start.is_file() else 0.0), loop.name, doc))
    for folder in find_graph_check_dirs(run_dir):  # R22b: a stage that only checked its graph is not "no loop"
        first = min(p.stat().st_mtime for p in folder.glob("check-*.json"))
        loops.append((first, folder.name, graph_check_doc(key, run_dir, folder, 0, option, stage_of)))
    loops.sort(key=lambda t: (t[0], t[1]))
    for index, (_, _, doc) in enumerate(loops, 1):
        doc["order"] = index
        doc_id, suffix = f"{key}-{doc['loop']}", 2
        while doc_id in docs["backchain"]:
            doc_id, suffix = f"{key}-{doc['loop']}-{suffix}", suffix + 1
        docs["backchain"][doc_id] = doc

    visited = {row["action"] for row in stages if "action" in row}
    facts = _facts(run, run_dir, out, raw_status, children, failures, knowledge_root, docs["backchain"],
                   unknown, from_state, seeded_note, option, packet_set, unreadable,
                   (sum(b["records"] for a, b in verify_blocks.items() if a not in visited), verify_unreadable))
    return docs, facts


_MATCH_WORD = {True: "yes", False: "no", "unknown": "unknown"}


def _plan_line(run) -> str:
    """The run's work items and steps loop as one facts line (a measure the run lacks reads "not measured" and why)."""
    unmeasured, items = run["unmeasured"], run.get("workItems")
    if items is None:
        return f"- Work items and steps loop: not measured ({unmeasured.get('workItems', 'no reason recorded')})"
    added = sum(1 for item in items if item.get("origin") == "replan")
    done = sum(item["implementVisits"].get("done", 0) for item in items)

    def total(field, label):
        return f"{label} {run[field]}" if field in run else f"{label} not measured ({unmeasured.get(field, 'no reason recorded')})"
    return (f"- Work items: {len(items)}" + (f" ({added} added by replan)" if added else "")
            + f"; {sum(i['stepPlans'] for i in items)} step plans; {sum(i['loops'] for i in items)} passes through the "
              f"steps loop ({sum(i['revises'] for i in items)} revises); {done} done implement visits; "
            + total("stepsPlanned", "steps planned") + ", " + total("stepsExecuted", "executed"))


def _carried_line(run) -> str:
    """The packet checklist as one facts line: how many packets were read, how many are an Improve child's, and per label how
    many of the producer packets carried it."""
    rows = run["stages"]
    read = [r["carried"] for r in rows if "carried" in r]
    improve = sum(1 for r in rows if r.get("packetImprove"))
    separate = sum(1 for r in rows if "improvePacketBytes" in r)
    return (f"- Packet text carried (producer packets read {len(read)}; {separate} visits have a separate Improve packet file; "
            f"{improve} visits (old layout) keep only an Improve child's packet, not read): " + (", ".join(f"{label} {sum(1 for c in read if c.get(label))}" for label, _, _ in CARRIED)
                             if read else "no label counted"))


def _ending_lines(run) -> list[str]:
    """How the run ended, as facts lines (a line only for a part the run document has): hosts, the ending, why it is blocked,
    the listeners the harness ended and the unreturned product's checks."""
    lines = []
    hosts = run.get("hosts") or []
    if len(hosts) > 1:
        lines.append("- Hosts: " + "; ".join(" ".join(h[k] for k in ("host", "model", "effort") if k in h) for h in hosts)
                     + " (more than one: calls, context peak, window, compactions and visit context are not exported)")
    ending = run.get("ending")
    if ending:
        tail = (f"; {ending['stage']} never accepted" if "stage" in ending else "") + (
            f", {ending['unacceptedMin']} min after the last accept" if "unacceptedMin" in ending else "") + (
            f", {ending['unacceptedTurns']} turns" if "unacceptedTurns" in ending else "")
        sessions = (f"; {_count(ending['sessions'], 'session')}, {_count(ending['resumes'], 'resume')}"
                    if "sessions" in ending and "resumes" in ending else "")
        earlier = "".join(f"; earlier: {e.get('by', 'ended')}" + (f" at {e['stage']}" if "stage" in e else "")
                          for e in ending.get("earlier") or [])
        lines.append(f"- Ended: {run.get('status', 'unknown')}" + (f": {ending['by']}" if "by" in ending else "")
                     + tail + sessions + earlier)
    blocked = run.get("blocked")
    if blocked:
        lines.append("- Blocked: " + "; ".join(f"{label} {blocked[key]}" for key, label in
                                              (("by", "class"), ("headline", "headline"), ("question", "question"))
                                              if key in blocked) + (f"; {len(blocked['options'])} options"
                                                                    if blocked.get("options") else ""))
    left = run.get("leftBehind")
    if left:
        def named(item):
            return (item["command"] + "".join(f" :{p}" for p in item.get("ports") or []) + f" ({item['where']})"
                    + (f" {item['endedBy']}" if "endedBy" in item else ""))
        lines.append("- Left behind: " + (
            "; ".join([*(f"ended {named(i)}" for i in left.get("reaped") or []),
                       *(f"still running {named(i)}" for i in left.get("survived") or [])] or ["none"])
            if left["observed"] else f"not observed ({left.get('reason', 'no reason recorded')})"))
    verdicts = run.get("verdicts") or {}
    if "worktreeChecks" in verdicts:
        lines.append(f"- Checks in the worktree (product not returned): {verdicts['worktreeChecks']['passed']}/{verdicts['worktreeChecks']['total']} pass"
                     + (f"; in the work folder: {'all pass' if verdicts['checks'] else 'not all pass'}" if "checks" in verdicts else ""))
    return lines


def _measure_lines(run, verify_loose: tuple[int, int]) -> list[str]:
    """The R22b measures as facts lines: the script checks ShipLoop recorded, the unverified outcomes, the tool use and the
    planning window (a measure the run lacks reads "not measured" and why)."""
    unmeasured, rows, lines = run["unmeasured"], run["stages"], []
    checked = [r["verify"] for r in rows if "verify" in r]
    loose, unreadable = verify_loose
    lines.append((f"- Script checks (tests/<action>-verifyN.md): {_count(sum(v['records'] for v in checked), 'record')} on {_count(len(checked), 'visit')}, "
                  f"{sum(v['passed'] for v in checked)} passed, {sum(v['red'] for v in checked)} ran red"
                  + (f"; {sum(v.get('couldNotRun', 0) for v in checked)} could not run" if any("couldNotRun" in v for v in checked) else "")
                  + (f"; {_count(loose, 'record')} {'names' if loose == 1 else 'name'} an action that is no visit" if loose else "")
                  + (f"; {unreadable} unreadable" if unreadable else ""))
                 if checked or loose or unreadable else "- Script checks (tests/<action>-verifyN.md): none recorded")
    listed = [r for r in rows if "unverified" in r]
    if listed:
        lines.append("- Unverified outcomes: " + "; ".join(f"{r['stage']} {len(r['unverified'])}" for r in listed))
    use = run.get("toolUse")
    if use is None:
        lines.append(f"- Tool use: not measured ({unmeasured.get('toolUse', 'no reason recorded')})")
    else:
        wrappers = use.get("wrappers")
        packets = use.get("packets") or {}
        lines.append("- Tool use: " + ("no wrapper script" if wrappers == [] else "wrapper scripts " + ", ".join(
            f"{w['name']} {w['runs']}" for w in wrappers) if wrappers else "wrappers not recorded")
                     + "; packets " + (", ".join(f"{name} {packets[key]:,}" for key, name in (
                         ("files", "files"), ("bytes", "bytes"), ("printed", "printed"), ("printedChars", "printed chars"),
                         ("readWhole", "read whole"), ("readPartial", "read in part"), ("shellReads", "shell reads"),
                         ("shellChars", "shell chars")) if key in packets) or "not recorded"))
    plan = run.get("planning")
    if plan:
        lines.append("- Planning window: " + ", ".join(
            [f"{plan['windowMin']} min on the engine clock" if "windowMin" in plan else
             f"not measured ({unmeasured.get('planning', 'no reason recorded')})"]
            + ([f"{plan['hostWindowMin']} min on the host's"] if "hostWindowMin" in plan else [])
            + ([f"{'closed at' if plan.get('closed') else 'still open through'} {plan['through']}"] if "through" in plan else [])
            + ([f"Improve {plan['improveMin']} min over " + (_count(plan["children"], "child", "children") if "children" in plan else "? children")]
               if "improveMin" in plan else [])
            + ([f"{plan['outputTokens']:,} output tokens" + (f", {plan['reasoningPct']}% reasoning" if "reasoningPct" in plan else "")]
               if "outputTokens" in plan else [])))
    else:
        lines.append(f"- Planning window: not measured ({unmeasured.get('planning', 'no reason recorded')})")
    return lines


def _record_lines(run) -> list[str]:
    """The R23a parts as facts lines (a line only for a part the run document has; a missing build field says it is not measured and why)."""
    lines, unmeasured = [], run["unmeasured"]
    outcome = run.get("outcome")
    if outcome:
        lines.append(f"- Outcome: {outcome.get('class', 'unknown')}" + (f", {outcome['basis']}" if "basis" in outcome else ""))
    identity = run.get("identity") or {}
    if identity or any(key.startswith("identity.") for key in unmeasured):
        lines.append("- Build: " + ", ".join(
            f"{label} {identity[field]}" if field in identity else f"{label} not measured ({unmeasured.get('identity.' + field, NO_REASON_RECORDED)})"
            for field, label in (("pluginSha", "plugin"), ("promptSha", "prompt"), ("hostBuild", "host build"))
            if field in identity or f"identity.{field}" in unmeasured))
    env = run.get("environment") or {}
    parts = []
    if "tools" in env:
        parts.append("tools " + ", ".join(f"{name} {version}" for name, version in env["tools"].items()))
    browser = env.get("browser")
    if browser:
        parts.append("browser " + (
            f"{browser.get('version', 'probed')} (" + "; ".join(f"{kind} {what}" for kind, what in browser.get("targets", {}).items()) + ")"
            if browser["probed"] else ("declared, not probed" if browser["declared"] else "not declared")
            + (f": {browser['reason']}" if "reason" in browser else "")))
    overlap = env.get("overlap")
    if overlap:
        listed = ", ".join(f"{r['folder']} {r['overlappedMin']} min" for r in overlap["runs"])
        parts.append((f"ran alongside {_count(len(overlap['runs']) + overlap.get('runsOmitted', 0), 'other run')} ({listed})"
                      if overlap["runs"] else "no sibling run overlapped (host events of the sibling folders only)")
                     + "; the shared seconds are neither an upper nor a lower bound")
    gone = [f"{key[len('environment.'):]} ({reason})" for key, reason in unmeasured.items() if key.startswith("environment.") and key.count(".") == 1]
    if gone:
        parts.append("not observed: " + "; ".join(gone))
    if parts:
        lines.append("- Environment: " + "; ".join(parts))
    at_stop = run.get("productAtStop")
    if at_stop:
        position = " ".join(filter(None, (at_stop.get("engineStatus"), "at " + at_stop["engineStage"] if "engineStage" in at_stop else None)))
        if not at_stop["ran"]:
            lines.append("- At the stop (information only): the checks did not run (" + at_stop.get("reason", NO_REASON_RECORDED) + ")")
        else:
            lines.append(f"- At the stop (information only): {at_stop['passed']} of {at_stop['total']} checks pass in the unreturned worktree"
                         + (f", {at_stop['timedOut']} timed out" if at_stop["timedOut"] else "") + (f" (engine {position})" if position else ""))
            lines += [f"  - {'timed out' if c.get('timedOut') else 'failed'}: {c['command']}" + (f": {c['output']}" if "output" in c else "")
                      for c in at_stop["checks"] if not c["pass"]]
    return lines


def _facts(run, run_dir, out, raw_status, children, failures, knowledge_root, loops, unknown, from_state,
           seeded_note, option, packet_set, unreadable, verify_loose=(0, 0)) -> list[str]:
    stages = run["stages"]
    totals: dict[str, list] = {}
    for row in stages:
        if row["min"] is not None:
            totals.setdefault(row["stage"], []).append(row["min"])
    untimed = sum(1 for row in stages if row["min"] is None and not row.get("seeded"))  # a seeded visit has no time by design
    seeded, skipped = sum(1 for row in stages if row.get("seeded")), sum(1 for row in stages if row.get("skipped"))
    kinds = f" ({len(stages) - seeded - skipped} work, {skipped} skipped, {seeded} seeded)" if seeded or skipped else ""
    most = max((c["passes"] for c in children.values() if c["passes"] is not None), default=0)
    unmeasured = run["unmeasured"]
    slowest = sorted(totals.items(), key=lambda kv: (-sum(kv[1]), kv[0]))[:5]
    verbs: dict[str, int] = {}
    for failure in failures:
        verbs[str(failure.get("verb"))] = verbs.get(str(failure.get("verb")), 0) + 1
    knowledge = run["knowledge"]
    largest = next(iter(knowledge.items()), None)
    lines = [f"# Run Review facts: {run['key']}", "",
             f"- Run: ShipLoop status {raw_status or 'unknown'}; {_count(len(stages), 'accepted action')}{kinds}; "
             f"{run.get('wallMin', 'unknown')} min from start to the last accept",
             f"- Driver: {' '.join(run[k] for k in ('host', 'model', 'effort') if k in run) or 'unknown'}; "
             f"case {run.get('case', 'unknown')}; {run['release']}",
             "- Verdicts: " + (", ".join(f"{k} {v['passed']}/{v['total']}" if isinstance(v, dict) else f"{k} {'pass' if v else 'fail'}"
                                         for k, v in run["verdicts"].items())
                               if run.get("verdicts") else "no result.json"),
             "- Slowest stages (min, accept to accept): " + (", ".join(
                 f"{stage} {sum(m):.1f}" + (f" ({len(m)}x)" if len(m) > 1 else "") for stage, m in slowest) or "none"),
             f"- Phases: {', '.join(f'{title} {state}' for (title, _), state in zip(PHASES, run['phases']))}",
             f"- Improve: {run['imp']}" + (f"; most passes in one child: {most}" if most else "")
             + (f"; {run['improveMin']} min bind to receipt" if "improveMin" in run
                else f"; minutes not measured ({unmeasured['improveMin']})")
             + ("" if "improvePasses" in run else f"; passes not measured ({unmeasured['improvePasses']})")
             + (f"; {run['improveScope']}" if "improveScope" in run else ""),
             "- Model calls (main thread only): " + "; ".join(
                 f"{label} {run[field]:,}" if field in run else f"{label} not measured ({unmeasured[field]})"
                 for field, label in (("calls", "calls"), ("contextPeak", "context peak"),
                                      ("contextWindow", "window"), ("compactions", "compactions"))),
             (f"- ShipLoop command failures: {len(failures)}" + (
                 f" ({', '.join(f'{v} {n}' for v, n in sorted(verbs.items()))})" if verbs else ""))
             if "refusals" in run else
             f"- ShipLoop command failures: not measured ({run['unmeasured']['shiploop_failures']})",
             f"- Model glue: {run['glue']} commands" if "glue" in run else
             f"- Model glue: not measured ({run['unmeasured']['model_glue']})",
             f"- Planning documents: {len(knowledge)} files, {sum(knowledge.values()) / 1024:.1f} KB"
             + (f" in {knowledge_root.relative_to(out).as_posix() if knowledge_root.is_relative_to(out) else knowledge_root}"
                f"; largest {largest[0]} {largest[1] / 1024:.1f} KB" if largest else ""),
             f"- Packets {sum(r.get('packetBytes', 0) for r in stages) / 1024:.1f} KB, results "
             f"{sum(r.get('resultBytes', 0) for r in stages) / 1024:.1f} KB over {_count(len(stages), 'accepted action')}",
             _plan_line(run),
             f"- Packet documents: {len(packet_set)} written, {sum(d['bytes'] for d in packet_set.values()) / 1024:.1f} KB "
             f"of packet files, {sum(1 for d in packet_set.values() if d.get('truncated'))} truncated; "
             f"{unreadable} packet files unreadable (no document written); "
             f"{sum(1 for d in packet_set.values() if d.get('kind') == 'improve')} of the documents are an Improve child's packet",
             _carried_line(run),
             f"- Planning review option (state.md): {run['planningReview']}",
             f"- Backchain passes option (state.md): {option}",
             "- Backchain loops: " + ("; ".join(
                 f"{d['loop']}: {next(f['v'] for f in d['facts'] if f['k'] == 'Graph check')}" if d.get("graphCheckOnly") else
                 f"{d['loop']} {next((f['v'] for f in d['facts'] if f['k'] == 'Passes'), '?')} passes, "
                 f"{next((f['v'] for f in d['facts'] if f['k'] == 'Final status'), '?')}"
                 + (f", stage {d['stageMin']} min" if d.get("stageMin") is not None else "")
                 + (f", candidate match {_MATCH_WORD[d['candidateMatch']]}" if "candidateMatch" in d else "")
                 for d in loops.values()) or "none found under scratch/ or backchain/"),
             f"- Run directory: {run_dir.relative_to(out).as_posix()}"]
    lines += _ending_lines(run)
    lines += _measure_lines(run, verify_loose)
    lines += _record_lines(run)
    if untimed:
        lines.append(f"- Stages with no minutes (no accept stamp, or none on the visit before): {untimed} of "
                     f"{len(stages)}; their minutes are null, not 0")
    if unknown:
        lines.append(f"- Stages not in the phase table (shown with the previous phase): {', '.join(sorted(set(unknown)))}")
    if from_state:
        lines.append(f"- Accepted actions without a result file (stage from state.md): {len(from_state)}")
    if seeded_note:
        lines.append(f"- Seeded visits not marked: {seeded_note}")
    return lines


# ---------------------------------------------------------------- writing

def _validate_all(docs: dict[str, dict[str, dict]]) -> list[str]:
    return [f"{collection}/{doc_id}: {problem}" for collection, items in sorted(docs.items())
            for doc_id, doc in sorted(items.items()) for problem in validate_doc(collection, doc)]


def write_export(out: Path, docs: dict[str, dict[str, dict]], facts: list[str] | None = None,
                 compact: bool = True, prune_prefix: str | None = None) -> Path:
    """Validate every document, then write docs/, writes.json and (for a run) facts.md and review-export.json."""
    problems = _validate_all(docs)
    if problems:
        raise ExportError("documents violate SCHEMA.md:\n  " + "\n  ".join(problems))
    extras = [f"{c}/{i}: {', '.join(extra_fields(c, d))}" for c, items in sorted(docs.items())
              for i, d in sorted(items.items()) if extra_fields(c, d)]
    if facts is not None and extras:
        facts = [*facts, f"- Fields the contract does not name: {'; '.join(extras)}"]
    # The packets are megabytes of the run directory's own files: they are written below and uploaded, never committed.
    bundle = json.dumps({"schema": SCHEMA_ID, "docs": {c: d for c, d in docs.items() if c != "packets"}},
                        sort_keys=True, separators=(",", ":")) + "\n"
    if compact and len(bundle.encode("utf-8")) > MAX_COMPACT_BYTES:
        raise ExportError(f"review-export.json would be {len(bundle.encode('utf-8'))} bytes, over {MAX_COMPACT_BYTES}")
    out = out.expanduser().resolve()
    writes = []
    for collection in sorted(docs, key=lambda c: (COLLECTION_ORDER.index(c) if c in COLLECTION_ORDER else 99, c)):
        folder = out / "docs" / collection
        if docs[collection]:
            folder.mkdir(parents=True, exist_ok=True)
        if prune_prefix:  # an earlier export of this run may have written documents this one no longer has
            for stale in sorted(folder.glob("*.json")) if folder.is_dir() else []:
                if (stale.stem == prune_prefix or stale.stem.startswith(prune_prefix + "-")) \
                        and stale.stem not in docs[collection]:
                    stale.unlink()
        for doc_id in sorted(docs[collection]):
            path = folder / f"{doc_id}.json"
            path.write_text(json.dumps(docs[collection][doc_id], sort_keys=True, indent=1) + "\n", encoding="utf-8")
            writes.append({"op": "set", "collection": collection, "doc_id": doc_id, "file_path": str(path)})
    (out / "writes.json").write_text(json.dumps(writes, indent=1) + "\n", encoding="utf-8")
    if facts is not None:
        (out / "facts.md").write_text("\n".join(facts) + "\n", encoding="utf-8")
    if compact:
        (out / "review-export.json").write_text(bundle, encoding="utf-8")
    return out


def export_run(run_out: Path, key: str | None = None, name: str | None = None, order: int | None = None,
               out: Path | None = None) -> Path:
    """Export one run output directory; returns the export directory."""
    run_out = Path(run_out).expanduser().resolve()
    docs, facts = build_run(run_out, key, name, order)
    run_key = next(iter(docs["runs"]))
    return write_export(out or run_out / "review-export", docs, facts, compact=True, prune_prefix=run_key)


# ---------------------------------------------------------------- the stage catalog (--stages, defaults/stages.json)

ENGINE_STAGE_SPEC = SKILL_ROOT.parent / "shiploop" / "scripts" / "shiploop_stage_spec.py"
STAGES_FILE = "stages.json"
STAGES_NOTE = ("generated by export.py --stages from skills/shiploop/scripts/shiploop_stage_spec.py; "
               "do not edit by hand, a test fails on drift")


def exit_check(complete_runs, improve) -> str:
    """The kind of check that ends a stage, from its stage row's own fields (SCHEMA.md "Stage catalog").

    `script-run`: the row has `complete_runs`, so the script runs a gate or the recorded commands (lint gate, test loop,
    the focused or every test command, the quality loop's terminal check) before it accepts done. Else `review loop`:
    the row has an `improve` rule (`always`, or `last-item`), so an Improve child reviews the result before the graph
    advances. Else `model judgement`: the model decides against the row's `done_when` and nothing script-run or reviewed
    follows. A row with both is `script-run`; no row has both today (a test says so). The mode is not here: see
    effective_exit_check."""
    return "script-run" if complete_runs else "review loop" if improve else "model judgement"


def effective_exit_check(entry: dict, planning_review: str | None) -> str:
    """A catalog entry's exit check in a run that recorded `planning_review` (None or `not recorded`: the entry's own).
    Under `none` the engine starts no Improve child at the five planning stages (`planningChoice`), so a stage whose
    only check was that review is `model judgement` there; `stage`, an unknown value and no record leave it as it is."""
    if planning_review == PLANNING_NONE and entry.get("planningChoice") and entry["exitCheck"] == "review loop":
        return "model judgement"
    return entry["exitCheck"]


def load_stage_spec(path: Path | None = None):
    """The sibling shiploop skill's stage table, loaded as a module of its own (it imports nothing from ShipLoop)."""
    import importlib.util
    path = Path(path or ENGINE_STAGE_SPEC)
    if not path.is_file():
        raise ExportError(f"missing {path}: --stages reads the stage table of the shiploop skill beside this one")
    name = "run_review_engine_stage_spec"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module  # dataclasses look their module up while the class is built
    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop(name, None)
    return module


def stage_catalog(spec) -> list[dict]:
    """One entry per engine stage, in graph order, from the stage table `spec` (never hand-written): `purpose` is the
    row's goal as the engine states it, `exitCheck` is exit_check of its fields, `completeRuns` and `improve` say why
    (omitted when empty), `planningChoice` is true for the stages `planning_review none` covers, and `reads` lists the
    results the stage reads first (`item:<stage>` means this work item's). A stage's readers are the inverse of `reads`."""
    entries = []
    for name in spec.STAGES:
        row = spec.STAGE_SPEC[name]
        entry = {"stage": name, "purpose": row.goal, "exitCheck": exit_check(row.complete_runs, row.improve)}
        if row.complete_runs:
            entry["completeRuns"] = list(row.complete_runs)
        if row.improve:
            entry["improve"] = row.improve
        if name in spec.PLANNING_CHOICE_STAGES:
            entry["planningChoice"] = True
        entry["reads"] = list(row.reads)
        entries.append(entry)
    return entries


def write_stages(out: Path | None = None, spec_path: Path | None = None) -> Path:
    """Write defaults/stages.json (or OUT/stages.json) from the engine's stage table: one entry per line, so a change reads as a diff."""
    entries = stage_catalog(load_stage_spec(spec_path))
    problems = [p for e in entries for p in _type_problem(("items", SCHEMA["config"]["stages"][0][1]), [e], e["stage"])]
    if problems:
        raise ExportError("the stage catalog violates SCHEMA.md:\n  " + "\n  ".join(problems))
    target = Path(out).expanduser().resolve() if out is not None else DEFAULTS
    target.mkdir(parents=True, exist_ok=True)
    path = target / STAGES_FILE
    path.write_text('{"generated": ' + json.dumps(STAGES_NOTE) + ',\n"stages": [\n'
                    + ",\n".join(json.dumps(e, ensure_ascii=False) for e in entries) + "\n]}\n", encoding="utf-8")
    return path


def defaults_docs() -> dict[str, dict[str, dict]]:
    expectations = _read_json(DEFAULTS / "expectations.json")
    config = _read_json(DEFAULTS / "config.json")
    stages = _read_json(DEFAULTS / STAGES_FILE)
    docs: dict[str, dict[str, dict]] = {"expectations": {}, "config": {}}
    for entry in expectations:
        docs["expectations"][entry["key"]] = {k: v for k, v in entry.items() if k != "key"}
    for doc_id, doc in config.items():
        docs["config"][doc_id] = doc
    docs["config"]["stages"] = {"stages": stages["stages"]}  # the derived catalog, a replica like the expectations
    return docs


def upgrade_docs(live: dict[str, dict[str, dict]], page_url: str | None = None) -> tuple[dict[str, dict[str, dict]], list[str]]:
    """The defaults written over a page database, keeping what the owner wrote there: (documents to write, notes).

    `live` is {collection: {id: document}} as the page holds it. Each expectation the defaults name is written as the
    defaults have it (text, clauses, revs), so a stored `status` is not carried; the old `iter-*` documents and any other
    document the defaults do not name are never written, and nothing is deleted. A revision the page holds and the
    defaults lack refuses the whole upgrade (ExportError naming the document): copy the page's text and revs into
    defaults/expectations.json first, so the defaults never overwrite the owner's wording. A page text with no such
    revision that differs from the defaults is replaced, and a note names it. config/prompt is the defaults'; config/page
    holds the page's own URL and is written only when the page has none, or when `page_url` names a URL the page does
    not already hold: then the page's own document is kept and only its artifactUrl is set (a note names a URL it
    replaces)."""
    defaults = defaults_docs()
    pages = {c: {i: d for i, d in (live.get(c) or {}).items() if isinstance(d, dict)} for c in ("expectations", "config")}
    docs: dict[str, dict[str, dict]] = {"expectations": {}, "config": {}}
    notes, refused = [], []
    for key, want in defaults["expectations"].items():
        have = pages["expectations"].get(key)
        if have is not None:
            missing = [rev for rev in have.get("revs") or [] if rev not in (want.get("revs") or [])]
            if missing:
                refused.append(f"expectations/{key}: the page holds {_count(len(missing), 'revision')} the defaults lack "
                               f"(the latest at {missing[-1].get('at')}); copy the page's text and revs into "
                               f"defaults/expectations.json first")
                continue
            if have.get("text") != want.get("text"):
                notes.append(f"expectations/{key}: the page's text, which has no revision of its own, is replaced by the "
                             f"defaults' text")
        docs["expectations"][key] = want
    if refused:
        raise ExportError("the page holds wording the defaults would overwrite:\n  " + "\n  ".join(refused))
    docs["config"]["prompt"] = defaults["config"]["prompt"]
    if pages["config"].get("prompt") not in (None, docs["config"]["prompt"]):
        notes.append("config/prompt: replaced by the defaults (fields the defaults do not have are dropped)")
    docs["config"]["stages"] = defaults["config"]["stages"]  # derived from the engine's table: always the defaults'
    if pages["config"].get("stages") not in (None, docs["config"]["stages"]):
        notes.append("config/stages: replaced by the defaults (the stage catalog is derived from the engine's stage table)")
    have = pages["config"].get("page")
    if page_url is None:
        if have is None:
            docs["config"]["page"] = defaults["config"]["page"]
    elif (have or {}).get("artifactUrl") != page_url:
        if have and have.get("artifactUrl"):
            notes.append(f"config/page: artifactUrl {have['artifactUrl']} is replaced by {page_url}")
        docs["config"]["page"] = {**(have if have is not None else defaults["config"]["page"]), "artifactUrl": page_url}
    return docs, notes


def read_live(path: Path) -> dict[str, dict[str, dict]]:
    """The page's documents from a file in the shape of the committed database snapshot: {docs: {collection: {id: {data,
    version, updatedAt}}}}, as ArtifactData returns each row."""
    raw = _read_json(Path(path).expanduser())
    rows = raw.get("docs") if isinstance(raw, dict) else None
    if not isinstance(rows, dict):
        raise ExportError(f"{path}: expected {{\"docs\": {{collection: {{id: {{\"data\": document}}}}}}}}, the snapshot's shape")
    live: dict[str, dict[str, dict]] = {}
    for collection, items in rows.items():
        for doc_id, row in (items or {}).items():
            if not (isinstance(row, dict) and isinstance(row.get("data"), dict)):
                raise ExportError(f"{path}: {collection}/{doc_id} has no document under \"data\"")
            live.setdefault(collection, {})[doc_id] = row["data"]
    return live


PAGE_URL = re.compile(r"https?://\S+")


def export_defaults(out: Path | None = None, live: Path | None = None, page_url: str | None = None) -> Path:
    """The starting expectations and page settings for a new page, or with `live` (read_live) the upgrade of that page
    (upgrade_docs), whose notes are printed. `page_url` is the artifact's own URL, which only publish knows: it becomes
    config/page.artifactUrl, which the prompt's head prints as `Page:`."""
    if page_url is not None and not PAGE_URL.fullmatch(page_url):
        raise ExportError(f"--page-url {page_url!r} is not an http(s) URL")
    docs = defaults_docs()
    if live is not None:
        docs, notes = upgrade_docs(read_live(live), page_url)
        for note in notes:
            print(f"note: {note}")
    elif page_url is not None:
        docs["config"]["page"] = {**docs["config"]["page"], "artifactUrl": page_url}
    return write_export(out or Path(tempfile.gettempdir()) / "run-review-defaults", docs, compact=False)


# ---------------------------------------------------------------- a review bundle (--check, --docs)

# The rules are the ones SKILL.md lists, and no more. A failure stops a publish; a warning is listed and does not.
CLAUSE_ID = re.compile(r"S-[1-9][0-9]*")
DONE_WHEN = re.compile(r"\bDone when\b:?")
# A loose test for evidence a reader can follow: a path (rooted at / or ~, or segments of three or more characters
# around a slash, so "and/or" is not one), a file name with an extension, or a commit (seven or more hex digits
# holding a digit and a letter).
EVIDENCE_TOKEN = re.compile(
    r"(?<![\w.~/-])(?:~|\.{1,2})?/[\w.~-]+"
    r"|\b[\w.~-]{3,}(?:/[\w.~-]{3,})+"
    r"|\b[\w-]+\.(?:py|md|json|jsonl|js|cjs|html|sh|txt|toml|ya?ml|csv|log)\b"
    r"|\b(?=[0-9a-f]*[0-9])(?=[0-9a-f]*[a-f])[0-9a-f]{7,40}\b")


def _default_clauses() -> set[str]:
    return {clause for entry in _read_json(DEFAULTS / "expectations.json") for clause in entry.get("clauses") or []}


def _default_keys() -> set[str]:
    return {entry["key"] for entry in _read_json(DEFAULTS / "expectations.json")}


def _ends_with_done_when(goal: str) -> bool:
    """The instruction's last labelled part is `Done when: <condition>` (the form is in references/advice.md)."""
    last = None
    for last in DONE_WHEN.finditer(goal):
        pass
    if last is None:
        return False
    condition = goal[last.end():].strip()
    return bool(condition) and not re.search(r"(?:^|\s)(?:Do|Files and symbols|Test):", condition)


def _documents(docs: dict, collection: str) -> dict[str, dict]:
    return {i: d for i, d in (docs.get(collection) or {}).items() if isinstance(d, dict)}


def check_bundle(bundle) -> tuple[list[str], list[str]]:
    """The review rules over one bundle: (failures, warnings), a line each, each naming the document it is about.

    Failures: the schema and enums (validate_doc); every option's findings exist in the bundle; a change-expectation
    option has `change` and no other kind has one; each option's instruction (goal) ends with a Done when clause; at
    most one recommended option per finding; every `clauses` id is an S-n id that defaults/expectations.json uses; a
    finding's `criterion` and each key of a review's `basis` is a key of defaults/expectations.json (a typo would
    silently read "not examined").
    Warnings: an open finding no option names; evidence with no path or commit token; an open finding with no effect."""
    if not isinstance(bundle, dict) or not isinstance(bundle.get("docs"), dict):
        return [f'bundle: expected {{"schema": "{SCHEMA_ID}", "docs": {{collection: {{id: document}}}}}}'], []
    failures, warnings = [], []
    if bundle.get("schema") != SCHEMA_ID:
        failures.append(f"bundle: schema is {bundle.get('schema')!r}, expected {SCHEMA_ID!r}")
    docs = {}
    for collection, items in bundle["docs"].items():
        if isinstance(items, dict):
            docs[collection] = items
        else:
            failures.append(f"bundle: docs.{collection} must map document ids to documents")
    failures += _validate_all(docs)
    if docs.get("packets"):
        failures.append("bundle: packets documents are not part of a review bundle (the run directory is their record)")

    findings, options = _documents(docs, "observations"), _documents(docs, "actions")
    links = {oid: [x for x in o["findings"] if isinstance(x, str)] if isinstance(o.get("findings"), list) else []
             for oid, o in options.items()}
    recommended: dict[str, list[str]] = {}
    for oid, option in sorted(options.items()):
        where = f"actions/{oid}"
        failures += [f"{where}: findings names {fid!r}, which is not a finding in this bundle"
                     for fid in links[oid] if fid not in findings]
        kind, change = option.get("kind"), option.get("change")
        if kind == "change-expectation" and not isinstance(change, dict):
            failures.append(f"{where}: a change-expectation option needs change {{target, to, reason}}")
        if kind != "change-expectation" and change is not None:
            failures.append(f"{where}: only a change-expectation option carries change (kind is {kind or 'not set'})")
        goal = option.get("goal")
        if not (isinstance(goal, str) and _ends_with_done_when(goal)):
            failures.append(f"{where}: the instruction (goal) must end with a 'Done when: ...' clause")
        if option.get("recommended") is True:
            for fid in links[oid]:
                recommended.setdefault(fid, []).append(oid)
    failures += [f"observations/{fid}: {len(ids)} recommended options ({', '.join(ids)}); at most one"
                 for fid, ids in sorted(recommended.items()) if len(ids) > 1]
    known = _default_clauses()
    for eid, expectation in sorted(_documents(docs, "expectations").items()):
        for clause in expectation.get("clauses") if isinstance(expectation.get("clauses"), list) else []:
            if not isinstance(clause, str) or not CLAUSE_ID.fullmatch(clause):
                failures.append(f"expectations/{eid}: clause {clause!r} is not an S-n id")
            elif clause not in known:
                failures.append(f"expectations/{eid}: clause {clause} is not in defaults/expectations.json")
    keys = _default_keys()
    failures += [f"observations/{fid}: criterion {f['criterion']!r} is not a key of defaults/expectations.json"
                 for fid, f in sorted(findings.items()) if isinstance(f.get("criterion"), str) and f["criterion"]
                 and f["criterion"] not in keys]
    failures += [f"reviews/{rid}: basis names {key!r}, which is not a key of defaults/expectations.json"
                 for rid, review in sorted(_documents(docs, "reviews").items())
                 for key in (sorted(review["basis"]) if isinstance(review.get("basis"), dict) else []) if key not in keys]

    named = {fid for ids in links.values() for fid in ids}
    for fid, finding in sorted(findings.items()):
        where, is_open = f"observations/{fid}", finding.get("status") in (None, "open")
        if is_open and fid not in named:
            warnings.append(f"{where}: open finding with no option (the page shows 'no option yet')")
        evidence = finding.get("evidence")
        if isinstance(evidence, str) and evidence.strip():
            if not EVIDENCE_TOKEN.search(evidence):
                warnings.append(f"{where}: evidence has no path or commit token ({evidence.strip()[:60]!r})")
        elif is_open:
            warnings.append(f"{where}: evidence has no path or commit token (none given)")
        if is_open and finding.get("effect") is None:
            warnings.append(f"{where}: open finding with no effect (the page shows it as 'not rated')")
    return failures, warnings


def _read_bundle(path: Path):
    try:
        return json.loads(Path(path).expanduser().read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as exc:
        raise ExportError(f"cannot read the review bundle {path}: {exc}") from exc


def _count(n: int, word: str, plural: str | None = None) -> str:
    """"1 check", "2 checks", "1 review pass", "2 review passes", "1 child", "2 children" (the third argument is an irregular plural)."""
    return f"{n} " + (word if n == 1 else plural or word + ("es" if word.endswith("s") else "s"))


def check_file(path: Path) -> tuple[int, dict | None]:
    """Check one review bundle file and print the result: (exit code, the bundle when it passed)."""
    bundle = _read_bundle(path)
    failures, warnings = check_bundle(bundle)
    for line in warnings:
        print(f"warning: {line}")
    for line in failures:
        print(f"fail: {line}", file=sys.stderr)
    counts = f"{_count(len(failures), 'failure')}, {_count(len(warnings), 'warning')}"
    if failures:
        print(f"check: FAILED ({counts})", file=sys.stderr)
        return 2, None
    documents = sum(len(items) for items in bundle["docs"].values())
    print(f"check: ok ({_count(documents, 'document')}, {counts})")
    return 0, bundle


def write_docs(path: Path, out: Path | None = None) -> int:
    """Check a review bundle, then write its documents and writes.json through the writer an export uses."""
    code, bundle = check_file(path)
    if bundle is None:
        return code
    written = write_export(out or Path(tempfile.mkdtemp(prefix="run-review-docs-")), bundle["docs"], compact=False)
    print(written)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("run_dir", nargs="?", type=Path, help="a run output directory of test/shiploop_e2e/run.py")
    parser.add_argument("--defaults", action="store_true", help="export the starting expectations and settings")
    parser.add_argument("--live", type=Path, metavar="FILE",
                        help="with --defaults: the page's documents in the snapshot's shape; write the defaults over "
                             "that page, keeping its revisions (refused when the defaults lack one)")
    parser.add_argument("--page-url", metavar="URL",
                        help="with --defaults: the artifact's own URL, set as config/page.artifactUrl (the prompt's "
                             "head prints it; a page cannot read its own URL)")
    parser.add_argument("--stages", action="store_true",
                        help="rewrite defaults/stages.json (or OUT/stages.json with --out) from the shiploop skill's stage table")
    parser.add_argument("--check", type=Path, metavar="FILE", help="validate a review bundle (exit 2 on a failure)")
    parser.add_argument("--docs", type=Path, metavar="FILE",
                        help="check a review bundle, then write its documents and writes.json under --out")
    parser.add_argument("--key", help="the runs document id (default <host>-<model>-<release>-<case>-<yyyymmdd>)")
    parser.add_argument("--name", help="the run's display name")
    parser.add_argument("--order", type=int, help="sort key (default the run's start, epoch seconds)")
    parser.add_argument("--out", type=Path, help="export directory (default RUN_DIR/review-export; for --docs a new temporary directory)")
    args = parser.parse_args(argv)
    if [args.run_dir is not None, args.defaults, args.stages, args.check is not None, args.docs is not None].count(True) != 1:
        parser.error("give one of RUN_DIR, --defaults, --stages, --check FILE or --docs FILE")
    if args.live is not None and not args.defaults:
        parser.error("--live goes with --defaults")
    if args.page_url is not None and not args.defaults:
        parser.error("--page-url goes with --defaults")
    try:
        if args.check is not None:
            return check_file(args.check)[0]
        if args.docs is not None:
            return write_docs(args.docs, args.out)
        if args.stages:
            path = write_stages(args.out)
        elif args.defaults:
            path = export_defaults(args.out, args.live, args.page_url)
        else:
            path = export_run(args.run_dir, args.key, args.name, args.order, args.out)
    except ExportError as exc:
        print(f"export: {exc}", file=sys.stderr)
        return 2
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
