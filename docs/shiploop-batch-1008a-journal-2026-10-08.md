# Batch 1008, worktree A: journal (REVISE, REGISTER, DOCCHECK, B6)

Living journal for the four items built in worktree A of `docs/shiploop-batch-1008-plan-2026-10-08.md`
(navigator and prompts). One section per item, written in the item's own commit. Each entry gives the
status of its findings (firm, interim, exploratory, superseded), the evidence, and what stays unmeasured.
Evidence for every design and audit: `docs/experiments/batch-1008-design-audit-20261008/design-audit.json`
(the entry whose key is the item name). Basis: origin/main 8a198cdd (skill-craft 1.23.0, ShipLoop 0.55.0).
REVISE is not one of the B1 to B12 items, so it has its own section here and not a row in the batch-1007
plan's audit table.

## REVISE: a redone step plan names the plan it amends (2026-10-08)

**Built (status: firm that the lines print and the route accepts an amended plan; the effect on cost is
unmeasured).** When a work item is sent back to `step-plan`, its packet now names the item's previous step
plan and the result that sent it back (both `results/<action>.md`, which `_new_result_records` writes for
every accepted action), asks for an amendment, and has the printed head's Done-when ask the summary to say
which rows are carried over. Code: `_sent_back_results`, `_revise_delta_lines` and the Done-when bullet in
`_goal_lines` (`skills/shiploop/scripts/shiploop_navigator.py`). Tests: `test/shiploop-revise.test.py`.
No state key, protocol version or gate changed.

**Why this much (firm for the numbers, interim for the conclusion).**
- On current defaults a revise redo is cheap: Sonnet 1.22.0 redid 10 stages in 1.18 min against 4.23 for
  the first pass; Grok 1.23.0 redid step-plan and test-spec in 2.28 min against 5.08 (28 and 45 percent).
- The one expensive redo of the current releases, Luna xhigh 1.21.0, rewrote the plan (all 4 criteria
  reworded, 1 step became 5, 2 test commands became 7, step-plan 38.7 to 120.1 min, its Improve child 26.7
  to 76.4 min). The Grok redo amended (all 8 criteria kept verbatim, C9 added). The packet never said
  "amend" and never named the previous plan, because `planning_revision.current_actions` drops the item's
  step plan from "Results this stage builds on" once it is sent back; it stayed only in `context-index.md`
  under "Superseded results".
- Luna has two expensive redos, not one: 123 min on 1.16.1 and 165.9 min on 1.21.0 (see the LEARNINGS
  entries "Luna max battleship on 1.16.1, final" and "Planning time: Luna xhigh and Grok medium on
  1.21.0, and where the minutes go"). Both followed the missing-module cause the test-author probe
  (`test-probe` in `stage_spec.complete_runs`) now guards. Whether the Luna growth was necessary is a
  reader's judgement: the revise reason required a new "real module seam" step.
- Every cheap redo (Sonnet 1.22.0, Grok 1.23.0) kept its context under inline delegation. No redo has
  been measured after a context clear, which is the case the tenet argument is about. So the time effect
  is unmeasured, not zero, and the tenet gain is designed, not demonstrated.

**Corrections from the audit that changed the build.**
- `_replan_delta_lines` is a shape precedent only. Its "result before the replan ... carried over" branch
  is presence-tested (`test_outer_stages_after_a_non_code_replan_are_scoped_to_the_delta`) and has never
  fired in a saved run; the one live packet with the replan delta took the no-prior-result branch. The
  amend wording is therefore not proven by it.
- The amend obligation needed a stated check, so it is also a Done-when bullet in the printed head
  (the full packet's mid-packet lines are about halfway into a 54 KB packet).
- Wording avoids "Revision 1 of 2" (it collides with the head's "revision N" and the budget text) and
  reuses the phrase `_in_progress_lines` uses, "has gone back to step-plan N of 2 times". Both results are
  marked as untrusted accepted host reports to revalidate, because after a clear or in an Ask Agent worker
  the reader is not the author.
- No silent "return nothing if a row is missing": a state that records a revision without its revise row,
  or a revise without an earlier accepted step plan, is refused at render (both refusals are reached by a
  test; the second needs `planning_review none`, because under `stage` the Improve bookkeeping refuses it
  earlier).
- The tautological "state keys unchanged" test was dropped; the guard asserts that the previous plan's
  path is absent from a first visit and from the next item, not that a common word is absent.

**Dropped, with the reasons and a re-open trigger.**
- Script-derived Improve opening (owner backlog item 7, improvement-backlog-2026-10-05). Of 23 Improve
  children across the four runs, 1 `improve-start` was refused: Grok 1.23.0, a 9,450-byte contract, 234
  bytes over the 9,216 budget, fixed in about 39 s. The expensive case is Luna xhigh (4 refusals, 3 of them
  the size guard, in the LEARNINGS entry "Luna max battleship, plan stage: the Backchain loop cannot
  persist its first callback (F3)" and the 1.21.0 planning-time entry). The "0.5 to 1.7 minutes per
  child" figure in the design has no derivation in its cited files: treat it as an estimate. **This drops
  an owner-listed item, so it is the owner's call.** Re-open when a current release shows more than one
  refusal per run recurring, or opening minutes comparable to the stage's own authoring minutes on a host
  the owner cares about. First remedy: raise the bound. `CONTRACT_BUDGET` derives from
  `until_loop_ephemeral.MAX_STATE_BYTES`, a constant in this repository (pinned to `STATE_LIMIT` by
  `test/shiploop-actual-improve-cli.test.py`); `docs/shiploop-fast-planning-plan-2026-10-04.md` (c8) names
  raising it. Second remedy: derive the opening from state.
- Engine "cheaper revise" (skipped stages, delta-only review, a prefilled template, fewer Improve passes):
  each trades S-10 rigour or saves seconds. The result record is about 1,200 tokens.
- Test-red guard against a missing module: already shipped as the `test-probe` run at `test-author`.

**Scope: step-plan only (interim).** `planning_revision.current_actions` also drops the item's test-spec
through integration-verify results after a revise, so those redone stages have the same "previous result
unnamed" gap. Their measured redo cost is lower on all three hosts (Luna test-spec 39.9 to 25.2 min, Grok
113 to 62 s, Sonnet 33 to 16 s), which supports the step-plan-only scope. Re-open on a measured expensive
redo of one of those stages.

**Unknowns left open.**
- Does the amend wording shrink a Luna-class redo? Settle by the next live run that contains a revise: read
  the Run Review export's per-visit minutes, and compare the redo's criteria carry-over and result bytes
  with the first plan.
- The Improve child that reviews the redone plan (76.4 of Luna's 120.1 min) is not told the plan is an
  amendment; whether that shortens its until-two-passes-change-nothing loop is unmeasured. S-10 is untouched.
- A revise after a bound parallel chain (`state['chain_bindings']`) was not examined.
- The could-not-run revise route fixed by 6a59012c is cited without a run; the commit exists.
- Whether a live refusal of the test-author probe on a real missing module ever happens: the probe has
  run at W1 and W2 in the Grok 1.23.0 run and was accepted first time. A failing test plus an unimportable
  module in one command with no ids reads as red (`PROBE_CASES`, "known limit"); adversarial-only, unchanged.

**For the Run Review session (skills/shiploop-run-review is not edited here).** The redo packet grows by
about 600 bytes. The change adds no export field; a stage card must not parse these lines.

## REGISTER: one true pass-log rule, test-command authority documented (2026-10-08)

**Built (status: firm that the text is static and the same in both places; interim for whether it changes
behaviour).**
- `context_index.PASS_LOG_RULE`, used by the packet line (`_context_index_lines` in
  `shiploop_navigator.py`) and the context index "In progress" line (`_in_progress_lines`). Neither reads
  the log, so both stay true at the moment of recovery. It tells the pass to create the log when it starts
  (the batch plan's decision), to append after each pass what was checked and what is left, and a reset to
  open it first if it exists; if it does not, nothing was logged and the scratch files and worktree show
  how far the stage got.
- `references/state-files.md`: one `notes/` row, and the `inbox/` and `results/` roles; a "Test commands"
  paragraph in "Test decisions in `state.md`", stated in the terms of the test-strategy duty ("one file owns
  the suite commands") and pinned by `test/shiploop-navigator-contract.test.py`, which is untouched.
- `docs/record-register-2026-10-07.md`: a "Dispositions, 2026-10-08" section, and the "byte-compares" wording
  corrected to parsed equality on planning-return paths.
- Tests (`test/shiploop-rehydration.test.py`): a wording-level test that the packet line is conditional
  (failed first; not a refusal route, so the "route not wording" rule does not apply), the index pin updated,
  and a guard that two renders around the creation of a non-empty or empty log are byte-identical for the
  packet and the index (green before and after: it keeps a future change from reading the host-written log).

**Why the design changed (audit, firm).** The design printed "none yet" or "open it first" by looking for the
file at render time. A packet is written once, at action start (`navigator.emit`), and only `next` rewrites
it. After a context loss the model re-reads the packet file: 5 of 11 Grok compactions began that way with no
`next` (SPEC S-6 cites the same evidence). A mid-stage log, the behaviour the aid wants to induce, would
leave "none yet" on disk. `_in_progress_lines` also states the log, is regenerated only at save, and could
not be kept true at all. A render-time existence check would also make a derived view depend on a
host-written file outside `state.md`.

**Dropped.**
- The loop-contract change (remove the pass-log row from `test_loop.build_contract`, `quality.build_contract`
  and the `listing_problem` list). The contract file is written once, at the transition into the action
  (`transition_writes` via `_lint_transition`); `next` never rewrites it and the printed `Start:` feeds that file
  to the runtime. A loop started before a release would produce a terminal packet whose context still carries the
  row, `check_loop_packet` refuses it, and restarting re-feeds the same stale file, so the refusal has no working
  exit; the guard case in the design started from a freshly built contract and could not see that. It would save
  about 240 bytes of a 3.3 to 5.0 KB contract and contradicts the tenet's "repetition across packets is
  grounding". Re-open only with a real exit (ShipLoop rewriting the contract on `next`, a new write path) and a
  test that writes the old-shaped file to disk; the note would then be minor.
- Enforcing that docs match the ledger, or pointing docs at `state.md`; and removing the inbox or results copy.
  See the register's dispositions for the numbers.
- The compact evidence file `docs/experiments/batch-1007-live-20261007/records-single-source.json`. The
  per-run analysis was done in the design agent's scratch space and its script was not kept, so it cannot be
  regenerated or validated here. The figures (13 context losses, 29 command rows, first-write positions) are in
  `docs/experiments/batch-1008-design-audit-20261008/design-audit.json` (key REGISTER) with the audit's
  corrections, and the corrected numbers are in the register. End state: unachievable in this change, not
  written-but-not-run.

**Audit corrections to the evidence (applied in the register).** Event 10305 is a same-context existence check,
not a post-reset read (one post-reset read, not two); cancellation 11926 and compaction 12067 were in
carry-forward W2, not system-test-author; the 1.22.0 write-to-complete gap is 7 to 39 events, not 2 to 18;
`planning_context.collect` runs only on planning-return paths. The S-6 probe claim "met for the contract change
by the 1.23.0 kills" is dropped with the contract change: the only loss inside a loop stage was one test-green
compaction, and none in a quality or regression loop.

**Unknowns left open.**
- Does the create-at-start instruction get followed, and on which host? Settle with the next paired Sonnet and
  Grok runs: rerun the events analysis (first-write position as a share of the stage's events). The cost to
  weigh is about one extra write per action (38 to 47 per run). Sonnet has written none in 84 actions.
- Does an existing mid-stage log reduce redone work after a reset? Needs a log first; probe with a
  clear-the-context inside a long Grok stage (implement, plan or carry-forward ran 9.6 to 14.5 minutes).
- Share of recoveries that re-read the packet file versus run `next`, per host: 5 of 11 packet-first on Grok,
  Claude unmeasured.
- The 7 ledger command rows in no prose file mean the "plans point at the strategy file" duty is not met for
  per-item commands; documenting it records the gap and does not close it. Do test commands drift when a second
  feature inherits the strategy file? n=0.
- A packet-text change moves the baseline of any byte-identity comparison of dry-run packets (the LEARNINGS
  practice of comparing dry-run packets before and after a prompt change); no test pins it.

## DOCCHECK: no new document checker; two small messages (2026-10-08)

**Measured, and what it decides (status: firm for the counts of the one run, interim for the conclusion;
n=1, ShipLoop 1.21.0, Luna xhigh).** The lever the backlog called "script-owned document checks instead of
model-written check scripts" is mostly not document checks. In the Luna xhigh 1.21.0 run
(`/Users/dadleet/e2e-runs/20261005/v1210-battleship-luna-xhigh`; planning window 375.0 min to the first
test-spec accept, 904 shell calls) the 196 inline scripts split into Improve and Backchain loop glue 68 =
44.8 min, document authoring 52 = 37.5, other read and probe 34 = 13.7, result and state reads 20 = 10.4, and
pure document checks 22 = 8.9 min (links, anchors, whitespace 15 = 6.6; ids and content 7 = 2.3). That agrees
with `docs/pending-work-plan-2026-10-06.md` (13 of 162 scripts, 7.5 min), and it supersedes the ledger lever
L11 ("about 100 scripts, 73.8 min, 35 to 55 savable"), whose raw per-response analyses were not kept and which
cannot be re-derived. Caveats: each figure is time from the previous tool result to the call, so it includes
the model's thinking and is an upper bound; the 8.9 depends on the classifier's precedence (glue, then
authoring, then check) and the classifier was not preserved, so this is not re-runnable here. An independent
count by the audit agrees on 904 shell calls and 43 scripts with a markdown-link regex (about 15.4 min by the
same upper bound, roughly 4 percent of the window), so "no new checker" holds under any classification.
The four named runs: the Grok none runs have no document-check script at all; the Sonnet stage-mode runs
have 3 to 4 counts-only passes. Evidence: `docs/experiments/batch-1008-design-audit-20261008/design-audit.json`
(key DOCCHECK). The compact classifier output was not committed because its script was not kept (end state:
unachievable here, not written-but-not-run); the live pair below is where it would be re-measured.

**What generic checks would have found (firm).** Of 43 Luna scripts with a markdown-link regex (24
read-only, 5.8 min, 5 distinct `slug()` implementations) none reported a broken link, anchor or trailing
whitespace; the only gaps found were product-specific content assertions a script cannot own. Six delivered
knowledge homes: 0 trailing-whitespace lines, 0 broken anchors, 1 broken relative file link (the Grok 1.23.0
`docs/shiploop/README.md` links `../SHIPLOOP.md`, which should be `../../SHIPLOOP.md`; that run had no review
pass). **Known gap, not fixed:** it ships in a file ShipLoop itself commits. Re-open owning relative-file link
existence in `knowledge_home.check` (files under `docs/shiploop` and `SHIPLOOP.md` only, never anchors) on any
measured escape of a broken link, and a requirement-ID or criterion traceability check on any measured
escape whose origin is a planning document, and only over a structured field, never prose search (plans
write "R-1..R-9" and a mention is not coverage). No thresholds are proposed.

**P2: an unparsable result file takes the rejected-request route (built; firm).** `_submitted_result` let
`store.StorageError` from `read_record` reach `shiploop_protocol.main`'s heavy branch ("Request failure: no
in-memory result ... Durable cursor recovery ... Do not infer a next action"), the text made for lost state.
A file the model just wrote that has no fence, a trailing comma, an unterminated fence or a duplicate key is a
fault in that file. It now raises `NavigatorError` carrying the parser's reason and "fix the result file and
run the same command again", so it takes the light route that already serves the sibling failures in the
same function. The heavy branch stays for real storage faults. The route is tested through the real CLI in
`test/shiploop-callback-contract.test.py` (four bad files, each refused with state unchanged and then fixed
and accepted). Heavy-route refusals on a malformed model-written result occurred in 3 of 16 run folders under
`/Users/dadleet/e2e-runs`: v1190-hello-sonnet (1), v1200-hello-sonnet (2, events 124 and 135, not 3 as the
design said) and v1230-battleship-grok-none (1, about 0.2 min). The saving is small; the point is that the
text no longer tells the model to stop inferring a next action over a typo it can fix.
- `improve-reconcile` shares this function, so the message names no verb ("run the same command again").
  Its route is not tested (it needs a stopped Improve child): a stated gap, not "covered by construction".
- Same class, left alone, occurring in none of 16 folders: the `--final-result` read in
  `_derived_improve_receipt` (a shared helper for model-written record reads would cover both and is
  not much larger than this change; decide deliberately), and the handoff refusal "handoff requires a
  verified workspace return: <commands>" (`workspace_completion_guard` raises `ProtocolError`, so it prints
  "Do not infer a next action" though it names the commands to run).
- Unowned, not credited to this item: `improve-complete` requires a `checks.md` that nothing parses, and in
  planning reviews the model fills it with counts or `tests 0` summaries (4 of the 8 `checks.md` files in the
  Sonnet 1.23.0 run). The next live pair should count it as its own family.

**P1: the Checked-by line of a stage with no script-run check names the faults `complete` refuses (built;
firm that line and gates agree, unknown whether it changes behaviour).** 23 of 34 stages have no
`complete_runs`, and their packet said "Checked by: nothing automatic beyond the result's form". That is
false for the gates that exist, and it invites a model to re-implement them: the result JSON shape
(`_canonical_result`), evidence-file existence (`_check_submitted_evidence`), the credential screen
(`_reject_credentials`), the plan's assumption list (`_check_submitted_assumptions`), a step plan's test
commands, criteria, paths and steps (`_check_submitted_test_commands`, `_normalise_criteria`,
`_normalise_steps`), `consumer_entry` sources (`_check_submitted_consumer_entry`), the recorded command lists
(`_check_submitted_recorded_commands`) and the knowledge closes (`knowledge_home.check`). By hand in the
named runs: criteria coverage and step deps in Luna 1.21.0, Grok medium 1.21.0 and both 1.23.0 runs; evidence
existence in two; credential screens (5 or more) in Grok medium 1.21.0; a result-JSON pre-check before
`complete` in all six runs (Grok 1.23.0 chains 3 of its 5 into the `complete` call, so their marginal cost is
about zero). `_checked_line` now builds one line (the keepalive suite requires one `Checked by:` line) from
`_COMMON_GATES` plus `_stage_gates`, which reads the tables the gates read (`assumptions.STAGES`,
`RECORDED_COMMANDS`, `knowledge.CLOSES`) so a stage cannot be named that the gate does not serve.
- Audit corrections applied: it was not folded into a pending note (the line shipped in 1.23.0, so a new
  note); the text says "absolute" because `_check_submitted_evidence` checks only paths that start with `/`
  (a relative reference to a missing file is accepted; reproduced in a scratch run); it says "an explicit
  credential pattern", because the screen's own docstring says a false result is not a guarantee; it does not
  name "a fault named in the stage's knowledge lines" (no gate or test); and it names the non-form gates the
  design missed (release-plan's `consumer_entry`, the recorded command lists, the knowledge closes).
- Tests: `test/shiploop-packet-completeness.test.py` declares which stages may carry which gate word and checks
  all 23 lines (failed on all 23 before); `test/shiploop-callback-contract.test.py` pairs each named fault
  with its real refusal and an accepted correction through the CLI (eight faults plus the knowledge close),
  green before and after as a guard: remove a gate and the line over-promises, and this fails.
- A fault the line does not name is the status quo, not a regression: `implement` is refused by
  `item_scope.scope_refusal` for changes outside the step plan's paths, but its `complete_runs` text lists only
  the lint gate (same defect class, `_CHECK_TEXT`, recorded and not changed); `release-verify`'s knowledge close
  likewise; a newly added gate is not named automatically.
- Not measured: whether an accurate line reduces hand-written re-implementations of owned gates. Settle with the
  next live pair (Sonnet checks on, Grok none) by counting inline scripts in the planning window for five
  families (result-json pre-check, criteria coverage, step deps, evidence-exists, credential screen) and report
  counts only. Baselines read: Sonnet 1.23.0 1 coverage, 1 deps, 1 result-json; Grok 1.23.0 2 result-json, 1
  coverage; Grok medium 1.21.0 coverage 3, credential 5 or more, result-json 6; Luna 1.21.0 evidence-exists 3 or
  more, result-json 11. The Sonnet hand-written pre-checks prevented no refusals (zero `shiploop_failures` in
  both Sonnet runs): habit or `checks.md` filler.

**Kept-head window (found while building P1, firm).** `test/shiploop-status-display.test.py` holds the status
block inside the first 8000 characters of every dry-run packet (`shiploop_status_hook.WINDOW`, the head Claude
Code keeps of oversized Bash output). The longer step-plan line pushed the ask-agent redo packet to 8045, so the
new Done-when bullet of the REVISE entry was shortened and the step-plan clause tightened; the heaviest packet
(ask-agent, step-plan after a revise) now ends the block at 7960 (measured with `graph-dry-run --scenario all --delegation ask-agent`); the first-visit ask-agent
step-plan packet ends it at 7819 and the next item's at 7864. **The margin of the redo packet is 40 characters, so the next addition to the head of
a step-plan packet must shorten something else or raise `WINDOW` deliberately;** the window is a host fact I
could not verify, so I did not raise it.
