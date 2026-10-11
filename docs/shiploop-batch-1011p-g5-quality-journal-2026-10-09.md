# Batch 1011, group G5: the delivered product's quality as a record, not a verdict — journal, 2026-10-09 (first round and fix round)

Worktree `.claude/worktrees/b1011p-aaa47e`, branch `batch1011p-aaa47e`, base `30a3b40a`. Harness-only: no skill, no release.
Basis: `docs/shiploop-e2e-harness-batch-1011-plan-2026-10-09.md` (row G5), the design and its audit
`docs/experiments/batch-1011-harness-design-audit-20261009/design-audit.json` (key `F5-delivered-quality`; the audit's
`safer_alternative` is the scope), SPEC `test/shiploop_e2e/SPEC.md` (the amendment of this group: the table row `quality` and the bullets
"A planning_review mode is an option of a named case" and "Delivered quality is recorded, never judged").
Evidence: `docs/experiments/batch-1011p-g5-quality-20261009/` (`evidence.json`, `mutants.py` with `mutants-result.json`, `heldout_probe.py`).

This journal was written after the first round (head `5e82846d`) and rewritten after two adversarial reviews of that head (lens A:
correctness, process safety, test validity; lens B: conformance, scope, honesty). Claims of the first version that the reviews or
the rerun showed false are listed next, marked **superseded**; they are not silently removed.

## Corrections to the first version of this journal, the commit messages and the README (status: superseded)

| First-round claim | What is true | Found by |
|---|---|---|
| "this evidence run starts no server on a fixed port" (evidence.json `how`, Part 3, the commit text) | The mutation phase itself listened on :3000 whenever a mutant of `if (require.main === module)` or of `Number(process.env.PORT) \|\| 3000` made a test's `require('../server')` or a spawned server bind it; five of the eight deliveries have such a line. The first sweeps therefore did bind :3000, in this evidence run and in the design's prototype. The phase now runs every child under a preload that refuses the declared ports (see Part 2); the rerun below saw no listener on :3000. | reviewer A (A1) |
| "a kill in the phase loses nothing that exists today" | The export and the baseline row had been moved after the phase; a SIGKILL during it lost both (repro: result.json present, no quality, no baseline file, no review-export). They are written before the phase again. | A3, B1 |
| "never `killpg` after a clean reap" kept test-run helpers safe | It left every helper a test run started in its group orphaned after a normal exit (13 test runs, 13 children alive), out of reach of SIGTERM. The group is now ended when the leader exits, before it is reaped. | A2 |
| "load stretches seconds, not counts" | Five sweeps of r3-checkers on one copy of the reviewer's machine gave 78/86 four times and 80/86 once. A failing run is now confirmed by a second run. (The five sweeps below, on an idle machine, were identical: the instability was not reproduced here.) | A4 |
| "the ratio is an upper bound: equivalent mutants survive", "so it never reaches 1" | Neither is a bound: surviving equivalent mutants lower it; hangs, load-induced failures and port collisions counted as caught raise it; a delivery whose sites are all killable reaches 1. | A8, B6 |
| "a caught mutant proves the file ran" | A sign, not a proof; only a confirmed, non-timeout kill counts as one. | B11 |
| "the regraded r2-battleship-grok-none is measured and its hosts come from its launch records" (F6, LEARNINGS, the commit) | It passes the gate, but its `invocation.json` says case `custom`, so it is given no declaration: read-only, `quality.measure` gives it `observed: false, "the case declares no quality measures"`, `hosts_used [grok, claude]`. The saved `none` runs (all case `custom`) can never get a mutation or acceptance block by regrade. The gate fixture has no launch records and its test only calls `quality_gate`. | A6, B2 |
| the printed "never loaded by the tests" | The SPEC says "no sign of a load"; the line now says that. | A7, B5 |
| "lowest of four Battleship deliveries" beside a table of five; prototype ratios "by other operators" | The comparison is r1, r2, r3 recomputed and v1230 (prototype, not recomputed): r2-battleship-grok-none (0.81, prototype, none mode, mixed host) is left out because it is a mixed-host run of the other mode. The prototype's operators ARE `js-1` (`mutate2.py` OPS equal `JS_OPERATORS`; its off-by-one is `bound-literal`): "other code, same operators". "Not separable at n of 4" brought back the design's invented rule of thumb; it now says "not separable from run-to-run spread" with no n. | B9 |
| "all eight saved deliveries inline the page JavaScript in HTML" | Seven do; r2-battleship-grok-none builds its page in `server.js` strings. | audit, first round |

The SPEC refinement `18bd076e` (loaded_by_tests) was committed nine seconds after the code it describes (`2b432fc5`): an inversion of the rule
that the SPEC changes first. The fix round put its document changes (`55b6eb35`) before the code that depends on them.

## What was asked and what was built

| Step | Commit | What |
|---|---|---|
| 1 | `8b98ccf7` | SPEC amendment, dated 2026-10-09: the `quality` row; the planning_review option; "Delivered quality is recorded, never judged". |
| 2 | `bf085ec9` | `--planning-review stage\|none` as an option of a named case. The prerequisite: the Grok `none` runs (r2, r3 of 2026-10-08; baseline rows 2026-10-06T18:17 and 2026-10-07T10:17) are case `custom`, style null, because the mode rode in `--prompt`/`--check`. |
| 3 | `2b432fc5` | `test/shiploop_e2e/quality.py` (JS mutation, Checkers held-out acceptance, the Claude memory-write reader), `checks/checkers_accept.py`, `test/fixtures/quality/`. |
| 3b | `18bd076e` | SPEC refinement: `loaded_by_tests` is "no sign of a load" (late: see above). |
| 4 | `b33bb47c` | `run.py` wiring, `cases.json` declarations, README. |
| 5 | `5e82846d` | first-round journal, evidence, gate replay, LEARNINGS. |
| fix 0 | `55b6eb35` | SPEC and README corrections the fix round's code depends on (committed first). |
| fix 1 | `1de9e7bf` | a test run's whole group is ended when its leader exits, before the reap; one narrow `end_group`; honest ceiling labels. |
| fix 2 | `1e13016d` | the port-refusing preload and `quality.refuse_ports`. |
| fix 3 | `aab161db` | confirmation of kills, evidence lines, signs of a load, page script no operator reaches, syntax-check timeouts. |
| fix 4 | `6333c137` | the phase last (export and row first), no `quality` in the row, `hosts_used` from runrecord, regrade keeps an observed block, `stage` appends nothing, the card is looked for before any host CLI, one acceptance block. |
| fix 5 | this commit and the next | this journal, the rerun evidence, the mutant list and its result, the probe. |

Not built, by the brief and the audit: the UI/browser observation (until it can click through CDP; no `find_browser`), the Battleship acceptance
set, the port lease and serialisation and the record of busy declared ports (G4's environment record and an owner decision),
`CLAUDE_CODE_DISABLE_AUTO_MEMORY`, the argv exec scrub, the overlap record (G4), the name-pattern kill count (G1). Sizing: the design said
`m`; the audit's `l` was right.

## Part 1. `--planning-review` on a named case

`python3 test/shiploop_e2e/run.py --case battleship --planning-review none`: for `none` the harness appends the engine's own wording to the
case prompt, `Start ShipLoop with the run option --planning-review none and --improve-skill <plugin_dir>/skills/improve/SKILL.md.`;
**`stage` is the engine's default and appends nothing**, so a stage run has the prompt (and any hash of it) of a run without the option
(fix round, A12). The card is looked for as soon as the plugin directory is known, before the host CLI installs the plugin (A11; Grok's
`plugin install` used to run first); refused with `--seed-at`; a resume must name the run's own value or none. `invocation.json` gains
`planning_review` and `improve_skill` (null when not given). The choices are the engine's `PLANNING_REVIEW_MODES`. `load_case` is untouched.

Argparse prefix abbreviations (`--pro`, `--chec`) are accepted by `run.py` as by any argparse program, so the exec-based `scrub_argv` the
design proposed would have been bypassed. It is not built. A named case carries no check text in the harness argv; a custom `--prompt` /
`--check` run still does (the r3 Checkers model printed it with `pgrep`, events 550 and 570), and Claude's `-p <prompt>` and Codex's last
argument carry the case prompt in the host's argv (standard input stays closed, S-14). Documented in the SPEC and the README.

## Part 2. Mutation of the delivered tests

`quality.mutation(copy, spec, ...)` on a copy under `<output>/quality/copy` (`export_delivery`: `git ls-files --cached --others
--exclude-standard`, no `.git`; `work/` is only read, hash- and `git status`-checked by a test).

* **Operators** (catalog `js-1`, `quality.JS_OPERATORS`, the prototype's set): `===`/`!==`, `<`/`<=`/`>`/`>=`, `&&`/`||`, `true`/`false`, spaced
  `+`/`-`, the literal after a comparison stepped by one; in code only (comments, strings and template bodies are masked; a regular
  expression literal is not recognised). Any change to the operators or the mask is a new id.
* **Targets**: `.js .mjs .cjs` outside `test`, `tests`, `__tests__`, `node_modules`, `docs`, files that look like node's own test patterns and
  the case's `exclude` (`system` for Battleship and Checkers). Nothing else has a catalog: a Python delivery is `observed: false`.
* **Fixed ports** (fix 2). `test/shiploop_e2e/refuse_ports.cjs`, named in the JS catalog, is added to `NODE_OPTIONS` for the baseline, every
  mutant run and the acceptance server. It makes `listen` fail as an address in use and `connect` fail as a refused connection on the ports
  in `quality.refuse_ports` (3000 for battleship and checkers), writes one line per refusal to a log of that run's own, and is inherited by a
  test's children. A delivery whose own unmutated tests touch a declared port is `observed: false`, "its tests bind a fixed port; not run",
  before any mutant runs. A caught mutant whose run had a refusal keeps the marker (`port_refused`, per-kill `port_refusals`).
* **Baseline gate**: the unmutated copy's test run must touch no declared port, finish within the ceiling, exit 0 and count at least one test
  (the engine's `shiploop_test_counts`, through the JS catalog: no `pass N` regex in generic code, a departure from the audit's wording that
  keeps S-12).
* **Confirmation** (fix 3). A failing run is run once more (after asking the stop). Failing twice: `killed`, with the first failing line as
  `evidence`. Failing then passing: `unconfirmed`, out of the ratio, both outcomes recorded. A hang (`timeout`) is not repeated.
  `killed + survived + invalid + unconfirmed + not_run = sites`; `ratio = killed / (killed + survived)`. A syntax check that does not finish or
  cannot start makes the mutant `not_run` with its reason, not `invalid`.
* **Order and ceilings**: round-robin across files so a ceiling hit leaves a sample of every file. `RUN_CEILING_SECONDS = 10` *defines* a hang
  (reaching it is a caught mutant and a `timeout`, so changing it changes results; basis: the limit the prototype sweeps ran with, beside
  suites of 0.23 to 1.27 s) and `PHASE_CEILING_SECONDS = 600` (about five times the longest sweep measured, 113 s, under the launcher's ~30
  min) is where the phase gives up. The audit asked for one ceiling; a hung mutant would otherwise spend the whole phase. The other constants
  (listen wait, read-back size, display cuts, the held-out HTTP call) are labelled in the code.
* **`loaded_by_tests`**: true when the baseline's V8 coverage lists the file or a *confirmed, non-timeout* kill of it exists (a sign, not a
  proof); false = no sign (a lower bound: a server the tests stop with a signal writes no coverage, the saved r1 Checkers `server.js`); null =
  no coverage and no kill.
* **`uncovered`** (A10): the HTML files with inline `<script>` and their script line counts, beside each file's `lines`. 22 to 29 percent of
  the delivered JavaScript of r1-bs, r3-bs, r1-ck and r3-ck lives there, which no operator reaches.
* **Processes** (fix 1): every child starts in its own session, is registered in the caller's `groups` (the harness passes
  `run.LIVE_HOST_GROUPS`) the moment it starts and forgotten after it is reaped. The leader is waited for with `waitid(..., WNOWAIT)`, which does
  not reap; when it exits (or hangs past the ceiling) `end_group` kills the whole group while the leader still pins its pid (on macOS `getpgid`
  raises for an exited, unreaped process while `killpg` works), then reaps. A reaped leader is never signalled; a running one is signalled only
  if `getpgid(pid) == pid`, which `start()` also checks at registration. `end_group` is the one function the phase signals through; the
  harness's other group kills (`run.kill_group`, `hosts.run_process`) are unguarded and only the test helper `kill_hosts` uses the guard (the
  first-round docstring said otherwise). **Superseded 2026-10-09 by the integration branch:** every group kill of the harness, this one included, is now
  `listeners.end_group` (the same rule), and `quality.end_group` keeps its contract and reaps after it; see
  `docs/shiploop-batch-1011-integration-journal-2026-10-09.md`. The stop is asked before every run and once after the last.

## Part 3. Held-out acceptance, Checkers only

`checks/checkers_accept.py` holds six checks: `red-moves-first`, `illegal-keeps-turn`, `off-board-keeps-turn` (the bundled item split),
`legal-moves-alternate`, `red-jump-mandatory`, `black-jump-mandatory-and-removal`. `cases.json` quotes the prompt sentence each reads.
`quality.acceptance` starts the case's `start` command in the copy with `PORT` set to a free port (under the same port guard), imports the
module inside the harness process and calls each check, so no check text or id is on any argv (a test spies on every `Popen`). One block per
case: the multi-block merge served no case and was removed. The script is readable at a path the harness prints in its own command line and
resume prompt, so `held_out_seen: 0` is not proof the model never read it.

Calibration: `test/fixtures/quality/reference_checkers.py` is a hermetic service with one defect switch per rule; the exact failing set of
each of the eight variants is pinned. Battleship: the design's probe (`heldout_probe.py` in the evidence folder, unchanged) passes 8 of 8
runnable items on all five saved Battleship deliveries, r3 included: it separates nothing and is not built.

## Part 4. The Claude memory-write reader

`quality.memory_writes(events.jsonl)`: Claude `Write`/`Edit`/`MultiEdit` calls whose `file_path` is under `.../.claude/projects/<slug>/memory/`,
`{path, tool, line}` (1-based). Over the 25 saved event files it finds exactly two, in `20261008/r3-checkers-sonnet` at lines 599 and 605. It
reads no directory, touches nothing under `~/.claude` and sets no environment variable. A write by a shell command is not seen. For a mixed-host
run a note says the list covers Claude's calls only; for a run with no Claude session, or no launch record, it is null with the reason.

## Part 5. Wiring and order

`_main` writes result.json and metrics.json, the Run Review export and the baseline row as before, prints its report, and only then runs the
phase: `quality_gate` (stop, engine active, `shiploop`, `committed`, the case lock) decides whether the delivery is measured, `quality_record`
calls `quality.measure`, and result.json is written again with `quality`. The baseline row carries no `quality`. Any exception in the phase is
`quality.failed_block` (the declared keys, `hosts_used`, the events as null with a reason): no verdict, exit code or baseline decision changes. A
regrade measures too, unless another harness holds the case; one that cannot measure keeps the earlier observed block and records why in
`quality_regrade_skipped`. `hosts_used` and `mixed_host` are `runrecord`'s, null with a reason when no launch record exists.

## Evidence (fix round rerun: the fixed code, under the port guard)

`evidence.json` has per-file counts, every kill with its first failing line, every timeout, every port refusal, every survivor, the acceptance
results, five sweeps of r3-checkers and one whole example block. Other batch agents were also testing on the machine (the load average at the end of the sweeps is in the commit message); seconds are not comparable, counts are. A watcher polled
`lsof` for a listener on :3000 every 0.3 s during every run and saw none.

| Delivery | Sites (lines mutated) | Caught | of which timeout / port-refused | Unconfirmed | Ratio | Prototype | First round (unguarded) | Held-out |
|---|---|---|---|---|---|---|---|---|
| r1-battleship-sonnet | 33 (game 70, server 97 lines) | 27 | 3 / 2 | 0 | 0.8182 | 27/33 | 27, 3 timeouts | |
| r2-battleship-sonnet | 42 | 33 | 1 / 2 | 0 | 0.7857 | 33/42 | 33, 3 timeouts | |
| r3-battleship-sonnet | 36 (lib/game 74, server 148) | 20 | 0 / 1 | 0 | 0.5556 | 20/36 | 20, 1 timeout | |
| v1230-battleship-sonnet | 58 (sites only) | not run: its tests touch :3000 (1 refusal) | | | | 43/58 | not swept | |
| r2-battleship-grok-none (mixed host) | 105 (sites only) | not run: its tests touch :3000 (97 refusals) | | | | 85/105 | not swept | |
| r1-checkers-sonnet | 108 | 88 | 0 / 1 | 0 | 0.8148 | 88/108 | 88, 0 | 6 of 6 |
| r2-checkers-sonnet | 72 (sites only) | not run: its tests touch :3000 (1 refusal) | | | | 61/72 | not swept | 6 of 6 |
| r3-checkers-sonnet | 86 (rules 109, server 100) | 78 | 1 / 2 | 0 (five sweeps) | 0.907 | 78/86 | 78, 2 timeouts | 5 of 6 |

* **The guard changed what the counts mean, not the counts.** The same mutants are caught as before: 27, 33, 20, 88, 78 caught of 33, 42, 36, 108,
  86. What changed is which mutants were doing it: the `===`/`!==` flip of `require.main === module` (server.js 92, 124, 143, 95, and 93/125/96/87
  for the `|| 3000` logic-flip) were the mutants that bound :3000, and are now counted as `port_refused` with the refusal count. In the first
  round some of them timed out (a server answering on :3000 and nothing exiting): 3/3/1/0/2 timeouts then, 3/1/0/0/1 now.
* **r3-checkers five sweeps:** 78/86 each time, identical kills and survivors, `unconfirmed` 0 in all five (72 s each). The reviewer's 80/86
  sweep on a busy machine was not reproduced, so the confirmation is tested by a stand-in flake but not by a live one.
* **r3 Battleship** is the lowest of the Battleship deliveries compared (r1 0.82, r2 0.79 recomputed; v1230 0.74 prototype, not recomputed),
  consistent with the hand finding (8 of 17 hand-made mutants survived on r3, three of them page mutants outside this catalog), not separable from
  run-to-run spread. It does not single r3 out.
* **Page script no operator reaches** (`uncovered`): r1-bs 68 lines, r2-bs 76, r3-bs 80, r1-ck 57, r3-ck 80 inline-script lines, against the
  mutated JavaScript of the table.
* **Checkers held-out:** r1 6/6, r2 6/6, r3 5/6, failing `off-board-keeps-turn` only (HTTP 400 `{ok:false, error}`, no turn or winner).
* **Fixed-port deliveries run only to their baseline** (the guard refused the bind and the connect; nothing reached :3000).
* Memory writes: 2 in 25 saved event files, both r3-checkers-sonnet (lines 599, 605).

## Findings

| # | Finding | Status | Evidence |
|---|---|---|---|
| F1 | `js-1` reproduces the prototype's site counts for all eight deliveries and its caught counts for the five re-run; the prototype's operators are the same set. | firm | table; `evidence.json` |
| F2 | The coverage record alone calls the saved r1 Checkers `server.js` never loaded although 23 of its 32 mutants were caught (the tests stop the child with a signal, so it writes no coverage). A confirmed non-timeout kill is therefore a sign of a load; false means no sign. | firm | first-round `evidence.json`, `loaded_by_tests` tests |
| F3 | Checkers held-out: r1 and r2 pass 6/6, r3 fails `off-board-keeps-turn` only. One reading of two prompt sentences; its own id and its source quoted. | firm for the result; interim for what it means | `evidence.json` |
| F4 | Battleship held-out passes 5 of 5 (8 of 8 runnable items): no information, not built. | firm | `heldout_probe.py` rerun |
| F5 | r3 Battleship has the lowest ratio of the compared Battleship deliveries; not separable from run-to-run spread. | interim | table |
| F6 | The saved gate records behave as the audit read them: r3-battleship-grok-none (stopped, engine active, no tracked file) is not measured; r3-checkers is; the regraded r2-battleship-grok-none passes the gate but as case `custom` records only hosts and memory writes. | firm (gate), **corrected** (the first version claimed it was measured) | `gate-records.json`, `QualityGateTest` |
| F7 | A second non-blocking flock on a case lock in the same process fails, so the phase reuses the lock `main` holds. | firm | test |
| F8 | The mutation phase bound :3000 whenever a mutant made the product listen on its default: eq-flip of `require.main === module` and logic-flip of `Number(process.env.PORT) \|\| 3000` in five deliveries, `env.PORT === undefined` in v1230. | firm (reviewer A, then the guard's refusal counts: 1, 2, 2, 4, 4 refusals in 5 deliveries) | `evidence.json` `kills_with_a_port_refusal` |
| F9 | Three saved deliveries' own tests touch :3000 (v1230 ST-3, r2-checkers TC-1 (c), r2-grok TC-port); the guard turns that into `observed: false`. | firm | `evidence.json` |
| F10 | A normal exit leaves a test run's helpers in its group; they were orphaned until the group was ended before the reap. | firm | `ProcessSafetyTest` |

## Deviations from the design and the audit, with the reason

1. **Two ceilings, not one** (above). 2. **The engine's test counter**, not a regex in the catalog (S-12). 3. **Acceptance in-process**, not
`python3 script <id>` (ids on a command line are visible to any model on the machine). 4. **Six named check ids**, no robustness kind. 5.
**`killed` includes `timeout`** (a subset) and `port_refused` (a subset). 6. **`quality` is always present** for a run that reached the phase, with
`declared`; absent key means the run predates the phase. 7. **Regrade measures**, and keeps an earlier observed block when it cannot. 8. **The stop
file is not consumed by the phase.** 9. **All survivors and all kills are listed**, not capped. 10. **No `host_profile`/`host_isolation`.** 11.
**The baseline row carries no `quality`** (the first round added a summary; the reviews showed it forced the wait, duplicated G4's hosts record and
edited G3's line). 12. **Fixed ports are refused, not recorded-and-refused-at-launch**: the audit's "record busy declared ports and refuse only
when `observe()` shows a declared port bound" is given to G4's environment record and an owner decision (SPEC).

Disagreements with the audit: none that changed behaviour. The audit's "all 8 inline" was one off (above).

## Data shapes for the Run Review session

`result.json["quality"]` (optional: absent on runs from before this change; a run that reached the phase always has it; a regrade that cannot
measure keeps the earlier observed block and adds `quality_regrade_skipped: {reason}` at the top of result.json). The example is the real
`20261008/r3-checkers-sonnet` (its events and work folder); the whole block is in `evidence.json` `example_block`:

```
observed: true                      # false + reason when no delivered-product measure was taken
declared: ["mutation", "acceptance"]
hosts_used: ["claude"], mixed_host: false      # runrecord.hosts_used / mixed_host of the launch records; null + unmeasured.hosts_used when none
delivered_files: 18, seconds: 72
mutation: {observed: true, operator_id: "js-1", command: "node --test", source, baseline: {returncode, seconds, tests, port_refusals},
           refuse_ports: [3000], sites: 86, killed: 78, timeout: 1, port_refused: 2, port_refusals: 2, survived: 8, invalid: 0, unconfirmed: 0,
           not_run: 0, not_run_reasons: {}, ratio: 0.907, ceiling_hit: false, ceilings: {run_seconds: 10, phase_seconds: 600},
           per_file: {"rules.js": {sites, lines, loaded_by_tests, killed, timeout, port_refusals, survived, invalid, unconfirmed, not_run}, ...},
           uncovered: [{file: "index.html", inline_script_lines: 80}],
           kills: [{file, line, op, from, to, timeout, port_refusals, evidence: "<first failing line>"}],
           survivors: [{file, line, op, from, to, port_refusals?}],
           unconfirmed_mutants: [{file, line, op, from, to, first: {returncode, evidence}, second: {returncode}}], seconds}
           # or {observed: false, reason}, with baseline when it ran; "its tests bind a fixed port; not run" for a delivery that touches a declared port
acceptance: {observed: true, source, ids: [6], passed: [5], checks: [{id, source, pass, note}]}      # or {observed: false, reason}
held_out_seen: 0                    # null (+ unmeasured.held_out_seen) when events.jsonl is unreadable or the case holds nothing out
memory_writes: [{path, tool: "Write", line: 599}, ...]       # null + unmeasured when no Claude session or no launch record
notes: ["held_out_seen counts ... 0 is not proof ...", "memory_writes covers Claude's ... only; ..."]   # run-dependent caveats
unmeasured: {<key>: <reason>}
left_behind: {observed, reaped, survived}
```

Unobserved forms: `{observed: false, declared, hosts_used, mixed_host, reason, memory_writes, held_out_seen, notes?, unmeasured?, seconds}`; a phase that
raised: the same keys with `reason: "the quality phase failed: ..."`, the events null with a reason and `seconds 0.0`. `invocation.json`
gains `planning_review` and `improve_skill`. **The baseline row has no `quality`**: the page reads result.json. Rendering rules: every
figure is "record only"; show `observed:false` as "not observed: <reason>"; print `operator_id` beside the ratio and never compare two ids; show
`loaded_by_tests: false` as "no sign of a load"; show `timeout`, `port_refused` and `unconfirmed` beside the ratio; name `uncovered` page script;
mark `mixed_host`.

## Open risks, unknowns and what could not be verified

* **A live run was not made** (rule: no live E2E run, host, model, browser or fixed-port server). The phase is exercised through `run.main` with
  the fake hosts and a stand-in for `node --test`, and by hand over the saved deliveries.
* **A SIGKILL of the harness during the phase** is not covered by the `atexit`/signal path: the in-flight test run, if hung, is orphaned (bounded
  by one run; not mitigated). The result, the export and the row are on disk by then.
* **The guard is a Node preload.** It covers Node products; a non-Node delivery's ports are not guarded (no such catalog yet). It refuses
  through `net`; a product that opens sockets some other way (a native addon) is not covered. A product that reaches its default port with
  `NODE_OPTIONS` cleared in a spawned child would not carry the guard (the three saved ones inherit the environment).
* **Suite concurrency**: with `--max-parallel 3` a finished chain runs its CPU-heavy phase beside sibling chains' hosts; load can turn a slow
  mutant into a timeout or a one-off failure (now confirmed by a second run). Recorded, not serialised.
* **The confirmation is untested against a live flake**: the five idle-machine sweeps had `unconfirmed 0`. It is proven by a stand-in that fails
  once.
* **`held_out_seen`** counts lines naming the module, the checks folder, `E2E_CHECKS` or `cases.json`; the checks folder's path is printed in
  the harness's own command line and resume prompt.
* **Other runners and languages**: only `node --test` was exercised against real output; every other language is "no operator catalog".
* **Python 3.14 / macOS only** (`waitid` with `WNOWAIT`, the `getpgid` behaviour on a zombie) were exercised.
* The Run Review exporter was not read or changed; it copies result.json and picks named keys.

## Tests and verification (real results, 2026-10-09, fix round; GIT_CONFIG_* not exported)

`test/shiploop-e2e-quality.test.py`, 125 tests (registered in `suite_catalog.SHIPLOOP_SUITES` at 43 s; `test-groups.test.py` pins 71 ShipLoop
suites and 112 in all). By class: `PlanningReviewOptionTest` 9, `MutationOperatorTest` 7, `MutationRunTest` 27, `MutationNodeTest` 3 (real
`node --test`), `PortGuardTest` 7, `PortGuardNodeTest` 3 (real node, a declared port that is a free one the test picked), `PrintedLineTest` 2,
`ProcessSafetyTest` 9, `AcceptanceCalibrationTest` 5, `AcceptanceRunTest` 8, `EventFactsTest` 10, `MeasureBlockTest` 12, `QualityReapTest` 1 (real
lsof and signals, scoped to the test's folder), `QualityThroughMainTest` 14, `QualityGateTest` 6, `CaseQualityTest` 2. No test binds or connects to
a fixed port, reads the machine's process table (every class patches `listeners.observe` except `QualityReapTest`, which scopes it) or depends
on `/Users/dadleet/e2e-runs`; every process a test starts expires by itself (60 s, 120 s or 30 s at most).

| Command | Result |
|---|---|
| `python3 test/shiploop-e2e-quality.test.py` | 125 tests OK in 44 s |
| the same with node off `PATH` | 125 OK, 6 skipped (`MutationNodeTest`, `PortGuardNodeTest`; reason: "this class runs the real `node --test` and needs node on PATH") |
| `python3 test/shiploop-e2e.test.py` | 404 tests OK in 112 s (no test of that file was edited) |
| `python3 test/shiploop-e2e-runrecord.test.py` | 6 tests OK |
| `python3 test/test-groups.test.py` | 21 tests OK |
| `bash test/run-all.sh --group quick --changed-from 30a3b40a` | PASS, 21 suites OK, among them `shiploop-e2e` and `shiploop-e2e-quality` |

**Mutants.** `docs/experiments/batch-1011p-g5-quality-20261009/mutants.py` lists 104 mutants of `quality.py`, `run.py`, `checkers_accept.py` and
`refuse_ports.cjs`, and `mutants-result.json` the test that went red for each. All 104 are caught (none equivalent). They include the 48 of
review lens A under their ids (`A:M01` to `A:R17`, ported to the code as it now is; `A:R10` and `A:R13` break the successors of the code the
reviewer broke: the stage sentence no longer exists, the acceptance lists no longer concatenate). The reviewer's `M14` made an invalid regular
expression and was caught only by a crash; the ported `A:M14` is a valid one and is caught by an assertion. Reviewer A's survivors of the first
round, now red: `M01` (the reaped-pid guard; the test mocks `getpgid` to return the pid after the reap and asserts `killpg` is not called),
`M18` (the harness's PORT not stripped), `M24` (the coverage prefix; a sibling folder named like the copy), `R06` (TERMINATION with no stop file)
and `R11` (a custom run measured by a catalog that has battleship). Two first-round tests were vacuous in the way the reviewers said (the
`end_group` reaped-pid test and the hung-mutant test, which passed with the group kill removed because the child expired on its own after
60 s); both are repaired. The first fix commits' tests were written with their code (a departure from tests-first); the mutant list stands in
for the fail-first run, except where the commit message says a test failed first.
