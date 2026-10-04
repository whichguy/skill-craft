# ShipLoop E2E plan reconciliation, 2026-10-04

Execute: ask

Status: reconciles revision 6 of `docs/shiploop-e2e-plan-2026-09-27.md` (P14 to P21, written against `ede4b9df`) with the worktree branch `a1a3-integ-7f216e` (HEAD `9db0be37`; origin/main is `3102c341`, skill-craft 1.19.1). This document replaces rev 6's dependency order as the execution plan; rev 6's text stays as the design record. Nothing here is implemented. Governing spec: `test/shiploop_e2e/SPEC.md` (S-1..S-15).

Legend: [M] read in code or a record, or run (this pass, or a workstream's scratch repro under `/private/tmp/claude-501/-Users-dadleet-src-skill-craft/f7d9360d-b88d-417b-8773-fc5b3eee6419/scratchpad/plan-e2e/`: g1f, g2final, g3, g4final, g5final, g6); [I] inferred. This pass re-read directly: the resume branch, committed dict, `termination_facts` and `previous_row` in `run.py`; `metrics.collect`; the clean streak in `iterate.py`; `retention[3]` of `battleship-scoring` in `cases.json`; the SPEC baseline sentences; `LEAF_SOURCE` in `scripts/check-release-boundary.py`; the A2 design text; branch topology; live process state.

## 1. Where things stand

- [M] Landed on the worktree branch, unreleased: A1 (a test run that times out or cannot start is could-not-run), A2 (per-stage attribution from state history, timing unavailable instead of zero, baselines compare only within host/model/effort, no `cost_share_usd`), A3 (`termination_facts`). Released in 1.19.0 and on origin/main: the Run Review exporter, the regrade path that skips the version gate, `--strict-mcp-config` (bc3046db).
- [M] origin/main is 5 commits past the merge base bc3046db (1.19.1 release, plain parallel case, `budget_facts` interrupt fix); the worktree is 4 ahead and 5 behind. The only `run.py` change on origin is `budget_facts` and its call: no overlap with the increments below. [I] Its test-file, LEARNINGS and `cases.json` changes are additive.
- [M] a13 is uncommitted in worktree `a13-33dbfd` (note `changes/shiploop/system-test-open-item.md`, based on an older commit). A1's note is committed here. Skill changes need one release before a marketplace run can use them.
- [M] test/ and docs/ only commits need no change note and no `No-Change-Note` trailer (`LEAF_SOURCE` matches only `skills/<leaf>/` and `agents/<leaf>.md`). Two workstreams said the trailer was needed; that was wrong.
- [M] Branch `codex/shiploop-e2e-evidence` (6e22f287) implements P14 to P21 in a different design (SPEC amendment, eight qualification states, calibration receipts). It is unmerged. See owner decision 1.
- [M] Two product servers started by a Claude host's model are still alive, ppid 1, about 27 h old: pid 63872 (`python server.py`) and pid 83695 (`node server.js`). No harness run process is running now.

## 2. P14 to P21, reconciled

| Item | Status | One-line evidence |
|---|---|---|
| P14 Success contract | dropped as written | [M] `result.json` already keeps the axes apart (verdicts, metrics, `termination`, `expectations` with a named source per check); the 8 cases in `cases.json` have no boundary, no-op or expected-block case, so valid/incomplete/invalid, delivered/partial and behavioral-scenario states would have no consumer. The two wrong readings the audit found are verdict bugs, fixed by R1 and R2. Reopens at the first case that expects a block, a refusal or a no-op. |
| P15 Invocation and evaluator integrity | partly | Addressed: stop reasons (A3), connector isolation (bc3046db), invoked on resume (tested). Open and planned: plugin verdict on resume (R1), committed verdict (R2). Deferred: a reviewer that returned nothing counts as clean (D1), result lineage (D3). Dropped: run binding, improver scope, evaluator self-edit, checks graded in the worktree. |
| P16 Effects, recovery, stop ownership | partly | Addressed: budget extension record (`invocation-resume-*.json` plus A3), CI pin recorded at start. Planned: a regrade claims a host exit nobody saw (R6), documented limits (R8). Premise corrected: the draft's group-kill reap would not have reached the leaked servers [M: own process groups, ppid 1]. Deferred: D2, D7 to D10. Dropped: owned-effects. |
| P17 Outcome checks, judge calibration | partly | Addressed: temperature regressions (3f23a15d, pinned by `CheckHygieneTest`). Planned: retention id check false-FAILs a correct spec (R7). Obsolete: judge calibration, because no model judge can change `result.pass` [M: `all(verdicts)`]. Dropped: stub guard, request-to-check map, semantic retention. |
| P18 Causal review, retained unknowns | dropped | [M] `review.py` has no recorded live run (only synthetic probes); the reviewer prompt already carries the SPEC and the S-clause citation rule; the journal and Run Review observation status (open/fixed/accepted/reexpected) already retain unknowns. Trigger in D13. |
| P19 Fair comparisons, budget accounting | partly | Addressed by A2: timing unavailable, comparison within host/model/effort, no cost share. Planned: Codex cost and tokens read zero (R3), killed sessions make cost a silent lower bound (R4). Deferred: D4, D5, D11, D12. Dropped: denominator report, Claude turn unit, A/B campaign, replicate meter, budget threshold. |
| P20 Targeted qualification | partly | Planned: pre-register the batch's coverage map and decision table (R9). Dropped: frozen transfer variation. Deferred: MCP-count tripwire (D4). |
| P21 Close and promote claims | dropped as new machinery | [M] the Run Review iteration schema (verdict pending/confirmed/partly/refuted, next) and the journal already hold the close. Its wrong inputs are fixed by R1, R3 and R5. |

## 3. The batch and its cap

One release, one verification set.

- Release: only what is already landed or admitted, A1 and a13 (skill changes). Every increment below is test/ or docs/ and ships as ordinary commits before the release, because the version gate refuses a local HEAD with commits origin/main lacks [M].
- Verification set, in order: `run.py --preflight-only --host all` ($0); the Sonnet 5.5 hello gate (about $5, 15 min); one unseeded Luna max battleship (hours, no dollar cap; S-14 defaults recorded, not asked: `--timeout 36000`, at most one `--resume-run` if the process ends while ShipLoop is active).
- The hello gate shows the release, A2 and A3 live and the first identity-carrying baseline row. Only the Luna run can exercise a13. Proved by hermetic tests only, and said so: A1 could-not-run (no catalog case provokes it), R6, R7. Chain, retention and concurrency are not re-qualified [M: behaviour unchanged since 1.17.0 except read-only report listing and wording].
- Cap: nine increments, each one-line or small; no engine change after the release; no new case; no `suites.json` edit; no new result state; the only new fields are a count (`unreported_sessions`) and the host's own `usage` per session.

a13 decision table (committed by R9 before launch):

| Outcome of the Luna run | Reading |
|---|---|
| a. system-test accepted done with a person-owned open item recorded and the run continuing | a13 confirmed for this case, host, model and effort; a later block is a separate finding |
| b. done, no person-only case planned | a13 not exercised |
| c. blocked at system-test on a person-only case again | a13 refuted for Luna; take the deferred test-strategy change |
| d. blocked before system-test | new finding; a13 unexercised |
| e. host died or deadline | inconclusive; `termination` says why |

Hold while the Luna run is in flight [M: the active-resume gate refuses on each]: no release; no push to origin/main carrying a `changes/` note; run the harness from a checkout whose HEAD is an ancestor of origin/main; main CI not red before any `--resume-run`; Codex also refuses after any later release. Ordinary test and docs pushes are fine.

## 4. Increments, in order

Order is value first (what breaks or misleads a normal run), then dependency. R1 must land before the Luna launch, because its carry-forward needs the first launch's `invocation.json` to hold the plugin record.

Serialisation. `run.py`: R1, R2, R3 to R4 (summarize and whitelist hunks), R6. `metrics.py`: R3, R4, R5. `test/shiploop-e2e.test.py` and `LEARNINGS.md`: all code increments (append-only; rebase and run the whole file once at the end). README: R1 to R4, R8. Parallel worktrees are safe only across the disjoint chains: A (R1, R2, R6), B (R3, R4, R5), C (R7). D (R8, then R9) follows.

**R1. A resumed or regraded Codex or Grok run keeps its first launch's plugin verdict.** one-line.
- [M] The same-host resume branch sets `plugin = None`; `grade_claude_plugin` reads only Claude's init event; Luna v1161 `result.json` says plugin false, loaded [] although the first process graded true; reproduced with the fake Codex and Grok hosts. 11 of 25 recorded runs were operator-resumed (workstream recount), so this is the routine path.
- Change: add `"plugin": plugin` to the invocation dict; in the resume branch use `earlier.get("plugin")`. Claude stores None and still grades from its event. No migration: an older `invocation.json` grades as today. README plugin bullet gets one clause; the LEARNINGS "grading defect (open)" bullet is marked fixed and the v1161 plugin-fail reading superseded.
- Merges three workstreams' identical two lines (P15-plugin-resume, P16-resume-verdicts 1, P21-close-inputs 1).
- Test: `RegradeRecordTest.test_a_regrade_keeps_the_plugin_evidence_of_the_first_process` for claude, grok and codex (patch `released_versions`); fails today for grok and codex. Do not edit the shared fake-host fixtures (that breaks two existing tests [M]).

**R2. `committed` requires product files in HEAD.** small.
- [M] The verdict is `head != start_head` with nothing uncommitted. On a fresh run ShipLoop's `bootstrap_empty` makes an empty-tree baseline commit, so any HEAD passes. Two blocked Luna runs on disk read committed pass true with 0 files in HEAD (v1161: source holds one empty commit, ShipLoop's worktree 39). Replaying the rule over the 12 recorded results flips exactly those two. `result.pass` was never wrong (the shiploop verdict needs done plus a report); the row, baseline rows and the Run Review strip were.
- Change: `committed_facts(knowledge, start_head)` with `head_files` from `git ls-tree -r --name-only HEAD`; pass also needs `head_files > 0`. The printed line, the mismatch row, README and the `run.py` docstring change with the rule. LEARNINGS marks the earlier committed-pass readings superseded (not regradable: the runs are blocked).
- Known limit, documented not guarded: any file counts, so a future ShipLoop that returned knowledge-only commits to the source first would pass early [I]; today they stay in its worktree until the return [M].
- Test: `CommittedVerdictTest` on real git in a temp dir (empty baseline only gives False and 0; one file gives True and 1), plus one assertion that `mismatch.md` contains "files in HEAD".

**R3. Cost is unknown unless every ended session reported; the host's usage is kept per session; no figure is built from a snapshot.** small.
- [M] Luna v1161 reports cost 0 and tokens 0 although its end event carries 172.6M input and 1.62M output tokens and `total_cost_usd` None (`sum(... or 0)` in `metrics.collect` and `run.summarize_events`). Claude `tokens.output_total` is 5,459 against the host's 86,188 (per-event output is a streaming snapshot), so the per-stage `output_tokens` is about 25 times low. A per-key sum over a real Claude `result.usage` raises TypeError (nested dicts).
- Change: one `total_cost(sessions)` used by both sites (S-12); `sessions[].usage` kept as written and never summed; delete `output_total`, per-stage `output_tokens` and the turn `output` key (nothing reads them [M]); `input_peak` None when no turn reported usage and `progress.py` prints "n/a". README: remove the stale "cost share" and output-token claims; unit notes that Claude turns count assistant content blocks (1.70 to 1.96 times the API calls [M, 11 runs]) and that Claude `shiploop_failures` 0 means unmeasured until M1 (D6).
- Anchors: SPEC "How the harness checks the clauses" (cost scored beside verdicts), the S-7 row (peak context), S-12. No S-n names a cost unit (owner decision 5).
- Tests: `MetricsTest.test_unknown_cost_stays_unknown_and_the_hosts_own_usage_is_kept_unsummed` (including a trimmed real Claude usage dict), `test_no_token_figure_is_made_from_events_that_do_not_carry_it`, `StageAttributionTest.test_a_stage_row_carries_no_output_token_figure`, a progress "peak context n/a" test, and edited pins in `CodexHostTest` (two) and `CodexRunTest` (`cost_usd` None through `run.main`). The workstream prototype fails them unpatched and passes the whole file patched.

**R4. Killed sessions make the cost a visible lower bound.** small. Lands with R3 (same function).
- [M] `batch-sonnet/seat-reservations`: 4 session starts, 1 end, reports $1.85 for 423 turns; all 6 of the 12 run directories with more starts than ends carry `resumed_run`.
- Change: `unreported_sessions = max(0, starts - ended)` (starts from Claude `system/init`, Codex and Grok `available_commands`), whitelisted into `result.json` metrics and printed as " (lower bound: N session(s) never reported)" beside the cost. Not a baseline key and not a filter (interrupt-recovery rows must stay comparable). README: turns and cost add up across the sessions that reported. The interrupt fake prints its init event with `flush=True`.
- Test: `MetricsTest.test_a_session_killed_before_it_reported_makes_the_cost_a_lower_bound` (1, 0, Grok-shaped 1, never negative); `SeedTest` interrupt asserts 1 through `run.main`; `CodexRunTest` asserts 0. Without the whitelist the field never reaches `result.json`, which the tests pin.

**R5. `improve_children` counts directories.** one-line.
- [M] `len(list(improve.iterdir()))` counts each child's directory and its `-bind.md`: Luna v1161 reports 18 for 9; the live progress line doubles each increment; the exporter already counts directories.
- Test: add `improve/child-1-bind.md` beside the fixture's `improve/child-1`; the existing `== 1` assertion fails today (2).

**R6. A regrade claims no host exit.** small. Droppable if the batch crowds: nothing reads `termination` yet.
- [M] A regrade builds `process = {status exited, returncode 0, regraded true}`, so `termination_facts` reports exited, 0, one session for a run that started no host (reproduced on claude, grok and codex; A3 is unreleased, so this fixes it inside its own contract).
- Change: first line of `termination_facts`: `if process.get("regraded"): process = {}`; docstring says `sessions` and `resumes` count the final invocation only while `session_stops` covers every reported stop; the loop comment stops listing "awaiting" as a status (it is a view of blocked, not a status [M]); same two sentences in the A3 LEARNINGS bullet.
- Test: `RegradeRecordTest.test_a_regrade_reports_no_observed_exit` gives ("unknown", None, 0), `engine_status` done, `process.pass` true. Fails today on all three hosts.

**R7. The retention id check counts ids the way the engine does.** one-line.
- [M] `battleship-scoring` `retention[3]` counts ids with a line-start heading or bullet pattern; the engine's `_REQUIREMENT_ID` is `\bR-\d+\b` and accepts an id anywhere. Three real Battleship specs use three forms: bullets (8 ids), headings (6), table rows (old command reads 0, engine reads 10). BSD grep `-ow` diverges from the engine (reads 1 of 2 in `R-1 R-1a R-2`), so use `grep -oE '\bR-[0-9]+\b'` verbatim (JSON-escaped `\\b`). A dropped id still fails in every form.
- Change: one catalog line, plus one LEARNINGS entry carrying a Limits paragraph so dropped items are documented: the Battleship checks are protocol checks (three constructed stubs pass 4/4; rule correctness belongs to ShipLoop's own system test, S-9); coordinates are assumed 0-based; a check that times out or cannot start reads as a product FAIL; ports 39171 to 39176 can collide in a parallel suite; hello's zero-test guard depends on the interpreter's exit 5.
- Test: `CheckHygieneTest` table of four forms (bullet, bold bullet, table row, mixed line), a drift guard against `run.knowledge_home._REQUIREMENT_ID`, and a dropped-id failure. Bold bullet, table row and mixed line fail today. Not proved live by this batch (no chain run); the next battleship to battleship-scoring chain confirms it.

**R8. Document the limits a normal run can meet.** one-line, docs only.
- README "Launching long runs": a task kill stops the harness and no harness code runs; model-started background servers have outlived runs by more than a day because Claude Code gives each Bash call its own process group, which the harness's group kill does not reach; list them with `lsof -nP -a -d cwd -Fpn` filtered on the output directory (match a path boundary, since sibling cases share a suite directory) and kill by pid; no verdict reads them. README process bullet: on a resume the process block describes the last invocation only.
- LEARNINGS: a blocked run does not say whether a person or the engine blocked it; a timed-out check can leave its shell's children; a retention check running a suite in `$PRIOR_WORK` could write there (unobserved); run binding takes the oldest done run if two states exist (0 of 23 results); a resumed run's first-process row stays out of `baselines.jsonl` by hand.
- Test: `grep -q 'lsof -nP -a -d cwd'` and `grep -q 'no harness code runs'` on the README, `grep -q 'blocked run does not say'` on LEARNINGS; exits 1 before the edit, 0 after.

**R9. Pre-register the coverage map and decision table.** small, docs only.
- One LEARNINGS section committed before the Luna launch: the three-run map, the a13 decision table, the hold list, the S-14 defaults, and the coverage statement (hermetic-only, not re-qualified). Do not edit `suites.json` (its batch entry is stale and one suite means one host; the gate-then-Luna order is by hand).
- Test: `git log -1 --format=%ct -- test/shiploop_e2e/LEARNINGS.md` is earlier than the Luna `invocation.json` mtime, and the committed text contains "a13 decision table".

## 5. Sequence

0. Merge origin/main (3102c341) into the branch; run the whole test file once as the baseline.
1. Land R1 to R8 (chains A, B, C, then D); run the whole file once; run the quick tier.
2. R9; push all harness commits as ordinary commits (proceed optimistically on CI).
3. a13's own session commits it and rebases onto origin/main; merge; `scripts/release.py` for the A1 and a13 notes; push; refresh `skill-craft@whichguy` on the hosts.
4. Preflight `--host all`, then the Sonnet 5.5 hello gate, then the unseeded Luna battleship (hold list in force).
5. Close with one journal entry that maps the Luna result to its R9 row. It cites, for Claude, `cost_usd` and `result.num_turns` (never the harness turn count) and no failure, glue, /tmp, cancelled or knowledge-read count; for Codex, wall minutes and `termination` only, never a dollar figure or per-stage turns. It notes the gate's init event once (CLI version, server count 0 expected).

## 6. Deferred

| Id | Item | Why not now [M unless marked] | Reopens when |
|---|---|---|---|
| D1 | A review that did not finish counts as clean in `iterate.py` (workstreams G1, G3, G4) | Reproduced on fakes only; no recorded live `iterate.py` run; fix is one predicate | The owner will run `iterate.py` (owner decision 4), the first iterate run, or any `review.py` timeout on a real run. Ready: `usable(review)` is `process.status == 'exited'` and `'learnings'` present; stop after `record_learnings`; patch and tests in scratch `g4final` |
| D2 | Pin that a blocked run is not resumed | Behaviour is correct and never regressed; Luna v1161 ended blocked and was not resumed | The next edit to the in-process resume loop or the termination wiring. Ready: fake Grok `blocked` mode, mutation-checked |
| D3 | Keep each attempt's `result.json` | No reader of the earlier copy; the one real loss (first plugin verdict) is closed by R1 | A consumer of an earlier attempt's result, or the first resumed seeded run. Cover both overwrite sites (final write, version-gate stub) |
| D4 | Record `claude_code_version` and MCP server count with the row | Cause fixed and pinned (`--strict-mcp-config`); two strict full runs list 0 servers and 28 tools; no consumer | A Claude init lists servers, the CLI version changes, or a cost/turn shift between same-identity rows no run directory explains. Mitigation now: the closing journal entry. Ready: two lines in `summarize_events` plus a test |
| D5 | `previous_row` skips non-passing rows | All 15 committed rows lack identity, so none can match; the first comparison exists only from the second identity-carrying row; A2's incomplete stage rows exist to compare a stopped stage, so a blanket filter contradicts its intent | The first printed comparison against a pass-false row carrying host, model and effort. Until then leave resumed runs' first-process rows out of `baselines.jsonl` by hand |
| D6 | Claude failure counter (M1 in `docs/shiploop-callback-typos-plan-2026-10-04.md`, step 5) | Own admission and open question 4; unblocked by A2 | Own plan; land after R3 and R4 in separate commits. Constraints from this pass: key the call registry by `block.get('id')`, count main-thread commands only, share one failure helper with the Grok branch, report exit 127 apart from refusals. At M1 correct the 1.18.0 "failures 0" claim, the 1.19.0 entry and the four `evidence/claude-*.json` cells |
| D7 | Codex release drift (marketplace re-sync at session start) | A loud refusal exists; the in-process resume path has never run on Codex | The next Codex run expected to outlive a release cycle. Ready: no-model probe with `--ref <sha>` in a throwaway CODEX_HOME |
| D8 | Version gate on an active `--resume-run` | Unobserved; the checkout half was kept on purpose | The first refusal, or before relaunching a multi-hour run from a worktree with unpublished commits. The hold list substitutes for this batch |
| D9 | Reap model-started processes | Draft premise wrong; no verdict affected; documented by R8 | A stale server answers a check or a later run's own verification. Ready: scan by cwd under the output directory with a path-boundary match, once after the last session, record before any kill; never inside `launch()`, never by name |
| D10 | A `SystemExit` in one suite chain loses `suite-result.json` | Reproduced on fakes; no refused case in any real suite | The first refused case in a real suite; then a try/except per chain case and a "refused" row |
| D11 | Attempt-lineage row for a completed resume | Nobody counts eventual deliveries from `baselines.jsonl` | The first delivery count made from that file |
| D12 | Case or evaluator identity hash on rows | Git holds case history by date; nothing was misled | The first edit to a case prompt or check while a comparable passing row exists |
| D13 | Reviewer `owner` field for findings | Reviewer never ran live | A live review proposes a ShipLoop change for a harness-owned item; a missing owner must stay ShipLoop-owned |
| D14 | Codex stage rows never get an `incomplete` window (Codex events carry no turn timestamps) | Replay of both blocked Luna runs shows none; `termination.engine_unaccepted_stage` names the stage | A Codex stage comparison that needs it. The Luna close reads the termination field |

## 7. Dropped

- P14 five determinations, qualified-delivery rule, behavioral-scenario state: no consumer in code or catalog. Reopens with the first boundary or no-op case, which then declares its expected terminal behavior and source in `cases.json`.
- P15 run binding: 0 of 23 recorded results hold more than one ShipLoop run. Reopens when a result shows `shiploop.runs` above 1 (add it to the per-run scan in the callbacks plan, step 6). P15 improver scope, evaluator self-edit, read-only reviewer: adversarial, behind a human review gate, no recorded iterate run. P15 checks graded in the worktree: it would reward a run that never delivered (S-11); R2 and the recorded `worktree_checks` already explain Luna's failing checks. P15 invoked on resume: fixed and tested.
- P16 cumulative budget cap across resumes: contradicts the operator workflow where the 30-minute task limit makes `--resume-run` routine; the receipts exist. P16 CI re-read at close: the pin and start state are recorded and the orchestrating session cancels. P16 owned-effects: nothing in the harness has an external effect to reconcile. P16 reap in `launch()`: wrong premise, replaced by R8.
- P17 broken-Battleship stub guard, request-to-check map, semantic retention, judge calibration: adversarial or unobserved; recorded in R7's Limits. Reopens if a returned Battleship candidate passes all four checks yet fails the rules in review or system test (verified variant: check 4 also counts "sunk" results; rejects all three stubs and accepts the real products, not kept as code).
- P18 retention layer and adversarial review of the improver's diff: new vocabulary with no SPEC clause and no live reviewer use.
- P19 denominator report (no code computes a rate), Claude turn-unit change (no consumer; documented in R3), the roughly $28 hello A/B campaign (no decision waits on it; 9 of 12 first-pass changes fixed real defects per the journal, so the cost bought catches; same-release spread is $5.37 against $7.33), replicate meter, practical-improvement threshold (an invented number).
- P20 frozen transfer variation and extra chain or parallel runs: hand rotation across the parallel-graph cases did the job (F2); state the scope in the close instead.
- P21 decision-record machinery: a script would need thresholds the owner rules forbid inventing.

## 8. Unknowns

- U1 [I] Whether the Luna run plans a person-only case again decides a13's reading (table rows a and b). Observable in its test-strategy and system-test records.
- U2 [I] Whether the Luna run reaches a verdict without a stranding event; the 19.3 h precedent ended blocked at system-test on two human-only browser cases.
- U3 [I] Whether a host dies when its harness is killed. A python host did within 3 s in a scratch repro; no Claude, Codex or Grok host was tested. If one survives, `--resume-run` on a still-active state could start a second host on one ShipLoop run. Settle with `ps` at the next task-timeout kill.
- U4 [I] Whether Grok emits `available_commands` once per session (R4 may print a spurious lower-bound note; it fails safe, Grok is dormant).
- U5 [I] Whether Codex usage after `codex exec resume` covers only the new turn; any token sum is a lower bound until a live resume shows it.
- U6 [I] First live resume or regrade on Codex should print "plugin PASS"; the first launch's `invocation.json` shows the plugin record for $0, only a resume is the full test.
- U7 [M, workstream] Another session's seeded plain-parallel Claude run (`p1v-temperature-plain-1df460`) is the first live chain after fa231310 if its chain binds; read its `result.json` before the close says no chain has run since 1.17.0.
- U8 [I] Whether `head_files > 0` stays sound if a future ShipLoop returns knowledge-only commits first.
- U9 [I] Main CI of 3102c341 was pending when last read; any further push or release to origin/main during the batch changes the hold list.

## 9. Owner decisions

1. Branch `codex/shiploop-e2e-evidence` (6e22f287) and rev 6's "planned" status are stale. Recommend: do not merge it wholesale (eight new states, calibration receipts, a SPEC amendment that exists only there); treat this document as the current plan and borrow single ideas by trigger (D1, D13). Default if unanswered: leave the branch untouched. If it is merged, R6 and D1 become regressions and every group needs re-planning.
2. Is the Luna max battleship (hours, no dollar cap) wanted in this batch? It is the only run that can exercise a13. Default: yes, `--timeout 36000` and at most one `--resume-run`. If declined, the hello gate alone verifies the harness and the release, and a13 ships labelled not exercised.
3. a13 is uncommitted in `a13-33dbfd`. Only its session can commit it, rebase it on 3102c341 and say its adversarial review and non-regression statement hold. This plan neither commits nor merges it. If it is not ready at step 3, release A1 alone and skip the Luna run (decision 2).
4. Will `iterate.py` run in or right after this batch? If yes, promote D1 into chain A ahead of the release (minutes of work, test-only).
5. SPEC anchor for "an unreported measure is unknown, never zero" (R3, R4). Default: no amendment; cite the S-7 row, S-12 and "How the harness checks the clauses". If you read change admission as requiring an S-n, add one sentence to SPEC in its own commit before R3.
6. M1 (D6) timing. Default: after the batch, so the gate's Claude failure column reads "unmeasured". To measure it at the gate, M1 lands after R4 and delays the gate by its own admission.
7. Baseline policy for a failed or blocked row (D5): skip it (clean comparison) or keep it (A2 intends stage-wise comparison of a stopped run). Not needed until a printed comparison meets such a row.
8. Operator action, not done here (this pass is read-only): kill the two leaked servers (pid 63872, pid 83695) after confirming their cwd is under `/Users/dadleet/e2e-runs/20261003/batch-sonnet/`. The $28 hello A/B stays dropped; it is yours to buy if a cost question ever needs it.
