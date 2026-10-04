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

## Run 6b — 2026-09-26 — battleship-scoring follow-on in run 6's repository, marketplace 1.4.0 (ShipLoop 0.37.0)

- First follow-on run (P53): a copy of run 6's committed checkout, prompt "add scoring" (sunk ship name,
  shots, hits, accuracy on the page). Outcome: PASS on all 11 checks — 4 regression, 3 feature, 4 retention.
  4,996 s (83 min), 370 turns, $28.50 (run 6: 480 turns, $35.32), 8 sessions (7 cancelled), 16 Improve
  children, 49 test runs, 1 compaction, 0 truncated outputs.
- Retention held: discovery read docs/shiploop/spec.md and environment.md first; the spec kept R-1..R-7 and
  added R-8, R-9; reviews cited run 6's commit lessons (7acd322: headless Chrome cannot load this page) and
  reused test/system-browser.swift; the change extended rules.js, server.js and the existing test files (11
  files, +328/-111); no file removed, no dependency added. Weak point: the passing test count only went
  14 -> 15 (tests were restructured rather than added).
- Every model-written `git commit` at integrate was cancelled by Grok's auto permission check (three
  attempts, each ending a session); the model then accepted integrate without a commit. Result: a
  working-tree return, HEAD still at run 6's last commit, 11 modified files and the new feature record
  untracked in the source. This is the evidence for the branch fix that commits the item's declared paths
  when integrate is accepted.
- Also refused once: workspace start ("workspace root parent does not exist" for .shiploop-runs/<name>),
  fixed on the branch; three refused `complete` calls, all recovered.
- Costliest stages: implement 37 turns (the scoring step), spec 34, test-strategy 26, carry-forward 22,
  research 20. No system-test struggle this time: run 6's browser check was reused (6 turns).
- Harness: the retention checks worked and would have caught a rebuild. Next evaluation criterion to add:
  "source ends committed" (HEAD moved, nothing untracked) as a scored check, not only a fact.

## Run 7 — 2026-09-26 — battleship, Grok grok-4.7 medium, marketplace skill-craft 1.5.0 (ShipLoop 0.38.0)

- Outcome: PASS on every verdict, including the new `committed` (HEAD 7e86ce3e from an empty directory, 0
  uncommitted product paths). 3,937 s (66 min), 303 turns, $22.66, 4 sessions — against run 6 on 1.4.0:
  113 min, 480 turns, $35.32, 6 sessions. 0 ShipLoop command failures (run 6: 1), 0 truncated outputs (2),
  1 compaction (2), 16 Improve children, 59 test runs.
- Every 1.5.0 change was exercised and worked: workspace start bootstrapped the empty directory (no Git glue,
  no cancellation before state existed); improve-start started all 16 Improve children (no hand-written
  contract, no Until Loop start by hand); integrate committed the product itself (8cb0c599).
- The 3 remaining cancellations were the model's own inline probes and checks (a heredoc Node server for a
  planning experiment, a `node -e` check in the end-of-work review), not mechanical steps. Hypothesis to
  test: packets that say "write probe scripts to a file and run the file" draw fewer auto-mode refusals.
- Costliest stages: spec 40 turns/10.9 min, carry-forward 32/6.0 (run 6: 76), integration-verify 22,
  integrate 17, research 16. System-test-author 14 (run 6: 63).
- Release CI of 1.5.0 failed on two tests not updated for improve-start (Grok adapter allowlist, Improve
  schedule lead line) plus the adapter-hash-bound trace fixtures; the local quick tier had not selected
  them. Fix pending as 1.5.1 after a local full tier. Lesson: run `--group all` before release.py when a
  CLI verb is added.

## Run 7b — 2026-09-27 — battleship-scoring follow-on of run 7, marketplace 1.5.0 (ShipLoop 0.38.0)

- Outcome: FAIL on two harness-caused verdicts; the product passed every regression and feature check.
  5,381 s (90 min), 415 turns, $34.19 (run 7: 303 turns, $22.66), 8 sessions (7 cancelled), 16 Improve
  children, 3 ShipLoop command failures, 0 truncated outputs.
- `committed` FAIL was the harness: its own checks left `server.log` untracked in run 7's checkout, the
  copy started dirty (workspace start_clean False), and ShipLoop's return policy correctly fell back to a
  working-tree delta. In the worktree ShipLoop committed the item at integrate (4c60aed) and every later
  review. Fix: the harness deletes untracked files its checks create; server output goes to /dev/null.
- Spec retention "FAIL" was the harness too: the spec kept all nine IDs and modified R-4, R-7 and R-9 in
  place for scoring (allowed by the knowledge-home rule), with new test cases TC-9 and extended TC-2/6/8.
  The check now accepts new IDs or an in-place update that carries the feature.
- Other retention signals held: tests 9 -> 11, no dependency added, every earlier file present, and the
  live-server system test was fixed to fire the whole grid so a sink and the ship name actually occur.
- Cancellations: 3 of the first 4 were Improve review commits written as a heredoc message plus
  `git commit`; fixed (unreleased) by `shiploop improve-commit`. Others were model probes/checks and one
  `improve-start ... > /tmp/...` redirect: most refused commands write outside the host cwd (/tmp or the
  external workspace root). Hypothesis, not yet confirmed.
- improve-start printed a status line before its JSON packet; the model parsed the output with json.load
  and failed. Fixed (unreleased): stdout is only the runtime packet.

## Run 8b — 2026-09-27 — battleship-scoring follow-on of run 7, marketplace 1.6.0 (ShipLoop 0.39.0)

- Outcome: PASS on every verdict and all 11 checks — the first follow-on to end fully committed: HEAD moved
  7e86ce3e -> 442af8c4 (26 commits), 0 uncommitted product paths, 0 untracked files. 363 turns, $28.24,
  5 sessions (4 cancelled), 0 ShipLoop command failures, 1 compaction, 1 truncated output, 16 Improve
  children. Wall time 21,384 s includes a 4 h 49 min machine sleep (01:50-06:39); active time ~66 min.
- Retention: every earlier file kept, no dependency added, tests 9 -> 10, spec kept R-1..R-9 and added R-10
  (feature in spec: yes).
- improve-commit worked: Improve reviews committed only through it (no model-written git commit), so no
  session was lost to review commits (run 7b: 3). improve-start's stdout parsed as JSON.
- The 4 cancellations were the model's own actions: two `git checkout HEAD -- <file>` (discarding its own
  intake edit, reasonably refused) with a cp to /tmp, and two other model scripts.
- Implementation was cheap: four implement steps of 4-5 turns each; integrate 5 turns. Costliest: spec 49,
  step-plan 22, product-acceptance 22, release-plan 21. Regression's 290.8 min is the sleep.
- Harness: caffeinate now keeps the machine awake during a run (bd9c75a5); run 7b's harness defects (check
  leftovers, strict spec IDs) are fixed and did not recur.

Comparison of follow-ons (same prompt): 6b on 1.4.0 PASS but uncommitted, 7 cancelled sessions; 7b on 1.5.0
harness-FAIL, 7 cancelled; 8b on 1.6.0 PASS committed, 4 cancelled, 0 ShipLoop failures.

## P6 baselines — 2026-09-27 — cli-files and stateful-service focused suites, marketplace 1.7.0 (ShipLoop 0.40.0)

- First runs outside the browser-game style. Both PASS on every verdict including `committed`.
  - csv-report (cli-files, Python CLI): 328 turns, $25.46, 3 sessions (2 cancelled), 9/9 ShipLoop-run checks
    passed, glue 2, asked a person 0; spec kept 14 requirement IDs; HEAD 12 commits, nothing untracked.
  - seat-reservations (stateful-service, Python HTTP + SQLite, concurrency rule): 386 turns, $32.23,
    4 sessions (3 cancelled), 10/10 checks passed, glue 2, asked 0; 11 requirement IDs; 13 commits.
- The engine generalised: spec, test-first, implement, Improve reviews, system tests, release and return all
  worked for a CLI and a stateful service without any game-shaped guidance. The concurrency rule was
  planned (research probed SQLite locking) and the product passed the 50-request oversell check.
- Same cost shape as the web style: planning dominates (spec 42 and 55 turns, test-strategy 31), implement
  steps stay cheap. The quality loop found a real defect (non-numeric Content-Length crashed the handler).
- Remaining glue (both runs): the model's own `git add/commit` of docs between knowledge closes — the P3b
  behaviour already fixed on main (0.42.0). Cancellations: model probes and one Until Loop report written
  as a Python heredoc on stdin (candidate for an until-loop `--report-file`, upstream item).
- ShipLoop refusals worth reading: plan-stage improve-complete refused a final_result without the full
  work_items queue (the model recovered); one refused `complete` recovered on resubmit.
- Harness learnings: the glue metric needed two precision fixes during these runs (heredoc bodies are not
  commands; evidence notes are model output); rows appended from a suite run go to the checkout the runner
  lives in (move them before committing when a session shares a checkout).

## web-p5 — 2026-09-27 — web-service focused suite, checkout build (skill-craft 1.8.0, ShipLoop 0.41.0: P3-P5)

- battleship FAIL on `committed` only: ShipLoop reached done (process, invocation, plugin, shiploop all PASS),
  but the user's branch held 21 uncommitted product paths and none of the run's 16 commits.
  battleship-scoring was skipped (predecessor failed). 320 turns, $27.18, 2 sessions, 1 compaction,
  9/9 ShipLoop-run checks passed, 16 Improve children, asked a person 0.
- Root cause (engine): `system/browser-check.js`, written after the last work item, was untracked in the
  candidate at return. Any untracked product file forces the working-tree return route, so every run
  commit stayed on the run branch. Fix: `workspace plan-return` commits leftover product files through
  the one commit helper first; the reviewed plan then fast-forwards (f2c80133).
- Glue (engine): the model hand-committed `SHIPLOOP.md`, the knowledge index the references ask it to keep,
  because ShipLoop committed only `docs/shiploop/`. Fix: the index is knowledge, committed and screened with
  the home (bf8febce).
- Crash (engine): a release-plan `consumer_entry` with an absolute source path raised pathlib's
  NotImplementedError. Absolute paths are now refused with a message (f2c80133).
- P3b worked: the knowledge home was committed by ShipLoop after verify, document, step-plan,
  system-test-author and at every close; the glue fix to the metric (52e37e45) removed the /tmp start-file
  false positives.
- Harness: a checkout run is not release evidence (SPEC). The marketplace preflight (bbbb5242) now shows,
  before any run, what origin/main publishes and what the host actually installed.
- Forensics of the remaining signals (read-only analysis of the event log):
  - 4 of 6 glue entries were the old substring false positive (fixed by 52e37e45; the current metric counts
    2, both the SHIPLOOP.md hand commits fixed in bf8febce).
  - Refusals that the model recovered from in the same turn, with guidance already in the packet: an
    Improve receipt submitted with an uncommitted review edit; release-plan and release-verify submitted
    before their knowledge files existed.
  - Engine friction (next item): ShipLoop's own knowledge commit at release-verify stales the return receipt
    taken at release, so handoff refuses and the model runs a follow-up return by hand. Candidate fix: the
    script performs the follow-up return itself when only knowledge paths changed since the receipt.
  - Engine (upstream Until Loop): each non-terminal Until Loop packet prints the full report schema and fixed
    instruction; 3 outputs were truncated at the host's ~10k-character cap. Belongs with the until-loop
    short-output / `--report-file` item.
  - The one cancelled tool call was the host cancelling a `--help` probe at session start.

## temperature-report — 2026-09-27 — first graph-shaped case, Grok grok-4.7 medium, marketplace skill-craft 1.11.0 (ShipLoop 0.44.0)

- Outcome: **stopped, not graded.** Grok ran out of credits at 97 min (303 turns, peak context
  399 K, $7.91 reported). The run was killed deliberately to stop a resume loop; the output
  directory is kept. ShipLoop was active at revision 17, in the inner loop at the test
  specification, with 0 of 1 work items done. No product checks ran.
- Purpose: the validation plan's step 3 (docs/plan-orchestrator-validation-plan-2026-09-27.md),
  the first live fan-out/fan-in through the current release on the Ask-Agent parallel route.
- What it proved: asked for Ask-Agent delegation, ShipLoop recorded `delegation: ask-agent`, and
  Grok's step plan was exactly the intended graph. `S-convert` and `S-stats` were marked "may run
  in parallel", and `S-measure` "only after S-convert and S-stats are accepted". The dependency is
  carried only in step-task text; step plans have no `depends_on` since the 09-26 KISS change.
- What it did not reach: `implement`, where `chain bind` would happen. No chain binding exists, so
  the dispatcher fan-out itself is still unexercised by a real model.
- Time: intake 4.3, discovery 2.7, research 13.4, spec 29.6, test-strategy 5.8, plan 8.1,
  prepare 0.6, select-work 0.2, step-plan 28.9 minutes. Planning was about 94 of the 97 minutes;
  spec and step-plan dominate.
- Friction:
  - one `improve-bind` and one `complete` were refused;
  - the model hand-built loop contracts and ran its own `git commit`s ("model glue");
  - 4 tool outputs were truncated by the host;
  - the first session ended "cancelled after 91 turns" on a host permission check and was resumed
    once.
- Next: resume this run on another host (Claude Sonnet, budget-capped) from its recorded run
  directory, or rerun on Grok when credits return. The harness cannot switch hosts mid-run;
  `--continue-from` copies only the source checkout.

## temperature-report resumed on Codex — 2026-09-27 — gpt-5.6-luna xhigh, marketplace skill-craft 1.11.1 (ShipLoop 0.44.1)

- How: the first multi-host run. `--resume-run` continued the stopped Grok run in place on
  Codex, from inner-loop revision 17, using the ShipLoop CLI of the host that started it. The
  Codex session ran 34 min (2,048 s, 127 items); Codex reports no dollar cost.
- Outcome: **FAIL, paused at revision 20**, still before `implement`, so no chain was bound
  and the fan-out is still untested.
  - Verdicts: invoked, plugin and process pass; the ShipLoop and product verdicts fail.
  - Checks: 1 of 6 pass in the work directory.
- What worked: the test-spec Improve review ran and committed the test specification.
  Translating the Codex stream into Grok's shape gave a readable transcript, the model text,
  and tool calls. The harness saw ShipLoop was paused and correctly did not resume.
- **Defect, a normal-run failure:**
  - On the Ask-Agent route the model builds the Improve review's Until Loop contract by hand;
    `improve-start` writes it only on the inline route.
  - Luna's contract left the standalone ShipLoop binding marker out of `context.request`, so
    `improve-complete` refused the completed review's terminal packet. Neither can be
    regenerated, and the model paused the run: "Parent Improve import is blocked because the
    completed runtime context omitted the required standalone ShipLoop binding marker".
  - The Grok run showed the same risk as "hand-built loop contract" model glue, but got it right.
  - This matches the open 09-26 audit follow-up "ShipLoop-written Improve contract".
- Harness: a mixed-host run's turn count ignored the Codex session (it read 303, Grok's count).
  Fixed in metrics: a session that reports no per-call usage adds its own `num_turns`.
- Next: have ShipLoop write the Improve contract on the Ask-Agent route too, then run
  `temperature-report` fresh on Codex to reach `implement` and the chain.

## fanout — 2026-09-27 — first live fan-out/fan-in, Codex gpt-5.6-luna medium, marketplace skill-craft 1.11.1 (Plan Dispatcher 0.5.0)

- How: `test/shiploop_e2e/fanout.py`. Codex drove the published `plan-dispatcher` skill on dummy
  steps: A and B independent, J after both. Each step recorded its start, slept 30 s, and
  recorded its end. There was no ShipLoop SDLC and no product; per the owner, dummy steps are
  enough as long as the order is verified.
- Outcome: **PASS in 587 s.**
  - The dispatcher reports the run complete, with one attempt per step and no retries.
  - A and B ran as native Codex subagents, each with a launch handle, and overlapped 29.3 s of
    their 30 s: a real parallel fan-out.
  - J started about 240 s after both ended. The gap is the parent's verification and
    settlement; fan-in order holds.
- Meaning: the first live evidence through the current release that a real host follows the
  dispatcher's exact calls, fans out to parallel native workers and joins in dependency order.
  The earlier evidence was the 09-20 Grok pilot on older packages. ShipLoop's Ask-Agent chain
  route is still unexercised live; its Improve-contract defect (see the Codex resume entry)
  blocks it before `implement`.

## 1111 — 2026-09-27 — web-service + breadth suites in parallel, marketplace 1.11.1 (ShipLoop 0.44.1)

- First parallel run: the web-service suite and the breadth suite's three chains ran together (four Grok
  sessions, each with its own marketplace preflight: all installed 1.11.1). Grok credits ran out after
  about 62 minutes; three runs were stopped, unfinished.
- csv-report (cli-files) PASS on every verdict, including `committed`: 261 turns, $18.58, 1 session,
  0 ShipLoop failures, 0 cancellations. The return fix (commit leftovers, knowledge index) worked live;
  web-p5 had failed exactly there. Its row records glue 3; all three were metric false positives fixed
  during the run (e1539b8b, 339abaea, a5ccea84); recomputed glue is 0.
- seat-reservations reached release-plan with 9/9 ShipLoop-run checks and a real defect found by review
  (a Content-Length hang). The two battleship runs reached system tests and page work; review found real
  defects (`shipCells(null)` TypeError, `random()` == 1 off-board placement).
- Concurrency defect (plan P13): web battleship and seat-reservations both wrote their Until Loop report
  to the literal /tmp/improve-done-1.json; battleship then read the other run's report. That review
  loop's evidence is suspect. Models pick fixed /tmp names because the report goes on stdin and no packet
  names a scratch location. Parallel runs wait for P13.
- Engine refusal worth the fix (plan P12): the breadth battleship wrote the Improve completion record as
  raw JSON and was refused; the owner judged the hand-off over-precise. improve-complete now derives the
  record (730dfcda).
- Correction to an earlier claim: the truncated `opening.md` read was a model-built composite command
  (git log -7 --format=full plus several cats), not an oversized ShipLoop file (847 and 4,269 bytes).
  Real truncations remain the Until Loop action responses (~21 KB), the upstream --report-file item.
- Metric fixes from this round: run/evidence/ is model input; a contract counts as hand-built only when a
  command writes it or feeds it to the Until Loop runtime (json.dump(, not json.dumps).

## temperature-report on GPT-6 Luna max — 2026-09-27 — Codex gpt-6-luna max, marketplace skill-craft 1.13.0 (ShipLoop 0.46.0)

- Fresh run (a `--resume-run` of the earlier xhigh run was refused across the 1.13.0 release, as designed).
  Timed out at the harness's 3-hour limit while in the `plan` stage; the chain at `implement` was not reached.
- Stage times: intake 2.3 m, discovery 11.9 m, research 20.0 m, spec 79.2 m (159 tool calls),
  test-strategy 40.0 m, then about 27 m into plan. Four Improve children ran. Planning alone at max
  effort takes longer than the default timeout, so a chain-reaching run on Codex max needs
  `--timeout` of about 5 h or a lower effort for the planning stages.
- `improve-start` on the Ask-Agent route worked live (fix 938cc3fc): children started from the receipt's
  `next_argv`. Two `complete`/`improve-start` refusals were model misuse that the engine rejected without
  advancing the graph; one `workspace` call failed on a zsh quoting error in model-built glue.
- `turns 0` / `sessions 0` is expected for a killed Codex run: `codex exec` emits its turn and session
  totals only when it ends.
- Meaning: ShipLoop's parallel chain is still unproven live. Next attempt: Codex at a lower planning
  effort (or high) with a longer timeout, same case.

## batch 1121 (hello, seat-reservations, battleship, battleship-scoring) — 2026-09-27 — Codex gpt-6-luna max, marketplace skill-craft 1.13.0 (ShipLoop 0.46.0) — status: interim, evidence lost

- Outcome: hello passed (5 Improve imports, no `--result`). seat-reservations and battleship were still in
  `test-strategy` / `plan` at about 19:45 when the session ended; battleship-scoring never started. The
  scratch output directory was emptied by 2 Oct (no events, invocation or work history), so the runs cannot
  be resumed and the per-run files are gone. Only the numbers below were kept, from live snapshots. Lesson:
  keep the journal and exported evidence in the repo while a batch runs, never only in a scratchpad.
- Luna max vs the latest Grok run, minutes: intake 4.4/3.8 vs 3.3/3.5 (x1.1-1.3); discovery 14.1/10.7 vs
  3.2/2.4 (x4.4); research 45.0/26.9 vs 4.4/4.9 (x5.5-10); spec 105/99 vs 13/9.7 (x8-10); battleship
  test-strategy 64.3 vs 5.4 (x11.8). Rows are seat-reservations/battleship.
- Cost driver: each Improve review pass re-reads the whole contract (R-1..R-7, AC-01..AC-14, the planning
  docs, baseline and last seven commits). battleship's test-strategy ran about 6 passes 4-10 minutes apart.
  Stages without a review loop stay near Grok's time. Candidate fix, not yet built: a later pass reads what
  changed since the previous pass (the "reference, not reread" rule applied to Improve reviews).
- Engine defects with fixes queued (code on the branch that follows this entry, 1.14.0 base):
  N1 a spent investigation allowance paused the run instead of stopping exploration (7a4cfe28 -> allowance-never-pauses);
  N2 the execution-checkout path was mistaken for a `--result` value (1a8c6c0d);
  N3 the Improve packet did not say where the Until Loop card's relative links resolve (7c2a27be).
  Each is a one-line packet clarification with a change note; verify them together in the next batch.
- Observed, not yet a defect: a refused `improve-commit` because the commit message came from the wrong
  file; the refusal named the exact `nav-*/nav-*/commit-message.md` path and the model recovered at once.
  The nested `nav-` directories make that path easy to miss; watch for repeats before changing it.
- Harness default changed to Claude Sonnet 5.5 (`claude-sonnet-5-5`) on 2026-10-03 because Grok credits ran
  out; Luna max stays available with `--host codex`. A comparison needs the same host on both sides.

## chain-seeded — 2026-10-03 — first live ShipLoop parallel chain, Claude claude-sonnet-5-5, marketplace skill-craft 1.16.0 (ShipLoop 0.48.0)

- `run.py --case temperature-report --host claude --seed-at step-plan` (6833b41d): stages before
  step-plan recorded synthetically; the host followed ShipLoop's packets from step-plan.
  Output /Users/dadleet/shiploop-e2e-runs/chain-seeded-claude-e57b4d (outside the temp folder).
- **PASS on every verdict**: 1334 s (22 min), $11.75, 348 turns, 1 session, 0 ShipLoop command failures,
  0 model glue, 10 Improve children; all 6 case checks pass on the returned, committed product.
- **Chain PASS**: the model's step-plan graph was S1 convert, S2 stats (independent), S3 measure after
  both. Ledger order: S1 and S2 `launched_result` at 16:26:22, imported 16:27:21/16:27:22, settled
  16:28:34/16:28:50; S3 launched 16:29:18 only after both. 3/3 accepted, 3 native workers, 0
  main-context, most in flight 2. Per-step integration commits are in the product history
  (`ShipLoop chain prepared source=... target=...`).
- Meaning: ShipLoop's parallel chain works live from step-plan through return, on the release that
  includes 96d35fe2 (bridge-only navigation). Planning (intake to select-work) was not exercised by
  this run; the full run from intake is the remaining check.
- Cost shape: implement 5.2 m (114 turns) was the costliest stage; step-plan 2.4 m. Seeding removed
  the 2.5 h planning cost seen on Luna max.
- Expected gaps from seeding: docs/shiploop/spec.md missing (spec stage was synthetic); one of 11
  script verifications failed (not investigated; the run still passed every gate).

## hello + seat-reservations on Sonnet 5.5 — 2026-10-03 — Claude claude-sonnet-5-5, marketplace skill-craft 1.16.0 (ShipLoop 0.48.0) — status: firm for these two runs

- hello: all five verdicts pass; 7.4 min, 155 turns, $3.69; 0 ShipLoop failures, 0 glue, 0 truncations; 16 Improve
  children; HEAD 9f36c0ee. Baseline row committed (bd1e4817).
- seat-reservations: finished at revision 52 with every product check passing (unit, contract, restart,
  concurrency), 13 requirement ids, 19 commits, 9/9 script verifications; 420 turns, $6.32, 0 ShipLoop failures,
  0 glue, 0 truncations, 16 Improve children. The session was killed at the 10-minute background-task limit at
  revision 28 and resumed in place (`--resume-run`; it writes into the original directory, not `--output`).
- Pace: Sonnet reached the same graph in tens of minutes where Luna max spent 8-12x Grok's time on spec and
  test-strategy (see the batch 1121 entry). Per-stage minutes here are not comparable to Grok's: the regression
  stage's 22.1 min includes the time the run sat dead before the resume.
- Queued fixes N1-N3 (released in 1.16.0): N2 and N3 text reached the model (37 and 8 packet files) and no
  checkout-path or Until Loop path error occurred. N1's text reached 2 packets, but the run never hit the
  investigation allowance, so N1 is NOT proven live; it needs a slower research-heavy run (Luna) or a mock test.
- Harness defects found and fixed this round: (1) CI on 6833b41d failed because the seed inherited the runner's
  git-lfs filter (fix 9e937eb0: isolate Git config); (2) a resumed Claude run graded `invoked: false` because
  `shiploop_cli_ran` only read Grok/Codex `tool_call` events (fix 5fd875e1: also read Claude `tool_use`). The
  seat-reservations result.json was graded before fix (2), so its `pass: false` is stale; re-grading it with the
  fixed function returns invoked=true.
- Launch lesson: background tasks stop at 10 minutes; start long runs detached (nohup) and watch them with a monitor.

### Revision 2026-10-03 — the "review passes re-read everything" fix, status: superseded as a prompt change; metric built instead

- Claim under revision (batch 1121 entry above, cost driver): later Improve passes should read only what changed.
  Evidence against shipping that as a prompt change: in the finished Sonnet seat-reservations run, passes after
  the first still found real issues (one child: pass 1 a material command fix, pass 2 a misleading statement, pass
  3 a wrong count) and each came from re-reading the documents that had just changed, in full. A delta-only rule
  would keep that and drop only re-reads of unchanged accepted documents, but nothing measured shows those are
  costly on Sonnet: 17 passes across 8 children, at most 4 in one child, the longest child spanning about 96 s.
  The 8-12x multiplier was Luna max reasoning time per pass, seen only in commit timestamps of one lost batch.
- Decision: no packet change now. Built `metrics.improve_reviews` (passes per child, time between a child's first
  and last review note, note bytes), shown in every run's metrics.json and summary line, so the next slow-host run
  can show whether repeat passes spend real time before anyone trades review depth for speed. Seat-reservations
  baseline on Sonnet: 8 children, 17 passes, max 4.
- If a slow run shows a child spending hours on trivial repeat passes, the candidate packet line is: "After the
  first review, read in full every path changed since the previous review (git diff --name-only since its commit,
  plus uncommitted edits); re-check unchanged accepted documents only for the claims a changed path touches; the
  clean pass still verifies every exit criterion against the current artifacts." Verify it with a Luna run that
  compares findings per pass before and after; revert if later passes stop finding issues.
- Caveat: review-note mtimes may reflect import time rather than authoring time on some routes; treat `seconds`
  as an upper-level hint, not a stopwatch.

## chain-full — 2026-10-03 — full run from intake with the parallel chain, Claude claude-sonnet-5-5, marketplace skill-craft 1.16.0 (ShipLoop 0.48.0)

- `run.py --case temperature-report --host claude` from intake (no seed). Output
  /Users/dadleet/shiploop-e2e-runs/chain-full-claude-5b2cf8.
- **Every verdict passes** once graded by the current harness: shiploop done, committed (20 commits, spec
  committed with 9 requirement ids), all 6 case checks, plugin, process. The run's own grade said
  `invoked FAIL` only because the resumed Claude stream was graded before 5fd875e1 taught
  `shiploop_cli_ran` to read Claude `tool_use` events; the CLI ran 172 times.
- **Chain PASS inside a real-planning run**: the model's step-plan graph again split convert and stats
  (S1, S2) from measure (S3). S1 and S2 launched together at 17:02:10 and settled 17:05:08/17:05:28;
  S3 launched 17:06:02, only after both. 3/3 accepted, all native, most in flight 2. The chain was
  reached and passed within the first 30 minutes from intake.
- Planning on Sonnet 5.5 is fast: spec 5.3 m, step-plan 3.1 m, implement 6.4 m (the costliest stage);
  compare Luna max's spec 79 m on 2026-09-27. 475 turns, 16 Improve children, 0 ShipLoop command failures,
  0 model glue.
- Session handling: the first session was killed at 1798 s by the 30-minute background-task limit,
  mid carry-forward Improve; `--resume-run` finished the run in place in 266 s ($1.79 for the resumed
  session; a killed session reports no cost, so the total is unknown). Launch long runs as background
  tasks and resume after each kill; never detach with nohup (owner preference). On Claude the resume
  prompt names bare `shiploop next`, so the model spent ~17 s finding the CLI.
- Meaning: the Plan Orchestrator's last unproven link, ShipLoop planning a graph and running it as a
  parallel chain on a real host, now passes both seeded (6833b41d run) and from intake on the same
  release. Next live gaps: other hosts (Codex at xhigh, Grok when credits allow) and a wider graph.

## Batch 1003 (Sonnet breadth + Luna max battleship) — running findings, 2026-10-03 — status: interim (batch still running)

Cases: Sonnet 5.5 hello (gate, passed after a resume), seat-reservations, battleship, battleship-scoring; Luna gpt-6-luna max
battleship (detached, `--timeout 21600`) for review-pass data and a chance to exercise N1. Output in `/Users/dadleet/e2e-runs/20261003/`.
Marketplace skill-craft 1.16.0 (ShipLoop 0.48.0).

- F1 secret-detector false positive (engine, candidate fix after the batch): Luna's `complete` at discovery was refused twice with
  "result.summary appears to contain a credential secret". `shiploop_privacy.sensitive_text` flags any `auth|token|secret|signature|sig`
  label followed by a value, so descriptive text trips it: `auth: none required`, `session token: opaque UUID`, `secret=none` and
  `signature: n/a` all return True (checked on 1.16.0), while `no authentication, token or password handling` and `token required` do
  not. Battleship's design naturally mentions an opaque session token. Recoverable (the refusal names the cause; the model resubmits),
  but it spends turns and says "credential secret" when none is present. Candidate: extend the documentation-value words
  (`none`, `n/a`, `required`, `optional`, `opaque`, ...) in `_DOCUMENTATION_FIELD_WORD`; verify with a detector test of the four phrases
  above plus the existing real-secret cases. Not changed mid-batch.
- F2 launch limit: each background task is killed at the `timeout` it was given (10 min when set to the 600000 maximum), including the
  suite process, so a suite cannot be resumed as a whole; relaunch each case with `--resume-run <its output dir>`.

### Batch 1003 — Sonnet 5.5 results (skill-craft 1.16.0, ShipLoop 0.48.0) — status: firm for these runs; Luna max battleship still running

| Case | Verdicts | Turns | Improve children / review passes (max per child) | ShipLoop failures, glue |
|---|---|---|---|---|
| hello | all pass | 210 | 16 / 12 (3) | 0, 0 |
| seat-reservations | all pass, 2 work items | 423 | 24 / 25 (3) | 0, 0 |
| battleship | all pass | 353 | 20 / 24 (3) | 0, 0 |
| battleship-scoring (follow-on of battleship) | all verdicts pass; 1 stored check reads FAIL (see below) | 320 | 16 / 18 (3) | 0, 0 |

- seat-reservations' second work item came from two failed system-test verifications (and one expected red test); ShipLoop queued the
  fix, then the system test passed: the outer loop caught what the inner loop missed.
- battleship-scoring kept all 8 earlier requirement ids and added R-9 and R-10; the one failing stored check is a harness defect (the
  retention check counted ids only as Markdown headings; fixed in 42ca61f9, passes by hand on the real outputs).
- Costs in `metrics.json` count only sessions that ended; segments killed with their background task have no result event, so cost and
  turns undercount the killed segments. Per-stage minutes likewise omit time between a kill and its resume.
- N2 and N3 packet text reached the model (37 and 8 packet files in the first seat-reservations run); no checkout-path or Until Loop path
  error occurred in any of the four runs. N1 was not exercised (Sonnet never reached the allowance).
- Review passes: 79 passes across 76 children, at most 3 in any child, on Sonnet; the review-pass question therefore stays a Luna-only
  question, answered by the Luna battleship run's `improve_reviews` when it finishes.
- Harness defects found and fixed this batch (all pushed to main, 73 harness tests pass): (1) a Claude resume prompt named a bare
  `shiploop`, the model found only old plugin caches and stopped after 13 turns (7c1f1014: name the run's own marketplace CLI);
  (2) a run that finished after its parent was killed could not be graded (d09eb764: `--resume-run` on a done run regrades without a
  host); (3) the retention check's heading-only id match (42ca61f9). Earlier same day: the CI git-lfs seed failure (9e937eb0) and the
  resumed-run `invoked` grade (5fd875e1).
- Launch lesson (F2): a background task is killed at its `timeout`, and killing it also stops the suite process; the host session may
  carry the run on unobserved. After a kill, check the run's state: resume it if active, regrade it if done.

## chain-seeded on Codex — 2026-10-03 — gpt-6-luna xhigh, marketplace skill-craft 1.16.0 (ShipLoop 0.48.0) — stopped, chain not reached

- `run.py --case temperature-report --host codex --effort xhigh --seed-at step-plan`. Output
  /Users/dadleet/shiploop-e2e-runs/chain-seeded-codex-21de3d. Three 30-minute background-task sessions
  (each killed at the limit), resumed in place with `--resume-run`; stopped by rule after session 3 made
  no stage progress.
- Session 1: ~14 min reading the packet and confirming the synthetic records, then step-plan delegated to
  one native planning worker; killed while waiting, worker lost, nothing accepted.
- Session 2: step-plan accepted at ~17 min (revision 13; the same graph as Claude: S1 convert, S2 stats,
  S3 measure after both). ~12 min binding the Improve card and writing the child's opening file; killed
  just after dispatching the review worker.
- Session 3: the review worker found real planning gaps (spec-to-test mapping, measure.py criteria) and
  committed `b0c6132 Improve step plan: tighten acceptance contracts`, but its completion report was
  rejected for exceeding a report-size limit and it was still fixing that at the kill. Not verified:
  the refusal text is in the child's own session, not the parent stream.
- Meaning: on Codex xhigh each ShipLoop stage with an Improve child costs about one 30-minute session, and
  every kill loses the in-flight native worker, so a seeded run cannot finish under the background-task
  limit. Compare Claude Sonnet 5.5: the same seeded run in 22 min. The chain on Codex is still unproven.
- Open: (1) whether the report-size refusal is an engine defect (rerun the child's report or read its
  session); (2) how to run Codex past 30 minutes without detaching (owner preference: visible background
  tasks).

### Batch 1003 — Luna max battleship, plan stage: the Backchain loop cannot persist its first callback (F3) — status: firm for this run, engine fix candidate

- Observed (battleship, Codex gpt-6-luna max, skill-craft 1.16.0, 4h23m in): the plan packet gives the model ShipLoop-resolved locators for
  Backchain and the Until Loop but no script to start the Backchain loop, so the model hand-built the start contract
  (`run/scratch/backchain-until-loop-start.json`: workspace, work, exit and repeat conditions, required reviews, context) and validated it with
  its own script. The metric called that glue (3 events: the start contract, a start command, and a blocker note), and it was right.
- Result: after the plan review finished, the Until Loop rejected the first callback report twice with `state exceeds the small-file limit`.
  The runtime's `MAX_STATE_BYTES` is 16,384; the frozen state was already 16,287 bytes (the model's own preflight only bounded the context at
  15,000), so even a minimal report would be 28 bytes over. The model wrote `docs/shiploop/features/.../reviews/runtime-blocker-1.md`, did not
  edit state or start a replacement loop, and recorded that the Backchain parent plan action cannot be submitted as complete.
- Why it matters: a plan stage on a slow, thorough host can finish all its review work and still be unable to close, because a model sized a
  contract by hand. Sonnet never hit it (its planning did not start a Backchain loop). This is the model-glue gap the ShipLoop purpose says scripts
  should own, the way `improve-start` does for Improve children.
- Candidate fix (after the batch, with its own test): a ShipLoop script builds the Backchain loop start contract with a context budget that leaves
  at least the runtime's report headroom (the state limit minus the largest legal report), or the plan packet states that budget; verify with a
  contract whose state sits just under the cap and a report that fits.
- Evidence: `/Users/dadleet/e2e-runs/20261003/battleship-luna` (events.jsonl; the run's `scratch/backchain-until-loop-*.json` files and the
  `runtime-blocker-1.md` note in the worktree).

### Batch 1003 — Luna max battleship final result — status: firm for this run

- ShipLoop ended `blocked` at `plan` (revision 12) after 17,445 s (4h51m); the harness grades `shiploop` FAIL and `committed` PASS (nothing
  was committed to the product: no code existed). 720 turns, 6 Improve children, 10 review passes in 3 children (spans 1,061 s, 1,254 s and
  463 s), 5 ShipLoop refusals (2 secret-detector (F1), 2 inconsistent plan outcomes, 1 `improve-start`), 4 glue events (all the model-built
  Backchain loop contract and its validation, F3). Cost is not reported for Codex.
- Stage minutes (approximate, per accepted stage): intake 5.5, discovery 17.7, research 23.2, spec 65.9, test-strategy 142.1, plan 34.0, which is
  289 of the 291 minutes; the same graph took Sonnet under 5 minutes to reach plan. The test-strategy figure includes the Backchain attempt and
  its blocked callback (F3); treat per-stage minutes on a run with Improve imports as an upper bound.
- ShipLoop stopped honestly: plan outcome `blocked` (category external) with a printed resume command, no state edits, no replacement loop. The
  two plan refusals (`work_items require done or replan`, `assumptions are allowed only on a done plan result`) rejected an inconsistent blocked
  result and the model corrected it.
- Review-pass answer for Luna max: 10 repeat passes cost about 46 minutes of 291 (16%), and the stage's first-pass work, not repeat passes, is the
  cost. A "later passes read only what changed" prompt would save at most that share of this run and risks losing what later passes catch, so the
  review-pass prompt change stays unbuilt. The real Luna blocker was F3, not review depth.
- Baseline row for this run: appended to `baselines.jsonl` (host codex, plan blocked); not comparable to the Sonnet rows.
- N1 (spent investigation allowance never pauses the run): Luna research took 23 minutes and did not pause the run, but no allowance message was
  recorded; N1 stays unproven rather than disproven.

## batch B — 2026-10-03 — chain recovery, shape and repeat checks, Claude claude-sonnet-5-5, marketplace skill-craft 1.16.0 (ShipLoop 0.48.0)

Plan: docs/orchestrator-test-map.md "Next live checks" (group B). Harness d9a229bb..(group A commit):
`--interrupt-at chain-launched`, stricter chain grading (dependency order, integrated once, depth, per-case
expectations), cases unit-converter (wide) and word-report (deep). All runs `--seed-at step-plan`, outputs
under /Users/dadleet/shiploop-e2e-runs/.

| Run | Result | Chain | Notes |
|---|---|---|---|
| b1-interrupt-temperature-5ed5a4 | FAIL, paused | 0/3 | killed at 735 s with S1, S2 in flight; F1 |
| b2-interrupt-temperature-7459dc | FAIL, paused | 0/3 | killed at 476 s with S1, S2 in flight; F1 again |
| b1-unit-converter-a1950c | **PASS** | 5/5, 4 in flight | 23 min, $9.60 |
| b2-unit-converter-1df863 | **PASS** | 5/5, 4 in flight | host died at 28 min (SSL error, below); resumed, done |
| b1-word-report-1c7a7e | FAIL, paused | 5/5, depth 3, 7 attempts | S4, S5 retried; F2 |
| b2-word-report-b1f521 | **PASS** | 5/5, depth 3 | no retries; host died at 27 min (SSL); resumed in 54 s, done |
| b3-temperature-5c5493 | **PASS** | 3/3, 2 in flight | 16 min, $8.62 |

- **Shapes work.** Every chain the model planned was the expected shape: wide = four independent modules
  plus a join at capacity 4 (4 in flight, both runs); deep = S1, S2 -> S3(S1), S4(S2) -> S5 (depth 3, in
  dependency order, both runs). The stricter grader found no out-of-order launch and no double integration
  in any run.
- **F1 (2/2): losing the host mid-chain needs a person.** After the kill, the fresh session found both
  attempts active, their worktrees clean, and `TaskStop` on each handle returned "No task found". The
  chain guide forbids retry, import or cleanup until the original worker's stoppage is established, so it
  submitted `implement` blocked on the user (refused: chain unfinished) and paused asking "may I treat both
  workers as stopped and retry?". Native Claude workers die with their host, but nothing records which host
  session launched them, so a later session can never prove it.
- **F2 (1/1 runs with retries): a retried step blocks chain finish forever.** In b1-word-report S4 and S5
  were each retried after test-oracle defects; both retries were accepted (5/5, 26 tests pass in the run's
  worktree, 7/7 case checks) but the superseded attempts' Ask-Agent workspaces cannot be closed ("no
  non-integrated close"), so `chain finish` refuses and `implement` cannot complete; the model paused
  quoting "no completion-capable recovery route". The b2 repeat had no retries and finished. Retries are
  normal, so this breaks ordinary runs.
- **Environment:** both b2 shape runs lost their host at ~27 min to "API Error: Unable to connect to API:
  SSL certificate has expired" at the same moment; the API certificate checked valid minutes later. Both
  resumed in place with `--resume-run` and finished (resume works across a host death outside ShipLoop).
- Cost: passing seeded runs $8.60-11.20 and 16-23 min. Interrupted runs report only the resumed session's
  cost (a killed session reports none).
- Next (group C): fix F2 first (ordinary runs), then F1; one release; one verification batch (the word
  report with a retry, and kill-and-resume).

### Verification of F3/F1 on 1.16.1 — Luna max battleship (in progress) — 2026-10-03/04 — status: firm for the plan stage

Run `/Users/dadleet/e2e-runs/20261003/v1161-battleship-luna`, Codex gpt-6-luna max, marketplace skill-craft 1.16.1 (ShipLoop 0.48.1), `--timeout 36000`.

- The run passed the stage that ended the 1.16.0 run: the plan stage closed as done (39.2 min by the harness's stage-minutes metric; superseded 2026-10-04: accept timestamps give 196 min, see "Backchain ledger" below) and the run reached `prepare` at revision 12,
  about 6h25m in (1.16.0: blocked at plan, revision 12, 4h51m). Hello on Sonnet 5.5 also passed on 1.16.1 (143 turns, $3.30, 0 failures).
- Improve contracts: the model wrote its openings inside the printed allowance on the first try for spec (8,775 bytes of 9,216; the
  1.16.0 contracts were 11.9, 12.1 and 15.7 KB) and in three rounds for test-strategy (12,478 -> 10,005 -> accepted at 8,960): the
  refusal named the sections and how far over each was. Total refusals: 3 `improve-start` (one for a missing `## Environment` section).
- Backchain loop contract (the hand-built one that failed): 7,716 bytes against the 9,216 budget (its resources, 4,073 bytes, cite files
  instead of inlining). The loop started, saved every report (state 12.4-14.5 KB of 16,384; each replacement report fits) and ended
  `complete` after 7 callbacks with 2 consecutive trivial passes. The measuring command in the packet matched the runtime's count.
  The first handoff was 3.3 KB and the state grew to 14.5 KB at the largest report, so the 6,144-byte report reserve is adequate but not
  generous for Luna max; revisit if a loop ever reports under 1.5 KB of headroom.
- Residual finding F4: the refusal lists whole contract fields ("request" includes about 1.4 KB of ShipLoop text) beside an allowance for
  the model's sections only, so the model under-cut once and needed a second round. Fix for the next release: list each opening
  section's own byte size.
- Glue stayed at 2 (the model-built Backchain contract and its helper), unchanged in nature; whether a script should write that contract
  remains a design question (the budget guidance made the model-built one safe).

### Backchain ledger — Luna max battleship, 1.16.1 — 2026-10-04 — status: interim (run still active; the carry-forward and product-acceptance loops are not reached yet)

Question: what did the two Backchain loops add, and what did they cost? Evidence: `scratch/backchain-plan/` and `scratch/backchain-step-plan/`
in `/Users/dadleet/e2e-runs/20261003/v1161-battleship-luna/.shiploop-runs/work-20261003-225401-173a04/run/` (`review-records/`, `backchain-result.md`,
`until-loop-receipt.json`, `candidate-plan.json`, `generator-draft.json`) and `timeline.json` accept timestamps. Times below come from file and accept
timestamps, so they are approximate (run clock UTC-7). The same ledger, with per-pass verdicts the owner can change, is on the run review artifact
(`https://claude.ai/artifact/BFc6JGjLhENVJ9shRAA2iA`, private); this entry is the durable copy.

| Stage (accept to accept) | Total | Gather | Draft + elaborate | Passes | Write result | Improve review |
| --- | --- | --- | --- | --- | --- | --- |
| plan | 196 min | 25 | 20 | 103 (7 passes: 11, 15, 26, 18, 17, 12, 4) | 4 | 44 |
| step-plan (W1) | 188 min | 28 | 16 | 107 (4 passes: 42, 55, 6, 4) | 13 | 24 |

- Backchain stages are 384 of 969 min (40%) at the snapshot; the loops' own passes are 210 min (22%).
- **Added value (clear):** plan passes 1-4 found six real graph defects in 70 min (F-1 wrong supplier edge S6 from S4; F-2 duplicate-once and mutation
  order of the API; F-3 browser recovery output; F-4 S2 confirmation inspect -> execute; F-5 no inspection of the dependency files; F-6 non-deterministic S11
  confirmation). Step-plan passes 1-2 found four omissions in 97 min (F-01 rejection tests and docstrings; F-02 style note; F-03 README and local-skill fit;
  F-04 effort/benefit comparison), all against what the parent step-plan packet itself requires.
- **Wasted (clear):** plan pass 5 (17 min, F-7) was a stale source label in Backchain's own scratch metadata; it reset the clean streak. No product impact seen.
- **Confirming passes:** plan 6-7 and step-plan 3-4 found nothing by design (two clean passes required): 26 min. Whether they ever prevented anything is unknown.
- **Repeated work:** half of each graph is one "independently confirmed" step per acceptance criterion (plan S11-S20, step-plan S8-S17), planned twice by the model for
  the same item; elaboration doubled the 10-step generator draft to 20 steps before pass 1.
- **Not used by the script:** the 20-step plan graph was handed to ShipLoop as one work item with an empty `parallel_groups`; the result states its structure is
  "unknown because no deterministic validation receipt exists" (ids, references, acyclicity and sinks were checked by the model; a duplicate id S20 was caught only by that check).
- **A gap after both loops:** the W1 item plan was revised during build so SYS-PORT-09 checks the sanitized child PORT separately from its readiness probe port. One
  instance; whether the spec or sources already showed it is not established.
- **Not established:** whether the loops prevented later failures. No comparison exists: Sonnet starts no Backchain loop (plan accepted in 0.2 min) and the models differ.
- **Harness finding (supersedes the "39.2 min" plan figure above):** the harness's stage minutes move time between stages. Accept timestamps give test-strategy 94 min and
  plan 196 min; the harness reports 224 and 39. Totals agree within 5 min (385 and 380 through plan), so only the attribution is wrong.
- Candidates, none built: a script writes and validates the Backchain graph; the script emits the per-criterion verification steps from the spec; a controlled comparison
  (loops on versus a script-validated plan with no review loop, same model and case); harness stage minutes from the script's own timestamps.
