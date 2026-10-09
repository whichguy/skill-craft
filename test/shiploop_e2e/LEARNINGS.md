# ShipLoop E2E learnings

One entry per live run, newest last. Each entry is committed on its own with a
detailed message; read the last three commit messages before the next run or change.

## How expectations are set and mismatches decided (from 2026-10-04)

Every expectation names its source in `cases.json`: `checks_source` (the request),
`chain.source` (a SPEC clause), `retention_source`, `budget.source`; recovery runs use
SPEC S-6 and S-14. The harness prints each verdict with what was expected and its
source. Must-level verdicts fail a run; the budget is should-level (reported only).

A run that fails writes `mismatch.md` beside its output with Expected and Observed
filled in. Record each mismatch here in that shape:

- **Expected** (and its source) / **Observed** (with evidence paths)
- **Triage**, in order, stopping at the first yes: the check is wrong (fix the test); the
  environment (fix the harness or ops, keep the expectation); not reproduced and no clear
  trigger (rerun first); the expectation describes how, not what (change the expectation);
  a normal run never hits it (known limit); the behaviour comes from a deliberate rule (the
  owner decides); the expectation traces to its source (change the product). Corrected
  2026-10-04: the first version asked about the source before the known-limit and owner
  questions, so a spec-traced mismatch would have skipped both.
- **Decision**: product / expectation / owner / known limit / environment, and **why**
- **Verified by**: the hermetic test and the rerun that confirm it

Changing an expectation needs the same evidence as changing the product, stated in
its commit.

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
| hello | all pass | 210 | 16 / 12 (3) | 6, 0 (was 0, 0) |
| seat-reservations | all pass, 2 work items | 423 | 24 / 25 (3) | 16, 2 (was 0, 0) |
| battleship | all pass | 353 | 20 / 24 (3) | 13, 10 (was 0, 0) |
| battleship-scoring (follow-on of battleship) | all verdicts pass; 1 stored check reads FAIL (see below) | 320 | 16 / 18 (3) | 10, 0 (was 0, 0) |

- Corrected 2026-10-08 (M1, `docs/shiploop-batch-1009h-journal-2026-10-08.md`): the last column read 0, 0 because `metrics.collect`
  did not read Claude's tool blocks (item 7 of "Callback path typos across the 1003 batch", below), so those zeros were "not measured", not "none". The
  figures now shown are `metrics.collect` over the same run folders (`20261003/batch-sonnet/<case>`, turns 210, 423, 353 and 320
  match this table). They are heuristic counts of tool results, lower bounds for glue (a script the model wrote that wraps the CLI
  hides its calls); the old column is kept as "was". Corrected again the same day (review of the H1 commits): seat-reservations'
  glue read 3, one of which wrote `$W/docs/shiploop/environment.md` with `W=$B/../worktree`, the product worktree beside the run
  directory, which matched the run directory's prefix until the expansion resolved `/run/..`; the glue is 2.
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

### Batch B decisions (2026-10-04), in the mismatch shape

(F1 and F2 here are batch B's labels, separate from the F1-F4 of the 1.16.0/1.16.1 Luna batch above.)

**F2: a retried step blocks chain finish forever**
- Expected (SPEC S-6; the request): a retried step gets a fresh attempt and the chain finishes.
- Observed: b1-word-report-1c7a7e, 5/5 accepted, product 7/7 in the worktree, `chain finish` refused
  ("retained superseded Ask-Agent workspaces"), run paused.
- Triage: check correct; not environment; trigger clear (any retry); traces to S-6; the rule behind
  it (3e217ad5: never delete rejected work without authority) is right, but blocking finish is not
  part of that rule; a normal run hits it whenever a step is retried.
- Decision: **product**. Superseded workspaces are kept with their receipts and listed in the finish
  receipt (`retained_superseded`); they no longer hold the chain open. Nothing is deleted.
- Verified by: five lifecycle tests assert the new contract, and live on 1.17.0: c1 and c2 (below)
  finished with both lost attempts listed under `retained_superseded`.

**F1: losing the host mid-chain needs a person**
- Expected (SPEC S-6, S-14): after the host dies with workers in flight, a fresh session recovers
  the chain unattended.
- Observed: b1/b2-interrupt-temperature, 2/2 paused: `TaskStop` "No task found" for both handles,
  the chain guide forbids retry until stoppage is proven, so the session asked a person.
- Triage: check correct; the kill is deliberate, not environment; reproduced 2/2; traces to S-6 and
  S-14; the behaviour comes from a deliberate rule (`confirmed_stopped` before retry), so the owner
  decided.
- Decision: **owner, then product** (owner, 2026-10-03: "retry without proof"). `retry` accepts
  `confirmed_stopped: false` with `native_status: "unavailable"` in Plan Dispatcher and the chain
  bridge; the old attempt's workspace is kept, its late report is refused as stale.
- Verified by: Plan Dispatcher decisions S15 plus mutant `unconfirmed-retry-any` (18/18 mutants
  caught); chain-bridge test `test_lost_native_worker_is_retried_without_a_confirmed_stop_and_finish_keeps_it`;
  live on 1.17.0, 2 of 2: c1 and c2 recovered without a person (see "group C verification" below).

**Codex xhigh slowness (chain-seeded-codex-21de3d)**
- Expected: none was stated, so the run could not fail on time.
- Decision: **expectation**. Seeded chain cases now carry a should-level budget of 30 minutes (one
  background-task session), reported beside the verdicts.

## group C verification — 2026-10-04 — kill-and-resume on 1.17.0, Claude claude-sonnet-5-5 (ShipLoop 0.49.0, Plan Dispatcher 0.6.0)

Expected (SPEC S-6, S-14): after the host is killed with chain workers in flight, a fresh session
recovers the chain without a person; every verdict passes, including `recovery`.

| Run | Result | What the ledger shows |
|---|---|---|
| c1-interrupt-temperature-83752d | **PASS** every must verdict; budget over (30.9 of 30 min, should-level) | killed at 426 s with S1, S2 in flight; fresh session retried both (`native_status: unavailable`) ~70 s after resuming; replacements ran together (2 in flight); S3 after both; finish listed 2 kept attempts. Also killed once at the 30-min task limit in `handoff`; resumed, done in 22 s |
| c2-interrupt-temperature-f4c40f | **PASS** every verdict incl. budget (28.5 min) | killed at 761 s; same recovery path; $25.85 for its two sessions |

- Observed matches expected: F1 and F2 are fixed live, 2 of 2. The workspace return and release
  stages tolerate the kept attempt worktrees (both runs returned their product).
- Recovery cost: an interrupted seeded run took 28.5-31 min and about 2.5x the money of an
  uninterrupted one ($25.85 vs $8.60-11.20), because the killed session's work is replayed. The
  budget is should-level, so c1's 0.9 min over is reported, not failed. Open: whether interrupted runs
  should carry the same budget (the triage would call that an expectation question).
- Grader: both runs graded with the corrected in-flight count (2, not 4; 256883ce).

## dummy fan-out on 1.17.0 — 2026-10-04 — Claude claude-sonnet-5-5 (Plan Dispatcher 0.6.0)

- Question: did Ask Agent's new default (current workspace, 1.14.0) break Plan Dispatcher fan-out for
  non-Git steps? `fanout.py` writes stamps in a non-Git directory, where the current-workspace route
  allows only report-only workers.
- Observed: **PASS**. A and B native, 29.9 s of their 30 s overlapped, J after both
  (/Users/dadleet/shiploop-e2e-runs/fanout-claude-a67220). No regression; the model launched the steps
  as native workers directly. First fan-out pass on Claude (the 2026-09-27 pass was Codex).

## what a run leaves in the repository — 2026-10-04

- Fact: ShipLoop's execution worktree, every chain attempt worktree and every attempt branch live in
  the user's own repository's Git metadata. A fully passing run (b3-temperature) left three
  `ask-agent/...` branches and its `shiploop/run-...` branch; a recovered run (c2) left five attempt
  branches, two kept attempt worktrees and the run branch. Nothing told the user.
- Decision (owner, 2026-10-04): ShipLoop keeps never deleting them; the report lists them with the
  exact removal commands, and the completion packet says how many there are. Commands use
  `branch -d` wherever the branch is merged and never `--force`; nothing is offered for removal
  before the run is returned (an unreturned run's branches hold its work). A kept attempt's worktree
  removal refuses when a lost worker left uncommitted edits.
- Verified by: `test_leftovers_offer_safe_removal_only_after_the_run_is_returned` (real Git: nothing
  offered before return; the offered commands run as written and leave only `main`; the kept
  worktree's removal refuses while it holds uncommitted work) and the report-section test; on c2's run
  the completion packet reads "Left in your repository: 6 branch(es) from this run, including 2 kept
  attempt worktree(s)".

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
- **Added value (clear):** *[superseded 2026-10-04, see Correction below: passes 2-4 changed only confirm clauses]* plan passes 1-4 found six real graph defects in 70 min (F-1 wrong supplier edge S6 from S4; F-2 duplicate-once and mutation
  order of the API; F-3 browser recovery output; F-4 S2 confirmation inspect -> execute; F-5 no inspection of the dependency files; F-6 non-deterministic S11
  confirmation). Step-plan passes 1-2 found four omissions in 97 min (F-01 rejection tests and docstrings; F-02 style note; F-03 README and local-skill fit;
  F-04 effort/benefit comparison), all against what the parent step-plan packet itself requires.
- **Wasted (clear):** *[superseded 2026-10-04: the streak was not reset; wasted is 4 min, see Correction below]* plan pass 5 (17 min, F-7) was a stale source label in Backchain's own scratch metadata; it reset the clean streak. No product impact seen.
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

#### Correction, 2026-10-04 later the same day (supersedes three claims in the ledger above)

Evidence: candidate digests in `review-records/action-N-review.json`; the clean streak in `pass-reports/action*-done-packet.json`; the pre-loop
candidate recovered from `pass-reports/pass-01-audit-input.md` (the script kept no copy); the step-plan snapshots `review-records/review-0N-candidate-plan.json`.

- **Superseded: "F-7 reset the clean streak".** The streak was 0 after every pass through pass 5, 1 after pass 6 and 2 after pass 7. F-7 changed no candidate bytes
  (digest `3853b978` before and after). Its marginal cost is the extra confirming pass 7 (4 min), not pass 5's 17 min. Clearly wasted: 4 min.
- **Superseded: "six real graph defects in passes 1-4".** Pass 1 (11 min) found F-1 to F-3 and edited 14 of 20 steps (+5.8 KB, inputs 56 to 58). Passes 2-4 (59 min) each changed
  one confirm clause (S2, S4, S11; +0.4 KB together). Whether a stronger confirmation changes what gets built is unjudged until the comparison.
- **Step-plan differs:** passes 1 and 2 (97 min) both changed the structure (step D3 added, 16 steps changed); passes 3 and 4 changed nothing.
- **New, measured:** *[superseded below: the throwaway check omitted invariant 4]* a throwaway structural check (unique ids, existing suppliers, no cycles, declared null origins) passes on the pre-loop, after-pass-1 and final plan candidates, so a
  validator saves no minutes; requirement-id mention coverage (13 of 46 ids, identical before and after the loop) detects none of the findings and is rejected.
- **New, measured:** the `Backchain standalone Until Loop binding:` marker is in 0 of 6 files for the accepted plan and step-plan results; Backchain is optional and unchecked
  (all four Sonnet runs ran no loop); Sonnet's Improve plan reviews are 104 bytes each against 2.3 KB on Luna. Plan: `docs/shiploop-backchain-validator-comparison-plan-2026-10-04.md`.
- The run review page's ledger was corrected the same way: passes 2 to 5 are "cannot judge yet", pass 7 is "wasted", and a per-pass clean-streak strip shows the trace.

#### Second correction, 2026-10-04 (after an independent adversarial review of the plan; each point re-checked against the run)

- **Superseded: "a validator would have found nothing".** My throwaway check left out invariant 4. The reference validator (`harness/lib.js` in the Backchain checkout), run on the packaged candidates, passes the three
  plan candidates and **rejects both step-plan candidates** (`6f971770`, `024b3dc3`): discovered step D1 (added by pass 1's repair, the production Node entrypoint contract) is consumed by no step and satisfies no goal need.
  Passes 2 to 4 and Improve accepted it. Raw, every candidate fails invariant 6 because Backchain keeps `parallel_groups: []`, so the check must run on a packaged clone. The check saves no plan-loop pass, but it finds a real defect.
- **New, measured:** the step-plan loop ran an operation its packet does not allow: its caller packet names action `plan`, stage `draft` at `shiploop:step-plan`, while only the plan stage may request that (`BACKCHAIN_NATIVE_CALLS`); treat its numbers as off-protocol.
- **Corrected values:** pass 2 is +0 bytes, pass 3 +198 B, pass 4 +224 B (+422 B in all); "inputs 56 to 58" counts inputs (one new supplier edge and one new null-origin fact), not edges; the embedded pre-loop block plus a newline hashes exactly to the freeze-log digest `9e321e3d`
  (the recovery is byte-exact); F-7's cost is 4 to 12 min (one extra pass) plus its repair inside pass 5; `run/until-loop/` is empty in the Luna run too, so emptiness is not evidence that Sonnet ran no loop (no Backchain scratch directory and no receipt is); Sonnet's plan reviews run 98 to 439 bytes (104 bytes for battleship); the Sonnet battleship run took about 19 minutes.
- Plan: `docs/shiploop-backchain-validator-comparison-plan-2026-10-04.md` v2 (record-only first increment; no refusal gate until a script owns the loop contract; Track 1 starts from the planted draft; step-plan removed from the loop arm).

### Planning-size audit — 2026-10-04 — status: measured by an independent investigation, spot-checked (db61a4a7, effort, contradicting lines); causes by share are inferred

Question (owner): the planning stages look excessively large; is a planning prompt wrong? Evidence: `graph-dry-run` per release, the Luna 1.16.1 and Sonnet 1.16.0 battleship runs.

- **Packets barely regressed.** Producer packets (KB), full packet at spec / test-strategy / plan / test-spec / step-plan stays 29-44 at 1.0.0 and 37 / 31 / 50 / 49 / 28 at 1.16.1 (20-24% over the whole range). The printed head shrank tenfold at 1.5.0 (ff1e33b5 split head and file) and grew about 0.9 KB at 1.12.0 (91915885, the S-15 narrative).
- **The named reading grew 40% at 1.16.0.** `db61a4a7` (2026-09-28, "select installed Backchain and Until Loop resources explicitly", a justified fix for stalled planning) prints the six-file resource list at every `BACKCHAIN_STAGES` stage (spec, plan, step-plan, carry-forward, product-acceptance): reading per planning stage 220 KB at 1.15.0, 306 KB at 1.16.0. Before it the loop was probably unreachable (it required an Until Loop SKILL.md the bundle does not ship).
- **A packet invited a route it forbids.** The step-plan caller packet names action `plan`, stage `draft`; step-plan allows audit and, after a finding, repair or revise. The loop cost 136 of 592 planning minutes (23%). **Superseded in part, 2026-10-04 (the text is inconsistent, but it is not shown to be the cause):** the Luna events show the model chose a whole `plan`/`draft` loop before reading any step-plan packet text. The 5,250 B head it received after the select-work `complete` (events.jsonl) never mentions Backchain, and its next message announces the Backchain planning skill before it opens the full packet. The likelier source is context carried over from the plan-stage loop and the stage-less "whole `plan`/`draft`" wording in SKILL.md; cause unproven (one run). I2b therefore claims measured size and a consistent gate, not a loop fix (`docs/shiploop-i2b-trim-planning-prompts-plan-2026-10-04.md`).
- **Time by cause, Luna first work item, 592 min (inferred from timestamps):** step-plan loop 136 (23%), plan loop 128 (22%), Improve review loops 186 (31%), Improve opening files 35 (6%), producer stage work 107 (18%). Sonnet got the same packets and planned in about 4 minutes (stages 0.3-1.4 min; whole run 19 min), so packet size is not the driver; effort and the loops are. Luna ran at effort max (`invocation.json`).
- **Same request, planning artifacts (KB), Luna / Sonnet:** spec 20.8 / 2.0, test-strategy 42.6 / 3.5, plan 32.1 / 0.8, test-spec 27.3 / 2.3; Improve passes per stage 4/11/3/3/5 against 3/3/3/1/3. Luna's loop instructions scale with the number of outcomes (a criterion and confirmation each), the 42-lens screen and the exact-replay rule do not.
- **Plan loop, per pass:** parent made 17-43 tool calls per pass and the passes ran in a worker; each review record is 36-39 KB, about 60% a copied 14 KB lens screen plus identity fields; before the loop the parent made 170 calls (36 guidance reads, 191 KB), before the step-plan loop 58 guidance reads (497 KB, Backchain SKILL.md opened 10 times); 29 whole reference files (287 KB) were read across both stages.
- **Contradicting rules (verified):** `convergence.md` 69-77 asks every pass for actual reads of applicable cards and an all-42-lens screen; `technical-lenses.md` line 3 says to screen all categories once and not paste the library into every call; `convergence.md` 17-20 says to read the card and adapter reference in full against the printed head's "never a whole reference file". `backchain-planning.md` 272 calls the plan-stage loop optional ("may request") while the packet says the action must not be submitted without its result.
- **Justified, keep:** per-outcome confirmations (`backchain-planning.md` 80-98), `PLANNING_REVIEW_FOCUS`, the S-14 text, the state-budget rule, Improve after Backchain (it found a UI fix seven Backchain passes missed).
- **Action:** plan iteration I2b (`docs/shiploop-backchain-validator-comparison-plan-2026-10-04.md`, Part C): print the loop text and resource list only at `plan`; cut the repeated identity and digest text; records point to the existing lens screen. Screen-once is a rigor change and waits for the comparison.

### Run Review exporter, first real exports — 2026-10-04 — status: measured

- `export.py` on the active Luna 1.16.1 run, Sonnet battleship and Sonnet hello: 36, 48 and 35 accepted actions; wall time 1024, 19.1 and 13.4 min; planning documents 146 KB, 15 KB and 8.5 KB; Improve 7 children and 21 passes, 10 and 24, 8 and 12. Stage minutes come from accept deltas: Luna test-strategy 94.3 and plan 196.4 where the harness metric reports 223.6 and 39.2 (confirmed again). Its plan-loop pass minutes (11, 15, 26, 18, 17, 12, 4) and step-plan passes (42, 55, 6, 4) match the hand-built ledger.
- **Defect:** `metrics.json` `improve_children` counts each child's directory and its `-bind.md` file (16 for 8 children), so earlier notes saying "14 children" for the Luna run meant 7. The exporter counts directories.
- **Defect (fixed, 04af25ba):** a regrade of a finished run was refused by the version gate whenever the branch had unpushed commits, and `test_resume_run_on_a_finished_run_regrades_it_without_starting_a_host` depended on real git state. A regrade starts no host, so the gate no longer applies and the test patches the gate to a failing value.
- **Caveat:** for an active run `metrics.json` is stale (refusals and glue as of the harness's last write), so the page's Luna run uses the live counts; `carry-forward` belongs to Integrate in the stage spec, so Luna reads Integrate running.

### Backchain graph check, I1 and I2 — 2026-10-04 — status: measured on a recorded corpus (88 verdicts)

- **What shipped (unreleased, branch f3-budget-all-backchain-stages-f05ed2):** `shiploop_backchain_graph.py` ports Backchain's `lib.js` structural check to stdlib Python (`schemaErrors`, `validateStructure`, `completionStatus`, `unconfirmedProduces`, `computeParallelGroups`, packaged `packagePlan`), pinned to `test/fixtures/backchain-check`: 23 good and 28 bad structural fixtures, five Luna 1.16.1 candidates and 32 edge plans, recorded from Backchain `865547b` (`lib.js` `a9b99125`). The port reproduces all 88 exactly, packaged and raw: invariant, message, detail and the sha256 of the packaged text. `shiploop backchain-check --candidate PATH [--run-dir RUN]` prints a `shiploop-backchain-check/v1` receipt and records content-addressed files under `<run>/backchain/<action>/`; it changes no state and refuses nothing. Producer Backchain packets gain two additions: a 131-byte guidance line and the navigator's printed command (with `--run-dir`), not in Improve-pending packets; plan v2.1 (this commit) corrects the plan's "one packet line" and "sort every set" (the port keeps JavaScript insertion order because the verdict text depends on it).
- **Finding (firm, replaces the earlier hand-reading):** the three Luna plan candidates (pre-loop `9e321e3d`, after pass 1 `b66d62f0`, final `3853b978`) pass once packaged; both step-plan candidates (`6f971770`, `024b3dc3`) fail invariant 4 for discovered step D1. Every raw candidate fails invariant 6 because Backchain keeps `parallel_groups: []` and packages the groups afterwards, so the check must run on the packaged form.
- **Finding:** four structural "bad" fixtures with stored groups pass once packaged, so each verdict records the raw result too. `lib.js` invariant 4 also exempts a discovered step whose produce is a substring of the goal sentence, not only one matching a `goal_needs` entry.
- **Learning:** `lib.js` decides, not `SKILL.md`, and only JavaScript semantics reproduce it. Deliberate mutations each broke the corpus: Python `strip` or `\s` (control characters `\x1c`-`\x1f`, `\x85`, U+FEFF), Python key order (JS lists index keys first), a sorted cycle walk (JS reports the first cycle in insertion order), Python `str()` of stored group members and Python number text.
- **Integration note:** the verb adds one entry to the Grok adapter's allowlist, which changes its sha256. The implementer's quick tier failed `test_trace_corpus` on five host fixtures bound to that hash; its amended commit rebinds them after their golden attributions replayed unchanged. Anyone cherry-picking the first version of the I2 commit needs the amended one.
- **Deviations from `lib.js` (implementer's report, spot-checked by the corpus run):** input must be valid UTF-8 and nesting deeper than about 1,000 levels exits 3 ("could not run"), where Node would replace bad bytes or parse deeper; numbers echoed in failure details are written Python-style in the receipt (equal values; the packaged sha256 matches `lib.js`). **Open:** the receipt holds the candidate's absolute path, so checking the same bytes from another path rewrites `check-<sha12>.json` (the snapshot never changes); the verb works at any stage and writes under the current action; the run review exporter does not read the receipts yet; `ruff` reports an unused `action_id` in `shiploop_navigator.py` that predates this change.

### Callback path typos across the 1003 batch - 2026-10-04 - status: firm for the counts; independence and cause inferred; engine change deferred

Question: does ShipLoop need to change how a callback is printed or parsed, given paths with an inserted space in a Luna run? Plan: `docs/shiploop-callback-typos-plan-2026-10-04.md`. Evidence: `docs/experiments/shiploop-callback-failures-20261004/failures.json` (41 rows, 9 run summaries with per-session splits), written by the frozen `callback_failures.py` beside it from `/Users/dadleet/e2e-runs/20261003` (7 Claude Sonnet 5.5 runs; Luna max `battleship-luna` on 1.16.0 and `v1161-battleship-luna` on 1.16.1; no Grok run). The script reads only the first N lines of each run's `events.jsonl`, N recorded per run as `cutoff`; re-running at the recorded cutoffs gives a byte-identical file. The 1.16.1 Luna run was live (codex pid 63880), so its cutoff (7,171 lines, +18.83 h) is a snapshot and every Luna count can rise. The script is a one-time analysis that `metrics.collect` supersedes after metrics item M1 (Claude-shaped failure counting). [M] marks a count in the export, [I] an inference.

1. [M] 41 failed ShipLoop or Until Loop commands (nonzero exit; classes keyed on the typed command or on a refusal line at a line start):
   - 4 inserted-space paths (3 `shiploop complete`, 1 `until_loop next`).
   - 7 Until Loop script paths with the `until-loop/scripts/` segment dropped (U1).
   - 7 bare `shiploop next` (exit 127) and 4 older-cache refusals ("saved run state cannot be loaded"): together the Claude resume prompt that named a bare `shiploop` (fixed by 7c1f1014).
   - 15 refused on content, each with a `ShipLoop navigator:` or `ShipLoop blocked:` line at a line start. One (batch-sonnet seat-reservations, event 116) is a model script whose shell step failed just before the refusal.
   - 4 other: two Until Loop rejected-input packets (`battleship-luna`), one unmatched quote (v1161 event 5336), one model script whose bind step returned 127 (batch-sonnet battleship-scoring).
   - By host: Claude 15 (0 path typos), Luna 1.16.0 7, Luna 1.16.1 19.
2. [M] All 6 inserted-space paths are in session 2 of `v1161-battleship-luna`: the `codex resume` at +10.04 h (event 3180), typos at events 3999, 4285, 4857, 4982, 5526 and 5975 (+11.74 h to +16.54 h).
   - Three are callbacks: `shiploop complete` at 3999 and 5526 in `--result=`, at 4857 in `--run-dir=`. One is an Until Loop `next --state` path (4285). Two sit inside text: a heredoc that wrote a result file with a bad evidence path (4982) and an Until Loop handoff string (5975, exit 0).
   - Session 1 (events 0-3179): 41 callbacks, 1,469 typed paths, 0 typos. Session 2 (events 3180-7170): 52 callbacks, 1,532 typed paths, 6 typo commands: 3 callback typos (5.8%) and 4 failed ShipLoop or Until Loop commands. `battleship-luna`: 26 callbacks, 749 paths, 0 typos. "Typed paths" are path tokens under the runs root in every typed command, heredoc text included.
   - Claude assembles callbacks from shell variables: 141 of 149 recognised `complete` commands name the run dir by a variable (`$R`, `$W` or `$B`), 8 spell it out; 98 of 247 `complete ... --action` commands are not recognised by the CLI pattern. Its 0 says nothing about copying the printed path.
   - The at-risk population is Luna: 3 of 119 callbacks.
3. [M] The run-name explanation (`/20261003/ v1161-`) is contradicted. Session 1 typed that boundary 1,467 times with 0 errors; session 2 typed it correctly 1,527 times. `v1161-hello` (178 correct typings) is a Claude run and does not test it. Session age (a resumed `codex exec`, context 10 h old) is the only measured separator [I]; compactions are not visible in the Codex stream, so context age is unmeasured.
   - One-sided hypergeometric, all typos in session 2: 6 of 1,532 against 0 of 1,469 typings p=0.0176; 3 of 52 against 0 of 41 callbacks p=0.17 [I; consecutive typos are not independent].
4. [M] Correct typings between consecutive typos: 334 (from resume), 155, 246, 30, 247, 194 (path tokens from the previous typo command, inclusive, up to the next one). Since the last typo (event 5975) the session typed 326 more path tokens and 13 callbacks with no further typo, up to the cutoff. Each error was repaired correctly. "About one independent event" is unsupported: the readings run from 1 (contamination) to 6 events [I].
5. [M] Recovery: 10 of 11 path-class failures were repaired by the next call, one by +2 (Until Loop `done`, event 3067, 22.6 s). Total 110.2 s, 0.16% of the 18.83 h at the cutoff; the 3 failed callbacks cost 22.7 s, the 4 spaced commands 28.4 s, the 7 Until Loop script paths 81.8 s.
   - No state change: a mistyped run dir exits before `run_lock` ("no ShipLoop run directory", event 4857), a spaced `--result` value splits into an unrecognized argument and exits in argparse (usage, events 3999 and 5526), an Until Loop `next` with a spaced `--state` answers `state_change: unchanged` and the same unrecognized-arguments error (event 4285), a bad script path never runs. No stray ` v1161-battleship-luna` directory exists under the runs root.
6. [M] `_callback` (`shiploop_navigator.py`) is the one builder. `--result`, `--opening` and `--message` are `required=True` in `shiploop_protocol.py` and refused unless equal to the derived path (`_submitted_result`, the improve-commit, improve-start and improve-reconcile checks), so they carry no information. `run_dir_from_arg` (`scripts/shiploop`) walks up for `.shiploop` only, so `--run-dir` cannot be inferred for workspace runs. The printed result path is 131-157 characters in all nine runs (`result_path_len`). A typical layout prints 111, and a 355-character callback (234 without `--result`) [I: assumed layout].
7. [M] The failure metric is blind for Claude. `metrics.collect` reads only ACP `tool_call_update` events, so `metrics.json` has `shiploop_failures` of length 0 for all 7 Claude runs, against 15 failing commands in the export plus 28 refusals behind exit 0 in recognised ShipLoop commands (40 counting wrapper scripts that the CLI pattern does not recognise). The "Batch 1003 - Sonnet 5.5 results" table above says "0, 0" for four rows that hold 13 failures. Claude counts are lower bounds. The exporter already reads `metrics.shiploop_failures`, so M1 puts the one classifier in `metrics.collect`; the "0" cells are corrected by edit with a reason under M1, not here. **Superseded, 2026-10-08:** M1 is built (`metrics.ToolLog`, journal `docs/shiploop-batch-1009h-journal-2026-10-08.md`); the "0" cells above carry their corrected figures and the reason.

**Decision: defer the engine change (Item C: drop the derivable `--result`, `--opening` and `--message` flags from the callback).**
- Grounds: KISS (no break beyond a recoverable one-call cost) and Change admission's "cost more than it saves": Item C costs a release plus 18 test and fixture files to save about 28 s in an 18 h Luna run. Batch discipline also holds: no engine change while a run is live, one release.
- Accepted exception to S-4 and S-5 (a derivable path stays model-copied), with its cost: 4 failing commands, 28.4 s, 22.7 s of it on 3 callbacks, in 18.83 h of Luna max.
- Reopen Item C when either happens, on ShipLoop callbacks only (Until Loop paths are excluded; they are vendored argv, U1):
  - R1: a path typo in any run other than `v1161-battleship-luna` (any host, model, session or path length).
  - R2: a callback typo not repaired by the next ShipLoop command, or a run ending blocked because of one.
- The item stays monitored, never closed. A clean run is uninformative unless a resumed session types at least 1,442 paths with 0 typos [I].
- **2026-10-08: R1 fired.** `v1210-battleship-luna-xhigh` has three path typos, in the first `next --run-dir` of three of its four resumed sessions (see "Resume, stop and records" below). The decision stays deferred until the owner reopens it; nothing was built on it.

Where the export differs from the plan's counts (the Luna run kept going; the plan's session figures are from about event 6,752):
- Session 2 now has 52 callbacks and 1,532 typed paths (plan 47 and 1,442), the same 6 typo commands, 3 callback typos and 4 broken commands; Luna callbacks 119 (plan 114).
- The plan's p=0.017 does not follow from its own counts (6 of 1,442 against 0 of 1,469 gives 0.0147); it matches the later count (0.0176). Callbacks: 0.148 at the plan's counts, 0.17 now.
- The fifth typing interval is 247, not the plan's 249; the other five reproduce exactly.
- Refusals behind exit 0: 28 recognised and 40 in any command, against the plan's "about 30 (a reviewer counted 33)".
- "141 of 149 use `$R`": 141 use a variable run dir, 99 of them literally `$R`.
- All other plan figures reproduce: 41 failed commands and the 4/7/7/4/15/4 classes, 15/7/19 by host, session 1 (41, 1,469, 0), 110.2 s, 22.7 s and 28.4 s, 15 lines holding `20261003/ v1161` in the Luna events and none in the other eight, `shiploop_failures` length 0 for all seven Claude runs.

Next: when the Luna run ends, re-run `callback_failures.py` at the new cutoffs into `failures-final.json` (never overwrite `failures.json`) and update this section by edit. After every later long run, scan `shiploop_failures` for `unrecognized arguments`, `no ShipLoop run directory` and `can't open file`, and test R1 and R2.

### I2b prompt trim, built locally - 2026-10-04 - status: built, live behaviour unverified

Question: can the Backchain loop text and its resource list print only at `plan`, the one stage that may request a whole `plan`/`draft`, while spec, step-plan, carry-forward and product-acceptance keep the read-only audit route, without dropping a justified obligation? Anchors: S-7, S-6, S-3, S-5 and the owner rule "concise, aimed at meaningful change" (2026-10-04). Plan: `docs/shiploop-i2b-trim-planning-prompts-plan-2026-10-04.md`. Base f9096bb1 (tip of f3-budget-all-backchain-stages-f05ed2: it holds the validator verb and `BACKCHAIN_CHECK` line, the contract budget text 112b239c and the exporter). Built in worktree i2b-cd98de, branch i2b-trim-planning-prompts-cd98de, one local commit; not pushed, not released, no E2E run started.

**What changed (symbols, not line numbers).**
- `shiploop_prompts.py`: `_backchain_guidance` is assembled from four constants, `_BACKCHAIN_ROUTE` (all stages), `_BACKCHAIN_PLAN_CALL` (plan only: resource gate, record rules, plan-only child, and the E4 sentence that sends capability, old-custom-loop and no-fallback rules to the guide's "Source-aware native caller"), `_BACKCHAIN_AUDIT` (the four audit stages; E1 adds "A whole `plan`/`draft` is requested only at `plan`" and "A MISSING loop resource blocks repair/revise; no other install substitutes") and `_BACKCHAIN_IMPROVE_OWNER`. `BACKCHAIN_AUDIT_RESOURCE` is the one definition of the audit resource's label inside `resolved_backchain_resources`; `backchain_skills_root()` is the one resolver of the skills root.
- `shiploop_navigator.py` render block (E2): the full "Selected Backchain and Until Loop resources" list prints only in a producer packet at `plan`. Elsewhere a "Backchain audit resource (backchain-caller/v1 contract; operation review/audit)" line prints; the four producer audit stages add one script-computed line, "Loop resources for a repair/revise request, under <skills root>: all present" or "MISSING: <labels>" (S-5: the script reports what the host would otherwise check by hand). A bound Improve child gets the audit line only. The pointer and graph-check lines are unchanged.
- `references/backchain-planning.md` (E3): the selection-block sentence is plan-only and the other stages are named; the Owner binding sentence matches; the identity paragraph ("The durable selection record...", 154 words) is a 56-word record paragraph that keeps the five record field names; a two-sentence paragraph states what the other stages print. 2,593 to 2,578 words.
- Kept, each justified earlier: the route sentence at all five stages, the plan-only child paragraph, the budget paragraph (112b239c) and `BACKCHAIN_CHECK` (pinned by the validator) untouched, the native tail at plan, `read-only, one-pass diagnostic`, `exactly one repair/revise`, bounded edit authority, "incomplete, not submitted", `one-pass Backchain primitive`, `These restrictions belong to that Backchain child`, the guide's per-outcome confirmations, `PLANNING_REVIEW_FOCUS`, the S-14 text, Improve after Backchain.
- Left out: the reference patch's Backchain-skill hunks (`convergence.md` x3, `convergence-review.prompt.md`, the Backchain note): they belong to I2c (lens screens). The patch's word-limit test and its `dropped` phrase list are not carried (E5): the repo rule is no packet-size bound.
- Change note `changes/shiploop/trim-planning-prompts.md` (`bump: patch`): states the print rule and the shorter text; no claim about loops.

**Counts, measured by `graph-dry-run --scenario delivery --format json` (the plan's Verification 3 command) on the old tree (a `git archive` of f9096bb1) and on the new tree.** Words and UTF-8 bytes of `_backchain_guidance(stage)` as the producer packet prints it; packet bytes are the dry-run producer prompt, both measured from the same worktree path so path length cancels.

| stage | guidance words before / after | guidance bytes before / after | packet bytes before / after | list printed (before / after) | audit line (before / after) |
| --- | --- | --- | --- | --- | --- |
| spec | 688 / 301 | 5,099 / 2,106 | 35,185 / 31,379 | yes / no | no / yes |
| plan | 707 / 480 | 5,303 / 3,397 | 46,715 / 44,809 | yes / yes | no / no |
| step-plan | 688 / 301 | 5,099 / 2,106 | 46,592 / 42,786 | yes / no | no / yes |
| carry-forward | 688 / 301 | 5,099 / 2,106 | 33,130 / 29,324 | yes / no | no / yes |
| product-acceptance | 688 / 301 | 5,099 / 2,106 | 31,031 / 27,225 | yes / no | no / yes |

Improve-owner text, every Backchain stage: 509 to 132 words, 3,846 to 946 bytes. Each audit-stage packet is 3,806 B smaller (8-12%), plan 1,906 B (4%). The before figures equal the plan's measurement of 1.18.0-era text plus the local budget and check line (688/5,099 and 707/5,303), so the base is the one the plan assumed. The after figures run above the plan's patch-only 454/281/132 by E4 (+26 words at plan) and E1 plus the status-line wording (+20 words at the audit stages), as the plan expected. Word and byte counts are recorded, not pinned.

**Suites** (each run from the worktree, exit code captured before any filter). Baseline on the untouched base, then after the change: dry-run 12 to 16 tests, contract 52 to 55, guidance 36, backchain-check 20, actual-improve-cli 32, delegation 44, packet-bounds 8, package-integrity 7, reference-routing 4, navigator-v4 17; all ten rc=0 both times. The plan's expected counts (16, 55, 36, 20, 44) match. The quick tier (`bash test/run-all.sh --group quick --changed-from f9096bb1`, receipt outside the repo) selected and passed 27 of 27 suites, rc=0.

**The new tests fail without the change.** Checked by exporting the whole base tree (`git archive f9096bb1`), overlaying only the two new test files and running them there: contract 11 failing entries across 6 of the 55 tests (the producer and child packet views, the plan `required` list, the missing-resource sentence, and the three status-line tests), dry-run 12 failing subtests across 3 of the 4 new tests. The fourth, "the packet carries exactly the stage guidance", is a consistency invariant that holds on both trees by design. The pins are content and absence pins (what a stage prints or omits), none on words or bytes.

**Why the trim is justified by size and a consistent gate, not by a loop fix.** On the Luna 1.16.1 run (`/Users/dadleet/e2e-runs/20261003/v1161-battleship-luna`, events.jsonl, 0-based line index), line 2178 is the `shiploop complete` call for select-work; line 2179 is its output, the step-plan head, 5,250 B of text that never mentions Backchain (I parsed the text and searched it case-insensitively); line 2180 is the model's next message, "W1 is confirmed as the required integrated item. I'm using the Backchain planning skill to make its implementation and verification sequence executable...", and line 2181 is its first `cat` of the full step-plan packet. So the decision to start a whole `plan`/`draft` loop at step-plan predates any step-plan packet text; the packet text cannot have caused it. The likelier sources are the context carried over from the plan-stage loop and SKILL.md's "Source-aware Backchain selection", which calls a selected `plan`/`draft` or `repair`/`revise` one whole operation without naming a stage (inferred, not tested). The earlier planning-size bullet "A packet invited a route it forbids" stays true as an inconsistency between the caller packet and the stage's allowed operations and is marked superseded above for causation. Whether any packet text matters to that choice is unknown; a recurrence points at SKILL.md and carried context, and at a script-written loop contract (S-5/S-10), not at more trimming. n=1, Luna, exploratory.

**Step-plan wall time, method exported.** `docs/experiments/shiploop-step-plan-minutes-20261004/step_plan_minutes.py` (head line to complete line through `timeline.jsonl`; read-only) reproduced 163.9 minutes on the Luna 1.16.1 baseline (head line 2179, complete line 2950), run here on the live run directory without writing to it. The harness's `metrics.json` shows 1,679.5 s (28.0 min) for the step-plan stage in that run: superseded 2026-10-04 as a measure of the stage's wall time (misattributed, per the plan; the cause was not investigated here, and for an active run the file is also only as fresh as the harness's last collection).

**Plan versus code, found while building.** The plan and the patch call the list a "six-file" list; `resolved_backchain_resources` returns seven entries (the audit resource, `caller-contract.md`, is also one of the seven the plan packet requires), so the status line covers all seven and names the audit resource too when it is the missing one. The plan cites a LEARNINGS.md "superseded 2026-10-04" mark for the metrics.json step-plan minutes; the base marks only the plan stage's 39.2 min as superseded (187db6dd), so this section records the step-plan figure and its supersession itself. The plan's Part C and I2b-row edits (`docs/shiploop-backchain-validator-comparison-plan-2026-10-04.md`, the master plan table) are left for after live verification, as the sequencing document says.

**Unverified.** Live behaviour: whether a Luna max battleship run on a release carrying this text still starts a whole `plan`/`draft` loop at step-plan (V2 signals a, b, c of the plan: no resource block in step-plan packets, no `plan draft shiploop:step-plan` scratch contract, step-plan minutes against 163.9). A seeded run cannot confirm it. No hello or battleship run was started for this entry. Rollback: `git revert` of the single commit before release.

Related commits: db61a4a7 (resource list at every Backchain stage), 112b239c (contract budget at every Backchain stage), bd3cffd3 (refuse a contract that leaves no room for the first report), 931c53e2 and 6a997a02 (backchain-check), 30d60c14 (planning-size audit and plan Part C), 187db6dd (Backchain ledger and the plan-stage minutes misattribution), f9096bb1 (the plans), ff1e33b5 (packet head and file split, the S-7 basis).

### Luna max battleship on 1.16.1, final — 2026-10-04 — status: firm for this run (one run, one model)

- **Outcome.** The resumed Codex session (`gpt-6-luna`, effort max, `--timeout 36000`) ended itself after 9.29 h with `end_turn`: ShipLoop `blocked` at `system-test`, revision 57, 39 accepted actions in 1,158.5 min (19.3 h) from start to the last accept, 2,189 turns in the resumed session, no report. Verdicts: invoked pass, process pass, committed pass, plugin fail, shiploop fail, checks fail. The harness's `checks` run against the work directory, where the candidate was never released; the same commands pass in the run's worktree (`node --test` and the live requests). Evidence: `test/shiploop_e2e/evidence/codex-gpt-6-luna-1.16.1-battleship-20261003.json` (the compact Run Review export), run directory `/Users/dadleet/e2e-runs/20261003/v1161-battleship-luna`.
- **Stage minutes (accept to accept, from the export):** step-plan 216.2 (2 visits), plan 196.4, test-spec 128.6 (2), test-strategy 94.3, implement 77.8 (8). Improve: 9 children and 41 review passes (the harness's `improve_children` of 18 counts each child's directory and its `-bind.md` file, observation o31). 13 ShipLoop command failures (complete 8, improve-start 4, improve-commit 1), 21 model-glue commands, 0 truncations, 0 questions to a person. Planning documents 157.7 KB in 9 files; packets 1,788 KB.
- **F3 held live, four more times:** both Backchain loops closed (plan 7 passes, step-plan 4). Of the four `improve-start` refusals, three were the new size guard doing its job at start, before any work: a 12,478-byte contract at test-strategy (3,262 over; the refusal named Environment 4,172 and Current context 2,993 as the largest parts), 10,005 at plan, and 9,487 in the resumed session at system-test-author (271 over); each was shortened and accepted on the next call. The fourth was an empty required section. The packet had already printed the allowance (about 4,686 bytes for the text a model writes), so Luna exceeds a printed budget by up to 2.6x and the refusal at start is what makes it converge; a script-written contract (a02) would remove the guess.
- **System test ended the run (new finding, status open):** all five registered Node suites passed on the real candidate (16 of 16). The test strategy, written three stages earlier, had planned two required browser cases (`SYS-BROWSER-PLAY-13`, `SYS-BROWSER-RECOVERY-14`) that need a person with DevTools; the model marked the stage `blocked` and ended on the `awaiting` route. SPEC S-14 says a step that needs a physical observation records an open item and continues with everything that does not depend on it; `testing-and-documentation.md` says a required browser check without its capability stays blocked or unverified. The two rules do not say what the run does next, and product-acceptance, release-plan, release-check and the report never ran (`Release none`). Action a13 on the page: decide from what the later stages need before changing text.
- **Grading defect (open):** the resumed process graded `plugin` as failed with `loaded: []`, while the first process of the same run graded it true: the resume path carries no evidence of the original install. The process that graded it ran harness code from before the exporter and the regrade fix, so it wrote no `review-export/` either; the export above was produced afterwards from the run's own records.
- **No baseline row.** A resumed run writes none. The `2026-10-04T01:54:32` row in the batch worktree's `baselines.jsonl` is the first process's timeout row (process false, turns 0), not a verdict for this run; it is not committed.
- **Why it took 19 h against Sonnet's 19 min on the same request:** the loops and effort, not packet size (planning-size audit above). Two releases (1.17.0, 1.18.0) were published while it ran; the run kept its installed 1.16.1 copy, and a resume after a death would have been refused by the version gate.

### Verification of skill-craft 1.19.0 — 2026-10-04 — status: measured (one to two hello samples per release)

- **Published and refreshed.** Release commit `19fa890d` (skill-craft 1.19.0, ShipLoop 0.51.0, shiploop-e2e-audit 0.6.0) pushed through `release-push.py` with its head, tree and base pinned; the full CI tier on it passed in 18.8 min. `--preflight-only --host all` reported 1.19.0 / 0.51.0 and 0 unreleased notes on Claude (origin/main export), Codex and Grok (fresh-profile installs). The real installs were refreshed after CI went green: Claude 1.18.0 to 1.19.0 (a restart applies it), Grok 1.16.1 to 1.19.0 (`grok plugin update skill-craft` accepts the plain name), Codex last, with no live Codex session, to 1.19.0.
- **Hello gate passes.** Sonnet 5.5 (`--source marketplace`): all five verdicts true, both checks pass, 0 ShipLoop failures, 0 glue, 0 questions to a person, a non-empty review export. Evidence: `test/shiploop_e2e/evidence/claude-claude-sonnet-5-5-1.19.0-hello-20261004.json`.
- **The cost of the same request keeps rising (status: superseded 2026-10-04 by "Hello cost analysis and Claude connector isolation" below: the rise is not shown to be release-linked; the environment was uncontrolled).** Four hello runs, every one passing with 0 failures:

  | Release | Turns | Cost | Improve children / review passes | Children done in one pass |
  | --- | --- | --- | --- | --- |
  | 1.16.1 | 143 | $3.30 | 8 / 8 | 8 of 8 |
  | 1.18.0 (checkout of `4f237af4`) | 167 | $4.39 | 8 / 18 | 3 of 8 |
  | 1.19.0 gate | 194 | $5.37 | 8 / 14 | 5 of 8 |
  | 1.19.0 repeat | 254 | $7.33 | 11 / 19 | 7 of 11 |

  The rise starts before this batch (1.18.0 is already 17% above 1.16.1), the repeat split the request into two work items, and the largest per-stage growth is in the Improve-wrapped stages (carry-forward 4, 8, 18 and 12 turns; spec 18, 24, 24 and 36) *[superseded 2026-10-04: those stage figures were attributed from result-file times; A2 attributes from the engine's accept stamps, which gives carry-forward 5, 8, 13 and 12 and spec 19, 30, 26 and 40 for the same four runs, totals unchanged; see "A1 to A3 landing and review"]*. With one or two samples per release only the direction is established. The earlier expectation of 143 to 155 turns and $3.3 to $3.7 was a band inferred from two runs; it is removed with its reason on the page (iteration I2r), and action a14 asks what Improve's first pass changes before any text is touched. Evidence for all four runs: `test/shiploop_e2e/evidence/` (the 1.18.0 run is a checkout of the published commit, not a marketplace install).
- **Not verified live by this run.** A Sonnet hello starts no Backchain loop, so the `backchain-check` receipt, the size guard inside a looped stage and the I2b trim are covered by tests only until the next looped Luna run; the step-plan whole-loop question stays observational (observation o32).
- **Baseline rows:** the two 1.19.0 marketplace rows (194 and 254 turns) are committed with this entry; the 1.18.0 checkout row is not (it is a checkout, kept in its evidence file).

### Hello cost analysis and Claude connector isolation — 2026-10-04 — status: measured by a read-only investigation, quotes spot-checked; cause of the Oct 3 to Oct 4 step not determined

- **Nothing the Improve review reads changed.** `git diff` of `skills/improve` between 1.16.1 and 1.19.0 is empty; `PLANNING_REVIEW_FOCUS` and `END_REVIEW_FOCUS` are byte-identical in the packets of all four hello runs; the `shiploop_prompts.py` changes are Backchain guidance only (`112b239c`, `3592b195`), and `backchain-check` was never invoked in a hello run. The 0 of 8 to 5 of 8 jump in first-pass changes (2 of 16 children on Oct 3, 12 of 27 on Oct 4) is clustered by day, so sampling or environment, not a release.
- **Most first-pass findings were real.** Of 12 first-pass changes in the 1.18.0 and 1.19.0 runs, 9 fixed a defect against the stage's review focus (replayable confirm-by commands, a spec/test count mismatch, a vacuous test, a rollback claim checked by running the tool), 3 were marginal or churn. The 1.16.1 baseline looks cheap partly because its reviewers let the same defect classes through (its notes hard-code "no defect, no edits", six children took 0 to 1 s). Passes 2 and 3 changed nothing in any of the 12.
- **Decomposition.** The 1.19.0 repeat's extra $1.96 over the gate run is 73% one refusal-triggered replan: `system-test-author` recorded a shell pipeline as suite `focused`, ShipLoop refused it ("could not read how many tests it ran"), and the model added a docs-only second work item, forcing select-work, step-plan, a second run and a second system-test (about $1.44). The `system-test-author` guidance names suites `focused`, `regression` or `check` without defining `check`; only the step-plan text does. Wait for a recurrence before touching it. From 1.16.1 to the repeat (+$4.04): that wave 37%, Improve extra passes at most 8% (all Improve activity about 22%), everything else about 42%.
- **The environment was not controlled, and that is now fixed.** The 1.18.0 and 1.19.0 gate runs loaded 15 claude.ai connectors (174 tools, several shown connected, among them Interactive Brokers and Docusign) into an unattended run, while 1.16.1 and the 1.19.0 repeat loaded none (28 tools); Claude Code moved from 2.1.288 to 2.1.289; two of the runs ran concurrently; initial context was about 60k tokens against 54k. A probe with one turn confirmed the cause: a plain launch with `--setting-sources project,local` loads 15 connectors and 174 tools, and adding `--strict-mcp-config` loads 0 and 28. `ClaudeHost.argv` now passes `--strict-mcp-config` (test pinned in `test/shiploop-e2e.test.py`, README isolation paragraph updated).
- **Measurement caveats for these tables.** `metrics.json` `turns` counts assistant content-block events, about 1.7 times the API calls (84, 94, 113 and 149 real calls for the four runs); `cost_share_usd` is the run's cost times a stage's turn share, not a measured stage cost; stage turns come from result-file mtimes and jitter between neighbouring stages, so a stage showing 0 turns is boundary jitter. The stage tables above are indicative only. *[superseded 2026-10-04 in part: `cost_share_usd` and result-file times no longer exist (A2). Stages now come from the engine's accept stamps; the jitter that remains is those stamps being whole seconds, which puts a boundary turn in the next stage at about a quarter to a third of boundaries. The "indicative only" caveat stands; see "A1 to A3 landing and review".]*
- **Status and next measurement.** The release-linked reading of the hello cost rise is not supported; noise between the two same-release 1.19.0 runs ($1.96) is larger than the release-to-release steps ($1.10 and $0.98). If the owner wants it settled: an interleaved serial A/B of three 1.16.1 and three 1.19.0 hello runs on Sonnet 5.5 with the connector isolation (about $28); a clean 1.16.1 that now changes at least 25% of children means drift, one that stays at 2 of 8 or fewer and costs $1 or more less in two of three pairs means bisect (`1ff8c841`, `b97c3a0a`, `19fa890d`). Observations o37 to o39 and actions a14 to a16 on the page.

Note (2026-10-04): every Claude run in batches B and C (and the seeded/full chain runs of 2026-10-03)
used the harness before bc3046db, which loaded the user's claude.ai connectors into the unattended run.
Their verdicts stand, but their token and cost figures include the connectors' tool definitions.

## Harness contract change — 2026-10-04 — status: firm (hermetic tests); not yet seen in a live run

Not a run entry. It changes what the next run records and what it compares against, so read it
before the next baseline comparison. Full reasoning, measurements and the change-admission
record: `docs/shiploop-graph-engineering-comparison-2026-10-04.md`.

- **Baselines now compare only within one host, model and effort** (SPEC: the driver is a
  parameter). `baselines.jsonl` rows gained `host`, `model`, `effort`, per-stage rows and
  `termination`; `previous_row` requires all three to match. **The 12 existing rows name none of
  them, so they are no longer used as baselines** *[corrected 2026-10-04: 13 rows at that commit, 15 after the 1.19.0 hello rows; none names host, model or effort]* — the next run per case/host/model/effort
  prints no comparison and becomes the new first row. That is deliberate: those rows mixed hosts.
- **Per-stage attribution reads ShipLoop's own records**, not result-file mtimes: `state.md`
  history joined to `timeline.json` by action id, carrying each stage's `outcome`. A stage the
  engine could not stamp reports `timing: "unavailable"` instead of a zero-length window, and so
  does the stage straight after an unstamped one, whose window covers both.
- **`cost_share_usd` is gone.** It was one total redistributed by turn count, so a price change
  or expensive work elsewhere moved a stage's dollars. Total cost stays whole-run.
- **An unfinished run now attributes the stage it never accepted** (an `incomplete` row), which is
  the stage an attrition question is about. Of the 11 recorded protocol-4 runs, 7 reached
  `handoff`, 1 blocked at `plan` and 3 were left active; the worst now reports
  `carry-forward never accepted`. *[superseded 2026-10-04: that snapshot was taken while the Luna battleship run was still in flight; it ended `blocked` at `system-test` (see "Luna max battleship on 1.16.1, final"), so that run is no longer one of the active ones (the design document, section 4.2, counts two abandoned runs that stay active in the record) and its unaccepted stage is `system-test`.]*
- **`result.json` and each baseline row carry `termination`**: process status and return code,
  each session's own stop reason, why the driver stopped resuming, and the engine's status and
  unaccepted stage. `unknown` is kept rather than guessed, and a ShipLoop refusal is never
  reported as the cause.
- **`script_verifications` gained `could_not_run`**: attempts where no command reached a verdict
  about the product. ShipLoop no longer counts those toward its 7 refused runs, so an environment
  problem cannot rewrite a work item's step plan. Expect `0` on a healthy run; any non-zero value
  is an environment problem, not a product one. *[superseded 2026-10-04: a non-zero `could_not_run` means no verdict about the product was reached, which is an environment problem or a product hang; the harness cannot tell them apart, and A1's own record says a timeout is not a diagnosis.]* **No case exercises a slow or breakable suite, so
  these paths have never run live** — that is the open evidence gap for that engine change.

### A1 to A3 landing and review - 2026-10-04 - status: reviewed; follow-up fixes in flight

Question: do the landed A1 to A3 changes hold up under adversarial review, including their interplay with what the release line shipped while they were being built? Design, measurements and the change-admission records: `docs/shiploop-graph-engineering-comparison-2026-10-04.md` (sections 8 and 10). Evidence: `docs/experiments/shiploop-a1a3-review-20261004/` (compact findings export and the group table with dispositions).

**What landed.** Three commits from the graph-engineering session, authored on the 1.17.0 release commit `1ff8c841` and merged onto the 1.19.x line as `9db0be37` (the only conflict was this file): `0d8d32f9` (A1: a test run that reaches no verdict is `could-not-run`, not a product failure), `3c604304` (A2: stage attribution from the engine's own records and baselines compared within one host, model and effort; A3: the harness records why a run ended) and `e469f2a4` (the design document). Hermetic suites were green on the branch before the merge (test-loop 31, harness 100). No live run has exercised any of it.

**The review.** Four scopes (A1, A2, A3, the integration with the release line) by three lenses (rules, adversarial, runtime); each finding verified by two skeptics; 186 agents; reproductions ran against the integration branch and the recorded runs under `/Users/dadleet/e2e-runs` (read-only or on copies). The agent models and effort are not recorded in the exported dossier. Result (status: firm for the 68 findings both skeptics confirmed, interim for the 10 with one dissent): 78 confirmed (30 major, 48 minor; 68 by both skeptics, 10 by one), 9 further candidates rejected by both, in 16 groups (the review's grouping file lists 16). By group: revise route refused after could-not-run (4), budget-skipped command (1), hosts without per-turn usage (8), Claude per-call counters (2), `stage_diff_lines` (5), Claude API error as success (4), `session_stops` not per session (3), regrade records (6), marketplace-branch regrade (1), missing tests (3), missing admission records (3), keepalive premise (3), A2 edge cases (19), A1 minor (6), no comparable baseline (1), stale documentation (9).

**The material findings.**
- The route out that A1's refusal names (`revise`) is refused at `test-green` and `regression` (`check_terminal` unlocks it only when `refused_runs` reaches the cap, which could-not-run attempts never advance) and at `static-checks` (the quality loop has no bypass), so the "mitigated" dead end of the A1 record was not. The keepalive's 14-continuation release is the only terminator and its notice names the refused outcomes.
- Counters a host does not report are recorded as measured zeros: Codex has no per-turn usage, so 39 of 39 stage rows of the recorded Luna run say 0 turns against 2,189, and `stage_diff_lines` then prints "no per-stage turn difference"; on Claude the per-call counters are zero by construction.
- The termination record fabricates a host exit on a regrade (`--resume-run` on a finished run starts no host, yet the record says "host exited rc=0") and records a Claude session that died on an API error as stop `success`.
- A regrade through the marketplace branch of the version gate (another host, or a missing plugin directory) overwrites a finished run's passing `result.json` with a failing stub.

**Process learning.** The other session's change-admission record covered only A1, on the reading that harness observation needs none; SPEC has no such exemption, and the admission its harness changes lacked is exactly where these findings sit (silent failure, broken saved runs, a metric that misleads). Separately, a change set built on a stale base needs a review of its interplay with what shipped meanwhile: here the 1.19.0 baseline rows, the keepalive's dependence on `MAX_REFUSED_RUNS`, and the Run Review exporter's own stage minutes. The caller search for A1 (`test_loop.verify(`) missed the dependents of a constant and a restriction.

**What this commit fixes (docs and journal only).** Retrospective admission records for A2 and A3 and a corrected A1 record in the design document; symbol citations instead of line numbers; test count 7 (not 6); the two attributions (metrics and exporter) stated with what each is used for (first stage 16.0 s in the exporter, 21.3 s in `metrics.json` on the 1.19.0 hello gate run); the README's per-stage, baseline-identity and termination text; and the superseded marks below. Baseline rows: `baselines.jsonl` held 13 rows at A2's commit (not 12) and holds 15 now; none names host, model or effort, so none is a baseline.

**Superseded by this entry (2026-10-04, marked in place above).** The 1.19.0 hello per-stage figures attributed from file times (carry-forward 4, 8, 18, 12 turns; spec 18, 24, 24, 36) become 5, 8, 13, 12 and 19, 30, 26, 40 under A2's attribution, recomputed here on the same four run directories with `metrics.collect`; totals are unchanged. The "Measurement caveats" bullet's mtime and `cost_share_usd` statements, the "Harness contract change" bullets (12 rows; three runs left active with the worst at carry-forward; a non-zero `could_not_run` is an environment problem, not a product one) are marked with their reasons.

**Not fixed, by decision** (design document, section 10.4): whole-second engine stamps move the closing turn of a stage into the next one (a recount on four hello runs: a turn within the second after the stamp at 50 of 157 boundaries, so read stage turns as plus or minus one); a recreated `timeline.json` looks like real stamps; a timeout whose partial output already shows failing tests is `could-not-run`; a command that fails to start inside `/bin/sh -c` (126 or 127) counts as a product failure; a harness killed with its host writes no termination record. The exporter's separate stage minutes and the wall-clock inclusion of interruption gaps are documented, not changed. An owner decision the skills follow-up left open: the end-of-work review gate (`carry-forward`, which allows only done, repeat and blocked) has no remedy outcome for a command that cannot run.

**Unverified.** The follow-up fixes (two implementer branches, not merged when this was written: the dispositions in the evidence README say "see follow-up"); every behaviour above in a live run; the 9 rejected candidates, which the export does not carry. The integrator updates this entry and the evidence README after merging the follow-ups.

### a13 system-test open item, built - 2026-10-04 - status: built, live behaviour unverified

- **Finding (Luna max battleship on 1.16.1: one run, one model).** The run ended `blocked` at `system-test` after 19.3 h on two required browser cases (`SYS-BROWSER-PLAY-13`, `SYS-BROWSER-RECOVERY-14`) that only a person can run, although all five registered suites had passed on the real candidate; product-acceptance, release-plan, release-check and the report never ran (entry "Luna max battleship on 1.16.1, final" above, commit 4b5d41dd). SPEC S-14 says a step that needs a physical observation becomes an open item and the run continues, and the packet's common text already said so; the model resubmitted `blocked` with a `no_default` that explained why the case needs a person, not why nothing else could proceed. What left it no route to `done` was stage completion: the closing paragraph of "Stage readiness and completion" in `testing-and-documentation.md` says a required case already due but failed, blocked or not run prevents declaring the boundary complete, and `DUTIES["system-test"]` had no open-item route (only `DUTIES["release-verify"]` spelled one out). The script was never the obstacle: it reruns the recorded system commands and accepts `done` whatever the result summary says about a person-only case (the new test-loop test shows this on the unchanged base). Sonnet 5.5's battleship runs recorded the same browser limit as an open item at test-strategy, passed system-test as `done` and carried the item through product-acceptance, release-plan and handoff in prose; they never made the case a due pre-release gate, so the difference is the phase assignment and the model, not the text.
- **What changed (text only; no script, state field, verb or exit rule).** (1) `DUTIES["system-test"]`: one 118-word paragraph mirroring the `release-verify` route: a required person-only case for which the discovery and test-strategy records show this host has no route does not make the result blocked; record it as an open item in the result (case ID, who does what, what they report, owner a person, due stage handoff or the stage whose external effect it gates); submit `done` once every other due check and ShipLoop's rerun pass; the handoff reports it unverified, never as a pass; `blocked` with `awaiting` only when a later stage takes an external, hard-to-reverse effect the case exists to gate, or nothing else can proceed; an enabled delivery contract keeps its own obligation phases. A browser appears only as the example (S-8). (2) The closing paragraph of "Stage readiness and completion": the same exception, stated as "not such a check", before the sentence on enabled delivery contracts, so the card and the packet agree (S-3). (3) `DUTIES["handoff"]`: one clause listing each open item as unverified with who reports what (the text named limits, blockers and follow-up work, not open items). `DUTIES["product-acceptance"]` is unchanged: its stage spec already accepts a request outcome "pending with its owner and due stage", and the relabelled due stage is what makes the item not yet due there. Change note: `changes/shiploop/system-test-open-item.md` (patch).
- **Tests.** New: `test_a_person_only_case_with_no_host_route_is_an_open_item_not_a_block` (`test/shiploop-guidance.test.py`: content pins for the paragraph, the reference sentence and the handoff clause; presence pins that the guards stay ("Do not substitute a planned case or local mock", the rerun refusal, "A local pass cannot replace a blocked/unrun required remote check"); absence pins that no other stage carries the phrase and that the paragraph names no tool or product); `test_a_done_system_test_with_a_person_only_open_item_advances_and_still_reruns_the_commands` (`test/shiploop-test-loop.test.py`: the rendered packet names the route; `done` carrying an open item is refused while a recorded command fails, then accepted, advances to product-acceptance, and its summary reaches that packet; the script's two rerun records are false then true, so S-9 holds); `test_a_person_only_open_item_does_not_waive_a_contract_system_test_obligation` (`test/shiploop-consumer-delivery.test.py`: an open-item summary is still refused at the contract's `pre-update` obligation; `test_required_phase_obligations_block_false_completion_and_preserve_effect` already pins the bare refusal). Counts, base a1a3-integ-7f216e to after, all exit 0: guidance 36 to 37, test-loop 43 to 44, consumer-delivery 26 to 27; navigator-contract 55, rehydration 8, keepalive 57, packet-bounds 8, delegation 47, navigator-dry-run 16 and actual-improve-cli 32 unchanged. On a `git archive` export of the base the guidance pin and the test-loop test fail (the text is absent); the consumer-delivery test passes there because it pins an unchanged refusal, and the test-loop test passes there too once its packet assertion is removed (the navigator already accepted such a result, so the change is in what the packet says, not in what the script accepts). No packet-bounds or delegation bound was raised: none failed. Quick tier (`--group quick --changed-from a1a3-integ-7f216e`): exit 0 (31 of 31 selected suites passed).
- **Size** (`graph-dry-run --scenario delivery`, `produce` events, run path normalised): the system-test packet 23,621 to 24,315 characters (+694; 3,028 to 3,146 words) and the handoff packet 23,030 to 23,088 (+58; 2,914 to 2,924 words); the other 32 stages are identical.
- **Unverified.** Live behaviour: whether a Luna max battleship run on a release carrying this text submits `done` at system-test, and whether it then still blocks at `release-verify` (whose route is unchanged: `blocked` with `awaiting` when the release cannot be accepted without the observation). It needs a live run; none was started. Residual text left as is: the testing reference's browser section says to keep an unavailable browser check "blocked/unverified", and "Deployment and handoff" says required blocked or not-run checks remain unfinished at product-acceptance; both read as the status of the check, which the open item keeps, not as the run's outcome. The stage's printed done-when line ("every due system test ran") is script text; the relabelled due stage is what makes the item not due there. Gaming risk (a runnable check labelled person-only) rests on the paragraph's requirement that the discovery and test-strategy records show no route, on the script's rerun of every recorded command, and on "Do not substitute a planned case or local mock"; in the Luna run Chrome and safaridriver were installed and the model only scanned its tool catalog, a separate question not addressed here.
- **Deferred, phase two.** `DUTIES["test-strategy"]` and `DUTIES["system-test-author"]` plan a person-only case with no discovered route as an open item from the start, instead of a required pre-release gate. Only if a live run on this text still spends hours on person gates.
- Related: 4b5d41dd (the Luna final entry and action a13), 3592b195 (I2b, the same Luna run), 6a59012c (A1 review follow-up, which rewrote the test-loop file this change extends).

## Cost and counts that misled — 2026-10-04 (R3 to R5, chain B) — status: firm (hermetic tests; recorded runs recomputed); not yet seen in a live run

Plan: `docs/shiploop-e2e-plan-reconciliation-2026-10-04.md` section 4. Commits: R3 `8de0bcb5`, R4 `ddf33967`, R5 `7eb7ee88`, on top of `ce32a143` (counters a host does not report are null) and `3c604304` (A2, A3). The plan was written before `ce32a143`; each item was re-checked against the code at `8b42ff18` first.

**Disposition.**
- R3, partly done by `ce32a143`: `metrics.collect` already gave a null cost when no session reported one, null Codex turns, and `input_peak` None for a stream with no usage events (progress already printed "peak context n/a"). Left, and fixed: `run.summarize_events` still summed `or 0`, so `result.json` `cli.cost_usd` was 0 and the process line printed `cost=$0` for the same Codex run (reproduced through `run.main` on the fake Codex); a mix of one session that reported and one that did not printed the part as the whole; the host's own usage was dropped; the output-token fields (null for Claude and Codex since `ce32a143`) were still summed from Grok-shaped usage events and read by nothing; a usage event without numbers added a 0 to the peak. One `metrics.total_cost(sessions)` now serves both sites; `sessions[].usage` keeps the host's dict as written; `tokens.output_total`, the per-stage `output_tokens` and the `output_tokens` unmeasured entry are gone (nothing read them: `progress.py` reads `input_peak` only and the Run Review exporter reads neither).
- R4, open: no start count existed. `unreported_sessions = max(0, starts - ended)` is in `metrics.json` and `result.json` metrics, printed beside the cost, and is not a baseline key.
- R5, open: `improve_children` counted `-bind.md` receipts.

**Evidence** (copies of the finished run directories under `/Users/dadleet/e2e-runs`, `metrics.collect` rerun with this code, then `export.py` over each; the exporter ran on all three and its own counts agree with the metrics now):

| Run | cost | unreported_sessions | improve_children | host's own usage in `sessions[0].usage` |
|---|---|---|---|---|
| `20261003/v1161-battleship-luna` (Codex) | null (was `cli.cost_usd` 0) | 1 (2 starts, 1 end) | 9 (was 18) | input 172,611,340, output 1,622,714 |
| `20261003/batch-sonnet/seat-reservations` (Claude) | $1.8496, a lower bound | 3 (4 starts, 1 end) | 12 (was 24) | output 28,419 |
| `20261004/v1190-hello-sonnet` (Claude) | $5.3678 | 0 | 8 (was 16) | output 69,770 |

A scan of the 12 recorded run directories finds 6 with more session starts than ends; all 6 carry `resumed_run`. Five single-session Claude runs carry 1.60 to 1.72 harness turns per `result.num_turns` (the plan's 11-run range was 1.70 to 1.96; the README now says between 1.6 and 2).

**Superseded by this entry** (not edited in place above, the journal is append-only here):
- Any earlier reading of a Luna run's cost as $0 or its tokens as 0 (`v1161-battleship-luna` `result.json` and `metrics.json`, and committed `baselines.jsonl` row 12, which carries `cost_usd` 0 for a Codex run; it names no host so it is never compared, and it is left as written).
- Any "Improve children" count from a metrics file written before `7eb7ee88`: each is double (the v1161 Luna 18 is 9; the Run Review exporter already said 9).
- "$1.85 for 423 turns" for `batch-sonnet/seat-reservations` as a whole-run cost: it is the cost of the one session that reported, beside the turns of four.
- Claude `tokens.output_total` and per-stage `output_tokens` in any `metrics.json` written before `ce32a143` (a streaming snapshot: 4,087 against the host's 69,770 on `v1190-hello-sonnet`, 5,459 against 86,188 on `v1190-hello-sonnet-2`: 16 to 17 times low).

**Limits, not fixed.** Whether a real Grok host emits `available_commands` once per session is unobserved (it is dormant), so a Grok run could print a spurious lower-bound note, which fails safe. After `codex exec resume`, whether Codex usage covers only the new turn is unobserved, so `sessions[].usage` summed across a resumed Codex run may not be the whole run. A cost is null when any ended session reported none, even if another did (each session's own cost stays in `sessions`). `iterate.py`'s two cost lines now print "not reported" instead of `$None` (a two-line change outside the metrics files, forced by `cli.cost_usd` becoming null).

### Retention id check counts ids the way the engine does - 2026-10-04 - status: firm for the check (hermetic tests, four real specs replayed); not yet seen in a live chain run

Question: does the `battleship-scoring` retention check that guards the earlier requirement ids (the `ids()` check in its `retention` list) fail a correct spec because it counts ids differently from the engine rule it mirrors? The engine's `_REQUIREMENT_ID` (`shiploop_knowledge_home.py`, used by its own dropped-id gate and by `run.knowledge_facts`) is `\b(R-\d+)\b`: an id anywhere on a line. Plan: `docs/shiploop-e2e-plan-reconciliation-2026-10-04.md`, increment R7.

- **Finding.** The catalog line counted an id only at the start of a heading or a bullet (`^([#]+[[:space:]]*|[-*][[:space:]]+)R-[0-9]+`). A bold bullet (`- **R-1** ...`), a table row (`| R-1 | ... |`) and an id in the middle of a line were read as no id. With zero earlier ids the check's own `[ "$earlier" -gt 0 ]` fails, so a correct, fully retained spec failed `checks`. Replayed on 2026-10-04 on the four real Battleship specs on disk (run directories under `/Users/dadleet/e2e-runs/20261003/`), counting ids three ways:

  | Spec | Form | Old check | New check | Engine |
  | --- | --- | --- | --- | --- |
  | `batch-sonnet/battleship` | bullets | 8 | 8 | 8 |
  | `batch-sonnet/battleship-scoring` | bullets | 10 | 10 | 10 |
  | `battleship-luna` (first Luna run) | headings | 6 | 6 | 6 |
  | `v1161-battleship-luna` (1.16.1, max effort) | table rows | 0 | 10 | 10 |

  Three specs used three forms, so the form is the model's choice and not a rule the harness may impose. A follow-on of the 1.16.1 Luna product would have read `earlier ids: 0` and failed however well it built on the spec.
- **Change (one catalog line).** `ids()` runs `grep -oE '\bR-[0-9]+\b'` (JSON-escaped `\\b`), the engine's rule in grep's syntax. Not `grep -ow 'R-[0-9]+'`: BSD grep (macOS `/usr/bin/grep`) reads 1 of the 2 ids in `R-1 R-1a R-2` where the engine reads 2. A dropped id still fails in every form and is named in the check's output (`missing: R-2`).
- **Tests** (`RetentionIdCountTest`, the last class in `test/shiploop-e2e.test.py`; the real shell command from `cases.json` run through `run.run_checks`): five spec forms (heading, bullet, bold bullet, table row, mixed line `R-1 R-1a R-2`), each passing when every id is kept with the printed count equal to the engine's, and failing with the dropped id named when one is lost; a spec with no ids still fails; a drift guard that extracts the pattern from the catalog line, requires it verbatim with a real backslash, and compares what `grep -oE` finds with `_REQUIREMENT_ID.findall` on eight sample texts. On the base (`git archive a1a3-integ-7f216e` with only the new test file copied over) 7 subtests fail: bold bullet, table row and mixed line in both form tests, and the drift guard; heading and bullet pass on both (the old pattern read them). Mutation check: restoring `grep -owE 'R-[0-9]+'` in the catalog fails the mixed-line subtests and the drift guard.
- **Limits: what is not guarded, and why.** Each was checked against `cases.json` and `run.run_checks` on 2026-10-04.
  - The Battleship checks are protocol checks. Three constructed stubs pass all four `battleship` checks (re-run through `run.run_checks`: PPPP each): a server that answers every fire with `sunk` and `gameOver: true`; one that has no fleet, counts shots per game and answers `miss`, ending the game at the 100th shot; one whose page says no game is playable, with one constant game id and `miss` plus `gameOver: true` on every fire. The checks read the response shape and that a 10x10 sweep ends the game, not fleet placement, ship sizes or hit and sink counts. Rule correctness belongs to the product's own tests and ShipLoop's own system test (S-9: the evidence is a script-run check); the harness does not repeat it. Reopens if a returned Battleship candidate passes all four checks yet fails the rules in review or system test. The plan measured a variant of check 4 that also counts `sunk` results: it rejected all three stubs and accepted the real products; it is not kept as code.
  - Coordinates are assumed 0-based. The checks fire rows 0 to 9, columns 0 to 9 and (0, 0); the prompt says "10x10 grid" and names no base, so a product that rejects row 0 or column 0 fails.
  - A check that times out or cannot start reads as a product FAIL. `run_checks` records `pass: false` with `returncode: null` and output `timeout` after 180 s, and a command that cannot start inside `sh -c` (126 or 127, `node` missing) is a plain non-zero. A1 treats these as could-not-run only inside ShipLoop's own test loop, not in this harness's grading. Read a failing check's output before reading it as a product defect.
  - Ports 39171 to 39176 are fixed (three checks per case; `grep -o 'PORT=[0-9]*'` on `cases.json` finds exactly these six, and no other case uses a fixed port). One suite cannot collide with itself, because the chain that uses them runs its two cases in order. Two runs grading at once on one machine (two suites, or a suite beside a `--case` run) share them, and a stale server from an earlier run holds its port and answers in place of the product (README, "Launching long runs"). A collision reads as a product FAIL.
  - `hello`'s second check is `python3 -m unittest -q`. It fails a product with no test only because Python 3.12 and later exit 5 when no test ran (`python3` 3.14.7: `NO TESTS RAN`, exit 5). On the macOS system Python 3.9.6 the same command prints `OK` and exits 0, so a hello product with no test passes both checks there. The harness takes the `python3` on `PATH`.
  - An id mentioned anywhere keeps the check passing, including in prose after its requirement was deleted. That is the engine's own rule, so the check is as strong as ShipLoop's gate and no stronger.
- **Unverified.** No live run exercised the new line. The next `battleship` to `battleship-scoring` chain confirms it on a product spec; the four replays above are the evidence until then.

Related: `3f23a15d` (check hygiene tests for the temperature case, the pattern this follows), `ce32a143` (the 151-test base).

### Limits a normal run can meet - 2026-10-04 - status: documented, not guarded; each limit checked against code or a record on 2026-10-04

Question: which limits will a normal run hit that the harness neither prevents nor reports? Plan: `docs/shiploop-e2e-plan-reconciliation-2026-10-04.md`, increment R8 (README, "Launching long runs", carries the process and recovery recipe; this entry carries the rest). Nothing here changes behaviour, and none of it is pinned by a test.

- **A blocked run does not say whether a person or the engine blocked it.** `termination.engine_status` is `blocked` for any accepted `blocked` result. The reason text starts with the model's own claim of who can unblock it (`blocked_by`: `user`, `access` or `external`; `BLOCKED_BY` in `shiploop_navigator.py`), and `halted` and `paused` come from a command, not from a result. Nothing records whether a person's decision was truly needed or the model chose to stop, which is the question the decision table in the next entry turns on. Read the blocked stage's own records, not the status.
- **A timed-out check can leave its shell's children.** Reproduced: `run.run_checks` with a 2 s timeout on `sleep 41 & wait` returned `pass: false`, `returncode: null`, output `timeout`, and `sleep 41` was still alive afterwards, because `subprocess.run(shell=True, timeout=...)` kills the shell, not what the shell started. A check that starts a server and times out before its own `kill` leaves it on its fixed port (the Battleship ports in the previous entry). The same applies to a server a model started in the host (README, "Launching long runs").
- **A retention check that runs a suite in `$PRIOR_WORK` could write there (unobserved).** `battleship-scoring` runs `node --test` inside `$PRIOR_WORK` to count the earlier tests (`count "$PRIOR_WORK"`), and `run.py` describes that directory as the earlier checkout, read only. A test that writes a file would write into the earlier product, which later follow-ons copy. `run_checks` removes untracked files only from the work directory. No run's prior checkout was compared before and after, so this has never been seen to happen.
- **Run binding takes the first done run in path order if two states exist.** `grade_shiploop` sorts every `state.md` under the output directory (not `home/` or `build/`), chooses the first run that is `done` with a `report.html`, else the first of all, and reports how many it found as `shiploop.runs`; for `.shiploop-runs/work-<date>-<time>-<id>` that order is the oldest first. 0 of the 12 `result.json` files under `/Users/dadleet/e2e-runs` on 2026-10-04 show `runs` above 1 (the plan counted 23 results; the other 11 are not on this disk). Reopens when a result shows `runs` above 1.
- **A resumed run's first-process row stays out of `baselines.jsonl` by hand.** The first process of a run that is later resumed writes its baseline row only if the harness itself finished (a `--timeout` end; a task kill writes nothing), and that row is a timeout row (process false), not the run's verdict. A resumed or seeded invocation writes no row (`baseline_file` is None when `resumed or seeded`). Leave such a row uncommitted, as the Luna 1.16.1 entry did, until a baseline policy for a failed row is decided (the plan's D5).

### Batch plan and pre-registered readings - 2026-10-04 - status: pre-registered

Registered before any Luna invocation of this batch, so no reading below can be chosen after the result. Plan: `docs/shiploop-e2e-plan-reconciliation-2026-10-04.md` (sections 3 and 4, increment R9); governing spec `test/shiploop_e2e/SPEC.md`. `suites.json` is not edited: its batch entry is stale and one suite means one host, so the order below is run by hand.

**Timing evidence.** No Luna `invocation.json` of this batch exists when this entry is committed (no run directory of the batch exists). The only Luna ones on this machine are the 1.16.1 run's (`/Users/dadleet/e2e-runs/20261003/v1161-battleship-luna/invocation.json` and its `invocation-resume-codex-*.json`) and the earlier `battleship-luna` run's, all from before this batch (the newest mtime is 1791104159, the 1.16.1 resume file). The check that this entry was registered first: the commit that introduced it, `git log -S'a13 decision table' --format=%ct -- test/shiploop_e2e/LEARNINGS.md | tail -1`, is earlier than the batch Luna run's `invocation.json` mtime (`stat -f %m <that file>`). The plain `git log -1 --format=%ct -- test/shiploop_e2e/LEARNINGS.md` gives the same answer until the first journal entry written after the launch is committed.

**The three-run map.** One release, one verification set, in this order:

1. `run.py --preflight-only --host all` ($0): the published version on every host, and no unreleased note on the install under test.
2. The Sonnet 5.5 hello gate (`--source marketplace`, about $5, 15 minutes). It shows the release, A2 (stage attribution from the engine's records, baselines compared within host, model and effort) and A3 (`termination`) live, and writes the first identity-carrying baseline row. Expected: every verdict true (invoked, plugin, process, shiploop, committed, checks) and both checks passing, as on the 1.19.0 gate.
3. One unseeded Luna battleship (`--host codex`, model `gpt-6-luna` as on the 1.16.1 run, effort max as the plan words it; hours, no dollar cap). Baselines compare within one effort and a standing owner exception of 2026-09-27 says ShipLoop E2E runs pass `--effort xhigh`, so the launcher confirms the effort before launch and the close records the one used; the table below does not depend on it. It is the only run that can exercise a13 (the open item for a step that needs a person, action a13 on the Run Review page). If the owner declines this run, the hello gate alone verifies the harness and the release, and a13 ships labelled not exercised.

**The a13 decision table.** How the Luna run's outcome is read, fixed now:

| Outcome of the Luna run | Reading |
|---|---|
| a. system-test accepted done with a person-owned open item recorded and the run continuing | a13 confirmed for this case, host, model and effort; a later block is a separate finding |
| b. done, no person-only case planned | a13 not exercised |
| c. blocked at system-test on a person-only case again | a13 refuted for Luna; take the deferred test-strategy change |
| d. blocked before system-test | new finding; a13 unexercised |
| e. host died or deadline | inconclusive; `termination` says why |

**Hold list while the Luna run is in flight** (the active-resume gate refuses on each): no release; no push to origin/main carrying a `changes/` note; run the harness from a checkout whose HEAD is an ancestor of origin/main; main CI not red before any `--resume-run`; Codex also refuses after any later release. Ordinary test and docs pushes are fine.

**S-14 defaults, recorded and not asked** (SPEC S-14: unattended by default): `--timeout 36000` for the Luna run, and at most one `--resume-run` if the process ends while ShipLoop is active. A resume that is refused, or a second one, is a finding, not a retry.

**Coverage: what is proved how.**
- *Hermetic tests only, and said so:* A1 (a test run that reaches no verdict is could-not-run; no catalog case provokes it), R6 (a regrade claims no host exit) and R7 (the retention id check counts ids as the engine does; the next battleship to battleship-scoring chain confirms it on a product spec).
- *The hello gate can show:* the release, A2 and A3 live, the first identity-carrying baseline row, and the Run Review export.
- *Only the Luna run can show:* a13, per the table above. A Codex resume or regrade is the first live test of the plugin evidence carried across a resume (the plan's U6) and happens only if a resume is needed.
- *Not re-qualified:* chain execution, retention across a follow-on, and concurrency. Their behaviour is unchanged since 1.17.0 except read-only report listing and wording, and this batch starts no chain, follow-on or parallel suite run.

**How the close reads.** One journal entry after the Luna run maps its result to its row above. For Claude it cites `cost_usd` and `result.num_turns` (never the harness turn count) and no failure, glue, `/tmp`, cancelled or knowledge-read count; for Codex it cites wall minutes and `termination` only, never a dollar figure or per-stage turns. It notes the gate's init event once (Claude Code version, server count 0 expected).

### Verdicts that misled a reader: plugin on a resume, committed on an empty baseline - 2026-10-04 - status: fixed in the harness (R1, R2 of `docs/shiploop-e2e-plan-reconciliation-2026-10-04.md`)

Question: which verdicts recorded for the two blocked Luna runs (`/Users/dadleet/e2e-runs/20261003/battleship-luna`, skill-craft 1.16.0, and `/Users/dadleet/e2e-runs/20261003/v1161-battleship-luna`, 1.16.1, both Codex `gpt-6-luna` max) said something the run had not done? Both runs were re-read on disk without writing to them; the fixes were exercised on the fake hosts only, not in a live run.

**Plugin verdict lost on a resume or a regrade (R1, status: firm).** A Grok or Codex event stream cannot show which plugin loaded; their only evidence is the install check made before the first process started. The resume branch (same host) and the regrade branch both set the plugin record to nothing and graded from the stream, so a resumed or regraded Grok or Codex run read `plugin` false with `loaded` empty whatever its first launch had graded. `v1161-battleship-luna` is that case: `result.json` says plugin false, `loaded` empty, while its first process graded true (the resumed process overwrote the first `result.json`; the first grade is recorded in the "final" entry above). Claude was never affected: its init event shows the plugin on every launch. Reproduced on the fake hosts before changing anything (the base `a1a3-integ-7f216e` and the merged follow-up `ce32a143`, which fixed which plugin directory a regrade uses but not its verdict): grok and codex regrade and same-host resume read false, claude true. Fix: `invocation.json` now records the plugin record made at launch (`null` for Claude) and a resume or regrade reads it back; an `invocation.json` written earlier grades as before, with no evidence and so a fail (no migration; it does not guess a pass). Tests in `PluginVerdictCarriedTest`: regrade and resume for claude, grok and codex, the record at launch, and the absent-record case. On the base the grok and codex regrade and resume subtests fail and the record-at-launch test errors; the absent-record test passes there too (it pins behaviour that was already right).

**Superseded by this fix.** The "Grading defect (open)" bullet of "Luna max battleship on 1.16.1, final" is fixed for runs launched from this commit on; its recorded `plugin fail` for `v1161-battleship-luna` was a lost record, not a failed install, and the run is blocked at system-test so it cannot be regraded (its `invocation.json` was written before the record existed).

**`committed` passed on an empty tree (R2, status: firm).** The verdict was HEAD differing from where the run started with nothing uncommitted. On a fresh run the start is "no commit" and ShipLoop's first act in an empty directory is an empty baseline commit ("Empty baseline for the first ShipLoop run"), so any HEAD differed and the verdict was true before ShipLoop had returned a file. Both blocked Luna runs show it on disk: `battleship-luna` (HEAD `5d5d582f`) and `v1161-battleship-luna` (HEAD `0881235d`) have `committed.pass` true, one commit each, and `git ls-tree -r HEAD` lists 0 files in both. Neither returned anything to the source checkout: `v1161-battleship-luna` holds its candidate in ShipLoop's worktree (its checks pass there), and `battleship-luna` was blocked at plan (revision 12), before any implementation. Replaying the rule read-only over the 12 recorded results under `/Users/dadleet/e2e-runs` (all 12 had `committed.pass` true) flips exactly these two; the other ten each hold files in HEAD. `result.pass` was never wrong, since the `shiploop` verdict needs done plus a report and both were blocked; the baseline row, the printed line and the Run Review strip were. Fix: `committed_facts(knowledge, start_head)` also requires `head_files > 0` (`git ls-tree -r --name-only HEAD`), and the printed line, the mismatch row, the README and the `run.py` docstring say "files in HEAD". Known limit, documented in the function and not guarded: any file counts, so a future ShipLoop that returned only knowledge files (`docs/shiploop/`) to the source checkout before the product would pass early; today those stay in ShipLoop's worktree until the product is returned. Tests in `CommittedVerdictTest`, on real git in a temp directory (the empty baseline gives false and 0 files, one file gives true and 1, the start and the uncommitted conditions still hold) and through `run.main` with a fake host that leaves only the empty baseline commit (result, baseline row, printed line and `mismatch.md` containing "files in HEAD"). On the base the new tests fail: `committed_facts` does not exist, and the run through `main` reports `committed` pass and a passing run.

**Superseded by the R2 fix.** Three recorded readings of "committed pass" meant only ShipLoop's empty-tree baseline commit, since neither run returned a file: the verdict list for `v1161-battleship-luna` in "Luna max battleship on 1.16.1, final" above; the `verdicts.committed` true in its evidence file `test/shiploop_e2e/evidence/codex-gpt-6-luna-1.16.1-battleship-20261003.json`; and the `committed.pass` true in the `result.json` of `battleship-luna` (1.16.0). Neither run can be regraded (both are blocked, and a regrade needs a done run), and this entry edits neither the evidence file nor the uncommitted baseline row of the first process; read those three as "committed: false, 0 files in HEAD".

**R6 (a regrade claims no host exit), status: already fixed by `ce32a143`; only a comment changed here.** A regrade now keeps the termination its original run recorded (marked `regraded`) or, with none, reports `not observed (regraded: no host ran)`, return code `None`, 0 sessions; `ResumedRunRecordTest.test_a_regrade_keeps_the_termination_the_original_run_recorded` and `test_a_regrade_with_no_record_says_no_host_ran_and_fabricates_no_exit` pin it. One comment in the resume loop listed "awaiting" as a run status; the engine's statuses are active, paused, blocked, halted and done (`_STATUSES` in `shiploop_navigator.py`), and a person's pending question is a view of `blocked`, so the comment now omits it. A reproduction on the fake claude, grok and codex hosts, run on the merged code before any edit, gave the same record on all three. One thing is left as designed: a regraded run's `result.json` `process` block still reads status `exited`, return code 0, with `regraded: true`, so the `process` verdict is true without a host; the printed report and `termination` say no host ran, and a false verdict would fail every regrade.

**Second review pass: a regrade restates the run's own record (R1 and R6 follow-up, status: fixed).** A second adversarial pass over the merged A1 to A3 follow-up (`8b42ff18`) confirmed that a regrade, which starts no host, still made three things up. Dispositions, each pinned in `RegradeRecordTest` and failing on the base (`a1a3-integ-7f216e`): (1) a regrade of a finished Grok or Codex run replaced its passing `result.json` with a failing one, because the plugin was graded from Claude's init event (three findings; `ce32a143` only removed the stub): the regrade now restates the plugin verdict in the run's own `result.json` (`invocation.json` when no result was written) and still grades Claude from its events; `test_a_regrade_of_a_finished_run_keeps_its_passing_result_on_every_host` asserts `result["pass"]`, plugin, host, model, effort and the process block for claude, grok and codex (it uses copies of the claude and grok fakes that print the ShipLoop CLI by path, as a real host's events do, since a regrade reads `invoked` from the CLI; the shared fakes are untouched). (2) A regrade wrote a process block of "exited, rc 0, 0.0 s, pass true" (three findings), so a host that exited 3 after finishing the run turned a failed result into a pass beside a termination that said it failed: `regraded_process` keeps the original run's block (verdict, return code, sessions, elapsed seconds) marked `regraded`, or, with no record, writes status "not observed", return code `None` and a `None` verdict that the verdict list, the mismatch list and the report leave out ("process n/a"); `test_a_regrade_never_turns_a_failed_host_into_a_pass` and `test_a_regrade_with_no_record_of_a_host_exit_says_so_and_leaves_that_verdict_out`. (3) A regrade took host, model and effort from the command line or `invocation.json`, so `--host codex` relabelled a Grok run, and a run resumed on another host reverted to its first launch's host: it now restates the run's `result.json` (host, model, effort, plugin, versions; `invocation.json` as the fallback), ignores `--host`, `--model` and `--effort` with a printed note, and does not refuse them (a documented operator route is to relaunch with `--resume-run ... --host codex` and let the harness find the run already done); `test_a_regrade_keeps_the_host_model_and_effort_the_run_recorded_whatever_the_command_line_says` and `test_a_run_resumed_on_another_host_is_regraded_as_that_host_with_its_plugin_and_versions`. Consequences to know: a host that timed out or failed in the invocation the record describes keeps `process` false on a regrade, as the instruction was, even if a later unrecorded invocation finished the run; a run with no `result.json` regrades with the process verdict left out, so its `pass` judges the product only.

Not changed, same pass (minor findings left in place by scope): a regrade still builds the host environment, reruns the Grok keepalive installer and rewrites `keepalive`, and writes an `invocation-resume` file and a prompt file for a launch that never happened; the first run's `mismatch.md` stays on disk after a regrade that passes (it is a record a person fills in, so it is not deleted); a Claude regrade whose `invocation.json` lacks `plugin_dir` compares against `<out>/missing-plugin` (a record this harness wrote always has it).

### Counters a host cannot show, second pass (review 2, metrics, chain E) - 2026-10-04 - status: firm (hermetic tests; two recorded runs recomputed and exported); not yet seen in a live run

Base: the integration branch at `ed005f11`. Commits: Grok-only counters `1a35bc50`, whole-run turns `40f349c8`, `summarize_events` `7741df81`, the suite `/tmp` check `ea21092e`, error subtype `3a84d137`, cache writes in context `fa1ea772`. Builds on `ce32a143` (null counters, the `unmeasured` map) and `8de0bcb5` (cost unknown unless reported). Each finding below is from `docs/experiments` review pass 2 of the A1 to A3 work, re-checked against the code first.

**Disposition.**
- *Fixed, `1a35bc50`: compactions, truncated outputs and knowledge reads are Grok-only detections (3 findings, plus the progress one).* `GROK_SIGNALS` names the four counters read only from a Grok event shape (compactions, truncated outputs, cancelled tool calls, knowledge reads). `collect` marks them unmeasured, with the reason, unless the stream carries per-call `usage` events (Grok's; the signal `stage_turns` already uses). The two ints are null in `metrics.json`, `result.json` and the baseline row; the two lists are emptied; `progress.py` says once which counters the host cannot show and skips a null counter.
- *Fixed, same commit: `cancelled_tool_calls` counts any failing command whose output contains "cancelled" (2 findings).* It is one of the four. The Grok half of the findings could not be reproduced (no Grok stream is recorded); the Codex half is fixed by not reading the Grok detector on a Codex stream at all.
- *Fixed, `40f349c8`: whole-run turns are a measured 0 for a killed Codex session.* `turns` is null unless a call or an ended session reported a count; with a session that never reported beside one that did it is a lower bound, printed "N (lower bound)" through `metrics.turns_text`.
- *Fixed, `7741df81`: `summarize_events` still records cost 0 and stop "success" (8 findings).* Chain B's `total_cost` had already fixed the cost and the process line (`8de0bcb5`, `cost_text`); left, and fixed: the stop reason now comes from `metrics.session_stop` and `num_turns` is null when no session reported one.
- *Fixed, `ea21092e`: `shared_tmp_writes` ignores `unmeasured["tmp_writes"]` (4 findings).* A run with unmeasured writes is left out of the comparison, named in `suite-result.json` as `tmp_writes_unmeasured`, and printed as not checked. *Superseded 2026-10-08: Claude's `/tmp` writes are measured now, so nothing marks `tmp_writes` unmeasured and the path was removed; see "The Claude tool-block reading".*
- *Fixed, `3a84d137`, beyond the list: an error result dropped its subtype (3 findings in `session_stop`).* Pinned by tests only; the recorded runs hold only subtype "success".
- *Fixed, `fa1ea772`, added by the coordinator: `context_tokens` left out `cache_creation_input_tokens`.*
- *Rejected, with evidence:* deriving the Claude tool-call marking from assistant events rather than `tool_use` blocks (part of one finding): a Claude stream with no `tool_use` block has no tool call to miss, so its tool-call counters are true zeros; the Grok-only marking no longer depends on tool calls at all. Reading Claude's `system/compact_boundary`: the SDK names it, but no recorded run contains one, so the shape is unverified. Tightening the cancelled detector's substring: no recorded Grok stream exists to check a narrower text against.
- *Not touched (outside my hunks of `run.py`, or outside the list):* `LiveView.event`'s "done" line still prints subtype or stopReason; `main`'s `cli["truncated_outputs"]` comes from `host_truncations`, a Grok-shaped detector that returns an empty list for Claude and Codex; `main`'s "baseline vs" and follow-on lines format `before['turns']` and `run_metrics['turns']` directly, so a null prints "None" (the fix is `metrics.turns_text`); a resumed Codex run loses per-stage `tool_calls` because item ids restart each session and `collect` keys calls by `toolCallId`; a stream with no `timeline.jsonl` labels per-call usage as absent.

**Evidence** (copies of the finished run directories, `metrics.collect` rerun before and after on the same input, then `export.py` over the regenerated `metrics.json`):

| Run | Before | After |
|---|---|---|
| `20261003/v1161-battleship-luna` (Codex) | `cancelled_tool_calls` 23 (19 `node --test` summaries printing "cancelled 0", 4 reads of SKILL.md prose; none a refusal), 9 knowledge reads from 144 `search_replace` calls (writes), compactions and truncated outputs 0, "turns 2189" with `unreported_sessions` 1, `unmeasured` = [stage_turns] | the four counters null or empty and named in `unmeasured` with `stage_turns`; "turns 2189 (lower bound)" |
| `20261004/v1190-hello-sonnet` (Claude) | "compactions 0, truncated outputs 0" beside "cancelled tool calls not measured"; `input_peak` 238,400 | the same two null and the map holds 8 names (was 5); `input_peak` 239,826 (per-turn undercount up to 60.7%, peak 0.6%) |

The exporter ran on both. Its documents are identical to the ones built from the earlier metrics except the output path in `writes.json`, because it reads only `shiploop_failures`, `model_glue` and `improve_reviews`; it still publishes Claude's blind counters as measured zeros (refusals 0, glue 0 on the hello run), which is the separate Run Review design track, and `metrics.json` now carries the complete `unmeasured` map for it.

**Superseded by this entry** (the journal is append-only here):
- Any `compactions 0`, `truncated outputs 0`, `cancelled tool calls N` or knowledge-read list in a Codex or Claude `metrics.json`, `result.json` or baseline row written before `1a35bc50`, and the Luna run's "23 cancelled tool calls" in particular (none was a refusal); committed `baselines.jsonl` rows are left as written (none names a host, so none is compared).
- Any Claude `input_peak` or per-turn context written before `fa1ea772`: low by the cache writes.
- Any `cli.stop` of "success" in a `result.json` written before `7741df81` for a session that ended on an API error.

**Limits, not fixed.** A stream that mixes hosts (a resume on another host) is read as the host that wrote usage events. A Grok session killed before its first usage event reads as not Grok, which fails safe (its Grok-only counters become unmeasured). A Claude compaction would show only as a `system/compact_boundary` event this harness does not read.

### Fast planning: why Luna is slow, and what one pass buys — 2026-10-04 — status: interim (one run; no replay and no run on the change yet)

Question: the owner said Luna runs take far too long and asked to cut planning prompts and default Backchain to one
pass. What is the time, which prompts and passes carry it, and what would a single pass cost in quality?

Evidence read: the Luna max battleship run on 1.16.1 (19.3 h, planning 647.5 min), its three Codex rollouts (2,919
responses), its Backchain loop records and its nine Improve children, the Sonnet runs on the same packets, and the
vendored Until Loop run on scratch repositories. Compact copies are in `docs/experiments/shiploop-fast-planning-20261004/`;
the design is `docs/shiploop-fast-planning-plan-2026-10-04.md`.

Findings:
- **Firm (measured):** the model generated tokens for 99.5% of the wall clock (about 55 tokens/s); waiting was about
  2%, tool execution 0.3%. 57.6% of the 3.54M output tokens were reasoning, and 2,276 short or message-only responses
  spent about 376 min (32.5% of wall time) thinking before a short command. Prompt input is 3.3% of latency, so cutting
  prompt bytes cannot speed Luna up; Sonnet planned the same request in 4.8 min from same-shaped packets.
- **Firm:** the Backchain plan loop took 7 passes (12, 15, 26, 18, 20, 10, 5 min). Pass 1 edited 14 of 20 steps; passes
  2 to 4 changed one `confirm` clause each (about 0.4 KB) and pass 5 a metadata label; passes 6 and 7 changed nothing.
  No edge, goal or supplier changed after pass 1. No later packet names the plan graph, and Improve at plan reviews
  `plan.md`, not the graph. The structural check (`backchain-check`) passes the plan graph before pass 1 and after every
  pass, so it does not discriminate at plan; it does fail both step-plan candidates on orphan step D1.
- **Firm (runtime experiment, `gate_experiment.out`):** the vendored Until Loop has no pass-ceiling field (`max_iterations`
  and `budget` are refused); at `required_trivial_reviews: 0` a non-trivial first pass with exit `satisfied` completes after
  one pass, an `unsatisfied` report continues, and `unresolved` with `satisfied` is refused. Gate 1 is not one pass.
- **Interim:** a one-pass default saves about 92 to 94 min of the 1,158 (8%) at the plan stage; `none` about 128 min (11%);
  Improve one pass would save 96 to 126 min but needs ShipLoop script changes and had warranted later fixes at
  test-strategy and test-spec, so it stays. About 17 h would remain, still above the 10 h session limit.
- **Exploratory:** whether Luna will write gate 0 and report `satisfied` after one changing pass under the new exit text
  (in 1.16.1 it reported `unsatisfied` through pass 6 under the two-review text); the effect of effort max against xhigh
  (no same-case run exists); whether 1.20.0's trim already removes the step-plan loop (the v1200 run died too early).

Decisions: SPEC S-10 carve-out dated 2026-10-04 (own commit, before the code); option `--backchain-passes one|converge|none`,
default `one`; Codex E2E default effort xhigh (`04ad68a2`); Improve unchanged; replay skipped on the owner's instruction,
so the first live run is the only evidence (risk recorded in the plan); exporter facts handed to the Run Review work.

Superseded by this entry: the exit rule "two clean passes, no pass cap" for the plan Backchain loop (SPEC S-10 as of
2026-10-03; now carved out), expectation B1 "every pass earns its time", and the claim in the earlier "Backchain ledger"
entry that the plan graph's later passes were each worth keeping (the graph is unconsumed). The Luna max baseline stage
totals stop being comparable once a run uses xhigh and one pass.

Pre-registered for the next Luna run (no thresholds): the written gate and exit text in `until-loop-start-input.json`,
passes and minutes per pass of each Backchain loop, whether a step-plan whole loop starts at all, plan-stage and
planning-window minutes beside 196.4 and 647.5, Improve passes per stage as the unchanged-code control (1.16.1: 4, 11, 3,
3, 5), and defects later stages find in the plan and test strategy.

Implemented (2026-10-04; the printed text is not changed until the one-pass gate text lands):
- **I1, the run option.** `backchain_passes` (`one` default, `converge`, `none`) is a required state key like `lint`, set once by
  `--backchain-passes` on `init` and `workspace start`, validated in `new_state` and `validate`, and handed from the recorded
  state to `shiploop_prompts.prompt` and `_backchain_guidance` (default `one`, rendered text identical for every mode) and to
  `graph-dry-run`. No verb changes it mid-run; a retry that names another value is refused naming the recorded one; a saved run
  without the key is refused by the generic missing-key check with the fresh-run hint (no migration, no separate message).
- **Evidence for I1.** Route tests, not wording: `BackchainPassesOptionTest` in `test/shiploop-navigator-contract.test.py`
  drives the real CLI for the default, each mode, an invalid value, a changed retry (`init` and `workspace start`) and a state
  without the key, wraps `guidance.prompt` to show the recorded mode reaches the packet render, and checks the SPEC S-10
  carve-out's option name, default and values against the code constants (parity, not prose). All 8 failed on the unchanged
  code because the option did not exist, and pass now. The ShipLoop and Improve test family (61 files, 1,244 tests) has the
  same two failures as the base (`shiploop-cross-run`, `shiploop-status-display`; a progress-observer file in a run directory,
  also failing solo on the base), and `shiploop-full-runtime`, which failed once on the base in a temp-directory cleanup
  race (`Directory not empty`) and passes solo on the base, passed on the change. No test enumerated state keys by hand, so none needed an update.
- **I2, the one-pass gate text, in the packet and in every document the host reads, in one commit** (supersedes the header's
  "printed text is not changed", 2026-10-04: this increment is the text change). `_backchain_guidance`
  prints the gate per mode. `converge` prints today's text byte for byte (checked for every stage against the output before the
  change). `one`, the default, prints at `plan` the 94-word paragraph: `required_trivial_reviews: 0`, the exit condition to copy
  verbatim (one complete review/fix/check cycle, findings repaired within the edit bounds, every `Confirm by` clause meeting the
  planning guide's Outcomes rule, `backchain-check` ok on the final candidate with its receipt cited, domain evidence saved),
  and the rule that a pass completing that cycle reports `exit_assessment: satisfied` even when it repaired the candidate. A
  14-word instruction puts `Backchain passes: one` beside the binding marker in the child's `work`. The four audit stages carry
  a 16-word pointer, with no gate field. `none` prints the one-pass text until its own packet lands (I3).
  `references/convergence.md`, `references/caller-contract.md` and the Backchain card now say the caller selects the gate: by
  default two consecutive trivial reviews and both qualifying records; with the marker line one cycle, gate 0, and one review
  record plus the `backchain-check` receipt as the terminal evidence set. ShipLoop's `SKILL.md` and `backchain-planning.md` point to
  the packet's printed gate. `skills/backchain/evals/evals.json` gains `until-loop-binding-one-pass-marker`; the standalone
  two-review case stays.
- **Measured (words, flattened).** Plan-stage Backchain guidance 480 to 579 (+99); each audit stage 301 to 317 (+16); the whole
  plan packet 3,698 to 3,797. The plan predicted about +70 at plan: it assumed the 23-word ownership clause ("Until Loop owns the
  callback handle, progress, ... terminal transition") is replaced by the paragraph. It is kept (a justified obligation; the
  repo rule is to raise a bound rather than trim), shortened by 9 words, so the paragraph (94) and the marker instruction (14)
  net +99. `converge` is +0 everywhere.
- **Evidence for I2 (route, not wording).** `OnePassGateTests` in `test/improve-runtime.test.py` reads `required_trivial_reviews`
  from the printed text, starts the vendored runtime with it and reports: gate 0 plus non-trivial and satisfied completes after
  1 action; unsatisfied continues and the next satisfied report completes (2 actions, no ceiling); unresolved plus satisfied is
  refused and the same action still takes a valid report; blocked stops; the printed converge gate (2) needs two trivial
  reviews after a repair. `BackchainGateDocumentsTest` in `test/shiploop-navigator-contract.test.py` keeps the exit clauses the
  packet prints identical to the ones `convergence.md` states, pins the evidence sets, and scans every Backchain-gate statement
  in `skills/backchain` and `skills/shiploop` for a scope (by default, the converge mode, the marker line or the packet's
  printed gate), plus the rendered default packets at every Backchain stage. On the unchanged code 4 of the 6 runtime tests (the other two pin runtime
  behaviour that did not change), 6 of 8 dry-run entries and the doc tests failed for the right reason (the printed gate was
  still 2). The ShipLoop and Improve family (61 files, 1,260 tests: the 1,244 of I1 plus 16 new) has the same two failures as
  origin/main and the I1 base (`shiploop-cross-run`, `shiploop-status-display`: a `.progress.lock` file in a run directory);
  `bash test/improve.test.sh` (vendored runtime hashes), the skill-frontmatter, test-groups, ci-policy and interop-hygiene tests
  and the 35-test mock suite pass. One run of `UnchangedFirstPassTests` (runtime and test unchanged by I2) failed once under
  heavy load and did not reproduce in 6 reruns on the change and 49 on origin/main: unexplained, recorded as a rare flake.
- **Not verified in I2 (needs a host).** Whether Luna copies the printed gate and the marker line, and reports `satisfied` after a
  repairing pass; the contract bytes against the 9,216 budget with the longer exit sentence (R0 was skipped by the owner, so the
  first live run answers both). `none` still prints the one-pass text.
- **I3, mode `none`: no whole Backchain loop at `plan`** (2026-10-04; supersedes "`none` still prints the one-pass text"). In a run
  recorded with `--backchain-passes none` the `plan` packet prints the audit route the four audit stages print (the read-only
  `review`/`audit`, one bounded `repair`/`revise` after a finding that runs one pass, the Until Loop state budget, the record-only
  `backchain-check` line) and no loop text: no `plan`/`draft` request, no binding marker, no gate field. Every audit stage says
  "No whole `plan`/`draft` is requested in this run (`Backchain passes: none`)" in place of "A whole `plan`/`draft` is requested
  only at `plan`" (the old sentence would be false for the run). The navigator prints, at `plan`, the audit resource and the
  loop-resource status line (`MISSING:` is still named, since a repair/revise starts a loop) and not the six-file "Selected
  Backchain and Until Loop resources" block. `offers_whole_backchain_loop(stage, mode)` in `shiploop_prompts.py` is the one
  definition of "this stage offers the loop" for both the packet text and the resource block. `one` and `converge` print what they
  printed before: checked for all five Backchain stages against the text captured before the change (20 of 20 renders byte-identical;
  only the 10 `none` renders differ). `skills/shiploop/references/backchain-planning.md` says the plan-stage owner may request a whole
  `plan`/`draft` "not when the run's Backchain passes option is `none`", so the guide the packet points to agrees with the packet.
- **Measured (I3, words, whole dry-run packets).** `plan` guidance: `one` 579, `converge` 480, `none` 320. Whole `plan` packet: `one`
  5,441, `converge` 5,342, `none` 5,162 (-279 against `one`, -180 against `converge`, 43,060 bytes against 45,679). Each audit stage is
  +2 words in `none` against `one`. The plan predicted "480 to about 301" (-179) for the loop text against converge; the measured
  guidance saving against `converge` is 160, because the audit route at `plan` keeps the 16-word pointer, the none sentence and the
  record-only check line that the audit stages carry. The six Backchain and Until Loop files are no longer named at `plan`
  (12 reads, 109 KB at `plan` in the 1.16.1 run).
- **Evidence for I3 (route, not wording).** The dry-run tests render the plan packet through the real `graph-dry-run --backchain-passes none`
  CLI, and the contract tests render it through `navigator.render` from a state recorded with each mode. 5 dry-run and 2 contract
  tests are new; all 7 failed on the unchanged code because `none` printed the one-pass loop text and the six-file block, and pass now.
  They pin content, not whole texts: `none` keeps the audit route, the budget, the MISSING rule, the status line and the check line, and
  names `plan`/`draft` once (to say it is not requested); drops the binding marker, the `plan`/`draft` action, the plan-only-child
  paragraph and every `required_trivial_reviews`; the `none` plan packet has fewer words than `one` and than `converge`; `one` and
  `converge` still print the loop text and the six-file block; the audit stages differ from `one` only by the sentence. The ShipLoop and
  Improve family (65 of 67 files green, 1,299 tests in the 63 unittest files, `bash test/improve.test.sh` green) has the same two failures as the
  base commit `0df9b0c4` (`shiploop-cross-run`, `shiploop-status-display`), both reproduced there.
- **Not verified in I3 (needs a host).** Whether a host given the `none` plan packet still starts a whole loop on its own (the
  packet says it is not requested and does not print what it would need); whether a host that finds a defect at `plan` takes the audit
  route rather than writing the plan unchecked; what `none` saves in minutes (about 128 on the 1.16.1 run is the plan's estimate, not
  measured).
- **Review of I1 to I3 and its fix commit (2026-10-04; status: firm for the fixes, hermetic tests; not yet seen in a live run).**
  Four review lenses (engine, documents, tests, bounds) read `a89135f7`, `0df9b0c4` and `a34a6ee6`; each finding was re-checked
  against the code before a change. Key learning: the exit condition I2 wrote for gate 0 ("every `Confirm by` clause meets the
  planning guide's Outcomes rule") contradicted the reference it sits in, which makes a weak clause on a step the cycle may not
  change (running, completed or protected) advisory. At gate 0 the loop completes on the host's own `satisfied` and nothing adds a
  ceiling, so an exit no host can honestly meet on such a graph either keeps the loop running or leads the host to report
  `satisfied` against its own rules. A fresh `plan` was never affected (every step is provisional); `repair`/`revise` at the audit
  stages and replans over accepted steps were. The packet-to-`convergence.md` parity test did not see it: both said the same wrong
  thing, and the test ran in one direction only, so a clause only the reference carried also went unseen (a mutant that added one
  stayed green).
- **Accepted and fixed in the review commit.** D1 (major): the clause reads "on a step this cycle may change" in the packet and in
  `convergence.md`. D6: `convergence.md` names ShipLoop's `references/backchain-planning.md` (Outcomes) for a standalone caller.
  T-2: the parity is two-way (the two clause lists are equal) and a new test pins the scope in both places. E1: the changed-retry
  refusal says only the owner starts a fresh run, so it no longer contradicts the workspace wrapper's "do not create a replacement
  run". E2, D3, L4: the documents say `one` prints the gate and an exit condition, `converge` prints the two-review gate and the host
  takes its exit condition from the convergence reference, and the repair/revise pointer is printed in `one` and `none` only. E3, D2,
  L2, T-1: the planning guide scopes its resource-block statements to runs that offer a whole loop, with content pins on those
  paragraphs and on the `none` description in `SKILL.md`. D4, L3: the audit pointer is an instruction ("put the line
  `Backchain passes: one` beside the binding marker in the child request"; without the line the child runs the reference's
  two-review default), the plan text says "child request" like the Backchain references, and `none` no longer prints
  `Backchain passes: none` as if it were a second marker value. T-4: the `none` plan test pins `BACKCHAIN_CHECK` itself, not only
  the navigator's command line (a mutant dropping it was green). T-5: the blocked-report test says it pins runtime behaviour. D5:
  the document scan also matches "two clean", "two reviews" and "two trivial" and reads `agents/*.md`. D7, L1: corrections below.
  D8 (part): `graph-dry-run.md` documents `--backchain-passes`. E4: the plan's note on `harness.md` is corrected.
- **Rejected, with the evidence.** L5: the `harness.md` entry in the scan's exemption list is live, not dead; the scan flattens
  paragraphs and the flattened paragraph matches "two consecutive" (the reviewer's grep was line by line and missed the wrapped
  phrase, the same miss the plan's note made). T-3: `converge` printing today's text is pinned by obligations and phrases on purpose;
  the plan rejected a whole-text golden. T-6 and T-7: not caused by these commits, and neither a contradiction nor a vacuous test
  (T-6 is an index-stat race of the vendored runtime in a fixture; T-7 matches the precedent of the sibling tests). D8 (other
  part): the option-lifecycle paragraph repeats in four documents, each read alone and none contradicting another, so it stays.
  E5, L7: `shiploop-cross-run` and `shiploop-status-display` fail identically on origin/main `38119014` (a `.progress.lock` file in a
  run directory). E6, L6: the branch is behind origin/main (the two-dot diff shows the Run Review moves in reverse, and
  `test/shiploop_e2e/LEARNINGS.md` conflicts on merge); merge before release, keep both sides' sections, and review with
  `git diff c895d921..HEAD`.
- **Corrections (dated; the bullets above are not edited).** "Each audit stage is +2 words in `none` against `one`" was +3 (317
  against 320 words of guidance). After D4 the audit stages are 328 words in both `one` and `none` and 301 in `converge`; the plan
  stage is 586 in `one`, 480 in `converge` and 328 in `none` (whole plan prompt 3,804, 3,698 and 3,546 words). "Scans every
  Backchain-gate statement" overstated `BackchainGateDocumentsTest`: it matches a fixed list of phrases in Markdown files and
  accepts a paragraph that names a scope anywhere in it; it does not read `evals.json` (pinned by
  `test_the_evals_cover_the_default_and_the_marker_path`). The plan document marks its `+70` and `-179` figures superseded by the
  measured `+99` and `-160`.
- **Evidence for the fixes (route, not wording).** On the unchanged source the changed tests failed for the right reason: 5 contract
  tests (the `Confirm by` scope, the mode documents, the planning-guide scope, and the changed-retry refusal through `init` and
  through `workspace start`) and 4 dry-run tests (the audit pointer, the `none` sentence at the audit stages and at `plan`, the
  printed exit clause), 25 failure records in all. The strengthened tests that already held were shown to bite by mutation: a clause
  only `convergence.md` carries and a clause dropped from the packet (two-way parity), "two clean reviews" in the planning guide and
  "two trivial reviews" in the agent card (the scan), and the `BACKCHAIN_CHECK` sentence dropped at `none` plan. After the fixes:
  navigator-contract 74 tests, navigator-dry-run 26, improve-runtime 12, actual-improve-cli 32, packet-bounds 8, guidance 37,
  delegation 47, e2e 198 and 18 more files all pass, `bash test/improve.test.sh` passes (vendored Until Loop hashes), and the only
  failures are the two above, reproduced on origin/main.
- **Not verified in the review commit (needs a host).** That a repair/revise host now writes the marker line from the audit
  instruction (not replayed); that a host reads "on a step this cycle may change" as the convergence reference defines it.

### Codex rollouts: calls, context window and compactions (R10, R11, R15 of the Run Review plan) - 2026-10-04 - status: firm (hermetic tests; the Luna 1.16.1 run read in place); not yet seen in a live run

Base: `c895d921` on origin/main. Commits: R10 `ebc68f00`, R11 `3ad31bf8`, R15 this commit. Plan: `run-review-redesign-plan.md` increments R10, R11 and R15 (R15 was deferred in the plan as journal item C2; the owner pulled it in because it is the user's "meta context used" for the Luna run). Hermetic only: no E2E run, nothing written under `e2e-runs` (the real-run figures are a read-only `metrics.collect` over the finished run directories).

**R10, a blocked run can be regraded.** `--resume-run` on a ShipLoop run whose status is `blocked` is a regrade: no host starts, the recorded host, model, effort, plugin verdict and process block are restated, the original termination is kept with `engine_status_at_regrade: blocked`, and no baseline row is written. `active` is still a real resume; `paused` and `halted` still refuse. Reason: the Luna run is blocked, its `metrics.json` predates the `unmeasured` key, and S-14 forbids continuing a blocked run as if answered. A fixture proves it; the real Luna regrade is plan item R13 and was not run.

**R11, model calls and the context window.** `model_calls` counts a Claude message once at its first event (unique `message.id`; an event with no id counts one) and a Grok `usage` event each; `window_tokens` is the `contextWindow` the result events' `modelUsage` agree on. `turns` is unchanged (events). Recorded Claude hello runs, read in place: v1190-hello-sonnet-2 149 calls against 254 turns, window 1,000,000, input peak 271,220 (the host's own `num_turns` is 157); v1190-hello-sonnet 113 against 194; v1180-hello-sonnet 94 against 167; v1161-hello 84 against 143. A host that reports nothing leaves the field null with the reason in `unmeasured` (Grok reports no window; a Codex run without rollouts has no call count).

**R15, the rollout reader (`test/shiploop_e2e/rollouts.py`).** What the records are, read from the three Luna rollouts (56, 21 and 91 MB): a `token_usage_record` per model request (thread_id, session_id, response_id, usage); a `token_count` event after each call (last_token_usage, `model_context_window` 258,400); a `compacted` record per compaction whose `compaction_response_id` equals the `response_id` of the usage record just before it.

- *Counting rule: a call is a `token_usage_record` that is not a compaction request; the headline is the main thread (thread_id equal to session_id).* The two call counts the peer gave are both right and measure different things. 2,919 is every usage record in the three files (1,381 + 320 + 1,218). 2,565 is the main thread's calls: the 2,599 main-thread usage records (1,381 + 1,218) minus its 34 compaction requests, equal to the `token_count` events that follow a call (1,366 + 1,199). The rest of 2,919 is 314 sub-agent calls and 40 compaction requests (34 main, 6 sub-agent). Chosen because a request is not work the thread chose to do: it has no `token_count` of its own, holds the whole context to summarise it (totals 192,277 to 259,670, one above the 258,400 window) and would otherwise be every run's peak.
- *Compaction facts.* 34 main-thread compactions (15 + 19) and 6 in the sub-agent. Every one is preceded directly by its request. The sub-agent file also holds a seventh `compacted` record, stamped at the fork, whose request is in the parent's file: inherited history, not counted (a compaction counts only when its request is a record in the same file). The `token_count` after a `compacted` record reports the shrunken context (input 0, first one 12,298) and is not a call; 35 other `token_count` events (12 + 19 + 4) repeat the previous event's cumulative total.
- *Main thread against sub-agents.* A stage window cannot tell a sub-agent's work from the thread waiting for it, so headline and per-stage figures are the main thread's and the sub-agent's are summed once under `subagents` (Luna: 314 calls, peak 217,302, 6 compactions). The resumed session is a second root thread in a new file and adds up.
- *Peak is `total_tokens` of the heaviest call: its input plus its own output.* Luna: 251,867 of 258,400 (97.5%), in the resumed session's `static-checks` stage; the first file's own peak is 250,042 (96.8%), the number first reported. The input side alone, which is what Claude's `input_peak` measures, peaks at 244,669 (94.7%), so a Codex peak reads higher than a Claude one by up to the call's output: compare within a host.
- *Real run, `metrics.collect` over `20261003/v1161-battleship-luna` (reads 168 MB in 0.6 s, the reader about 0.3 s; memory holds a few thousand tuples):* `model_calls` 2,565, `window_tokens` 258,400, `input_peak` 251,867, `compactions` 34, `unmeasured` = [cancelled_tool_calls, knowledge_reads, stage_turns, truncated_outputs] (compactions left it). Per stage: system-test-author 106 calls, peak 246,167 (95.3%), 2 compactions; carry-forward 184 calls, peak 246,408 (95.4%), 3 compactions; the heaviest stage is static-checks, 251,867 (97.5%). Per-stage calls sum to 2,562: three main-thread calls come after the last accepted stage (0.5, 8.7 and 56.6 s after the blocked `system-test` result) and belong to no window; all 34 compactions are in a window.
- *Hermetic proof:* RolloutContextTest (8), StageWindowsTest (1), CodexRolloutMetricsTest (4) and one run-level test through `run.main` with a fake Codex that writes a rollout. A synthetic two-thread fixture fixes the calls, peak, peakPct, compactions and per-stage splits, including a call exactly at a window end and a half-written last line. `per_stage` was refactored onto the new `stage_windows`; 20,000 random scenarios give identical rows to the old code.

**Superseded by this entry:** the plan's "Luna 2,919 calls, 34 compactions in the main thread" (2,919 includes the sub-agent and the compaction requests; the main thread has 2,565); any reading of the Luna peak as 250,042 (the first file only); the plan's note that Codex shows calls, context and compactions as not measured (they are measured when its rollouts exist).

**Limits, not fixed.** A rollout of a thread whose thread_id differs from its session_id is read as a sub-agent on that evidence alone (a Codex version that forks the main thread this way would be undercounted). The window is the last one a main-thread `token_count` reported; a run that changed model mid-way would show one window. Rollouts live in the run-owned CODEX_HOME and only the figures `collect` distilled survive in `metrics.json` and `result.json`; a regrade after the rollouts are deleted marks them unmeasured again. A run that mixes hosts is read as the host that wrote per-call events (Codex rollouts are read only when none did). The Luna `metrics.json` on disk was written before all of this and is refreshed only by a regrade (R10, then plan item R13).

### Planning time: Luna xhigh and Grok medium on 1.21.0, and where the minutes go — 2026-10-05 — status: firm for these runs (one run each); interim for what to change

Question: after 1.21.0's one-pass Backchain and the Codex xhigh default, planning on Luna still took 375.9 min. Where does it go, and does another model do better? The owner's working ceiling for the planning window (intake to the first test-spec accept) is 30 min (first said 7; corrected the same day).
Runs: `v1210-battleship-luna-xhigh` (Codex gpt-6-luna xhigh, 1.21.0 / ShipLoop 0.53.0; killed three times by the 2-hour background-task limit and resumed in place, stopped by the owner at 588 min in W1 implement) and `v1210-battleship-grok-medium` (grok-4.7 medium, same version; a planning-only probe stopped on purpose after the first test-spec accept). Evidence: docs/experiments/shiploop-planning-time-20261005/ (account, stage clock, run documents); the Run Review draft page holds both runs.

Findings:
- **Firm, 1.21.0's one-pass Backchain works live.** Luna wrote the plan-stage contract with `required_trivial_reviews: 0`, the exit text from the packet plus case clauses and the `Backchain passes: one` marker line (8,717 B against the 9,216 B budget); the loop completed in one action, 23.5 min from contract to terminal packet, against 105.7 min over 7 passes on 1.16.1 max. The step-plan revise loop also ran at gate 0 with the marker, one cycle. No whole Backchain loop started at the first step-plan (the max run had one of 136 min). Both models drafted the plan with the new `backchain-check` and fixed what it found.
- **Firm, planning windows.** Grok medium 72.7 min; Luna xhigh 375.9 (375.0 by stage clock); Luna max (1.16.1) 647.5. Per stage in docs/experiments/shiploop-planning-time-20261005/stage-clock.md. Spec and prepare did not get faster on Luna; plan 196.4 to 121.0, step-plan 187.7 to 38.7, test-spec 61.2 to 39.9, research 24.7 to 10.1.
- **Firm, time is tokens.** Luna emitted 1.15M output tokens in the window at a constant ~55 tokens/s (OLS 55.6; R2 0.993); a model request was in flight 99.3% of it; every ShipLoop command together ran about 10 s. Reasoning is 59% of output tokens (encrypted; contents unknowable). The planning documents (116 KB, about 29k tokens) were rewritten about 3.1x. 30 minutes allows about 100k output tokens including reasoning; the planning window produced 11.5x that.
- **Firm, where the Luna xhigh minutes sit (tiling by timestamps).** Improve review children 203.4 min (54%: 5 children, 22 passes; 12 changed something = 146.5 min, 10 changed nothing = 28.2 min; opening each cost 1.2-10.5 min, 26.3 in all; about 247 KB of review paperwork per child against 112 KB of reviewed documents); plan-stage Backchain work 64.1 (17%, of which 22.5 was reading and the first plan.md draft before any Backchain artifact, 21.8 the one loop pass); all other authoring 108.5 (29%). Intake, discovery, research, prepare and select-work took 131k output tokens (41.5 min) to produce about 5.5k tokens of final text: their cost is reasoning and reading, not document size.
- **Firm, the small things.** Retries, refusals and failed edits 14.2 min central in the window (3.8%; ceiling 33.4); compaction recovery at most 32 (8%); kill recovery 12-24; together at most about 90 min, so at least 285 min remain with all of it removed. The 2-hour background-task limit killed the harness at 120.3 min intervals (the stored "about 30 min" note is stale).
- **Firm, the revise loop is the single largest waste.** The W1 test-red failed because the plan gave the tests no real module to load; the run went back to step-plan and test-spec. The redo cost 165.9 min of stages (28% of the Luna xhigh run) against 99.2 min the first time through them, and 123 min in the 1.16.1 run; Improve and Backchain review at planning missed the gap both times.
- **Firm, Grok medium.** Its Improve children: 5 children, 26 passes, 42.4 min (58% of its 72.7), about 1.6 min a pass against Luna's 9.2. Its spec review took 9 passes, six of which changed the spec, and four consecutive commits widened one import allow-list (one concept, four passes). The other 30.3 min (authoring, Backchain, intake to research, prepare, select-work) sit at the 30-minute ceiling by themselves. It chose one work item where Luna's plan had three.
- **Interim, what would reach 30 min.** On Luna xhigh the floor with no model-run Improve and no Backchain loop beyond the plan.md draft is 115-131 min (108.5 other authoring plus 7-22.5), so loops alone do not do it; lower reasoning effort and less reading are also needed. On Grok medium, removing the stage-by-stage Improve reviews would leave about 30 min. Levers and savings (L1-L18) are in ledger-account-final.json: no model-run Improve at planning 203 min gross on Luna; one review at the end 118-178; `--backchain-passes none` 22-57 (shipped, no code change); script lint instead of model-written check scripts (100 scripts, 74 min) 35-55; cheaper revise up to 67 per escape; size caps about 49; effort per stage unknown (no experiment).
- **Exploratory, not measured.** What the 683k reasoning tokens contain; what dropping review costs downstream (review caught 5 warranted fixes in the Luna window but missed both replans); Grok medium's build quality on this version (the probe stopped before implementation); Luna at high or medium effort (never run).

Owner decisions open: remove or collapse the stage-by-stage Improve reviews at planning (strains "steps iterate until a check confirms each exit criterion" and S-10, needs an engine change and a SPEC carve-out); `--backchain-passes none` as the default (one constant and its pins); script-owned lint for document checks; a cheaper revise path. **Superseded 2026-10-05:** the first of these is decided as `--planning-review stage|none` (see "Planning review" below and `docs/shiploop-planning-review-plan-2026-10-05.md`); the other three are out of scope there (D10) and stay open.
Corrections: the ledger evaluation called the Luna run's stop at 14:32Z unexplained; it was the owner's instruction to stop it (killed at 07:32 PDT). The Grok probe's auto-stop missed the baseline step between two polls and the host ran into test-author before it was killed (planning minutes are unaffected).
Related: 520bfb85 (1.21.1), 1411d5f1 (1.21.0), 9747d769 and 0df9b0c4 (the one-pass carve-out and text), 04ad68a2 (Codex xhigh default).

### Planning review — 2026-10-05 — status: I3, I0, I1, I2 and review fixes R1 built (hermetic tests green); live behaviour unverified; I5 (the default flip) is the owner's

Question: the owner said "yes, do the planning review change" with a 30-minute ceiling for the planning window (intake to the first test-spec accept). The design (its repository copy lands with the SPEC carve-out commit, I0; the evidence for I3 is finding F9 of `docs/experiments/shiploop-planning-time-20261005/ledger-account-final.json` and the test table below): a run option `--planning-review stage|none`, a SPEC carve-out, and, first and independent of the option, a guard for the defect class that cost the most minutes in the Luna xhigh run. Increments: I3 (the test-author probe), I0 (SPEC carve-out and evidence), I1 (option, value `stage` only), I2 (`none`), I5 (the default flip, the owner's decision, after measurement).

Findings behind I3 (see "Planning time" above for the run data):
- **Firm, the W1 redo was not detection-limited.** The Luna xhigh W1 `test-author` accepted `done` while saying its focused command had not run (the file the tests load did not exist). `test-red` forbids product edits and its gate returns on any outcome but `done`; the host sent `revise` there, so the gate never ran. Nothing owned the missing file, and `test-author`'s own done-when ("each case in the test spec has a test the focused command runs") had no script check because the row had no `complete_runs`. The redo cost 165.9 min against 99.2 first time through (28% of that run; F9). The real judge already refuses a recorded node:test missing-module output at red mode (`ids-missing` with IDs, `uncounted` without): measured on a fixture, kept as a guard test.
- **Firm, the first design of the probe was wrong.** Judging every exit code in red mode makes an exit-0 run with no readable count (`green`) and an exit-0 run whose listed IDs never appear both acceptable, so an exit-0 run that ran nothing passes. Reproduced on seven recorded outputs; the corrected judge (exit 0 in passing mode, non-zero in red mode, accepted `passed` and `red`) refuses both and still accepts a counted pass and a counted failing test. The seven outputs, the other three refusal statuses and the two real node outputs are rows of `PROBE_CASES` in test/shiploop-test-loop.test.py.
- **Not covered by the probe.** A test that contradicts its own helper (the 1.16.1 implement revise, 123 min) looks RED at `test-red`, so it passes the probe. The probe protects the run total, not the planning window.

Implemented (I3):
- `test-probe` complete run on the `test-author` row; `test_loop.PROBE_STAGE`; `verify` runs the focused commands once at that stage and records `expect: "a test ran"`; one focused-run gate in the navigator serves `test-author` and `test-red` (S-12); the refusal has its own header ("did not run a test"), names the placeholder rule in its closing sentence instead of the red stage's "not the product code", and after `MAX_REFUSED_RUNS` refusals names `revise`. Two generic sentences in the `step-plan` and `test-author` duties (S-8). SKILL.md and the testing reference say so.
- Verification: fail first on the unchanged tree (refusals "not raised", records missing, `PROBE_STAGE` and `PROBE_RULE` absent), then green. Packets: of 778 captured texts (574 dry-run packets, 204 catalog duties, prompts and Improve prompts, both delegations) 736 are byte-identical and the 42 that differ are the step-plan and test-author packets, each by exactly the added sentences; every spec, test-strategy, plan and test-spec packet and all 68 Improve prompts are identical.
- Cost: one more run of the focused commands per `test-author` done (the path ShipLoop already runs at `test-red`). Run Review baselines: `script_verifications.records` gains one record per `test-author` action, so a record count is not comparable across this change.
- Verification of the final tree (after the I3 commit e11b86ef, `SHIPLOOP_PROGRESS=off`, exit codes taken before any filter): the footprint named for this change, the whole `test/shiploop-*.test.py` family (62 files, the chain suites included; `shiploop-chain-lifecycle` alone took 1,306 s under load), the improve suites, `skill-interop-hygiene`, `skill-frontmatter` and `test-groups`/`ci-policy`: 66 files exit 0, 1,357 unittest tests in 64 of them; `shiploop-e2e` 229 tests; the apparatus suites through the real navigator (`check_suite.py --skill-root skills/shiploop`) mock 35 and all 338. Fail first was run on a throwaway worktree of origin/main d1cca62f: 8 new or changed tests failed for the right reason and 4 labelled guards passed.
- Correction: the message of e11b86ef says `test-loop` has 46 tests, 8 new. It had 45 and has 54: 9 new, the ninth being the real-runner guard (`test_the_probe_accepts_a_real_failing_test_and_a_real_counted_pass`) added before the commit. A landed message is not edited.
Related: 9747d769, a89135f7, 0df9b0c4, a34a6ee6, 2f091a35, a9f592a3, 4484b25a.

Decided and recorded (I0, SPEC-first, docs and a harness test only; the option code follows):
- **Decision record.** `docs/shiploop-planning-review-plan-2026-10-05.md` holds the two modes (what each keeps and loses), the carrier of each exit criterion per stage and mode, the Change-admission disposition of every finding of both attacks (9 and 10) and of the owner's rules, the alternatives and why each is out of scope, the measurement plan M1 to M4 and the revert rule. The evidence is in `docs/experiments/shiploop-planning-review-20261005/` (final design, the draft the attacks read, four reports, two attacks, the Sonnet commit `b1e196d` message, the E6b excerpt, the probe-judge and per-pass scripts with their output). SPEC: a second `S-10 carve-out, owner decision 2026-10-05` (S-10's head now says "carve-outs").
- **Owner resolutions (2026-10-05).** D1 the default stays `stage` in code until the owner flips it (the flip, I5, is a later dated SPEC commit plus one constant, not part of this work); D2 `once` and `plan` are not built; D4 the per-item merge is rejected; D5 the probe landed first; D6 the ceiling counts the journal's window (intake to the first `test-spec` accept); D7 recording `planning_review` in baseline rows and the exporter is a handoff to the Run Review session; D8 the owner is told before any release; D9 the end-of-work review does not carry the planning documents (revisit after M2); D10 L11, L17 and `--backchain-passes` defaults are out of scope.
- **Firm, the counts.** Review is 54% (Luna xhigh: 203.4 of 375.9 min, 22 passes) and 58% (Grok medium: 42.4 of 72.7, 26 passes) of the planning window, 79 to 80% of that in the global trio (spec, test-strategy, plan). `none` leaves 26.8 to 30.3 of 72.7 on Grok medium if no work moves into authoring and about 40 to 44 if the five first passes (13.3 min, `passes.out`) do; 172.5 of 375.9 on Luna at best.
- **Firm, the structural hole.** No script-run check at planning, in any mode, covers whether the spec's criteria are complete and verifiable, whether the test strategy maps every criterion to a check, or whether a test spec's oracles are independent. The Improve child's own S-9 evidence was loop mechanics, never a check of the review's content, so `none` removes a second look, not a script-run check. What carries the rest: ShipLoop's gates at `complete`, the I3 probe, the later red, green and regression gates. The carve-out says this and says it strains the owner's step rule and the enterprise-rigour rule.
- **Interim, savings.** The `none` figures are arithmetic upper bounds on saving; no run without the planning reviews exists. The share of pass 1 that is a second authoring pass (74.4 min on Luna, 13.3 on Grok) and would move to the producer is unmeasured. Stage times vary about 2x between runs of one model.
- **Exploratory, quality.** The escape rate without review is unknown. Measured catches the first draft omitted: a Sonnet 5.5 plan review caught a missing importable-server seam (`b1e196d`, the class that cost Luna 165.9 min when its reviews missed it), and the review with the platform-claim bullet caught 10 of 15 real plan-stage errors against 0 of 15 (E6b; Sonnet, condensed packets, three trials per cell). Break-even on Luna: 1.2 to 3.0 extra escapes per run; on Grok the cost of an escape was never measured.
- **What the attacks changed.** Attack 1 (9 findings): the flip is gated by M1 and M2 and is its own commit (accepted), but its premise that Backchain `none` shipped as an opt-in is wrong (`a89135f7` made one pass the default in the same release); `once` is excluded on the owner's window only (figures now per window and clock); the omitted catches are in; `stage` packets stay byte-identical. Attack 2 (10 findings): the probe judge fix (built in I3), the `once` findings are moot while `once` is not built, the plan child's missing `improve-commit` route is rejected for `stage` and `none` (omitted today in every run), and the first Improve card resolving at the end of a `none` run is a recorded limit, not an engine change.
- **A correction to the design.** It said the spec and test strategy are committed "before any review" under `none`. The knowledge commit follows any accepted stage; under `stage` that is after the review, under `none` it is at `complete` with no review of them at all. The SPEC says "committed when each is accepted and no Improve child reviews them afterwards".
- **Handoffs to the Run Review session** (files that session owns, not edited here): record `planning_review` from `state.md` in baseline rows and the export (D7) so cells are not compared across modes silently; an exporter that reads no improve evidence reports zero passes and zero minutes with no reason, so a `none` run and a run with missing evidence look the same (unmeasured must read unknown); its phase-1 expectation text "The script accepts each only after its Improve review" is untrue under `none`; item a24 of `docs/shiploop-run-review-journal.md` ("compare Improve's planning passes") is answered by M1 to M4.
- **Increment status.** I3 landed (`e11b86ef`, `7ad157cb`); I0 is this commit; next I1 (the option, value `stage` only, packets byte-identical) and I2 (`none`). Parity tests (the carve-out's values against `PLANNING_REVIEW_MODES`) arrive with I1 as a subset check and with I2 as equality; the default parity test arrives with the flip, because the SPEC states no default until then.
- **Verification (I0).** Fail first, on the unchanged tree (test file edited, docs not yet): 3 of the 7 `FastPlanningRecordTest` tests failed for the right reason (the phrase "carve-outs below" absent from S-10; the journal did not cite the new directory; the superseded documents had no "Superseded 2026-10-05"), the 4 existing ones passed. After, with `SHIPLOOP_PROGRESS=off` and each exit code taken before any filter, all exit 0: `shiploop-e2e` 231 tests (229 before), navigator-contract 75 (its `BackchainPassesOptionTest` reads both carve-outs), navigator-dry-run 26, improve-schedule 13, actual-improve-cli 32, test-loop 54, stage-spec 8, packet-bounds 8, guidance 38, delegation 47, full-runtime 2, lint 81, improve-runtime 12, `improve.test.sh`, test-groups 21, ci-policy 10, `shiploop-run-review` 212 (it reads the SPEC), skill-interop-hygiene, skill-frontmatter (22 skills), and the apparatus suites through the real navigator (`check_suite.py --skill-root skills/shiploop`): mock 35, all 338. No skill, script or prompt changed, so no packet golden applies to this commit.
Related: 9747d769, a89135f7, 0df9b0c4, a34a6ee6, 2f091a35, a9f592a3, 4484b25a, 4af28a7e, 47bba520, b960891b, 520bfb85, 1411d5f1.

Implemented (I1, the option with its one registered value; no behaviour change):
- **The option.** `PLANNING_REVIEW_MODES = ("stage",)`, `DEFAULT_PLANNING_REVIEW = "stage"` and `reviewed_stages(mode)` in `shiploop_stage_spec.py` (the navigator re-exports the two constants; `reviewed_stages("stage")` is `with_improve("always")`, and nothing calls it until I2 changes the checkpoint). State key `planning_review` in `_STATE_KEYS`, `new_state(planning_review=)`, a value check in `new_state` and in `_validate_current_state`, `recorded_planning_review`. `--planning-review` on `init`, `workspace start` (forwarded to `init`) and `graph-dry-run`, its choices read from the constants, so `none` is refused by the CLI as an invalid choice until I2 registers it. `guidance.prompt` and `guidance.duty` take it keyword-only with the literal default `stage` and no text change. No `--set` verb, no environment variable. A saved run without the key is refused through `next`, `report` and `init` with `missing: planning_review` and the fresh-run hint; nothing is migrated.
- **One retry guard (S-12).** `_require_retry_fixed_option(requested, flag, label, recorded)` in `shiploop_protocol.py`; `_require_retry_backchain_passes` is rewritten onto it and `_require_retry_planning_review` is its second caller at both retry sites. The backchain messages are byte-identical (a test pins the full sentence and passes on the unchanged code). The design's signature also carried `existing` and `run_dir`, which the guard never reads, so they stay on the two thin wrappers only (the call-site shape the lint and delegation guards have).
- **Byte identity, proven.** Captured before the first edit and again after, at `6db8ef7a`, both delegations: 574 dry-run packets (every scenario, every stage, the plan Improve packet included) and 204 catalog texts (prompt, duty and Improve prompt of each of the 34 stages). The baseline was rendered twice (equal, so the render is deterministic); 778 of 778 identical after, and the two 17.1 MB capture files are `cmp`-equal. The in-repo pin is deliberately weaker than a golden: naming `stage` renders exactly what omitting it renders, for every stage and delegation, and the catalog still renders the default. No whole-text golden is committed (a committed golden of these packets would be rewritten by every unrelated prompt edit); the method is `golden.py` over `shiploop_navigator_dry_run.run_scenario` and the catalog, normalising only the random action ids, request tag and feature-folder suffix.
- **A test technique for an option with one value.** With `stage` the only registered value, a changed retry cannot be named through the shipped CLI (it is refused as an invalid choice first). The two retry refusals therefore run the real CLI in a child process that registers a second value in `shiploop_stage_spec` before the navigator is imported (`FORCED_SECOND_VALUE` in `PlanningReviewOptionTest`): real parser, real run-directory load, real retry gates at `init` and `workspace start`. The shim does nothing once I2 registers `none`, and the SPEC parity test is a subset check until then (equality arrives with I2).
- **Fail first (I1).** On the unchanged source with the new tests in place: 12 of 13 new tests failed for the right reason (`PLANNING_REVIEW_MODES` and `_require_retry_planning_review` absent, `prompt() got an unexpected keyword argument 'planning_review'`, `KeyError: 'planning_review'` on a state without the key, `--planning-review` unrecognised so no `invalid choice`, no `### Planning review option` heading, the carve-out's key absent from `new_state`) and the one labelled guard (the backchain retry messages) passed. After the change all 13 pass.
- **Verification (I1).** `SHIPLOOP_PROGRESS=off`, every exit code taken before any filter: the whole `test/shiploop-*.test.py` family plus the improve suites, `prompt-marketplace-contract`, `skill-interop-hygiene`, `skill-frontmatter`, `test-groups` and `ci-policy`: 70 files, all exit 0, 1,602 unittest tests in 65 of them (`shiploop-chain-lifecycle` alone 52 tests in 1,382 s under load). Of those: navigator-contract 86 (75 + 11), navigator-dry-run 27 (26 + 1), stage-spec 9 (8 + 1), `shiploop-e2e` 231, improve-schedule 13, actual-improve-cli 32, test-loop 54, packet-bounds 8, guidance 38, delegation 47, full-runtime 2, lint 81, improve-runtime 12, `improve.test.sh`. The apparatus suites through the real navigator (`check_suite.py --skill-root skills/shiploop`): mock 35, all 338.
- **Handoffs.** To the Run Review session (files it owns, not edited): `skills/shiploop-run-review/scripts/export.py` reads `state.get("backchain_passes")`; it should read `planning_review` the same way and `SCHEMA.md`, the baseline rows and `test/shiploop_e2e/metrics.py` should record it so cells are not compared across modes silently (D7). To I2: the checkpoint, the validator's required set and the packet text still read `guidance.PLANNING_REVIEW_STAGES`; `reviewed_stages` is where `none` goes.
Related: 9747d769, a89135f7, 0df9b0c4, a34a6ee6, 2f091a35, a9f592a3, 4484b25a, e11b86ef, 6db8ef7a.

Implemented (I2, `none`):
- **The mode.** `PLANNING_REVIEW_MODES = ("stage", "none")`; `PLANNING_CHOICE_STAGES` (the five stages the option covers: `spec`, `test-strategy`, `plan`, `step-plan`, `test-spec`); `reviewed_stages("none")` is `with_improve("always")` minus those five, so `system-test-author` and `release-plan` keep their child and the last `carry-forward`'s rule is not the option's. `_improve_checkpoint` (the one place that decides whether a result parks a child) and the validator's required-record set read `reviewed_stages(recorded_planning_review(state))`. `guidance.PLANNING_REVIEW_STAGES` (the seven; it feeds `STEP_PLANNING_STAGES`, which drives which packets print the accepted spec and plan sources) and `_IMPROVE_STAGES` (the allow-list for where a record may sit) stay static: a record at an unreviewed stage can only come from a hand edit, and the required set and the active-child check carry the rule. Two refusals are reworded for every mode: "including every planning-stage result this run's planning_review option reviews", and "a stage that does not start an Improve child in this run (planning_review: X)" (the stage-mode text changed too, so `test/shiploop-improve-schedule.test.py` and `test/shiploop-workspace.test.py` pin the new words). Walks of a two-item run: `stage` starts 10 children, `none` starts 3 (the last item's `carry-forward`, `system-test-author`, `release-plan`) and none in the planning window.
- **Packet text, one table.** `_NO_REVIEW_SWAPS` in `shiploop_prompts.py`: seven `(stage, old, new)` rows applied only for the recorded mode `none` (`*` is the sentence every packet carries): COMMON's handoff sentence (its list is built from `reviewed_stages("none")`), the plan duty's promise, the two Backchain-call sentences of the plan packet that name the review (`cannot clear ordinary Improve`, `not the separate Improve executor's authority`), and the step plan's three promises (delegated paragraph, inline paragraph, and "the next review is the packet's automatic Improve handoff"). `_check_swaps` runs at import: each `old` must occur exactly once in every stage-mode text it occurs in (both delegations, the plan's Backchain call) and in at least one, so an edit to the text above that leaves a row matching nothing or twice fails the import. The test-facility sentence uses the existing mechanism with `improves` read from the mode. In the navigator: `_improve_line(state, stage)` says no child starts and ShipLoop's checks at `complete` are the only gate; the plan's purpose line drops "its Improve child evaluates whether the evidence supports it"; the experiment guide, notebook and "keep detailed experiment prompts" lines are not printed (at `discovery` and `research` too: they locate the plan child's notebook); the plan's work-queue rule drops "including after reconciliation" and "or Improve final_result".
- **Byte identity, proven.** Every packet the dry-run renders (574, every scenario, every stage, the plan Improve packet included) and every catalog text (204: prompt, duty and Improve prompt of the 34 stages), both delegations, captured before the first edit of this increment at `7317f458` and again after: 778 of 778 identical, the two 17.1 MB capture files `cmp`-equal, and the baseline rendered twice was equal. The in-repo pins are content pins: each swapped sentence is in the stage render exactly once and absent from the none render, naming `stage` equals omitting it, and the catalog renders the default.
- **The scan.** `PlanningReviewNoneTest` renders the real packet of every planning stage for each mode and delegation (and `--backchain-passes one|converge|none`) and requires that the Improve line promises a child exactly where the mode starts one and that every other sentence naming Improve at an unreviewed stage is on a reasoned list (twelve entries: the nested-review prohibition, the generic retention rules, the status and progress rules, the chain-precedence rule, and the none texts themselves). The first run of the scan flagged the chain-precedence sentence of an ask-agent packet and the new none sentences, none of which the design's inventory had listed, so the list, not a shorter scan, took them. A document scan (`PlanningReviewDocumentsTest`) requires every document that says a planning result is followed by an Improve review to name the option or sit on a reasoned list (six reference documents that only describe what a review challenges), plus content pins for the documents that state the schedule.
- **Apparatus.** `dag_replay.py` keeps one literal checkpoint table per mode; every case declares `planning_review` (a case without one is refused) and `synthetic-none-full` replays a none run (37 events: 34 producer callbacks and 3 Improve completions); `workflow_review.py` judges the Improve inventory against the schedule of the mode a state records and reports a state that records none as unverified. `shiploop_navigator_dry_run.py` holds `REVIEWED3` as a literal table per mode and `graph-dry-run --planning-review none` simulates the none schedule (37, 55, 39, 39, 43, 39 and 1 events for the seven scenarios, computed by hand in the test).
- **Deviations from the design.** (1) The design lists a change to the `test-spec` duty; that duty makes no Improve promise (the sentence the design attributed to it, "the next review is the packet's automatic Improve handoff", is in the `step-plan` duty), so the table has a third `step-plan` row and none for `test-spec`. (2) The two Backchain-call sentences of the plan packet are swapped too (the design's consumer list named them for the docs; the packet carries them). (3) The `improve-reconcile` route under none is refused by the existing gates ("requires the bound active initial plan Improve child", and "allowed only before prepare" once plan is accepted); no new refusal was added. (4) `FORCED_SECOND_VALUE` (I1's test shim) is deleted: the retry refusals now run through the shipped CLI with `none`.
- **Fail first (I2).** Final test files run against a throwaway worktree of `7317f458`: 12 of 24 tests in `shiploop-improve-schedule` fail (none is not a value; the reworded refusal; `scenarios()` takes no mode), 1 in `stage-spec`, 2 in `navigator-dry-run`, 18 distinct tests in the three navigator-contract classes, 4 in the apparatus (`test_dag_replay`, `test_workflow_review`), and the one reworded pin in `shiploop-workspace`. The reasons are all "`none` is not a registered value", "refusal text not reworded", "swap table and `_check_swaps` absent", "documents do not name `none`", "case declares no planning_review". Labelled guards that pass on the unchanged code: the `stage` halves of the forged-child and assumption-list tests, and the stage-mode packets.
- **Verification (I2).** `SHIPLOOP_PROGRESS=off`, every exit code taken before any filter, on the final tree: the whole `test/shiploop-*.test.py` family plus `improve-*`, `prompt-marketplace-contract`, `improve.test.sh`, `test-groups` and `ci-policy` (67 files) ran once with all exit 0 (1,626 unittest tests; `shiploop-chain-lifecycle` alone 52 tests in 1,439 s under load) and again after the last documentation edit with 64 of 65 exit 0 (chain-lifecycle and `shiploop-e2e` excluded); the one failure was a document pin that this increment's own rewording of a sentence had broken, fixed and rerun green. Final counts: navigator-contract 99 (86 before; 13 new), navigator-dry-run 28 (27), improve-schedule 24 (13), stage-spec 9, `shiploop-e2e` 231, test-loop 54, packet-bounds 8, guidance 38, delegation 47, full-runtime 2, lint 81, improve-runtime 12, `improve.test.sh`, test-groups 21, ci-policy 10, `skill-interop-hygiene`, `skill-frontmatter` (22 skills); the apparatus suites through the real navigator (`check_suite.py --skill-root skills/shiploop`): mock 37 (35), all 341 (338). `scripts/check-release-boundary.py --base origin/main`: OK. A real `none` run through the shipped CLI (init, five `complete` callbacks, `prepare` with its knowledge commit, then `select-work`) had no child at any planning stage. No failure needed a base comparison.
- **Not verified (needs a run).** That a host reads no difference in a `stage` run (the packets are byte-identical, so none is expected); that a `none` run's host does not look for a review it was told is absent; the minutes a `none` run saves (M1 and M2 of the plan document); the quality cost of the missing second look, which no script-run check replaces (the SPEC carve-out says so).
- **Handoffs.** To the Run Review session (files it owns, not edited): record `planning_review` from `state.md` in the exporter and the baseline rows (D7), so a `none` cell is not compared with a `stage` cell silently; a run with no Improve evidence reports zero passes and zero minutes, which now also describes a none run's planning window (unmeasured must read unknown); its phase-1 expectation text "The script accepts each only after its Improve review" is untrue under `none`. The `skills/rubric-eval/suites/architecture-v4/make_packet_frame.py` frame and the shipped `references/graph-dry-run-scenario.json` depict the stage schedule and need an explicit `stage` pin only at the default flip (I5).
Related: 9747d769, a89135f7, 0df9b0c4, a34a6ee6, 2f091a35, a9f592a3, 4484b25a, 7317f458, 6db8ef7a, e11b86ef.

Implemented (R1, review fixes on I3, I1 and I2; 2026-10-05):
- **What the review found, and what was done.** A review of `e11b86ef`, `7ad157cb`, `6db8ef7a`, `7317f458` and `f6ed230f` by four lenses (engine, tests, identity, rules) gave 4 actionable findings and 15 minor ones; each was reproduced before it was accepted or rejected. Accepted and fixed: **E1/T1** (major) the test-author probe accepted a Python unittest module that cannot be imported as a RED test (see below); **F1** (blocker) a `--planning-review none` run started without `--improve-skill` blocked at its first `static-checks` (see below); **F2** (major) the document scan was scoped by document, so any document that named the option once could carry any false sentence, and several did; **E2** the probe's refusal header and its not-red reason said no test ran, or told the author to make a passing test fail, for a run in which tests ran; **E3** and the identity lens's F1 two sentences promised a review in a none run in words the packet scan could not see ("Each reviewed step's ...", "the normal Improve handoff"); **T2** the none CLI helper looped without a bound, so a schedule regression hung the suite for 30 minutes instead of failing in seconds; **T3** three behaviours had no pinning assertion (mutants P15, P16, R7 survived); **T4** (the document scan's scope, answered by F2); **F3** (rules) the oracle note, and **F3** (identity) the record, mis-stated what the change does; **F4** the record and this heading still described the tree at the I0 commit; **F5** the Sonnet catch was called "the same class" as Luna's defect. Rejected, with the reason: **F2** (identity) and **T5**, no committed stage-mode golden (the owner rule keeps the byte-identity golden a verification, not a committed whole-text test; the finding itself says it is not required, and identity was proved again, below); **T6**, the workflow-review oracle test runs in the full apparatus group, which CI runs on release commits by its existing policy; **F6**, the branch base (`d1cca62f`, origin/main is a docs-only commit ahead): the integrator merges, a rebase here would rewrite landed commits; **F7**, a "Handoffs" section in the decision record: the handoffs are recorded accurately in this journal and in the commit messages and the report lists them, a new section is not a one-line contradiction fix; the one new handoff (F1) is below. **The identity lens's suggestion** to make the none-packet scan also flag "reviewed" generally is not taken: 20 sentences of the five none packets contain a review word without naming Improve, all about Backchain, Until Loop or the host's own checks, so a general flag would be an allowlist of 20 legitimate sentences; the two promising phrases are pinned at all 34 stages instead.
- **Firm, E1/T1: the probe did not refuse an unloadable unittest module.** unittest's loader reports a module it cannot import as one synthetic test (`unittest.loader._FailedTest`) that errored; `Ran 1 test` and `FAILED (errors=1)` count it, so `shiploop_test_counts._unittest` read `ran=1 failed=1`, the judge said `red`, and the probe accepted it (reproduced through the CLI: `complete` outcome done with a focused command printing the recorded output and exiting 1, no ids; the same command with ids was refused). Every other runner's load-failure output was already read as no test (jest, pytest collection, node --test in both reporters, go build, mocha, vitest, rspec, cargo, dotnet, gradle): unittest was the one mis-accepted, and `test-red` and `test-green` inherited it, so the W1 defect class still reached `implement` for Python projects without IDs. Fixed in code, in the counts, not in prose (S-8): the loader's `ERROR: ... (unittest.loader._FailedTest...)` entries are taken out of both `ran` and `failed`, so an unloadable module reads `ran=0` and is refused as `no-tests`. Real output of Python 3.14 is the fixture, with the 3.8 to 3.11 spelling. The limit that remains, stated in the SPEC carve-out: a command that runs a failing test and also has a module that cannot load, with no ID listed for it, is accepted (a count cannot tell); `PROBE_CASES` pins it as a labelled known limit.
- **Firm, F1: under `none` nothing binds the Improve card before the first item's loops read it.** `state["improve_skill"]` is first recorded by the first `improve-bind`; under `stage` that is at `spec`, under `none` at the last item's `carry-forward`. The quality loop (`static-checks`) and the test loops read it at every item, so in a default-init `none` run the first `static-checks` packet said "Unavailable: no Improve card is bound to this run ... Report outcome blocked", a host that reported done was accepted with no loop evidence, the test loops silently lost their Until Loop, and no verb binds a card without an active child. The design's claim that a missing card was "a recoverable stall at the end of the run" (A2-10) was wrong, and so were the places that said the card is first needed at the end (SKILL.md, the SPEC carve-out, the decision record in its modes table, quality list, alternatives, limits and A2-10 row, this journal's Attack 2 bullet, the change note). Reproduced on the pure navigator before the fix: stage prints "Bound Until Loop card", none prints "Unavailable". Built: `init` and `workspace start` refuse `--planning-review none` without `--improve-skill=<absolute selected Improve SKILL.md>` and resolve the card there (`standalone.resolve_skill`), before anything is created (a refused `workspace start` leaves no root, worktree or branch); an identical retry of an existing run is recovery and needs no flag. One helper, called at both entry points (S-12). The state API is not guarded: `new_state` still takes an empty card (the dry-run and the oracles build none states without one). The consequence for the default flip: with `none` as the default every new run must name its card, so the flip also makes `--improve-skill` required; the record says so at I5. Tests: the CLI refusals and the recovery through the shipped CLI, and a labelled guard that a none run started with the card has both loops bound and refuses done without the loop terminal packet.
- **F2, the document scan.** `PlanningReviewDocumentsTest` is scoped by sentence: a sentence that promises an Improve review at a planning stage must itself name the option (`planning_review`, `--planning-review`, a `stage` or `none` run, "when the run has one", "where the stage has one") or be on a per-sentence reasoned list (24 entries; five of them are sentences about children that start in every mode, which are listed one by one because a category regex let a sentence that also named the end-of-work review pass). The first run on the unchanged documents flagged 39 sentences. Qualified in place: `repeatable-test-suites.md` ("reviews each planning result" was false under none), three README table rows, the README example, the plan's dependency check (the obligation stays at `plan` in every mode and gains the review only in `stage`), `research-loop.md`'s dependency-check obligation (now "before the plan is accepted"), the `navigator.md` row, `behavioral-requirements.md` and `project-knowledge.md`, `backchain-planning.md`, and the e2e-audit harness README and SKILL and MOCK-REPLAY. Mutations killed: a new unqualified sentence appended to `navigator.md`, one inserted under "When Improve runs" in SKILL.md, and the original `repeatable-test-suites.md` sentence restored (the first mutant is the review's; the third survived a first version of the scan that exempted any sentence naming `end-of-work`).
- **E2, E3 and the small ones.** The probe refusal header is "did not show a usable test run"; a non-zero exit with only passing tests is told "exit 0 when its tests pass, or fail inside a test" (test-red keeps "fail on the missing behaviour"). Two rows join the none swap table for every stage the text is printed at (the inline step directive "Each reviewed step's" becomes "Each step's"; the interaction guide's "and the normal Improve handoff" is dropped), with the guard extended to the inline handoff and the interaction guide; the stale allowlist reason for the second sentence went with its entry. T3: assertions for the no-verdict probe attempt (no placeholder rule, "test or fixture") and the validator refusal's new words; the mutants P15 and P16 now fail. T2: `advance_to` stops after 60 steps naming the stage it stuck at. Wording corrections that a landed message or entry cannot carry: the oracle note and the I2 bullet above said `workflow_review` reports a state that records none as unverified; it reports a state that records **no** `planning_review` as unverified, and judges a `none` state against the `none` schedule (`test_the_inventory_follows_the_recorded_planning_review` pins both); I3 added three sentences to the duties (two at `test-author`, one at `step-plan`), not one each; `none` packets are shorter in bytes at all five planning stages but longer by 5 and 1 words at `step-plan` and `test-spec` (review measurement at `f6ed230f`); the I3 header "did not run a test" is the old header.
- **Byte identity, proved again.** Captured before the first edit of this commit (`f6ed230f`) and after: 574 dry-run packets (every scenario, every stage, the plan Improve packet included) and 204 catalog texts (prompt, duty and Improve prompt of each of the 34 stages), both delegations, stage mode: 778 of 778 identical, the two 17.1 MB capture files `cmp`-equal. In none mode the only change in 506 dry-run packets and 136 catalog texts is the two intended sentences (84 renders of the inline directive, 74 of the interaction-guide phrase).
- **Fail first (R1).** The final test files against a throwaway worktree of `f6ed230f`: `shiploop-test-counts` 2 of 11 fail (the unloadable-module counts and the judge in both modes); `shiploop-test-loop` 5 of 58 fail (two new `PROBE_CASES` rows, the unittest judge test, the E2 refusal wording, the header pin) and the loop-binding test passes (a labelled guard); `shiploop-improve-schedule` 2 of 27 fail (the init and `workspace start` refusals; the recovery test and the validator-words pin are guards); `shiploop-navigator-contract` 31 failing subtests in 4 tests (the sentence-scoped scan, the two phrases at 34 stages, the none packet scan without its stale entry, and the five document pins for the card requirement). The reasons are all "the behaviour is absent": no refusal, the unittest synthetic test counted, the sentences still promised.
- **Verification (R1).** `SHIPLOOP_PROGRESS=off`, every exit code taken before any filter. `run-all.sh --group quick --changed-from d1cca62f`: 40 of 40 suites exit 0 (navigator-contract 101 tests, 99 before; improve-schedule 27, 24; test-loop 58, 54; test-counts 11, 9; shiploop-e2e 231; workspace 59; run-review 212; mock apparatus 37). Beyond it: shiploop-full-runtime (2 tests), improve-runtime (12) and improve.test.sh pass; 34 more suites (the rest of the shiploop-* family, improve, improve-agent, improve-plugin, skill-interop-hygiene, prompt-marketplace-contract, dual-body-guard, integration-boundaries) all exit 0; shiploop-chain-lifecycle passes (52 tests, 1,755 s under load). After the last documentation edits navigator-contract (101), packet-bounds, guidance, improve-schedule (27), test-counts (11), stage-spec, navigator-dry-run, test-groups, ci-policy, shiploop-e2e (231), run-review (212), test-loop (58) and the mock apparatus suite (37) were run again, all exit 0. The apparatus suites through the real navigator (`check_suite.py --skill-root skills/shiploop`): mock 37, all 341. `scripts/check-release-boundary.py --base d1cca62f`: OK. No failure needed a base comparison.
- **Not verified (needs a run).** Whether a host given the refusal supplies the flag on its second attempt (the message names the flag and the form of the path); the unittest fix against the `_FailedTest` spelling of Python versions other than 3.14 and the 3.8 to 3.11 name (the fixture); live behaviour of a `none` run end to end, which still waits on M1 to M4.
- **Handoffs.** To the Run Review session (files it owns, not edited): any E2E cell that runs `--planning-review none` must also pass `--improve-skill=<absolute selected Improve SKILL.md>` in the `workspace start` or `init` its prompt names (`test/shiploop_e2e/run.py` and the case catalog are its files), or the cell is refused at its start; the earlier handoffs stand (record `planning_review` in the exporter and baseline rows and `metrics.py`; the zero-passes reading of a none planning window; the phase-1 expectation text; item a24; `script_verifications` gains one record per `test-author` action; `make_packet_frame.py` and `graph-dry-run-scenario.json` need a `stage` pin only at the flip).
Related: 9747d769, a89135f7, 0df9b0c4, a34a6ee6, 2f091a35, a9f592a3, 4484b25a, e11b86ef, 7ad157cb, 6db8ef7a, 7317f458, f6ed230f.

## Node Battleship on 1.22.0 (Claude Sonnet 5.5, `--source checkout`) and what stopped the Google Apps Script case — 2026-10-06 — status: firm for the run's numbers and the three findings' mechanisms; interim for their costs

**Question.** The owner asked to continue the E2E runs and watch the expected flow of building Battleship from one prompt (they meant Google Apps Script; the main harness has only the Node.js `battleship` case, so that case ran first and the GAS case is below). **Conditions.** `python3 test/shiploop_e2e/run.py --case battleship --host claude --source checkout` from a clean checkout of `81e0502f` (the marketplace gate refuses while run-review notes are pending, so a checkout build was the only route), skill-craft 1.22.0 / ShipLoop 0.54.0, planning review `stage` (the default), output `/Users/dadleet/e2e-runs/20261006/v1220-battleship-sonnet`, started 15:05Z. Related commits: the harness at `81e0502f`, the release `45f163d0`.

**Result (expected against achieved).** Expected: the flow tests first, then implementation, then verification, and a planning window under the owner's 30 minutes. Achieved: invoked, plugin, process, shiploop, committed and all four product checks pass; 1059.8 s, $6.5405, 238 turns counted from events (134 reported by the host), one session, no resume, 18 `node --test` tests, 18 commits. Planning (intake to the first test-spec accept) took about 7.3 stage-minutes (intake 0.2, discovery 0.1, research 0.1, spec 3.8, test-strategy 0.7, plan 0.7, prepare 0.3, select-work 0.1, step-plan 0.7, test-spec 0.6) with all five planning Improve children run; the whole run held 10 Improve children and 25 passes (at most 3 per child). Flow: baseline, test-author, test-red, three implement steps, test-green, test-refine, a second pass through step-plan, test-spec and the build stages, then regression, document, skill-assess, skill-validate, static-checks, verify, integrate, integration-verify, carry-forward, system-test-author, system-test, product-acceptance, release-plan, release-check, release, release-verify, operations and handoff (46 accepted stage records). Script verifications 14 of 15 passed; compactions, truncated outputs, cancelled tool calls and ShipLoop command failures are unmeasured on this host. Narrative: emitted 4, shown 0 (the same as the hello run on 1.20.0: emitted 8, shown 0); S-15 records it, it is not a verdict. The baseline line says nothing was compared, because no earlier row has this host, model and effort.

**Finding 1 (engine, open): `node --test` is uncounted.** `skills/shiploop/scripts/shiploop_test_counts.py` reads jest, vitest, pytest, unittest, mocha, cargo, go and dotnet, not node:test. The one failed verification is `run/tests/nav-4964e120cef043bda1bce0dcb834ddc4-verify1.md` (stage test-refine, item W1, 15:15:31Z): both focused suites passed with their listed IDs, but the regression run `node --test` printed `ℹ tests 13`, `ℹ pass 13`, `ℹ fail 0` and was recorded `uncounted` (counts null, minimum 12), so the verification failed and the step plan was revised after implementation; the second pass cost about two minutes. The 1.22.0 test-author probe refuses an uncounted run as well, so a node:test project whose focused command lists no IDs would be refused there. Fix (not built; the batch rule): a `_node_test` reader for the spec reporter's `ℹ` summary and TAP's `# pass`/`# fail`, a fail-first test on this captured output, a `skills/shiploop` patch note. Status: firm for the mechanism, interim for the cost (n=1).

**Finding 2 (audit apparatus, fixed): its freshness gate could never pass.** `skills/shiploop-e2e-audit/harness/freshness.py` looked for `plugins/shiploop`, `plugins/improve` and a catalog row per skill; since the one-plugin layout (`7370ff6b`) the package is `plugins/skill-craft/skills/<leaf>`, so every live audit case, `battleship-create` included, was refused with `required-package-tree-is-missing`. The hermetic tests used the old layout and stayed green. Fixed in `c27081e5` (19 tests, all failing first; the old layout is now refused, not read); the real gate printed `ready: true` on the launch below.

**Finding 3 (environment, owner action): the real Grok profile is not authenticated.** The audit launch for `battleship-create` (Grok 4.7 medium, 7200 s) passed freshness and then exited 2 with `harness-or-environment-error` and no message: `grok models` prints "You are not authenticated." and `~/.grok/auth.json` was rewritten at the attempt. No builder ran, no credits were spent, nothing was deployed (`/Users/dadleet/e2e-runs/20261006/gas-battleship-audit/battleship-create/`). Every Grok run is blocked until the owner runs `grok login`, including the main harness's Grok host and the planning-time probes. The audit preflight (`run.py check`) does not test authentication; a `grok models` probe there would refuse before any directory exists (candidate, not built). The test review (`docs/test-suite-review-2026-10-06.md`) recommends the offline single-player `battleship-gas` case in the main harness on Claude instead, which needs neither the login nor a deployment; the choice is the owner's.

## Google Apps Script Battleship one-shot, Grok 4.7 medium, audit harness `battleship-create`, 2-hour allowance — 2026-10-06 — status: firm for the run record; interim for the conclusions (n=1)

**Question and conditions.** The owner asked to run the Google Apps Script Battleship one-shot case end to end and watch the expected flow. Audit harness `skills/shiploop-e2e-audit/harness/run.py run --step battleship-create` from a clean checkout of `4dc6dae8`, Grok 1.0.46, `grok-4.7` at `medium`, `--timeout 7200`, the real Grok profile, ShipLoop 0.54.0 (the Claude marketplace clone, which Grok reads), planning review `stage`, Backchain one pass; launched 20:57:41Z after `grok login` (the first launch, before the login, exited silently: see the entry above). Output `/Users/dadleet/e2e-runs/20261006/gas-battleship-audit/battleship-create-2`; compact record `docs/experiments/gas-battleship-audit-20261006/evidence.json`. The owner authorized one dedicated deployment and the spend.

**Result (expected against achieved).** Expected: a full one-shot (planning, two work items, system test, release and deployment) inside the allowance. Achieved: the harness killed the builder at 7203.9 s (`exit -9`, `timed_out`); overall `invalid-trial`, process `failed-or-budget-exhausted`, protocol `incomplete-active`, product `unverified`. 990 tool calls (25 failed), reported usage null so the cost is unknown, 9 compactions (the first four took about 1.5 minutes each; the other five were not timed), 7 Improve children. 42 stages were accepted. Minutes since launch: intake 4.6, discovery 7.7, research 9.5, spec 27.5, test-strategy 38.3, plan 56.3, test-spec 63.8 (the planning window, intake to the first test-spec accept, is about 64 minutes, 2.1 times the 30-minute ceiling; the earlier Grok medium Node run took 72.7), work item W1 "Rules module and the 21 local cases" from 57.8 to carry-forward 85.4, work item W2 "Page, doGet, and manifest" from 85.8 to integration-verify 117.3, then its carry-forward Improve review was pending at the cap. Not reached: system-test-author, system-test, product-acceptance, release-plan, release-check, release, release-verify, operations, handoff. The flow before the cap held in the expected order for both items (baseline, test-author, test-red, implement, test-green, test-refine, regression, document, skill assessment, static-checks, verify, integrate, carry-forward).

**Nothing was deployed.** The builder reached the deployment MCP only through `search_tool` and `use_tool` (12 calls, all read-only: `auth status`, three `guide` reads, `setup settings`, an `ls` for "battleship", and searches for the deploy schema); no create, push, deploy or promote call. The partial product (`app/Code.gs`, `app/Index.html`, `app/Rules.html`, `app/appsscript.json`, `test/rules.test.js`, `test/page.test.js`) passes its own 26 `node --test` tests when run locally afterwards; that is not an independent verification.

**Findings.** (1) A stage-mode Grok medium run needs more than the audit harness's 7200 s allowance for this two-item GAS build: planning alone was 64 minutes and the two items about 31 minutes each; how much more the system test and release need is unmeasured. The earlier decision to try the 2-hour cap anyway is why this ended as an invalid trial, not a defect. (2) The planning window is the same order on both Grok medium cases (64 and 72.7 minutes), against 7 minutes on Sonnet 5.5, so the 30-minute ceiling is a host question before it is a prompt question; `--planning-review none` is the measured lever left (the audit harness's literal prompt cannot pass it). (3) Tooling: ShipLoop's run directory for an audit run is `.shiploop-runs/<product>-<stamp>/` beside the product directory, not inside it; `test/shiploop_e2e/progress.py` reads it when pointed there. **Open:** a rerun needs a longer allowance (`--timeout`), `none`, or the offline single-player case on Claude recommended by `docs/test-suite-review-2026-10-06.md`; the choice and any spend are the owner's.

## Full Node Battleship on Grok 4.7 medium with `--planning-review none`, 1.22.0 — 2026-10-06 — status: firm for the run's numbers; interim for the conclusions (n=1, different release than the stage comparison)

**Question.** After the stage-mode Grok runs (Node planning 72.7 min, the GAS case over the 2-hour cap), does `--planning-review none` bring a full one-shot on this host under the ceiling and still pass? **Conditions.** Main harness, `--host grok --source checkout` from a worktree pinned at `e824945f`, ShipLoop 0.54.0, the `battleship` case prompt plus one sentence asking for `--planning-review none --improve-skill <build>/skills/improve/SKILL.md` (the harness has no run-option flag yet, so the option rides in the prompt; the guard confirmed `planning_review: none` in `state.md` before the run continued), the case's four checks passed with `--check`. Output `/Users/dadleet/e2e-runs/20261006/v1220-battleship-grok-medium-none`; compact record `docs/experiments/grok-none-battleship-20261006/evidence.json`.

**Result.** All verdicts pass (invoked, plugin, process rc 0, ShipLoop done, committed with 17 files and 23 commits, 4 of 4 product checks). 93.6 minutes, 467 turns (lower bound), $12.50 (a lower bound: usage was unreported for most sessions), 5 compactions, 3 Improve children (5 review passes) against 10 children in the stage runs, script verifications 18 of 19, 52 accepted stages. Planning (intake to the first test-spec accept) was about 22 minutes against 72.7 for the stage probe of the same case, host and effort; the plan stage (one Backchain pass) was the longest at 8.4. Rest of the time: work item 1 about 16 minutes after its baseline, work item 2 about 24, the system-test phase about 18 (system-test-author 15.6, the largest single stage), the release phase about 12.5.

**What it supports, and what it does not.** It supports that, on this case and host, dropping the planning Improve reviews moves planning from 3x the ceiling to under it with the product passing its checks. It does not show what the unreviewed planning documents lost (no comparison with the reviewed set yet), it is one run, and the stage figure is from 1.21.0 (the release adds the option and the test-author probe). The pre-registered flip rule needs a second `none` probe.

**Findings.** (1) `shiploop_test_counts._SKIP_LINE` treats a test whose title contains the word `pending` (also `skip`, `skipped`, `todo`, `deselected`) as skipped, so a passing test titled "...pending cell..." counted as missing and `complete` was refused at system-test ("system-test is not done"); the model renamed it. Fix, with the `node --test` summary reader from the earlier entry, waits for the end of the batch: match skip markers only in runner syntax, not title words. (2) `complete` at release-plan was refused until the planning knowledge was written to the repository (the S-11 retention gate working as designed, one refusal). (3) The model hand-built 3 loop contracts (model glue), and the narrative was shown 1 of 22 times.

## Node Battleship from the batch-1007 build, Sonnet (checks on) and Grok 4.7 medium (checks off) — 2026-10-07 — status: firm for the run records; interim for the conclusions (n=1 each)

**Question and conditions.** Does the build (branch batch1007-68672e at bc1d6452: node:test counter, runner-syntax skip rule, `Checked by:` packet line, `get-next-work-item`, settled-fact lines, producer/Improve packet files) pass the Node Battleship case on both hosts, and do the fixes show up live? Both from the checkout source (`--source checkout`), launched in parallel, the Grok one with `--planning-review none` in the prompt as on 2026-10-06. Evidence: `docs/experiments/batch-1007-live-20261007/evidence.json`.

**Sonnet, checks on: PASS.** All six verdicts and 4 of 4 product checks; 20.0 minutes, 294 turns, $9.65 (the 2026-10-06 Sonnet run: 238 turns, $6.54). The extra turns are in static-checks (10 to 20), plan (8 to 17), spec (37 to 46) and implement (20 to 27). Whether the batch's longer packets caused that or it is run-to-run spread cannot be told from one run on each side; the cost is recorded, not explained.

**Grok, checks off: BLOCKED at system-test, honestly.** 47 stages accepted, planning 17.5 minutes (the 2026-10-06 run: about 22), 503 turns, $14.17 (a lower bound), 6 compactions, three host sessions (two cancelled by the task runner, resumed by the harness). The system-test stage reported `blocked_by access`: headless Chrome in the Grok host stayed on `about:blank` (`CVDisplayLinkCreateWithCGDisplay failed -6670`), so the browser case could not be observed; the restart-persistence case passed. The product is in the unreturned worktree, so the harness's commit and product checks fail and are not a verdict on the game. Chrome on this machine does load a local page headless when run directly afterwards, so the cause is the Grok host's sandbox or session, not proven.

**What the live runs support.** (1) The counter works: every focused and regression `node --test` run in both runs was counted (Grok: 12 focused passed, 4 red, 10 regression passed), with no `uncounted`, no `ids-missing` and no title-word refusal; this is the first pair of runs where `min_tests` could bite. (2) The settled-fact line worked as intended: Grok planned the browser case as its own `check` command, outside `node --test`, so the plain `node --test` (19 tests) passed without Chrome. (3) Three host sessions, two cancellations and six compactions in the Grok run all resumed from the packets and the ledger with no restart of finished work (the accepted-stage count only rose); this is the tenet's clear-the-context probe, unplanned but real. (4) The stage name `get-next-work-item` appears in both ledgers and exports. (5) The Improve packet no longer overwrites the producer packet (50 packet files, 2 `-improve.md`). It does not support: a quality judgement of either product (the Grok one was not returned), or that the Grok block is a defect: it is an environment access gap the engine stopped on rather than claim.

**Findings.** (1) Open question for the owner: when a required system observation cannot be made on the host, the run stops blocked, which is correct, but the case then yields no deliverable and the harness reports commit and product checks as failures; consider whether the harness should grade a blocked-by-access run as its own verdict. (2) The skill stages still ran as model turns (5 of 5 and 4 of 4 not applicable again; script-completing them was deferred by the audit). (3) The Sonnet cost rise is unexplained. **Superseded in part, 2026-10-08:** the rise is decomposed in "The Sonnet cost rise, decomposed" below. It is not "unexplained" in arithmetic (a fit of the host's usage reproduces both costs, and most of the rise is later calls re-reading a longer context), but its cause remains open (n=1 per side, a different Claude Code build on each, and the behavioural effect of the new packet text is not excluded).

### Investigation of the entry above, 2026-10-08 — did tests pass with null validation, and what blocked Grok? (status: firm; evidence `docs/experiments/batch-1007-live-20261007/null-validation-audit.json`)

**Null validation, yes, before this batch.** In the 2026-10-06 runs every focused and regression `node --test` record had `counts: null`: Sonnet 34 of 34, Grok 30 of 30, and `min_tests` was set but never enforced on 27 and 30 of them. They passed on exit code plus the ids shown, with a skip rule that read title words. This batch's runs counted every one (0 null). **Still exit-code-only:** the `check` suite. Sonnet's release-verify recorded `node --test` (39 tests) and `node --test test/system.test.js` (3 tests) as suite `check` with counts null: they ran tests, but zero tests would have passed. Grok's 10 check runs were all file-existence or grep checks, including `test -f browser.mjs` passing at five gates while `browser.mjs` had never passed. Fixed in this commit: output that shows a runner summary is counted even under `check`, and zero is refused (`no-tests`). Existence and grep checks stay exit-code checks by design.

**The Grok block, what is proven.** The delivered Grok product is sound: from the unreturned worktree, `node --test` 19 pass, `restart-check.mjs` exit 0, and `browser.mjs` loads the page and plays in Chrome from this machine's shell. But `browser.mjs` as written fails even where Chrome works (it reads `#status` right after a click that fires an async fetch, then tests the Enter result with a case-sensitive `/miss|hit|sunk/` against "Hit."); two lines fix both. So the block hid a second defect behind the environment one: the model-authored check had never run green. **Not proven:** why the page stayed `about:blank` in the Grok host (the 2026-10-06 Grok run drove Chrome with near-identical flags successfully; plain headless Chrome loads a local page from this shell). **Process finding:** the test-strategy probe was `Chrome --version` ("Chrome is installed"), so the access gap surfaced at W2 implement (about 50 minutes in), was deferred to system-test, and stopped the run at 101 minutes; a probe that loads a local page and reads the title back would have surfaced it in planning. Changed: the test-strategy duty now asks for that probe and for the access gap to be recorded in the strategy with the requirement it leaves unobserved.

**Blocked is a verdict that needs a person (SPEC S-14), not a defect.** The harness reports it with the engine's own reason and refuses to answer it; no harness change is proposed. What an owner can do with a blocked-by-access run: provide a host where the observation can be made, or accept the named requirement as unverified.

## Resume, stop and records: what the harness lost and what a resume told the host — 2026-10-08 — status: firm for the counts (recomputed from the run folders, `docs/experiments/resume-records-20261008/evidence.json`, rerun with its `collect.py`); the new paths are hermetic-tested and not yet seen in a live run

Source: the RESUME item of the batch 1008 plan (`docs/shiploop-batch-1008-plan-2026-10-08.md`), its design and two-agent audit (`docs/experiments/batch-1008-design-audit-20261008/design-audit.json` on the batch branch). The SPEC amendment is its own earlier commit (db51a260). Harness only: no skill, packet or engine file changed.

**What was wrong, and what changed**

1. [M] A Claude run built from a checkout was continued with a bare `shiploop next`. `ClaudeHost.plugin_cli` looked only under `<output>/marketplace`; on `20261007/v1230-battleship-sonnet` (`--source checkout`, build under `build/`) the old harness (8a198cdd) built the bare command, while the Grok folder `v1230-battleship-grok-none` got the exact one. The marketplace route had lost 13 turns to the same prompt (7c1f1014). Now one helper (`run.run_cli`) gives the CLI of the host and plugin the run started on (the host's installed copy for Grok and Codex, else the plugin build), the prompt always names it, the bare form is gone, `ClaudeHost.plugin_cli` is deleted, and a resume whose CLI file is gone is refused before a host starts. A run continued on another host keeps the first host's CLI. Status: firm (fail-first tests); never seen live (no Claude checkout run has been resumed).
2. [M] 3 of the 11 harness run folders with an `invocation.json` from 2026-10-04 to 2026-10-07 have no `result.json`, `metrics.json` or `review-export`: `v1200-battleship-luna` (stopped after about 48 minutes), `v1210-battleship-grok-medium` (a planning-only probe) and `v1210-battleship-luna-xhigh` (the owner's stop at 588 minutes). The 8 that ended on their own have all three. A task kill or an owner stop gives the harness no chance to write them. Now `--resume-run <dir> --grade-only` writes them from what is on disk, starting no host, for a run in any status that has a ShipLoop state, and `<output>/stop` ends a running host on purpose (see the README). **U3 settled:** `--grade-only` on a scratch copy of `v1210-battleship-grok-medium` (an active, stopped run) wrote `metrics.json`, `result.json` and a Run Review export (`review-export.json`, `facts.md`, `writes.json`, `docs/`); `termination` says no host ran and the engine is active at `test-author`. Whether the export is useful for such a run is the Run Review session's call; the optional `process.status: stopped` is a new free-text value no consumer enumerates (grepped in `test/shiploop_e2e` and `skills/shiploop-run-review`).
3. [M] A stopped or deadline-ended segment must not become a baseline. The existing `hang` fake with `--timeout 3` appended a row with process status `timeout` and engine status `unknown`, which `scan_baseline` then offers as the last comparable row. Now no row is written for a run whose engine is still active when the harness ends (a deadline, a stop, a spent resume budget). Three existing tests that read a row written for an active run were changed to expect none (the Codex resume of a stopped Grok run, the spent-budget termination record and the blocked-run regrade). **Corrected the same day after review:** that first form covered only an active engine, so the audit's own reproduction (`hang`, `--timeout 3`, engine unknown) still appended its row, and a stop before any engine state did too. The rule now also covers a host the harness killed (process status `timeout` or `stopped`) whatever the engine says; a host that ends on its own with no engine state keeps its row (its own ending is what the row records). Tested through `run.main` with the existing `hang` fake and `--timeout 3`, and with `hang` plus the stop file.
4. **A requested stop never exits 0** (`run_suite` reads 0 as PASS for gate and case rows, and any process can create the file inside a suite case's output directory); the printed header says `STOPPED`, and no `mismatch.md` is written for it. The process verdict of a stopped host is none, not failed. **Corrected after review:** only a killed host read as `stopped` in `result.json`; a stop found as a session ended on its own (`stuck-stop`) or between sessions left `process.status: exited`, `pass: true` and `termination.process_status: exited` under a `STOPPED` header. Now a stop reads as `stopped` with no verdict however it is found, the session keeps its own status in `process.sessions`, and a stop during a resumed session is tested too.
5. The printed `resume:` line is exact: `invocation.json` records the host's argv but not `--timeout`, `--max-resumes`, `--max-budget-usd` or `--permission-mode`, so a resume typed from the old text would run with the default `--timeout` of 10800 s, above any task limit, and be killed with no records. The line carries them, parses with the harness's own parser (tested, each flag non-default so dropping one fails), and prints before any host spend and again when the run is left active with ShipLoop state. **Corrected after review:** the end line was also printed by `--grade-only`, where the flags are the grader's (default `--timeout` 10800 s) and not the run's, reproducing the hazard it exists to prevent; a regrade now prints a pointer to the command printed at the start, and a run with no ShipLoop state (which `--resume-run` refuses) prints the start line only.
6. **Superseded, 2026-10-08:** the README's "a background task is killed after 18-30 minutes". The limit is the timeout the launching task was given. Dated observations: 10 minutes (2026-10-03, the 600000 ms tool maximum), 1798 s (2026-10-03, a 30-minute kill) and 120.3 minutes (2026-10-05); the Luna xhigh run's relaunch gaps were 7208, 7208 and 7211 s. The README now says to pass `--timeout` below whatever the launcher gave, and that the deadline starts after preflight and install while finalization still runs the product checks (180 s each, again for an unreturned worktree) and the export. Not measured: how far below the task limit `--timeout` must be (finalization time at a real deadline is unmeasured).

**Callback typos, R1 of the 2026-10-04 decision** (`docs/shiploop-callback-typos-plan-2026-10-04.md`). R1 was "a path typo in any run other than v1161-battleship-luna". `v1210-battleship-luna-xhigh` has three, all in the first `next --run-dir` of a fresh resumed session, with exact resume prompts (evidence file, `luna_xhigh_first_next_of_fresh_sessions`): a duplicated `20261005/` segment, a dropped `v`, an inserted `./`; the fourth resumed session's was exact, and Grok's two resumes in `v1230-battleship-grok-none` were exact. Each was repaired by the next call (about 10 s; the third ran by luck), so R2 (a typo not repaired, or a run blocked by one) is not met. Two readings of the earlier decision change: the typos come in fresh sessions, not old ones, which contradicts "session age" as the leading cause; and Item C as scoped (drop the derivable `--result`, `--opening` and `--message` flags) leaves `--run-dir` typed, so it would not remove these. R1 therefore fired and is recorded, not reinterpreted; reopening Item C is the owner's decision, and what it would buy is unproven. Re-orientation after a kill is not an address problem: the first `next` ran 8 to 18 s after the resume in 6 of 6 resumes, and the 948 to 1868 s to the first `complete` in the Luna sessions is replay of 22 to 34 minute Improve passes (ledger figures cited, not re-derived).

**Known limits, not guarded:** `--grade-only` against a live host records a mid-run snapshot and replaces `result.json` (stop the host first; the README says so); `<output>/stop` is polled every 2 s, so a stage that finishes inside a tick can overshoot by a stage (a stage-named `--stop-at` and its overshoot field are deferred); a Codex run still cannot resume across a release (a0925b33); a stop requested while an Improve child or a native chain worker is in flight leaves the state the engine's kill-at-any-point design already handles (the `--interrupt-at` tests) but has no stop-specific test.

**Not built, and why** (audit): `--stop-at STAGE` (the pending plan's RC2/RC3; trigger "planning probes become routine" not met, an external watcher that creates the stop file covers it), a SIGTERM handler (the signal the task runner sends is unknown, U2), passing the old session id on a Grok or Codex resume (U5/RC5-2, owner's go), the Codex `marketplace add --ref` pin (U1, investigation only).

Verification: `test/shiploop-e2e.test.py` 269 tests OK (247 before). Fail-first: the new test file run in a tree with `test/shiploop_e2e` from 8a198cdd failed 21 of the 24 new tests (`ClaudeResumePromptTest` 3 of 3, `ResumeCliThroughMainTest` 4 of 5, `RunCliTest` 2 of 2, `StopFileTest` 4 of 4, `GradeOnlyTest` 3 of 3, `ResumeCommandTest` 3 of 3, `UnfinishedRunBaselineTest` 2 of 4). The 3 that pass on the base are guards that must stay true: a regrade never needs the CLI, a finished run still writes its row, a run with no engine state still writes its row. The deadline test is a characterization of the README's recipe (the existing `hang` path finalizes) and fails on the base only through its baseline-row assertion.

### Display hold for host runs — 2026-10-08 — status: mitigation built (hermetic tests); the cause of the Grok `about:blank` of 2026-10-07 is unproven (SUPERSEDED 2026-10-09: display sleep is not the explanation; see 'Correction of 2026-10-09')

What is verified here: `pmset -g log` on this machine shows the display OFF from 2026-10-07 06:04:23 to 10:10:57 (-0700; a 13 s wake at 10:10:57), which covers the whole window in which the Grok run `v1230-battleship-grok-none` could not load a page in headless Chrome (09:25 to 10:12), and ON from 2026-10-06 17:40:51 to 18:20:15, which covers the launches of the 2026-10-06 Grok run (`v1220-battleship-grok-medium-none`, 17:47 to 17:59) that loaded it (TC-4 and TC-15 passed). `kern.boottime` is 2026-10-06 07:18, so no reboot lies between. The log rolls over, so these times are copied here. [M]

Reported by the batch audit and not re-run here [A]: `CVDisplayLinkCreateWithCGDisplay failed -6670` appears on passing launches too (7 lines) and on hanging ones (14 to 15), so it is not diagnostic; from a Claude Desktop child shell 7 of 9 `--dump-dom` launches (data: and loopback URLs, new and old headless) hit a 25 s timeout today, one passing in 0.5 s and the next hanging, so headless Chrome is flaky from a bare shell with no model, harness or Grok involved; a display woken with `caffeinate -u -d` still hung once. Display-off is therefore a correlated, unproven candidate, neither the cause nor ruled out.

What changed: every host session now runs under `caffeinate -d -i` on macOS (`run.keep_awake`; `-i` was already held; elsewhere nothing is wrapped), tested through `run.launch` with a recording `caffeinate` first on PATH (`KeepAwakeTest`, 4 tests, 4 fail on the previous code). That removes the variable for the runs the harness launches; it does not make a model's browser check pass.

Not done, and why: the audit's three-cell probe (Terminal, Desktop task, fresh Grok session) was not run. As written it cannot run on macOS (`timeout` and `gtimeout` are not installed, so the first command exits 127; use a Python subprocess timeout), one launch per cell cannot discriminate (the same command passed and then hung a second later; use at least 5 launches per cell and compare pass rates), and its decision table lacks the row "cell A also fails" (the failure then reproduces without Grok, the harness or a model, so it is machine or Chrome state). Have the probe print the display state and `pmset -g assertions`. Until it runs, a Grok battleship run that reaches a browser check on this machine can block there again; a one-shot page-load probe in test-strategy would pass about one time in five on a flaky Chrome and still miss it.

## The planning block of metrics.json — 2026-10-08 — status: firm for the reproduced figures (six recorded runs recomputed, three extracts under `docs/experiments/planning-measures-20261008/` replayed by tests); the block has not been seen in a live run yet

Source: the MEASURES item of the batch 1008 plan, its design and two-agent audit (`docs/experiments/batch-1008-design-audit-20261008/design-audit.json` on the batch branch). Anchor: the owner's 30-minute planning rule (SPEC S-10 carve-out, 2026-10-05) and S-12; the SPEC amendment is db51a260. Harness only.

**Why.** The planning window has been stated with different definitions: 72.7 against 72.0 and 71.88 minutes, 42.4 against 45.9 and 45.82 in Improve children, and the engine's clock against the host's (20.5 against 22.05, 374.95 against 375.93). One function now labels both clocks, and the Improve share is a field of the run, so the next planning run is read off `metrics.json` instead of an 11-agent ledger.

**Reproduced from the recorded folders** (`metrics.collect` on the real runs, 2026-10-08; minutes unless noted) [M]:

| Run | Window engine / host | Improve (children) | Other | Output tokens (reasoning) |
|---|---|---|---|---|
| Luna xhigh 1.21.0 | 374.95 / 375.93 | 203.35 (5) | 171.6 | 1,153,899 (59.2%) |
| Grok medium 1.21.0 | 71.88 / 72.59 | 45.82 (5) | 26.06 | 274,906 (38.7%) |
| Grok `none` 1.22.0 | 20.50 / 22.05 | 0 (0) | 20.50 | 86,986 (43.4%) |
| Grok `none` 1.23.0 | 18.68 / 19.23 | 0 (0) | 18.68 | 89,994 (43.7%) |
| Sonnet 1.22.0 | 7.32 / 7.40 | 4.04 (5) | 3.28 | not measured |
| Sonnet 1.23.0 | 6.47 / 6.57 | 2.57 (5) | 3.90 | not measured |

Luna's per-stage Improve shares are spec 44.49, test-strategy 61.06, plan 56.92, step-plan 26.70, test-spec 14.17. The engine started 92.8 s (Grok `none` 1.22.0) and 58.9 s (Luna) after the host's first event; that is `before_engine_seconds`, and it is why the two clocks differ. A window that spans host kills (Luna had three resumes inside its 375.9-minute window, at 120.3, 240.5 and 360.6 minutes after the host's first event, and a fourth at 480.8 in the 588-minute run) is wall clock and includes the gaps.

**Token figures are only where the host's per-call counts are exact** [M]. Grok: the usage events of a whole run sum to the `end` events' totals exactly (306,979 output and 114,518 reasoning on the 1.22.0 run, one `end`; 350,555 and 149,416 on 1.23.0, three). Codex: the per-record `output_tokens` of each of the 5 rollout threads equals that thread's last cumulative `thread_token_usage` (376,313 / 355,372 / 374,677 / 378,081 / 323,237), over 1,135 records with no repeated `response_id`, **only when the 18 compaction requests are counted**; the earlier reader (`rollouts._read`'s `calls`) drops them, and for the window that is 1,116,758 against 1,153,899 output tokens (the 10 requests carry 37,141, no reasoning). The window is the host's clock (`clock: host`): on the engine's clock Luna is 1,151,219 and Grok `none` 85,215 / 36,787 [A]. Claude's per-message counts are streaming snapshots, so its figure stays unmeasured. This re-adds an output-token figure for the window only; the earlier removal of a whole-run `tokens.output_total` and per-stage `output_tokens` (nothing read them) stands, and the readers of this one are `summary_lines`, `progress.py` and the owner's reading of the 30-minute rule.

**Rules from the audit that are in the code and tested:** an Improve child's seconds run from its bind file to the accept stamp; stamps are truncated to whole seconds and the bind time is fractional, so an accept up to one second before the bind is 0.0 and a larger negative is unmeasured (never a negative in `producer_seconds`); an action with no entry in `improve_results` is a measured 0.0 (a `none` run), a child with no readable bind file is unknown; a recreated `timeline.json` (every action one stamp), a missing start, a seeded run (stages accepted before the host's first event) and a window whose end stamp is unreadable are unmeasured as a whole; an open window reports `through` and is never 0; a `revise` test-spec does not close the window. All reasons live inside the block; the top-level `unmeasured` map is untouched.

**Not built, and why.** (1) `shape` (items, steps, dependency layers, paths, criteria per work item). The Run Review exporter already records steps planned and executed per item (S-12), and the audit found the owner's meaning of "substantial independently executable steps" unresolved: on Grok `none` 1.23.0 the Backchain check files report 17 steps in groups of 2/2/4/9, while the delivered plan is two items of one step each, so a step-plan count alone would hide the signal the question needs. Asked of the owner, not guessed. (2) A status-block or context-index row for the planning clock: `status_block(state)` is pinned equal to `status.md` by the navigator contract test, `status.md` is rewritten only on transitions, and the hook's compact output never prints it. The live record-only clock is `progress.py`'s once-only line when the window closes. (3) Per-stage tokens (nothing apportions a total to a stage). Known limits: Improve seconds read file times, so a run folder copied without them (or regraded from a copy) reads wrong; the third stage-minute implementation (the exporter's bind to receipt, the harness's stage rows) stays until the Run Review session reads this block; a Codex window with sub-agent requests is covered by a synthetic fixture only (the 1.21.0 window has none).

**Side finding, not fixed (its own item).** `metrics.collect` counts every Grok `available_commands` event as a session start, so `unreported_sessions` is 471 on the Grok `none` 1.22.0 run (472 events, 1 `end`) and 511 on 1.23.0 (514, 3), and the printed cost says "lower bound: 471 session(s) never reported" although the cost equals the host's end totals [M, recomputed 2026-10-08]. The planning block deliberately does not use `starts`. [superseded 2026-10-09: the count is now null for Grok with the reason in `unmeasured` and the lower-bound marking stays without a number; see the entry "Run identity and the baseline report"]

Verification: `test/shiploop-e2e.test.py` over `PlanningClockTest`, `PlanningImproveSplitTest`, `PlanningTokensTest`, `PlanningPlumbingTest` and `RecordedRunReproductionTest`, all fail on the previous harness (no `planning` key) and pass here.

## The narrative's Pace row records and no longer forecasts — 2026-10-08 — status: firm for the forecast errors (recomputed from the packets of five recorded runs, `docs/experiments/planning-measures-20261008/pace-forecast.json`, rerun with `pace_forecast.py`); whether removing the number changes any model or user behaviour is unmeasured

What it was: ShipLoop 0.55.0 and earlier printed "N steps in X min · about Y min left in <scope> at this run's pace (an estimate, not a promise)", Y being the observed average per step times the steps left in the phase (preparation, the work items, release). The packet carries it at every milestone, so the model sees it and shows it to the user.

What the recorded runs say [M, forecast read from the Pace rows in `run/packets/*.md`, actual from `timeline.json`, minutes]:

| Run | Preparation, first forecast (after step 2): forecast vs actual | Larger-scope examples |
|---|---|---|
| Grok medium 1.21.0 | 8 vs 54.5 (6.8x short) | work-item scope not finished |
| Grok `none` 1.22.0 | 6 vs 14.7 (2.4x) | work items 88 vs 44.4 (2.0x over), release 13 vs 30.2 (2.3x short) |
| Sonnet 1.22.0 | 1 vs 5.6 (5.6x) | work items 15 vs 8.3 |
| Grok `none` 1.23.0 | 6 vs 14.4 (2.4x) | work items 24 vs 48 and 5 vs 13.1 at later steps |
| Sonnet 1.23.0 | 1 vs 4.4 (4.4x) | work items 12 vs 10.6, 5 vs 5.1 (close), release 5 vs 4.5 (close) |

Preparation is the worst case (its stages differ in size: 0.78 to 9.55 min on Grok `none` 1.23.0, 2.45 to 121 on Luna xhigh, `stages` rows of the planning block) and the last preparation packet over-forecasts (3 vs 0.8). The earlier design note that the work-item and release forecasts "were within roughly 30%" holds for Sonnet 1.23.0 only and is **superseded** by this table: the audit of 2026-10-08 found them 40 to 62% short (Grok `none` 1.23.0) and 2 times over (Grok `none` 1.22.0).

Decision, 2026-10-08, built as its own commit so it can be dropped alone: all three scopes record and none forecasts. Why not preparation only: choosing where a forecast is "wrong enough" needs a threshold nobody has calibrated, and the formula (average of unequal steps times steps left) has the same flaw in every scope. SPEC S-15 asks for "the observed pace", not a forecast. The `remaining` computation and the formatter branch are deleted, not zeroed. The status block, the hook's compact text and `status.md` never carried Pace, so they are unchanged. Not measured: whether the model or a user acts differently without the number (low prior: the row stays); a paired probe is the only way to know. S-6 holds: the row still tells a model holding only this packet where the run stands, and nothing that states a stage's purpose, operation, check, product or recovery moved.

Version skew in the evidence script: it splits scopes with this checkout's `navigator.graph`, so a 1.21.0 history's `select-work` rows (renamed `get-next-work-item`) fall outside every group; the scope ends it reads (`prepare`, the last inner stage, the final accept) are unaffected.

## The Sonnet cost rise, decomposed — 2026-10-08 — status: firm for the arithmetic (rebuilt from the committed export by a test), interim for the cause (one run on each side)

Supersedes "(3) The Sonnet cost rise is unexplained" of the 2026-10-07 entry above. Source: the INVEST item of the batch 1008 plan and its two-agent audit. Evidence: `docs/experiments/batch-1007-live-20261007/cost-decomposition.json`, written by `cost_decomposition.py` from the two run folders and checked by `SonnetCostDecompositionTest` (`recomputed` equals `decompose(inputs)` on the committed inputs). The 2026-10-06 run (`v1220-battleship-sonnet`, 238 turns, $6.54) and the 2026-10-07 run (`v1230-battleship-sonnet`, 294 turns, $9.65) ran the same prompt.

**What is firm [M].**

- Rates of $2 input, $4 cache write (1 h), $0.20 cache read and $10 output per million tokens reproduce both sessions' `total_cost_usd` from the host's own `usage` (6.5405192 and 9.6542784, error 0). This is a fit, not a published price. Cache reads are 70.3% of the first run's cost and 73.7% of the second's.
- The rise is $3.114: cache read +$2.519, cache write +$0.264, output +$0.331. Model calls (unique assistant message ids) went 133 to 167 (the harness's `turns`, 238 to 294, counts content-block events); mean context per call 174,758 to 214,989 tokens, peak 258,602 to 324,726; cache-read tokens 23,005,566 to 35,599,892.
- The rise is quadratic in the work. Each run is one session that is never cleared, so every token added is read again by every later call. Priced at equal length, the first 133 calls of the new run read 25,230,430 cache-read tokens (+9.7%); its 34 extra calls (context 286k to 325k) read 10,369,462, which is 82.3% of the 12,594,326-token increase.
- The two runs are not a controlled pair. The Claude Code build differs (2.1.291 against 2.1.292, read from the init events; no record of the harness named it before, and `claude_code_version` is now recorded in `metrics.json`), and both carry `plugin_version` 1.22.0 and `shiploop_version` 0.54.0 although their code differs (`local_head` 81e0502f against bc1d6452), so "same build" cannot be read from the version string.

**What the audit derived and this repository does not recompute [A]** (labelled `from_the_audit` in the export; input side of each call only, fitted rates). The engine text added between the two builds (the `Checked by:` line, 7,514 bytes over 45 packets; three duty additions, 660 bytes) can explain at most about 2% of the rise, about $0.051 plus $0.007 if every added byte stayed in context for every later call: a bound on bytes. Where the rise fell, by growth priced per later re-read: spec +$0.84 to +$0.86 (4 Improve review passes against 3, a Skill load of improve), plan +$0.32, static-checks +$0.16 to +$0.18 (3 quality-loop iterations against 2), implement +$0.11 to +$0.12; nine stages that took one call each in the old run took 17 calls in the new one. The new product is larger (26,030 to 34,983 bytes outside docs, +34%; model-authored tool-input bytes +39%), and the old run was not a clean baseline (46 accepted rows including one revise for the uncounted `node --test` refusal, against 38 rows and none).

**What it supports and what it does not.** It supports: the packet text is not where the money went (bytes, at most about 2%), and the rise is the model making more calls in a longer context. It does not support: "the model's own work" as a cause (that is nearly a tautology, since every cost is the model's work), or the absence of a behavioural effect of the new text. The `Checked by:` line reached the model in 28 tool results and was never quoted in a tool input or assistant text, which is no proof it changed nothing. Two host variables are uncontrolled (the CLI build; the work-item decomposition, 3 implement steps in the old first pass and 5 in the new run). Settle it only by repeated runs on one build (3 per host), and by a 3-against-3 with `_checked_line` empty if a later rise exceeds the same-build spread. No engine change is proposed.

**Design tension, not a defect (owner decision).** `packet_head` tells the model to Read the full packet with a file tool, and packet files run 30 to 58 KB. The costliest growth events in both runs are such reads (intake packet, the improve Skill, the improve packet). If every packet were read in full at its stage start, the carry cost would be about $8 to $9 a run (a computation from measured sizes at 2.58 bytes per token, not a measurement); the runs stay cheap because the model mostly reads windows with the shell. Do not trim that instruction as a cost lever without checking that every packet still restates its purpose, operation, check, product and recovery (the main tenet).

## Round 1 of the bounded improvement loop: ShipLoop 1.24.0 on Battleship (Sonnet checks on, Grok checks off) and Checkers (Sonnet checks on) — 2026-10-08 — status: firm for the run records; interim for conclusions (n=1 per cell)

**Purpose and rule (owner, 2026-10-08).** The sample apps exemplify the ShipLoop SDLC; every finding is judged by fidelity to the stages, SPEC and main tenet and by generality, never by what makes the sample pass. Bounded loop: at most 3 rounds, halt on regression, the same error 3 times, or 3 rounds without progress. Evidence: `docs/experiments/round1-20261008/evidence.json`; the analysis (four lenses per run, then a synthesis) is `docs/experiments/batch-1009-round1-analysis-20261008/`.

**Results.** Sonnet Battleship PASS in 13.8 min, 207 turns, $5.70 (batch 1007 build: 20 min, 294 turns, $9.65). Sonnet Checkers PASS in 13.1 min, 185 turns, $5.16 (first run of this case, no baseline). Grok Battleship, checks off: stopped blocked at `system-test-author` after 76 min, 301 turns, $8.75 (a lower bound), 4 compactions; planning (checks off) 23.3 min engine clock. The batch-2 changes were visible live: `skill_na` recorded in one of the two Sonnet runs so both skill stages cost 0 s; release-verify ran in a clean export of the returned result (`observed.where = returned-result`, tree equals the delivered repo's tree); an Improve child's packet sits in its own `-improve.md`; the display was held awake with `caffeinate -d -i` for every host.

**The Grok block is the case end-state rule working.** At `system-test-author` the model ran the HTTP-level check (it passed), tried Chrome for the browser case for 21 minutes and 71 turns, and then declined to record the case as passed: `blocked_by access` with a question offering "accept the HTTP check and leave the browser interactions unverified" or "wait for a browser", naming what stays unobserved (Enter key, 320px scroll, reduced motion, in-flight second click, on-screen error text; requirements R3, R11, R14). **Correction of the earlier hypothesis:** the 2026-10-07 entry tied the Chrome `about:blank` failure to the display being off (pmset showed it off for the whole window). In this run the display was held on and headless Chrome still did not finish loading the page (`--dump-dom` also did not return), so display sleep is not sufficient as the cause; the cause in the Grok host stays unproven. **The probe still did not prove the capability:** at test-strategy the model "probed" with `curl` to a server that did not yet exist (connection refused), concluded "no browser MCP", and never checked whether Chrome could load a page, so the access gap surfaced 40 minutes later and cost 21 minutes of Chrome flag iteration. The wording asked for last round was followed to the letter and missed the point; the fix (probe a stand-in page, because the product does not exist at test-strategy time) is in the next batch.

**CI lesson.** The 1.24.0 release commit failed `full / shiploop-2` in CI: five errors in `ReleaseVerifyReturnedResultTests` because the CI runner's global Git config carries git-lfs filters, which the workspace refuses; the tests passed on this machine, in the implementers' reruns and in the reviewers' reruns because none of them used a CI-like global Git config. Fixed in `abc47622` (the test isolates `GIT_CONFIG_*`; reproduced first with a config defining the lfs filter). **Rule for new real-git tests: isolate Git config.** Every release should be followed by a CI check before it is described as done; the quick-tier CI of the fix commit passed but the full tier of the release commit was not rerun.

**What the analysis found (the next batch).** Faithful strengths: script-owned evidence held in both Sonnet runs (10 verification records, 29 commands, counted, no skips), release-verify observed the returned result, loops found real defects, honest limits were disclosed. Candidates implemented in the next batch: the return review is a hand edit of a script-owned file; rollback text written before the return kind is known; step-plan "Confirm by" contract disagreements; unverified outcomes and open assumptions have no structured home; Improve packets do not restate the goal and done-when; knowledge-close demands files the packet does not list; `improve-bind` prints a placeholder path; the Backchain child's required status is ambiguous; `run/notes/` is never created; the harness cannot read Claude-host tool calls. Held for a second run: release-check discrimination, implement/baseline script runs, min_tests ratchet, plan-document location, document-stage paths, `skill_na` template visibility (1 of 2 uptake).

## The Claude tool-block reading: failures, glue, /tmp writes, per-stage context and the scripts the model ran — 2026-10-08 — status: firm for the figures (recomputed over the 15 recorded Claude runs and the two round-1 runs, regraded in scratch copies); not yet seen on a Claude Code build after 2.1.294

The harness was blind for Claude for one reason: `metrics.collect` read only Grok's event shape (item 7 of "Callback path typos across
the 1003 batch"; M1 of `docs/shiploop-callback-typos-plan-2026-10-04.md`). It now reads Claude's `tool_use` and `tool_result` blocks
through the one classifier Grok's `tool_call` events use (`metrics.ToolLog`), and the round-1 lenses no longer need to mine
`events.jsonl` by hand. Journal and the audit's corrections: `docs/shiploop-batch-1009h-journal-2026-10-08.md`; recorded calls:
`docs/experiments/claude-tool-blocks-20261008/`.

- **A refusal is recognised by its own line, not by an exit code.** The model pipes the CLI through `head`, `grep` or `sed`, so all 5
  refusals of the round-1 Sonnet Battleship run have no exit at all. Over 15 recorded Claude runs: 72 results with a refusal line at
  a line start, all genuine ShipLoop output (a command guard on top would have dropped 9 of them, a real knowledge-file refusal
  among them), plus 10 exit-only failures (7 `Exit code 127` of a bare `shiploop`). `ShipLoop workspace blocked:` is a third prefix.
- **Grok's exit 0 is not a hidden refusal.** The audit read 5 anchored lines at exit 0 in three Grok runs as hidden refusals; they are
  `in_progress` updates (a placeholder exit 0) of calls whose `completed` update carries exit 2. The classifier reads Grok's completed
  update only; the old and new lists agree on four recorded Grok runs except v1220 (+1, a compound command whose `$CLI workspace`
  verb shows once variables are expanded).
- **Shell variables are expanded per command**, and an assignment still unresolved (`R=$?`, quoted inside a `sh -c`) is not recorded.
- **Glue is a lower bound for Claude.** 14 of 15 recorded runs wrote and ran helper scripts that wrap the CLI (r1 Battleship: sub.sh 30
  runs, istart.sh 7; idone.py, 17 runs, wraps the Until Loop's done command and not the CLI);
  `tool_use.scratch_scripts` lists them beside `model_glue`, which keeps its definition.
- **A failure is counted once per call, not once per id.** Codex numbers its calls again in every session (the recorded Luna run v1210:
  1,542 `tool_call` events, 486 distinct ids, 337 of them used more than once), and the first version of the shared classifier kept the ids it had counted,
  so a later failure that reused one was dropped silently. The review found it with a synthetic pair and a recorded run (9 against 10
  failures on v1210); the compatibility check that said "old and new lists agree" had compared four Grok runs only. Checking a change
  to a shared classifier means every host that has a recorded run, not the one that motivated it. Codex differences against 847fa64e:
  v1161 Luna records the refusal line instead of `AssertionError` (the model's own failing assert printed just before it), v1210 Luna
  gains one refusal whose command names no verb.
- **`shiploop_failures` is heuristic, glue and script runs are lower bounds.** A compound command's exit is attributed to the ShipLoop call
  in it (v1220 Grok +1), so the failure count can be high as well as low.
- **Packets, printed versus read (r1 Battleship):** 44 packet files, 1,707,162 bytes; 44 printed replies, 37,367 characters; 4 packet
  Reads, 2 whole (28,595 and 21,636 characters); 23 shell commands on packets, 64,249 characters.
- **`passed 10` held two red records** (the test-red record and the test-author probe); `script_verifications.red` says so.
- **Stage context for Claude:** `{calls, peak, peakPct}` per stage; 119 of the 120 calls of r1 Battleship fall in a stage window.
- **Dropped, with reasons:** Claude compactions (no recorded `compact_boundary`), truncated outputs, knowledge reads, cancelled calls,
  `improve_reviews.identical` (the required pair of clean passes is not waste).
- **Known limits:** main thread only; a result saved to a file is unread; a document line that starts with a prefix would count;
  script runs are lower bounds (r1 Checkers: 29 against 30 by hand for sub.sh).

## A run leaves nothing listening, and a signalled harness leaves no orphan host (batch 1010, item A6) — 2026-10-08 — status: firm for the facts read from this machine (pid 63973, the r2 events, the Grok log, the timings); the new paths are hermetic-tested and not yet seen in a live run

Round-2 analysis candidate A6 (`round2-analysis.json`): two round-2 Sonnet runs met a stale server on port 3457 and one committed
a false lesson. SPEC amendment first, in its own commit (`4ec2a54a`): "A run leaves nothing listening", the SIGTERM and SIGHUP
sentence under "Every ending leaves its records", and "Runs compared on wall time or per-call cost run one after the other".

- **The leak, verified live.** Pid 63973 is `node .../r1-checkers-sonnet/.shiploop-runs/work-20261008-174135-41d2f7/worktree/server.js`,
  parent pid 1, process group 63956 (the host's was 57814), started 10:49:51 on 2026-10-08, cwd `.../r1-checkers-sonnet/work`, bound
  `*:3457`. r1-checkers-sonnet exited rc 0 after 787.8 s, so no kill ran: `launch()` kills only on a deadline, a stop or an
  interrupt, and Claude Code gives each Bash call its own process group, which a group kill of the host never reaches. r2-battleship
  events 362 to 363 (`PORT=3457 node server.js ... &`, then `EADDRINUSE :::3457`) and r2-checkers events 557 to 558 met it; r2-checkers
  event 562 (`... & sleep 1; ...; kill %1; wait`, job control is off so `%1` names nothing) hung to the 120 s timeout at 570, and 572 ran
  `pkill -f "node server.js"`, which does not match the leaked `node /abs/path/server.js`. The false lesson is at
  r2-checkers-sonnet `work/docs/shiploop/environment.md` line 17 and `features/*/outcome.md` line 9 (S-11). Both models chose 3457 by
  habit: neither the cases nor `skills/` name a port.
- **Census** (read-only, the design workflow): 26 case folders under `/Users/dadleet/e2e-runs`, exactly one with a listener under it
  (r1-checkers-sonnet); the other seven user listeners have cwd `/`, so "cwd or an argv path under the case folder" had no false positive
  here. Measured again at build time: 8 own listeners, `observe()` 0.115 to 0.121 s over three scans (lsof twice, ps once), `protected_pids`
  0.02 s, a detect-only `listeners.inside` of r1-checkers-sonnet finds pid 63973 on port 3457 with that cwd, and of the name
  `r1-checkers-sonne` (a bare prefix) finds nothing. Pid 63973 was not stopped on purpose (that needed the owner's go); it ended later in the mutation-run incident the reap commit describes (a test scope that called the mutated selector let the real reap signal this user's other listeners: Ollama and its server, the OrbStack engine and the leaked pid; launchd restarted the rest, and the restart of Ollama and OrbStack was not done by this work).
- **Probes of the design** (scratch, reproduced as hermetic tests): SIGTERM freed a listener's port in 0.27 s and left a `case-10` sibling
  alone when `case-1` was reaped; an exclusive `flock` holds across a second open file description in one process and across processes and
  is released when the holder is SIGKILLed; a host started with `start_new_session=True` survives a SIGTERM to the harness by default and
  dies with a handler; `subprocess.run(shell=True, timeout=1)` leaves `sleep 301 &` alive after the timeout, so a timed-out case check
  leaks too.
- **Built: reap** (this entry's first commit). `listeners.py` observes with `lsof -iTCP -sTCP:LISTEN -Fpcun`, `lsof -a -d cwd -p` and `ps -ww`,
  keeps the harness user's, matches the working directory (a real path) or any command-line word (as given and as resolved, a leading
  `--opt=` stripped) on a path boundary, never pid 1, the harness or its ancestors, and stops with SIGTERM then, after 3 s, SIGKILL, reading
  the table again before each signal. `run.launch` reaps when a session ends, `main` reaps again after the case checks and before a resumed
  session starts (an earlier invocation's harness may have been killed), and a regrade reaps nothing. The record is `left_behind` in result.json
  (`observed`, `reaped`, `survived`, or `observed: false` and the reason, the passes merged so an unseen pass never reads as none).
  Ordinary harness tests patch the observer to return nothing, so none reads this machine's table (pid 63973 would otherwise be seen).
  The classes that use the real lsof scope what it shows to their own temporary folder. A test whose lsof is absent skips with a stated reason.
- **Built: the stale-listener refusal.** A launch, `--preflight-only` and a suite (once, before its folder or any case exists) are refused
  while a listener sits under another case's output folder and that case's harness is not alive. Liveness is an exclusive `flock` on
  `<output>/.harness-lock`, taken by `main` and released when it returns; the kernel drops it on any death (reproduced: a holder
  SIGKILLed frees it), so parallel suite cases and pairs started by hand are never refused. Looking is read-only (`os.open` with
  `O_RDONLY` and a shared lock; the first design's `open(path, "a")` would have created a lock file in every old case folder it
  inspected), the run's own folder is reaped and not refused, a regrade is never refused, and a case a suite starts skips its own check
  (a `SystemExit` in a worker thread reaches the suite only after the running chains finish, with no suite-result.json). No listener
  is ever stopped by the refusal. Where lsof cannot be read a line is printed and the launch goes ahead. Measured at build time: 26 case
  folders, 0 listeners under any of them, 0 lock files (old folders have none), `stale()` 0.14 s. The leaked pid 63973 was already
  gone by then (see the incident in the reap commit), so the first launch on this check is not refused by it.
- **Decision (reversible, the owner's to take): refuse rather than warn.** The refusal has no override, so a finished case folder served
  by hand blocks every later launch until its process is stopped by pid. The smaller alternative is a printed warning plus a recorded
  `stale_listeners_at_start`, which drops the lock, `case_folder`, `stale` and about 40 lines. Refusal was kept because the round-2
  contamination was a launch that went ahead and the round-2 criterion asks for the refusal; after the reap, a stale listener arises only
  from a SIGKILLed harness or a leak from before this change.
- **Built: a signalled harness ends its hosts and writes its records.** The exit-241 defect of the r2 Grok run: `r2-grok.log` ends
  `exit 241` (-15 mod 256, a SIGTERM) 855 s in, `r2-battleship-grok-none/timeline.jsonl` stops at +854 s and restarts at +2788 s, and 139
  ledger files of `.shiploop-runs/work-20261009-002036-d50cd1` were written between 17:35:01 and 18:02:11, after the harness died at
  about 17:34:30: `launch()` starts the host with `start_new_session=True` and Python's default SIGTERM runs no code, so the host kept
  working as an orphan for about 28 minutes with no events or metrics being collected and no result.json. (The design's probe: a
  start_new_session host survives a SIGTERM to its parent by default and dies with a handler. Why the orphan stopped at 18:02 is not
  known, U5, and is not needed.) `run.py` as a program now takes over SIGTERM and SIGHUP: the handler records the signal, sets
  `TERMINATION`, kills every registered host group at once (`LIVE_HOST_GROUPS`, a copy iterated because suite worker threads add and
  discard concurrently; a group is dropped from the set as soon as its leader is reaped, so a reused pgid is never signalled), and
  restores the default action so a second signal ends the harness at once. `launch` and the resume loop read `TERMINATION` as a requested
  stop (`stopped`, no process verdict, `termination.resume_stop` `terminated by SIGTERM`, exit 1, no baseline row, no relaunch), a suite
  starts no further case, and an `atexit` kill covers a Ctrl-C or an exception (superseded for a suite on 2026-10-08: the kill came
  too late there, see the review section below). The reused route is the stop file's (`StopFileTest`).
  A SIGHUP the launch ignored stays ignored (the audit's correction: an unconditional handler would have overridden `nohup`, the README's
  stated exception for multi-hour runs). The tests run the harness as a real subprocess so the `__main__` wiring and the real signals
  are what is tested and the test process's own handlers are never touched; a fake `lsof` first on PATH gives it an empty process table.
- **Decisions and limits.** Proven for SIGTERM only; U1 (which signal a task runner sends at its time limit, and with what grace) stays
  open, to be settled by the audit's probe (a short background task whose Python child traps TERM, HUP and INT and spawns a detached
  heartbeat). A SIGKILL is uncatchable: `--grade-only` is the remedy, and a `host.pid` check that refuses a resume while an orphan host
  of a SIGKILLed harness is alive (A6-host-pid) is not built, since the only observed kill was a SIGTERM. A signal that arrives during
  the case checks lets them finish (up to 180 s each) before the records are written, and a second signal ends the harness at once.
  `iterate.py` and the review and fan-out agents (`hosts.run_agent`) are not covered by the handlers; `iterate.py` still gets the
  `atexit` kill. A mutant that dropped the early return for a session begun after the signal survived, so that code was removed: the
  poll loop ends such a session at its first poll.
- **Sequencing** (A6-sequence) is a rule and a README sentence with no code: runs compared on wall time or per-call cost run one after the
  other (`--serial` for a suite, or launch the second after the first ends). The suite default of 3 parallel chains stays for finding
  failures. A baseline row has no overlap field, so a later comparison cannot exclude an overlapped run; `timeline.jsonl` t0 is the only
  record. The r2 pair started within 0.1 s of each other (1791505216.323 and .384).
- **Dropped:** A6-sentence (a ShipLoop line about loopback ports): the contamination came from the leak, not from a missing rule, the
  scratch-directory line already sits in every packet (`shiploop_navigator._run_rules`, pinned by `test/shiploop-navigator-v4.test.py`),
  and it would need a change note and a release for an unmeasured benefit. Reopen only if a post-fix rerun still writes a port lesson
  into durable knowledge.
- **Decision (reversible): a leftover is a record, not a verdict.** `pass` is unchanged. Making it a verdict would fail a run for a
  model's habit the harness already cleaned up.
- **Open:** U2 whether `lsof` exists on the `ubuntu-latest` CI runner (the pure parse and selection tests run either way; the real-process
  classes skip with a reason if it is missing); U3 whether lsof may read the user's processes inside a Desktop background-task sandbox
  (`left_behind.observed` and `reason` will say); U4 whether the Codex or Grok host keeps a listener of its own with a cwd under the case folder
  (`left_behind.reaped` should then name it; exclude by command name rather than weaken the folder rule); U6 the leak rate (one of 26 case
  folders today and two found by hand earlier; `left_behind` measures it from now on); U7 Run Review's `facts.md` does not render
  `left_behind` yet (skills/shiploop-run-review is another session's; the exporter ignores unknown result.json keys, so nothing breaks).
  Not covered, documented in the README: non-listening leftovers, UDP and unix-socket servers, and a server with cwd and command line both
  outside the folder.

## A6 adversarial review, first round: what it found and what was fixed (batch 1010, item A6) — 2026-10-08 — status: firm for the fixes that have a test that failed first; the incident below is an environment fact

The review of `f1329599`..`b1065a15` returned `fix-needed` (2 major, 9 minor). Fixed in this order, one commit each; every fix whose
test could fail first did, and the mutants named below were applied to a scratch copy and not to the worktree.

- **A missing module took the whole test file down (major).** `test/shiploop-e2e.test.py` imported `listeners` at module level, so with
  production reverted to `b73c30ba` and `listeners.py` absent, all 398 tests died at the import (reproduced: `ModuleNotFoundError`
  at the import line). The audit had asked for the import inside the new tests. Now the import is guarded (`listeners = None` only for
  a missing `listeners` module; any other import error still raises), the seven listener classes carry `@needs_listeners` and fail one by
  one on `listeners.py does not exist`, and the older tests (`HarnessCase`, `KeepAwakeTest`) take their "no listener" patch from
  `nothing_listens()`, which patches nothing where the module is absent. Same experiment after the fix: 398 tests, 41 failures and 2
  errors, all in the new classes (36 on the guard, 5 on real assertions, 2 on `run.TERMINATION` missing), every older test green.
- **A failing signal test left orphan hosts (minor).** Only the first session's pid was killed, so a harness that relaunched its host (mutant
  "the handler does not set TERMINATION") left ppid-1 fake hosts sleeping 600 s: the defect the work fixes. One cleanup now reads every pid
  in `<FAKE_LOG>.sessions` and kills its group (only when the pid leads its own group), registered so it runs after the harness itself is
  killed. Before/after on that mutant, one test each: the old file left one ppid-1 host, the new left none.
- **Fixtures that look like a leak (minor).** The regrade test held a real server under a finished, lock-free case folder, which another
  session's real launch would have refused on, naming `kill <pid>`. It now holds the case lock, as a live host's harness would. The
  refusal test cannot hold it (it asserts the lock-free state); its case record is written last and the lock taken as soon as the
  refusal is seen, a window of one scan. `test_a_resume_stops_what_the_earlier_invocation_left_before_its_host_starts` still has such a
  window of a few seconds, because a resume must be lock-free to be allowed; accepted.
- **The incident (environment, not code; the owner's to undo).** While mutation-testing the reap, a first mutant ("every listener
  selected") ran against a test scope that called the mutated selector, so the real reap sent SIGTERM to this user's other listeners:
  Ollama (app and server) and the OrbStack engine stopped and were not restarted, the leaked pid 63973 ended, and launchd respawned the
  rest. Checked read-only after the review: no Ollama process, `orbctl status` prints `Stopped`. To restore: `open -a Ollama` and
  `orbctl start`. The scope guard (`scope_to_tmp`, `guarded_signal`) now checks by the test's own folder and refuses to signal any
  pid outside it, independent of the code under test; mutants of the selector fail on that guard and signal nothing. Mutants that widen the
  selection are not run against the real-process classes.
- **A second harness for a running case went on silently (minor).** `hold_case` returns None where another harness holds the lock, and
  `main` carried on: a second `--resume-run` of a live run would have reaped the live harness's servers, started a second host in the same
  work directory and consumed the stop request its owner had made. Now `main` refuses (`another harness is running <out>`, nothing
  started or stopped) unless the invocation is a regrade, which starts and stops nothing and may read a case that is running; and only the
  invocation that holds the lock removes a stale stop file (the removal moved from the top of the resume branch to after the lock; the
  existing `test_a_stop_never_answers_a_blocked_run` pins that a regrade still clears it when it holds the case). Red first:
  `SystemExit not raised` and the stop file gone after a regrade. Mutants killed: refuse a regrade too, never refuse, remove the stop file
  whatever the lock, never remove it (6 of 6 with the port mutants below).
- **`listeners_of` raised on a name with no colon (minor, latent).** The test and the value used different indexes
  (`rsplit(":", 1)[-1]` against `[1]`), so `n123` raised `IndexError` out of `launch()`. lsof prints `host:port` for a TCP endpoint, so this
  cannot happen in a normal run; a name that is not `host:port` now yields no port (`_port`), pinned by a test that failed first on the
  `IndexError`.
- **A Ctrl-C on a suite did not end its hosts (minor, but it falsified the documented guarantee).** The review ran `run.py --suite breadth`
  with three fake hosts and sent SIGINT: 40 s later the harness was running and all three hosts were alive, while SIGTERM on the same
  suite ended in 31 s with rc 1, the hosts gone and `suite-result.json` written. A suite runs its cases in worker threads; the
  `KeyboardInterrupt` reaches the main thread, which is inside `ThreadPoolExecutor.__exit__` waiting for them, so the `atexit` kill ran only
  after the hosts had finished. `run_suite` now catches it while waiting for a chain, calls the same `terminate(name)` the SIGTERM handler
  uses (named `SIGINT`) and waits for the chains' records, so a suite's Ctrl-C reads as a SIGTERM. Red first: the new real-subprocess test
  waited 45 s and reported `the suite kept running after a Ctrl-C`. Not done: the second-press rule (`SIG_DFL`) of SIGTERM and SIGHUP is
  not extended to SIGINT, because there is no deterministic test for it; a second Ctrl-C raises `KeyboardInterrupt` again.
- **The batch suite's gate branch was untested (minor).** The mutant "the gate ignores TERMINATION" survived the whole file because the
  signalled-suite test used a `breadth` suite, which has no gate. A `batch` suite with a gate now has its own test (gate row skipped as
  `terminated by SIGTERM`, the cases behind it `the gate failed`, no host started); the mutant is killed. Mutants of the Ctrl-C path:
  wrong name, rows dropped, `TERMINATION` not set all killed. One survived by construction (setting `TERMINATION` without the immediate
  kill still ends the host at its next poll, at most 2 s); the immediate kill sits in `terminate`, which `LiveHostTest` pins with a 30 s poll.
- **The documents said more than the code did (minor).** `run.py`'s module docstring (which is also `--help`) described the stop file and
  `--grade-only` but not the signals, `left_behind` or the two refusals; it does now, pinned by a test. The README gained the transition
  case (a harness started before the lock existed holds none, so a launch refuses its listeners as stale while it is still running:
  wait, or stop the server by pid), the second-harness refusal and the exact Ctrl-C behaviour for a suite and for a single case (the
  latter pinned: no `result.json`). SPEC: the cross-reference "the exception in the bullet after next" broke when a bullet is added, so it
  now names the bullet and a test forbids the positional form; the Ctrl-C sentence and the second-harness refusal are amended in the
  rule they belong to (the same-day refinement of the 2026-10-08 amendment, made with the code that needed it).

## Rounds 2 and 3 of the bounded improvement loop (1.25.0 and 1.26.0) — 2026-10-08/09 — status: firm for the run records; interim for conclusions (n=1 per cell)

Evidence: `docs/experiments/round2-round3-20261008/evidence.json`; analyses and the audited designs under `docs/experiments/batch-1010-round2-round3-analysis-20261008/`. Rule in force: the sample apps exemplify the SDLC; judge by fidelity and generality; bounded loop of three reruns (spent).

**Numbers.** Sonnet Battleship: round 1 13.7 min / 207 turns / $5.70, round 2 13.4 / 206 / $5.81, round 3 12.5 / 197 / $5.67 (stable). Sonnet Checkers: 12.9 / 185 / $5.16, then 20.7 / 293 / $8.51, then 14.9 / 232 / $6.65: the round-2 rise decomposes into about $0.8-1.0 of intended new validation (a real-browser closure of an open assumption, a Backchain audit, more Improve passes) plus run-to-run spread (the same build, same case, already differed 48% on Battleship in round 0) [superseded 2026-10-09: those two rows were two builds on two Claude Code builds (plugin trees 19868f9ee770 and 452b7e2eb831, local_head 81e0502f and bc1d6452, Claude Code 2.1.291 and 2.1.292), so the 48% is a difference between uncontrolled builds and says nothing about run-to-run spread on one build; see the entry "Run identity and the baseline report"], so no engine regression is claimed. Grok checks-off Battleship: round 1 blocked at system-test-author (76 min), round 2 ShipLoop done and 4 of 4 product checks (52 accepted; planning 15.7 min), round 3 stopped by the loop's same-error rule after 35 minutes of Chrome debugging inside implement.

**What the batches did, live.** Batch 3 (1.25.0): 11 of 13 changes confirmed working in both Sonnet runs (no hand edit of `return-plan.md`, a one-call `review-return`, the route and rollback statement in every packet, `run/notes/` created, the step-plan contract, the installed Improve card at bind, the gated `unverified` list, Improve packets restating goal and done-when, the Claude tool-call metrics); F1 not exercised; the stand-in browser probe in the duty body not working (never read). Batch 4 (1.26.0): the per-item test-count ratchet computed silently (no false refusal, no count ever dropped), the Improve child directory is created where it is named, the listener reaper ended two leaked servers, the SIGTERM handler worked live; the whole-word id refusal, the ratchet's refusal and the launch preflight never fired (unproven live, not broken). The probe moved into the test-strategy Done-when worked: Checkers and Grok probed Chrome against a stand-in page and cited the output; Battleship Sonnet classified its page as needing no browser and probed nothing.

**Corrections to earlier claims.** (1) The SIGTERM that killed the round-2 and round-3 Grok harnesses was a model's `pkill -f "node server.js"` in a concurrent Checkers run, which matched the Grok harness's argv (it embeds every check command); the round-3 harness handled it as designed, the cause was my launching Grok concurrently with Checkers against the sequencing rule I had just written. (2) The display-asleep explanation of the Chrome failure is withdrawn: with the display held awake Chrome hung in round 1, worked in round 2 and hung in round 3, and a file: stand-in loads while the real page over http://127.0.0.1 does not, so the open question is Chrome-over-loopback inside the Grok host, not the display. (3) A resumed run's printed continue command omitted `--plugin-dir` for a checkout build, so run as printed it would have tested the published plugin rather than the run's own build.

**Incidents.** (a) CI: the 1.24.0 release commit failed one shard because the runner's global Git config carries git-lfs filters (fixed, reproduced first); the 1.25.0 and 1.26.0 release CI ran green to the end. (b) A defect in my own earlier harness change: `per_stage` crashed on turn rows without a `call` key after a resumed Grok run, losing its metrics until fixed (b73c30ba). (c) **Process safety:** while mutation-testing the new listener reaper, an implementer's run sent SIGTERM to the user's other listeners and stopped Ollama and the OrbStack engine on this machine; they were still stopped when the loop ended and need the owner to restart them. Rule: code that signals processes is mutation-tested only against processes the test itself started, never against the machine's real listeners; the reaper's production selection is by working directory under a case folder.

**Candidates left (generic, small), from the round-3 analysis:** R3-1 the integrate row and its "not committed" notice tell the model to hand-commit what `plan-return` commits (Battleship hand-committed twice); R3-2 the rollback in release-plan.md is not the printed recipe in 3 of 4 runs (make it a head-visible Done-when line); R3-3 no rule on process and port lifecycle (stop only the pid you started, never a name pattern); R3-4 release-check's "ran once and recorded its not-there-yet output" is answered by a sentence (a shape gate); R3-5 the `host_dependent` guard text cannot work on a browser-script check row; and the transport-faithful probe (serve the stand-in over HTTP on loopback). Held for another run: the producer classifying the browser case away, baseline commands not script-recorded. Known limits: oracle strength and RED-for-the-right-reason are model-judged (S-9); Improve is a confirmatory ceremony (S-10); status lines in the knowledge home are not refreshed.

## Correction of 2026-10-09: round 2's Grok run was finished by Claude, and Chrome fails in the Grok host, not at random — status: firm (invocation records, tool names, init events)

**What was wrong.** The round-2 Grok checks-off Battleship result recorded above as "ShipLoop done, 52 accepted, 4 of 4 checks, planning 15.7 min, the browser case worked this time" is a MIXED-HOST run. The Grok host was orphaned by the SIGTERM (a concurrent Checkers model's `pkill -f "node server.js"`) and ran on, unsupervised, from accepted visit 9 to 31; when it exited I resumed the run with `--resume-run <out> --plugin-dir <build>` and without `--host grok`, and the harness defaulted to **Claude Sonnet 5.5**, which did visits 31 to 52, including the system-test-author browser check, the product-acceptance walk and the handoff. Evidence: `invocation-resume-claude-1791508003.json` (host claude, model claude-sonnet-5-5) beside `invocation-resume-grok-1791509021.json`; the resume log's tool names are Claude's (`Bash`), not Grok's (`run_terminal_command`); events.jsonl holds a Claude init event; the Run Review session's audit found the same (Grok to visit 9, a 32-minute orphan gap, then Claude). Its metrics.json mixes the first Grok session with the Claude resume and has nothing for the orphan gap. So r2 is not a Grok datapoint after visit 31 (and its cost, turns and planning window are not a Grok measurement).

**Consequences.** (1) "Chrome worked in the Grok host in round 2" is false: Chrome worked in the Claude host. Across the Grok runs since 2026-10-07 where Chrome was tried (v1230, round 1, round 3) it failed to load the real page over `http://127.0.0.1` every time (a `file:` stand-in loads), while in the 2026-10-06 Grok run (v1220) it worked, and in every Claude run it worked. That is host-specific since 10-07, not "flaky", and not the display (held awake in round 1 and 3 and still hung). The cause inside the Grok host is unproven; Chrome version drift between 10-06 and 10-07 and the Grok host's network sandbox are the open candidates. (2) The "hung, worked, hung" pattern stated in the rounds 2 and 3 entry is withdrawn. (3) The loop-state memory note and the evidence file are corrected. **Harness defect behind it (mine):** `--resume-run` takes host, model and effort from the command line, defaulting to Claude, instead of from the run's own `invocation.json`; the printed resume command carries `--host grok` explicitly, which I omitted by hand. Fix queued in the harness batch: default them from the recorded invocation and refuse a silent host change.

## Run identity and the baseline report — 2026-10-09 — status: firm for the recomputed figures (22 saved folders and the 23 committed rows, replayed by tests from `docs/experiments/baseline-spread-20261009/runs.json`); interim for what a spread is worth until a cell holds three runs of one build

Batch 1011, group G3 (the F3 design, adversarially audited; scope is the audit's safer alternative). SPEC amendment `7604de03`, identity `90de0f13`, one matching rule `c5b95321`, the Grok session count `073fd4dd`, the report `a10b34d1`. Harness only: no skill is touched.

**Four ways the single-last-row comparison misread the loop's runs [M, all recomputed from the saved folders].**
1. *A version string is not a build.* v1220-battleship-sonnet (238 turns, $6.54) and v1230-battleship-sonnet (294, $9.65) both record plugin 1.22.0 / ShipLoop 0.54.0; their built plugin trees differ (digests 19868f9ee770 and 452b7e2eb831), as do `local_head` (81e0502f, bc1d6452) and Claude Code (2.1.291, 2.1.292). Conversely HEAD over-splits: r1-battleship-sonnet (587cd90d), r1-checkers-sonnet (5e209285) and r1-battleship-grok-none are one tree (3a7515d2efd3). A row now carries `plugin_sha256` (a digest of file paths and bytes, leaving out `__pycache__`, `*.pyc` and symlinks, taken at launch), so "same build" is a fact about bytes. The design's own digest values (142047ca62ed) came from another algorithm and are not reproduced; the equivalence classes agree.
2. *A blocked run was a basis.* r1-battleship-grok-none was itself blocked (301 turns) and printed `turns 503 -> 301, cost $14.1673 -> $8.7455` against baselines.jsonl row 20 (the 2026-10-07 Grok run, blocked at system-test, `verdicts.shiploop` false). One rule now (`run.matching_rows`) serves `scan_baseline`, `previous_row` and the live line: a row whose ShipLoop did not reach done is a record and never a basis, and a run that did not itself reach done prints `nothing compared: this run did not reach done`.
3. *Rows were lost.* The committed file holds 3 of the loop's 7 finished rows (r1 Checkers, r3 Battleship, r3 Checkers); r1 Battleship and r1 Grok were only in worktree b1008a's file, r2 Battleship and r2 Checkers only in b1009i's, so r2 and r3 were compared with older rows. `--baseline-report` unions the file with the folders.
4. *The Grok cell is `custom` and its prompt embeds the run folder* (`--improve-skill <run>/build/.../SKILL.md`): five runs, five raw prompt hashes (f32a5a16, 0a4c7bbe, 4a7bc018, f45d5e6e, cd6dbebe), one hash (5ea67bf3...) once the run's own folder is masked. The prompt key applies to `custom` always, and to a named case only when both the run and the row carry one: the smaller key, chosen so the existing `baseline vs` line survives for the 23 committed rows (none carries the hash). The transitional break is the two committed Grok rows (`custom`, rows 17 and 19): they match no new `custom` run until a row with the hash exists. The sample line under `baseline vs` states facts (`plugin tree same/different (digests)`, `Claude Code build 2.1.292 -> 2.1.294`, `n earlier row(s) in this cell on k recorded build(s)`) and no verdict.

**A regrade is not a resume [M].** `versions.regraded` is true in v1230-battleship-sonnet, r1-battleship-sonnet, r1-checkers-sonnet, r2-battleship-grok-none and the v1180/v1190 hello runs, and unset in the one real resume, r3-battleship-grok-none (`earlier_terminations` has 1 entry, a second launch record). The design's rule "`resumed_run` set means not counted" would have dropped five finished runs (Battleship n=4 instead of 5). The report classes each attempt once: no result.json, seeded, mixed host (r2: Grok started it, Claude finished it, `runrecord.mixed_host`), resumed (`earlier_terminations` or more than one launch record), process not observed (`process.status`; a regrade's `termination.process_status` reads "not observed" even when the original process was observed, as for the v1190 hello runs), did not reach done, no driver recorded, counted. Over the 35 attempts of the 22 folders and 23 rows: 15 counted, 9 rows that name no host/model/effort, 4 not done, 3 resumed, 3 with no result.json (killed before their records), 1 mixed host.

**What the recomputed cells say [M, interim as to meaning].** Sonnet Battleship: 5 runs on 5 plugin trees and 3 Claude Code builds, cost $5.6749 / $5.8146 / $9.6543 (min/median/max), turns 197 / 207 / 294, minutes 12.6 / 13.8 / 20.0, planning 4.85 / 5.56 / 6.47 minutes over 4 of 5 (v1220 predates the block; v1230's file row lacks its closed 388 s window, which the regraded folder holds: the row wins where it has a value and the folder fills the rest). Sonnet Checkers: 3 runs, cost $5.1613 / $6.6509 / $8.5146, turns 185 / 232 / 293. Overlap, as a lower bound: at least 4 of 5 Battleship and 3 of 3 Checkers rows overlapped another recorded run. Grok `none`, 5 attempts: 1 counted (v1220), 2 not done, 1 mixed host, 1 resumed; its one counted cost and turns are lower bounds. **Not separable on this data:** a cell has no two runs of one build, so build effects and run-to-run spread cannot be told apart, and the report says a range across builds is not a noise estimate. It makes no within/above/below claim: the design's `MIN_EARLIER_ROWS = 3` was attributed to the owner and no such statement exists; at n = 3 with nothing changed a new run falls outside the range of the earlier three 2 times in 4 (at most 2/(n+1) without ties).

**Host builds are recorded, never looked up afterwards [M].** Claude's build is `metrics.claude_code_version` (its init event; the report reads the init event of an older run too). Grok's and Codex's is `<cli> --version`, first stdout line (`grok 1.0.50 (c58f321264ba)`, `codex-cli 0.162.0`), probed once per launch and written on the launch record; a regrade restates it and the report never calls a CLI, so every run launched before this commit has `host_build` null for Grok and Codex (a test patches the probe to fail if called).

**The Grok session count (commit `073fd4dd`) [M].** `available_commands` is Grok's announcement of its tool and command list and is repeated inside one session: r1-battleship-grok-none has 314 for 2 `end` events and 301 model calls (2 open the first launch, 8 follow the first `end` at the head of the resume). The only per-session marker is `end`. "The first announcement at the head or after an `end`" reproduces the harness's session count on v1220 (1), v1230 (3) and r1 (2) but undercounts r3 (two launches killed in turn, one start), and an undercount would print an exact cost where a session's cost was lost, so it is not used. `unreported_sessions` is null for Grok with the reason in `unmeasured`; cost and turns stay marked lower bounds, without the invented number (`metrics.lower_bound` is the one predicate). **The rule G2's rows will enable:** run.launch knows the first line of each launch, so a launch whose line range holds no `end` event never reported; counting those replaces the null.

**Unknowns left, not guessed.** (1) Whether a Codex plugin tree digested at launch equals what the session loads (Codex syncs installed plugins to the marketplace's current release at session start); only Grok checkout installs were measured equal (the design audit compared the build folder with the installed copy on 4 runs of 52 to 104 minutes; not repeated here). (2) Pricing and the served model are assumed constant across a cell (the model is recorded as requested). (3) The committed rows of worktrees b1008a and b1009i are not copied into `baselines.jsonl` (it is a committed data file: the owner's decision); the report recovers them from the folders as long as the folders exist. (4) A deliberate edit to a named case's prompt starts a new cell; the report shows the boundary as a new cell, not as missing history.

**Deferred on purpose.** The `spread` block in `result.json` and the `_main` reorder (no reader yet), `--repeat` (a shell loop is sequential), `harness_sha256`, and any within/above/below claim or `MIN_EARLIER_ROWS`.

Verification: `test/shiploop-e2e-baseline.test.py` (the 93 tests; red first on the missing symbols, the blocked row returned as the basis, `312 is not None`, and `unrecognized arguments: --baseline-report`), the unchanged 404 tests of `test/shiploop-e2e.test.py` (one test edited: its bare `available_commands` is now the Codex shape), and `RecordedLoopRunsTest` over the committed `runs.json` (generated by the shipped command, not by a second implementation). Journal: `docs/shiploop-batch-1011q-g3-baseline-journal-2026-10-09.md`.
