# Run options

Split from the ShipLoop skill card (`../SKILL.md`). Read before choosing `--delegation`, `--lint` or `--planning-review` at `workspace start` or `init`, and before `delegation --set` or `lint-mode --set`.

## Execution delegation

A new run from `workspace start` or `init` records `delegation:
inline`: this conversation is the only writer and executes every assignment,
including Improve and implementation steps, without native workers.
Inline Improve checkpoints run the `improve` skill here, reviews and checks
included, and start no reviewer, test-runner or executor agent unless the user
asked for independent review.

Pass `--delegation agents` at `workspace start` (or direct `init`) for the
direct native-agents hybrid route: every producer stage stays inline in this
conversation (with optional F17 read-only fan-out in `discovery`, `research`,
and `product-acceptance`, and optional read-only failure-diagnosis fork in
`implement`/`test`), while Improve checkpoints run in
one direct coding-capable native worker from `CHILD/worker-brief.md` with a
2-line emit-time host hint from `references/host-bindings.json` (forked for
planning/outer reviews where supported, fresh for `document` and `reflect-and-revise`
code reviews; the parent collects the native return and interprets findings
before `complete`, which carries `--review-mode=fork|fresh`, replaced with
`--review-mode=fresh` on fork→fresh fallback or `--review-mode=inline-fallback`
when a host has no subagent tool;
see [direct review workers](improve-context.md#direct-review-workers-delegation-agents)).

Pass `--delegation ask-agent` at `workspace start` (or direct `init`) to opt in
to the legacy Ask Agent route (`improve-agent` + fresh INNER workers). Every run records the
setting; a saved run without it is refused with an error naming the missing
`delegation` key. An `init` or `workspace start` retry cannot change it. For an
existing run, use:

```sh
python3 "$CLI" delegation --run-dir "$RUN_DIR" --set inline   # or agents, ask-agent
```

The setting applies from the next issued action: the action pending when you
switch, including its Improve checkpoint, keeps the route it was issued with
(the packet says so), so a worker or bound child that may already own it
is never re-routed. It is refused on a halted or done run; setting the recorded
value is a no-op. `graph-dry-run --delegation inline|agents|ask-agent` previews
any route (inline by default); `shiploop host-binding` prints the detected host
and its `host-bindings/v2` data read-only.

## Script-owned lint

A new run records `lint: fix`. On inner-loop start ShipLoop snapshots the item
base, then for changed files discovers built-in ruff/shellcheck, repo-configured
linters (eslint, prettier, tsc, mypy, black, markdownlint-cli2, yamllint,
gofmt, clang-format, phpcs, rubocop; actionlint, terraform fmt and ktlint
whenever on PATH), and fallback `npm run lint` / `make lint`. pre-commit is
never run; nothing is ever installed.

- **Lint gate.** `complete` with `done` on `implement` (every step), `test`,
  `document`, and step-review import lints changed files and applies safe
  changed-line fixes. It refuses once after an auto-fix (rerun the step's
  checks), and while a new changed-line finding, a base-compared new regression
  elsewhere in a changed file (such as a newly unused import or variable), or a
  Tier-0 Python shadowed top-level `def`/`class` lacks a `lint_waivers` entry
  (`[{"id", "reason"}]`). Pre-existing `at-base` findings, uncompared
  repo-linter `unattributed` findings, missing tools, tool errors, timeouts and
  an unrun pass never refuse. At `test` and `document`, the gate precedes
  ShipLoop's test runs. `implement` and `test` packets print `lint` for
  post-edit checks.

`off` stops linters, the gate and auto-fix only (the item base is still
recorded). Output lists each command's argv, cwd, exit code and output, applied
vs. NOT APPLIED hunks, new vs. base findings, and per-file coverage; steps still
run their own checks ([lint catalog](lint-catalog.md)). `--lint fix|report|off`
at `init` or `workspace start` sets it (`report` shows would-be fixes as
NOT APPLIED); saved runs without the key are refused (never migrated), and
`init`/`workspace start` retries cannot change it:

```sh
python3 "$CLI" lint-mode --run-dir "$RUN_DIR" --set report   # or fix, off
python3 "$CLI" lint --run-dir "$RUN_DIR" --action "$ACTION"   # report-only rerun
```

`lint-mode` refuses halted or done runs; switching to `fix` runs report-only
if no per-item base exists. `lint` exits 0 clean and covered, 1 when findings
or uncovered files remain, and 3 when unrun; ShipLoop never gates on its exit
code.

## Planning review option

`--planning-review stage|none` at `init` or `workspace start` records the run option
`planning_review` (default `stage`): which planning results start an Improve stage.
The option is the user's choice: pass `none` only when the user asks to run without planning reviews.
`stage` starts one after each of `spec`, `test-strategy`, `plan` and `step-plan`;
`step-plan` is reviewed only for the first work item and for an item that was sent
back, and later items follow the pattern that review set (rule `first-item`,
2026-10-19). `test-spec` is not reviewed in either mode (2026-10-26): the test
stage's own checks bind its cases. With `--planning-review none` no Improve stage starts after any of the four:
each result is accepted on ShipLoop's own checks at `complete` (cited files exist, the
plan's assumption list, the step plan's commands, criteria and paths, the knowledge
home's checks), the graph advances, and no Improve review covers it in this run. The
packets say so: the Improve line, the plan and step-plan duties and the shared handoff
sentence name only the stages that hand off. The Improve stages after each step's `document` stage,
`system-test-author`, `release-plan` and the last `reflect-and-revise` start in both modes; the
option does not cover the Backchain loop or the inner stages' Until Loops.

Besides the review, `none` removes what only the plan child hosts: its `improve-reconcile`
route and review-time `plan-time experiments` notebook (the packets do not print them). The `plan` producer's own Until Loop,
isolated `RUN/experiments/` sandbox, and `assumptions` / `intake` experiment-question gates still run in both modes. The spec and the test
strategy are committed to `docs/shiploop` when each is accepted, with no review after, so
later runs inherit them unreviewed. Under `stage` the `spec` child binds the selected Improve
card; a `none` run has no planning child to bind it, yet its first `implement` step starts an
Improve stage. So a `none` run names the card where it starts: `init` and `workspace start`
refuse `--planning-review none` without
`--improve-skill=<absolute selected Improve SKILL.md>`, and resolve the card there, so a missing
or unloadable card shows at the start and not in the first work item.
`--planning-review none` leaves no model-run second look at the plan graph at all; it is the highest-risk
combination, documented and not refused. SPEC S-10's second carve-out names what stands in for
the review (ShipLoop's gates) and what nothing replaces (whether the criteria and oracles are
complete).

Like `lint`, a saved run without the key is refused (start a fresh run),
never migrated, an `init` or `workspace start` retry cannot change it, and no verb
changes it mid-run: a fresh run is the route to another value.
