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
- F6 (exploratory, unrelated to the runner): `shiploop-actual-improve-cli`'s
  `test_a_live_shaped_pass_needs_at_most_1500_characters_of_model_output` depends on the checkout path's length. On
  5d3628b0 it writes 1,536 characters and fails at a checkout path of about 130 characters (a scratch worktree), and
  passes at this worktree's 59-character path. CI's path is shorter still. Update 2026-10-28: it still reproduces on
  337b09c5, writing 1,538 characters at a 150-character checkout path and passing at 59.
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
now asks for a path-independent measurement with headroom, and asks the owner before any number changes.

**Findings**

- F18 (firm): round 1's assumptions are now stated where the code is, each beside the test that guards it. Proof:
  the comments above `MAX_DEFAULT_JOBS` and `_SHIPLOOP_PACKET_SOURCES`, and `test/test-groups.test.py` passing.
- F19 (firm): the hub check no longer depends on a count. Adding consumers leaves a hub's selection unchanged, and
  turning the hub rule off fails it. Proof: the mutant above.
