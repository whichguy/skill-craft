# Run options

Split from the ShipLoop skill card (`../SKILL.md`). Read before choosing `--delegation`, `--lint` or `--planning-review` at `workspace start` or `init`, and before `delegation --set` or `lint-mode --set`.

## Execution delegation

A new run from `workspace start` or `init` records `delegation:
inline`: this conversation is the only writer and executes every assignment,
including Improve and implementation steps, without Ask Agent or native workers.
Inline Improve checkpoints run the `improve` skill here, reviews and checks
included, and start no reviewer, test-runner or executor agent unless the user
asked for independent review. Pass `--delegation ask-agent` at `workspace start`
(or direct `init`) to opt in to the delegated route: each Improve checkpoint runs
the `improve-agent` skill, which starts one fresh native worker that runs
`/improve`, and implementation uses chains. Every run records the
setting; a saved run without it is refused with an error naming the missing
`delegation` key. An `init` or `workspace start` retry cannot change it. For an
existing run, use:

```sh
python3 "$CLI" delegation --run-dir "$RUN_DIR" --set inline   # or ask-agent
```

The setting applies from the next issued action: the action pending when you
switch, including its Improve checkpoint, keeps the route it was issued with
(the packet says so), so a worker, bound child or chain that may already own it
is never re-routed. It is refused on a halted or done run; setting the recorded
value is a no-op. `graph-dry-run --delegation
inline|ask-agent` previews either route (inline by default).

## Script-owned lint

A new run records `lint: fix`. ShipLoop then lints each work item itself. When
the item's inner loop starts it snapshots the item base. For every file the
item changed, it discovers the linters for that file type: built-in ruff and
shellcheck, the linters the repository configures (eslint, prettier, tsc, mypy,
black, markdownlint-cli2, yamllint, gofmt; actionlint whenever it is on PATH),
and `npm run lint` or `make lint` for a changed file no other linter covers.
Repository-configured linters run repository code; pre-commit is never run,
because it may download environments. Nothing is ever installed.

- **Lint gate.** The `complete` that submits `implement` (every step), `test` or
  `verify` as done (each of them edits code) lints
  every changed file and applies safe fixes on lines the item changed. It
  refuses that submission once after an auto-fix (rerun the step's checks, then
  submit again), and while a new finding on a line the item changed has no
  entry in the result's `lint_waivers` (`[{"id", "reason"}]`, using the IDs the
  refusal prints). Findings present at the base or elsewhere in a file, missing
  tools, tool errors, timeouts and a pass that cannot run never refuse. At
  `test` and `verify` the gate runs before ShipLoop's test runs, so the tests
  cover any auto-fix. The implement and test packets print the report-only
  `lint` command to run after each edit.
- **Advisory pass.** The `complete` that enters `verify` lints the item's
  changes again and, on the item's first entry only, applies safe fixes to later
  edits; a later entry reruns it report-only.

`off` stops the linters, the gate and auto-fix only; the item base and the
change inventory `verify` reads are still recorded. The block follows
the packet's callback. It lists every command's exact argv, cwd, exit code and
complete output, shows auto-fixes as an applied diff plus NOT APPLIED hunks,
separates new findings from debt already present at the item base, and states
per-file coverage. The step still selects and runs its own checks. Details and
safety pins: [lint catalog](lint-catalog.md).

`--lint fix|report|off` at `init` or `workspace start` selects the option; a
saved run without the key is refused (start a fresh run), never migrated. `report`
shows would-be fixes as NOT APPLIED. An `init` or `workspace start` retry cannot
change it. For an existing run:

```sh
python3 "$CLI" lint-mode --run-dir "$RUN_DIR" --set report   # or fix, off
python3 "$CLI" lint --run-dir "$RUN_DIR" --action "$ACTION"   # report-only rerun
```

`lint-mode` is refused on a halted or done run. A switch to `fix` applies fixes
only where a per-item base exists; otherwise the pass says its base fell back
and runs report-only. The `lint` rerun exits 0 when clean and fully covered, 1
when new findings remain or a file is uncovered, and 3 when the pass could not
run; ShipLoop never gates on that exit code (the implement gate runs its own
pass).

## Planning review option

`--planning-review stage|none` at `init` or `workspace start` records the run option
`planning_review` (default `stage`): which planning results start an Improve stage.
`stage` starts one after each of `spec`, `test-strategy`, `plan` and `step-plan`;
`step-plan` is reviewed only for the first work item and for an item that was sent
back, and later items follow the pattern that review set (rule `first-item`,
2026-10-19). `test-spec` is not reviewed in either mode (2026-10-26): the test
stage's own checks bind its cases. With `--planning-review none` no Improve stage starts after any of the four:
each result is accepted on ShipLoop's own checks at `complete` (cited files exist, the
plan's assumption list, the step plan's commands, criteria and paths, the knowledge
home's checks), the graph advances, and no Improve review covers it in this run. The
packets say so: the Improve line, the plan and step-plan duties and the shared handoff
sentence name only the stages that hand off. The Improve stages after each item's last `implement` step,
`system-test-author`, `release-plan` and the last `carry-forward` start in both modes; the
option does not cover the Backchain loop or the inner stages' Until Loops.

Besides the review, `none` removes what only the plan child hosts: its `improve-reconcile`
route and the plan-time experiments (the packets do not print them). The spec and the test
strategy are committed to `docs/shiploop` when each is accepted, with no review after, so
later runs inherit them unreviewed. Under `stage` the `spec` child binds the selected Improve
card; a `none` run has no planning child to bind it, yet its first `implement` step starts an
Improve stage. So a `none` run names the card where it starts: `init` and `workspace start`
refuse `--planning-review none` without
`--improve-skill=<absolute selected Improve SKILL.md>`, and resolve the card there, so a missing
or unloadable card shows at the start and not in the first work item.
`--planning-review none` with `--backchain-passes none`
leaves no model-run second look at the plan graph at all; it is the highest-risk
combination, documented and not refused. SPEC S-10's second carve-out names what stands in for
the review (ShipLoop's gates) and what nothing replaces (whether the criteria and oracles are
complete).

Like `backchain_passes`, a saved run without the key is refused (start a fresh run),
never migrated, an `init` or `workspace start` retry cannot change it, and no verb
changes it mid-run: a fresh run is the route to another value.
