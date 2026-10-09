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

**Fix round (2026-10-09, after two adversarial reviews of `3ea72361`): section 13.** It supersedes what sections 3, 5, 9, 10 and the
first journal commit said about where a window ends and about the compaction figures: the first build ended a window at the first
call that named the next accepted action, which under Improve is the call that only parks it, and it did not bound a window by
session in a run with no `sessions.jsonl`. Those sections are corrected in place; section 13 says how many windows moved and why.

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
(the watcher's 0.5 s poll plus the harness's 2 s one, about 2.5 s; the first version said 2.25 s) or the two-invocation procedure is inadequate. The README sentence that records the deferral now
points at the recipe; the SPEC amendment states the same in its Dispositions.

## 3. What each part measures, and how to read it

**`sessions.jsonl` (firm: through-main tests with the harness's own fake Claude, Grok and Codex hosts).** Why the harness writes it:
the host's events cannot give session boundaries (Grok repeats `available_commands`; the saved r3 run has 237 in a two-session run, r2
has 74, and a `--resume-run` overwrites `result.json`, so the invocation before it left no session list). A start row is written once
launch's own checks have passed and just before the host is spawned (`launch(before_start=...)`, which hands over the very line count
launch took; a launch refused before any host ran leaves no row; a launch that raises after it leaves an end row `status: crashed`). `told` holds the CLI and
run directory the resume prompt named, as values, because `ClaudeHost.argv` passes its prompt in `-p` and writes no prompt file
(`run.resume_told`, cross-checked against `run.resume_prompt` in a test). The end row carries `engine`, the ledger as it stands at that
moment (`metrics.engine_position`: status, stage, revision, how many actions are accepted, the newest one's stage and action). The start
row carries the same, read before the host starts. A harness killed with its host leaves a start row with no end row.

**`metrics.reorientation` (firm for the definitions, pinned by tests; the figures are in section 4).** Over the events from the fresh
start, it returns `tool_calls`, `seconds`, `seconds_to_accept_stamp`, `accepted {stage, action}`, `first_grounding` (`next`, `packet`,
`other`, or null) with `calls_before_grounding`, `recovery`, `failures`, `rewrote`, `asked_user`.

- *Which action, and which call.* The action a window waits for is the FIRST the ledger accepted after the start (the start row's
  `engine.accepted` names it exactly; without it, the first one stamped at or after the start's second; an unstamped row that could be
  the next one makes the window not measured, and an accept in the start's own second taken for the next one makes it not measured
  because its submission is then not found: safe, not wrong). The window ends at the LAST `complete` or `improve-complete` that names
  it, did not fail, began before its accept stamp's second ended and returned at or after the stamp. The engine's stamp is
  whole-second truncated, so a cut at the stamp loses the call (it starts after the truncated stamp: 1003.7 against 1003.0 in the
  pinned test), a cut at stamp+1 keeps the next one (1003.9), and an Improve park's parent `complete`, which returns long before the
  accept, is not the call (Luna xhigh line 157: the first build read 3 calls and 18.0 s for an accept 2730.4 s after the start; the rule
  reads 114 calls and 2730.7 s). A packet read that merely names the pending action, a resubmission after the accept, and a refused
  `complete` are not the end. `seconds` runs to the call on the runner's clock; `seconds_to_accept_stamp` runs to the engine's stamp (good
  to a second). Both are recorded because the two recorded samples were quoted on different clocks (r2: the stamp, r3: the call).
- *What is not measured.* A window the records cannot place is `measured: false` with its reason and is never extended to a later
  action: the action was accepted by something that left no event (an orphan host), by a script the window does not see or by an id the
  command reads from a file (reviewer B's probe cases A and B, which the first build measured across two stages); only a call that
  parked it was seen ("parked"); no later accept exists; an accepted action after the start has no stamp; or, in a run whose sessions
  are not recorded, another launch began (runrecord.launch_epochs, the one reader of the launch records) or a host `end`, `result` or
  Claude `init` event stands inside the window ("session bounds not recorded"). That last rule is conservative on purpose: a Grok `end`
  followed by `--resume` keeps the context, but an unrecorded run cannot say which it was, so r1's compaction at 9512 (a window that
  holds an `end` event) is left unmeasured; with a `sessions.jsonl` the `continued` row says it was the same context and the window
  stays measured.
- *`first_grounding`* is the first call that goes to ShipLoop's scripts or reads a packet (it submits or asks, it is not only a question):
  `next`, `improve-next` (the Improve runtime's own recovery command, `until_loop_ephemeral.py next`), `packet`, or `other` (another
  ShipLoop verb: `complete`, `lint`, an `improve-*` verb). A read of the skill card is not grounding (r3 read SKILL.md first, then ran
  `next`: `calls_before_grounding` 1). The classifier is `metrics.call_kind`, and the evidence script calls it.
- *`recovery`*: whether the first `next` was repeated as told. `cli` and `run_dir` are `exact`, `equivalent` (the same place after
  normpath and realpath: the recorded Luna `/./` ran with exit 0), `different` or `unreadable` (a relative path or an unexpanded
  variable cannot be compared; it is never called different). `failed`, `exit`, `next_calls`, and `revision_seen` (the engine
  revision the first `next` that returned a packet printed).
- *`rewrote` is a lower bound.* Paths a file-edit tool (write, edit, replace, create) wrote both in the SAME stage's pre-start portion
  (since the previous accepted action's stamp) and in the window. An empty list reads `none seen by file-edit tools`, never a measured
  none: Claude writes most files by shell (r2's sixth call writes the result file with `cat > ... <<EOF`). Window `failures` are a
  lower bound too (a wrapper script written in an earlier session is not known to the window).
- An unmeasured window has **no count**: no `accepted`, `tool_calls`, `seconds`, `seconds_to_accept_stamp`, `failures`, `rewrote` or
  `asked_user`; it keeps `measured`, `reason`, `first_grounding`, `calls_before_grounding` and `recovery`, which do not need an accept.

**`fresh_starts` (firm: fixture tests over r2, r3 and Luna; Codex placement unverified against a live run, section 10).** Entries are
ordered by first event. Each window stops at the next recorded FRESH start, and a `continued` session does not cut it (it keeps the context); call ids are
scoped by session inside a window (Codex numbers its calls `item_1` in every session, a continued one included), and a test with three
sessions shows session 2's window would end at session 3's `complete` without the bound. `after_kill` (fresh starts only) sets three engine revisions beside each other: the killed session's end row, this
session's start row, and the first `next` result it got; `moved` is true when they differ and null while fewer than two are known; it means the engine moved between the kill and the fresh
session's first `next`, which a command of the killed session still running can do, an orphan host can, and so can the fresh
session's own ShipLoop calls before that `next` (an `improve-bind` increments the revision). It
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
keeps one row per compaction (`compactions.json`, regenerated in the fix round). A prototype over three Grok runs had found the first
call after a compaction was a packet read in 6 of 12; recomputed, with the harness's one classifier (`metrics.call_kind`):

| Runs | Compactions | First call after the compaction | First grounding call |
|---|---|---|---|
| prototype set: r1, r3, v1230 Grok | 12 (9 measured) | **packet read 6**, plain 3, skill card 1, other ShipLoop verb 1, `next` 1 | packet 8, other verb 2, `next` 1, none 1 |
| all six Grok runs on disk | 23 (19 measured) | packet 10, plain 7, `next` 3, `improve-next` 1, other verb 1, skill card 1 | packet 14, `next` 3, other verb 3, `improve-next` 2, none 1 |
| all four Luna runs with rollouts | 60 (50 measured) | plain 40, packet 9, `next` 6, skill card 2, other verb 2, `improve-next` 1 | packet 33, other verb 10, `next` 9, `improve-next` 8 |

("Plain" is a call that is not a ShipLoop call and reads no packet or skill card: a test run, `git status`, a scratch read.) The first
call and the first grounding call need no accept, so those two columns count all compactions; the rest of this section counts measured
windows only.

Per run, first call (packet / `next` / `improve-next` / other verb / skill card / plain) and measured windows: v1210 Grok 1/1/1/0/0/2 and 5
of 5; v1220 Grok 3/0/0/0/0/2 and 5 of 5; v1230 Grok 2/1/0/0/0/3 and 5 of 6; r1 Grok 3/0/0/1/0/0 and 3 of 4; r2 Grok 0/1/0/0/0/0 and 0 of 1; r3
Grok 1/0/0/0/1/0 and 1 of 2; Luna `20261003/battleship-luna` 1/0/0/0/0/6 and 7 of 7; `20261003/v1161-battleship-luna` 5/4/1/2/2/20 and 33
of 34; `20261004/v1200-battleship-luna` 0/0/0/0/0/1 and 0 of 1; `20261005/v1210-battleship-luna-xhigh` 3/2/0/0/0/13 and 10 of 18.

Reading it. (1) A packet read is the commonest first call after a Grok compaction, in about half the cases, and the commonest first
grounding call on both hosts; it is not universal, and on Codex the first call is usually something else. (2) The Improve runtime's own
recovery command is a real first grounding call (Grok 2, Luna 8), which the first build did not recognise (v1210 Grok at events
line 1305 and v1161 Luna at 4606 recorded 32 and 77 calls before grounding for windows whose first call was it).
(3) **The SPEC's S-6 evidence line does not reproduce literally; this is an owner finding, and the SPEC line is not edited in G2.** It
says that after each of the 5 compactions in the 2026-10-06 Grok run the model's first call was to re-read the current packet. The
v1220 run's 5 compactions complete at lines 1681, 4279, 6917, 8659 and 10303; the first calls after them are a packet read, `node
--test`, a `test -f` and a scratch tail, a grep of the packet and a packet read. So the first call touches the packet in 3 of 5 and
re-reads it in 2 of 5, and the packet is the first grounding call in all 5, after 0, 4, 3, 0 and 0 other calls. Proposed replacement
for the evidence line: "re-grounded on the packet within at most 4 calls; the first call touched it in 3 of 5". (4) A compaction keeps
a summary, so it is a weaker clear than a new session; and the measure says what the model did first, not whether it redid work:
`rewrote` is non-empty in 5 of 19 measured Grok windows and 23 of 50 Codex windows, but a stage that builds a file over several edits
rewrites it legitimately, so `rewrote` is a candidate signal for a later redo measure and not a redo count. (5) Window sizes, for scale
only: Grok 1 to 139 calls (median 42), 8.9 s to 1096.0 s (median 326.7 s); Codex 7 to 484 calls (median 75.5), 43.1 s to 11674.2 s
(median 1111.7 s). The first build recorded Grok 1 to 117 calls, 8.9 s to 2102.7 s and Codex 3 to 362 calls, 18.0 s to 9278.1 s; those
ranges, both medians and the rewrote counts (4 of 21 and 24 of 58) were wrong for the reasons in section 13.

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
| 12 | Specify the probe command | Implemented in the README: `--prompt` plus `--check` (not `--case hello --prompt`), `--planning-review none` with an absolute `--improve-skill`, a `none` probe at a planning stage never inside an Improve park (the later Improve children still run: the saved v1220 `none` run parked at system-test-author, release-plan and carry-forward) |
| 13 | State what the probe tests; label r2 and r3 non-clean | In the SPEC amendment and the README |
| 14 | Sequence with concurrent work | Not rebased (base is the plan commit). Phase 1 reads no store output and takes no snapshot, so the store's rehydration and recovery text does not enter; `revision_seen` parses the packet head `ShipLoop navigator | <stage> | revision N` and reads null if that line changes |

Missed unknowns of the audit: the SIGKILL final newline is fixed (`run.events_line_count`, 3 tests). Keepalive ownership surviving the
kill, Claude's auto-memory and the global `CLAUDE.md` are not removed or recorded: the SPEC labels the memory and `CLAUDE.md` (they load
into both sessions; the old session's servers are reaped) and, from the fix round, the README names the keepalive owner binding
(`home/.local/state/shiploop/keepalive`, `OWNER_STALE_SECONDS` 1800), which the first version of this journal wrongly said both
documents already did. `CLAUDE_CODE_DISABLE_AUTO_MEMORY` stays unset (its effect
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
- The start row is written inside `launch` (`before_start`), not by the `session()` closure before calling it (fix round, item 16).
- `fresh_starts_unmeasured` is a list of notes joined with "; " (not recorded / partial / compactions not detected / failed), and it is
  no longer None for a Claude run or a Codex run without rollouts, whose compactions are not detected.
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
(`r3` line 8341): `"reorientation": {"measured": false, "reason": "the ledger accepted no action after this start",
"first_grounding": null, "calls_before_grounding": null, "recovery": {"told": null, "next_calls": 0, "first_next": null, "revision_seen": null}}`,
and `"stage_in_flight": null`; it has no `accepted`, `tool_calls`, `seconds`, `seconds_to_accept_stamp`, `failures`, `rewrote` or `asked_user`
(its `reason` is one of: the ledger accepted no action after this start; an accepted action after it has no accept stamp; the next
accepted action was not submitted by a tool call this window recognises; every call that names it returned before its accept stamp
(parked); session bounds not recorded: <why>; the session wrote no event). `first_grounding` is `next`, `improve-next`, `packet`, `other`
or null. `first_next.cli` and `run_dir` are `exact |
equivalent | different | unreadable`, null when `told` is null. `moved` is a boolean or null (fewer than two revisions known).
`metrics.json["fresh_starts_unmeasured"]`: null, or notes joined with "; ": `"not recorded: this run has no sessions.jsonl ..."` (then the
list holds compactions only) or `"not recorded: sessions.jsonl exists but cannot be read ..."`; `"partial: sessions before events line N are
not recorded"` (a run begun before the record and then resumed); `"compactions not detected on this host: <reason>"` (Claude, a Codex run
without rollouts: an empty list is not a measured none); or `"failed: <Type>: <message>"` (the passive record failed and the rest of the
metrics are intact). Every `fresh_starts` figure
is record-only: not printed, not scored, not in `result.json`, not in a baseline row. Lower-bound markers to show on the page:
`failures.bound` and `rewrote.bound` are `lower`; a mixed-host run keeps `host` per entry (r2's fresh start is `claude`).

Stage rows (`metrics.json["stages"][i]`, which `result.json` copies into `metrics.stages`, so it changes with them): `context` is now absent for a row with no event (it was a zero-call context) and present for
Grok rows (`{"calls": n, "peak": tokens, "peakPct": null}`), with Claude rows and Codex rollout rows unchanged. The Run Review exporter
matches stage rows to visits by position and tolerates a missing `context`.

## 10. Open risks, and what could not be verified

- No live probe has run. `sessions.jsonl` has been written only by the harness's fake hosts; a real Claude, Grok or Codex session has
  not produced one. The first live S-6 pair is the check.
- Codex compactions are placed by joining the rollouts' clock to the runner's stamps. The listed counts equal the counted ones on the two
  saved runs read (`20261003/battleship-luna` 7 and 7, `20261003/v1161-battleship-luna` 34 and 34), but that proves nothing about the
  placement: both come from the same rollout records. Where the first call after a Codex compaction really falls is unverified against
  a live run.
- Claude compactions are not detected (no recorded stream shows one; `GROK_SIGNALS` says so), so a Claude run lists fresh starts only.
- A window is recognised by the submitting command's own text. A submission through a script written in a session the window does not see,
  or an id the command reads from a file, is not recognised: the window is then NOT MEASURED (the first build skipped such a call and ended
  the window at a later stage's submission, recorded as measured with that stage's calls: it was wrong, and the first version of this
  journal said "never wrong"), and `failures` misses the same calls (the lower bound).
- `revision_seen` depends on the packet head format; a changed head reads as unknown.
- `rewrote` is not redo (section 5). The signal is a candidate for the later redo measure and must not be quoted as a regression.
- `test/shiploop-e2e.test.py` measures about 118 to 121 s locally against `QUICK_MAX_SECONDS` 120 at load average 7 to 8 (404 tests, all
  green); this group adds three `grade_shiploop` calls per `run.main` (0.4 ms each on the fake folders the tests use, about 1 ms) and no test to it.
  On real output folders `grade_shiploop` (an rglob) takes 7 to 36 ms (here: r3 11.4 ms, v1220-sonnet 8.5 ms, luna-xhigh 29.9 ms; the
  reviewers measured 16.7, 21.6 and 36.1 ms), and `engine_now` calls it twice per host session (start row and end row): negligible
  against a session of minutes.
- Merge: conflicts are expected in `SPEC.md`, `LEARNINGS.md`, `run.py`, `metrics.py`, `suite_catalog.py` and `test-groups.test.py`; keep
  both sides. The pinned counts in `test-groups.test.py` here are 71 ShipLoop suites and 112 in all.

## 11. Tests and commands

New file `test/shiploop-e2e-reorientation.test.py`: 118 tests, 7.5 s locally (the faster of two serial runs at load average 6). Every
behaviour has a test that failed first for the right reason, and was spot-checked red by breaking the code. The first build was spot-checked by hand (about 25
mutations); the fix round runs the reviewer's own 49 mutations, adapted to the new code, plus 17 more for the new logic (66 in all: 64 apply to the final tree and all 64 are red, including the reviewer's M03, M18, M32, M33, M34, M41 and M47; M25 (a redundant early return, removed) has no pattern left, and N16 (the stop at the stamp's following second, an equivalent mutant) is pinned by a lazy-reading test and red). Two survived in the first build and were repaired then: `key not in
tools.failed` in `_recovery` (redundant; removed) and `_plausible_submission` (two checks covering each other; simplified, and now covered
by a resubmission test).

Final runs on the finished tree (the code at `261f5d11`; the journal, LEARNINGS entry and regenerated evidence follow in the last
commit), `SHIPLOOP_PROGRESS=off`, no exported `GIT_CONFIG_*` variable, load average 5 to 8:

| Command | Result |
|---|---|
| `python3 test/shiploop-e2e-reorientation.test.py` | 118 tests, OK, 7.5 s |
| `python3 test/shiploop-e2e.test.py` | 404 tests, OK, 112.1 s (the first run after the per-stage change had 1 failure, the Codex-rollout assertion edited in section 7; other runs took 111.9 s, 118.5 s and 120.7 s under heavier load) |
| `python3 test/shiploop-e2e-runrecord.test.py` | 6 tests, OK |
| `python3 test/test-groups.test.py` | 21 tests, OK (71 ShipLoop suites, 112 in all) |
| `bash test/run-all.sh --group quick --changed-from 30a3b40a` | PASS, 31 suites, all OK (receipt kept outside the checkout). Run on the code of `9a64f5aa`; the only change since is one test and one assertion in the reorientation file (`261f5d11`), which was rerun: 118 tests OK |

## 12. Commits (base `30a3b40a`)

First build: `e8a1787c` SPEC amendment; `10191f97` `ToolLog.feed` and the registered test file; `47d80d3a` `sessions.jsonl`; `84ee4eb4`
`metrics.reorientation` and the fixtures; `29361db7` `fresh_starts`; `6a5dc5cb` the per-stage corrections; `4cc0fa4d` the README recipe;
`e9792be9` SPEC correction; `29386693` hardening and the registered duration; `4df8ad78` fail-open ledger read, slimmer fixtures, a README
sentence; `3ea72361` this journal, the LEARNINGS entry and `docs/experiments/reorientation-20261009/`.

Fix round: `c8a1b7a9` SPEC and README corrections the code depends on (before the code); `61a0f799` window placement and the notes (items 1 to
5, 7); `3372a844` one classifier (items 8, 15); `18ba3984` the start row once launch's checks pass (item 16); `b1f60d1b` fixtures and
extract.py (items 6, 15); `9a64f5aa` the registered duration comment (item 17); `261f5d11` two tests that could not fail (M03 and the lazy read); then the regenerated evidence, this journal and the LEARNINGS
entry.

Order note (review item 18): the SPEC correction `e9792be9` came after code that diverged from the first amendment (`47d80d3a`, `29361db7`);
history is not rewritten. In the fix round the statement commit `c8a1b7a9` precedes the code that implements it.

## 13. The fix round (two adversarial reviews of `3ea72361`)

**What was wrong, in one paragraph.** The committed compaction evidence was false for 31 of the 79 windows recorded as measured.
Cause A (21 windows whose figures moved; the reviewers counted 26 windows ending at a park): under Improve the parent `complete` only parks
the action, and the first build ended the window there. Cause B (10 windows no longer measured; the reviewers counted 5, the launch
records find 5 more): in a run with no `sessions.jsonl` nothing bounded a window, so it crossed host sessions. A call the window did not recognise
was skipped, so the window ended at a later stage's submission (wrong stage, calls, seconds and rewrote), and a `continued` row cut
windows it should not have. All of it reproduced on the saved runs before any code changed.

**Regenerated evidence** (`compactions.json`, 83 compactions): 69 windows are measured and 14 are not. Of the 79 first recorded as
measured, 48 are unchanged, 21 stay measured with a new end (Luna xhigh line 157: 3 calls and 18.0 s became 114 calls and 2730.7 s), and
10 are no longer measured (8: another launch began inside the window; 2: a host `end` or `init` event stands inside it). The 4 first
recorded as not measured still are (3: the ledger accepted nothing after them; 1: session bounds). The 14 are therefore: 3 no later accept,
8 launch inside, 2 host end event, 1 host init event. Every figure in section 5 was recomputed (Grok 19 of 23 and Luna 50 of 60 measured;
the ranges, medians, `rewrote` counts and first-call counts changed as listed there).

| # | Item | Disposition |
|---|---|---|
| 1 | Windows ending at an Improve park; no session bounds without `sessions.jsonl` | Fixed: first-accept rule, last call that returned at or after the stamp, "parked", launch epochs and host end or init events (`metrics.reorientation`, `metrics.fresh_starts`, `runrecord.launch_epochs`); `WindowPlacementTest`, `SessionBoundsTest`, `UnrecordedSessionsTest`. Evidence regenerated, above. The README line on Improve parks corrected (planning stages only) |
| 2 | A `continued` row cut windows; Codex id reuse | Fixed: only the next fresh start bounds a window; call ids scoped by session; `ContinuedAndRecordedSessionsTest` |
| 3 | An unrecognised submission was skipped to a later stage | Fixed by the first-accept rule (`test_an_unrecognised_submission_is_not_skipped_to_a_later_stages_one`, reviewer B's cases A and B); the journal sentence "never wrong" corrected (section 10) |
| 4 | A run begun before the record then resumed looked complete; undetected compactions looked like none | Fixed: `partial` and `compactions not detected on this host` notes; `FreshStartsNoteTest` |
| 5 | An unreadable `sessions.jsonl` raised from `start` and from `collect` | Fixed: the read tolerates `OSError`, `collect` reads it inside its try; `test_an_unreadable_sessions_file_never_stops_a_launch_or_the_metrics` |
| 6 | The r2 fixture held no Grok event and no running updates | Fixed: the Grok tail around compaction 1900 and the running updates are kept; the test asserts two entries |
| 7 | Tests that could not fail (M03, M32, M18/M47, M33/M34, M41) | Fixed: one test each (a Grok placeholder update, the production wiring of `earlier`, both clauses of the row filter, a reused call id, the stage_in_flight fallback); all red under mutation |
| 8 | A second classifier; the Improve runtime's `next` unrecognised; wording | Fixed: `metrics.call_kind`, `improve-next`, `measure.py` calls it; "goes to ShipLoop's scripts or reads a packet" |
| 9 | The SPEC said `result.json` is unchanged | Fixed in the SPEC (own commit, before the code) |
| 10 | Keepalive ownership not in the README | Fixed: one README sentence; the journal row corrected |
| 11 | "up to about 2.25 s" | Fixed: the watcher's 0.5 s plus the harness's 2 s poll; the pinned number removed from the test |
| 12 | Timing measured on fake folders | Restated in section 10 |
| 13 | "Checked against the counts" checks nothing | Dropped in sections 3 and 10 |
| 14 | `after_kill.moved` has other causes | The README lists them; `revision_seen` stays the first `next` that returned a packet |
| 15 | S-12 duplicates | One packet-head regex; `extract.py` calls `tool_call_events` and `cancelled_update`; `sessionlog.py` and `runrecord.py` name each other |
| 16 | A refused launch left a `crashed` session | Fixed: `launch(before_start=...)`; `LaunchBookendsTest` and one through-main test |
| 17 | Duration comment | Fixed (118 tests, 7.7 s) |
| 18 | Commit order | Recorded in section 12 |
| 19 | The journal's unmeasured shape was incomplete | Section 9 lists `accepted`, `seconds_to_accept_stamp` and `asked_user` among the keys an unmeasured block lacks |

Not done, as instructed: the SPEC S-6 evidence line (the owner finding and the proposed replacement are in section 5),
`skills/shiploop-run-review/scripts/export.py` (its `NO_VISIT_CONTEXT` text still says context is read only from Codex rollouts; for the
Run Review session), and `--clear-at`.
