# Local validation journal

Living record of the work that makes local test runs in this repository faster without weakening them, and keeps
them out of the developer's own state (round 2). Each round
states its question, the cases, the conditions and the result. Each finding carries a status (firm, interim,
exploratory or superseded) and cites its evidence. The runner is `test/run_suites.py` behind `test/run-all.sh`, the
inventory and the selection rules are `test/suite_catalog.py`, and `test/test-groups.test.py` pins both.

## Why (owner, 2026-10-25)

The owner, on 2026-10-25: "These are taking far too long. I need some way to get more efficient validation of these
things." That day's release cycle ran the serial quick group three times, each about 10 to 25 minutes. The
`--changed-from` selection also missed, twice, the packet-size suites that a prompt edit is most likely to break.
Commit 58a8f2eb records it: "the earlier quick runs had not selected those suites". A third, wider run caught a step-plan
head over its cut.

## Round 1 (2026-10-25): `--jobs N`, the packet-source rule and the `prompt` group

**Questions.** Can suites run side by side with the same verdict and output as a serial run? Does a prompt or packet
source edit reach the packet-size suites? Is there a loop for prompt edits that is shorter than quick?

**Changes** (one commit; its message cites this round):

- `run_suites.py` gains `--jobs N`. The default is `min(os.cpu_count(), 8)`, which is 8 on the 18-core development
  machine and 4 on a GitHub `ubuntu-latest` runner. The suites run in a thread pool, but output, `OK`/`FAIL` lines and
  receipt records are still emitted in catalog order: suite *i* is printed once it and every suite before it have
  finished. The exit code is unchanged (1 if any suite failed). `--jobs 1` keeps the original loop, where a suite
  starts only after the previous one is in the receipt. The receipt gains `jobs` and `wall_seconds`. A closing line
  gives the wall time and the three slowest suites, which set the floor no job count goes under. On Ctrl-C the runner
  TERMs, then after one second KILLs, the process group of each suite still running. Each suite leads its own session,
  so before this the interpreter would have waited at exit for all of them.
- `suite_catalog.py` gains `PACKET_SIZE_IDS`: `shiploop-packet-completeness`, `shiploop-step-packets`,
  `shiploop-packet-recut` and `shiploop-head-order`. A packet source selects those four plus
  `shiploop-packet-obligations`, alongside whatever the name and hub rules pick. The packet sources are
  `shiploop_prompts.py`, `shiploop_navigator.py`, `shiploop_stage_spec.py`, `shiploop_loops.py` and
  `shiploop_narrative.py`. Before this, `shiploop_prompts.py` (a hub with more than 8 referencing suites) selected the
  fixed hub consumer set and none of the four. The four `_PATH_SUITE_IDS` rows that sent the same files to
  `shiploop-packet-obligations` alone are folded into this rule. `SKILL.md`, `references/` and `commands/` already
  selected the four, through `_SHIPLOOP_PROMPT_IDS`, which now spells them as `*PACKET_SIZE_IDS`.
- A new group, `prompt`, runs the four packet-size suites and `shiploop-packet-obligations`, plus the light suites whose
  own test files changed since `--changed-from REF` (which is now accepted for quick or prompt). It is the loop while
  editing a prompt; quick stays the gate before a push. The ledger was added at the parent session's request. The
  2.11.0 release failed CI on it while the four packet-size suites passed locally: its anchors are literal phrases of
  `shiploop_prompts.py`, and a rewrap had split "first step that uses it" across two source lines.
- `validate_catalog()` now refuses a selection rule that names an unknown suite id, so a renamed suite cannot drop out
  of a rule without a word. Every id resolved when the check was added.

**Tests** (`test/test-groups.test.py`, 46 tests):

| Test | Shows |
|---|---|
| `test_parallel_jobs_report_what_one_job_reports` | On the 11 fake `ask-agent` suites, `--jobs 4` and `--jobs 1` give the same exit code, stdout (less the timing and receipt-path lines), stderr and receipt records, in catalog order. Run four times: no failure, then one at the first, the middle and the last suite. |
| `test_jobs_run_suites_side_by_side_and_one_job_never_overlaps` | Each fake suite passes only once 4 have arrived at a barrier, so `--jobs 4` passing proves the overlap. The control is `--jobs 1` with a barrier of 2, where exactly the first suite fails. |
| `test_an_interrupted_parallel_run_stops_the_suites_it_started` | SIGINT to a `--jobs 3` run whose suites sleep 60 s: the runner exits within 10 s, no fourth suite starts, and every suite process is gone. |
| `PacketSourceSelectionTest` (5 tests) | The four ids are pinned. Each packet source and the prompt surface selects them in quick, and each source also selects the ledger in quick and keeps the hub. The `prompt` group is the four, the ledger and the changed light suites. An unknown id in a rule is refused. |
| `test_execution_continues_after_failure_and_persists_incremental_receipt` | Now runs with `--jobs 1`: the serial receipt is still written after each suite, before the next one starts. |

Fail-first: the same test file run against 5d3628b0's runner and catalog gives 6 failures and 17 errors. The errors
are mostly the missing `PACKET_SIZE_IDS` and `--jobs`. The behavioural miss was printed separately: on 5d3628b0,
`targeted()` for `shiploop_prompts.py`, `shiploop_navigator.py` and `shiploop_stage_spec.py` holds none of the four.
A mutant runner with the interrupt cleanup removed fails the interrupt test, because the runner is still alive after
10 s.

**Timing** (development machine, 18 cores, shared with other sessions; the evidence is the receipts below):

| Run | Code | Suites | Wall | Load average (1 min, start to end) |
|---|---|---|---|---|
| `--group quick --changed-from origin/main` | 5d3628b0, serial | 16 | 295.9 s | 9.0 to 13.9 |
| `--group quick --changed-from origin/main` | this round, `--jobs 8` | the same 16 | 133.0 s | 15.1 to 14.4 |
| `--group prompt`, before the ledger joined it | this round, `--jobs 8` | 4 | 10.5 s (22.1 s of suite time) | 15.1 |
| `--group prompt` | this round on 5d3628b0, `--jobs 8` | 5 | 8.5 s (22.1 s of suite time); the ledger fails 7 tests, the four pass | 11.7 |
| `--group quick --changed-from origin/main` | this round rebased onto 891be21e, `--jobs 8` | the same 16 | 125.9 s, PASS | 10.4 to 11.0 |
| `--group prompt` | this round rebased onto 891be21e, `--jobs 8` | 5 | 8.5 s, PASS (the ledger is green after 891be21e) | 11.0 |

The parallel quick run is 2.2 times faster. Its wall equals its slowest suite, `shiploop-chain-async` (124.5 s serial,
127.5 s in parallel), and `shiploop-navigator-contract` is second (105.9 s, then 101.2 s). Every other baseline suite
finishes under them, so a quick run cannot get shorter without making those two shorter. On a change selected after
this one, the floor is whichever selected suite is slowest. The brief's 2026-10-25 measurement of seven ShipLoop
suites shows the same: `shiploop-callback-contract` (325 s), `shiploop-actual-improve-cli` (302 s) and
`shiploop-navigator-contract` (163 s) set a 5.4-minute wall against about 14 minutes serially. `test-groups` grew from
6.0 s to 27.2 s in the parallel run. A test that rebuilt `quick()` once per catalog suite cost 8.5 s and was fixed
before the commit. The file now takes about 13.5 s alone, most of it the eight fixture runs of the equivalence test.

**On GitHub CI.** The round was pushed to `main` as ef3fb8be, which is f72de7b3 rebased onto 79b3490e. An
`ubuntu-latest` runner has 4 vCPUs, so the default there is `--jobs 4`. Both runs below are push runs of the quick
tier on the same 16 baseline suites, since 79b3490e changed only docs:

| Run | Commit | Quick job, setup included | Runner wall | Result |
|---|---|---|---|---|
| [40237296441](https://github.com/whichguy/skill-craft/actions/runs/40237296441), serial | 79b3490e | 3 min 26 s | not printed (the old runner has no timing line) | success |
| [40237477513](https://github.com/whichguy/skill-craft/actions/runs/40237477513), `--jobs 4` | ef3fb8be | 1 min 23 s | 51.0 s | success |

On CI the floor is `shiploop-navigator-contract` (50.9 s), then `shiploop-chain-async` (30.8 s) and
`shiploop-navigator-dry-run` (30.3 s). `shiploop-chain-async`, the local floor, takes about 125 s on the shared
development machine against 30.8 s on CI. The cause of that gap was not measured.

The 5-suite prompt run on 5d3628b0 reproduces the 2.11.0 CI failure locally in 8.5 s. `shiploop-packet-obligations`
fails seven tests while the four packet-size suites pass. That is the case for keeping the ledger in the group. The
fix, 891be21e on `main`, keeps the anchored phrase on one source line. On `main`'s own diff from 5d3628b0 to 891be21e,
which edits `shiploop_prompts.py` and `shiploop_navigator.py`, quick now selects the four packet-size suites and the
ledger.

Where the slow suites spend their time (per class, the four profiled side by side on 5d3628b0, load average about 12
to 13):

| Suite | Tests | Seconds | Largest classes |
|---|---|---|---|
| `shiploop-chain-async` | 3 | 128.9 | `AsyncCallbackTests` is all of it, about 43 s per test |
| `shiploop-navigator-contract` | 130 | 101.0 | `EightStageInnerLoopCliTests` 60.8, `CliBoundaryRegressionTests` 15.7 |
| `shiploop-callback-contract` | 84 | 215.2 | `RefusalRouteTests` 73.3, `EveryStageRouteTests` 29.3, `PathHandlingRouteTests` 22.2 |
| `shiploop-actual-improve-cli` | 89 | 173.9 | `EphemeralImproveCliTests` 81.5, `ImproveCommitContractTests` 50.8 |

Evidence in `docs/experiments/local-validation-20261025/`:

- `quick-serial-5d3628b0.receipt.json` and `quick-jobs8.receipt.json`: the two quick runs.
- `prompt-jobs8-5d3628b0-ledger-red.receipt.json`: the 5-suite prompt run.
- `slow-suites-by-class.txt`: the profile.

**Findings**

- F1 (firm): `--jobs` keeps the verdict, the exit code and the catalog-order output. Proof: the equivalence and
  barrier tests, and the 16-suite quick run passing at `--jobs 8` with the same suites as the serial run.
- F2 (firm): a prompt or packet source edit now selects the packet-size suites in quick. Proof:
  `PacketSourceSelectionTest`, which fails on 5d3628b0.
- F3 (interim): a quick run's wall is now its slowest selected suite. For the baseline that is `shiploop-chain-async`,
  then `shiploop-navigator-contract`. Shortening those, by sharding one or by trimming its slow classes, is the next
  gain. Sharding was not done in this round. All four slow suites run plain `unittest.main()`, and the catalog keys
  durations, shards and the count pins by path, so a split needs a `load_tests` partition in the test file plus
  catalog entries that share a path. `shiploop-chain-async` is three tests in one class, so only a split by test name
  would work, and a new test would fall outside every shard. That is not a simple change. Splitting it three ways would
  bring the baseline's floor to `shiploop-navigator-contract`, about 100 s against 133 s. Update 2026-10-28: the floor
  is now `shiploop-navigator-contract`, at 86.4 s on CI and 156.5 s locally, so splitting `shiploop-chain-async` alone
  would no longer shorten quick. See F17.
- F5 (firm): the `prompt` group needs the obligation ledger. On 5d3628b0 the four packet-size suites pass while the
  ledger fails, which is the 2.11.0 CI failure. Proof: `prompt-jobs8-5d3628b0-ledger-red.receipt.json`.
- F6 (fixed 2026-10-28; exploratory when written, unrelated to the runner): `shiploop-actual-improve-cli`'s
  `test_a_live_shaped_pass_needs_at_most_1500_characters_of_model_output` depends on the checkout path's length. On
  5d3628b0 it writes 1,536 characters and fails at a checkout path of about 130 characters (a scratch worktree), and
  passes at this worktree's 59-character path. CI's path is shorter still. Update 2026-10-28: it still reproduces on
  337b09c5, writing 1,538 characters at a 150-character checkout path and passing at 59.
  Fixed 2026-10-28 (test only, on 89a30e03): the cause was that the count included text the checkout decides. The
  command and the runtime's done line carry the interpreter, the checkout and the temp directory, about 400 of the
  1,380 characters at this worktree's 71-character path (review 578, command 283, done 519). Measured with those
  three paths replaced by fixed placeholders (a scratch run, not committed), a pass is 985 characters (review 578,
  command 143, done 264) at 71 and at 150 characters. The owner was offered keeping 1,500 for that path-free text
  (515 characters, 52%, of headroom; the original 1,437 against 1,500 left 4%, ad794e11), a bound of 1,200 or 2,000,
  or no number, and chose no number (2026-10-28; earlier the same day: "I'm also sensitive to fixing lengths with
  numeric values. I don't think we should be doing something that's so tight.").
  So the size test is removed. Its shape claim was already asserted by
  `test_an_unchanged_pass_gets_script_written_checks_and_the_printed_commands_finish_the_stage` (ShipLoop writes
  checks.md and the report JSON, and the commands are literal: no `$`, the receipt's own `done_argv`, the report by
  its absolute path) and by the IMP-8 test (every printed command drives the run for the hooks). The first now carries
  the reason in its docstring. What is no longer checked: a longer review, or longer but literal commands, are not
  failed; the review is the model's own text, and what regressed the live tails (IMP-8: 35-39% of 2.0-2.4 KB per
  tail typed through shell variables) is the shape.
  Proof: the old test at a 150-character detached worktree still failed with 1,538 (578, 362, 598). The whole
  `shiploop-actual-improve-cli` suite passes at 71 and at 150 characters. A done line typed through a shell variable
  (`REPORT=...; ... < "$REPORT"`, patched into a scratch worktree's `shiploop_navigator.py`) fails the shape test at
  its `assertNotIn("$", ...)`. `test_a_live_shaped_pass_needs_at_most_1500_characters_of_model_output` no longer
  exists; the older evidence files that name it are history.
- F4 (firm since 2026-10-28; interim when written on 2026-10-25): GitHub CI now runs each group with 4 jobs, the
  runner's CPU count. Quick ran in parallel there and passed: run 40237477513 took 1 min 23 s against 3 min 26 s serial.
  The full shards (`shiploop-1|2|3`, `core`) have not yet run in parallel anywhere, and the first release commit will be
  their first parallel run. If one is flaky under parallel load, `--jobs 1` in `ci.yml` restores the serial run.
  Superseded in part on 2026-10-28: the full shards have since run at `--jobs 4` in six release runs, and the last two
  passed every shard. See the recheck below and F16.

## Round 2 (2026-10-26): a private state home per suite, and the suites that wrote the developer's state

**Why.** On 2026-10-26 a SessionStart hook showed a real session "saved work". It was an active depth-2 Until Loop
stack in the owner's `~/.local/state/until-loop`. Its frames held placeholder values: work "w", request "q", scope "s",
and workspaces in test temp directories.

**Questions.** Which test wrote that stack, and does any current suite still write the developer's state? How can a
hermetic suite be made to fail when it does?

**Attribution (firm).** The file is `innerloop-session-0eba9f4e….json`. Its lock was created at 08:01 on 2026-10-18,
and the JSON was last written at 08:03. Until Loop names the file after the SHA-256 of the host session identity.
Hashing the session IDs of the local Claude Code transcripts matched exactly one session, `8acf399b…`. That session
had merged origin/main's Until Loop 0.10.0 runtime into the integration worktree (fe02651e). At 08:01:37 it ran
`until-loop-vendor` and six other suites directly, as `python3 -B test/<name>`, and at 08:02:55 it started a subagent
that ran them again. The branch's `test/until-loop-vendor.test.py` still had
`LeanReturnTests.test_a_run_without_a_receipt_prints_the_full_packet`. That test ran the CLI `start` with the
placeholder contract and none of `--isolated`, `--directory` or `--receipt`. Under 0.10.0 such a call is an
automatic session start: the stack is keyed to the inherited `CLAUDE_CODE_SESSION_ID` and written under
`${XDG_STATE_HOME:-~/.local/state}/until-loop`. The test's `done` then failed against the new two-pass rule, so the
frame stayed active, and the two runs pushed one frame each. 29407b46 deleted `LeanReturnTests` 30 minutes later.
`until-loop-vendor` on main calls the in-process `start()`, which writes an isolated temp file.

**Probe of the Until Loop suites** (unchanged runner and suites; 8 jobs). The probe ran 42 suites: quick's selection
for the runtime's three scripts, plus 11 more that name the runtime. Each ran with `XDG_STATE_HOME` set to one shared
sentinel and `CLAUDE_CODE_SESSION_ID=leak-probe`. All 42 passed, none wrote Until Loop state, and the real directory
was unchanged. The sentinel did hold a ShipLoop keepalive health record, and its `run_dir` named
`shiploop-full-runtime`. Every suite writes the same key, so that record shows only the last writer.

**The keepalive leak.** `shiploop_keepalive.health_notice` writes `home()/health/<host>-<sha256(session)[:32]>.json`
whenever a packet prints with `CLAUDECODE` and `CLAUDE_CODE_SESSION_ID` (or the Grok pair) in the environment.
`home()` is `SHIPLOOP_KEEPALIVE_HOME`, else `$XDG_STATE_HOME/shiploop/keepalive`. A suite run inside a session
inherits both markers, so its record lands in the developer's state under the live session's key. CI has no markers
and never writes one. The census of the owner's directory that day:

- 32 of 170 health records named a test temp directory as their `run_dir`. The largest sources were
  `shiploop-callback-contract` (7), `shiploop-lint` (6) and `shiploop-slice` (3).
- No entry in `runs/`, `bindings/` or `decisions.log` named one.
- Other live sessions were still adding records while this round ran: four between 08:07 and 08:34, keyed to
  sessions other than this one.
- Their temp prefixes were `shiploop-exp-`, `shiploop-callback-contract` and `shiploop-chain`. `shiploop-exp-` is
  `shiploop-e2e-experiments`, a suite main added that day, after this round's first base (7e9a59b6).

**Changes** (one commit; its message cites this round):

- `run_suites.run_process` gives each suite a private `XDG_STATE_HOME`, a temporary directory removed afterwards. It
  also drops `UNTIL_LOOP_STATE_DIR` and `SHIPLOOP_KEEPALIVE_HOME` from what the suite inherits. A suite that leaves
  anything in that home fails, with an error that names the files and how to isolate them. The path is resolved: an
  unresolved macOS temp path sits under the `/var` symlink, which Until Loop refuses as a state root. A leaking start
  would then fail before writing anything, and the guard would never see it. The body that runs the process moved
  unchanged into `_run_bounded`.
- `test/state_home.py` `isolate()` gives the calling process a private `XDG_STATE_HOME`, removed at exit, and drops
  the two overrides. The 27 suites below call it once at module level, so a direct run is isolated too. Every ShipLoop
  suite builds its subprocess environment from `os.environ`, so one call reaches them all. Only
  `shiploop-e2e-slice` (`GIT_ENV`) and `shiploop-e2e-run-trace` (`ENV`) copy the environment at module level, and
  both copies come after the call.
- `test/README.md` describes both.

**Tests** (`test/test-groups.test.py`, `StateHomeGuardTest`, 3 tests):

| Test | Shows |
|---|---|
| `test_a_suite_that_starts_a_session_without_its_own_state_root_fails_and_the_developers_stays_empty` | The real runtime's automatic session start, with the placeholder contract, fails the suite. The error names the stack, and stand-ins for the developer's `UNTIL_LOOP_STATE_DIR`, `SHIPLOOP_KEEPALIVE_HOME` and `XDG_STATE_HOME` stay empty. |
| `test_keepalive_health_written_for_the_host_session_fails_the_suite` | The real `health_notice`, called under Claude Code markers, fails the suite and names the health record. |
| `test_a_suite_that_gives_the_runtime_its_own_state_root_passes` | A suite that gives the runtime its own `XDG_STATE_HOME` passes, and its stack is in its own directory. |

Fail-first: against origin/main's `run_suites.py`, all three fail. The leaking suites pass. The isolated suite's stack
lands in the inherited `UNTIL_LOOP_STATE_DIR` instead of its own directory, because that override beats
`XDG_STATE_HOME`.

**The full catalog under the guard** (fail-first for the suites, before any suite fix; inside a live Claude Code
session; `--jobs 8`; load average about 29 to 46 from other sessions; 2249 s wall):

| Outcome | Suites |
|---|---|
| Passed | 131 |
| Failed only on the guard (their own tests exited 0), each leaving `shiploop/keepalive/health/claude-<this session>.json` and its lock | 23 |
| Timed out at 1800 s and left the same record (`shiploop-chain-lifecycle`) | 1 |
| Failed its own 20 s hold under load (`experiments-shiploop-chain-native-pilot`; passes alone in 140 s under the new runner) | 1 |

No suite left Until Loop state. `shiploop-full-runtime` passed here only because an earlier `setUp` form of the fix was
already in place when it started; the probe is its evidence.

**After the fix: direct runs.** The 25 suites ran 8 at a time, the way `python3 -B test/<name>.test.py` runs inside a
live session: host markers inherited, and `XDG_STATE_HOME` pointed at a per-suite sentinel standing in for the
developer's state. All 25 passed, and every sentinel was empty. `shiploop-chain-lifecycle` took 1324 s.

**Quick group** after the fix, `--changed-from origin/main` (85 suites, `--jobs 8`): PASS, 85 of 85, in
458.3 s wall. The real state counts (keepalive records naming a temp directory; Until Loop files) were the same before
and after the run.

**After the rebase onto 3e1ece77** (49 commits on main). The guarded runner ran 63 suites: quick for
`--changed-from origin/main` (61) together with every suite main had changed since 7e9a59b6 (14). 61 passed. The two
suites main had added, `shiploop-e2e-experiments` and `shiploop-e2e-run-trace`, failed only on the guard: each left a
keepalive health record under this session's key. Both now call `isolate()`. Afterwards they pass as direct runs with
empty sentinels and under the guarded runner. The real state counts did not change during the 63-suite run.

Evidence in `docs/experiments/local-validation-20261026/`:

- `until-loop-probe.txt`: the 42-suite probe.
- `full-catalog-state-guard.json`: each suite's status, return code, time and the files it left, for the full run
  before the fix.
- `direct-runs-after-fix.txt`: the 25 direct runs, and the 2 after the rebase.

**Findings**

- F7 (firm): the 2026-10-18 stack came from `LeanReturnTests`'s CLI `start`, which 29407b46 deleted. No current suite
  writes Until Loop state. Proof: the attribution above, the probe, and the full catalog.
- F8 (firm): 27 ShipLoop suites wrote keepalive health records under the live session's key when run inside a
  session: 25 at 7e9a59b6, and 2 that main added that day. `state_home.isolate()` stops that for direct runs. Proof:
  `full-catalog-state-guard.json`, the post-rebase run, and `direct-runs-after-fix.txt`.
- F9 (firm): `run-all.sh` gives each suite a private state home, and a suite that leaves anything there fails. Proof:
  `StateHomeGuardTest`, which fails on origin/main's runner.
- F10 (superseded 2026-10-27 by F13): the guard only fires where the leaking code path runs. Keepalive writes only
  under host session markers, which CI lacks, so it catches keepalive leaks in local runs inside an agent session, not
  in CI. Until Loop needs a session identity too, so CI would catch only a suite that sets its own
  `UNTIL_LOOP_SESSION_ID`. Round 3 gives CI stand-in markers.
- F11 (firm, fixed on main): `experiments-shiploop-chain-native-pilot` failed its 20 s B hold in both loaded runs that
  day (load average 29 to 46) and passed alone; it is independent of this round. Main's 2dbb8c4b, the same day, raised
  the hold to 120 s and the call limit to 180 s, after the same failure under `--jobs 8` (its journal's F38). This
  round was rebased onto that commit.
- F12 (closed 2026-10-27): the leaked records in the owner's state were not removed by this round. They were 2 Until
  Loop files and 32 keepalive records with their locks. On 2026-10-27, at the owner's word, all 66 went to Trash, and
  no keepalive record names a temp directory since. Sessions that run these suites from a checkout without this commit
  keep adding records until they update. The canonical checkout's uncommitted work went to
  `archive/canonical-wip-2026-10-27`, verified blob for blob, and the checkout was fast-forwarded to main. On 2026-10-27,
  18 of 28 worktrees still predated the fix; a separate session is archiving and removing the 15 stale ones.

## Round 3 (2026-10-27): stand-in host markers on CI, and a timing that sleep broke

**Why.** F10: the two stores that leaked write only under host session markers, and GitHub runners have none, so the
round 2 guard could not fire on CI. Separately, `shiploop-e2e-environment` failed once on 2026-10-27 while the machine
slept.

**Changes** (one commit; its message cites this round):

- `.github/workflows/ci.yml`: the "Hermetic group" step, which every tier runs, sets `CLAUDECODE: '1'` and
  `CLAUDE_CODE_SESSION_ID: ci-stand-in`. CI suites now take the same keepalive and Until Loop session paths as local
  runs inside an agent session, so a leak trips the round 2 guard there too. `test/ci-policy.test.py` pins both lines.
- `test/test-groups.test.py` `test_ci_stand_in_markers_let_the_guard_see_a_keepalive_leak` reads the two values from
  `ci.yml`, removes any real host markers, and runs the real `health_notice` through `run_suites.run_process`. Without
  markers, as on CI until now, the leaking suite passes; with the workflow's markers it fails. Fail-first: origin/main's
  `ci.yml` has no markers, so the test fails at its first assertion.
- `shiploop-e2e-environment`'s `test_a_check_that_times_out_is_timed_out_and_not_a_product_failure` now measures with
  `time.monotonic()` instead of `time.time()`. On 2026-10-27 the suite ran in 80.4 s of run time and 1086.5 s of wall
  time (`pmset` logged sleep and wake), and the test measured 173.5 s against its 15 s bound; a rerun passed. Every
  other duration in that file already used the monotonic clock, which does not advance while a Mac sleeps. A test cannot
  stage the sleep, so this change has no fail-first.

**Trial** (quick tier, `--changed-from origin/main`, in a CI-like environment: this session's real host markers removed,
the two stand-ins set): PASS, 17 of 17 suites, in 101.9 s wall at
`--jobs 8`. The 17 are quick's fixed baseline, which includes the ShipLoop boundary suites, plus the suites that this
round's changed files select.

**Findings**

- F13 (interim until CI runs it): CI now exercises the host-session paths where keepalive and Until Loop write state,
  so a suite that leaks that state fails on CI as well as locally. Proof:
  `test_ci_stand_in_markers_let_the_guard_see_a_keepalive_leak` and the trial above. The full tier with the markers is
  proven only on macOS so far; round 2's full catalog ran under a live session's real markers and showed no other
  effect. It meets ubuntu at the next dispatched or release full tier.
- F14 (firm): a duration bound measured with `time.time()` fails when the machine sleeps mid-test. Use
  `time.monotonic()` for durations, and keep the wall clock for timestamps the product compares (the same file's
  `launch_stamp` and overlap fixtures).

## Recheck of round 1 (2026-10-28, on 337b09c5)

**Question.** Main has gained 152 commits since round 1 landed (98983fa2). Do round 1's pieces and claims still hold?

**Code on main.** All of round 1 is still present:

- `test/run_suites.py`: `DEFAULT_JOBS`, `_outcomes`, `_stop_process_groups` and `_timing_line`. Round 2 added the
  state home around `run_process`.
- `test/suite_catalog.py`: `PACKET_SIZE_IDS`, `_SHIPLOOP_PACKET_SOURCES`, `prompt()`, and the unknown-id check in
  `validate_catalog()`.

Every name in `_SHIPLOOP_PACKET_SOURCES` still selects all of `_SHIPLOOP_PACKET_IDS` in `quick()`, and
`select(("prompt",))` is still the four packet-size suites plus `shiploop-packet-obligations`. `.github/workflows/ci.yml`
has no `--jobs` pin. The catalog has grown to 161 suites (106 ShipLoop), against 155 in round 1.

**Local runs** (this worktree fast-forwarded to 337b09c5, no local changes, `--jobs 8`, load average 9.7 at the start
and 18.5 at the end):

| Run | Suites | Wall | Slowest | Result |
|---|---|---|---|---|
| `--group prompt` | 5 | 8.7 s | `shiploop-packet-completeness` 8.7 s | PASS |
| `--group quick --changed-from HEAD` | 16 | 156.5 s | `shiploop-navigator-contract` 156.5 s, `shiploop-chain-async` 149.4 s, `shiploop-navigator-dry-run` 27.4 s | PASS |

**CI quick.** Run [40714446518](https://github.com/whichguy/skill-craft/actions/runs/40714446518) (04c45dce) took
86.5 s of runner wall for the same 16 suites. The slowest were `shiploop-navigator-contract` at 86.4 s, against 50.9 s in
round 1, then `shiploop-navigator-dry-run` at 43.1 s and `shiploop-chain-async` at 40.0 s.
`shiploop-navigator-contract` has 134 tests now, against 130 then.

**CI full tier at `--jobs 4`.** Every release since round 1:

| Release | Run | Result | Cause of a failure |
|---|---|---|---|
| 2.14.0 (6a5b9d24) | [40347599478](https://github.com/whichguy/skill-craft/actions/runs/40347599478) | failure | `shiploop-e2e-experiments`: a pinned ref (9ed4ec24) missing from CI's shallow clone; 26351fb9 skips it there |
| 2.15.0 (cebe0c3c) | [40350502942](https://github.com/whichguy/skill-craft/actions/runs/40350502942) | failure | the same |
| 2.16.0 (6f8f3af1) | [40364730883](https://github.com/whichguy/skill-craft/actions/runs/40364730883) | success | |
| 2.17.0 (2c961b40) | [40447967270](https://github.com/whichguy/skill-craft/actions/runs/40447967270) | failure | 8 suites. Six had stale expectations from the release's own change (090c8c88, 70d88d37), and two had races "that the busier runner exposed": git's detached auto-maintenance lock in `shiploop-e2e`, and SIGPIPE under `pipefail` in `install-targets`. All were fixed in 595973e7 |
| 2.17.1 (a1d6ed32) | [40599499725](https://github.com/whichguy/skill-craft/actions/runs/40599499725) | success | |
| 2.18.0 (292a2a36) | [40604228225](https://github.com/whichguy/skill-craft/actions/runs/40604228225) | success | |

At 2.18.0 each full shard's wall was set by one suite:

| Shard | Suites | Wall | Slowest suite |
|---|---|---|---|
| `core` | 53 | 662.6 s | `plan-dispatcher-mutants`, 472.7 s |
| `shiploop-1` | 30 | 466.1 s | `shiploop-chain-lifecycle`, 450.2 s |
| `shiploop-2` | 37 | 515.1 s | `shiploop-test-loop`, 323.2 s |
| `shiploop-3` | 39 | 244.1 s | `shiploop-e2e`, 119.9 s |
| `e2e-apparatus` | 2 | 848.4 s | `shiploop-e2e-apparatus` |

**F6 and the leaked state.** F6 still reproduces (see F6). A broad scan of the owner's keepalive health records for
temp paths found 43, all dated 2026-10-16 or earlier. Each one's `run_dir` is a session scratchpad under
`/private/tmp/claude-501`, which means a real run, not a test fixture. That agrees with F12: no test-fixture record
remains.

**Findings**

- F15 (firm): round 1 holds on 337b09c5. The pieces are present, the packet-source rule and the prompt group select as
  designed, and both groups pass. Proof: the checks and local runs above.
- F16 (firm): the full tier passes at `--jobs 4` on GitHub's runners (2.17.1 and 2.18.0, every shard). Parallel load has
  exposed three latent test races so far: the two at 2.17.0 (fixed in 595973e7) and the native-pilot hold (F11). Each
  was a test defect that serial timing had hidden, not a runner defect, so `--jobs 1` was never needed. Proof: the
  release table.
- F17 (interim): the quick floor grew. `shiploop-navigator-contract` went from 50.9 s to 86.4 s on CI with 4 more
  tests, and from about 101 s to 156.5 s locally, partly the higher load. It is now the quick tier's floor in both
  places, so shortening that one suite is the next gain for quick. In the full tier, the apparatus (848 s) and one
  heavy suite per shard set the wall.

## Round 1 follow-up (2026-10-28): assumptions written into the code, tight checks removed

**Why.** The owner, 2026-10-28: "make sure to insert our assumptions into the existing code so that we don't undo
something. I'm also sensitive to fixing lengths with numeric values. I don't think we should be doing something
that's so tight."

**Changes** (one commit; test infrastructure only; rounds 2 and 3's code is unchanged):

- `test/run_suites.py`: an assumptions block above `MAX_DEFAULT_JOBS`. It states that every suite is hermetic and a
  suite that fails only beside others has a test defect, that no verdict may depend on a loaded machine's speed, that a
  parallel run reports what a serial one does, that `--jobs 1` keeps the incremental receipt, and that an interrupt
  stops the suites already started. Each names the test that guards it. The cap of 8 is marked as a default, not a
  correctness bound.
- `test/suite_catalog.py`: assumptions above `_SHIPLOOP_PACKET_SOURCES`. Every module that writes packet text belongs
  there, the hub rule would otherwise swallow the packet suites, the ledger travels with them, and the rules only add
  suites. `prompt()` gains its own: it is never a gate, and it runs light suites only.
- `test/test-groups.test.py`:
  - `test_a_hub_file_selects_a_bounded_consumer_set` asserted `len(extra) <= len(_HUB_SUITE_IDS) +
    len(PACKET_SIZE_IDS) + 2`, and the navigator sat exactly at that ceiling (15 of 15). It is replaced by
    `test_a_hub_file_selects_its_fixed_set_however_many_suites_reference_it`, which adds twice
    `HUB_REFERENCE_LIMIT` fake consumers and requires the selection not to change. A mutant with the hub rule off fails
    it for the navigator and the store.
  - The barrier and interrupt tests wait up to `PATIENCE_SECONDS` (60 s), against 10 s, 20 s and 5 s before. On
    success each returns as soon as its condition holds, so the headroom costs nothing. The interrupt test's fake suites
    now sleep 600 s, so a runner that waited for them still fails, and a failing run kills its leftover fake suites. A
    mutant runner without the interrupt cleanup fails it ("still waiting for its suites after 60 s") and leaves no fake
    suite behind. The serial control keeps its 0.5 s wait, because one job never overlaps and a longer wait would only
    slow it.
  - The prompt-group test drops a count of 5. Its ids are pinned by name, and `validate_catalog()` refuses an unknown
    one.

**Not changed:** the counts pinned on purpose by other rounds and authors. These are the catalog audit counts in
`test_audited_catalog_counts_and_fixed_commands`, the quick baseline's `assertLess(len(baseline), 17)`, and the
1,500-character bound behind F6. They are left alone so this round undoes nothing it did not write. The F6 task card
now asks for a path-independent measurement with headroom, and asks the owner before any number changes. Update
2026-10-28: the 1,500-character test is removed and its shape is asserted instead (see F6).

**Findings**

- F18 (firm): round 1's assumptions are now stated where the code is, each beside the test that guards it. Proof:
  the comments above `MAX_DEFAULT_JOBS` and `_SHIPLOOP_PACKET_SOURCES`, and `test/test-groups.test.py` passing.
- F19 (firm): the hub check no longer depends on a count. Adding consumers leaves a hub's selection unchanged, and
  turning the hub rule off fails it. Proof: the mutant above.

## Round 4 (2026-10-29): a suite's bytecode broke a sibling suite's `tar` on CI

**Question.** Why did CI's quick job fail on `1961f4c5` (run 40813164137) when every local run was green?

**What CI showed.** `sync-plugin-views` and `native-marketplace-adapters` failed within 2 ms of each other (03:51:21Z),
each with `tar: ./test: file changed as we read it`. Both copy the checkout with `tar -cf - .` into a fixture. The
rerun failed the same way. The full tier had passed on the release before it (`3d7b83a3`).

**Cause (inferred; the runner was not observed).** At `--jobs 4` the first four suites in catalog order start
together: `test-groups`, `ci-policy`, `sync-plugin-views` and `native-marketplace-adapters`. The first two are Python
suites that import `test/ci_policy.py`, `suite_catalog.py` and `run_suites.py`, so on a fresh runner checkout they
create `test/__pycache__` while the other two are copying. GNU tar exits 1 when a directory changes during the copy.
The runner's own `python3 -B` does not reach the processes it starts, so `run_process` gave its children an
environment with bytecode writing on.

**Why no local run showed it.** Two reasons, both found today:
- macOS's bsdtar (3.5.3) makes no such check. GNU tar is not installed here and was not downloaded.
- The owner's shell exports `PYTHONDONTWRITEBYTECODE=1`, so nothing here wrote bytecode in the first place.

**Change.** `run_suites.run_process` sets `PYTHONDONTWRITEBYTECODE=1` for every suite, beside `SHIPLOOP_PROGRESS=off`
and the private `XDG_STATE_HOME`. The tar sites are left alone: the fixtures already exclude `__pycache__`, and the
`test/` directory itself changing was the only trigger found.

**Evidence.**
- `test/test-groups.test.py` `ChildBytecodeTest`: a child that imports a sibling module leaves no `__pycache__`. The
  test removes the variable from the parent environment, so the runner has to supply it. Fail-first: before the change
  the child left one `__pycache__`; after, none. `test-groups`: 51 OK.
- Through the runner, with the variable removed from the parent environment as on CI, running
  `test/ci-policy.test.py`: origin/main leaves `test/__pycache__` (0 dirs before, 1 after); with the change, 0 after.
- ruff on `test/run_suites.py` and `test/test-groups.test.py`: 4 and 12 findings, the same counts as origin/main.

**Findings**
- F20 (interim): the cause is inferred and GNU tar was not run here. The fix is proven at the runner: a child suite no
  longer creates bytecode in the tree.
- CI on the fix commit `7f21c0e7` (2026-10-29): the push run (40889687968) and a full-tier dispatch (40889741622, all
  five groups) are green. The quick job ran only `test-groups` and `ci-policy`, so it did not repeat the failing
  condition. The full tier's core group (53 suites, `--jobs 4`, catalog order) ran `sync-plugin-views` and
  `native-marketplace-adapters` and both passed on the Linux runner. That is the nearest repeat so far, but the log
  prints each suite's output at the end, so it does not show whether they started beside the Python suites. F20
  stays interim until a quick run that selects both suites, as the 1.21.0 release's hook changes will, is also green.

## Round 5 (2026-11-14): two intermittent failures in one CI shard, the fourth fixture to race git's auto-maintenance lock and a port collision

**Question.** Why did `full / shiploop-2` fail on the release commit `9710190f` (run 43669277848, job 132675527691) when the
same shard had passed on the six release commits before it?

**What CI showed.** One failure in `shiploop-e2e-grok-chat-full-quality` (42 tests in 6.422 s, so the runner was not slow):
`QualityGateTest.test_public_prepare_empty_commit_then_scoped_reassessment_preserves_failure`, at the before/after inventory
assertion in `QualityGateTest.public`: `Lists differ: ['work/.git/objects/maintenance.lock'] != []`. The lock was in the
"before" inventory and absent or rewritten in the "after" one. Every other job of the run passed except `python-floor`, which
was still running when this was read. Excerpt: `docs/experiments/git-maintenance-lock-20261114/ci-failure-excerpt.txt`.

**The rerun (attempt 2, same commit and tree).** `gh run rerun 43669277848 --failed` ran the shard again (job 132681484968,
03:11:33Z to 03:26:26Z). `shiploop-e2e-grok-chat-full-quality` passed (42 tests OK in 9.570 s), so the first failure was a race and
not a regression. The shard failed again, on a different suite: `shiploop-e2e-ticket-comments` (17 tests in 81.274 s),
`CalibrationTest.test_each_defect_fails_exactly_the_check_that_reads_what_it_breaks`, variant `comments-newest-first`. That test
expects the defect to fail exactly one check and saw two: besides `basics`, the `persisted` check failed with "the candidate exited
(rc 1) before it listened on PORT=55427" and the tail of a Node `Server.listen` stack from the candidate's `server.js`. The
record cuts off the front of the stack, so the error's name is not in it. The pushed range changed nothing in `test/shiploop_e2e`
but one review file and four scenario files, and the suite's own last change is `bf68e959` (2026-10-31). Excerpt:
`docs/experiments/git-maintenance-lock-20261114/ci-attempt2-failure-excerpt.txt`.

**Cause.** The test makes a fixture commit (`--allow-empty`, "empty knowledge commit") and calls `public("--prepare-only")` on
the next line. git runs `git maintenance run --auto --quiet --detach` after a commit, and the detached process holds
`objects/maintenance.lock` for a moment; when that moment straddles the inventory's first walk, the lock is in "before" and gone
from "after". It is the same class as `595973e7` (the first, `CheckScratchFileTest`, now in `shiploop-e2e-resources`),
`9679c936` (the security fixture) and `85a7cda7` (the V7 Git fixtures). Load is not required: this run was quick.

**Why no local run showed it.** On git 2.54.0 (Apple Git-157) the lock was never seen after a commit returned (0 of 300 commits,
with or without the flag), and the failing test passed 6 of 6 alone (0.56 to 0.76 s). The launch itself is measurable: Trace2
recorded `git maintenance run --auto --quiet --detach` for 40 of 40 fixture-shaped commits without the flag and 0 of 40 with it.
`85a7cda7` saw the same on the same git. The runner's git version was not read in this run; `595973e7` named 2.55 for its race.

**Change.** `-c maintenance.auto=false` on both fixture commits of that suite (`QualityGateTest.setUp` and the test's own
commit), command-local, nothing persisted, the inventory untouched. Skipping the lock in `public()`'s inventory was not chosen:
that inventory exists to catch the code under test writing under the product, `.git` included (the choice `85a7cda7` made too).

**Evidence** (`docs/experiments/git-maintenance-lock-20261114/`, `results.txt`).
- Mechanism: the Trace2 counts above. The suite after the change: 42 tests OK in 9.2 s. ruff E9,F,B: six B023 findings at
  unrelated loop closures, the same six before and after.
- Base rate: the test was added by `17f5e10f` (2026-11-12), and `full / shiploop-2` passed on the six release commits
  `7ceaecf4` to `48bc8d63` (runs 43366639890, 43376061606, 43447175323, 43464757577, 43604725247, 43608872092) and failed on
  this seventh.

**Findings**
- F21 (interim): git's detached auto-maintenance after a fixture commit is the cause, and the flag removes the launch (40 of 40
  to 0 of 40). The fix has not been seen to prevent a CI failure. The race is intermittent (1 of 7 release runs of this shard, and
  the rerun of the same commit and tree passed this suite),
  ~~the push's own run is the quick tier (it does not select this suite)~~ [superseded 2026-11-14, the same day: for a push,
  `test/ci_policy.py` `select()` runs the suites matching `base..HEAD`, so the quick job of the fix push (run 43671490703, job
  132682382137) did run this suite once, 42 tests OK in 9.223 s; the claim came from reading the quick tier as a fixed baseline
  only, and the commit message of `111e2a27` carries the same wrong sentence], and one green run, quick or full, is weak
  evidence for a shard that passes six times in seven without the fix. It stays interim until the next full tiers (the next
  release, and the weekly Monday run) are green.
- F22 (exploratory, updated 2026-11-15): four fixtures in 19 days have hit this class (`595973e7` on 2026-10-26, `9679c936` and `85a7cda7` on
  2026-11-08, this one). 110 of the 114 test files containing the literal `"commit"` never mention `maintenance.auto` or
  `gc.auto` (a grep count, not an audit of which really run a git commit). Only fixtures that inventory or copy the tree right
  after a commit have failed, so the rest are left alone. ~~A runner-level setting (`GIT_CONFIG_COUNT=1`,
  `GIT_CONFIG_KEY_0=maintenance.auto`, `GIT_CONFIG_VALUE_0=false` in `run_suites.run_process` and the CI jobs) would end the
  class in one place (Round 4 set `PYTHONDONTWRITEBYTECODE=1` there for a similar class), but it changes the environment of every
  suite, is not run through the full tier before CI, and does not protect a standalone `python3 test/<file>`. That sets
  direction, so it is the owner's call and is not made here.~~ [superseded 2026-11-15: the owner chose a runner-level setting,
  and the mechanism written here cannot be used; see the update.]
  - Update 2026-11-15. The owner answered "Yes, at the runner" to "Turn git's auto-maintenance off at the test runner for every
    suite?". The mechanism F22 named cannot be used, and I wrote it without reading `test/run_suites.py`: `run_process` removes
    `GIT_CONFIG_COUNT` and the first three KEY/VALUE pairs from every suite's environment on purpose (`_GIT_CONTEXT_OVERRIDES`,
    commit `78594ebb`, 2026-11-04: a suite's Git configuration comes from its fixture, never from the shell that started it),
    because ask-agent's workspace guard refuses them ("prepare refuses Git context environment overrides"), and ShipLoop's Git
    helpers name them as Git context overrides too. Measured (`envroute_probe.py`, `results.txt`): with the three variables
    reaching the suites through `run_process`, the three suites that commit protected fail 3 of 3 (`ask-agent-parallel`: 224
    tests, failures=2 and errors=18; `agent-harness-audit` and `install-arbitrary-skill`: the refusal above), against 0 of 3 with
    the strip (233 tests OK, OK, OK).
  - Done instead: a CI step, `git config --global maintenance.auto false`, in the `checks` job before the suites run
    (`.github/workflows/ci.yml`). It is a setting in the machine's own `~/.gitconfig` and not an environment variable, so neither
    the strip nor the guards see it. Through `run_process`, over 40 fixture commits on a fresh HOME: 40 detached maintenance
    launches without it and 0 with it (`globalconfigprobe.py`). `ci-policy`
    `test_checks_job_turns_git_background_maintenance_off_before_it_runs_the_suites` pins the step before the suites and forbids
    `GIT_CONFIG*` in the workflow's code; it fails on the old workflow and on 4 of 4 mutants (step removed, moved after the
    suites, written as `GIT_CONFIG_*` variables, written twice). `test-groups` `CIGitMaintenanceTest` runs the step's own
    command under a fresh HOME and has a child that `run_process` starts make two fixture commits: it fails on the old workflow
    and on 5 of 5 wrong forms (key misspelled, `true`, `--local`, `--system`, `gc.auto 0` alone, which does not stop the launch)
    and accepts the equivalent spelling of the boolean.
  - Scope, stated plainly: CI machines only. A local `run-all.sh` is unchanged (this macOS git 2.54.0 never showed the lock, 0 of
    300 commits, and no local failure of this kind is on record); a suite that gives itself another HOME does not read the step
    and keeps its own flag; a standalone `python3 test/<file>` on a machine without the setting is unprotected. The per-fixture
    flags stay (removing them would change no outcome). Nothing here has yet been seen to prevent a CI failure; F21's reasoning
    applies, and the next full tiers are the evidence.
  - CI on the push, 2026-11-15 (`65a85d43`): the quick run (43725596376, quick job 132846804879) passed. The runner's git is
    2.56.1 (the checkout step's log), the new step ran, and `test-groups` (65 tests) and `ci-policy` (14 tests) passed there, so
    both halves of the route test held on the runner's own git: a fixture commit starts the detached launch without the step and
    does not with it. The full-tier dispatch on main (run 43725606385, 14.5 minutes) passed all ten jobs, so no suite broke under
    the setting. That is one pass, and `full / shiploop-2`, which failed twice on the release run, passed with both the fixture
    flags (`111e2a27`) and the step in place, so it cannot say which of them would have prevented a failure. F22 stays interim
    until the next release's full tier and the Monday run.
- F23 (updated 2026-11-15: the cause is firm and the rate bounded, see Round 6; mended in ~~the two ticket suites' tests~~ [superseded 2026-11-15,
  later the same day: the tests of the five calibration suites that grade variants through serve.py, see the follow-up in Round 6], ~~`checks/serve.py`
  left to the owner~~ [superseded later the same day: the owner answered "Yes, add retry", and `checks/serve.py` chooses the port again, see the last
  update of Round 6]): a second, independent intermittent failure in the same shard, `shiploop-e2e-ticket-comments` in attempt 2: a
  candidate exited before it listened on the port the harness had chosen. `checks/serve.py` picks the port with `free_port()`
  (bind to port 0, read the number, close) and starts the candidate with `PORT=<it>`, so another process can take that port in
  between, and the shard runs several server-starting suites at once (`--jobs 4`). ~~That is a reading, not an observation: the
  record does not name the listen error, and no rate was measured.~~ [superseded 2026-11-15: the error is `EADDRINUSE`, reproduced
  with the real `serve.py` on Linux and macOS, and the rate is bounded; the record did not name it because `tail()` keeps the last 600
  characters of the candidate's stderr and the calibration test printed the first 300 of the check's output, so the error line fell off the
  front and `code: 'EADDRINUSE'` off the end.] The shard passed on the six release commits before this one.
  It is a related class to the one `26728edd` and `8c5b4d4e` measured and fixed for the `brownfield-tickets` calibration suite
  (another project's server answering on the same port number, mended by grading again until a grade agrees), not the same
  mechanism; `8c5b4d4e` names `ticket-comments` and `ticket-sla` as not examined and leaves the live scoring check to the owner.
  ~~Not fixed here: a retry in `checks/serve.py` would also reach live deliveries, which is the owner's call as in `8c5b4d4e`, and
  one failure is not a rate.~~ [superseded 2026-11-15: the rate is now measured (about one early exit in 181 CI executions of this
  suite, 0.12% of serve.py runs on this Mac), and the calibration suites' tests are mended; a retry in `checks/serve.py` is still the
  owner's call, as in `8c5b4d4e`, and is put to them in Round 6.] [superseded later the same day: the owner said yes, and it is made;
  Round 6's update has what it does and what it was measured to do.]

## Round 6 (2026-11-15): the ticket-comments early exit measured, and the mend in the tests (F23, F24)

**Question.** Round 5 left F23 as a reading: a candidate "exited (rc 1) before it listened on PORT=55427", its error cut off, no rate. What
is the error, how often does it happen, do `shiploop-e2e-ticket-sla` and the other suites that start servers through `checks/serve.py` share
it, and what is the narrowest mend? `8c5b4d4e` left a retry in `checks/serve.py` or in live scoring to the owner, and allowed a mend confined to
the calibration suites' tests.

**What was run** (`docs/experiments/serve-port-race-20261115/`; its README has the commands and the files).
- The CI history: all 941 job logs of the 476 `ci.yml` runs since 2026-10-31 (`ci_history.py`, read-only).
- The real `serve.py` against a port another socket holds, seven kinds of holder, on Linux and on macOS (`pinned_port_demo.py`); which port
  numbers the kernel hands out (`port_pool.py`).
- The real `serve.py` (imported, so `free_port()`, the Popen and `wait_for_candidate()` are the repository's) called 33,000 times on Linux
  (a container: kernel 7.2.12, Node 26.12.1, 4 CPUs, no network, lsof replaced by a shim) and 18,000 times on this Mac, from 2 to 16 callers at
  once, with and without neighbours that bind ports (`serve_race_probe.py`, `run_matrix.sh`).
- One unmodified run of each suite that goes through serve.py, with a tap that counts its serve.py runs (`tap/`, `run_tap.sh`).

**Results.**
- *The record.* The visible text starts inside the first stack frame of a Node `listen` failure. `tail()` keeps the last 600 characters of the
  collapsed stderr and the test printed `output[:300]`, so `Error: listen EADDRINUSE: address already in use :::55427` fell off the front and
  `code: 'EADDRINUSE'` off the end. The runner was Ubuntu 26.04 with Node `v27.0.0-alpha.0.1.0` (first used by CI on 2026-11-12), whose `net` has a
  `callSetupListenHandle` frame that Node 26.12.1 has not, so the stack cannot be compared line for line.
- *The error.* On Linux every kind of socket on the port (a Node or Python listener on any address, a bound socket, an established
  connection's local port) makes the candidate exit rc 1 with `EADDRINUSE`. serve.py then says "answered by pid H, not by the candidate"
  when the holder is still a listener at its first lsof look, and exactly the CI line, "exited (rc 1) before it listened on PORT=N: Error: listen
  EADDRINUSE", when the holder is not a listener or has gone. So the CI holder was not a listener when serve.py looked. It was reproduced
  without a synthetic neighbour: 16 callers at once gave 1 early exit (`EADDRINUSE`) and 6 foreign-listener lines in 18,000 calls (0.039%,
  0.016 to 0.080), and the three the probe recorded were each another live candidate of the probe: two callers had been handed one number.
- *Where the number comes from.* On Linux `free_port()`'s port is always odd and drawn over all of 32768 to 60999 (14,116 numbers), a Node
  `listen(0)` is always odd and from the lower half (7,058), a `connect()` source port is always even; the distinct counts in 2,000 draws
  (1,868 and 1,733) are what uniform draws from those pools give. A candidate is lost when another socket takes its number in the window
  between the release and the candidate's bind (0.13 to 0.2 s at the median) and still holds it then: about the sockets holding a number at that
  moment over 14,116. Five thousand binds a second held 30 ms (about 165 held) gave 11 early exits in 2,000 calls (0.55%, 0.28 to 0.98;
  1.2% predicted); `node --test` of the base fixture in 4 and in 16 loops gave no early exit in 2,000 calls (one foreign-listener line).
- *The rate on CI.* One early exit in 181 executions of this suite (85 full-tier), 180 OK; none in 84 of `ticket-sla`. The tap counted 54
  serve.py runs in one execution of `ticket-comments`, 82 of `ticket-sla`, 184 of `user-directory`, 39 of `user-chain`, 4 of `brownfield`, 13 of
  `brownfield-tickets`: about 37,900 runs in the history for one early exit (0.0026%, 0.0001 to 0.015), which mechanism (A) alone explains.
  The one failure came on the newer Node (1 of 22 executions on it, 0 of 159 before; a chance of 12 percent that the one failure falls among
  those 22 by luck, so an effect of the Node version is neither shown nor excluded).
- *A second mechanism, on macOS.* 21 early exits in 18,000 calls (0.12%, 0.07 to 0.18), all `EADDRINUSE`, 1 of them in a run of two callers,
  on twelve port numbers that recur from run to run. `free_port()` binds IPv4 loopback and a Node candidate binds the IPv6 wildcard, so a number held
  by an IPv6 socket, or by a connection whose local address is not loopback, is handed out although the candidate cannot bind it. Today eight of the
  twelve are long-lived IPv6 connections (remote port 443 or 80), one is an IPv6 wildcard listener, one an IPv4 connection to port 5223 (`bad_ports.py`,
  `macos-bad-ports.txt`; addresses not kept). It needs no concurrency, and on Linux it is unlikely (a connection's source port is even, `free_port()`'s is odd).
- *The suites.* All five calibration suites that grade variants through serve.py do it once: `ticket-comments`, `ticket-sla`, `user-directory`
  (`CalibrationBase.setUpClass`), `user-chain` and `brownfield` (`CaseChecksTest.checks`); `brownfield-tickets` grades again (`26728edd`); every
  `ChainRunTest` grades a failed check once more and the hidden acceptance goes through `quality.serve_on_free_port` (`d9a92f05`). `user-directory` has
  the most serve.py runs. The other family failure in these suites, `user-directory`'s on 2026-11-05 (run 42133217612, a hidden check answered by another
  server), is the wrong-answer face of the same cause and was mended by `f1399b5b`'s ownership check; `brownfield-tickets`' of 2026-11-01 was a
  `FileExistsError`, not a port. [2026-11-15, later the same day: "do it once" holds no longer for `user-directory`, `user-chain` and `brownfield`; see the follow-up below.]

**Change** (`test/shiploop-e2e-ticket-comments.test.py`, `test/shiploop-e2e-ticket-sla.test.py`). `CalibrationTest.setUpClass` grades each variant's own
checks again, alone, until the failed set is the one its defect declares, at most 3 more times, and the last grade stands (`settle`, `own_checks`: the rule of
`26728edd` and `8c5b4d4e`, in the tests only); a defect read by the wrong check disagrees every time and fails after 4 grades. The failure text now carries the
check's whole output (run_checks keeps its last 2000 characters). Tests: `SettleTest` (3, no node) and `RegradeRouteTest` (the real serve.py, a held port, the first
grade fails and the second passes); with the rule off (`REGRADES = 0`) 3 of the 4 fail in each suite. The two suites pass whole (21 and 27 tests).

**Decision** (routine, AGENTS.md "Decisions": a choice between equivalent fixes, and the owner's carve-out for live scoring). The regrade in the tests of the
suite that failed and of its sibling, which has more serve.py runs and the same shape. Not done, with the reason:
- ~~A retry or a different `free_port()` in `checks/serve.py`: it scores live deliveries and changes the oracle digest (`boundary.oracle_files` hashes `checks/`), so it is the
  owner's call (`8c5b4d4e`). The question is in the report that goes with this commit; the rule it would copy is `quality.serve_on_free_port`'s (a server that exits on `EADDRINUSE` naming its own port is
  started again on another, at most three tries, `d9a92f05`).~~ [superseded 2026-11-15, later the same day: the question was put to the owner, who answered "Yes, add retry"; made, in the update below.]
- A shared helper in `test/shiploop_e2e/`: it would change the evaluator digest (`boundary.evaluator_files` hashes the `*.py` at the top of that folder).
- ~~The other three suites (`user-directory`, `user-chain`, `brownfield`): the same change applies at the places named above; not made because the task named the ticket
  pair and no failure with this signature is on record for them. `user-directory`'s 184 runs make it the most exposed, about 3.4 times `ticket-comments`.~~ [superseded
  2026-11-15, later the same day: made in the follow-up below; the only reason for leaving them was that the first task named the ticket pair, and no failure with this
  signature is on record for them still.]

**Follow-up (2026-11-15, later the same day): the regrade in the other three suites** (`test/shiploop-e2e-user-directory.test.py`,
`test/shiploop-e2e-user-chain.test.py`, `test/shiploop-e2e-brownfield.test.py`). The Decision above left them as the first follow-up; a second session, asked
to apply the same test-only regrade to them, did. Nothing under `test/shiploop_e2e/` moved (the evaluator and oracle digests are the same) and `checks/serve.py`
is untouched.
- *Change.* Each suite carries the ticket pair's `REGRADES = 3`, `settle` and `own_checks` (copied, as the pair's own are). `user-directory`'s
  `CalibrationBase.setUpClass` (41 variants; 123 of the suite's 184 serve.py runs are its variants' own checks, 39 + 48 + 36 by link) and `user-chain`'s
  `CalibrationTest.setUpClass` (22 variants; 29 serve.py runs, and for each variant a `node --test` of the delivery's own suite as the first own check) grade
  a variant's own checks again, alone, until the failed positions are `EXPECTED[...][variant][0]`, at most 3 more times, the last grade standing. `brownfield`'s
  `CaseChecksTest.expect` (3 variants; two of the case's three checks run the base's own `node --test`) grades again until the three verdicts are the declared
  ones (`[False, True, False]` for the base, `[True, True, True]` for the reference and the alternative: the shape of `agreed()` in brownfield-tickets, `8c5b4d4e`).
  The failure text of each carries the checks' whole output (`run_checks` keeps the last 2000 characters) where it carried the first 300 or 400.
- *Tests.* Each suite gets `SettleTest` (3, no node: the pair's, with the sets or flags of that suite in them) and `RegradeRouteTest` (the real serve.py: a socket on
  every address holds a port, the first grade's checks are handed it, the second grade passes; a `user-roles`, `user-teams` and `user-listing` reference
  delivery). The first grade fails `[False, False, False]` in `user-directory` (all three own checks start a candidate through serve.py), `[True, False, False]` in
  `user-chain` (its first own check is the delivery's own `node --test`) and `[True, True, False]` in `brownfield` (only its third check does). Fail first: with
  `REGRADES = 0` 3 of the 4 new tests fail in each suite (the test that a grade that agrees is not graded again passes by design); restored to 3, all four pass (3.9 s,
  5.0 s and 8.9 s at a load average of 40).
- *The wiring.* `docs/experiments/serve-port-race-20261115/wiring_probe.py` runs a suite's calibration classes (`user-directory`'s three, `user-chain`'s and
  `brownfield`'s `CaseChecksTest`) with the first grade of every delivery handed a held port, so the suite's own `setUpClass` or `expect` has to regrade. As shipped the
  classes pass: `user-directory` 16 tests (41 deliveries, 37 graded twice and 4 once: the four whose declared own set is all three checks, which the held port fails too),
  `user-chain` 4 tests (22 deliveries, 11 twice and 11 once: those whose declared set holds the checks that go through serve.py), `brownfield` 2 tests (3 deliveries, 2 twice and the
  base once); none was graded more than twice. With `--regrades 0` the same classes fail (43, 17 and 2 failures, subtests included, every delivery graded once). So each suite's own
  path goes through the regrade, and a first grade that disagrees is what makes it grade again (`wiring-results.txt`).
- *Whole suites* (macOS, the three at once at nice 10 beside `test-groups`, load average 33 to 43 from other work): `user-directory` 45 tests OK in 273.6 s (41 before
  plus 4; one skip, the abstract base of the per-link calibrations), `user-chain` 23 OK in 103.9 s (19 plus 4), `brownfield` 31 OK in 84.8 s (27 plus 4);
  `test-groups` 65 tests OK in 40.4 s. `ruff --select E9,F,B`: the same findings before and after (`user-directory` one B905 and `user-chain` a B905 and an F841, all at lines
  this change did not write; `brownfield` none). `git diff --check` clean.
- *What stays.* (1) ~~`checks/serve.py` and the live scoring checks: the owner's open question (F23).~~ [superseded later the same day: the owner said yes to the retry in
  `checks/serve.py`; see the last update of Round 6.] (2) The variants' hidden acceptance (`user-directory`, `user-chain`,
  `brownfield`'s `CalibrationTest`) is graded once: it goes through `quality.serve_on_free_port` (a server whose port was taken is started again on another, three starts)
  and the listener-ownership check of `f1399b5b`, which is what mended the one failure of these suites on record that is of this family (`user-directory`, 2026-11-05); in
  the CI history of 2026-10-31 to 2026-11-15 `user-directory` failed 1 of 68 executions (that one), `user-chain` 0 of 130 and `brownfield` 0 of 214. (3) `brownfield`'s
  `ThroughMainTest` (the fake-host run's three flags, graded once: its one serve.py run is the base's HTTP check, which fails by design whatever answers, and its two `node --test`
  checks are the wobble `8c5b4d4e` mended for brownfield-tickets, not seen for `brownfield`) and every `ChainRunTest` (a failed check is graded once more, as before).
  (4) No counter of regrades, as in the pair: a rate that creeps up would not show, and a check that wobbles below four grades in a row is hidden too. (5) The rescue of a
  natural collision has not been seen in these suites (with no counter it could not be): what is shown is the route with a held port.

**Findings**
- F23 (above, updated): firm for the cause (`EADDRINUSE` from a port number another socket took between `free_port()` and the candidate's bind), measured for the
  rate on Linux and macOS, interim for the CI rate (one event). Unknown: which socket held 55427 on the runner.
- F24 (firm for the inventory, exploratory for the Mac's rate): `free_port()` asks the IPv4 allocator, a Node candidate binds the IPv6 wildcard, and on macOS
  twelve port numbers that other programs held through IPv6 sockets were handed out again and again: 0.12% of serve.py runs on this Mac on this day against 0.0026% on CI. A live
  run of a link of the ticket or user chains makes 3 to 12 serve.py runs (its regression and own checks), so about 0.4 to 1.4% of live runs at this Mac's rate, if the rate holds
  for the way live runs call serve.py (one at a time). The number will change with what other programs hold. Update 2026-11-15, later the same day: the calibration
  exposure is closed in the tests of all five suites that grade variants through serve.py (the ticket pair, then `user-directory`, `user-chain` and `brownfield`; see the
  follow-up above); ~~the live exposure in the line above is unchanged, and the live scoring through serve.py stays the owner's question.~~ [superseded later the same
  day: the owner said yes to a retry in serve.py, so the live exposure is closed too; see the last update of Round 6.] [2026-11-15, evening: "closed too" held for the checks that
  run through serve.py; the `ticket-due-times` probe chose its own ports and was the one live check left with the exposure. It has the rule now; see the last update.]
- F25 (firm for the wiring with a held port, none for a natural collision): the three suites of the follow-up regrade through their own grading paths. With the first grade of
  every delivery handed a held port (`docs/experiments/serve-port-race-20261115/wiring_probe.py`, `wiring-results.txt`), `user-directory`'s three calibration classes (41
  deliveries), `user-chain`'s (22) and `brownfield`'s `CaseChecksTest` (3) pass with the regrade as shipped, and fail with it off (`--regrades 0`: 43, 17 and 2 failures, subtests
  included). Not shown: the rescue of a natural collision (there is no counter), and Linux (the route tests and the probe were run on macOS only).

**Update (2026-11-15, later still): the retry in `checks/serve.py`.** The owner answered "Yes, add retry" to the question that ended the report of the commit above.
It is made in this commit.
- *What.* `checks/serve.py` starts the candidate again on another free port, at most 3 starts in all (`TRIES`, as `quality.LISTEN_TRIES`), when another process holds
  the port it was handed: the candidate exits with `EADDRINUSE` naming its own port (`port_taken`, the rule of `quality.port_taken`), or a process outside the
  candidate's group listens on it (`candidate_problem` says `taken`). Not started again: a candidate that exits for another reason, one that names another port, one
  that never listens within 10 s, a table lsof cannot read, and a port pinned with `E2E_SERVE_PORT` (the regression's). The ownership check is unchanged and every
  start must pass it; a retried check prints one line to stderr, and after the third start the failure names the ports. `wait_for_candidate` keeps its contract
  for `due_times_probe.py`. [2026-11-15, evening: `due_times_probe.py` no longer calls it; its `Server` asks `candidate_problem` itself, see the last update. `wait_for_candidate`
  keeps its contract and the resources suite's test of it, and has no other caller.]
- *One more trigger than the question named.* The question said "exits with `EADDRINUSE` naming its own `PORT`"; a foreign listener on the port is retried too, because it
  is the other face of the same cause: of the 7 collisions measured at 16 callers on Linux, 6 were that signature, and a retry on `EADDRINUSE` alone would have cured one.
  `quality.serve_on_free_port` gets both, because its wait does not give up on a foreign listener before the candidate's own bind fails. It is stated here and in the
  commit so that it can be narrowed if the owner wants the narrower rule.
- *Measured, the same probe, the retry in place* (`matrix-linux-retry.jsonl`, `matrix-macos-retry.jsonl`). Linux, 16 callers, 12,000 calls: 5 chosen again, 0 failed
  (the same row without the retry: 1 early exit and 3 foreign-listener lines in 12,000, and 3 in 6,000 before). 5,000 binds a second, 2,000 calls: 15 chosen again, 0
  failed (11 early exits without). macOS, 8 callers, 6,000 calls: 7 chosen again (0.12%, the rate without it was 21 in 18,000), none failed on a port. Eight calls of
  that run ended for another reason: all eight candidates had logged that they listen and exited 0 within 0.6 s of each other, so something outside the probe sent
  them SIGTERM, and serve.py rightly did not start them again.
- *Tests* (`test/shiploop-e2e-resources.test.py`). `CandidateProblemTest` (7, no node) pins which refusals are a taken port. `ServeRetryTest` (7) runs the real
  serve.py: started again on another port; three starts at most and the failure names the ports; an `EADDRINUSE` naming another port, another exit code and a pinned
  port are started once; a real collision (a socket on every address holds the number `free_port()` hands out) passes on the second start; the candidate of a given-up
  start is ended before the next. Against the old serve.py 11 of the 14 fail (the three "started once" tests pass by design); the 8 serve.py tests that were there still pass.
- *Not done.* ~~`due_times_probe.py` (the `ticket-due-times` case) starts its own servers with `serve.free_port()` and keeps the same exposure; the retry does not reach
  it.~~ [superseded 2026-11-15, evening: `Server` in `due_times_probe.py` has the same rule; see the last update.] A candidate that stays alive beside a foreign listener on its
  port (a macOS dual bind) is ended and started again; one that always starts a detached listener of its own on `PORT` is started three times and fails as before, and may leave
  those listeners to the run's reaper.
- *Digests.* `checks/` is hashed into the oracle digest, so every case's oracle digest changes at this commit and no comparison that needs the old one spans it (as
  `d9a92f05` said of the evaluator digest). SPEC's "Concurrency must not change a verdict" and the README's `checks` paragraph carry the amendment.


**Update (2026-11-15, evening): the same rule in `due_times_probe.py`.** The "Not done" of the update above, made on the task the session that wrote it handed on (its brief named
`serve.TRIES`, `serve.candidate_problem`, `serve.free_port` and `serve.listeners.end_group` as what to use). Nothing under `skills/`, `agents/` or the catalogs moves, and neither does `checks/serve.py`.
- *What.* `Server.__init__` (`test/shiploop_e2e/checks/due_times_probe.py`: the one place the probe starts a service, so all of `migrate`, `restart`, `switch`, `rollback`, `off` and `cli`, and the base's 1.4.0 starts of
  `rollback` and `off`) loops at most `serve.TRIES` starts: a fresh `serve.free_port()`, `node src/server.js` with that `PORT`, then `serve.candidate_problem(proc, port, stderr)`. `None` keeps the start. Otherwise the start's
  group is ended (`serve.listeners.end_group`) and reaped, and the next start comes only when the refusal's `taken` is true and this was not the last start, after one stderr line (`due_times_probe.py: another process took PORT=N;
  starting the <label> server again on another port (start K of 3)`). Every other refusal, and the last start, print one `FAIL:` line through `serve.fail` (what `wait_for_candidate` does with a refusal), then `(the <label> server did not
  start)`, and exit 1, as before. The last start's line also names the ports tried, as serve.py's does: the one addition to "the old behaviour", so that a failure after three starts is told from a single refused start; it is one line to
  drop. `main()` and the six modes are untouched.
- *Where the tests are.* `git grep due_times_probe test` finds the probe only through `cases.json`: no suite calibrates it (the 56-cell calibration of 2026-11-14 is `docs/experiments/planning-points-probe-20261114/calibrate.py`, run before any live run; its first run found the reference breaking `test/query.test.js`, so it ran more than once). The suite that covers it is `shiploop-e2e-resources`: `test_case_checks_name_existing_helper_scripts_and_subcommands` ties each `"$E2E_CHECKS/due_times_probe.py" MODE` of `cases.json` to the file and its `"MODE":` keys,
  and serve.py's own tests are there, so `DueTimesProbeServerTest` (8 tests, a real `node` service per start) is too: a service that exits `EADDRINUSE` naming its port is started again on another, and `Server` keeps the second
  start's port and base (it answers a request there); three starts are the most and the failure names the ports; a refusal that is not a taken port ends the probe on whichever start it comes (taken, then another exit code: two starts);
  a real collision (a socket on every address holds the number `free_port()` hands out) passes on the second start; the service of a start that is given up is ended before the next is started. Three controls pass by design: a service that
  listens is started once with nothing on stderr; `EADDRINUSE` naming another port and another exit code are started once.
- *Fail first.* Against the unchanged probe 5 of the 8 fail (3 errors, 2 failures, each because it gave up after one start) and the 3 controls pass; with the change 8 OK (2.7 s, and 2.9 s for the 22 with serve.py's two classes in the Linux container).
- *Measured* (`docs/experiments/serve-port-race-20261115/due_times_held_port.py`, `due-times-held-port.jsonl`; README, evening follow-up). The probe's own modes against the case's reference delivery and its base, the old probe
  (`b578deaa`, the tip of `main` before this change, serve.py's retry beside it) and the new, with the first `free_port()` of every `Server` handing out a number that a socket of the driver holds (48 runs, macOS, load average 14 to 16).
  The control passes 6 of 6 modes on the reference and exactly `rollback`, `off` and `cli` on the base (`migrate`, `restart` and `switch` fail with 11, 36 and 9 `FAIL:` lines), the same for both probes, with 15 servers and 15 starts per full pass.
  With the first start held the old probe fails all 6 modes on both deliveries (one `FAIL:` line each, "answered by pid ..., not by the candidate", and "a server did not start"), so the collision decides the verdict; the new probe gives the
  control's verdict in all 12 cells (the same `FAIL:` counts) with 15 servers, 30 starts and 15 retry lines.
- *Whole suites with the change* (macOS, the four at once at nice 10, load average 11 to 21 from other work): `test-groups` 70 tests OK in 42.4 s, `shiploop-e2e-resources` 133 OK in 173.3 s (125 before plus the 8),
  `shiploop-e2e-ticket-comments` 21 OK in 83.0 s, `shiploop-e2e-ticket-sla` 27 OK in 370.9 s. On Linux (the container of the study: kernel 7.2.12, Node 26.12.1, Python 3.14.9, `lsof_shim.py`) the new class, `ServeRetryTest` and
  `CandidateProblemTest` pass together: 22 tests in 2.9 s. `ruff --select E9,F,B`: the probe has the same two findings before and after; the resources test has no finding but F821 (685 before, 709 now: the names its support module
  injects, which the new lines use as the old ones do); the driver is clean.
- *Digests.* `checks/` is hashed into the oracle digest, so every case's oracle digest changes at this commit and no comparison that needs the old one spans it, as in the update above (`boundary.fingerprint`: oracle `0eebb016daac`
  before `a669c801`, `049862eda389` on `b578deaa`, `c70aea9cceda` with this change; evaluator `48f9a88313e3` before and after it). SPEC's "Concurrency must not change a verdict" and the README's `checks` paragraph state the rule of "a case's HTTP
  check" and now hold for this probe too; they need no sentence.
- *Not done, and unknown.* The probe's own natural collision rate (no churn neighbours here): its start is serve.py's sequence, so a full pass of 15 starts would hit about 0.04% at CI's rate and about 1.8% at this Mac's (0.12% a start) if the
  per-start rates hold for it. A retry that is itself taken; the driver on Linux (one run per cell, macOS only; the tests ran there, above, and CI's quick tier on the push runs the resources suite on its Linux runner). The held socket is a listener, so the 12 failures were the
  foreign-listener face; the early-exit face is pinned by `CandidateProblemTest` and by `DueTimesProbeServerTest.test_a_service_that_exits_eaddrinuse_naming_its_port_is_started_again_on_another_port`. A given-up start writes nothing the base's data file would keep (the base saves after a change and at SIGTERM, by write and rename), but a
  delivery that saved at open would leave its second start a file it had already migrated, which is the `restart` case. The two `ruff --select E9,F,B` findings the probe had before (F401 `time` unused, F541 an f-string without a placeholder)
  are left. A retried start leaves one stderr line, kept in the check's output (`run.run_checks` stores the last 2000 characters of stdout plus stderr), and no trace in a verdict.
- F26 (firm for the route with a held port, none for a natural collision of the probe's own start): the `ticket-due-times` probe's servers have serve.py's retry, and a taken port no longer decides its verdict (the README's evening follow-up has the table).

## Round 7 (2026-11-22): the "suite cleanup" line in the push check, and the repeated kill behind it (F27 to F30)

**Question.** The guarded push (`scripts/release-push.py`) runs `test/test-groups.test.py` as one of its checks. On 2026-11-22 at 07:51 that run printed
`suite cleanup: failure or uncertainty during bounded cleanup` once, after 40 dots, and passed (78 tests, 20.8 s); the push before it, eight minutes earlier, printed
nothing. `88cfb703` (2026-11-15), which wrote that line and the cleanup behind it, saw the same line at the same place (after 40 dots) and recorded its cause as
unconfirmed. The owner asked for it to be looked into. What prints it, how often, is anything left running when it prints, and can the same thing fail a real suite?

**What was run** (`docs/experiments/suite-cleanup-diagnostic-20261122/`, whose README has the commands; macOS, Darwin 27.2.0, Python 3.15.1, load average 5 to 8 from
other sessions' work, their live E2E runs on the machine for part of it).
- *The place.* Forty dots is the 41st test in run order, `SuiteGroupOwnershipTest.test_timeout_grace_interrupt_finishes_owned_group_before_escape`. The classes and
  tests were the same, in the same order, at the commit that push was made from. The dots and the line go to the same stream, so the order is exact.
- *The cleanup, step by step* (`double_kill.py`). The runner's own `_SuiteProcess._signal_group(SIGKILL)` called twice on a real group (a leader and a child, both
  ignoring SIGTERM, in their own session), a chosen time apart, with the exit probe's and `killpg`'s answers recorded each time, then the runner's own reap: 1,000
  trials back to back and 250 at each of eight requested delays from 20 microseconds to 5 ms (3,000 trials).
- *The test itself* (`run_test41.sh`). The one test run 150 times before the change and 150 times after it, counting the runs that print the line.
- *Earlier sightings* (`results/record-search.txt`). Every Claude session record on this machine (13 GB, all projects) and every Codex session record (3.1 GB)
  searched for the text a real run prints when the runner records this; the one run that has it was read, with its log, by a read-only Opus agent, and its counts
  were checked against the log.

**Results.**
- *What prints it.* `_abort_process` (the cleanup for an exception that escapes while a suite runs) sent the group SIGKILL twice within microseconds: once as the last
  step of `_terminate_process_group` (SIGTERM, a 1 s wait, SIGKILL) and once more as its own "final owned KILL attempt". When the first one reaches live processes, which
  is the case for a leader that outlives the SIGTERM wait, macOS refuses the second with `EPERM` while the group it reached is still exiting: no member can be signalled
  any more, and the leader cannot be waited for yet. `_signal_group` accepts `EPERM` as harmless only when its exit probe, taken just before the signal, said the leader
  had exited and `ps` then shows nothing but zombies in the group. In that window the probe still says "not exited", so it records `signal 9: PermissionError; group
  cleanup unconfirmed`, and `_abort_process` prints the line. The 41st test is the one whose leader ignores SIGTERM and whose cleanup goes through `_abort_process`.
- *The window, measured* (`results/double-kill.txt`). Trials in which the second kill was refused while the probe still said "not exited" (the warning recorded):

  | time asked for between the two kills | warned | the rest |
  | --- | --- | --- |
  | none (back to back) | 36 of 1,000 | 964: the second kill was accepted |
  | 20 microseconds | 246 of 250 | 4 accepted |
  | 50 microseconds | 249 of 250 | 1 accepted |
  | 100 and 200 microseconds | 250 of 250 each | |
  | 500 microseconds | 24 of 250 | 226: the probe said "exited", the kill was refused, the `ps` check passed |
  | 1, 2 and 5 ms | 0 of 250 each | the same: exited, refused, checked, quiet |

  So the group stops accepting signals some tens of microseconds after the kill, and the leader becomes waitable between about half a millisecond and a millisecond
  after it. The times are the ones asked of `time.sleep`; the real gap is longer by the sleep's overshoot, which was not measured.
- *Nothing was left running.* In all 3,000 trials the reap that followed (probe "exited", `killpg` refused, `ps` check) recorded nothing more, and `ps`, taken right
  after each warned trial, showed the leader as a zombie and no other member of the group. The test asserts the same of its own two processes before any fallback, and
  passed every time.
- *How often in the test.* Before the change the line printed in 19 of 150 runs of the test (12.7%), and the test passed in 150 of 150 (`results/test41-before.txt`).
  About one push check in eight, which fits one sighting in this session's pushes of the day and one in the banks of `88cfb703`.
- *Earlier sightings.* No Claude session record but this session's own holds the runner's record as a run's output. The Codex records hold it for one run. On
  2026-11-18 a quick tier (82 suites selected, release 3.1.0) was started by a `codex exec --sandbox workspace-write` worker, so inside a sandbox in which `/bin/ps` could
  not be started (`PermissionError: [Errno 1] Operation not permitted: 'ps'`), a loopback bind was refused and keychains could not be made. All 23 suites that had
  reported when that session stopped the run carry `cleanup: signal 9: PermissionError; group cleanup unconfirmed` and `FAIL`: 18 of them after their own tests had
  passed (`shiploop-no-model-launch`: "Ran 10 tests in 8.806s", "OK", then the cleanup line and `FAIL`). The session called the environment unusable ("the sandbox
  cannot inspect or signal test processes"), and ran the tier outside it three times: 79 of 82 passed (three failures of other kinds), then 82 of 82 twice, with no
  cleanup line. Its commit `ed1b57ab` says so in one sentence and does not name the line. The diagnostic of this round's question is a run's output once more in those
  records: `88cfb703`'s own sighting, in `test/test-groups.test.py` on stock Python 3.9.6.
- *What that run shows.* On macOS the group of a suite that has ended holds only its leader, a zombie until the runner reaps it, and `killpg` answers `EPERM` for such
  a group. So every normal reap takes the route "refused, ask `ps`": all 3,000 reaps of the probe did, and were quiet. A suite's verdict on macOS therefore depends on
  `/bin/ps` starting and answering within the observer's 2 s; where it cannot start, every suite is reported failed, whatever its tests did.
- *Six processes that run left behind.* A `node --test` worker (56210, stopped this morning at the owner's word: `docs/shiploop-sdlc-structure-journal.md`, R173) and
  five Python workers that ignore SIGTERM (56247, 56264, 56352, 56737 and 56752, still there at this writing) all started on 2026-11-18 between 03:12:39 and 03:12:42
  local time, while that tier was running, each in a group whose leader is gone and in a temporary folder that has since been deleted. They match one for one the six
  workers that `BaseTestsProcessOwnershipTest` in `test/shiploop-e2e-brownfield-tickets.test.py` starts through `owned_fixture`: one under `node --test`, five in Python
  that ignore SIGTERM, one of the five keeping its pipes. What ends such a worker is `fixture_process.stop_group`, which looks at the group with `ps` before it sends
  anything (`live_members`) and raises when it cannot look. So in that sandbox they were never sent a signal. The attribution rests on the time, on where the tier had
  got to in the catalog and on the exact match; no record names that suite as running at that second. By the reading agent's account, that session's own check for
  survivors searched by the clone's path and by its own process tree, and these had neither. They were in groups of their own, not in a suite's, so the runner's record was
  not about them.
- *The change.* `_abort_process` now sends its final SIGKILL only when `_terminate_process_group` raised, which is the case its comment always named ("a failed
  TERM/wait must not prevent the final owned KILL attempt"). A termination that completed has just sent that SIGKILL. A member the first kill missed is still covered:
  the runner signals the group once more when it finds the leader exited, before it reaps it (`_internal_poll`), and `_abort_process` reaches that through
  `communicate` or its last `wait`. Nothing else in the runner moved: not `_signal_group`'s rule, not the diagnostics, not a time bound.
- *The test.* The 41st test's own `killpg` wrapper now also notes a group SIGKILL sent to the suite's group after an earlier one was delivered and while a read-only
  exit probe still says the leader has not exited, and asserts there was none. It does not assert on the warning list or on stderr: those depend on how fast the
  machine is, the repeat does not. *Fail first:* with only the test changed it failed 5 of 5 times, on the new assertion and nothing else (`results/fail-first.txt`);
  the line itself printed in 2 of those 5. *After:* with the runner changed too, 0 of 150 runs printed the line and 150 passed (`results/test41-after.txt`, load
  average 7 to 8), and the whole file passed, 78 tests in 37.0 s, with no cleanup line (`results/test-groups-after.txt`).
- *Lint.* `ruff check` (0.17.2 with its defaults; the repository configures none) reports the same 92 findings on the two changed files before and after, none added;
  the two scripts of the evidence folder are clean under `ruff` and `shellcheck` (`results/lint.txt`).
- *Tier.* The quick tier for the change, started when no live run of any session was on the machine: 21 of 21 suites passed in 214.1 s at 8 jobs, and no suite's
  log holds a cleanup record.

**Findings**
- F27 (firm): the line in the push check came from the second, redundant group SIGKILL of `_abort_process` landing in the window in which macOS refuses to signal a
  group that is already dying. No process was left behind in any of the 3,000 trials or the 150 runs; the line was a false alarm. With the second kill sent only after
  a failed termination, the test printed it in 0 of 150 runs (19 of 150 before).
- F28 (firm, one run on record): on macOS every suite's verdict passes through `ps`, because the group of a suite that ended and left nothing running always answers
  `EPERM`, and `_darwin_zombie_only_group` asks `/bin/ps` to confirm that only zombies are left. Where `ps` cannot be started, every suite is reported failed with
  `cleanup: signal 9: PermissionError; group cleanup unconfirmed`, passing or not. That is the one real run on record with the text: the sandboxed tier of 2026-11-18, 23
  of 23 suites, 18 of them with passing tests. A `ps` slower than the observer's 2 s would fail the one suite being reaped; that is not on record. Left as it is: that
  sandbox also refused the ports and keychains the suites need, so the tier has no use there, and outside it no run on record shows the text. If the line is on every
  suite, look at whether `ps` can run, and run the tier outside the sandbox.
- F29 (firm for the mechanism, no case on record): `_signal_group`'s rule is unchanged, so it still records `EPERM` as unconfirmed when a group signal lands while
  the leader is exiting and not yet waitable. Outside `_abort_process` that takes a coincidence: a suite that ends at the moment its timeout fires or its run is
  cancelled, or a leader that takes about the 1 s grace to die from SIGTERM. All of those are on paths that already report a timeout or a cancellation, and the text is
  added to that report. On the passing path the runner signals the group only after its probe says the leader exited; a member of the group still exiting when `ps`
  looks would fail the check and the suite with it. Not seen: 3,000 of 3,000 reaps in the probe were quiet, and no run outside the sandbox has the text. Not built,
  and why: a rule that waits for the leader's exit before judging `EPERM` puts a time bound into the code that decides which processes the runner may signal, and a
  rule that lets the reap's positive check clear an earlier record needs three call sites that read the records before the reap to change with it; no run on record
  needs either.
- F30 (firm for the code path, very likely for the attribution): where `ps` cannot start, `fixture_process.stop_group` raises before it sends a signal, so a worker
  that an owned fixture leaves in its group outlives the test. Six such processes of `BaseTestsProcessOwnershipTest` lived from the sandboxed tier of 2026-11-18 until
  2026-11-22; one was stopped at the owner's word that morning, and the five others are left as they are for the owner to decide. Not changed: the rule that nothing is
  signalled without a look at the group is the module's own, and the one case on record is that sandbox.

**Decision (routine, this session's, 2026-11-22).** Remove the repeated kill instead of only writing down what the line means. The line had cost three looks (its
author's on 2026-11-15, this session's report of it, the owner's question), and a diagnostic that fires on one push in eight for no fault is one nobody will believe on
the day it fires for one. Removing an action was chosen over adding a rule to `_signal_group` for the reason in F29. Not built, and offered to the owner instead: a
check at the start of a tier that refuses to run where `ps` cannot start. It would have ended the sandboxed run of 2026-11-18 before it failed 23 suites and left six
processes; there is that one run on record, and its session saw the cause within six minutes.

**Not done, and unknown.** Linux was not run in this round: the change removes a call, the test's new assertion holds wherever the reap's kill follows the probe, and
CI's Linux runners run `test-groups` on the push. No test was found that reaches the branch that still sends the final SIGKILL (a termination that itself raises
inside `_abort_process`); that branch behaves as before. The gap between the two kills inside the real `_abort_process` was not timed, only its effect (12.7% in the test
against 3.6% back to back in the probe). Why macOS answers `EPERM` and not success for a group that is dying was not read from the kernel's source; that a group
holding only a zombie answers `EPERM` to `killpg` on macOS was measured before (`docs/shiploop-batch-1011-integration-journal-2026-10-09.md`). Whether the `EPERM` of
the sandboxed run was that ordinary answer or the sandbox's own refusal cannot be told from its log; with `ps` unable to start the runner could confirm neither. The two
probe scripts were written for this round and are run by no suite.
