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
printed command carried it), so nothing in r3's records shows a wrong-host launch. I did not claim it in the SPEC. The r2 resume log's first line
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
The design audit's numbers (16 of 16 bounded launches of Chrome 154.0.8037.99 printed the title in 0.36 to 0.47 s; 3 of 16 exited in 12 to 20 s) are
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

## Deviations from the design, and why

1. **No `--version` probe of any host CLI.** The design called the host CLI with `--version` for every host. The brief assigns the host build to
   G3, which records `host_build` on each launch record; this change reads `launch_environments[i].host_build` and never starts a CLI. For the
   saved runs it is null (their records predate it). Consequence: the three base fakes needed no `--version` branch, and `claude_code_version`
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
9. **`outcome_class` is also written to the baseline row** (one key), so a future skip rule can read it; `scan_baseline` is not changed here
   (G3 changes it in a sibling worktree). Until that rule exists the blocked 20261007 Grok row (503 turns, pass false) is still offered as the
   last comparable row; the SPEC says so.
10. **Launch records are named by the second they began in, so two launches of one host in one second overwrite one file.** This is existing
    behaviour (`invocation-resume-<host>-<seconds>.json`); a real resume is never that fast, and the one test that resumes twice waits 1.1 s.
    Not changed. Interim: noted, not fixed.

11. **Not built from the design:** the `## Ended as` section of `mismatch.md` and a `host_cli_version` key in the baseline row. Neither is in the
    brief's scope; the host build is G3's launch-record field, and a second field beside `claude_code_version` is what the audit warned against
    (correction 9).

## Open risks

- A harness killed with SIGKILL during the (at most about 21 s) browser probe leaves the headless browser it started, which the harness cannot
  stop; the probe's own `finally` runs on every other ending. Chrome 154 was seen to linger after printing, so an orphan would persist until
  killed by pid. The window is the probe only, and only for a case that declares a browser.
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
- A skip rule in `scan_baseline` for rows whose `outcome_class` is not PASS: G3 owns `scan_baseline`; one line plus a test once it lands.
- The ENVIRONMENT-SUSPECT overlay, `unverified`, a start-time `other_harnesses_alive`: rejected or dropped by the audit and the plan.
- Overlap across output roots (a run started with `--output` elsewhere is invisible) and a pause-aware overlap (the span counts a pause
  between sessions): documented limits, not built.
- Whether the harness-side probe predicts what happens inside the Grok host (audit missed unknown 0): needs the identical `--dump-dom` command
  run through the Grok host's shell tool next to a Claude host. Not run.

## Hand-off for the packet group (do not edit skills/ here)

The lingering `--dump-dom` fact: Chrome 154 printed the dumped DOM and then often did not exit (3 of 16 bounded launches exited within 12 to 20 s;
the audit's measurement). A probe duty in a packet or platform reference should read the browser's output and stop the process it started
once the expected content appears, not wait for the process to exit. This fits the Grok r1 record, where the `--dump-dom` call returned only
"still running after 30s ... moved to the background", but that is unproven.

## Data shapes for the Run Review session (exact keys)

Everything is additive and optional. `result.json`, top level:

- `outcome_class`: `"PASS" | "FAILED" | "BLOCKED" | "STOPPED" | null`. `outcome_basis`: string (for null, why it is unknown). Also `outcome_class`
  in each baseline row. Not a verdict: do not put it inside a `verdicts` map.
- `termination` gains `engine_blocked_by` (`"user" | "access" | "external" | null`), `engine_awaiting_kind` (`"answer" | "present" | null`),
  `engine_awaiting_no_default` (`true | false | null`: true when the engine stated why no default would do), and, on a regrade that kept the original
  ending, `engine_stage_at_regrade`, `engine_status_reason_at_regrade`, `engine_blocked_by_at_regrade`, `engine_awaiting_kind_at_regrade`,
  `engine_awaiting_no_default_at_regrade` beside the existing `engine_status_at_regrade`.
- `product_at_stop`: absent for a run that passed; otherwise
  `{"information_only": true, "ran": true, "worktree": "<path>", "engine": {"status": "blocked", "stage": "system-test-author"}, "checks": [{"command": "...", "pass": true, "returncode": 0, "timed_out": false}, {"command": "...", "pass": false, "returncode": null, "timed_out": true}, {"command": "...", "pass": false, "returncode": 1, "timed_out": false, "output": "<=300 chars"}], "passed": 4, "failed": 0, "timed_out": 0, "total": 4}`
  or `{"information_only": true, "ran": false, "reason": "...", "engine": {"status", "stage"}}`. `shiploop.worktree_checks` is gone.
- `environment`: `{"start": <start record>, "end": <end record or {"observed": false, "reason": ...}>, "hosts_used": ["grok", "claude"], "mixed_host": true, "environments": [{"launch": "invocation.json", "host": "grok", "model": "grok-4.7", "effort": "medium", "host_build": null, "environment": null | <start record>}, ...], "overlap": {...}}`.
  - start record: `{"observed": true, "at": "2026-10-09T16:42:10Z", "tools": {"node": "v25.9.0", "python3": "Python 3.14.7", "git": "git version 2.54.0 (Apple Git-157)"}, "cpus": 18, "loadavg": [8.11, 6.96, 6.06], "display_hold": true, "unread": {}, "browser": <browser record>}`; a value that could not be read is `null` and its reason is in `unread` (`{"node": "not found on PATH"}`).
  - end record: `{"observed": true, "at": "...", "cpus": 18, "loadavg": [...], "unread": {}}`; for a regrade `{"observed": false, "reason": "regraded: the end of the run was not observed"}`.
  - overlap: `{"observed": true, "basis": "...", "span": {"first": 1791481009.559, "last": 1791485559.3}, "siblings_read": 8, "runs": [{"folder": "r1-checkers-sonnet", "case": "custom", "hosts": ["claude"], "overlapped_seconds": 787.1, "started_offset_seconds": 280.4}]}`; `runs: []` means read and none overlapped; `{"observed": false, "reason": ...}` means unknown.
  - browser record: not declared `{"declared": false, "probed": false, "reason": "no case or --need declares a browser"}`; declared but not runnable `{"declared": true, "probed": false, "reason": "..."}`; probed `{"declared": true, "probed": true, "binary": "...", "version": "Google Chrome 154.0.8037.99", "flags": [...], "ceiling_seconds": 20.0, "grace_seconds": 1.0, "file": <target>, "http": <target>}` where a target is `{"title_seen": true, "output_s": 0.41, "exited": false, "lingered": true, "returncode": null, "killed": true, "group_empty": true, "error": null}` (`http` may be `{"probed": false, "reason": ...}` if the loopback stand-in could not listen).
- Each launch record (`invocation.json`, `invocation-resume-<host>-<seconds>.json`) gains `needs` (array) and `environment` (the start record; for a regrade's own record `{"observed": false, "reason": "regraded: no host was launched"}`).
- `metrics.json` is unchanged. A mixed-host run is named by `environment.mixed_host` and `hosts_used`; its `host` in `result.json` is the host that ran last.
- Suggested rendering: a class chip with the basis (not in the verdict map); a "Product at stop" card (n of m at the stated stage, labelled information only); an "Environment" block with the machine, a MIXED HOST banner, the overlap list with the start offsets, and the browser rows with seconds.
