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
7. [M] The failure metric is blind for Claude. `metrics.collect` reads only ACP `tool_call_update` events, so `metrics.json` has `shiploop_failures` of length 0 for all 7 Claude runs, against 15 failing commands in the export plus 28 refusals behind exit 0 in recognised ShipLoop commands (40 counting wrapper scripts that the CLI pattern does not recognise). The "Batch 1003 - Sonnet 5.5 results" table above says "0, 0" for four rows that hold 13 failures. Claude counts are lower bounds. The exporter already reads `metrics.shiploop_failures`, so M1 puts the one classifier in `metrics.collect`; the "0" cells are corrected by edit with a reason under M1, not here.

**Decision: defer the engine change (Item C: drop the derivable `--result`, `--opening` and `--message` flags from the callback).**
- Grounds: KISS (no break beyond a recoverable one-call cost) and Change admission's "cost more than it saves": Item C costs a release plus 18 test and fixture files to save about 28 s in an 18 h Luna run. Batch discipline also holds: no engine change while a run is live, one release.
- Accepted exception to S-4 and S-5 (a derivable path stays model-copied), with its cost: 4 failing commands, 28.4 s, 22.7 s of it on 3 callbacks, in 18.83 h of Luna max.
- Reopen Item C when either happens, on ShipLoop callbacks only (Until Loop paths are excluded; they are vendored argv, U1):
  - R1: a path typo in any run other than `v1161-battleship-luna` (any host, model, session or path length).
  - R2: a callback typo not repaired by the next ShipLoop command, or a run ending blocked because of one.
- The item stays monitored, never closed. A clean run is uninformative unless a resumed session types at least 1,442 paths with 0 typos [I].

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
- *Fixed, `ea21092e`: `shared_tmp_writes` ignores `unmeasured["tmp_writes"]` (4 findings).* A run with unmeasured writes is left out of the comparison, named in `suite-result.json` as `tmp_writes_unmeasured`, and printed as not checked.
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
