# Blind vs with-build test-writing sessions: activity, adapters, own reports

Sources: RUNS = /Users/dadleet/e2e-runs/ratchet-parallel-20261121-6f54fb (blind a, b), OLD = /Users/dadleet/e2e-runs/ratchet-reworded-20261121-08805f (with-build a, b). Counts made by the helper scripts `analyze.py`, `flagged.py`, `show.py` in this folder, then checked by hand (see "How this was counted").

## Part 1: what each session ran

| session | seconds | shell cmds | acceptance-test runs | of those showing a failing test (literal `not ok` / `✖` / `# fail N`) | first acceptance run | product's own tests | distinct product source files read | `search_replace` edits | output tokens |
|---|---|---|---|---|---|---|---|---|---|
| blind a (due-times-a) | 956.4 | 26 | 3 | 1 literal (3 of 3 by hand, see below) | #18 of 26 | 1 | 12 | 13 | 44,295 |
| blind b (due-times-b) | 1180.4 | 35 | 8 | 3 literal (6 of 8 by hand, see below) | #17 of 35 | 4 | 16 | 0 (13 file-writing shell commands instead) | 51,912 |
| with-build a (p3R due-times-a) | 1004.4 | 36 | 15 | 7 | #14 of 36 | 3 | 3 | 10 | 43,678 |
| with-build b (p3R due-times-b) | 807.0 | 25 | 5 | 1 | #13 of 25 | 1 | 12 | 3 | 35,653 |

Token usage is in the stream: the final `end` event has `usage` (input_tokens, cache_read_input_tokens, output_tokens, reasoning_tokens). Output tokens as above; reasoning tokens (reported separately in the same event) are 16,832 (blind a), 20,505 (blind b), 16,532 (with-build a), 13,862 (with-build b). Input tokens: 2,232,088 / 2,788,066 / 3,066,947 / 1,953,207.

Notes on the "failing" column:
- Blind a: all 3 runs use a Node runner over `ratchet/acceptance.json` that prints one summary line per item. Only run #18 prints the literal `not ok` lines. Run #22 prints per-item exit status 1 plus the failure message ("Expected values to be strictly equal:"), and run #25 prints "42 commands, 55 named cases, 21 baseline passes, 21 baseline failures". By hand all 3 show failures on the starting product.
- Blind b: literal failures in #17, #20 (direct `node --test ... acceptance/run.cjs`), #30 (runner; its Python assertion crashed with a traceback that contained the test output). Runs #21, #25, #32 are runners that print one line per item with the exit code (20 or 21 lines of exit status 1), and no literal `not ok`; by hand that makes 6 of 8. Runs #23 and #29 are green selections (C-2, C-11, C-25, C-27 and C-2, C-25, C-33).
- With-build a: literal failures in #18, #22, #25, #27, #28, #33, #34. With-build b: literal failure in #13 only (C-33, C-34, U-7).

What the blind sessions ran their tests against (one line each):
- Blind a: the unmodified starting product in the work folder (adapter `ROOT = path.resolve(__dirname, '..')`, launched with `spawn('npm', ['start'], { cwd: ROOT })`). No command created or copied another product during the session; the adapter's rollback/baseline helper unpacks `git archive 72d9828...` (the local 1.4.0 base) into a temp dir because the plan's `ada051d...` object is missing (session command #7 `git cat-file -t ada051d...` exit 128), and `cleanCheckout()` copies ROOT without `.git` and `acceptance` into a temp dir for the `npm test` check. Final command #26 `git diff --exit-code -- src bin scripts test package.json ratchet/spec.md ratchet/plan.md` exit 0.
- Blind b: the unmodified starting product in the work folder (`root = path.join(__dirname, '..')`, `launch('npm', ['start'], { cwd })`). No command created or copied another product; the adapter's `legacy()` helper unpacks `git archive ada051d` if that commit exists, else `72d9828`, into a temp dir for rollback checks (`ada051d` is missing here, so it uses `72d9828`). Final command #24 `git diff --exit-code HEAD -- .` exit 0.

## Part 2: the adapter files

### Files and line counts

| folder | file | lines |
|---|---|---|
| blind a | adapter.cjs | 446 |
| blind a | child-controls.cjs | 116 |
| blind a | suite-reporter.cjs | 17 |
| blind a | suite.cjs | 1005 |
| blind a | total | 1584 |
| blind b | adapter.cjs | 465 |
| blind b | http.cjs | 353 |
| blind b | operators.cjs | 143 |
| blind b | persistence.cjs | 340 |
| blind b | reporter.mjs | 9 |
| blind b | run.cjs | 6 |
| blind b | scenarios.cjs | 147 |
| blind b | total | 1463 |
| with-build a | harness.cjs | 302 |
| with-build a | http.cjs | 369 |
| with-build a | npm-reporter.cjs | 14 |
| with-build a | operations.cjs | 309 |
| with-build a | rollout.cjs | 447 |
| with-build a | runtime.cjs | 117 |
| with-build a | total | 1558 |
| with-build b | deadlines.cjs | 191 |
| with-build b | listing.cjs | 184 |
| with-build b | operators.cjs | 267 |
| with-build b | production.cjs | 370 |
| with-build b | runtime.cjs | 35 |
| with-build b | support.cjs | 293 |
| with-build b | total | 1340 |

Adapter files: blind a `adapter.cjs` (446 of 1584 lines, 28.2%); blind b `adapter.cjs` (465 of 1463 lines, 31.8%). The with-build sessions have no file named adapter; the file that holds `spawn(` is `harness.cjs` (a, 19.4%) and `support.cjs` (b, 21.9%), used below only for comparison.

### (b) Names each blind adapter sets or reads to start or configure the product

"plan" = appears in `work/ratchet/plan.md` of that session; "spec" = in `ratchet/spec.md`. "docs" = in the starting project's README.md or docs/.

Blind a `adapter.cjs`:

| name | where in adapter | in plan.md | notes |
|---|---|---|---|
| PORT | env for `npm start` | yes | also in spec |
| DATA_FILE | env for `npm start` and the CLI (`viaEnv`) | yes | also in spec |
| DUE_TIMES | env for `npm start` (`flag`, `'on'` when `enabled`) | yes | also in spec |
| DUE_HOURS_URGENT / _HIGH / _NORMAL / _LOW | `HOUR_SETTINGS` map | yes | not in spec |
| WORKER_INTERVAL_MS | env for `npm start` | no | in spec (1) and docs (5) |
| NOTIFY_FILE | env for `npm start` | no | docs only (3); not in spec |
| TZ | env for `npm start` (default `UTC`) | no | in neither plan, spec nor docs; test-side |
| MAX_BODY_BYTES, LOG_REQUESTS | deleted from the child env only | no | docs |
| `--data`, `--json` | args to `bin/tickets.js` and `scripts/weekly-report.js` | yes (both) | |
| `npm start`, `npm test`, `bin/tickets.js`, `scripts/weekly-report.js` | commands | `npm start`, `npm test`, `bin/tickets`, "weekly" yes | |
| NODE_OPTIONS (`--require child-controls.cjs`, `--test-reporter`), RATCHET_CHILD_CONTROL, NODE_TEST_CONTEXT, npm_config_* | test machinery | no | only in adapter |

Blind b `adapter.cjs`:

| name | where in adapter | in plan.md | notes |
|---|---|---|---|
| PORT | env for `npm start` | yes | also in spec |
| DATA_FILE | env for `npm start` and the CLI | yes | also in spec |
| DUE_TIMES | env for `npm start` (`flag`) | yes | also in spec |
| DUE_HOURS_URGENT / _HIGH / _NORMAL / _LOW | `setting` map | yes | not in spec |
| WORKER_INTERVAL_MS | env for `npm start` | no | in spec (1) and docs (5) |
| NOTIFY_FILE | env for `npm start` | no | docs only (3) |
| TZ | env for `npm start` (default `UTC`) | no | in neither plan, spec nor docs; test-side |
| MAX_BODY_BYTES, LOG_REQUESTS | deleted from the child env only | no | docs |
| `--data` | arg to `bin/tickets.js` | yes | |
| `--raw`, `--json` (through `npm run report:weekly -- --json`) | args | no for both in plan; yes in spec; `report:weekly` is in plan | |
| `--status`, `--priority` | args to `bin/tickets.js` | no | docs only (1 each); not in spec |
| `npm start`, `npm test`, `bin/tickets.js`, `npm run report:weekly` | commands | all yes in plan | |
| ACCEPTANCE_BIND_FILE, ACCEPTANCE_CLOCK_FILE, ACCEPTANCE_CLOCK_STEP, ACCEPTANCE_PROCESS_FILE, ACCEPTANCE_REDIRECT_BIND, NODE_OPTIONS (`--require adapter.cjs`), NODE_V8_COVERAGE, NODE_TEST_CONTEXT, npm_config_* | test machinery | no | only in adapter (the adapter doubles as the preload module) |

So in both adapters, the product names the plan gives (PORT, DATA_FILE, DUE_TIMES, the four DUE_HOURS_* names, `--data`, and `npm start`) are in the plan; the other product-side names (WORKER_INTERVAL_MS, NOTIFY_FILE, `--status`, `--priority`, and in b `--raw` and `--json`) come from the starting project's docs or the spec, and TZ and the preload/control variables exist only in the adapter.

### (c) Does any other acceptance file start the product or name a product setting directly?

Counts of lines matching each pattern, adapter-like file vs all other files (the grep patterns: `spawn(`, `npm start`, `src/server`, `process.env.DUE`, `DUE_HOURS`, `DATA_FILE`, `DUE_TIMES`):

| folder | adapter-like file | pattern | in that file | in all other files |
|---|---|---|---|---|
| blind a | adapter.cjs | `spawn(` | 1 | 0 |
| blind a | | `npm start` | 3 | 1 (suite.cjs:79, only inside a test title: `'npm start serves health ...'`) |
| blind a | | `src/server` | 0 | 0 |
| blind a | | `process.env.DUE` | 0 | 0 |
| blind a | | `DUE_HOURS` | 4 | 0 |
| blind a | | `DATA_FILE` | 3 | 0 |
| blind a | | `DUE_TIMES` | 2 | 0 |
| blind b | adapter.cjs | `spawn(` | 1 | 0 |
| blind b | | `npm start` | 5 | 0 |
| blind b | | `src/server` | 0 | 0 |
| blind b | | `process.env.DUE` | 0 | 0 |
| blind b | | `DUE_HOURS` | 1 | 0 |
| blind b | | `DATA_FILE` | 2 | 0 |
| blind b | | `DUE_TIMES` | 2 | 1 (http.cjs:237, only inside a message string `responses for DUE_TIMES=...`; the value `on` is carried by `const on = 'on'` in http.cjs:9) |
| with-build a | harness.cjs | `spawn(` | 1 | 0 |
| with-build a | | `npm start` | 0 | 2 (operations.cjs) |
| with-build a | | `src/server` | 0 | 0 |
| with-build a | | `process.env.DUE` | 0 | 0 |
| with-build a | | `DUE_HOURS` | 1 | 12 (http.cjs 4, operations.cjs 2, rollout.cjs 6) |
| with-build a | | `DATA_FILE` | 1 | 5 |
| with-build a | | `DUE_TIMES` | 1 | 3 |
| with-build b | support.cjs | `spawn(` | 1 | 0 |
| with-build b | | `npm start` | 0 | 1 (operators.cjs) |
| with-build b | | `src/server` | 1 | 0 |
| with-build b | | `process.env.DUE` | 0 | 0 |
| with-build b | | `DUE_HOURS` | 1 | 11 (deadlines.cjs 7, production.cjs 4) |
| with-build b | | `DATA_FILE` | 2 | 2 |
| with-build b | | `DUE_TIMES` | 2 | 8 |

Blind a also has two other direct names outside the adapter, neither of which starts or configures the service: `suite.cjs:26` reads `process.env.RATCHET_ITEM` (the suite's own item selector) and `suite.cjs:744` passes `--raw` to the adapter's `cli()` helper. `child-controls.cjs` reads `RATCHET_CHILD_CONTROL` (the adapter's own preload). Blind b: `http.cjs:70-71` mentions `PORT=${port}` in assertion messages only. Neither blind session's non-adapter files start the product or set a product setting by name.

## Part 3: the two blind sessions' own "Assumed" sections (verbatim)

### blind a (`b1-due-times-a/work/ratchet/tests-1.md`)

```
## Assumed

- The plan's `ada051d8b4eca7b4b67a5b904f50fc7dd5612ff6` object is unavailable locally. The adapter can use `72d982867f943160fbde9456c9f523c5001dd7f3`, this checkout's unmodified 1.4.0 base, for rollback and baseline comparison.
- The literal 8080, 4180 and 65535 cases observe the requested bind port and substitute port zero at Node's bind boundary to keep the tests on free ports. A separate explicit-port test uses the real configured port.
- The clock and fault controls run through Node's standard APIs in the `npm start` child. The interruption control targets the active-file replacement boundary described in the plan.
```

### blind b (`b1-due-times-b/work/ratchet/tests-1.md`)

```
## Assumed

- `72d9828` is the local 1.4.0 reference when the plan's `ada051d` object is missing. The archive identifies itself as 1.4.0 and contains the pristine source and tests.
- A Node preload supplies deterministic wall time to `npm start` without importing the product's internal `manualClock`. For the default-port checks it records the requested port and lets the operating system bind port 0.
- The local POSIX runner honors directory and file permissions and a child-process file-size limit. These faults simulate a blocked save and an interrupted write without depending on a temporary file name.
- C-34 observes individual `node:test` cases from `npm test` and looks for evidence of due-time coverage in the added suite. The coverage evidence is a proxy for the substance of the added assertions.
```

## How this was counted

- Events: `events.jsonl` in each session folder. A shell command = event `type == "tool_call"` with `toolName == "run_terminal_command"`, text `rawInput.command`, result from the later `tool_call_update` with the same `toolCallId` (`rawOutput.exit_code`, `rawOutput.output_for_prompt`). The 4 sessions have 26, 35, 36 and 25 such commands. `search_replace` events counted separately. Output tokens from the last `end` event's `usage.output_tokens`.
- Seconds: `run.json` `sessions[]` entry whose label is `tests-1-1`, field `seconds`.
- Acceptance-test run (classified by script, then reviewed by hand per command): a command that executes `node ... acceptance/...` or a runner (Node `spawn` / Python `subprocess.run`) over the commands in `ratchet/acceptance.json`. File-writing parts of a command (`cat > acceptance/x <<EOF`, Python `write_text` edits) were stripped before matching, but a command that writes a file and then runs tests counts as one run (this applies to many of the first runs). Not counted by hand: `node --check` / syntax-only commands (blind a #24, blind b #24, with-build a #13), commands that only write `ratchet/acceptance.json` (blind a #17, with-build b #12), and ad-hoc probe scripts that load the adapter or harness but are not the tests (blind a #21 interruption/IO probe, with-build a #23, with-build b #21).
- Failing-test column: literal match of `not ok`, `✖` or `# fail [1-9]` in `output_for_prompt`, as asked. The blind sessions' runners (blind a #22 and #25, blind b #21, #25, #32) print per-item exit statuses instead of TAP, so I also report a by-hand count that includes runs whose lines show an exit status of 1 for items.
- Product's own tests: commands running `npm test` or `node --test` on `test/` (not under `acceptance/`). Blind a: `npm test -- --test-reporter=tap`. Blind b: `npm test | tail -24`, `node --test test/ids.test.js` with the tap reporter, the same file with the adapter's reporter, and `npm test` with the adapter's reporter. With-build a: `npm test | tail -62` (plus a name-pattern run), `npm test` with the adapter reporter, final `npm test`. With-build b: one `npm test` with a V8-coverage check. Runs of `npm test` inside an acceptance test were not counted.
- Product source files read: distinct paths under `src/`, `bin/`, `scripts/` named in a command containing cat, sed -n, rg, grep, nl, head, tail or `git show` (including `git show ada051d:src/...`), after stripping file-writing heredocs; I checked the resulting lists against the commands by hand. `rg --files` listings and directory-wide searches name no files and are not counted. Blind a (12): bin/tickets.js, scripts/weekly-report.js, src/app.js, clock.js, config.js, format.js, log.js, persistence.js, server.js, store.js, tickets/query.js, worker.js. Blind b (16): bin/tickets.js, scripts/weekly-report.js, src/app.js, clock.js, config.js, format.js, http.js, log.js, notifier.js, pagination.js, persistence.js, server.js, store.js, tickets/query.js, tickets/states.js, worker.js. With-build a (3): bin/tickets.js, scripts/weekly-report.js, src/format.js (read from git `ada051d`, i.e. the pre-change tree; it did not read the built source). With-build b (12): bin/tickets.js, scripts/weekly-report.js, src/clock.js, config.js, format.js, notifier.js, pagination.js, persistence.js, server.js, tickets/query.js, tickets/validate.js, worker.js. In the with-build sessions the work folder held the build, so reads of `src/` there are of the built product.
- Blind b made 0 `search_replace` events; it edited files through 13 shell commands (`cat > file` and Python `write_text`). Blind a made 13 `search_replace` events and 6 file-writing shell commands.
- Ambiguities: (1) "a command that ran acceptance tests" includes mixed commands that write and then run; (2) blind b #30 is counted as a run although its Python assertion crashed after the commands ran; (3) the failing-test column has the literal and by-hand variants described above; (4) the "adapter-like" file for the with-build sessions was chosen by me (the file containing `spawn(`), because those sessions were not asked for an adapter.
