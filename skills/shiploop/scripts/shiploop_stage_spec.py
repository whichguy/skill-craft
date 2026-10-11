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

# Shared prompt blocks a stage's packet carries (see shiploop_prompts.prompt).
BLOCKS = frozenset({
    "environment-discovery",   # recursive discovery requirement and locators
    "test-facility",           # reuse and define test facilities
    "test-decision",           # reopen the current item's test decisions
    "backchain",               # Backchain caller guidance (native call or audit)
    "reconciliation",          # selected-case reconciliation
    "code-craft",              # the Code craft rubric
    "interaction-design",      # actors, channels, events and UI planning
    "work-items",              # how a plan or carry-forward records work-item context
})

# Assistive tool runs the script performs around a stage.
ENTRY_RUNS = frozenset({
    "lint-base",           # snapshot the work item's lint base when the item starts
    "loop-contract",       # write the stage's Until Loop contract (every inner stage)
    "expectation-check",   # run the step plan's expectation checks on the item base; all match: no packet
    "change-inventory",    # record the item's changed files for the review loop
    "advisory-lint",       # lint the item's changes, auto-fixing on the first entry
})
COMPLETE_RUNS = frozenset({
    "loop-terminal",       # check the stage's Until Loop terminal packet against the contract rebuilt from state
    "lint-gate",           # refuse done while a new finding on a changed line is unwaived
    "expectation-check",   # rerun every expectation check and require each to match its state
    "test-base",           # run the item's tests on the base checkout: no new test ID passes; sets the floor
    "test-loop",           # run every recorded command on the candidate: each passes, every ID, the floor
    "test-rerun",          # run every recorded test command and require each to pass
})
EDITS = frozenset({"code", "tests", "docs"})
PHASES = ("prelude", "inner", "outer")
OUTCOMES = frozenset({"done", "repeat", "blocked", "replan", "revise"})

# Improve rules: "always" starts a child after the stage's accepted result, "last-item" only after the last work item's,
# and "step" after every accepted implement step (owner, 2026-10-10), whatever the planning review option says.
IMPROVE_RULES = ("always", "last-item", "step")

# A work item whose goal proves wrong while it is being built goes back to its
# step plan with the evidence, at most MAX_REVISES times; after that the user
# decides (blocked, blocked_by user).
REVISE_TO = "step-plan"
MAX_REVISES = 2
# The step exit criteria's stopping rule (SPEC S-10 carve-out, owner decision 2026-10-10): the same check still failing
# after this many genuine fix attempts ends the stage as revise. No script counts the attempts; the model applies it, and
# test/shiploop-stage-spec.test.py pins every prose copy to this value.
GENUINE_FIX_ATTEMPTS = 7


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
    improve: str | None = None             # one of IMPROVE_RULES, or None
    reads: tuple[str, ...] = ()            # accepted results to read first ("item:" = this item)
    blocks: frozenset[str] = field(default_factory=frozenset)
    outcomes: tuple[str, ...] = ("done", "repeat", "blocked")
    cases: bool = False                    # the test text ends with case_end_states (added once outcomes are final)

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
        if self.improve not in (None, *IMPROVE_RULES):
            raise ValueError(f"{self.name}: unknown improve rule {self.improve!r}")
        if not set(self.outcomes) <= OUTCOMES or "done" not in self.outcomes:
            raise ValueError(f"{self.name}: outcomes must include done and use known outcomes")


_PLANNING = "Keep this stage's decisions, constraints and source locators in its result and evidence_refs."

# Owner rule (2026-10-08): a test is authored and executed.  Every planned case ends in one of three states, with its
# evidence, and "written" or "not run" is not one of them.  ``case_end_states`` words the unachievable state from the
# stage's own outcomes, so no stage is offered a route its gate refuses (SPEC S-3, S-12).
_CASE_STATES = (
    "Every case ends in one of three states: validated (executed, and the observation matches the expectation), "
    "validated another way (the first method could not observe it, so the method changed and the new one was executed "
    "and passed; the result says what changed and why), or unachievable (a named reason, and the requirement it leaves "
    "unverified; {routes}). A case that is written but not run, or recorded as not run, is not an end state."
)


def case_end_states(row: "Stage") -> str:
    """The case end-state sentence for ``row``, built from the outcomes the row accepts.

    An OUTER test stage records an unachievable case as an open item and continues, but only for a case whose command
    ShipLoop does not rerun (the navigator's test-rerun gate refuses done while a recorded command fails); an INNER
    stage sends it back to the step plan with revise.  Blocked and replan are named only where the row accepts them.
    """
    if row.phase == "outer":
        routes = ["record it as an open item in the summary with its due stage and continue, provided its command is "
                  "not one ShipLoop reruns, since every rerun command must pass"]
    elif "revise" in row.outcomes:
        routes = ["report revise so the step plan reroutes the case"]
    else:
        raise ValueError(f"{row.name}: an unachievable case needs an open-item or a revise route")
    if "blocked" in row.outcomes:
        routes.append("report blocked with blocked_by access only when nothing else can proceed")
    if "replan" in row.outcomes:
        routes.append("report replan when the plan is wrong")
    return _CASE_STATES.format(routes=routes[0] if len(routes) == 1 else ", ".join(routes[:-1]) + ", or " + routes[-1])


# plan-return's own rule (``workspace.commit_leftovers``), worded once: the workspace Return route line and a worktree
# run's item-commit sentence both print it (SPEC S-12).
RETURN_LEFTOVERS = ("plan-return commits files left uncommitted, so commit nothing for the return except a file it "
                    "reports as not committed.")

# Who commits an item's files (SPEC S-4, S-5): one rule, printed by every stage that adds files to the item.  The first
# sentence mirrors ``item_scope.commit_scope`` (declared paths, the docs path class and docs/shiploop/); the second
# depends on the run: a worktree run's plan-return commits what is left, an in-place run has no return.
ITEM_COMMIT_STAGES = ("document", "verify")
ITEM_COMMITS = (
    "When verify is accepted, ShipLoop commits the item's changed files that the step plan's paths declare, its "
    "changed documentation files (for example README.md or files under docs/) and docs/shiploop/."
)
_LEFT_FOR_RETURN = ("Any other changed file is left for the return: " + RETURN_LEFTOVERS
                    + " Delete generated output the product does not need.")
_LEFT_IN_PLACE = ("ShipLoop commits no other changed file, and you commit nothing yourself: if the product needs one, "
                  "report revise so the step plan declares it; otherwise delete it.")


def item_left(execution_mode: str) -> str:
    """What happens to a changed file the item commit leaves, for a run in ``execution_mode``."""
    return _LEFT_FOR_RETURN if execution_mode == "navigator-worktree" else _LEFT_IN_PLACE


def develop(name: str, execution_mode: str) -> str | None:
    """A stage's Develop consideration as its packet prints it: the row's text plus, where the stage adds files to the
    item, the commit rule for this run."""
    text = stage(name).develop
    if name not in ITEM_COMMIT_STAGES:
        return text
    rule = ITEM_COMMITS + " " + item_left(execution_mode)
    return text + " " + rule if text else rule


_ROWS = (
    # ------------------------------------------------------------------ prelude
    Stage(
        "intake", "prelude",
        goal="confirm the request, boundaries and open questions",
        done_when=(
            "every sentence of the request maps to an outcome, a boundary or an open question",
            "each open question names who answers it (discovery, or a recorded default) and what it blocks",
            "the result says where the outcome will be visible, and when",
        ),
        deploy="Name where the result must become usable; a request that names the target is the grant.",
    ),
    Stage(
        "discovery", "prelude",
        goal="inspect the current repository, environment and baseline tests",
        done_when=(
            "the existing suite (full, or smoke if full is impractical) ran on the unchanged checkout, "
            "with command, exit code and output recorded, or none exists and that is recorded as missing coverage",
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
            "each proven access need is recorded as an open item with who can grant it and the gate it blocks",
        ),
        develop="For each need, evaluate reusing an existing part unchanged, composing parts, or augmenting one "
                "before building new; record the choice and, for augment or new, why the earlier options do not fit.",
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
            "each case that needs a host tool (a browser, a device, an account, a service) names it and cites the "
            "output of probing it now by doing the case's first step, against a stand-in while the product does not "
            "exist, and only a failed probe is recorded as the access gap, with the requirement it leaves unobserved",
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
    # Owner decision 2026-10-10: eight stages in five phases (Plan: step-plan, test-spec; Validate existing; Build:
    # implement per step with an Improve child after each, test, document; Verify; Carry forward).  Each stage's work
    # runs as one Until Loop with a ShipLoop-written contract (entry run loop-contract); its exit conditions are the
    # done_when lines below, and the gate rechecks by script what it can.  Evidence and the coverage review of the
    # seventeen stages this replaces: docs/experiments/inner-loop-redesign-20261010/.
    Stage(
        "step-plan", "inner",
        goal="plan this item's concrete changes, checks and the facts they build on",
        done_when=(
            "the result opens with one sentence naming the change and the checks that prove it",
            "steps lists every implementation step in the order to do them",
            "each step declares deps, the criteria it satisfies and the paths it changes, every criterion is satisfied "
            "by a step, and no step only changes test files (unless the whole item is tests)",
            "test_commands records focused, regression and at least one check command (lint, type or build), with "
            "check_na giving the reason when there is no check command, or test_commands_na giving the reason there "
            "are no commands",
            "expectations record, for every existing path a step changes or relies on, a works or broken "
            "expectation, and for every new path an absent one, each with a read-only check command",
            "each step's skills list names a concrete use for each helper skill, or is empty",
            "the files the item will change are declared in paths",
        ),
        develop="Name target files, interfaces and conventions; follow the house-style match contract.",
        test="Record the item's test commands; the test stage and verify run them exactly.",
        deploy="Note integration impact and any release prerequisite.",
        tools="ShipLoop records the item's lint base when the item starts; name the linters, type checks and build "
              "commands that cover the changed files.",
        entry_runs=("lint-base", "loop-contract"),
        complete_runs=("loop-terminal",),
        improve="always",
        reads=("spec", "test-strategy", "plan", "prepare"),
        blocks=frozenset({"test-facility", "test-decision", "backchain", "interaction-design"}),        outcomes=("done", "blocked"),
    ),
    Stage(
        "test-spec", "inner",
        goal="specify the tests this item needs before code changes",
        done_when=(
            "every completion criterion has at least one test case, or a justified not-applicable",
            "each case has an independent oracle, a RED and a GREEN definition, and an ID a focused command lists",
        ),
        test="Specify cases before code: positive, failure and boundary.",
        entry_runs=("loop-contract",),
        complete_runs=("loop-terminal",),
        improve="always",
        reads=("spec", "test-strategy", "plan", "item:step-plan"),
        blocks=frozenset({"test-facility", "test-decision"}),        outcomes=("done", "blocked"),
    ),
    Stage(
        "validate-existing", "inner",
        goal="verify that what this item is about to change works before changing it",
        done_when=(
            "every works expectation passes its check on the current checkout",
            "every absent expectation finds nothing at its place",
            "every broken expectation fails exactly as the request reports",
            "each preparatory fix touches only the paths of an expectation that did not match, and ShipLoop commits "
            "it on accept",
        ),
        develop="Change no product file except a known small fix to a works expectation found broken, made before "
                "the build; ShipLoop commits it on accept as its own commit. Never start the item's own change here.",
        test="ShipLoop runs every expectation check on the item base; when all match, no packet is issued.",
        edits=frozenset({"code"}),
        entry_runs=("expectation-check", "loop-contract"),
        complete_runs=("loop-terminal", "expectation-check"),
        reads=("plan", "item:step-plan"),
        outcomes=("done", "blocked"),
    ),
    Stage(
        "implement", "inner",
        goal="make the planned step's change",
        done_when=(
            "only the step's paths changed since the step began, and no later step's work is in them",
            "after the last edit, every recorded check command exited 0",
            "after the last edit, the lint gate reports no unwaived new finding on a line this step changed",
            "the result lists each behaviour the change added that no test-spec case covers (or none), and whether "
            "each of the step's skills was used",
        ),
        develop="Make the planned change in the execution checkout, one reviewed step at a time, matching the house style.",
        test="After each edit, rerun the check commands; change the work, never the check. Tests are written in the "
             "test stage.",
        tools="Run `shiploop lint --action` after each edit; the lint gate runs at complete, on every step.",
        edits=frozenset({"code"}),
        entry_runs=("loop-contract",),
        complete_runs=("loop-terminal", "lint-gate"),
        improve="step",
        reads=("spec", "plan", "item:step-plan", "item:test-spec", "item:validate-existing"),
        blocks=frozenset({"code-craft"}),
        outcomes=("done", "blocked"),
    ),
    Stage(
        "test", "inner",
        goal="write the specified tests and make every recorded command pass",
        done_when=(
            "every case in the test spec is a test the focused command runs, with its ID in the name",
            "no new test ID passes on the item's base checkout, unless red_na names it",
            "one complete iteration after the last edit ran every recorded command, each exiting 0, running every "
            "listed ID and at least the floor of tests",
            "every test change made to pass a run has a recorded independent reason",
        ),
        test="Write the tests from the test spec, run every command, and fix the code (or a test, for a recorded "
             "independent reason) until all pass.",
        cases=True,
        tools="The lint gate runs before ShipLoop's own test runs.",
        edits=frozenset({"code", "tests"}),
        entry_runs=("loop-contract",),
        complete_runs=("loop-terminal", "lint-gate", "test-base", "test-loop"),
        reads=("test-strategy", "item:step-plan", "item:test-spec", "item:implement"),
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
        entry_runs=("loop-contract",),
        complete_runs=("loop-terminal",),
        reads=("spec", "plan", "item:step-plan", "item:implement", "item:test"),
        blocks=frozenset({"code-craft"}),        outcomes=("done", "blocked"),
    ),
    Stage(
        "verify", "inner",
        goal="verify the item against its acceptance criteria and review the change",
        done_when=(
            "every completion criterion is confirmed on the current candidate, with evidence made after the last edit",
            "every recorded command exits 0 on the candidate after the last edit",
            "each changed public entry point was traced with a valid, a boundary and an invalid input, and the "
            "latest review iteration found only trivial issues",
            "later-phase checks are marked pending with their owner",
        ),
        develop="Review the whole item's diff for what the per-step reviews could not see; on chained work, assemble "
                "the steps' results and check the shared interfaces.",
        test="Confirm each criterion; reconcile every selected case.",
        tools="ShipLoop records the change inventory and lints the item's changes on entry (auto-fixing once); on "
              "done it lints again and reruns every recorded command.",
        edits=frozenset({"code", "tests"}),
        entry_runs=("change-inventory", "advisory-lint", "loop-contract"),
        complete_runs=("loop-terminal", "lint-gate", "test-rerun"),
        reads=("spec", "test-strategy", "item:step-plan", "item:test-spec", "item:implement", "item:test"),
        blocks=frozenset({"reconciliation", "code-craft"}),
        outcomes=("done", "blocked"),
    ),
    Stage(
        "carry-forward", "inner",
        goal="record lessons, revise the remaining queue and decide on a reusable skill",
        done_when=(
            "every still-required future item is in the queue, in prerequisite order",
            "learnings and durable knowledge are recorded in the knowledge home, not in run notes",
            "the skill decision is recorded: none, reuse, update or create, with its reason and repeat evidence",
        ),
        develop="Record reusable learnings and conventions; create or update a local skill only for a procedure that "
                "repeated or will recur and that no existing skill covers.",
        test="Keep rerun procedures in the repository's test documentation.",
        edits=frozenset({"docs"}),
        entry_runs=("loop-contract",),
        complete_runs=("loop-terminal",),
        improve="last-item",
        reads=("spec", "plan", "item:verify"),
        blocks=frozenset({"test-facility", "backchain", "work-items"}),
        outcomes=("done", "blocked"),
    ),
    # ------------------------------------------------------------------ outer
    Stage(
        "system-test-author", "outer",
        goal="prepare end-to-end and system tests",
        done_when=("every system-level criterion has a system test, or a planned check with its due stage",),
        test="Author end-to-end and system tests against real boundaries, and run each once while authoring.",
        cases=True,
        deploy="Plan which tests run against the deployed target.",
        edits=frozenset({"tests"}),
        improve="always",
        # test-spec: every item's latest test cases (consumer contract CONSUMES, 2026-10-11).
        reads=("spec", "test-strategy", "plan", "test-spec"),
        blocks=frozenset({"test-facility"}),
    ),
    Stage(
        "system-test", "outer",
        goal="run end-to-end and system tests on the real candidate",
        done_when=("every due system test ran on the real candidate, with its output recorded",),
        test="Run system tests on the assembled candidate; a local pass does not replace a required deployed check.",
        cases=True,
        tools="On done, ShipLoop runs every system command system-test-author recorded.",
        complete_runs=("test-rerun",),
        reads=("spec", "system-test-author"),
        blocks=frozenset({"reconciliation"}),
    ),
    Stage(
        "product-acceptance", "outer",
        goal="assess the product against the original outcome",
        done_when=(
            "every request outcome was observed by an executed check, or is listed in unverified with its reason, "
            "owner and due stage",
            "missing product work is routed as replan",
        ),
        test="Assess the product against the original outcome, not only the spec.",
        reads=("intake", "spec", "system-test-author", "system-test"),
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
        # system-test-author: the system commands it recorded (consumer contract CONSUMES, 2026-10-11).
        reads=("spec", "plan", "system-test-author", "system-test"),
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
        done_when=(
            "the consumer behaviour is observed where consumers use it",
            "this run's outcome.md, environment.md and README.md are written under docs/shiploop, and outcome.md "
            "fills its ## Learned, ## Key considerations and ## Open for the next run sections",
        ),
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

    INNER stages from test-spec through verify build the item against its step
    plan, so a goal that proves wrong there goes back to the step plan (revise).  OUTER stages route missing product work as replan.
    A row that prints the case end states gets them here, from its final outcomes.
    """
    names = [row.name for row in rows]
    first, last = names.index("test-spec"), names.index("verify")
    finished = []
    for index, row in enumerate(rows):
        if first <= index <= last:
            row = replace(row, outcomes=row.outcomes + ("revise",))
        elif row.phase == "outer":
            row = replace(row, outcomes=row.outcomes + ("replan",))
        if row.cases:
            row = replace(row, test=(row.test + " " if row.test else "") + case_end_states(row))
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


# Run-level planning review option (state key ``planning_review``): which planning results start an
# Improve child.  A value is registered together with the behaviour it selects, so no commit records
# a value the engine ignores.  ``stage`` is today's behaviour: every stage whose rule is ``always``
# starts its own child.  ``none`` starts none at the five planning stages the option covers; the
# children after system-test-author and release-plan and the last carry-forward's rule are not the
# option's, so they keep running.  New CLI-created runs record DEFAULT_PLANNING_REVIEW; a saved run
# without the key is refused (one supported version), and no verb changes it mid-run.
PLANNING_REVIEW_MODES = ("stage", "none")
DEFAULT_PLANNING_REVIEW = "stage"
PLANNING_CHOICE_STAGES = frozenset(("spec", "test-strategy", "plan", "step-plan", "test-spec"))


def reviewed_stages(mode: str) -> frozenset[str]:
    """Stages whose accepted result starts an Improve child under planning review ``mode``."""
    if mode not in PLANNING_REVIEW_MODES:
        raise ValueError(f"unknown planning review option: {mode!r}")
    if mode == "none":
        return with_improve("always") - PLANNING_CHOICE_STAGES
    return with_improve("always")


def _check_table() -> None:
    names = [row.name for row in _ROWS]
    if len(names) != 24 or len(set(names)) != 24:
        raise RuntimeError("the stage table must list 24 unique stages")
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
