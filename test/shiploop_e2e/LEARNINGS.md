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
