# Batch 1009, worktree H: journal (the Claude tool-block reading, candidate H1)

Living journal for candidate H1 of the round-1 analysis (`docs/experiments/batch-1009-round1-analysis-20261008/analysis.json`):
`test/shiploop_e2e/metrics.py` stops being blind to Claude's `tool_use` and `tool_result` blocks. It is the long-deferred item M1 of
`docs/shiploop-callback-typos-plan-2026-10-04.md`, built in four parts, one section each, written in the part's own commit: H1a (the
one classifier and the failure rule), H1c (per-stage context), H1b (the `tool_use` block) and H1d (red records). H1e to H1g were
dropped by the design (each is named in its section). Basis: origin/main 847fa64e (skill-craft 1.24.0, ShipLoop 0.56.0). Evidence of
the design and of its audit: `docs/experiments/claude-tool-blocks-20261008/design-audit.json`. The recorded calls the tests read:
`docs/experiments/claude-tool-blocks-20261008/` (`extract.py` rebuilds them from the round-1 run folders). Harness only: no file under
`skills/` changes, so no packet text, kept-head window, state key or `changes/` note moves, and no saved run is refused.

Status words: firm (hermetic tests plus a recorded-run recomputation), interim, exploratory, superseded.

## H1a: Claude's tool blocks are classified like Grok's tool calls (2026-10-08)

**Built (status: firm for the counts on the 15 recorded Claude runs and for the hermetic tests; not yet seen on a Claude Code build
other than 2.1.2xx).** `metrics.ToolLog` takes every host's tool calls and results: Grok's `tool_call` and `tool_call_update` events,
Codex's after the translator, and Claude's `tool_use` blocks (assistant events) and `tool_result` blocks (user events, `tool_results`).
It yields `shiploop_failures`, `model_glue`, `tmp_writes`, `asked_user`, `reads` and each stage's `tool_calls`. Removed with it:
`CLAUDE_BLIND` and `CLAUDE_TOOL_BLOCKS` (the four names Claude marked unmeasured), the per-stage `stage_tool_calls` branch,
`run.shared_tmp_writes`'s `unmeasured` parameter, `tmp_writes_unmeasured` in `suite-result.json` and the "collisions not checked"
print: after the change no host puts `tmp_writes` in `unmeasured`, so they were unreachable (one supported version, no fallbacks).
`REFUSAL_LINE` gained `workspace blocked` (`shiploop_protocol.py` prints `ShipLoop workspace blocked: {exc}`, exit 2; the line was
not recognised, so `failure_line` returned ""). `run.py` and `progress.py` print `metrics.failure_text`, so a refusal behind a pipe
reads "exit not shown" and not "exit None". Tests: `ClaudeToolBlocksTest` and the flipped `HostCoverageTest`,
`SuiteTmpCheckHostTest` and `MeasuredHostPrintingTest` in `test/shiploop-e2e.test.py`.

**The failure rule (firm).** A ShipLoop failure is one tool result, counted once, in either of two cases.
- Its text has a line that begins `ShipLoop navigator: `, `ShipLoop blocked: ` or `ShipLoop workspace blocked: `, whatever exit the
  host showed. The recorded `line` starts at that line, so the model's own traceback before it is not the line (r1 Checkers:
  "KeyError" before "Until Loop terminal packet is not complete").
- The host showed a nonzero exit (Claude shows it only as a leading `Exit code N`) and the command, or the body of a script the model
  wrote earlier in a heredoc, names a ShipLoop verb.
The verb comes from the command alone, else it is `unknown`; a script's verb is not guessed (r1 Checkers `ih.sh` holds several).

**Corrections from the audit that changed the build.**
- *No command guard on the refusal arm.* The design's prose and one planned test said a refusal-shaped result of a command that is
  not ShipLoop is no failure, but its prototype had no such guard and its numbers (5 and 4) came from the unguarded version. The audit
  built the guarded one: it drops 9 of the 72 anchored refusal results in the 15 recorded runs (12.5%), including a real
  knowledge-file refusal in r1 Checkers, and all 72 are genuine ShipLoop output. So the anchored line alone decides. The known
  false positive (a document line that begins with a prefix, for example a `cat` of a journal quoting one) is stated in the README
  and pinned by a test, and no recorded run has one.
- *Exit arm narrowed.* "A command that names the CLI or a scratch script" would make r1 Battleship result 374 (`idone.py`
  FileNotFoundError, `Exit code 1`) a sixth failure. The arm needs a ShipLoop verb in the command or in a model-written script's
  body; a test runs that recorded result after the recorded write of `idone.py` and expects none.
- *Variable expansion.* In r1 Checkers a quoted `sh -c '... R=$?; ...'` inside the command overrode the real `R=<run dir>`, so
  `$R/scratch/sub.sh` expanded to `$?/scratch/sub.sh`. An assignment whose value is still unresolved after expansion (`$?`, `$!`,
  `$(`, a variable not yet assigned) is not recorded; a test is built from that recorded command.
- *One rule for every host, and the audit's Grok premise was wrong.* The audit said Grok runs also hide refusals behind exit 0
  (5 results with an anchored line at `exit_code` 0 in the v1210, v1220 and v1230 runs). Read as events, every one of them is a
  `status: in_progress` update (a placeholder exit 0 with the output so far) of a call whose `completed` update carries exit 2:
  a first draft of the uniform rule recorded those calls with exit 0 and the dedupe then dropped the real exit. So Grok's running
  updates are skipped and only the completed update is classified, by the same rule as Claude's result
  (`test_a_grok_call_is_read_from_its_final_update_not_the_running_one`, the shape of the recorded v1210 call; the guard fails the
  test when removed). No recorded Grok run has a refusal behind a real exit 0, but the mechanism (a pipe) is the same, so the
  arm is not Claude-only. Effect on history, measured on the four recorded Grok runs: the old and new lists are identical for
  v1210, v1230 and r1; v1220 reads 3 where it read 2, because a compound command (`$CLI workspace plan-return ...` then a failing
  `curl`, exit 1) names its verb only once `$CLI` is expanded; it is the same over-count Claude has. Baseline printouts compare
  glue, not failures, so no printed comparison changes.
- *Variables are expanded for Grok and Codex commands too*, one function for all hosts (only a command that assigns a variable
  before using it is affected).

**Evidence (recomputed, not hand-mined).** `metrics.collect` over all 15 recorded Claude runs under `/Users/dadleet/e2e-runs/2026*`
ran without a crash, 0.02 to 0.06 s each. Failures 82: 72 are anchored refusal results (the same 72 the audit counted, so none is
lost or invented) and 10 are exit-only (7 are `Exit code 127` of a bare `shiploop` on a PATH without it, a setup failure counted as
verb `next` with no line; 2 are `improve-bind` commands whose Python traceback was the output; 1 is a compound command whose exit
is attributed to the ShipLoop call in it). Exits shown on 18 of the 82. r1 Battleship: 5 failures (3 `complete`, 2 `workspace`; none
has an exit), glue 1 (`git -C $WT add` and `commit`), `/tmp/bs.pid` the one shared `/tmp` write, 120 stage tool calls. r1 Checkers: 4
failures (1 `complete`, 2 `unknown`, 1 `workspace`), glue 2, 105 tool calls. Old figures this replaces: both runs read `[]`, `[]`
and null per-stage tool calls. The Batch 1003 table of `LEARNINGS.md` is corrected with its reason (hello 6, seat-reservations 16,
battleship 13, battleship-scoring 10 failures; glue 0, 3, 10, 0).

**Pre-change baseline rows (resolves M1's open question 4).** The four Claude rows in `baselines.jsonl` (2026-10-04, 10-06, 10-07,
10-08) hold null for `model_glue`, `shiploop_failures` and `tmp_writes` and name them, with `stage_tool_calls`, in `unmeasured`. So
the next Claude row prints "not measured -> N"; no marker is needed. `test_a_claude_row_from_before_the_tool_blocks_were_read_compares_as_not_measured`
builds such a row and checks the printed line.

**What stays unknown or unmeasured.**
- Another Claude Code build: `Exit code N` and the result shapes were checked on every recorded build (about 3,500 results, no
  exception: every Bash result with the prefix has `is_error` true and none without it does). Settled for a new build by regrading its
  run; a mismatch shows as `is_error` true results with no prefix.
- Sub-agent calls: no recorded Claude run used Task or Agent and no assistant message carries `parent_tool_use_id`; a
  `delegation=agent` run's inner calls would be absent, so every count is main-thread.
- Background Bash tasks arrive as `system/task_started` and `task_notification` events (3 in r1 Battleship); none ran a ShipLoop
  command. A background ShipLoop call would be unseen.
- A result the host saved to a file (`<persisted-output>`, about 5 in older runs) starts with neither prefix within its preview, so a
  failing command with a large output is invisible. All counts are lower bounds for this reason, and for the loop case (a looping
  command with several ShipLoop calls is one failure: battleship-scoring has 19 refusal lines in 8 results).
- Model glue still counts commands: a script the model wrote that wraps the CLI hides its ShipLoop calls from every count here
  (14 of the 15 recorded runs wrote one). The README says so; H1b lists the scripts.
- Compactions, truncated outputs, cancelled tool calls and knowledge reads stay unmeasured for Claude (no `compact_boundary` in any
  of the 15 streams; the only context drops fall at a `system/init`, a session start; the others each need a second reader).

**Related commits.** 1a35bc50 (Grok-only counters are unmeasured elsewhere; the `GROK_SIGNALS` precedent), 8444e11d (the planning
block's recorded-extract tests, the pattern the fixtures follow), 06f2a012 (the callback plan that admitted M1), 847fa64e (the
round-1 analysis that found every lens hand-mining `events.jsonl`).

## H1c: Claude stage rows carry the context the Codex rows carry (2026-10-08)

**Built (status: firm for the figures on the two round-1 runs and the fixture-exact tests; no run has been judged by it).** A timed
stage row of a Claude run gets `context` {calls, peak, peakPct}, the shape the unmodified exporter's `_visit_context` already reads
for Codex (`rollouts.rollout_context` perStage, minus compactions). `calls` are the messages whose first event falls in the window,
`peak` the largest input side (input, cache reads, cache writes) of an event in it, `peakPct` the peak over the context window the
result events report (`per_stage(..., context_window)`; `rollouts.share` is now public because both hosts use it). `turns` keeps its
events-based definition because `baselines.jsonl` stores it. Test:
`ClaudeToolBlocksTest.test_stage_rows_count_model_calls_and_their_peak_context_not_events`, over the 47 recorded events (30 assistant
events, 16 messages, three cut windows whose expected figures were computed from the fixture by a separate loop before the code
existed); the through-exporter test also checks that `visitContext` leaves the page's unmeasured map and every stage has its calls.

**Corrections from the audit that changed the build.** The design's test said "the sum of `context.calls` equals `model_calls`". That is
false on real runs: calls after the last accepted stage are in no window (119 of 120 on r1 Battleship, 104 of 105 on r1 Checkers; the
stage rows' tool calls still sum to all 120 and 105, so the one message no window holds has no tool_use block). The
test asserts equality only on a synthetic cut whose last accept follows the last event, and "fewer" on a cut that ends early.

**Evidence.** r1 Battleship: 37 stage rows, all with a context; the heaviest stage peak 236,029 of a 1,000,000 window (the run's
`input_peak` is 237,430, from a call after the last accepted stage); stages 0 calls: skill-assess and skill-validate (the script
records them itself, with no peak). r1 Checkers: 36 rows, peak 235,247, one 0-call stage (integrate). Stage `turns` sums: 206 and 184
(the "turns 184 vs model_calls 105" of the Checkers lens).

**Not verified / unmeasured.** Compactions stay unmeasured for Claude: no `compact_boundary` in any of the 15 recorded streams, and
the only context drops (5 older runs, 7 drops by the audit's scan) fall at a `system/init`, a session start, with no positive control.
The exporter's SCHEMA rows that say only a Codex run has per-visit context are stale; see the hand-off at the end of this journal.
