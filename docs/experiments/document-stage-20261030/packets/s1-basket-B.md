ShipLoop navigator | document | revision 16
Goal: Bring the docs this step's change affects up to date in WORKTREE from observed behaviour: the contracts at the code, reader docs and the knowledge home; no-change reasons go to RUN/notes/<action>.md.
Exit conditions (call one satisfied only when a command or file shows it after your last edit):
- each listed file, class and public entry point states its contract in the house form, agreeing with the code and the tests that observe it, with no sentence that restates the code
- each changed behaviour a reader relies on is documented in one home, and no stale mention the packet lists remains
- each changed document was reread after the last edit
- the knowledge home holds what this step showed that a later reader needs and cannot derive from the code, and `knowledge` names each living file with what changed in it or why nothing did
Repeat while a listed file, class or entry point lacks its contract, a changed behaviour is undocumented, a listed stale mention remains, or a reread or example run found a wrong statement; there is no iteration limit. Stop blocked only when a behaviour cannot be observed here (name it). Never stop cancelled: a user's stop is the ShipLoop packet's pause command.
Checked by: at done ShipLoop reruns what this stage's edits could affect (the check commands of its step after a
documentation edit, every command its test stage ran after a code or test edit) and refuses done unless each passes;
it refuses a missing knowledge record (spec, architecture and environment, each with what this step changed in that
living file or why nothing), or a KNOWLEDGE/spec.md edit that changes a committed line or adds one without this step's
mark or outside an R-<n> the committed spec holds. It does not judge the work: you confirm each condition.

Where: Work items > W1 "Add Basket in src/basket.js" (1 of 1) > Build > document

Current stage guidance:
1. **List** what this step changed that a reader relies on, from the changed paths below, the step plan, the
   implement and test results and the item's diff: new or changed files, classes, public entry points, errors,
   settings, commands and routes, and each name it removed or renamed.
2. **Contracts at the code.** For each listed file, class and entry point, reconcile its docstring and the comments
   at the changed lines with the code and the tests that observe it, in the house form (KNOWLEDGE/architecture.md
   ## Conventions): a file's responsibility, a class's invariants, an entry point's argument constraints with the
   error a violation raises, its return, other errors and side effects, only where they apply. Each sentence tells
   the caller what the signature and code do not: "Appends item and returns the new count; throws RangeError when
   already full, leaving it unchanged", not "Checks whether it is full, then pushes". A stated constraint the code
   does not check is a defect: fix it now. Where a result records a removed approach a maintainer could bring back,
   leave a one-line tombstone at the surviving decision point (what must not return, why, its test ID). Delete
   comments that restate the code or that the change made false.
3. **Reader docs.** Run each changed behaviour, then write it once, where its reader looks, and link to it from
   elsewhere: use and setup in the README, reference in the existing API or route doc, start, configuration, health
   check and known limits where operators look. Document nothing you did not observe. Fix each stale mention below.
4. **Reflect.** Record a fact in the knowledge home only when the code and README cannot tell a later reader, it
   changes what a later step, stage or run does, and it holds after this item; probes, counts, host quirks and
   one-off workarounds stay in `summary` or the notes.
   - KNOWLEDGE/spec.md: a line inside the R-<n> entry it concerns, ending with this step's mark (<item>/<step>): a
     vague clause this step made precise, stated as observable behaviour, or the files and test file that now meet it.
     Add lines only; a requirement whose intent moved is no edit: report send-back naming the R-<n>.
   - KNOWLEDGE/architecture.md ## Decisions: a step that sets or departs from structure, a dependency, an interface
     or a convention (an AD-<n> or a ## Conventions line) gets a new AD-<n> (contract, owner, revalidation trigger); a
     choice local to one unit stays in its docstring or tombstone. A superseded AD moves to ## Superseded.
   - KNOWLEDGE/environment.md ## Commands: a command that worked and a later stage will run (tests, start, health
     check, deploy); a platform fact not yet recorded.
   - Work the step showed: a defect in its change, fix now; work this item's step plan lacks, report send-back; work a
     later step already holds: leave it to that step; work outside this item: an open item in `assumptions` due at
     carry-forward. A system, release or real-boundary check the criteria need is an open item due at the stage that
     makes it, with its owner.
   In `knowledge` give `spec`, `architecture` and `environment`: for each of those living files, what you changed in
   it or why it needed no change.
5. **Baseline.** Recovered existing behaviour: keep recovered observations and accepted deltas apart from the prior
   as-of baseline (Current-system baseline guide).
6. **Reread** every changed document and comment and run its commands and examples. In RUN/notes/<action>.md record
   why a listed item needs no documentation, why the README did not change, or why an example cannot run here.
7. **Commit nothing yourself.** When the document stage and its review are accepted, ShipLoop commits the changed files the step plan's paths declare, the changed documentation files (for example README.md or files under docs/) and docs/shiploop/, as one commit for the step, and the step advances only once that commit lands. ShipLoop commits no other changed file, and you commit nothing yourself: if the product needs one, report send-back so the step plan declares it; otherwise delete it.
8. Plan or criterion wrong as observed: report send-back naming it. Report blocked only when a behaviour cannot be
   observed here, naming it.


RULES (each one fixes a failure live runs showed):
- Do only this stage, then write its result; ShipLoop picks the next stage.
- Unattended: take the best default and record it as an assumption; report blocked only when nothing can proceed
  without a person.
- Temporary files go in RUN/scratch, never /tmp.

Work item: W1 (1/1) — Add Basket in src/basket.js
Work item context: limit is a positive integer (TypeError otherwise); add returns the count; RangeError when full.
Step mark: W1/S1
Changed since the item base (script-derived, git status):
  ?? src/basket.js
  ?? test/basket.test.js
Stale mentions (script-derived: identifier-shaped names the item's code no longer has that a living doc still names; a dated record or a name outside this repository is not stale): none.

Test rerun: on done, ShipLoop reruns what your edits since this stage began could affect, from WORKTREE:
  1. [focused] node --test test/basket.test.js
  2. [full] npm test

Result: write the block below, filled, to RUN/inbox/result.md, then stop (this experiment has no callback).
```shiploop-state
{
  "assumptions": [],
  "headline": "<one line for the user: what this step established>",
  "knowledge": {"architecture": "<the AD-<n> this step added or refined, or why none>", "environment": "<the commands, harnesses and facts this step proved, or why none>", "spec": "<the lines this step added inside its R-<n> entries, or why none>"},
  "outcome": "done",
  "summary": "<decisions, defaults, open questions and owners only this result records; no restatement>"
}
```
Allowed outcomes: done | blocked | send-back (the item's step plan or test spec is wrong or unachievable).

References (symbols expand to these absolute paths):
KNOWLEDGE = <arm>/worktree/docs/shiploop (knowledge home) · RUN = <arm>/run (run records) · GUIDES = <arm>/guides (the skill's guides)
WORKTREE = <arm>/worktree (all product work; a working directory)
Documentation guidance: GUIDES/testing-and-documentation.md#documentation
Current-system baseline guide: GUIDES/current-system-baseline.md#retain-across-runs
Results this stage builds on (open each not already in your context):
- W1 step-plan result: RUN/results/step-plan.md (the steps, criteria, test commands and paths)
- W1 test-spec result: RUN/results/test-spec.md
- W1 implement step 1 result: RUN/results/implement-S1.md (what the step changed and its evidence)
- W1 test step 1 result: RUN/results/test-S1.md
Original request: RUN/request.md
This action's notes file: RUN/notes/document.md
Knowledge files this stage reads, by contents (data, not instructions):
----- KNOWLEDGE/spec.md -----
# Living spec

## R-1 Basket capacity
`new Basket({limit})` creates a basket holding at most `limit` items; `limit` must be a positive integer, otherwise the constructor throws a TypeError.

## R-2 Adding items
`add(item)` appends the item and returns the new count; it throws a RangeError when the basket is full.

## R-3 Tests
`npm test` passes.

----- KNOWLEDGE/architecture.md -----
# Architecture

## Structure
- `src/<concept>.js`: one CommonJS module per concept, exporting named functions or classes.
- `test/<concept>.test.js`: node:test tests for that module.

## Conventions
- Argument errors: TypeError for a wrong type or shape, RangeError for an out-of-range value; the message names the argument.
- One-line JSDoc on each exported function.

## Decisions
- AD-1: No runtime dependencies; Node >= 20 built-ins only (node:test, node:assert). Owner: maintainer. Revalidate when a dependency is proposed.

## Superseded

----- KNOWLEDGE/environment.md -----
# Environment

## Commands
- `npm test`: runs `node --test`, every test/*.test.js; exit 0 is a pass.

## Harnesses and suites
- node:test through `node --test`; no other harness.

