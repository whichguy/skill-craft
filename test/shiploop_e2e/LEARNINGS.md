# ShipLoop E2E learnings

One entry per live run, newest last. Each entry is committed on its own with a
detailed message; read the last three commit messages before the next run or change.

## Run 1 — 2026-09-26 — battleship, Grok grok-4.7 medium, ShipLoop 0.31.0 build

- Outcome: stopped by the 150-turn cap after 2,327 s; Grok reported $10.88. ShipLoop was at
  W1 `regression` (revision 26), 16 stages accepted, 17 still ahead. The product existed only in
  ShipLoop's external worktree; `work/` stayed empty, so every product check failed.
- Product: 12/12 `node --test` pass and all harness checks pass when run against the worktree;
  playable page; correct 400/404 handling. One real defect: `lib/game.js:66` memoizes the first
  response per cell, so re-firing a cell after the game ended returns `gameOver: false`,
  contradicting ShipLoop's own requirement R-8. No planned case covered repeat-after-game-over;
  HTTP tests never assert hit/sunk/gameOver:true through the API.
- Time: preparation ~21 min (spec 7, test-strategy 6), the whole work item ~14 min.
- Turns: 223 tool calls; ~60% overhead (run records 22%, CLI 18%, skill reads 9%, other 9%),
  ~40% product edits and test runs. Improve children at spec, test-strategy, plan, step-plan and
  test-spec took ~39% of calls and produced three small doc edits (b041544, eb8c529, 4c36017).
- Context: one conversation grew from 33 K to 331 K tokens per model call (32.7 M cached tokens);
  cost grows roughly with turns squared.
- Truncation: Grok caps tool output at ~20 KB. Seven preparation packets (23–36 KB) and
  Improve's 48 KB SKILL.md were cut off; the model recovered by reading Grok's terminal logs.
- Orchestrator: fixed 34-stage graph plus 8 unconditional Improve children (≥50 callbacks for one
  item); Improve requires exactly two reviews; not-applicable stages are model-justified one turn
  each; return to the source happens only at release; Plan Dispatcher not exercised (inline, 1 item).
- Keepalive: reading a saved packet in an unrelated Claude session bound that session to the run
  and blocked its stop (observe binds on any SHIPLOOP-RUN marker in tool output).
- Harness lessons: grade run state wherever ShipLoop puts it; `node --test` passed with zero tests
  until the check required a passing test; Grok logs tool output as a byte array plus
  `output_for_prompt` (measure the latter).

## Run 2 — 2026-09-26 — battleship, Grok grok-4.7 medium, skill-craft 1.0.1 (ShipLoop 0.33.1, b7653ed)

- Outcome: the Grok session ended after 158 turns and 2,662 s ($11.36 reported), stop reason `cancelled`,
  with no error. ShipLoop was active at revision 25, last accepted stage test-green; 15 stages accepted,
  19 still ahead. `work/` stayed empty; ShipLoop's worktree passes all four checks.
- Root cause of the stop: on turn 158 the model submitted test-refine's `complete` with its output redirected
  to /tmp. Since 153160e, `complete` on a test stage reruns every recorded test command, so it ran long enough
  for Grok to move it to a background task. The model then ended its turn to wait; in headless mode a finished
  turn ends the session, killing the callback. The keepalive hooks never ran in this session (no decision was
  written to the isolated profile's keepalive state), so nothing refused that turn end.
- Timeline: preparation 26.7 min (spec 10.1 min, research 4.2, plan 4.0, test-strategy 3.4); the item's stages
  through test-green 15.2 min. Run 1 reached select-work 6 minutes sooner.
- Improve: 10 children. Spec's took six actions, one finding per iteration (d1c61a5, 5282d88, 7f0f1e3,
  4e73e79) before two trivial passes; test-strategy and step-plan stopped on an unchanged first pass.
- The spec review found a real contradiction (a shot count versus rejected shots after the win) and resolved it
  by answering shots after the win with HTTP 400 `{error}` and no result or gameOver. The reviewer argues that
  replaces response fields the request names; the product is otherwise consistent with its own spec.
- Truncation: 1 truncated output (the first `next` packet, 19.6 of 26.2 KB), down from 7 in run 1. The model
  still redirected packets to /tmp files and grepped the skill's Python for result shapes.
- Context reached 336 K tokens per call (34.5 M cached tokens), the same range as run 1.
- Harness: the full-game check was stricter than the request. It now fails only when a shot after the game is
  over reports gameOver false (run 1's defect, exit 5); rejecting the shot passes (run 2's design).

## Run 3 — 2026-09-26 — battleship, Grok grok-4.7 medium, ShipLoop source 8019f09 (0.33.1 + 501fbb8)

- Outcome: PASS, the first complete run. ShipLoop reached done at revision 52 (15 prelude/inner/outer
  stages beyond run 2's furthest point), returned the product to work/ (source main 8729150), and all four
  checks pass there. 4,792 s over 4 Grok sessions (3 resumes), 295 turns, $22.90 reported.
- Sessions: three ended mid-run (794 s, 107 s, 970 s; stop "cancelled") when grok-4.7's final inference
  returned neither text nor a tool call. Grok dispatched only the `shutdown` Stop, never `end_turn`, so the
  pre-installed keepalive (5 decisions, all allow) could not refuse; the harness's resume kept the run alive.
- Foreground rule worked: test-refine's callback, which killed run 2, was accepted in 58 s; regression,
  verify (reruns every step-plan command), integrate, carry-forward and all 9 outer stages followed.
- Context: 33 K to 399 K tokens per call, then Grok auto-compacted at ~400 K to 56 K; the model re-read the
  skill and references (+54 K in two minutes). 15 host-truncated outputs (25-50 KB ShipLoop packets).
- Product: 10/10 node:test, all harness checks; shots after the win rejected with 400 {error} (documented as
  spec D-6/T-4). A mutation that swaps the game-over and already-fired checks passes both the unit suite and
  the harness: test-spec never combines two rejection rules on one cell.
- Improve: 7 children with records; 4 made material changes (spec, test-strategy, step-plan,
  system-test-author), 2-3 were cheap confirmations. The step plan split the item into three implement steps.
- Improve's loop state lives in the system temp directory (innerloop-*.json via mkstemp), not the run.

## Run 4 — 2026-09-26 — battleship, Grok grok-4.7 medium, skill-craft 1.2.0 (ShipLoop 0.35.0)

- Outcome: FAIL after 54 s and 5 turns ($0.06): the first Grok session ended with an empty final reply
  while setting up git in the empty directory, before ShipLoop had written any state. The harness resumed
  only `active` runs, so it stopped. The keepalive recorded one allow (shutdown).
- Learned: the empty-reply session end can happen at any point, including before the run exists; resume
  must cover "no run yet" too. Paused, blocked, awaiting, halted and done runs are still never resumed.

## Run 5 — 2026-09-26 — battleship, Grok grok-4.7 medium, skill-craft 1.2.0 (ShipLoop 0.35.0, dae33e4b)

- Outcome: PASS in one Grok session, no resumes: 4,291 s (71.5 min), 314 turns, $25.09 reported; done at
  revision 52; all four checks pass in work/. The handoff returned the game as working-tree changes, not a commit.
- Timeline: preparation ~28 min (spec 8, test-strategy 6: checks are "planned until they actually run"),
  W1 through carry-forward ~26 min with three implement steps, outer stages ~18 min (release-plan 7.3).
- Intake's new interaction/state questions went to discovery, not the user; no awaiting stall.
- Context: one compaction at ~392 K (-> 52 K); 17 truncated outputs, including Improve's SKILL.md (~49 KB
  printed with cat) and Improve bind packets up to 52.6 KB.
- Starting an Improve child still needs model-written glue: a SyntaxError in an inline Python snippet at
  test-spec (recovered), and twice Until Loop's "receipt's parent must be an existing directory".
- Release-plan's Improve review found that consumer_checks default to suite "check" (exit code only), so a
  zero-test `node --test` would pass release-verify; the model rewrote them to counted regression tests.
- release-verify was accepted "done" with "No browser session was available"; the page test only matches the
  title and counts 100 buttons, never running the click handler.

## Run 6 — 2026-09-26 — battleship, Grok grok-4.7 medium, marketplace skill-craft 1.4.0 (ShipLoop 0.37.0)

- First run through the marketplace version gate: installed 1.4.0 / 0.37.0 == catalog, HEAD == origin/main.
- Outcome: PASS, all four checks. 6,775 s (113 min), 480 turns, $35.32 over 6 host sessions; done; 16 Improve
  children, 42 test runs, 2 compactions, 2 truncated outputs (run 5: 17), 1 refused `complete`.
- Returned committed: HEAD has 16 commits, 0 untracked files, docs/shiploop/spec.md tracked (7 requirement IDs).
  Run 5 had returned only a working-tree delta because its product files were never committed in the worktree.
- Five sessions ended `cancelled`: Grok's auto permission mode refused model-written shell twice for Git setup
  in the empty directory (before any state) and twice for `mv packet.json packet.stopped-<stamp>.json` on the
  stopped-child restart route; one more at start. A refused tool call ends a headless turn; resume recovered
  every time. Fixed on the unreleased branch: workspace start bootstraps an empty directory, and
  `improve-start --restart-stopped` archives a stopped child itself.
- Costliest stages (turns/minutes): carry-forward 76/17.7 (the end-of-work Improve), system-test-author
  63/16.9 (a headless-browser check that first could not load the page; its Improve child stopped), product-
  acceptance 31/6.9, release-plan 29/6.0, spec 26/7.7. Implement steps: 5 + 21 turns.
- Context: peak ~400 K twice. Each Improve child's start contract (~6 KB) was hand-written by the model, and
  the Until Loop runtime reprints its ~6 KB frozen context after every `done` (resources alone 3.1 KB).
  improve-start (unreleased) removes the first; the second belongs to until-loop (print a head, point at the
  receipt).
- The analysis session was bound by keepalive again: event-dump output contained `improve-bind --run-dir=`
  and the observe fallback searched output text. Fixed on the branch: markers and --run-dir are read only
  from a driving command.
- Harness: learning retention — per-stage metrics now make run-to-run comparison possible; keep them in each
  entry. Further learning — the follow-on (6b) tests whether the committed spec and modules are reused.
  Evaluation criteria — add cancelled tool calls and sessions per run as reliability scores next to cost.
