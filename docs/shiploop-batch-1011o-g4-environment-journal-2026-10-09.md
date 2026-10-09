# Batch 1011, group G4: environment, product at stop, outcome class, resume defaults (2026-10-09)

Worktree `b1011o-aaa47e`, branch `batch1011o-aaa47e`, base `30a3b40a`. Design and audit: `docs/experiments/batch-1011-harness-design-audit-20261009/design-audit.json`,
key `F4-environment-and-product-at-stop` (verdict implement-smaller / approve-with-corrections; the audit's `safer_alternative` is the scope,
as `docs/shiploop-e2e-harness-batch-1011-plan-2026-10-09.md` adopts it). Harness only: nothing under `skills/` or `agents/` changed, so no change
note and no release. Status of every claim below is marked firm (reproduced from the saved runs or a test), interim, exploratory or superseded.

## What was built, and in which commit

| Part | Commit subject | Where |
|---|---|---|
| SPEC amendment (anchor, non-regression, dispositions) | `docs(shiploop-e2e): SPEC amendment of 2026-10-09 ...` | `test/shiploop_e2e/SPEC.md`: three rows in "How the harness checks the clauses", the "Parallel work" known limit, and two rules |
| `product_at_stop` | `feat(shiploop-e2e): product_at_stop replaces shiploop.worktree_checks ...` | `run.product_at_stop`, `iterate.learnings_message` |
| `environment` and the browser capability record | `feat(shiploop-e2e): the environment record ...` | new `environment.py`; `run._main`; `cases.json` `needs`; fixtures `test/fixtures/e2e-environment/` |
| `outcome_class` | `feat(shiploop-e2e): outcome_class ...` | `run.outcome_class`, `run.blocked_detail`, `run.termination_facts` |
| `--resume-run` defaults and the host-change refusal | `feat(shiploop-e2e): --resume-run continues the run's own driver ...` | `run.resume_identity`, `--allow-host-change` |
| This journal, the README and LEARNINGS | `docs(shiploop-e2e): G4 journal ...` | |

Tests: `test/shiploop-e2e-environment.test.py`, registered as its own suite (`test/suite_catalog.py` list and duration, `test/test-groups.test.py`
counts 71 and 112), because `test/shiploop-e2e.test.py` measures about 115 to 120 s locally against `QUICK_MAX_SECONDS` 120.

## Findings (what was measured, and what it says)

**F1. Of the nine round runs, one is mixed-host; the brief's "r2 and r3 were resumed with the wrong host" is evidenced for r2 only. Firm.**
`runrecord.launches` on the fixtures: `r2-battleship-grok-none` names `["grok", "claude"]` (invocation.json grok, then
`invocation-resume-claude-1791508003.json`; the `invocation-resume-grok-1791509021.json` beside them is a regrade and is not a launch). The other
eight are single-host. `r3-battleship-grok-none`'s only resume record is a Grok launch (`--host grok` was passed; its resume log shows the
printed command carried it), so nothing in r3's records shows a wrong-host launch. The claim came from the dispatching brief; no file in the
repository says it (commit 4337522a's message wrongly says "the brief and LEARNINGS say" it: LEARNINGS says r2 only). I did not claim it in the SPEC. The r2 resume log's first line
is `host=claude model=claude-sonnet-5-5` and its printed resume command carries `--host claude`, which is the harness repeating the default it
took (the resume had been started without `--host`).

**F2. All nine round runs overlapped another run; three saw the overlap begin more than a second after their own start. Firm; the audit's "5 of 9" does not reproduce.**
Recomputed from the first and last `timeline.jsonl` stamps of the saved folders (and replayed from the committed extracts by
`OverlapTest.test_the_nine_round_runs_...`): 9 of 9 overlapped at least one sibling. An overlap that began later than the run's own start by more
than one second: `r1-battleship-grok-none` and `r1-battleship-sonnet` (`r1-checkers-sonnet` began 280.4 s and 280.9 s in) and
`r3-battleship-grok-none` (`r3-checkers-sonnet` began 763.3 s in): 3 of 9. With any positive offset the count is 6 of 9 (the other three,
`r2-battleship-sonnet`, `r2-checkers-sonnet` and `r3-battleship-sonnet`, had a sibling begin 0.06 to 0.53 s after them), so "5 of 9" matches neither
threshold. Seven of the nine started within 0.6 s of a sibling (the r1 pair, the r2 trio, the r3 pair). The conclusion the audit drew holds
under every count: a count taken when a run starts records a misleading 0 or 1 for the incident it was meant to catch, so `overlap` is read at the
end from the whole span and lists each neighbour's `started_offset_seconds` (positive: it began later).

**F3. The recorded results classify as the owner's hand attribution said. Firm (replayed from the 11 recorded result.json extracts).**
`v1230-battleship-grok-none` and `r1-battleship-grok-none`: BLOCKED. `r3-battleship-grok-none`: STOPPED. `r2-battleship-grok-none` (regraded, pass true)
and the seven Sonnet runs: PASS. Their old results have no blocked detail, so the basis says "no blocked result was read from the state"; the
engine states (state.md extracts) give `v1230`: blocked_by access, awaiting kind `present`, no_default stated; `r1`: access, `answer`, no_default
stated; `r3`: engine active at implement, no blocked detail.

**F4. A paused engine and a halted engine need a definition, and the engine's own code supplies one. Firm (shiploop_navigator, read).**
`shiploop_navigator` groups `paused` and `blocked` as "awaits resume" and `done` and `halted` as terminal, and `control()` accepts resume for
paused and blocked only. So paused is BLOCKED with no `blocked_by` (no blocked result names who can unblock it), and halted is FAILED (terminal and
unfinished). The exhaustiveness test reads the engine's status set from `shiploop_navigator._STATUSES`, so a new engine status fails it until a
class is chosen.

**F5. A Claude host killed by the deadline is STOPPED, not FAILED. Firm (a mutant the first test table did not kill).**
Claude is not resumable, so its `resume_stop` is "host is not resumable" even when the harness killed it at `--timeout`; only `process_status`
`timeout` tells the two apart. The classifier checks `process_status` before the resume_stop prefixes, and a test case pins it.

**F6. The browser probe has not been run against a real browser by this change. Interim: nothing here measured Chrome.**
The design audit's numbers (16 of 16 bounded launches of Chrome 154.0.8037.99 printed the title in 0.36 to 0.47 s; 3 of the 16 exited before the audit's 12 to 20 s ceiling and the other 13 were still running there and were killed, so their exit time is unknown) are
the basis for reading the title, not the exit, and are quoted as the audit's. The tests use a fake browser that prints the title and then lingers,
exits by itself, exits slowly, never prints, or dies. The calibration is still to do, from a Terminal tab and from a Desktop background task, ten
launches each, thirty seconds apart, with no other Chrome running:
`python3 test/shiploop_e2e/environment.py --need browser` and journal `title_seen`, `output_s`, `exited`, `lingered` per kind. No overlay,
threshold or verdict is built on it.

**F7. Closing a pipe that a thread is still reading blocks until the pipe closes, so a helper that left the browser's group could hang the probe. Firm (reproduced with a `sleep` child of my own, then by a test).**
A first version read the browser's output through a buffered reader in a thread and closed it at the end. Closing blocks while another thread is
inside a read of the same buffered file; a helper that left the group (a detached crash reporter, say) and holds the output open therefore held
the probe: the new test took 8.2 s against its 6 s bound with the helper holding the pipe for 8 s, before any host would have started. The reader now
polls the raw descriptor with `select` and a stop flag, and the pipe is closed only after the reader has gone. Commit
`fix(shiploop-e2e): the browser probe does not block on a pipe a helper holds open`.

## Method and evidence, per part

- Red first, then green, for every behaviour; the red reason is in each commit message. After green, mutants were applied to scratch copies of
  the production file and the suite re-run: browser probe 8 (wait for exit, ignore the grace, keep the server open, keep the profile, kill an
  exited browser, signal the wrong group, drop a hygiene flag, ignore the ceiling), tools and overlap 12, run.py wiring 11, outcome class 14 plus
  3 added after survivors, resume 9. Survivors were closed with stronger tests, not left: the grace mutant (a `slow-exit` fake mode), a blocked
  detail read after the block was answered, a `no_default` that was always true, and a deadline-killed Claude host.
- The process-safety rule held: no test reads the machine's process table (the base case patches `listeners.observe`), starts a real browser
  (the base `HarnessCase.setUp` patches `environment.autodetect_browser` to none, and the probe's tests inject a fake with `--browser-bin`), or
  signals a process it did not start. The probe's tests wrap `os.killpg`: a group that is not a fake browser's own is recorded and not sent,
  and a bystander in a session of its own is asserted alive afterwards. The mutants that signal a wrong group were therefore caught by the
  wrapper and sent nothing. Mutants of code that signals were applied only to the probe's own fake children.
- Fixtures: `test/fixtures/e2e-environment/` (156 KB): `rounds/<run>/invocation*.json` and `timeline.jsonl` (first two and last two stamps) for the
  nine round runs, `recorded/<date>/<run>.json` (pass, host, process, termination) for 11 results, `engine/<run>/state.md` (reduced) for the
  three Grok runs that did not pass. `extract.py` rebuilds them from `/Users/dadleet/e2e-runs`; no test reads that folder.

## Verification at the final tree (ee246a81), machine load 7 to 9 from the sibling groups' runs

- `python3 test/shiploop-e2e-environment.test.py`: 93 tests OK, 32.4 to 33.0 s (three runs).
- `python3 test/shiploop-e2e.test.py`: 404 tests OK, 113.1 s (115.6 s at the base before any change; 115.0, 119.0 and 120.5 s on the way, the
  last two under heavier load). No test was added to it.
- `python3 test/shiploop-e2e-runrecord.test.py`: 6 OK. `python3 test/test-groups.test.py`: 21 OK.
- `bash test/run-all.sh --group quick --changed-from 30a3b40a`: PASS, 28 suites (including `shiploop-e2e`, `shiploop-e2e-runrecord`,
  `shiploop-e2e-environment`, `shiploop-run-review`, `shiploop-navigator-contract` and the apparatus mock replay).
- A first quick-tier run with `GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null` exported failed `shiploop-chain-async` (3 tests: "prepare
  refuses Git context environment overrides"). That suite refuses those overrides by design, so the quick tier is run without them; the e2e
  harness tests isolate Git themselves (`isolate_git`). Not a product defect; the rerun without them passed.

### Verification after the fix round (head 3519a1d1 and this entry's commit), load 7 to 9

- `python3 test/shiploop-e2e-environment.test.py`: 125 tests OK, 60.5 s (93 tests, 33 s before the fix round; the probe's process-safety tests
  start real fake browsers). Catalog duration 65 s, under `QUICK_MAX_SECONDS` 120.
- `python3 test/shiploop-e2e.test.py`: 404 OK, 113.8 s. `python3 test/shiploop-e2e-runrecord.test.py`: 6 OK. `python3 test/test-groups.test.py`: 21 OK.
- `bash test/run-all.sh --group quick --changed-from 30a3b40a`, run without exported `GIT_CONFIG_*` variables: PASS, 28 suites OK, 0 FAIL.
- Mutants of scratch copies that survived the first fix-round tests and now turn red: the grace not polled for a stop, `lingered` counting an
  interrupted browser, a non-finite stamp accepted, a glob-only launch-record name counted unreadable, the needs read from the first launch or
  ignored, the stamp never bumped. Item 8 and 17's named mutants (E6, E2, E16, E19, R12, R20, R21, R27, E4, E5, the killpg guard, the fixed port) all
  turn red.

## Deviations from the design, and why

1. **No `--version` probe of any host CLI.** The design called the host CLI with `--version` for every host. The brief assigns the host build to
   G3, which records `host_build` on each launch record; this change reads `launch_environments[i].host_build` and never starts a CLI. It is null for the saved runs (their records predate it) and,
   by G3's design, for every Claude launch (Host.cli_version returns None for Claude); each entry carries `host_build_reason` to say which. Consequence: the three base fakes needed no `--version` branch, and `claude_code_version`
   (from Claude's init event) stays the one authority for Claude, with no second competing field (audit correction 9).
2. **`other_harnesses_alive` is replaced by `overlap`** (audit correction 2), read at the end from sibling timelines instead of at the start
   from `.harness-lock`. The lock read also raced a sibling's `hold_case` (`case_alive` takes a brief shared lock), which the end-of-run read does
   not do.
3. **`environment` is a list of launches as well as a start/end pair** (audit correction 3): each launch record carries its own start, and the
   result carries `hosts_used`, `mixed_host` and `environments`. A regrade restates every launch's record and the last launch's start.
4. **No ENVIRONMENT-SUSPECT overlay, no `unverified`, no `ended_as`, no `outcome_detail.environment_failed`** (audit corrections 1 and 5); the
   class and its basis are two keys, `outcome_class` and `outcome_basis`.
5. **The design's `environment.probe` module-level API is `environment.start_record` / `end_record` / `browser_record`.** The design's `failed_needs`
   has no consumer once there is no overlay, so it is not built.
6. **Tool versions run three short `--version` execs** (node, python3, git; 0.036 s together on this machine), read once per harness process and
   cached, so the 400 `main()` calls of the existing suite pay once. "Process-free" in the brief is read as: starts no browser or host and
   signals nothing. A tool that cannot be read is null with its reason in `unread`.
7. **`--resume-run` model and effort are defaulted from the last launch record only while the host is unchanged**, and an explicit `--model` or
   `--effort` wins. The brief said "refuses a silent host change"; it did not ask to refuse a model change, so none is refused (an explicit flag
   is not silent). A cross-host finish needs `--allow-host-change`, the one flag added: without a named flag a deliberate finish on another host
   cannot be told from the mistake that produced r2, and the SPEC records why.
8. **A custom prompt prints a one-line note and the README documents the limit** (audit correction 8; both options were allowed). The note
   is printed for a fresh custom launch with no `--need`, not for a named case, a resume or a regrade.
9. **`outcome_class` is in result.json only.** An earlier version also wrote it to the baseline row; the review removed it. Which baseline rows are
   comparable is the baseline code's own rule (`scan_baseline`, which group G3 changes in a sibling worktree: a row whose engine did not reach done
   is never compared); no baseline rule reads `outcome_class`, and this change does not touch `scan_baseline`.
10. **Launch records are named by the second they began in** (`invocation-resume-<host>-<seconds>.json`). I first left this as existing behaviour
    ("a real resume is never that fast"). The fix round's regrade test showed otherwise: a regrade that began in the same second as the launch before
    it, on the same host, overwrote that launch's record and the run then read as one host's. `run.launch_stamp` now takes the next free number
    for the record and the prompt file, so neither is overwritten; fixed in the fix round.
11. **Not built from the design:** the `## Ended as` section of `mismatch.md` and a `host_cli_version` key in the baseline row. Neither is in the
    brief's scope; the host build is G3's launch-record field, and a second field beside `claude_code_version` is what the audit warned against
    (correction 9).

## Open risks

- A harness killed with SIGKILL during the (at most about 43 s) browser probe leaves the headless browser it started, which the harness cannot
  stop; a SIGTERM or SIGHUP to the harness, a Ctrl-C, an exception and the standalone command's SIGTERM all end the browser (the probe stops it
  at once, its group is registered with the harness's host registry, and its `finally` kills what is still running). Chrome 154 was seen to
  linger after printing, so an orphan would persist until killed by pid. The window is the probe only, and only for a case that declares a
  browser. A process-group signal sent after the leader was reaped could in theory reach a reused group; that gap is unreproduced on macOS and
  nothing was built for it (no `waitid`).
- Three cases now declare a browser (`battleship`, `battleship-scoring`, `checkers`), so every run of them starts a headless browser on the harness
  side for about a second before the host starts. A suite of three starts up to six together. The cost is recorded in the `output_s` fields; if a
  real calibration shows the browser load disturbs a run, the declaration is one line per case in `cases.json`.
- The record has no calibration against a real browser, so what a failed probe would mean is unknown; nothing reads it.
- The browser `version` is what the binary on disk reports with `--version`, not the build of a browser that is already running (the audit saw a
  running Chrome on 154.0.8037.98 helpers while the disk binary was 154.0.8037.99). The build used in the round-1 runs is unrecoverable.
- `overlap` sees only siblings in the same parent folder, and counts a pause between sessions as overlap.
- `outcome_class` cannot say whether a block was warranted, and a paused engine is BLOCKED by the engine's own grouping, not by an observation of
  who paused it.

## Existing tests edited (legitimately broken by the change)

- `test/shiploop-e2e.test.py`: `LearningsTest.RESULT` and its assertion move from `shiploop.worktree_checks` to `product_at_stop`;
  `HarnessCase.setUp` patches `environment.autodetect_browser` to none; and seven tests that finish a Grok run on Codex now pass
  `--allow-host-change` (`CodexRunTest.test_resume_run_continues_a_stopped_grok_run_on_codex`,
  `ResumedRunRecordTest.test_a_resumed_run_keeps_the_termination_each_earlier_invocation_recorded` and
  `.test_a_refused_resume_never_overwrites_the_record_of_the_run_it_would_have_continued`,
  `RegradeRecordTest.test_a_run_resumed_on_another_host_is_regraded_as_that_host_with_its_plugin_and_versions`,
  `BaselineAbsentTest.test_a_resumed_run_says_it_is_not_a_baseline`, `StopFileTest.test_a_stale_stop_file_does_not_stop_a_later_resume`,
  `ResumeCliThroughMainTest.test_a_run_continued_on_another_host_keeps_the_cli_it_started_on`). No other existing test changed.

## Deferred, with the reason

- The real-browser calibration (F6) and any use of the record: needs a real browser run from a Terminal and from a Desktop task.
- The ENVIRONMENT-SUSPECT overlay, `unverified`, a start-time `other_harnesses_alive`: rejected or dropped by the audit and the plan.
- Overlap across output roots (a run started with `--output` elsewhere is invisible) and a pause-aware overlap (the span counts a pause
  between sessions): documented limits, not built.
- Whether the harness-side probe predicts what happens inside the Grok host (audit missed unknown 0): needs the identical `--dump-dom` command
  run through the Grok host's shell tool next to a Claude host. Not run.

## Hand-off for the packet group (do not edit skills/ here)

The lingering `--dump-dom` fact: Chrome 154 printed the dumped DOM and then often did not exit (3 of the 16 bounded launches exited before the audit's
12 to 20 s ceiling and the other 13 were still running there and were killed; the audit's measurement). A probe duty in a packet or platform reference should read the browser's output and stop the process it started
once the expected content appears, not wait for the process to exit. This fits the Grok r1 record, where the `--dump-dom` call returned only
"still running after 30s ... moved to the background", but that is unproven.

## Fix round (review of 056a16be by two adversarial reviewers), 2026-10-09

Text corrections came first (a4b56729), then one code commit per behaviour. Item numbers are the coordinator's.

| Item | Disposition | Where | Test |
|---|---|---|---|
| 1 B1 overlap bound | fixed (text and the `OVERLAP_BASIS` constant) | SPEC Parallel work, README, LEARNINGS, journal, `environment.OVERLAP_BASIS` | `OverlapTest` basis assertion |
| 2 A1 probe process safety | fixed | `probe_target` (`finally` ends the browser, `should_stop`, `getpgid` OSError), `LIVE_PROBE_GROUPS` + `end_live_probes` (called by `run.end_live_hosts`), `environment.main` SIGTERM/SIGHUP handler, `run` passes `TERMINATION.is_set` | `test_a_harness_told_to_end_during_the_probe_...`, `StandaloneProbeTest` (SIGTERM and SIGHUP), `test_a_probe_that_cannot_confirm_its_group_...`, `test_the_harness_ending_its_live_hosts_...`, `test_an_exception_while_the_probe_waits_...`, `test_a_probe_told_to_stop_...` |
| 3 A2+B7 regrade identity | fixed | regrade restates `runrecord.launches(out)[-1]`; `resumed_run.from_host` meaning documented; refusal text honest for an already-mixed run | `test_a_regrade_restates_the_identity_of_the_last_launch_...`, `test_a_resume_of_a_mixed_run_names_the_last_launch_...`, `test_the_refusal_names_the_recorded_host_...` |
| 4 B3 baseline row | fixed | `outcome_class` removed from `baseline_row`; sentences replaced by a pointer | two through-main tests assert it is absent |
| 5 B4 one blocked reader | fixed | `metrics.blocked_detail(state)` | `RecordedOutcomeClassTest` shared-reader tests |
| 6 B6 null reasons | fixed | `host_build_reason`, `environment_reason`, `restated_start` reason | `test_a_null_host_build_or_environment_says_why`, `test_a_start_that_cannot_be_restated_...` |
| 7 B2 SPEC wording | fixed (text) | SPEC machine-record rule | |
| 8 A3 vacuous tests | fixed | E6 display hold False case; E2 sequential timestamps; E16 reader thread and closed pipe; E19 `group_empty` follows `_group_alive` | see the mutant table |
| 9 B9 sequential probes | fixed | `browser_record` | `test_the_two_kinds_are_probed_one_after_the_other_...` |
| 10 A5 unmeasured read as measured | fixed | `runrecord.unreadable`, `result_block`, `overlap` (`siblings_unreadable`, finite stamps, first <= last, hosts null with a reason) | `OverlapTest`, `LaunchRecordsTest` |
| 11 B8 labels | fixed | comments, `empty_seconds` recorded, SPEC and README wording | `test_the_record_says_the_three_times_it_used` |
| 12 B10 cap stops | fixed | `run.CAP_STOPS` | `test_a_host_session_that_ended_on_the_cap_...` |
| 13 A7 halted | documented | SPEC S-14 row, README | |
| 14 A8 PATH label | fixed (text and the `environment.py` docstring) | | |
| 15 A9 regrade server | documented, not reaped | comment in `_main`, README | |
| 16 A10 model/effort note | fixed | `_main` resume branch | `test_a_model_or_effort_that_differs_...` |
| 17 A4 gaps | fixed | R12 needs carry from the last launch; R20 follow-on env through main; R27 refusal names the recorded host; flags pinned; killpg guard in the fixture; port 0 | see tests |
| 18 B11 text slips | fixed (text) | journal, LEARNINGS | |
| 19 B12 flag rationale | fixed (text) | SPEC, README | |
| 20 B13 shapes | fixed (journal data shapes, README) | `version_unread`, absent `engine_*` keys of an old regrade, the `start` duplicate (documented, kept) | |
| 21 A6 | documented: unreproduced, nothing built | journal open risks | |

## Data shapes for the Run Review session (exact keys)

Everything is additive and optional. `result.json`, top level:

- `outcome_class`: `"PASS" | "FAILED" | "BLOCKED" | "STOPPED" | null`. `outcome_basis`: string (for null, why it is unknown). In result.json only (not in
  the baseline row). Not a verdict: do not put it inside a `verdicts` map.
- `termination` gains `engine_blocked_by` (`"user" | "access" | "external" | null`), `engine_awaiting_kind` (`"answer" | "present" | null`),
  `engine_awaiting_no_default` (`true | false | null`: true when the engine stated why no default would do), and, on a regrade that kept the original
  ending, `engine_stage_at_regrade`, `engine_status_reason_at_regrade`, `engine_blocked_by_at_regrade`, `engine_awaiting_kind_at_regrade`,
  `engine_awaiting_no_default_at_regrade` beside the existing `engine_status_at_regrade`. A regrade of a result written before this change has
  none of the `engine_blocked_by` / `engine_awaiting_*` keys (only the `*_at_regrade` ones), not nulls. The shared reader of the blocked detail is
  `metrics.blocked_detail(engine)` (keys `blocked_by`, `awaiting_kind`, `awaiting_no_default`); `termination` prefixes them with `engine_`.
- `product_at_stop`: absent for a run that passed; otherwise
  `{"information_only": true, "ran": true, "worktree": "<path>", "engine": {"status": "blocked", "stage": "system-test-author"}, "checks": [{"command": "...", "pass": true, "returncode": 0, "timed_out": false}, {"command": "...", "pass": false, "returncode": null, "timed_out": true}, {"command": "...", "pass": false, "returncode": 1, "timed_out": false, "output": "<=300 chars"}], "passed": 4, "failed": 0, "timed_out": 0, "total": 4}`
  or `{"information_only": true, "ran": false, "reason": "...", "engine": {"status", "stage"}}`. `shiploop.worktree_checks` is gone.
- `environment`: `{"start": <start record>, "end": <end record or {"observed": false, "reason": ...}>, "hosts_used": ["grok", "claude"], "mixed_host": true, "environments": [{"launch": "invocation.json", "host": "grok", "model": "grok-4.7", "effort": "medium", "host_build": null, "host_build_reason": "..." (superseded at the 2026-10-09 integration: "identity_unmeasured": {"host_build": "..."}, read through runrecord.host_build with G3's reasons), "environment": null | <start record>, "environment_reason": null | "..."}, ...], "launches_unreadable": [], "overlap": {...}}`. `hosts_used` and `mixed_host` are `{"observed": false, "reason": ...}` when a launch record cannot be read (its file names are then in `launches_unreadable`). `environment.start` is a copy of `environments[-1].environment` for a launch (the browser record appears in both).
  - start record: `{"observed": true, "at": "2026-10-09T16:42:10Z", "tools": {"node": "v25.9.0", "python3": "Python 3.14.7", "git": "git version 2.54.0 (Apple Git-157)"}, "cpus": 18, "loadavg": [8.11, 6.96, 6.06], "display_hold": true, "unread": {}, "browser": <browser record>}`; a value that could not be read is `null` and its reason is in `unread` (`{"node": "not found on PATH"}`).
  - end record: `{"observed": true, "at": "...", "cpus": 18, "loadavg": [...], "unread": {}}`; for a regrade `{"observed": false, "reason": "regraded: the end of the run was not observed"}`.
  - overlap: `{"observed": true, "basis": "...", "span": {"first": 1791481009.559, "last": 1791485559.3}, "siblings_read": 8, "siblings_unreadable": [], "runs": [{"folder": "r1-checkers-sonnet", "case": "custom", "hosts": ["claude"], "overlapped_seconds": 787.1, "started_offset_seconds": 280.4}]}`; an entry's `hosts` is null with `hosts_reason` when its launch records cannot be read; `runs: []` means the neighbours read had no host events in common with this run (first to last host event: neither an upper nor a lower bound), not that nothing else ran; `{"observed": false, "reason": ...}` means unknown.
  - browser record: not declared `{"declared": false, "probed": false, "reason": "no case or --need declares a browser"}`; declared but not runnable `{"declared": true, "probed": false, "reason": "..."}`; probed `{"declared": true, "probed": true, "binary": "...", "version": "Google Chrome 154.0.8037.99", "flags": [...], "ceiling_seconds": 20.0, "grace_seconds": 1.0, "empty_seconds": 2.0, "version_unread"?: "...", "file": <target>, "http": <target>}` where a target is `{"title_seen": true, "output_s": 0.41, "exited": false, "lingered": true, "returncode": null, "killed": true, "group_empty": true, "interrupted": false, "error": null}` (`http` may be `{"probed": false, "reason": ...}` if the loopback stand-in could not listen).
- Each launch record (`invocation.json`, `invocation-resume-<host>-<seconds>.json`) gains `needs` (array) and `environment` (the start record; for a regrade's own record `{"observed": false, "reason": "regraded: no host was launched"}`).
- `metrics.json` is unchanged. A mixed-host run is named by `environment.mixed_host` and `hosts_used`; its `host` in `result.json` is, from this fix round on, the host of the run's last launch (a regrade restates it
  through `runrecord.launches`); the saved r2 result still says grok beside a Claude-finished run, and `resumed_run.from_host` and `from_model`
  now name the last launch's host and model (they named the first launch's; results written before keep the old meaning).
- Suggested rendering: a class chip with the basis (not in the verdict map); a "Product at stop" card (n of m at the stated stage, labelled information only); an "Environment" block with the machine, a MIXED HOST banner, the overlap list with the start offsets, and the browser rows with seconds.
