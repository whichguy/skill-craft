"""The fixed stage table: one row per SDLC stage, in graph order.

Each row states what the stage is for and the considerations that do not
change from run to run: how the stage develops, tests and delivers software,
which assistive tools (linters, formatters, type checkers, test runners) the
script runs around it, how it iterates and which outcomes it may return.
Every other per-stage set in ShipLoop is derived from this table, so a stage's
behaviour is read in one place.  The dry-run and e2e-audit stage lists stay
independent on purpose: they are oracles that check this table.

This module imports nothing from ShipLoop, so any module may import it.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from types import MappingProxyType
from typing import Mapping

# Shared prompt blocks a stage's packet carries (see shiploop_navigator_v3_prompts.prompt).
BLOCKS = frozenset({
    "environment-discovery",   # recursive discovery requirement and locators
    "test-facility",           # reuse and define test facilities
    "test-decision",           # reopen the current item's test decisions
    "backchain",               # Backchain caller guidance (native call or audit)
    "reconciliation",          # selected-case reconciliation
    "code-craft",              # the Code craft rubric
    "pass-or-stop",            # the prompt-only pass-or-stop loop
    "interaction-design",      # actors, channels, events and UI planning
    "work-items",              # how a plan or carry-forward records work-item context
})

# Assistive tool runs the script performs around a stage.
ENTRY_RUNS = frozenset({
    "lint-base",           # snapshot the work item's lint base when the item starts
    "test-loop-contract",  # write the test-loop Until Loop contract
    "change-inventory",    # record the item's changed files for the quality loop
    "quality-contract",    # write the quality-loop contract and the Code craft rubric
    "advisory-lint",       # lint the item's changes, auto-fixing on the first entry
    "report-lint",         # lint report-only (or repeat the unchanged record)
})
COMPLETE_RUNS = frozenset({
    "lint-gate",           # refuse done while a new finding on a changed line is unwaived
    "test-loop",           # check the test-loop terminal packet, then run the commands
    "test-red",            # run the focused commands and require them to fail in a test
    "test-rerun",          # run every recorded test command and require each to pass
    "quality-terminal",    # check the quality-loop terminal packet
})
EDITS = frozenset({"code", "tests", "docs"})
PHASES = ("prelude", "inner", "outer")
OUTCOMES = frozenset({"done", "repeat", "blocked", "replan", "revise"})

# A work item whose goal proves wrong while it is being built goes back to its
# step plan with the evidence, at most MAX_REVISES times; after that the user
# decides (blocked, blocked_by user).
REVISE_TO = "step-plan"
MAX_REVISES = 2


@dataclass(frozen=True)
class Stage:
    """One stage row.  Text fields are plain sentences for the packet."""

    name: str
    phase: str
    goal: str                              # desired end state; the status line shows it
    done_when: tuple[str, ...]             # conditions that confirm the goal
    develop: str | None = None             # how this stage treats product code
    test: str | None = None                # how this stage treats checks and tests
    deploy: str | None = None              # how this stage treats delivery
    tools: str | None = None               # the assistive tools that apply here
    edits: frozenset[str] = frozenset()    # what the stage may change: code, tests, docs
    entry_runs: tuple[str, ...] = ()       # script tool runs when the stage's action is issued
    complete_runs: tuple[str, ...] = ()    # script tool runs before done is accepted
    improve: str | None = None             # "always", "last-item" or None
    reads: tuple[str, ...] = ()            # accepted results to read first ("item:" = this item)
    blocks: frozenset[str] = field(default_factory=frozenset)
    outcomes: tuple[str, ...] = ("done", "repeat", "blocked")

    def __post_init__(self) -> None:
        if self.phase not in PHASES:
            raise ValueError(f"{self.name}: unknown phase {self.phase!r}")
        if not self.goal or not self.done_when:
            raise ValueError(f"{self.name}: a stage needs a goal and at least one done-when condition")
        for label, values, allowed in (("blocks", self.blocks, BLOCKS), ("edits", self.edits, EDITS),
                                       ("entry_runs", self.entry_runs, ENTRY_RUNS),
                                       ("complete_runs", self.complete_runs, COMPLETE_RUNS)):
            unknown = set(values) - allowed
            if unknown:
                raise ValueError(f"{self.name}: unknown {label} {sorted(unknown)}")
        if self.improve not in (None, "always", "last-item"):
            raise ValueError(f"{self.name}: unknown improve rule {self.improve!r}")
        if not set(self.outcomes) <= OUTCOMES or "done" not in self.outcomes:
            raise ValueError(f"{self.name}: outcomes must include done and use known outcomes")


_PLANNING = "Keep this stage's decisions, constraints and source locators in its result and evidence_refs."

_ROWS = (
    # ------------------------------------------------------------------ prelude
    Stage(
        "intake", "prelude",
        goal="confirm the request, boundaries and open questions",
        done_when=(
            "every sentence of the request maps to an outcome, a boundary or an open question",
            "each open question names who answers it (the user now, or discovery) and what it blocks",
            "the result says where the outcome will be visible, and when",
        ),
        deploy="Name where the result must become usable; a request that names the target is the grant.",
    ),
    Stage(
        "discovery", "prelude",
        goal="inspect the current repository, environment and baseline tests",
        done_when=(
            "the existing suite (full, or smoke if full is impractical) ran on the unchanged checkout, "
            "with command, exit code and output recorded",
            "every open question from intake is answered with a source or kept as an unknown with an owner",
            "conventions, runtimes, reusable code and delivery boundaries are recorded with source locators",
        ),
        develop="Record conventions, runtime and dependency versions and reusable code; edit no product file.",
        test="Run the existing suite first on the unchanged checkout; record and classify a failure, don't fix it.",
        deploy="Find how a change reaches its consumer, and whether returning to the source branch triggers CI or a deploy.",
        tools="Record the linters, formatters, type checkers and test runners the repository configures.",
        reads=("intake",),
        blocks=frozenset({"environment-discovery", "interaction-design"}),
    ),
    Stage(
        "research", "prelude",
        goal="resolve the unknowns that matter with evidence",
        done_when=(
            "every consequential unknown is resolved with evidence, or recorded with an owner and the gate it blocks",
            "each proven access need has been put to the user",
        ),
        develop="Prefer reuse: map each need to an existing library, service or skill where one fits.",
        deploy="Confirm access to each delivery target early with a safe, non-mutating probe.",
        reads=("intake", "discovery"),
        blocks=frozenset({"environment-discovery", "interaction-design"}),
    ),
    Stage(
        "spec", "prelude",
        goal="define required behavior and acceptance criteria",
        done_when=(
            "every request outcome maps to at least one acceptance criterion",
            "each criterion is independently verifiable and says how it will be confirmed",
            "non-functional requirements are assessed, or excluded with a reason",
            "unaffected existing requirements are preserved",
        ),
        develop="Define behaviour, error handling and consumer outcomes before any code.",
        test="State positive, failure and boundary expectations for each criterion.",
        deploy="Name the consumer surface where each criterion must be observed.",
        improve="always",
        reads=("intake", "discovery", "research"),
        blocks=frozenset({"backchain", "interaction-design"}),
    ),
    Stage(
        "test-strategy", "prelude",
        goal="map requirements to the checks that will prove them",
        done_when=(
            "every criterion maps to a check, its surface and the stage it is due",
            "the test harness is selected or revalidated, with setup and isolation stated",
            "planned checks are marked planned, not passed",
        ),
        test="Choose target-native tests across unit, integration, system and consumer layers.",
        deploy="Plan which checks run against the deployed target, and how.",
        tools="Name the test runner and any coverage or report tool the checks use.",
        improve="always",
        reads=("spec", "research"),
        blocks=frozenset({"test-facility"}),
    ),
    Stage(
        "plan", "prelude",
        goal="build the dependency plan and the work-item queue",
        done_when=(
            "every criterion is owned by a work item",
            "work items are in dependency order with readiness and completion conditions",
            "the assumption list is complete: each assumption evidenced, probed, or open with the item that settles it",
        ),
        develop="Plan namespaces, placement, schema and storage up front.",
        test="Plan a missing test facility as its own prerequisite work.",
        deploy="Include environment preparation and delivery work; ask for delivery authority at the first concrete boundary.",
        improve="always",
        reads=("intake", "discovery", "research", "spec", "test-strategy"),
        blocks=frozenset({"test-facility", "backchain", "interaction-design", "work-items"}),
    ),
    Stage(
        "prepare", "prelude",
        goal="ready the development and test environment",
        done_when=(
            "each planned check's runner starts in the prepared environment",
            "readiness is recorded, or a justified not-applicable",
        ),
        develop="Use what the repository already declares; install nothing without authority.",
        test="Confirm the test runner and fixtures start.",
        deploy="Prepare the development and test environments the plan named.",
        tools="Confirm the configured linters and the test runner run.",
        reads=("plan", "test-strategy"),
    ),
    # ------------------------------------------------------------------ inner
    Stage(
        "select-work", "inner",
        goal="confirm this work item is still the right next item",
        done_when=(
            "the item's prerequisites are accepted done",
            "the item is still required by the plan",
        ),
        tools="ShipLoop records the item's lint base when the item starts.",
        entry_runs=("lint-base",),
        reads=("spec", "plan"),
    ),
    Stage(
        "step-plan", "inner",
        goal="plan this item's concrete changes and checks",
        done_when=(
            "the result opens with one sentence naming the change and the checks that prove it",
            "ordered steps have dependencies, readiness and completion criteria, each with a Confirm by",
            "test_commands are recorded (focused and regression), or test_commands_na gives the reason",
            "the files the item will change are declared in paths",
        ),
        develop="Name target files, interfaces and conventions; follow the house-style match contract.",
        test="Record the item's test commands; test-red, test-green and regression run them exactly.",
        deploy="Note integration impact and any release prerequisite.",
        tools="Name the linters and type checks that cover the changed files.",
        improve="always",
        reads=("spec", "test-strategy", "plan", "prepare"),
        blocks=frozenset({"test-facility", "test-decision", "backchain", "interaction-design"}),
    ),
    Stage(
        "test-spec", "inner",
        goal="specify the tests this item needs before code changes",
        done_when=(
            "every completion criterion has at least one test case, or a justified not-applicable",
            "each case has an independent oracle and a RED and GREEN definition",
        ),
        test="Specify cases before code: positive, failure and boundary.",
        improve="always",
        reads=("spec", "test-strategy", "plan", "item:step-plan"),
        blocks=frozenset({"test-facility", "test-decision"}),
    ),
    Stage(
        "baseline", "inner",
        goal="record the relevant checks before any change",
        done_when=(
            "each recorded command ran on the unchanged item base, with its exit code and output recorded",
            "pre-existing failures are classified",
        ),
        test="Record the before state; fix nothing here.",
        reads=("test-strategy", "item:step-plan", "item:test-spec"),
    ),
    Stage(
        "test-author", "inner",
        goal="write the tests the item's test spec calls for",
        done_when=(
            "each case in the test spec has a test the focused command runs",
            "the tests are wired into the suite and repeatable",
        ),
        test="Write the tests the spec calls for; never weaken an assertion to fit an expected implementation.",
        tools="Tests follow the repository's test framework and lint rules.",
        edits=frozenset({"tests"}),
        reads=("test-strategy", "item:step-plan", "item:test-spec"),
        blocks=frozenset({"test-facility", "test-decision", "code-craft"}),
    ),
    Stage(
        "test-red", "inner",
        goal="run the new tests and confirm they fail for the right reason",
        done_when=(
            "the focused commands fail, and each new test's failure names the missing behaviour",
            "no failure is caused by syntax, import, fixture or environment",
        ),
        develop="Do not edit product code.",
        test="ShipLoop runs the focused commands and requires them to fail inside a test.",
        edits=frozenset({"tests"}),
        complete_runs=("test-red",),
        reads=("item:test-spec", "item:test-author"),
        blocks=frozenset({"test-facility", "code-craft"}),
    ),
    Stage(
        "implement", "inner",
        goal="make the planned change",
        done_when=(
            "every step's completion criterion is confirmed by its Confirm by after the last edit",
            "the lint gate reports no unwaived new finding on changed lines",
        ),
        develop="Make the planned change in the execution checkout, one reviewed step at a time, matching the house style.",
        test="After each step, rerun the checks it affects; change the work, never the check.",
        tools="Run `shiploop lint --action` after each step; the lint gate runs at complete.",
        edits=frozenset({"code", "tests"}),
        complete_runs=("lint-gate",),
        reads=("spec", "plan", "item:step-plan", "item:test-spec"),
        blocks=frozenset({"code-craft"}),
    ),
    Stage(
        "test-green", "inner",
        goal="run the focused tests and confirm they pass",
        done_when=(
            "every focused command passes on the bound Until Loop and when ShipLoop reruns it",
        ),
        test="Loop on the focused commands until they pass.",
        tools="The lint gate runs before ShipLoop's own test run.",
        edits=frozenset({"code", "tests"}),
        entry_runs=("test-loop-contract",),
        complete_runs=("lint-gate", "test-loop"),
        reads=("item:test-spec", "item:implement"),
        blocks=frozenset({"code-craft"}),
        outcomes=("done", "blocked"),
    ),
    Stage(
        "test-refine", "inner",
        goal="tighten the tests against the actual implementation",
        done_when=(
            "tests are tightened against the actual implementation",
            "every recorded command passes when ShipLoop reruns it",
        ),
        test="Tighten weak assertions; change a check only for an independent reason.",
        edits=frozenset({"code", "tests"}),
        complete_runs=("test-rerun",),
        reads=("spec", "item:test-spec", "item:implement"),
        blocks=frozenset({"test-facility", "test-decision", "code-craft", "pass-or-stop"}),
    ),
    Stage(
        "regression", "inner",
        goal="rerun the retained suites for regressions",
        done_when=(
            "every recorded command passes on the bound Until Loop and when ShipLoop reruns it",
            "nothing that passed at baseline fails now",
        ),
        test="Run the retained suites; fix the code, not the checks.",
        tools="The lint gate runs before ShipLoop's own test run.",
        edits=frozenset({"code", "tests"}),
        entry_runs=("test-loop-contract",),
        complete_runs=("lint-gate", "test-loop"),
        reads=("test-strategy", "item:baseline"),
        blocks=frozenset({"test-facility", "test-decision", "code-craft"}),
        outcomes=("done", "blocked"),
    ),
    Stage(
        "document", "inner",
        goal="update the documentation this change affects",
        done_when=(
            "each changed public behaviour is documented where users and maintainers look",
            "each changed document was reread after the last edit",
        ),
        develop="Update code, API, user and operator documentation from observed behaviour.",
        edits=frozenset({"docs"}),
        reads=("spec", "plan", "item:step-plan", "item:implement"),
        blocks=frozenset({"code-craft"}),
    ),
    Stage(
        "skill-assess", "inner",
        goal="decide whether a reusable skill or helper change is warranted",
        done_when=("a reuse or new-skill decision is recorded with its reason",),
        reads=("plan", "item:step-plan"),
    ),
    Stage(
        "skill-validate", "inner",
        goal="validate any skill or helper change against real inputs",
        done_when=("any changed skill or helper ran on a real input, or the not-applicable reason is recorded",),
        reads=("item:skill-assess",),
    ),
    Stage(
        "static-checks", "inner",
        goal="run formatting, lint, type and build checks",
        done_when=(
            "the quality loop ends with an iteration of only trivial findings",
            "every recorded command passes when ShipLoop reruns it",
        ),
        develop="Trace each changed public entry point with a valid, a boundary and an invalid input; fix against Code craft.",
        tools="ShipLoop records the change inventory, lints again (auto-fixing on first entry) and writes the quality-loop contract.",
        edits=frozenset({"code", "tests"}),
        entry_runs=("change-inventory", "quality-contract", "advisory-lint"),
        complete_runs=("quality-terminal", "test-rerun"),
        reads=("item:step-plan", "item:implement"),
        blocks=frozenset({"code-craft"}),
        outcomes=("done", "blocked"),
    ),
    Stage(
        "verify", "inner",
        goal="verify the item against its acceptance criteria",
        done_when=(
            "every completion criterion of the item is confirmed on the current candidate, with evidence made after the last edit",
            "later-phase checks are marked pending with their owner",
        ),
        test="Rerun or inspect each criterion's confirmation; reconcile every selected case.",
        tools="ShipLoop reruns lint report-only on entry, and on done runs every recorded command.",
        entry_runs=("report-lint",),
        complete_runs=("test-rerun",),
        reads=("spec", "test-strategy", "item:step-plan", "item:test-spec", "item:implement",
               "item:test-green", "item:regression", "item:static-checks"),
        blocks=frozenset({"reconciliation", "code-craft"}),
    ),
    Stage(
        "integrate", "inner",
        goal="integrate the candidate into the working branch",
        done_when=("the item's changes are assembled in the execution checkout, or a justified no-op is recorded",),
        develop="Integrate only through authorized Git operations; keep run state and logs out of product commits.",
        deploy="The original branch is returned only at the final workspace return.",
        edits=frozenset({"code"}),
        reads=("plan", "item:step-plan", "item:verify"),
        blocks=frozenset({"code-craft"}),
    ),
    Stage(
        "integration-verify", "inner",
        goal="verify the integrated result and shared interfaces",
        done_when=(
            "every recorded command passes on the integrated result when ShipLoop reruns it",
            "shared interfaces are checked",
        ),
        test="Verify the integrated result and the shared interfaces.",
        edits=frozenset({"code", "tests"}),
        complete_runs=("test-rerun",),
        reads=("spec", "item:integrate"),
        blocks=frozenset({"reconciliation", "code-craft", "pass-or-stop"}),
    ),
    Stage(
        "carry-forward", "inner",
        goal="record lessons and revise the remaining queue",
        done_when=(
            "every still-required future item is in the queue, in prerequisite order",
            "learnings and durable knowledge are recorded outside run notes",
        ),
        develop="Record reusable learnings and conventions.",
        test="Keep rerun procedures in the repository's test documentation.",
        edits=frozenset({"docs"}),
        improve="last-item",
        reads=("spec", "plan", "item:integration-verify"),
        blocks=frozenset({"test-facility", "backchain", "work-items"}),
    ),
    # ------------------------------------------------------------------ outer
    Stage(
        "system-test-author", "outer",
        goal="prepare end-to-end and system tests",
        done_when=("every system-level criterion has a system test, or a planned check with its due stage",),
        test="Author end-to-end and system tests against real boundaries.",
        deploy="Plan which tests run against the deployed target.",
        edits=frozenset({"tests"}),
        improve="always",
        reads=("spec", "test-strategy", "plan"),
        blocks=frozenset({"test-facility"}),
    ),
    Stage(
        "system-test", "outer",
        goal="run end-to-end and system tests on the real candidate",
        done_when=("every due system test ran on the real candidate, with its output recorded",),
        test="Run system tests on the assembled candidate; a local pass does not replace a required deployed check.",
        tools="On done, ShipLoop runs every system command system-test-author recorded.",
        complete_runs=("test-rerun",),
        reads=("spec", "system-test-author"),
        blocks=frozenset({"reconciliation"}),
    ),
    Stage(
        "product-acceptance", "outer",
        goal="assess the product against the original outcome",
        done_when=(
            "every request outcome is verified, or pending with its owner and due stage",
            "missing product work is routed as replan",
        ),
        test="Assess the product against the original outcome, not only the spec.",
        reads=("intake", "spec", "system-test"),
        blocks=frozenset({"backchain", "reconciliation"}),
    ),
    Stage(
        "release-plan", "outer",
        goal="plan the release, rollback and checks",
        done_when=(
            "release, rollback and post-release verification steps are planned",
            "delivery authority is recorded before the plan is accepted",
            "the consumer entry names how a person reaches the result",
        ),
        test="Plan the post-release checks.",
        deploy="Plan the release, its rollback and the post-release checks.",
        improve="always",
        reads=("spec", "plan", "system-test"),
        blocks=frozenset({"test-facility"}),
    ),
    Stage(
        "release-check", "outer",
        goal="confirm release readiness without releasing",
        done_when=(
            "each release precondition is observed",
            "each post-release confirm command ran once and recorded its not-there-yet output",
        ),
        deploy="Dry-run the deploy; do not release.",
        reads=("release-plan",),
    ),
    Stage(
        "release", "outer",
        goal="perform the planned release",
        done_when=(
            "the planned release ran with a recorded grant, or a justified not-applicable",
            "the released identity is recorded",
        ),
        deploy="Release only with a recorded grant; the dry run precedes the real deploy.",
        reads=("release-plan", "release-check"),
    ),
    Stage(
        "release-verify", "outer",
        goal="verify the release where consumers use it",
        done_when=("the consumer behaviour is observed where consumers use it",),
        test="A passing unit suite is not delivery evidence.",
        deploy="Verify the release in the target.",
        tools="On done, ShipLoop runs every consumer check release-plan recorded.",
        complete_runs=("test-rerun",),
        reads=("spec", "release-plan", "release"),
        blocks=frozenset({"reconciliation"}),
    ),
    Stage(
        "operations", "outer",
        goal="confirm monitoring, recovery and support readiness",
        done_when=("monitoring, recovery and support readiness are confirmed, or justified not-applicable",),
        deploy="Confirm monitoring and rollback work.",
        reads=("release-plan", "release-verify"),
    ),
    Stage(
        "handoff", "outer",
        goal="write the final handoff with status and evidence",
        done_when=(
            "the handoff states source, test, release and consumer status with evidence",
            "the workspace return is verified (worktree runs)",
        ),
        reads=("intake", "spec", "plan", "product-acceptance", "release-verify", "operations"),
        blocks=frozenset({"reconciliation"}),
    ),
)



def _finish(rows: tuple[Stage, ...]) -> tuple[Stage, ...]:
    """Add the outcomes that follow from a stage's place in the graph.

    INNER stages from test-spec through integration-verify build the item
    against its step plan, so a goal that proves wrong there goes back to the
    step plan (revise).  OUTER stages route missing product work as replan.
    """
    names = [row.name for row in rows]
    first, last = names.index("test-spec"), names.index("integration-verify")
    finished = []
    for index, row in enumerate(rows):
        if first <= index <= last:
            row = replace(row, outcomes=row.outcomes + ("revise",))
        elif row.phase == "outer":
            row = replace(row, outcomes=row.outcomes + ("replan",))
        finished.append(row)
    return tuple(finished)


_ROWS = _finish(_ROWS)
STAGE_SPEC: Mapping[str, Stage] = MappingProxyType({row.name: row for row in _ROWS})
STAGES: tuple[str, ...] = tuple(row.name for row in _ROWS)
PRELUDE: tuple[str, ...] = tuple(row.name for row in _ROWS if row.phase == "prelude")
INNER: tuple[str, ...] = tuple(row.name for row in _ROWS if row.phase == "inner")
OUTER: tuple[str, ...] = tuple(row.name for row in _ROWS if row.phase == "outer")


def stage(name: str) -> Stage:
    """Return one stage row; an unknown stage raises ValueError."""
    try:
        return STAGE_SPEC[name]
    except KeyError:
        raise ValueError(f"unknown navigator stage: {name!r}") from None


def with_block(block: str) -> frozenset[str]:
    """Stages whose packet carries a shared prompt block."""
    if block not in BLOCKS:
        raise ValueError(f"unknown prompt block: {block!r}")
    return frozenset(row.name for row in _ROWS if block in row.blocks)


def with_entry_run(run: str) -> tuple[str, ...]:
    """Stages, in graph order, where the script performs an entry tool run."""
    if run not in ENTRY_RUNS:
        raise ValueError(f"unknown entry run: {run!r}")
    return tuple(row.name for row in _ROWS if run in row.entry_runs)


def with_complete_run(run: str) -> tuple[str, ...]:
    """Stages, in graph order, where the script performs a tool run before accepting done."""
    if run not in COMPLETE_RUNS:
        raise ValueError(f"unknown complete run: {run!r}")
    return tuple(row.name for row in _ROWS if run in row.complete_runs)


def with_outcome(outcome: str) -> tuple[str, ...]:
    """Stages, in graph order, that accept ``outcome``."""
    if outcome not in OUTCOMES:
        raise ValueError(f"unknown outcome: {outcome!r}")
    return tuple(row.name for row in _ROWS if outcome in row.outcomes)


def with_improve(rule: str) -> frozenset[str]:
    """Stages whose accepted result starts an Improve child under ``rule``."""
    return frozenset(row.name for row in _ROWS if row.improve == rule)


def _check_table() -> None:
    names = [row.name for row in _ROWS]
    if len(names) != 34 or len(set(names)) != 34:
        raise RuntimeError("the stage table must list 34 unique stages")
    order = {name: index for index, name in enumerate(names)}
    for row in _ROWS:
        for read in row.reads:
            item = read.startswith("item:")
            source = read[5:] if item else read
            if source not in order or order[source] >= order[row.name]:
                raise RuntimeError(f"{row.name} reads {read!r}, which is not an earlier stage")
            if item and (row.phase != "inner" or STAGE_SPEC[source].phase != "inner"):
                raise RuntimeError(f"{row.name}: item reads are only for INNER stages")
    phases = [row.phase for row in _ROWS]
    if phases != sorted(phases, key=PHASES.index):
        raise RuntimeError("stages must be grouped prelude, inner, outer")


_check_table()
