# Coverage review of the inner-loop redesign: shared brief

## Context
ShipLoop is a script-owned SDLC navigator. For each stage it prints a "packet": a prompt telling the model what
to do, when the stage is done, what to run, and which files to consult. The model does one stage and then calls
`complete`. The script checks the result before the run moves on. **Context may be cleared between stages**
(SPEC S-6), so each packet must stand alone.

The owner is replacing the 17-stage inner loop (one work item) with 8 stages in 5 phases. The new prompts are
drafts. Your job is to make sure the drafts cover every obligation in today's prompts, and to rewrite your
stages in the owner's Until Loop shape.

## Sources (read-only; never edit them)
- Engine source, worktree `/Users/dadleet/src/skill-craft/.claude/worktrees/step-slice-32c6ee/skills/shiploop/`:
  - `scripts/shiploop_stage_spec.py`: the stage table (goal, done_when, develop, tools, entry_runs/complete_runs
    gates, reads, blocks, outcomes, improve);
  - `scripts/shiploop_prompts.py`: COMMON, DUTIES per stage, CODE_CRAFT, IMPROVE_* scopes, STAGE_REFERENCES,
    inner_context, STEP_SIZING, REQUIREMENTS_RULES;
  - `scripts/shiploop_navigator.py`: `_CHECK_TEXT` gate texts, the step-plan template, `_check_*` gates,
    `render`/`packet_head`, the delegated (ask-agent) route text;
  - `scripts/shiploop_test_loop.py`, `scripts/shiploop_quality.py`: loop contracts;
  - `SKILL.md`, `references/*.md`.
- `current.json` (this directory): today's per-stage goal, done_when, gates, duty text and blocks, extracted from the
  source above.
- `drafts.py` (this directory): the 8 draft stages. Each has role, gate_before/gate_after, prompt (DO / DONE WHEN /
  RUN / FILES), kept/moved/added/dropped, plus CONTRACTS and CONTEXT_SHAPE.
- `/Users/dadleet/src/skill-craft/test/shiploop_e2e/SPEC.md` (S-1..S-14) and
  `/Users/dadleet/src/skill-craft/.claude/worktrees/step-slice-32c6ee/docs/shiploop-inner-loop-stage-diagnosis-2026-10-10.md`.

## Owner decisions (2026-10-10; settled, do not argue against them)
1. **The 8 stages.**
   - Plan: step-plan, test-spec.
   - Validate existing: validate-existing.
   - Build: implement × steps, each followed by an Improve child review; test; document (only when public
     behaviour changed).
   - Verify: verify.
   - Carry forward: carry-forward.
2. **validate-existing** checks only what this plan expects to be true before implementation:
   - the expectations step-plan records (`expectations: [{id, statement, steps, check}]`);
   - open plan assumptions whose consumer is this item.

   It is not a general health check. ShipLoop runs the checks itself. When all hold, there is no model turn.
3. **test comes after implement.** It writes every test-spec case as a test, runs every recorded command
   (focused, regression, check), and fixes the code or the tests until all pass.
   - RED is checked by script: the new test IDs must not pass on the item's base checkout. `red_na` exempts a
     characterisation test.
   - The base regression count is the floor.
4. **Static checks.**
   - step-plan must record check commands (lint, type, build) or `check_na`.
   - implement runs them, and the test loop runs them.
   - verify takes static-checks' change inventory, its first-entry lint auto-fix and its quality loop, plus
     integrate's item commit.
   - On chained or parallel work, verify assembles the steps' results and checks the shared interfaces.
5. **Skills.**
   - step-plan picks helper skills per step (`skills: [{name, why, locator}]`), and the implement packet prints
     them.
   - carry-forward records a skill decision: create a local skill only when the procedure repeated or will
     recur and no existing skill covers it.
   - skill-assess and skill-validate are removed.
6. **Removed stages:** baseline, test-author, test-red, test-green, test-refine, regression, static-checks,
   skill-assess, skill-validate, integrate, integration-verify, get-next-work-item. get-next-work-item becomes a
   script check plus a "still required" line in step-plan.
7. **The knowledge home grounds every stage**, each file cited by heading: spec.md, architecture.md (AD-<n>
   decisions), environment.md and test-strategy.md. A deviation from architecture is recorded as a new AD-<n>.
8. **Every stage prompt is an Until Loop** (owner, latest). The packet specifies:
   - **the work** of one iteration;
   - **the exit conditions** that must be verified before the stage may finish;
   - **the repeat condition**.

   ShipLoop writes the contract in the runtime's exact schema:
   - `workspace`;
   - `work`;
   - `exit_condition`;
   - `repeat_condition`;
   - `required_trivial_reviews`;
   - `context`, made of `{request, scope, authority, environment, resources: [{purpose, locator}]}`.

   The packet prints the exact start command:
   `python3 <until_loop_ephemeral.py> start --receipt <abs> < <abs contract.json>`.

   The model cannot invoke /goal or the /until-loop Skill, so this script route is the mechanism. After the loop,
   the stage gate re-checks by script whatever it can.
9. **Packet shape** is four parts: DO / DONE WHEN / RUN / FILES. It stays concise; detail a stage rarely needs
   goes to the run reference file `run/reference.md#<section>`. Repetition across packets is fine.
10. **One supported version:** no compatibility text for old runs.

## Your output
Write ONE JSON file at the path given in your task:

```json
{
  "group": "...",
  "obligations": [
    {"old_stage": "...", "source": "<file>:<symbol>", "obligation": "<one line>",
     "status": "covered | moved | intentionally-dropped | MISSING | CONTRADICTED",
     "where": "<new stage + quoted draft phrase, or reference.md section, or the owner decision # that drops it>",
     "fix": "<replacement or added text when MISSING/CONTRADICTED, else empty>"}
  ],
  "stages": [
    {"id": "<new stage you own>",
     "prompt": "<the full revised prompt: DO (goal, Consult block, the Until Loop start line, the work of one iteration) / DONE WHEN (the exit conditions, each one verifiable) / RUN / FILES>",
     "contract": {"work": "...", "exit_condition": "...", "repeat_condition": "...", "required_trivial_reviews": 0},
     "gate_after": "<what ShipLoop checks by script after the loop: each exit condition mapped to its script check, or 'model evidence' when no script can check it>",
     "notes": "<anything the owner must decide>"}
  ]
}
```

## Rules
- **Be exhaustive on obligations.** That means every done_when line, every operative sentence in DUTIES and
  `develop`, every gate in `_CHECK_TEXT`, every Improve focus item, and every block (code-craft and others) the
  old stages carry.
- **Ignore pure repetition.** If two old stages state the same obligation, it is covered when one draft covers
  it.
- **Exit conditions must be observable.** Each is something a command, a file or a script check shows; never
  "the model is satisfied".
  - Each exit condition must equal or imply what the gate refuses, so the loop cannot exit on something the
    gate then rejects.
  - `required_trivial_reviews` is 1 only for a review-style loop (verify), else 0.
- **Keep prompts concise.** Cut nothing operative. Prefer one exact sentence over three.
- **Cite symbols, not line numbers.**
- **Do not edit any file except your output JSON.** Do not run ShipLoop itself; reading the source and tests is
  fine.

## Amendment (owner, after launch): the loop is invoked by name, in strong words
Every stage prompt's DO opens its loop with this block; adapt only the bracketed parts:

```
INVOKE /until-loop NOW with the argument below, verbatim. Do this stage's work only inside that loop.
/until-loop
  Work (one iteration): <the work>
  Exit when ALL of these hold (each shown by a command or file, after the last edit):
    1. <exit condition>
    2. ...
  Repeat while: <repeat condition>
  Contract (written by ShipLoop; start from it unchanged): <run>/loops/<id>-contract.json
  Receipt: <run>/loops/<id>-terminal.json
How to invoke: on Claude Code, the Skill tool with skill "until-loop" and this argument; on any host, open the
card <abs until-loop ADAPTER.md> and follow it with this argument. Either way the loop starts with:
  python3 <abs until_loop_ephemeral.py> start --receipt <receipt> < <contract>
```

The exit conditions in the argument must be the same text as the contract's exit_condition, and as the DONE WHEN
list. Write them once, in the same words.

## Amendment 2 (owner): validate-existing verifies what we are about to change
Expectations carry a state: works (an existing thing a step changes or relies on works today), absent (a new thing
does not exist yet and its place is free), broken (the request says it is broken; the check reproduces it). Every
existing path a step changes needs a works or broken expectation; every new path an absent one. When a works
expectation is found broken and the fix is known and small, validate-existing fixes it before the build as its own
commit touching only that expectation's paths; otherwise revise. drafts.py holds the current validate-existing text.
