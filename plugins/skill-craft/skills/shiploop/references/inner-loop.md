# The inner loop

Split from the ShipLoop skill card (`../SKILL.md`). Read when an inner stage
(`step-plan` through `reflect-and-revise`) needs the rule behind its packet, or
a stage reports `send-back`.

Each work item runs 7 stages in 4 phases (`INNER` in
`scripts/shiploop_stage_spec.py`):

| Phase | Stages |
|---|---|
| Plan | `step-plan`, `test-spec` |
| Validate existing | `validate-existing` |
| Build | `implement`, `test`, `document`, once per step |
| Reflect and revise | `reflect-and-revise` |

- `step-plan` records the item's `steps`, `paths`, `criteria`, test commands
  (with at least one check command, or `check_na`), `expectations` and each
  step's helper `skills` ([test loop](test-loop.md#test-loop), [expectations](#expectations-and-validate-existing)).
- `test-spec` writes one `### <ID>` case per criterion a test confirms, before any
  code changes; ShipLoop refuses a case ID that no focused command lists, and a
  focused ID with no case. The cases follow this step; the plan keeps every primary
  requirement in some work item's `follows`
  ([glossary](glossary.md)). Cases due at a later stage go under `## Due later` (read
  by `system-test-author`); criteria confirmed `searched` or `inspected` go under
  `## Not tested here`.
- `validate-existing` confirms the expectations on the unchanged checkout.
- `implement` builds one step per action; the lint gate runs on every step.
- `test` writes the step's tests and makes every recorded command pass, then
  ShipLoop runs its base and candidate runs.
- `document` is issued only when the step's diff touches a code or test path
  (`item_scope.behavioural`), else recorded not applicable. It updates the docs
  and records what the step showed in KNOWLEDGE; at done ShipLoop lints its lines
  and reruns what its edits could affect. Improve then reviews the step, tracing
  each changed entry point, and ShipLoop commits it
  ([commit stage](navigator.md#step-commits)). `verify` is retired.
- `reflect-and-revise` updates the knowledge home and queue and records a
  [skill decision](#reflect-and-revise-skill-decision). A replaced queue keeps every
  primary requirement in some item's `follows`.

From `test-spec` through `document`, a goal that proves wrong goes back to the
step plan ([Send-back](#send-back-back-to-the-step-plan)).

## Stage Until Loops

`plan` and every inner stage run inside one Until Loop started with one literal command on
every host. On entry ShipLoop writes `loops/<action>-contract.json`
(`shiploop_loops.contract_writes`): the stage's work, numbered Done-when exit conditions,
and repeat condition. At `plan`, the loop iterates isolated experiments under
`RUN/experiments/` (0 experiments finishes on iteration 1). The packet prints `RUN the
Until Loop now, once, before any work`, the `python3 <runtime> start --receipt <receipt> < <contract>`
command, and to follow each instruction until complete or stopped. Only `test` prints the
argument (`----- BEGIN until-loop ARGUMENT -----` to END); other stages print `Contract:
<abs> · Receipt: <abs>` and read Work, Exit and Repeat from the runtime's instructions
(decision 20). The block ends with the result rule (list the receipt in `evidence_refs`,
submit via the callback, and report the five runtime done-report fields). The runtime
rewrites `loops/<action>-terminal.json` at every step; Never write or edit the receipt, and never re-start
an active receipt (run its `next_argv` instead; once started, the block prints the resume
line). The runtime comes from the selected Improve card's `runtime/until-loop` or the
bundled Improve skill.

At `complete` ShipLoop reads the receipt that the result names in `evidence_refs`
and compares it with the contract rebuilt from run state, never the file on disk
(`loops.check_terminal`). It refuses an outcome the stage does not accept,
a missing or still-active receipt and a packet from another contract; `blocked`
needs no receipt when the loop never started. Every stage exits on its first
iteration whose exit assessment holds. There is no iteration limit.

`shiploop check` runs `complete`'s gates on a result and accepts nothing; `complete` takes its yes (`checks/`,
state-files.md). The Checked-by line says to run the callback with `check` in place of `complete`; the
step-plan loop checks each draft. A duplicate command runs once.

## Expectations and validate-existing

`step-plan` records item facts:
`"expectations": [{"id": "E1", "state": "works" | "absent" | "broken", "statement": "...", "steps": ["S1"], "paths": ["src/a.js"], "check": "<one shell command>", "from": "A3"}]`.
Each read-only command exits 0 when the state holds: `works`, an existing thing works today;
`absent`, a new path is free; `broken`, the reported failure reproduces. ShipLoop
refuses a step plan if a changed path lacks an expectation, a new path lacks `absent`,
a check writes, or an open item due here is omitted from `from`
(`expectations.check_step_plan`).

On `validate-existing` entry ShipLoop checks every expectation on the unchanged tree;
if all match, it marks the stage done by script. Otherwise, small known `works` fixes
edit only those paths uncommitted (`done` reruns checks and makes a preparatory commit;
`test` base runs start there). Wrong checks, unknown fixes, or plan-changing facts report
`send-back` with `failed_expectations: [{"id", "actual", "route": "check" | "steps"}]`.

## Reflect-and-revise skill decision

`done` records `"skill": {"decision": "none" | "reuse" | "update" | "create", "reason", "path", "evidence"}`.
`update`/`create` require an existing `SKILL.md` (`name`, `description` frontmatter) and
repeat `evidence`, and commit the skill directory ([contract](reflect-and-revise.md)).

## Send-back: back to the step plan

A fixable problem is never `blocked`. When a work item's goal proves wrong or
unachievable while it is being built, or a requirement must change, `test-spec`
through `document` report `send-back`: the item goes back to `step-plan` with
that result as evidence, and step-plan revises such a requirement and re-plans.
No count of send-backs stops an item (state.md `revisions`). A loop that stops
blocked for either reports `send-back`; a cancelled loop is refused (stop is `pause`).

Fix forward: accepted `document` steps stay done. On `send-back`, the current
step's results drop while edits stay. When non-final `Sk` (with remaining steps)
is valid and ready to commit while `S(k+1)..Sn` must re-sequence, `document` may
emit `done` with `replan_remaining: {"reason", "affects"}`: ShipLoop commits
`Sk`, recaptures the lint base, and returns to `step-plan` keeping `Sk` done.
In both routes, the amended step-plan starts `steps` with the printed done rows
unchanged (`"done": true`), then remaining steps. Fixes to done work add a new
step with new criteria; accepted due cases stay settled without reopening.

## After reflect-and-revise

After the navigator accepts `reflect-and-revise` and imports its Improve
completion, the locked transaction marks the item done, keeps its evidence, and
opens the next item's `step-plan` or returns ownership to `system-test-author`. Root status and queue remain global. At a PRELUDE or OUTER
stage an active Improve child resumes through its own recorded state. A blocked child or producer keeps the parent action
incomplete rather than creating a hidden success edge.
