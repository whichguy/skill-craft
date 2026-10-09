# Batch 1011, worktree n, group G2: journal (the clear-the-context re-orientation record, phase 1)

Living journal of group G2 of the 2026-10-09 harness batch (plan: `docs/shiploop-e2e-harness-batch-1011-plan-2026-10-09.md`). Worktree
`.claude/worktrees/b1011n-aaa47e`, branch `batch1011n-aaa47e`, base `30a3b40a`, design key `F2-clear-context-probe` in
`docs/experiments/batch-1011-harness-design-audit-20261009/design-audit.json` (the audit's `safer_alternative`, phase 1, is the scope).
Harness only: no skill, no release. Code and tests live in `test/shiploop_e2e/` and `test/shiploop-e2e-reorientation.test.py`; the
amendment is in `test/shiploop_e2e/SPEC.md` ("A fresh context is recorded, not scored", dated 2026-10-09, plus a correction commit).
Evidence: `test/fixtures/reorientation/` (compact extracts of the saved runs, rebuilt by the `extract.py` there) and
`docs/experiments/reorientation-20261009/` (`measure.py` and its `compactions.json`, the compaction table of section 5).

Status words: firm (a hermetic test that failed first, or a recorded figure recomputed from the saved runs), interim, exploratory,
superseded. Every figure below was recomputed from the saved runs; none is copied from the design text.

## 1. What was built, and what was not

Built (all record-only: no verdict, no threshold, no baseline key, nothing in `result.json`):

1. `ToolLog.feed` (with `metrics.tool_call_events` and `metrics.cancelled_update`): the one reader of tool calls and their results.
   `collect` calls it, and so does the windowed reading. Behaviour unchanged (77 existing tests green after the refactor).
2. `<output>/sessions.jsonl` (`test/shiploop_e2e/sessionlog.py`, hooked into the one `session()` closure of `run._main`): a start row
   before every host launch and an end row after it. Covers the three launch paths: the first launch or `--resume-run`, the fresh
   session after `--interrupt-at`, a Grok or Codex resume inside the run.
3. `metrics.reorientation`: a pure function over one session's events from a fresh start to the next accepted action.
4. `fresh_starts` in `metrics.json`: one block for every fresh start and every compaction (Grok's `auto_compact_completed`; Codex's from
   its rollouts), with `fresh_starts_unmeasured` where `sessions.jsonl` is missing.
5. Two `per_stage` corrections (a stage with no events has no `context`; a Grok usage event is a model call).
6. A README section "A fresh context (S-6)": what is recorded, and the recipe for the S-6 pair (a watcher that creates `<output>/stop`,
   then `--resume-run`), whose watcher a test runs.

Not built, on purpose: `--clear-at`, `ClearTrigger`, the kill and relaunch logic, the `accepted_files` sha256 compare, the extra
snapshot fields (`files_written`, `progress_on_disk`, `result_written`, `improve_active`, `batch`), a redo measure, any verdict. See
section 8.

## 2. Reconciliation with the earlier deferral

The README ("A stop that names a stage (`--stop-at`) is deferred ... an external watcher that creates the file when a stage's row
appears covers it meanwhile") and the LEARNINGS "Not built, and why" entry deferred a stage-named trigger and its overshoot field.
**Phase 1 does not reverse that deferral.** The watcher recipe is the documented path, and it is how r2, r3 and the four Luna xhigh
resumes became probes by accident. Phase 2 (`--clear-at`) is built only if the first live probes show that the stop file's overshoot
(its 2 s poll, so up to about 2.25 s) or the two-invocation procedure is inadequate. The README sentence that records the deferral now
points at the recipe; the SPEC amendment states the same in its Dispositions.

## 3. What each part measures, and how to read it

**`sessions.jsonl` (firm: through-main tests with the harness's own fake Claude, Grok and Codex hosts).** Why the harness writes it:
the host's events cannot give session boundaries (Grok repeats `available_commands`; the saved r3 run has 237 in a two-session run, r2
has 74, and a `--resume-run` overwrites `result.json`, so the invocation before it left no session list). A start row is on disk before
the host runs (tested by patching `run.launch` to raise: the row is there, and an end row `status: crashed` follows). `told` holds the CLI and
run directory the resume prompt named, as values, because `ClaudeHost.argv` passes its prompt in `-p` and writes no prompt file
(`run.resume_told`, cross-checked against `run.resume_prompt` in a test). The end row carries `engine`, the ledger as it stands at that
moment (`metrics.engine_position`: status, stage, revision, how many actions are accepted, the newest one's stage and action). The start
row carries the same, read before the host starts. A harness killed with its host leaves a start row with no end row.

**`metrics.reorientation` (firm for the definitions, pinned by tests; the figures are in section 4).** Over the events from the fresh
start, it returns `tool_calls`, `seconds`, `seconds_to_accept_stamp`, `accepted {stage, action}`, `first_grounding` (`next`, `packet`,
`other`, or null) with `calls_before_grounding`, `recovery`, `failures`, `rewrote`, `asked_user`.

- *The window ends at the tool call that submitted the accepted action.* A `complete` or `improve-complete` that names an action id the
  ledger accepted, that did not fail, and that does not begin after the accept stamp's second. The engine's stamp is whole-second
  truncated, so a cut at the stamp loses the submitting call (it starts after the truncated stamp: 1003.7 against 1003.0 in the
  pinned test) and a cut at stamp+1 keeps the next call (1003.9). A packet read that merely names the pending action, a resubmission
  of an action accepted before the session began, and a refused `complete` are not the end. `seconds` runs to the submitting call on
  the runner's clock; `seconds_to_accept_stamp` runs to the engine's stamp (good to a second). Both are recorded because the two
  recorded samples were quoted on different clocks (r2: the stamp, r3: the call).
- *`first_grounding`* is the first call that asks ShipLoop where the run stands: `next`, a read of a packet file, or another ShipLoop
  verb. A read of the skill card is not grounding (r3 read SKILL.md first, then ran `next`: `calls_before_grounding` 1).
- *`recovery`*: whether the first `next` was repeated as told. `cli` and `run_dir` are `exact`, `equivalent` (the same place after
  normpath and realpath: the recorded Luna `/./` ran with exit 0), `different` or `unreadable` (a relative path or an unexpanded
  variable cannot be compared; it is never called different). `failed`, `exit`, `next_calls`, and `revision_seen` (the engine
  revision the first `next` that returned a packet printed).
- *`rewrote` is a lower bound.* Paths a file-edit tool (write, edit, replace, create) wrote both in the SAME stage's pre-start portion
  (since the previous accepted action's stamp) and in the window. An empty list reads `none seen by file-edit tools`, never a measured
  none: Claude writes most files by shell (r2's sixth call writes the result file with `cat > ... <<EOF`). Window `failures` are a
  lower bound too (a wrapper script written in an earlier session is not known to the window).
- A window that reaches no accepted action is `measured: false` with its reason and **no count**; it keeps `first_grounding` and
  `recovery`, which do not need an accept.

**`fresh_starts` (firm: fixture tests over r2, r3 and Luna; Codex placement checked against two saved runs, section 10).** Entries are
ordered by first event. Each window stops at the next recorded session start (Codex numbers its calls `item_1` in every session, so a
window must not read into the next one; a test with three sessions shows session 2's window would end at session 3's `complete`
without the bound). `after_kill` (fresh starts only) sets three engine revisions beside each other: the killed session's end row, this
session's start row, and the first `next` result it got; `moved` is true when they differ and null while fewer than two are known. It
replaces the design's invented 1 s `settled` wait (audit correction 11): a `complete` already started in a Claude Bash call (its own
process group) can finish after the host's group kill, and the comparison sees it.

**`per_stage` (firm: four tests, one is the old `MixedHostTurnsTest` behaviour restated).** `context` is emitted only for a row that
holds an event, and a Grok `usage` event sets `call` (as `model_calls` already counted it), so a Grok stage row has `calls` and `peak`
(`peakPct` null: Grok reports no window) and a mixed-host run counts both hosts' calls. Before, the r2 stages accepted by an orphan Grok
host with no events carried `{calls: 0, peak: null}`, and a Grok stage of a mixed run showed `calls: 0` beside a real peak.

## 4. Evidence: the three accidental probes, recomputed

Reproduced from compact extracts (`test/fixtures/reorientation/`, real line numbers and runner stamps; `sessions.jsonl` reconstructed
because the runs predate it). They are accidental probes and **not clean samples**: r3's old Grok session went silent at an unfinished
`auto_compact_started` (events line 4120, no completed event) for 126 s before the resume; r2's 1933 s gap contains stages accepted by
an orphan Grok host that wrote no events. They pin the measure, not an expectation.

| Sample | Design / audit text | Recomputed | Note |
|---|---|---|---|
| `20261008/r3-battleship-grok-none`, Grok resume at events line 4121 (test-author) | 23 calls, 164 s | 23 calls; 163.2 s to the `complete` call; 164.0 s to the accept stamp | SKILL.md first, `next` second; recovery exact; 0 failures; the old session had edited `rules.js`, `server.js` and two test files in this stage, the fresh one wrote notes only: `rewrote` none seen |
| `20261008/r2-battleship-grok-none`, Claude fresh start at line 2704 (implement) | 7 calls, 23 s | **6 calls**; 21.8 s to the `complete` call; 22.7 s to the stamp | next, packet Read, ls, cat, lint, complete; the 7th call is 3 s after the accept; mixed-host run (Grok began, Claude finished) |
| `20261005/v1210-battleship-luna-xhigh`, four fresh sessions | "3 of 4 first `next` mistyped" | **2 of 4 failed** (exit 2, "no ShipLoop run directory"), 1 exact, 1 equivalent (`/./`) | the failing run directories were a doubled `20261005/` and a truncated `1210-battleship...`; the CLI was typed right all four times; the windows are unmeasured in the extract (it holds only each start) |

One further finding: the first Grok compaction in r3 (events line 1536) is followed by 29 calls and 326.7 s to the test-strategy accept,
the model never ran `next` (it read the packet by its path), and its first call was that packet read; the second (line 8341) has no
accepted action after it, so it is unmeasured, and its first call was a read of SKILL.md.

## 5. The first measure of the main tenet in action: the first call after a compaction (status: interim)

SPEC S-6 says to assume the previous context is gone. A compaction is the one place the recorded runs show that happening to a model
that carries on. `docs/experiments/reorientation-20261009/measure.py` runs the harness's own `metrics.collect` on the saved runs and
keeps one row per compaction (`compactions.json`). A prototype over three Grok runs had found the first call after a compaction was a
packet read in 6 of 12; recomputed:

| Runs | Compactions | First call after the compaction | First grounding call |
|---|---|---|---|
| prototype set: r1, r3, v1230 Grok | 12 | **packet read 6**, other 4, skill card 1, `next` 1 | packet 8, other 2, `next` 1, none 1 |
| all six Grok runs on disk | 23 (21 measured) | packet 10, other 8, `next` 4, skill card 1 | packet 16, `next` 3, other 3, none 1 |
| all four Luna runs with rollouts | 60 (58 measured) | other 42, packet 9, `next` 7, skill card 2 | packet 35, other 14, `next` 11 |

Per run, first call (packet / next / other / skill card): v1210 Grok 1/2/2/0; v1220 Grok 3/0/2/0; v1230 Grok 2/1/3/0; r1 Grok 3/0/1/0; r2
Grok 0/1/0/0; r3 Grok 1/0/0/1; Luna `20261003/battleship-luna` 1/0/6/0; `20261003/v1161-battleship-luna` 5/5/22/2; `20261004/v1200-
battleship-luna` 0/0/1/0; `20261005/v1210-battleship-luna-xhigh` 3/2/13/0.

Reading it. (1) A packet read is the commonest first call after a Grok compaction, in about half the cases, and the commonest first
grounding call on both hosts; it is not universal, and on Codex the first call is usually something else (a shell command, `git
status`). (2) **The SPEC's S-6 evidence line does not reproduce literally.** It says that after each of the 5 compactions in the
2026-10-06 Grok run the model's first call was to re-read the current packet. The v1220 run has 5 compactions; the first call
touches the packet in 3 of 5 (two reads and a grep, events lines 1716, 8708 and 10327), and the packet is the first grounding call
in all 5 but after 0, 0, 0, 3 and 4 other calls (a test run, a scratch read, a grep of the packet). The line holds as "the model
re-grounded on the packet within a few calls", not as "its first call". The SPEC text is left as it stands (it is the owner's evidence statement; this is a finding for
the owner and for Run Review, not an edit made here). (3) A compaction keeps a summary, so it is a weaker clear than a new session;
and the measure says what the model did first, not whether it redid work: `rewrote` is non-empty in 4 of 21 measured Grok windows and
24 of 58 Codex windows, but a stage that builds a file over several edits rewrites it legitimately, so `rewrote` is a candidate
signal for a later redo measure and not a redo count. (4) Window sizes, for scale only: Grok 1 to 117 calls (median 31), 8.9 s to
2102.7 s (median 234.9 s); Codex 3 to 362 calls (median 47.5), 18.0 s to 9278.1 s (median 743.1 s).

## 6. The audit's corrections, and what became of each

| # | Correction | Disposition |
|---|---|---|
| 1 | The engine-record verdict cannot fail live; do not call it "no redone work"; rename | Implemented by not building it: no verdict field exists. The SPEC reserves the name `continuity` (necessary, not sufficient for S-6) and says "shows no redone work" stays a reader's judgement |
| 2 | `pass: null` must not read as PASS | Moot in phase 1 (no verdict). The SPEC states the rule; every unknown here is `measured: false` or null with a reason |
| 3 | `told` as values; normpath and resolve | Implemented: `run.resume_told`, the start row; `_same_path` (exact, equivalent, different, unreadable) |
| 4 | Fix the fixture expectations | Implemented: the figures of section 4 come from the fixtures; Luna "two failed, one equivalent, one exact"; the window-end rule pinned in `WindowEndRuleTest` |
| 5 | `rewrote` a lower bound, the same stage's pre-start portion; window failures too | Implemented: `bound: lower` and a scope string on both |
| 6 | Test-suite budget | Implemented: `test/shiploop-e2e-reorientation.test.py`, registered with a measured duration and the `test/shiploop_e2e/` footprint; `test/shiploop-e2e.test.py` gets no new test (one existing assertion edited, section 7) |
| 7 | Reconcile the `--stop-at` deferral | Section 2 |
| 8 | Trim the verdict apparatus | Implemented by not building the sha256 compare, the snapshot fields or any verdict |
| 9 | Compactions as passive rows | Implemented (Grok events, Codex rollouts; Claude's not detected, no recorded stream shows one) |
| 10 | End rows with engine revision and last accepted action | Implemented (and the start row carries the engine too) |
| 11 | Replace the invented 1 s `settled` wait | Implemented as `after_kill`: three revisions compared, nothing waited for. K and the `:result` default are `--clear-at` questions, not built |
| 12 | Specify the probe command | Implemented in the README: `--prompt` plus `--check` (not `--case hello --prompt`), `--planning-review none` with an absolute `--improve-skill`, a `none` probe never inside an Improve park |
| 13 | State what the probe tests; label r2 and r3 non-clean | In the SPEC amendment and the README |
| 14 | Sequence with concurrent work | Not rebased (base is the plan commit). Phase 1 reads no store output and takes no snapshot, so the store's rehydration and recovery text does not enter; `revision_seen` parses the packet head `ShipLoop navigator | <stage> | revision N` and reads null if that line changes |

Missed unknowns of the audit: the SIGKILL final newline is fixed (`run.events_line_count`, 3 tests). Keepalive ownership surviving the
kill, Claude's auto-memory and the global `CLAUDE.md` are not removed or recorded: the SPEC and README label them (memory and
`CLAUDE.md` load into both sessions; the old session's servers are reaped). `CLAUDE_CODE_DISABLE_AUTO_MEMORY` stays unset (its effect
is unverified and it belongs to a probe-only session in phase 2).

## 7. Deviations from the design, and why

- `fresh_starts_unmeasured` is a sibling key, not an entry in the top-level `unmeasured` map: many existing tests assert that map
  exactly and a run from before the record is the common case; the `planning` block already keeps its own reasons apart. (SPEC
  corrected in its own commit.)
- The start row carries `engine` (the design had only the end row): it makes the kill-versus-launch comparison possible and costs one
  ledger read.
- `reorientation` takes lazily read `(line, event)` rows and an `earlier` callable, not `(events_path, stamps, start_line, end_line,
  told)`: it stops reading at the window's end, stays pure, and the caller owns the file.
- No `continuity`, `clear_probe`, `clear.json`, snapshot or hash compare (phase 2 and audit correction 8).
- `rewrote.paths` is null (not `[]`) with a reason when the earlier portion or the previous accept stamp is unknown.
- One existing assertion edited: `test/shiploop-e2e.test.py :: CodexRolloutMetricsTest.test_rollouts_are_not_read_when_the_host_reported_per_call_usage`
  asserted that no Grok stage row has a `context` at all. It now asserts the row carries the stream's own two calls and none of the
  rollouts' figures (what the test was written to show). `MixedHostTurnsTest` is untouched and green.

## 8. Deferred, and what would decide it

`--clear-at` and its kill: only if the first live probes show the overshoot or the two-invocation procedure inadequate. The redo
measure: after three live probes, from `rewrote` candidates and repeated-command candidates. `continuity`: only with a trigger that
takes a snapshot. The Claude memory switch, a record of keepalive ownership at the clear, the `inside:<stage>:K` placement, a clear
inside an Improve child, the `probes.jsonl` history and the bare-prompt variant (dropped by the audit). The Grok `unreported_sessions`
count (`available_commands` counted as session starts, 237 in r3): it belongs to the identity and variance group (G3); with
`sessions.jsonl` it is a one-line fix there.

## 9. The data shapes the Run Review session reads

All additions are optional; nothing existing changes shape except the stage rows noted last.

`<output>/sessions.jsonl` (one object per line; values from a fake Grok run through `run.main`, paths shortened to `<tmp>`):

```json
{"row": "start", "n": 1, "kind": "first", "reason": "start", "host": "grok", "model": "grok-4.7", "t": 1791564725.379, "events_line": 0, "told": null, "resumed_session": null, "engine": null}
{"row": "end", "n": 1, "t": 1791564725.428, "events_line": 5, "status": "exited", "returncode": 0, "engine": {"status": "active", "stage": "test-refine", "revision": 25, "accepted": 0, "last_accepted": null}}
{"row": "start", "n": 2, "kind": "continued", "reason": "resume-loop", "host": "grok", "model": "grok-4.7", "t": 1791564725.429, "events_line": 5, "told": {"cli": "<tmp>/build/plugins/skill-craft/skills/shiploop/scripts/shiploop", "run_dir": "<tmp>/out/work/.shiploop"}, "resumed_session": "sess-1", "engine": {"status": "active", "stage": "test-refine", "revision": 25, "accepted": 0, "last_accepted": null}}
```

`kind` is `first`, `fresh` (a new host session, no host session id passed) or `continued`; `reason` is `start`, `resume-run`,
`after-interrupt` or `resume-loop`. The saved runs' reconstructed rows carry `"reconstructed": true` and no end rows.

`metrics.json["fresh_starts"]` (values from `r3-battleship-grok-none`, the Grok resume at events line 4121):

```json
{"kind": "fresh", "n": 2, "reason": "resume-run", "host": "grok", "t": 1791528536.0, "events_line": 4121, "stage_in_flight": "test-author",
 "after_kill": {"end_revision": null, "start_revision": null, "first_next_revision": 11, "moved": null},
 "reorientation": {"measured": true, "accepted": {"stage": "test-author", "action": "nav-6d27b38fd69a48d094421df530fc3828"},
  "tool_calls": 23, "seconds": 163.2, "seconds_to_accept_stamp": 164.0, "first_grounding": "next", "calls_before_grounding": 1,
  "recovery": {"told": {"cli": "<run>/home/.grok/installed-plugins/skill-craft-f132a56c/skills/shiploop/scripts/shiploop", "run_dir": "<run>/.shiploop-runs/work-20261009-062034-d142b0/run"},
               "next_calls": 1, "first_next": {"call": 2, "failed": false, "exit": null, "cli": "exact", "run_dir": "exact"}, "revision_seen": 11},
  "failures": {"items": [], "bound": "lower", "scope": "the window's own calls only: a ShipLoop command run through a script written in an earlier session is not seen"},
  "rewrote": {"paths": [], "bound": "lower", "scope": "none seen by file-edit tools"}, "asked_user": 0}}
```

A compaction entry has `"kind": "compaction"`, `n` and `reason` null, no `after_kill`, and `recovery.told` null. An unmeasured window
(`r3` line 8341): `"reorientation": {"measured": false, "reason": "no tool call submitted an action accepted after this start ...",
"first_grounding": null, "calls_before_grounding": null, "recovery": {"told": null, "next_calls": 0, "first_next": null, "revision_seen": null}}`,
and `"stage_in_flight": null`; it has no `tool_calls`, `seconds`, `failures` or `rewrote`. `first_next.cli` and `run_dir` are `exact |
equivalent | different | unreadable`, null when `told` is null. `moved` is a boolean or null (fewer than two revisions known).
`metrics.json["fresh_starts_unmeasured"]`: null, or `"not recorded: this run has no sessions.jsonl ..."` (then the list holds compactions
only), or `"failed: <Type>: <message>"` (the passive record failed and the rest of the metrics are intact). Every `fresh_starts` figure
is record-only: not printed, not scored, not in `result.json`, not in a baseline row. Lower-bound markers to show on the page:
`failures.bound` and `rewrote.bound` are `lower`; a mixed-host run keeps `host` per entry (r2's fresh start is `claude`).

Stage rows (`metrics.json["stages"][i]`): `context` is now absent for a row with no event (it was a zero-call context) and present for
Grok rows (`{"calls": n, "peak": tokens, "peakPct": null}`), with Claude rows and Codex rollout rows unchanged. The Run Review exporter
matches stage rows to visits by position and tolerates a missing `context`.

## 10. Open risks, and what could not be verified

- No live probe has run. `sessions.jsonl` has been written only by the harness's fake hosts; a real Claude, Grok or Codex session has
  not produced one. The first live S-6 pair is the check.
- Codex compactions are placed by joining the rollouts' clock to the runner's stamps. Counts agree on the two saved runs checked
  (`20261003/battleship-luna`: 7 listed against 7 counted; `20261003/v1161-battleship-luna`: 34 against 34), and the windows are
  plausible, but where the first call after a Codex compaction really falls is unverified against a live run.
- Claude compactions are not detected (no recorded stream shows one; `GROK_SIGNALS` says so), so a Claude run lists fresh starts only.
- A window is recognised by the submitting command's own text. A model that submits through a script written in a session the window does not
  see is not recognised: the window is then unmeasured (never wrong), and `failures` misses the same calls (the lower bound).
- `revision_seen` depends on the packet head format; a changed head reads as unknown.
- `rewrote` is not redo (section 5). The signal is a candidate for the later redo measure and must not be quoted as a regression.
- `test/shiploop-e2e.test.py` measures about 118 to 121 s locally against `QUICK_MAX_SECONDS` 120 at load average 7 to 8 (404 tests, all
  green); this group adds about 1 ms of ledger reading per `run.main` (three `grade_shiploop` calls of 0.4 ms each) and no test to it.
- Merge: conflicts are expected in `SPEC.md`, `LEARNINGS.md`, `run.py`, `metrics.py`, `suite_catalog.py` and `test-groups.test.py`; keep
  both sides. The pinned counts in `test-groups.test.py` here are 71 ShipLoop suites and 112 in all.

## 11. Tests and commands

New file `test/shiploop-e2e-reorientation.test.py`: 79 tests in 17 classes, 7.6 s locally. Every behaviour has a test that failed first for
the right reason; spot-checked red by breaking the code: the plausibility check, the refused `complete`, equivalence collapsed to
different, `&` turned `|`, first grounding never `next`, the session bound removed, the not-recorded label removed, session kinds
unfiltered, the rollouts' `compaction_times` emptied, the Grok-only guard removed, the revision capture removed, `moved` collapsed, the
start row's engine dropped, the newline repair, the after-interrupt kind, the resume-run `told`, the passive record's `try`, the
row filter, the `told` type check, the per-stage `events and` and the Grok `call` flag, and three clauses of the README watcher. One
survived and was removed as redundant (`key not in tools.failed` in `_recovery`: a failed `next` prints no packet head). Another
survived because two checks covered each other and was simplified to the one that mattered (`_plausible_submission`).

Final runs on the finished tree (head `4df8ad78` plus this journal), `SHIPLOOP_PROGRESS=off`, load average 7 to 8:

| Command | Result |
|---|---|
| `python3 test/shiploop-e2e-reorientation.test.py` | 79 tests, OK, 7.6 s |
| `python3 test/shiploop-e2e.test.py` | 404 tests, OK, 111.9 s (the first run after the per-stage change had 1 failure, the Codex-rollout assertion edited in section 7; a later run was 118.5 s and one at 120.7 s under heavier load) |
| `python3 test/shiploop-e2e-runrecord.test.py` | 6 tests, OK |
| `python3 test/test-groups.test.py` | 21 tests, OK (71 ShipLoop suites, 112 in all) |
| `bash test/run-all.sh --group quick --changed-from 30a3b40a` | PASS, 31 suites, all OK (receipt kept outside the checkout); run on the tree before commit `4df8ad78`, which changed only `run._main`'s fail-open `engine_now`, the fixtures' state files and one README sentence; the four suites above were rerun after it |

## 12. Commits (base `30a3b40a`)

`e8a1787c` SPEC amendment; `10191f97` `ToolLog.feed` and the registered test file; `47d80d3a` `sessions.jsonl`; `84ee4eb4`
`metrics.reorientation` and the fixtures; `29361db7` `fresh_starts`; `6a5dc5cb` the per-stage corrections; `4cc0fa4d` the README recipe;
`e9792be9` SPEC correction; `29386693` hardening and the registered duration; `4df8ad78` fail-open ledger read, slimmer fixtures, a README sentence; this journal, the LEARNINGS entry and `docs/experiments/reorientation-20261009/`.
