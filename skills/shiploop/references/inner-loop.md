# The inner loop

Split from the ShipLoop skill card (`../SKILL.md`). Read when an inner stage (`step-plan` through `carry-forward`) needs the rule behind its packet, or a stage reports `send-back`.

Each work item runs 8 stages in 5 phases (`INNER` in
`scripts/shiploop_stage_spec.py`):

| Phase | Stages |
|---|---|
| Plan | `step-plan`, `test-spec` |
| Validate existing | `validate-existing` |
| Build | `implement` (one action per step), `test`, `document` |
| Verify | `verify` |
| Carry forward | `carry-forward` |

- `step-plan` records the item's `steps`, `paths`, `criteria`, test commands
  (with at least one check command, or `check_na`), `expectations` and each
  step's helper `skills` ([test loop](test-loop.md#test-loop), [expectations](#expectations-and-validate-existing)).
- `test-spec` writes one `### <ID>` case per criterion a test confirms, before any
  code changes; ShipLoop refuses a case ID that no focused command lists, and a
  focused ID with no case; last item: a primary requirement no case names
  ([glossary](glossary.md)). Cases due at a later stage go under `## Due later` (read
  by verify and `system-test-author`); criteria confirmed `searched` or `inspected`
  go under `## Not tested here`.
- `validate-existing` confirms the expectations on the unchanged checkout.
- `implement` makes one step per action. The lint gate runs on every step and an
  Improve stage reviews every accepted step. Tests are written later, at `test`.
- `test` writes the specified tests and makes every recorded command pass;
  ShipLoop then runs its own base and candidate runs.
- `document` is issued only when the item's real diff touches a code or test
  path (`item_scope.behavioural`); otherwise ShipLoop records it as not applicable.
- `verify` reruns every recorded command, traces each changed entry point and
  reviews the whole diff. When `verify` is accepted ShipLoop commits the rest
  of the item ([step commits](navigator.md#step-commits) came first).
- `carry-forward` updates the knowledge home and the queue and records a
  [skill decision](#carry-forward-skill-decision).

From `test-spec` through `verify`, a goal that proves wrong goes back to the
step plan ([Send-back](#send-back-back-to-the-step-plan)).

## Stage Until Loops

Every inner stage does its work inside one Until Loop, started with one literal
command on every host. On entry to the stage's action ShipLoop writes the loop
contract `loops/<action>-contract.json` (`shiploop_loops.contract_writes`): the
stage's work, its exit condition (the stage's Done-when lines, numbered) and its
repeat condition. The packet's loop block says `RUN the Until Loop now, once,
before any work`, then prints the start command,
`python3 <runtime script> start --receipt <receipt> < <contract>`, and says to follow each instruction it prints
until the receipt's status is complete or stopped. Only the test stage's packet
prints the argument (`----- BEGIN until-loop ARGUMENT -----` to END), as its
floors use its numbering. Every other stage prints `Contract: <abs> · Receipt:
<abs>`, and the runtime states the contract's Work, Exit and Repeat in each
instruction it prints (decision 20). The block ends with the result: list the receipt
in `evidence_refs`, run the callback, and if that refuses for the loop, run the
start command again; it also lists the five fields of the runtime's done report.
The `--receipt` makes the runtime rewrite the receipt at every step, the final state last,
at `loops/<action>-terminal.json`. Never write or edit the receipt. A second start
on one receipt resets the loop (the runtime does not refuse it), so the RUN line
says to run an active receipt's `next_argv` instead, and once the receipt exists
the block leads with the resume line in place of the RUN line and the start
command. The runtime is the selected Improve card's `runtime/until-loop`, or
else that of the Improve skill bundled beside ShipLoop.

At `complete` ShipLoop reads the receipt that the result names in `evidence_refs`
and compares it with the contract rebuilt from run state, never the file on disk
(`loops.check_terminal`). It refuses an outcome the stage does not accept,
a missing or still-active receipt and a packet from another contract; `blocked`
needs no receipt when the loop never started. `verify` exits only after one
complete iteration that finds only trivial issues; every other stage exits on
its first iteration whose exit assessment holds. There is no iteration limit.

`shiploop check` asks whether ShipLoop would accept the result now: it runs the
same evaluator as `complete`, accepts and counts nothing, and records one answer
in `checks/<action>.md` (yes, or no with the first refusal). `complete` takes a
yes whose key still matches (the revision, the package version, the loop
contract, the draft, the working tree, the item's base, the counted runs the
floors read and the lint option) without running any gate again; any change
makes it run them all. Each inner packet prints the check command beside its
callback; the step-plan loop runs it on every draft. A duplicate command runs
once; records: state-files.md `tests/` and `checks/`.

## Expectations and validate-existing

`step-plan` records the facts the item builds on:
`"expectations": [{"id": "E1", "state": "works" | "absent" | "broken", "statement": "...", "steps": ["S1"], "paths": ["src/a.js"], "check": "<one shell command>", "from": "A3"}]`.
Each check is one read-only shell command, run from the repository root, that
exits 0 when the stated state holds: `works`, an existing thing works today;
`absent`, a new path's place is free; `broken`, the failure the request reports
reproduces. ShipLoop refuses a step plan when an existing path a step changes
has no works or broken expectation, a new path has no absent one, a check
writes, or an open plan assumption this item consumes is not named in a `from`
(`expectations.check_step_plan`).

At `validate-existing` entry ShipLoop runs every check on the unchanged
checkout. When all match, it records the stage done by script and issues no
packet. Otherwise the packet lists each check's result. A works expectation
found broken whose fix is known and small is fixed in this stage, touching only
that expectation's paths. Do not commit it: on `done` ShipLoop reruns every
check, refuses a mismatch or a change outside those paths, and on accept commits
the fix as its own preparatory commit. The test stage's base run starts from
that commit. A wrong check, an unknown fix or a fact that changes the plan is
`send-back`, with `failed_expectations: [{"id", "actual", "route": "check" | "steps"}]`.

## Carry-forward skill decision

A done `carry-forward` records `"skill": {"decision": "none" | "reuse" | "update" | "create", "reason", "path", "evidence"}`.
For `update` and `create` ShipLoop refuses a `path` that is not an existing
`SKILL.md` with `name` and `description` frontmatter, or empty repeat `evidence`,
and on accept commits the skill's directory. When to create or update a skill:
[carry-forward contract](carry-forward.md).

## Send-back: back to the step plan

A fixable problem is never `blocked`. When a work item's goal proves wrong or
unachievable while it is being built, from `test-spec` through
`verify`, the stage reports `send-back`: the item goes back to
`step-plan` with that result as evidence, and its earlier results from the step
plan on stop counting as current. No count of send-backs stops an item;
state.md `revisions` records how many there were. A script-run loop has no iteration limit: it runs until its
exit condition holds. One that stops blocked because the item's goal proved wrong
reports `send-back`; a cancelled loop is refused, because a user's stop is the
packet's `pause` command. The per-item
count is kept in `state.md` `revisions`. The redone step-plan packet names the
item's previous step plan and the result that sent it back (both under
`results/`) and asks for an amendment: its Done-when has the summary say which
rows are new or changed and which are carried over.

## After carry-forward

After the navigator accepts `carry-forward` and imports its bound Improve completion, the
locked state transaction marks the completed item, retains its evidence, and
either creates the next item's `step-plan` action or returns ownership to
`system-test-author`. Root status and queue remain global. At a PRELUDE or OUTER
stage an active Improve child resumes through its own recorded state. A blocked child or producer keeps the parent action
incomplete rather than creating a hidden success edge.
