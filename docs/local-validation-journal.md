# Local validation journal

Living record of the work that makes local test runs in this repository faster without weakening them. Each round
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
  bring the baseline's floor to `shiploop-navigator-contract`, about 100 s against 133 s.
- F5 (firm): the `prompt` group needs the obligation ledger. On 5d3628b0 the four packet-size suites pass while the
  ledger fails, which is the 2.11.0 CI failure. Proof: `prompt-jobs8-5d3628b0-ledger-red.receipt.json`.
- F6 (exploratory, unrelated to the runner): `shiploop-actual-improve-cli`'s
  `test_a_live_shaped_pass_needs_at_most_1500_characters_of_model_output` depends on the checkout path's length. On
  5d3628b0 it writes 1,536 characters and fails at a checkout path of about 130 characters (a scratch worktree), and
  passes at this worktree's 59-character path. CI's path is shorter still.
- F4 (exploratory): GitHub CI now runs each group with 4 jobs, the runner's CPU count. Quick is covered by the local
  run above, but the full shards (`shiploop-1|2|3`, `core`) have not yet run in parallel anywhere. If one is flaky
  under parallel load, `--jobs 1` in `ci.yml` restores the serial run.
