# Batch 1011, group G5: the delivered product's quality as a record, not a verdict — journal, 2026-10-09

Worktree `.claude/worktrees/b1011p-aaa47e`, branch `batch1011p-aaa47e`, base `30a3b40a`. Harness-only: no skill, no release.
Basis: `docs/shiploop-e2e-harness-batch-1011-plan-2026-10-09.md` (row G5), the design and its audit
`docs/experiments/batch-1011-harness-design-audit-20261009/design-audit.json` (key `F5-delivered-quality`; the audit's
`safer_alternative` is the scope), SPEC `test/shiploop_e2e/SPEC.md` (the amendment of this group: the table row `quality` and the bullets
"A planning_review mode is an option of a named case" and "Delivered quality is recorded, never judged").
Evidence: `docs/experiments/batch-1011p-g5-quality-20261009/evidence.json` (recomputed over the eight saved deliveries, one example block).

## What was asked and what was built

| Step | Commit | What |
|---|---|---|
| 1 | `8b98ccf7` | SPEC amendment, dated 2026-10-09: the `quality` row; the planning_review option; "Delivered quality is recorded, never judged" (gate, order, processes, comparability, held-out, hosts, Claude memory), non-regression, dispositions. |
| 2 | `bf085ec9` | `--planning-review stage\|none` as an option of a named case. The prerequisite: the Grok `none` runs (r2, r3 of 2026-10-08; baseline rows 2026-10-06T18:17 and 2026-10-07T10:17) are case `custom`, style null, because the mode rode in `--prompt`/`--check`. |
| 3 | `2b432fc5` | `test/shiploop_e2e/quality.py` (JS mutation, Checkers held-out acceptance, the Claude memory-write reader), `checks/checkers_accept.py`, `test/fixtures/quality/`. Not yet called by `run.py`. |
| 3b | `18bd076e` | SPEC refinement the first recomputation forced: `loaded_by_tests` is "no sign of a load", a lower bound. |
| 4 | `b33bb47c` | `run.py` wiring (`case_quality`, `quality_gate`, `quality_record`, the second result write, the baseline-row summary, one printed line), the case data in `cases.json`, README. |
| 5 | this commit | this journal, the evidence extract, the gate replay fixture and test, a LEARNINGS entry. |

Not built, by the brief and the audit: the UI/browser observation (until it can click through CDP; no `find_browser`), the Battleship acceptance
set, the port lease and serialisation, `CLAUDE_CODE_DISABLE_AUTO_MEMORY`, the argv exec scrub, the overlap record (G4), the name-pattern kill
count (G1). Sizing: the design said `m`; the audit's `l` was right (a module, a case option, two scripts with a reference service, about 90 tests).

## Part 1. `--planning-review` on a named case (commit 2)

`python3 test/shiploop_e2e/run.py --case battleship --planning-review none`: the harness appends the engine's own wording to the case prompt,
`Start ShipLoop with the run option --planning-review none and --improve-skill <plugin_dir>/skills/improve/SKILL.md.` (for `stage` only
`--planning-review stage`); a plugin with no Improve card is refused before any host starts; refused with `--seed-at`; a resume must name the
run's own value or none (`planning_review_choice`). `invocation.json` gains `planning_review` and `improve_skill` (null when not given). The
choices are the engine's `PLANNING_REVIEW_MODES` (one source). `load_case` is untouched (its 4-tuple is unpacked by `FollowOnTest` and `_main`).
A suite passes the option through to every case. The baseline row's `planning_review` stays the one `state.md` recorded; a `none` run of
`battleship` now has case `battleship`, style `web-service`, and therefore a comparable cell and a quality declaration.

Argparse prefix abbreviations (`--pro`, `--chec`, `--planning`) are accepted by `run.py` as by any argparse program, so the exec-based
`scrub_argv` the design proposed would have been bypassed by them (the audit's point). It is not built; the first-class option removes the
exposure for named cases instead. A custom `--prompt`/`--check` run still carries its check text in the harness argv (the r3 Checkers model
printed it with `pgrep`, events 550 and 570), and Claude's `-p <prompt>` and Codex's last argument carry the case prompt in the host's argv
(standard input stays closed, S-14). Documented in the SPEC, not fixed.

## Part 2. Mutation of the delivered tests (commit 3)

`quality.mutation(copy, spec, ...)` on a copy under `<output>/quality/copy` (`export_delivery`: `git ls-files --cached --others
--exclude-standard`, no `.git`; `work/` is only read, hash- and `git status`-checked by a test).

* **Operators** (catalog `js-1`, `quality.JS_OPERATORS`): `===`/`!==`, `<`/`<=`/`>`/`>=`, `&&`/`||`, `true`/`false`, spaced `+`/`-`, the literal
  after a comparison stepped by one; in code only (comments, strings and template bodies are masked; a regular expression literal is not
  recognised, so a `//` inside one masks the rest of its line). Any change to the operators or the mask is a new id.
* **Targets**: `.js .mjs .cjs` outside `test`, `tests`, `__tests__`, `node_modules`, `docs`, files that look like node's own test patterns
  and the case's `exclude` (`system` for Battleship and Checkers). Nothing else has a catalog: a Python delivery is `observed: false`, with the
  files by extension in the reason.
* **Baseline gate**: the unmutated copy's test run must exit 0 within the ceiling and count at least one test. The count is read by the
  engine's one reader, `shiploop_test_counts.count`, through the JS catalog entry `js_test_count`. That is a deviation from the audit's wording
  ("the `pass N` regex with both prefixes lives in the extension catalog"): there is no regex in `quality.py` at all, because the engine
  already has the one catalog of how runners report counts (S-12), TAP and spec prefixes included.
* **Counting**: `killed` is a failing or hung run; `timeout` is the hung subset; `invalid` (the mutated file no longer parses, `node --check`)
  is out of the ratio; `survived` ran green. `killed + survived + invalid + not_run = sites`. `ratio = killed / (killed + survived)`, null when
  nothing was decided. All survivors are listed (`file, line, op, from, to`); the design capped them at 40 with no basis for 40.
* **Order and ceilings**: round-robin across files (first site of every file, then the second, ...), so a ceiling hit leaves a sample of every
  file (pinned: 4 mutants over 3 files leave 2/1/1). Two ceilings, both documented as ceilings and not tuning values, as `LSOF_TIMEOUT` is:
  `RUN_CEILING_SECONDS = 10` (one test run; the saved suites took 0.23 to 1.27 s, and the prototype sweeps ran with 10 s) and
  `PHASE_CEILING_SECONDS = 600` (the longest sweep here was 113 s, the prototype's 152 s). The audit asked for "one time ceiling": a second is
  needed because a mutant that hangs would otherwise spend the whole phase, and the prototype's fixed 10 s per run is the only recorded basis
  there is. No 20x-baseline rule and no 120-mutant stride cap (neither has a basis; the largest measured site count is 108).
* **`loaded_by_tests`** per file: true when the baseline run's V8 coverage (`NODE_V8_COVERAGE`, one record per process that exits by itself)
  lists the file **or a mutant of it was caught**; false when neither; null when no coverage was written and no mutant was caught. See finding F2.
* **Process safety** (audit correction 7): every child (baseline, syntax check, each mutant run, a product's server) starts in its own
  session, is registered in the caller's `groups` (the harness passes `run.LIVE_HOST_GROUPS`, so `terminate()` and the `atexit` hook end it) the
  moment it starts, and is forgotten once its leader is reaped; `end_group` signals a group only while `proc.poll() is None` and
  `os.getpgid(pid) == pid` (on macOS `getpgid` raises once the leader has exited, even before it is reaped, so a leader that has already
  exited is never signalled by group, and `killpg` is never called after a clean reap); a hung run is killed whole (a test starts a child that sleeps 60 s: both are gone within
  seconds, the phase returns in under 30 s); the `stop` callable (`run.quality_stop`: TERMINATION or `<output>/stop`) is asked before each
  mutant and once after the last, because a run the stop itself killed exits non-zero and would read as a caught mutant; `listeners.reap` runs on
  `<output>/quality` only (a real-lsof test: a server the test run leaves is stopped, a sibling under `<output>` is not). Not covered: a SIGKILL of
  the harness during the phase leaves the in-flight run (see open risks).

## Part 3. Held-out acceptance, Checkers only (commit 3)

`checks/checkers_accept.py` holds six checks (`CHECKS`: id to `fn(base_url) -> (ok, note)`): `red-moves-first`, `illegal-keeps-turn`,
`off-board-keeps-turn` (the bundled item split: off the board and negative index only), `legal-moves-alternate`, `red-jump-mandatory`,
`black-jump-mandatory-and-removal` (black must jump, and the removed piece's square can be recaptured onto). `cases.json` quotes the prompt
sentence each reads (`source`). `quality.acceptance` starts the case's `start` command (`node server.js`) in the copy with `PORT` set to a free
port, imports the module **inside the harness process** and calls each check, so no check text or id is on any argv (a test spies on every
`Popen` and asserts only the server's own command line is started). A server that never listens leaves the block unobserved (never failed);
a check that raises fails with the exception as its note.

Calibration (`AcceptanceCalibrationTest`): `test/fixtures/quality/reference_checkers.py` is a hermetic Checkers service with one defect
switch per rule (`black-first`, `illegal-flips-turn`, `offboard-400` which is the saved r3 delivery's behaviour, `no-alternation`,
`optional-jump`, `black-optional-jump`, `no-removal`). The exact failing set of each is pinned; every check fails some defect, every defect
fails some check, `offboard-400` fails exactly `off-board-keeps-turn`, and the correct service passes all six.

Battleship: the design's probe (`/private/tmp/f5-scratch/heldout_probe.py battleship`, unchanged, ephemeral ports) was rerun on the five saved
Battleship deliveries: **8 of 8 runnable items pass on every one, r3 included** (`HB11`, the default port 3000, is not run). It separates
nothing, so it is not built. Its title and sweep checks also duplicate checks that `cases.json` already has.

## Part 4. The Claude memory-write reader (commit 3)

`quality.memory_writes(events.jsonl)`: Claude `Write`/`Edit`/`MultiEdit` calls whose `file_path` is under `.../.claude/projects/<slug>/memory/`,
in order, `{path, tool, line}` with `line` the 1-based line of `events.jsonl`. Over all 25 saved event files (`/Users/dadleet/e2e-runs/2026*/*/`)
it finds exactly two writes, in `20261008/r3-checkers-sonnet` at lines 599 and 605 (`memory/feedback_no-broad-pkill.md` and `MEMORY.md`), and
none in the other 24. It reads no directory (36 of the 37 `e2e` project dirs hold an empty `memory/`), touches nothing under `~/.claude` and sets
no environment variable (`CLAUDE_CODE_DISABLE_AUTO_MEMORY` changes every Claude run: an owner decision). A write by a shell command is not seen:
a lower bound. For a run whose launch records show no Claude session the value is null with the reason in `unmeasured`.

## Part 5. Wiring (commit 4)

`_main` writes result.json and metrics.json as before; then `quality_gate` (stop requested or the harness told to end, engine active,
`shiploop` not passed, `committed` not passed, the case lock not held) decides whether the delivery is measured; `quality_record` calls
`quality.measure` (hosts from `runrecord.hosts_used(out)`, the live groups, the stop callable) and writes result.json again with `quality`.
Any exception in the phase is the block's reason (fail open: no verdict, no exit code, no baseline decision changes). A regrade measures too,
unless another harness holds the case lock. The stop file is not consumed by the phase (the next `--resume-run` removes it, as before).
`baseline_row` gains an optional `quality` summary for a case that declares measures; one `  quality   ...` line is printed per run.

## Evidence

All figures below were recomputed from the saved runs with this code (scratch copies; `evidence.json` holds per-file counts, every survivor and
the example block). Machine load average was 6 to 8 (other batch agents were testing), which stretches seconds, not counts.

| Delivery | Sites (per file) | Caught of sites | Timeouts | Ratio | Prototype (other code, one sweep) | Seconds | Held-out |
|---|---|---|---|---|---|---|---|
| r1-battleship-sonnet | 33 (game.js 22, server.js 11) | 27 | 3 | 0.8182 | 27/33 | 47 | |
| r2-battleship-sonnet | 42 (25, 17) | 33 | 3 | 0.7857 | 33/42 | 113 | |
| r3-battleship-sonnet | 36 (lib/game.js 19, server.js 17) | 20 | 1 | 0.5556 | 20/36 | 26 | |
| v1230-battleship-sonnet | 58 (39, 19) | not run: `test/system.test.js` ST-3 listens on :3000 | | | 43/58 | | |
| r2-battleship-grok-none (mixed host) | 105 (rules.js 69, server.js 36) | not run: `test/http.test.js` TC-port listens on :3000 | | | 85/105 | | |
| r1-checkers-sonnet | 108 (rules.js 76, server.js 32) | 88 | 0 | 0.8148 | 88/108 | 37 and 40 | 6 of 6 |
| r2-checkers-sonnet | 72 (52, 20) | not run: TC-1 (c) and ST-3 listen on :3000 | | | 61/72 | | 6 of 6 |
| r3-checkers-sonnet | 86 (64, 22) | 78 | 2 | 0.9070 | 78/86 | 65 | 5 of 6 (`off-board-keeps-turn`) |

* The site counts equal the prototype's for all eight, and the caught counts equal its for the five re-run, so the operator catalog `js-1` is
  the prototype's set and the figures that motivated the design are not artefacts of other code. The three deliveries not swept are the ones whose
  own tests bind port 3000: this work starts no server on a fixed port, so their ratios are the prototype's, not recomputed.
* r3-battleship swept twice in a row: 20 caught (1 timeout), 16 survivors, **identical survivors**. n=2 on one delivery; the design's "identical
  across two sweeps" for r1 Checkers (88/88) and r3 Battleship (20/20) could not be re-checked from retained files (one sweep each), this is a fresh pair.
* Timeouts: baselines took 0.3 to 1.0 s, so a 10 s run is a hang of at least ten times that even at load 6 to 8; r3's single timeout was the same in
  both sweeps. Whether a timeout is a real hang or load is not decided by the ratio; `timeout` is recorded for that reason.
* Seven of the eight keep the page's JavaScript in an HTML file (`<script>` inline, no `src`); r2-battleship-grok-none has no HTML file, its page
  is built in `server.js` strings. No operator reaches either, which is the known limit the SPEC names; the audit's "all 8 inline page JS in HTML"
  was one off.
* Headline wording (audit correction 15): the mutation ratio of r3 Battleship, 0.56, is the **lowest of four Battleship deliveries** (the others:
  0.82 and 0.79 recomputed, 0.74 prototype), **consistent with the hand finding** (8 of 17 hand-made mutants survived on r3, three of them page
  mutants outside this catalog), and **not separable at four runs or fewer**. It does not single r3 out, and no hand ranking of the other three
  exists to reproduce.
* Memory writes: 2 in 25 saved event files (above).

## Findings

| # | Finding | Status | Evidence |
|---|---|---|---|
| F1 | `js-1` reproduces the prototype's site counts for all eight deliveries and its caught counts for the five re-run. | firm | table above; `evidence.json` |
| F2 | The coverage record alone says the saved r1 Checkers `server.js` was never loaded, although 23 of its 32 mutants were caught: the tests spawn `node server.js` and stop it with a signal, so it writes no coverage. `loaded_by_tests` therefore counts a caught mutant as proof of a load, and false means only "no sign of a load" (a lower bound). Found by the recomputation; a test pins it; SPEC refined (`18bd076e`). | firm | `evidence.json` `loaded_by_tests_before_the_fix`/`after_the_fix` |
| F3 | The Checkers held-out set passes r1 and r2 (6 of 6) and fails r3 on `off-board-keeps-turn` only: HTTP 400 `{ok:false, error:"invalid coordinates"}` with no turn or winner, against the prompt's "returns JSON with ok, turn, winner" and "an illegal move ... leaves the turn unchanged". This is the defect the round-3 hand analysis found (a spec self-contradiction on off-board targets). The check is one reading of two sentences; a reader could take an off-board target for a malformed request, which is why it is its own id and quotes its source. | firm for the result; interim for how much it means (one delivery) | `evidence.json` |
| F4 | The Battleship held-out set passes 5 of 5 deliveries, r3 included (8 of 8 runnable items): no information, not built. | firm | rerun of the design's probe |
| F5 | The mutation ratio and the hand analysis agree on direction for r3 Battleship and cannot be separated from run-to-run spread at n of 4. | interim | table above |
| F6 | The saved gate records behave as the audit read them: r3-battleship-grok-none (stopped, engine active, no tracked file) is not measured; r3-checkers-sonnet is; the regraded r2-battleship-grok-none is measured and its hosts come from its launch records. | firm | `test/fixtures/quality/gate-records.json`, `QualityGateTest` |
| F7 | A second non-blocking flock on a case lock in the same process fails, so the phase reuses the lock `main` holds and never acquires one. | firm | `test_a_second_lock_in_one_process_fails_...` |
| F8 | A delivery's `node --test` suites bind ephemeral ports (port 0) in five of the eight; three bind :3000 in a test (v1230, r2-checkers, r2-grok). A live quality phase therefore needs :3000 free, and a baseline that is red because :3000 is held reads `observed: false`, never a ratio. | firm for the saved deliveries | `grep` of the saved tests |

## Deviations from the design and the audit, with the reason

1. **Two ceilings, not one** (above): a hung mutant would otherwise spend the whole phase.
2. **The engine's test counter**, not a regex in the catalog (S-12).
3. **Acceptance in-process** (`importlib`), not `python3 script <id>`: an id or a script name on a command line is visible to any model on the
   machine, which is the exposure the audit's own evidence showed (events 550, 570).
4. **Check ids** are named for what they read (six ids), not `HC2..HC9`; the robustness kind (unknown game id, malformed JSON) is dropped: it is not
   in the request, and `kind` was only there to keep it from reading as a requirement.
5. **`killed` includes `timeout`** (timeout is a subset, listed separately) so that `killed + survived + invalid + not_run = sites` is the whole
   arithmetic; the design's `detected_ratio` is `ratio` here.
6. **`quality` is always present in result.json** for a run that reached the phase (a gate reason, or "declares no quality measures"), with
   `declared` naming what the case asked for; the design said an absent key means "not declared". The baseline row's `quality` is absent for a case
   that declares nothing, so no cell changes shape.
7. **Regrade measures** (the audit left it open): a regrade reproduces the block from the run record and the delivered folder, and refuses when
   another harness holds the case.
8. **The stop file is not consumed by the phase.** The design had the phase's reap clean up; the README's rule that the next `--resume-run`
   removes a stale stop file is kept.
9. **Survivors are all listed**, not capped at 40.
10. **No `host_profile`/`host_isolation`**: with the env var out of scope (owner decision) the only hygiene part is the detector, whose home is
    the `quality` block.

Disagreements with the audit: none that changed behaviour. One correction is imprecise: "all 8 saved deliveries inline page JS in HTML" (seven
do; r2-battleship-grok-none builds the page in `server.js`); the safer behaviour (document the limit, compare within one catalog id) is
implemented as asked.

## Data shapes for the Run Review session

`result.json["quality"]` (optional: absent on runs from before this change; a run that reached the phase always has it). Example: the real
`20261008/r3-checkers-sonnet` (its events and work folder, hosts from its `invocation.json`); the full block is in `evidence.json` `example_block`:

```
observed: true                      # false + reason when no delivered-product measure was taken
declared: ["mutation", "acceptance"]
hosts: ["claude"], mixed_host: false          # from invocation*.json (runrecord.py), never --host
delivered_files: 18, seconds: 60.7
mutation: {observed: true, operator_id: "js-1", command: "node --test", source: "...", baseline: {returncode: 0, seconds: 0.359, tests: 32},
           sites: 86, killed: 78, timeout: 2, survived: 8, invalid: 0, not_run: 0, ratio: 0.907, ceiling_hit: false,
           ceilings: {run_seconds: 10, phase_seconds: 600},
           per_file: {"rules.js": {sites: 64, loaded_by_tests: true, killed: 61, timeout: 1, survived: 3, invalid: 0, not_run: 0}, "server.js": {...}},
           survivors: [{file: "server.js", line: 33, op: "rel-bound", from: ">", to: ">="}, ...], seconds: ...}
acceptance: {observed: true, source: "...", ids: [6 ids], passed: [5 ids], checks: [{id, source, pass, note}, ...]}
held_out_seen: 0                    # null (+ unmeasured.held_out_seen) when events.jsonl is unreadable or the case holds nothing out
memory_writes: [{path: ".../memory/feedback_no-broad-pkill.md", tool: "Write", line: 599}, {... "MEMORY.md" ..., line: 605}]   # null + unmeasured when no Claude session
unmeasured: {<key>: <reason>}       # only the null keys
left_behind: {observed: true, reaped: [], survived: []}     # the phase's reap of <output>/quality
```

Unobserved forms: `{observed: false, declared: [...], hosts: [...], mixed_host: false, reason: "<gate or why>", memory_writes, held_out_seen, unmeasured, seconds}`;
a sub-block `mutation`/`acceptance` is `{observed: false, reason}` (with `baseline` when the baseline ran). `invocation.json` gains
`planning_review` ("stage"/"none"/null) and `improve_skill` (absolute path/null). The baseline row gains `quality`:
`{observed, hosts, mixed_host, mutation: {operator_id, sites, killed, survived, ratio, ceiling_hit} | {observed: false}, acceptance: {ids: 6, passed: 5} | {observed: false}}`
(absent for a case that declares nothing); its `planning_review` stays the engine's. Rendering rules for the page: every figure is "record only";
show `observed:false` as "not observed: <reason>", an absent facet as nothing, never an unobserved ratio as 0; print `operator_id` beside the ratio
and never compare two ratios of different ids; show `loaded_by_tests: false` as "no sign of a load"; show `timeout`; mark `mixed_host`.

## Open risks, unknowns and what could not be verified

* **A live run was not made** (rule: no live E2E run, host, model, browser or fixed-port server). The phase is exercised through `run.main` with
  the fake hosts and a stand-in for `node --test`, and by hand over the saved deliveries; the first live Checkers/Battleship run is its real test.
* **A SIGKILL of the harness during the phase** is not covered by the `atexit`/signal path (the audit's first missed unknown): the in-flight
  test run, if it is hung, is orphaned. Orphaned `node --test` groups over a day old exist on this machine from other sessions. Bounded by one run;
  not mitigated (a wrapper with an alarm would add a process layer for an adversarial case).
* **Suite concurrency**: with `--max-parallel 3` a finished chain runs its CPU-heavy phase beside sibling chains' hosts; load can turn a slow
  mutant into a timeout. Recorded (`timeout`, `seconds`), not serialised.
* **:3000** must be free for deliveries whose tests bind it (three of the eight saved); otherwise the baseline is red and the mutation block is
  `observed: false` with that reason.
* **`held_out_seen`** counts lines naming the module, the checks folder, `E2E_CHECKS` or `cases.json`; a model that reads the harness repository
  by another route would not be counted. Zero in all 11 saved event files the design read, and 0 on r3-checkers.
* **Other runners**: only `node --test` has been exercised against real output; the engine's counter reads many runners but the catalog has only
  JS operators, so every other language is "no operator catalog".
* **Python 3.14 / macOS only** were exercised.
* The Run Review exporter was not read or changed (not mine); it copies result.json and has no key whitelist per the audit.

## Tests and verification (real results, 2026-10-09, load average 6 to 8)

`test/shiploop-e2e-quality.test.py`, 92 tests (registered in `suite_catalog.SHIPLOOP_SUITES` at 29 s; `test-groups.test.py` pins 71 ShipLoop suites and
112 in all). By class: `PlanningReviewOptionTest` 8, `MutationOperatorTest` 7, `MutationRunTest` 18, `MutationNodeTest` 3 (real `node --test`),
`ProcessSafetyTest` 6, `AcceptanceCalibrationTest` 5, `AcceptanceRunTest` 9, `EventFactsTest` 9, `MeasureBlockTest` 8, `QualityReapTest` 1 (real lsof and
signals, scoped to the test's folder), `QualityThroughMainTest` 11, `QualityGateTest` 5, `CaseQualityTest` 2. No test starts a server on a fixed
port, reads the machine's process table (every class patches `listeners.observe` except `QualityReapTest`, which scopes it) or depends on
`/Users/dadleet/e2e-runs`; every process a test starts expires by itself (60 s, 120 s or 30 s at most).

| Command | Result |
|---|---|
| `python3 test/shiploop-e2e-quality.test.py` | 92 tests OK in 26 s |
| the same with node off `PATH` | 89 OK, 3 skipped (`MutationNodeTest`, reason: "this class runs the real `node --test` and needs node on PATH") |
| `python3 test/shiploop-e2e.test.py` | 404 tests OK in 116 s (404 before the change as well; no test of that file was edited) |
| `python3 test/shiploop-e2e-runrecord.test.py` | 6 tests OK |
| `python3 test/test-groups.test.py` | 21 tests OK |
| `bash test/run-all.sh --group quick --changed-from 30a3b40a` | PASS, 21 suites OK, among them `shiploop-e2e` and `shiploop-e2e-quality` |

Each behaviour was checked by breaking the implementation: 36 mutants of `quality.py`, `run.py` and `checkers_accept.py` (the restore, the
order, each gate, the guard, the registration, the stop checks, the regex, the reap folder, the hosts, the lock, the coverage rule, the ceiling,
the planning_review rules, ...); 35 are caught and one survives, `timeout or returncode != 0` to `returncode != 0`, which is equivalent (a timeout
has no return code). The hung-mutant test first passed with the group kill removed, because the hung child expired on its own after 60 s; it now
asserts that the phase returns in under 30 s and that the child is gone before its own 60 s are up. `quality.py` was drafted before its tests
(a departure from tests-first), and the mutation checks stand in for the fail-first run.
