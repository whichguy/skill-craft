"""The nine proposed inner-loop stage prompts (DO / DONE WHEN / RUN / FILES), with what each absorbs, keeps, moves and
drops relative to today's stages. Writes drafts.json for the page."""
import json
from pathlib import Path

HERE = Path(__file__).parent
current = json.loads((HERE / "current.json").read_text())

CONSULT = {
    "spec": "living spec <repo>/docs/shiploop/spec.md and this run's feature spec",
    "env": "<repo>/docs/shiploop/environment.md",
    "arch": "<repo>/docs/shiploop/architecture.md",
    "ts": "<repo>/docs/shiploop/test-strategy.md",
}

STAGES = [
  {
    "id": "step-plan", "phase": "Plan", "name": "step-plan",
    "absorbs": ["get-next-work-item", "baseline (dropped: no gate read it)"],
    "role": "Plan this item: behaviour-sized steps, the criteria each satisfies, the test, lint and build commands, and the files it changes; confirm the item is still required.",
    "gate_before": "shape checks (commands, criteria, deps, paths) + Improve review",
    "gate_after": "the same, plus step sizing (each step: criteria + paths, a criterion with no step, a test-only step); Improve review. The before-state check is now validate-existing, with a gate",
    "prompt": """DO
Goal: plan this item's concrete changes and the checks that prove them.
First confirm the item is still required by the plan and its prerequisites are accepted
(ShipLoop lists them below); if not, report blocked naming the missing producer.
Consult, in this order, and cite the sections you used:
- spec (## Requirements, ## Non-functional requirements): the R-<n> this item serves; each
  criterion you write traces to one.
- architecture.md (## Structure, ## Interfaces and boundaries, ## Conventions, ## Decisions):
  where the change goes. A structural choice the file does not already make is a new AD-<n>
  under ## Decisions, written now.
- environment.md (## Commands, ## Targets and runtimes): the commands that run the tests,
  lint, type checks and build. Record a new working command under ## Commands (create the
  heading if missing).
- test-strategy.md (## Harnesses and suites, ## ID convention): the harness and test IDs.
Size each step as one behaviour-level change a named check proves: its criteria and paths.
Split two independently confirmable behaviours, a change across a module boundary (interface
first), a task that needs "and" between two outcomes, or a step too large to review in one
pass. Merge a step no check can confirm on its own into the step it serves. Tests are not a
step: the test stage writes them after implement. One fix or one mechanical rename is one step.
Record test_commands: focused (the item's new cases), regression (the retained suites) and
check: one entry for each lint, type-check and build command environment.md records for the
files this item changes, each exiting 0 when clean. These are the static checks; the test
stage runs them and ShipLoop reruns them at its gate and at verify. When the repository has
none for these files, say so in check_na.
Helper skills: for each step, pick the skills that would help do it well, from the skills
your host offers and the repository's local skills (environment.md ## Skills names the
directory). Record them on the step: skills: [{"name": "...", "why": "<what it helps with in
this step>", "locator": "<its SKILL.md path, when it has one>"}]. Pick a skill only for a
concrete use in that step; an empty list is fine. Implement prints them with the step.
Expectations: for everything a step will change, extend or call, record what must be true
before the change, with a check that shows it now. Each has a state:
- works: it exists and works today (an existing function, route, schema, file or behaviour
  the step modifies or builds on; a tool or service it calls);
- absent: it does not exist yet, and the place it goes is free (no file, name or route clash);
- broken: the request says it is broken; the check reproduces the failure as reported, and
  this item's steps fix it.
Record expectations: [{"id": "E1", "state": "works|absent|broken", "statement": "...",
"steps": ["S1"], "check": "<one read-only shell command, run from the repository root, that
exits 0 when the state holds>"}]. Turn each open plan assumption this item settles into an
expectation with "from": "A<n>". Only what this plan
touches or relies on; not a general health check. Every path a step changes that exists today
needs a works or broken expectation; a new path needs an absent one.

DONE WHEN
- the result opens with one sentence naming the change and the checks that prove it
- each step has deps, criteria and paths; every criterion is satisfied by a step
- test_commands lists focused, regression and at least one check command (or check_na says why there is none), or test_commands_na says why
- paths lists every file the item changes; new architecture decisions are written as AD-<n>
- each step's skills list names a concrete use for each skill (or is empty)
- every existing thing a step changes or relies on has a works or broken expectation, and every new path an absent one, each with a check
Checked by: ShipLoop refuses an expectation without a check, state or known step, and an existing step path with no works or broken expectation, a skill locator that does not exist, test_commands with no check entry and no check_na, a step without criteria or paths, a step path the item does not
declare, a criterion no step satisfies, a step that only changes test files (unless the item
is all tests), a criterion no command names, and deps that are not earlier steps; then an
Improve child reviews the plan.
Outcomes: done | repeat | blocked.

RUN  result template (steps with criteria and paths) · Call this when done · Recovery · Pause
FILES  grounding: spec, feature spec, environment, architecture, test strategy (absolute
paths) · results this builds on: spec, test-strategy, plan · stage guide""",
    "kept": ["steps with deps (dependency order)", "test_commands focused/regression", "criteria and paths", "Improve review", "interaction-design and test-facility blocks (condensed)"],
    "moved": ["get-next-work-item's 'still required / prerequisites' check -> the first DO line (prerequisites accepted is listed by ShipLoop)", "baseline -> validate-existing, now gated and run by ShipLoop"],
    "added": ["expectations: the preconditions this plan relies on, each with a check, for validate-existing (owner 2026-10-10)", "helper skills chosen per step, with why, carried into that step's implement packet (owner 2026-10-10)", "step sizing rules and their gate", "a required check suite: each lint/type/build command from environment.md, or check_na (the static-check invocations static-checks relied on, now recorded once and refused when missing)", "the Consult block: spec, architecture, environment, test strategy with headings", "new AD-<n> written at step-plan"],
    "dropped": ["the design-basis / interaction-design duplication (merged, review finding: ~3.3k)", "three overlapping test handoffs (one paragraph)"],
  },
  {
    "id": "test-spec", "phase": "Plan", "name": "test-spec",
    "absorbs": [],
    "role": "Specify the cases before code: at least one per criterion, each with an independent oracle and a RED and GREEN definition.",
    "gate_before": "knowledge-home close (the test-spec file) + Improve review",
    "gate_after": "unchanged",
    "prompt": """DO
Goal: specify the tests this item needs before any code changes.
Consult and cite:
- spec (## Requirements): every case cites the R-<n> or criterion it proves; its oracle comes
  from the requirement's text, never from code.
- architecture.md (## Interfaces and boundaries): the boundary each case tests at (unit, the
  module's public interface, or the real boundary the requirement names).
- test-strategy.md (## ID convention, ## Real-boundary checks): case IDs and where a real
  boundary is required.
Cover positive, failure and boundary cases. Each case: ID (matching the step plan's focused
ids), the criterion, the input, the expected observation, RED (how it fails today) and GREEN.
Write them to <repo>/<feature>/test-spec.md.

DONE WHEN
- every completion criterion has at least one case, or a justified not-applicable
- each case has an independent oracle, a RED and a GREEN definition, and a matching ID
Checked by: ShipLoop refuses done until <feature>/test-spec.md exists and is non-empty; then an
Improve child reviews the cases.
Outcomes: done | repeat | blocked | revise.

RUN  template · callback · recovery · pause
FILES  grounding · results: spec, test-strategy, plan, step-plan · the test-spec file to write (absolute)""",
    "kept": ["one case per criterion, oracle, RED/GREEN", "Improve review"],
    "moved": [],
    "added": ["the file name test-spec.md and the ID match with the step plan (both missing today; the first live complete was refused for it)", "Consult block with headings"],
    "dropped": ["the duplicated facility and test-decision handoffs (one line)"],
  },
  {
    "id": "validate-existing", "phase": "Validate existing", "name": "validate existing (what we are about to change works before we change it)",
    "absorbs": ["baseline"],
    "role": "Before building, verify the things this item is about to change or rely on: each works today, is absent where it is new, or fails exactly as the request reports. When something we are about to change is found broken and the fix is known, fix it now, before the build, as its own commit.",
    "gate_before": "baseline: none (a model-run before-state report that no gate read)",
    "gate_after": "ShipLoop runs each expectation's check, and the check of each open plan assumption whose consumer is this item, on the item's base checkout, and compares each with its state (works: passes; absent: nothing there; broken: fails as described). All match: recorded and the run moves on with no model turn. Any mismatch: this packet; done is refused until ShipLoop's rerun matches every expectation. A preparatory fix must be its own commit touching only paths of the mismatched expectation. revise is accepted naming the expectation and what is true.",
    "prompt": """DO
Goal: verify that what this item is about to change works before we change it.
ShipLoop checked, on the unchanged base (<worktree> at the item's lint base):
  E1 works   <statement> (S1, S2)  check: <...>  -> PASSED
  E2 absent  <statement> (S3)      check: <...>  -> FOUND <what is there>
  E3 broken  <statement> (S1)      check: <...>  -> did not fail as reported
  A4 (plan assumption this item settles) <statement>  check: <...>  -> FAILED
INVOKE /until-loop NOW with the argument below, verbatim. Do this stage's work only inside that loop.
/until-loop
  Work (one iteration): take the first mismatched expectation; with a small discriminating
    observation, find whether the fact or the check is wrong; then act:
    - the check is wrong (the fact holds): stop and report revise naming the expectation and
      the corrected check, so step-plan records it (a check is never changed unseen);
    - a works expectation is broken and the fix is known and small: fix it now, before the
      build, as its own commit touching only that expectation's paths, with a message naming
      it; this is a preparatory fix, not the item's change;
    - the environment lacks it (a tool, service, setting): fix the environment and record it in
      environment.md (## Commands, ## Targets and runtimes);
    - an absent expectation finds something there, a broken one does not reproduce, or the fix
      is not known: stop and report revise with what is true, so step-plan reshapes the steps
      (a needed repair becomes an earlier step of this item);
    - the fix lies outside this run (another system, a person's access): stop and report
      blocked (blocked_by external or access) with what is needed.
    Then rerun every expectation's check.
  Exit when ALL of these hold (each shown by its check, after the last edit):
    1. every works expectation passes its check on the current checkout
    2. every absent expectation finds nothing at its place
    3. every broken expectation fails exactly as the request reports
    4. each preparatory fix is its own commit touching only its expectation's paths
  Repeat while: an expectation is mismatched and the latest iteration fixed the environment
    or a known defect; otherwise stop and report revise or blocked as above. Never stop
    cancelled: a user's stop is the packet's pause command.
  Contract (written by ShipLoop; start from it unchanged): <run>/loops/<id>-contract.json
  Receipt: <run>/loops/<id>-terminal.json
Never weaken an expectation or edit a check only to make it pass. Never start the item's own
change here: a broken expectation is the build's to fix.
Consult: step-plan (the steps and paths each expectation covers); plan (## assumptions);
environment.md (## Commands); architecture.md (## Structure, ## Interfaces and boundaries).

DONE WHEN
- the four exit conditions above hold, or revise names the expectation and what is true
Checked by: ShipLoop reruns every check, refuses done unless each matches its state, and
refuses a preparatory fix that is not its own commit or touches another path.
Outcomes: done | blocked | revise (an expectation is false and not fixable here).

RUN  each check with its saved output · the start command · template · callback · recovery
FILES  grounding · results: step-plan (expectations, steps, paths), plan (assumptions) · environment.md""",
    "kept": ["a before-state check on the unchanged base (what baseline was for), now scoped to what the plan touches"],
    "moved": ["the regression count on the base -> the test stage's base run (the floor)"],
    "added": ["expectations with states works / absent / broken, recorded by step-plan for every path it touches (owner 2026-10-10: verify what we are about to change works before we change it; the only exception is what does not exist yet)", "a known small fix to a broken precondition is made here, before the build, as its own commit (owner 2026-10-10)", "a 'broken as reported' expectation reproduces the item's own defect before it is fixed", "open plan assumptions this item settles are checked here", "a gate: ShipLoop runs the checks; when all match there is no model turn"],
    "dropped": ["baseline's general rerun of every suite (not tied to the plan; no gate read it)"],
  },
  {
    "id": "implement", "phase": "Build", "name": "implement (per step)",
    "absorbs": [],
    "role": "Make one planned step's change against its criteria, in the execution checkout.",
    "gate_before": "lint gate",
    "gate_after": "the lint gate, then an Improve child reviews this step's change before the next step starts (owner 2026-10-10: Improve after every implementation step); criteria are proven in the test stage",
    "prompt": """DO
Goal: make step S<k> (k of N): <the step's task>.
Criteria for this step: <C-ids and their text>. Paths: <the step's paths>.
Earlier accepted steps: <S1..>. Later steps: <..SN> (do not start them).
Skills for this step (chosen at step-plan): <name: why · locator>, one per line, or none.
Use each for the purpose given: invoke it through your host, or read its SKILL.md and follow it.
If one does not fit after all, say so in the result.
Consult and cite: spec (the R-<n> behind this step's criteria) for the behaviour;
architecture.md (## Structure, ## Interfaces and boundaries, ## Conventions) for where the code
goes and how it reads. Follow it; if you must deviate, record why as a new AD-<n> under
## Decisions before you finish. Record a newly working command in environment.md under
## Commands.
Make the change in the house style. After the last edit, run the static checks and fix what
they report:
  [check] <each recorded check command, numbered: lint, type, build>
  Lint: the ShipLoop lint command below. Tests are written in the next stage, from the
test spec, so do not write them here.
  python3 <cli> lint --run-dir=<run> --action=<id>  (ShipLoop also lints at done).

DONE WHEN
- the step's change is made on its paths, and the check commands pass after the last edit
- the lint gate reports no unwaived new finding on changed lines
Checked by: ShipLoop lints this item's changes and refuses done while a new finding on a
changed line has no waiver. Then an Improve child reviews this step: its change against the
step's task and criteria, code craft, architecture.md, and the use of the step's skills. The
child makes and commits warranted edits; the next step starts from its result.
Outcomes: done | repeat | blocked | revise (the step plan is wrong or unachievable).

RUN  the check commands and the runnable lint command · template · callback · Improve start · recovery
FILES  grounding · results: spec, plan, step-plan, test-spec (what the tests will check) · code-craft rubric (condensed)""",
    "kept": ["one reviewed step at a time", "lint gate", "change the work, never the check", "code craft (condensed to its obligations)"],
    "moved": ["the step's criteria, paths and focused tests are printed (they were only implied: the model grepped the file for 'S2')"],
    "added": ["an Improve review after every step (owner 2026-10-10)", "the step's helper skills, with why and how to use them", "Consult block; deviation recorded as AD-<n>", "a lint command that runs as printed (today's head printed one that cannot run)"],
    "dropped": ["lint described five times (once)", "the third delegation statement", "the service-change paragraph (to the reference)"],
  },
  {
    "id": "test", "phase": "Build", "name": "test (author, run, fix until green)",
    "absorbs": ["test-author", "test-red", "test-green", "test-refine", "regression", "static-checks (its tools)"],
    "role": "One Until Loop after implement: write every specified case as a test, run every recorded command (focused tests, regression suites, lint/type/build), and fix the code or the tests until all pass. The code must behave as the test spec defines.",
    "gate_before": "six stages: test-author (probe run), test-red (expect fail), test-green (loop + rerun focused), test-refine (rerun all), regression (loop + rerun all), static-checks' tool runs",
    "gate_after": "the lint gate; the loop's terminal packet against its contract; then two script runs. On the item's base checkout with only this item's test files applied: no new test ID passes (RED proved after the fact; red_na exempts a characterisation test), The regression count on the base is the floor. On the candidate: every command exits 0, runs every listed ID, and reaches the floor.",
    "prompt": """DO
Goal: the test spec's cases are tests, and every recorded command passes: the code behaves as
the test spec defines.
Consult and cite: test-spec.md (every case and its oracle); test-strategy.md (## Harnesses and
suites, ## ID convention); environment.md (## Commands); architecture.md (## Conventions) for
test style and seams; spec for what a failing behaviour should be.
Commands (ShipLoop runs each from <worktree> before accepting done):
  1. [focused] <cmd> (must run: TC-1..TC-n)
  2. [regression] <cmd>
  3. [check] <lint / type / build cmd>
Start the bound Until Loop once (ShipLoop wrote its contract; pass it unchanged):
  python3 <until_loop_ephemeral.py> start --receipt <run>/tests/<id>-terminal.json < <run>/tests/<id>-contract.json
Each iteration: write or fix the tests for any case not yet covered (titled with its ID as a
whole word, registered in the focused and regression commands, asserting the specified
behaviour exactly, from the spec's oracle and never from the code); run every command; for
each failure find the cause with a small discriminating observation (a product defect, an
invalid test, or the environment) and fix the product code. Change a test only for an
independent reason you record (a wrong oracle, a requirement change), never to make it pass,
and never delete or skip one. A repeated unchanged failure is not progress: change the
approach. The loop exits when one complete iteration after the last edit ran every command
and each exited 0; there is no iteration limit. Never write the receipt; after a reset, if it
exists, resume from it, do not restart.
A characterisation test that also passes without this item's change: give the reason in red_na.

DONE WHEN
- every case in the test spec is a test the focused command runs, with its ID in the name
- the loop's last iteration ran every command after the last edit and each exited 0
- every test change made to pass a run has a recorded independent reason
Checked by: ShipLoop lints this item's changes, checks the loop's terminal packet against its
contract, then runs the tests twice itself. On the item's base with only this item's test
files: it refuses if a new test ID passes there (unless red_na names it), so no test passes
without the change. On the candidate: it refuses unless every command exits 0, runs every
listed ID, and runs at least as many regression tests as the base run did. After 11 refused runs
done is no longer accepted: report revise.
Outcomes: done | blocked | revise (a case or check is unachievable as planned: name it).

RUN  start command · receipt (prefilled in evidence_refs) · template (red_na optional) · callback · recovery
FILES  grounding · results: test-spec, step-plan, implement · environment.md · test-strategy.md""",
    "kept": ["executable tests from the independent spec, never from the code", "ID word rule", "never weaken an assertion", "RED: no new test passes without the change (now a script run on the base)", "red_na for characterisation tests", "the bound Until Loop with its frozen contract, uncapped", "terminal-packet check then ShipLoop's own rerun", "test-count floor (from the base run)", "fix the code, not the checks; independent reason for a test change", "11 refused runs -> revise"],
    "moved": ["test-author's writing -> the first iterations of this loop", "test-red's expected failure -> a script run on the base checkout, after the fact", "test-green (focused) and regression (all) -> one loop over all commands", "static-checks' lint/type/build -> the check suite in this loop", "test-refine's 'tighten assertions' -> the oracle rule; its 'reconcile removed cases' -> the floor"],
    "added": ["one goal: the spec's cases exist and all commands are green", "Consult block", "the base-checkout run: new test IDs must not pass there (replaces test-red); its regression count is the floor"],
    "dropped": ["six stages and their packets, results and callbacks", "test-first ordering (the tests now follow the code; the base run keeps the proof that they detect the change)", "four ShipLoop reruns of the same commands (now one, plus the base run)", "the 'placeholder so a test can load' rule (the code exists by now)"],
  },
  {
    "id": "document", "phase": "Build", "name": "document",
    "absorbs": [],
    "role": "Document each changed public behaviour where users and maintainers look (only when something public changed).",
    "gate_before": "none",
    "gate_after": "none; issued only when the item changed a public behaviour (step-plan paths include code, or the plan says so); otherwise ShipLoop records not applicable",
    "prompt": """DO
Goal: update the documentation this change affects.
Consult: spec (the R-<n> this item changed) and architecture.md (## Structure, ## Interfaces)
for what is now true. Update the README, API and operator docs from the observed behaviour;
link to the authoritative home instead of copying it. Durable facts and lessons go in the
repository's docs, not in run notes.

DONE WHEN
- each changed public behaviour is documented where users and maintainers look
- each changed document was reread after the last edit
Checked by: ShipLoop refuses a result with a mechanical fault (outcome, summary, an evidence
path that does not exist, a credential pattern); you confirm each condition.
Outcomes: done | repeat | blocked | revise.

RUN  template · callback · recovery
FILES  grounding · results: spec, plan, step-plan, implement""",
    "kept": ["document from observed behaviour", "durable facts in repo docs"],
    "moved": ["the maintained-requirements reconciliation -> spec and carry-forward (it is planning knowledge)"],
    "added": ["conditional issue (script-decided)", "Consult block"],
    "dropped": ["code craft rubric (3.7k; nothing in documenting uses it)"],
  },
  {
    "id": "verify", "phase": "Verify", "name": "verify (+ review and integration)",
    "absorbs": ["verify", "static-checks (its review)", "integrate", "integration-verify"],
    "role": "Accept the item: each criterion confirmed by evidence made after the last edit, the change reviewed against code craft and the architecture, and (on chained or parallel work) the candidate assembled and its shared interfaces checked.",
    "gate_before": "verify: rerun all; static-checks: quality loop; integrate: none; integration-verify: rerun all",
    "gate_after": "on entry: change inventory and first-entry lint auto-fix (static-checks' entry runs, moved); at done: the quality loop's terminal packet against its contract, the lint gate, then one rerun of every recorded command including the check suite; the item commit happens on accept (it was integrate's); on the chained route, assembly is checked as today",
    "prompt": """DO
Goal: verify the item against its acceptance criteria, and review the change.
Consult and cite: spec (every R-<n> this item serves, and its criteria); architecture.md
(## Decisions, ## Interfaces and boundaries) to check the change follows them or records a new
AD-<n>; test-strategy.md (## Real-boundary checks) for any boundary a local test cannot prove.
On entry ShipLoop lints this item's changes (auto-fixing formatting once) and writes the change
inventory to <run>/quality/<id>-inventory.md: every changed file with its lint state. Review
from it.
Run this as one Until Loop, the quality loop static-checks used to run (contract written by ShipLoop):
  python3 <until_loop_ephemeral.py> start --receipt <run>/quality/<id>-terminal.json < <run>/quality/<id>-contract.json
Each iteration does 1-3:
1. For each criterion, name the command or inspection that confirms it now; stale, skipped or
   missing evidence is not a confirmation. A real-boundary gap stays pending with its owner.
2. Review the whole item's diff for what the per-step Improve reviews could not see: trace
   each changed public entry point with a valid, a boundary and an invalid input across all
   steps; check consistency between steps against code craft and architecture.md; fix what
   you find (the checks rerun at done).
3. Chained or parallel work only: assemble the steps' results in <worktree>, inspect the
   combined diff and the shared interfaces, and confirm the candidate builds as one.
Mark later-phase checks (system, release) pending with their owner.

DONE WHEN
- every criterion is confirmed on the current candidate, with evidence after the last edit
- each changed entry point was traced and reviewed; findings are fixed or recorded
- later-phase checks are marked pending with their owner
Checked by: ShipLoop checks the quality loop's terminal packet against its contract, lints
again (a new unwaived finding is refused), and reruns every recorded command, the check
commands included, refusing unless each passes (skipped when no file changed since the test
stage's accepted run). A criterion reported unconfirmable
whose check needed execution means revise.
Outcomes: done | repeat | blocked | revise.

RUN  template · callback · recovery
FILES  grounding · the change inventory · results: spec, test-strategy, step-plan, test-spec, implement, test""",
    "kept": ["criterion-by-criterion confirmation after the last edit", "unconfirmable-when-execution-required -> revise", "later-phase checks pending", "entry-point tracing and code craft (from static-checks)", "integration on chained/parallel work"],
    "moved": ["static-checks' change inventory and first-entry lint auto-fix -> verify's entry", "static-checks' review loop -> step 2 here (today verify takes 1 turn: the review gives it its job)", "integrate + integration-verify -> step 3, chained route only"],
    "added": ["Consult block (architecture decisions checked here)"],
    "dropped": ["integrate and integration-verify on the inline route (a no-op and a repeat of the same rerun)", "two more reruns of the same commands"],
  },
  {
    "id": "carry-forward", "phase": "Carry forward", "name": "carry-forward",
    "absorbs": ["skill-assess", "skill-validate"],
    "role": "Record the item's lessons in the knowledge home, revise the remaining queue, and decide whether a repeatable procedure deserves a local skill; on the last item, start the end-of-work review.",
    "gate_before": "Improve (last item); skill-assess and skill-validate: none (two stages, almost always N/A)",
    "gate_after": "the skill decision is required; a created skill's SKILL.md must exist with name and description; Improve on the last item",
    "prompt": """DO
Goal: record what this item taught and revise the remaining queue.
Update the knowledge home in place: environment.md (## Commands: every command that worked),
architecture.md (## Decisions: any AD-<n> this item added or superseded; never delete one,
move it to ## Superseded), test-strategy.md (## Harnesses and suites). Read every pending
item's title and context, then return work_items only if the queue changes: it replaces the
whole future queue, in prerequisite order.
Skill decision: would a local skill have made this work faster or more reliable, and will
that work repeat? Create one only when the same procedure was done in two or more steps or
items of this run, or a pending item or the spec says it will recur, and no existing skill
(host or local) already covers it; reuse or extend an existing one first. Otherwise record
"skill: none" and the reason. A new skill goes in the repository's local skill directory
(environment.md ## Skills) as <name>/SKILL.md with name and description frontmatter; try it
once on this run's real procedure and record the result.

DONE WHEN
- every still-required future item is in the queue, in prerequisite order
- learnings and durable knowledge are recorded in the knowledge home, not in run notes
- the skill decision is recorded: a new local skill with its repeat evidence and trial, or none and why
Checked by: ShipLoop screens the home for credentials and refuses a dropped R-<n> or AD-<n>;
refuses a result with no skill decision, or a named new skill whose SKILL.md is missing or lacks
name and description; then commits; on the last item an Improve child reviews all executed work.
Outcomes: done | repeat | blocked.

RUN  template (work_items optional; skill: {"decision": "created" | "none", ...}) · callback · Improve start (last item) · recovery
FILES  grounding · results: spec, plan, integration""",
    "kept": ["queue revision rule (once, not three times)", "durable knowledge outside run notes", "end-of-work Improve on the last item"],
    "moved": [],
    "added": ["explicit updates to environment / architecture / test-strategy by heading", "the repeatable-skill decision with a repeat test (owner 2026-10-10), replacing skill-assess and skill-validate"],
    "dropped": ["the queue-replace rule repeated three times; the Backchain/budget text (to the reference)"],
  },
]

CONTRACTS = {
  "test": {"work": "Write or fix tests for every test-spec case not yet covered, register them in the focused and regression commands, then run every recorded command (focused, regression, check); for each failure find its cause and fix the product code, or change a test only for a recorded independent reason.",
           "exit_condition": "Every case in the test spec is a test the focused command runs, and one complete iteration after the last edit ran every recorded command, each exiting 0 after running at least one test and every ID listed for it.",
           "repeat_condition": "Repeat while a case has no test or the latest iteration found a failing command and changed code or tests to fix it; there is no iteration limit; stop blocked only when the harness cannot run here.",
           "required_trivial_reviews": 0},
  "verify": {"work": "Confirm each criterion with a check made after the last edit; trace each changed public entry point with a valid, a boundary and an invalid input; review the diff against code craft and architecture.md; fix what you find and rerun the checks.",
             "exit_condition": "Every criterion is confirmed with evidence after the last edit, every changed entry point is traced, and the latest iteration found only trivial issues.",
             "repeat_condition": "Repeat while a criterion is unconfirmed or a review iteration finds a non-trivial issue; stop blocked on a missing prerequisite.",
             "required_trivial_reviews": 1},
}
CONTRACTS["validate-existing"] = {
  "work": "Take the first expectation whose check does not match its state (works: passes; absent: nothing there; broken: fails as the request reports); find with a small discriminating observation whether the fact or the check is wrong; fix the environment, or make a known small fix to a broken works expectation as its own commit touching only that expectation's paths; then rerun every expectation's check.",
  "exit_condition": "Every works expectation passes its check, every absent expectation finds nothing at its place, every broken expectation fails exactly as the request reports, and each preparatory fix is its own commit touching only its expectation's paths.",
  "repeat_condition": "Repeat while an expectation is mismatched and the latest iteration fixed the environment or a known defect; otherwise stop and report revise (a wrong check, an unknown fix, or a fact that changes the plan) or blocked (a fix outside this run). Never stop cancelled.",
  "required_trivial_reviews": 0}
CONTEXT_SHAPE = {"request": "the run's original request (verbatim) and this item's title and context",
                 "scope": "this item's paths from the step plan; the execution checkout at its item lint base",
                 "authority": "ShipLoop's commit rule for the item; no push; never edit the recorded commands",
                 "environment": "the execution checkout; the recorded commands from the step plan; environment.md's Commands",
                 "resources": [{"purpose": "living spec", "locator": "<repo>/docs/shiploop/spec.md"},
                               {"purpose": "architecture", "locator": "<repo>/docs/shiploop/architecture.md"},
                               {"purpose": "environment", "locator": "<repo>/docs/shiploop/environment.md"},
                               {"purpose": "test strategy", "locator": "<repo>/docs/shiploop/test-strategy.md"},
                               {"purpose": "bound loop skill", "locator": "<skills>/improve/runtime/until-loop/ADAPTER.md"}]}

OLD_TO_NEW = {
  "get-next-work-item": "step-plan", "step-plan": "step-plan", "test-spec": "test-spec", "baseline": "validate-existing",
  "test-author": "test", "test-red": "test (script run on the base)", "implement": "implement", "test-green": "test",
  "test-refine": "test", "regression": "test", "document": "document", "skill-assess": "carry-forward",
  "skill-validate": "carry-forward", "static-checks": "test (tools) / verify (review)", "verify": "verify",
  "integrate": "verify (chained route)", "integration-verify": "verify (chained route)", "carry-forward": "carry-forward",
}


# Coverage review 2026-10-10: four reviewers mapped every obligation of today's prompts and rewrote the stages
# they own in the owner's /until-loop shape. Their prompts, contracts and gates replace the earlier drafts;
# validate-existing keeps the owner's works/absent/broken version above, with the reviewers' route fixes folded in.
REVIEWED = {}
for group in ("plan-validate", "build", "verify-carry"):
    for st in json.loads((HERE / f"coverage-{group}.json").read_text())["stages"]:
        if st["id"] != "validate-existing":
            REVIEWED[st["id"]] = st
for stage in STAGES:
    r = REVIEWED.get(stage["id"])
    if r:
        stage["prompt"], stage["gate_after"], stage["notes"] = r["prompt"], r["gate_after"], r["notes"]
        CONTRACTS[stage["id"]] = r["contract"]

for stage in STAGES:
    stage["draft_chars"] = len(stage["prompt"])
    olds = [s for s, new in OLD_TO_NEW.items() if new.split(" ")[0] == stage["id"]]
    stage["old_stages"] = olds
    stage["old_stage_text_chars"] = sum(current[s]["stage_text_chars"] for s in olds)
    stage["old_duty_chars"] = sum(current[s]["duty_chars"] for s in olds)

for stage in STAGES:
    if stage["id"] in CONTRACTS:
        stage["contract"] = {"workspace": "<the item's execution checkout, absolute>", **CONTRACTS[stage["id"]], "context": CONTEXT_SHAPE}
(HERE / "drafts.json").write_text(json.dumps({"stages": STAGES, "old_to_new": OLD_TO_NEW, "current": current}, indent=1))
for s in STAGES:
    print(f"{s['id']:14} absorbs {len(s['old_stages'])}  old stage text {s['old_stage_text_chars']:6}  draft {s['draft_chars']:5}")
print("total old", sum(s["old_stage_text_chars"] for s in STAGES), "draft", sum(s["draft_chars"] for s in STAGES))
