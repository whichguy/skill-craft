# ShipLoop planning phase: what the project has measured and decided

Digest for a later analysis, so it does not re-propose rejected ideas or ignore evidence. Read-only research; nothing in the repo was edited. As of repo HEAD `d47d69d4e82ed05a53f7a9d5f0b9ec3736941bed` (git dates run to 2026-10-31).

**Citation forms.**
- `path §heading` is a file under /Users/dadleet/src/skill-craft (docs/, test/, skills/).
- `commit <40-hex>` is the full commit message (`git show -s`).
- `LEARNINGS` is test/shiploop_e2e/LEARNINGS.md (entry title quoted).
- `mem:<name>` is a note in /Users/dadleet/.claude/projects/-Users-dadleet-src-skill-craft/memory/. These are the owner's memory, not repo files: use as pointers and verify.
- Labels are the source's own: [M] measured, [D] derived, [E] estimated, [I] inferred. Every run is n=1 unless stated, and "stage times vary about 2x between runs of the same model" (docs/shiploop-fast-planning-plan-2026-10-04.md §Diagnosis, CAVEATS).

## 0. What planning is today

- The stage table has 23 stages. Prelude: intake, discovery, research, spec, test-strategy, plan, prepare. Per work item: step-plan, test-spec, validate-existing, implement, test, document, carry-forward. Then 9 outer stages. (skills/shiploop/scripts/shiploop_stage_spec.py `_ROWS`, `_check_table`.)
- Improve rule per planning stage (same file): spec, test-strategy, plan = `always`; step-plan = `first-item` (first work item and any item sent back); test-spec = none (owner, 2026-10-26); intake, discovery, research, prepare = none. Later: document = `item` (after every step), carry-forward = `last-item`, system-test-author and release-plan = `always`.
- `planning_review` defaults to `stage`; `none` drops the four reviews at spec, test-strategy, plan, step-plan (stage_spec.py `PLANNING_REVIEW_MODES`, `DEFAULT_PLANNING_REVIEW`, `PLANNING_CHOICE_STAGES`; skills/shiploop/references/run-options.md §Planning review option). The default has been `stage` since the option was introduced (commit 7317f458b33a7e464ed3d91443b07d121b6cd001); the flip (I5, later PT-5) was never made.
- Backchain at plan: `--backchain-passes one|converge|none`, default `one`. `backchain-check` is structural and record-only (test/shiploop_e2e/SPEC.md S-10 carve-out 2026-10-04).
- Research/experiments: shared allowance of 15 active minutes, 64 observable host actions, two capability candidates, three experiments, reserve 2 min/8 actions. It is host-accounted guidance, not enforced; reaching it stops exploration, never the run (skills/shiploop/references/research-loop.md §Budget, stopping, and convergence; skills/shiploop/references/planning-experiments.md §Scope, accounting, and recovery). Text dates from commit 674e0581a010bb83b7bb0d0dcd80468d289a63d0 (2026-09-14) and 20e648b1c5a3b579c025b17daad722c89594b9d4 (2026-09-21), and is unchanged.
- Plan Improve child may run one bounded experiment cycle and the `improve-reconcile` route (initial plan child only, only under `stage`). Planning experiments exist in every protocol-4 run because protocol 4 is the only protocol (skills/shiploop/references/planning-experiments.md opening paragraph; commit a8302f258027c901896ddbac96d3effde9f2cbff).
- The plan result carries an `assumptions` list, gated at plan only; research's decision-note list is ungated (commit 374436417328375b5ae705dc493123ad027bc875).
- Only the inner stages start script-written Until Loops (`entry_runs loop-contract` in stage_spec.py). Prelude stages do not. Until Loops in planning exist only as the Improve child and the Backchain child.
- Packet head budget: the host cuts at 20,000 characters. The plan head ends its required text exactly at the 19,500 bound (commit fdec0f6ed642165effd33be640974c9ee25c1561; docs/shiploop-planning-speed-and-caps-plan-2026-10-28.md §10 Landed). The inline step-plan head is 19,997 of 20,000 (docs/shiploop-review-after-tests-design-2026-10-27.md §9 build notes, measured at the design T integration tip, 2026-10-28). Any new planning prompt text has to fit these.

## 1. Measured time and token cost per planning stage

"Planning window" = intake to the first accepted test-spec (SPEC S-10 carve-out 2026-10-05; metrics.json `planning` block). Since 2026-10-28 it is a record, never a budget (section 4).

### 1A. Planning window by run

| Run | Model / host / effort | ShipLoop | Window (min) | Improve share of window | Output tokens | Source |
|---|---|---|---|---|---|---|
| `v1161-battleship-luna` | Codex gpt-6-luna, max | 1.16.1 (2026-10-03/04) | 647.5 of a 1,158.5-min run (55.9%) [M] | Of the 592.3 min in the five loop stages: Improve loops 188.8 (31.9%) plus opening files 29.7 (5.0%); Backchain 263.5 (44.5%, includes about 50 min of prep and result writing; the SPEC carve-out and commit 9747d7690d4cea4621c1706c60ec03c84fec4a54 say the two Backchain loops took 213 of the 647.5); producer work 110.5 (18.7%) | 3.54M for the run, 57.6% reasoning; generating 99.5% of wall clock | docs/shiploop-fast-planning-plan-2026-10-04.md §Diagnosis; commit 9747d7690d4cea4621c1706c60ec03c84fec4a54 |
| `v1210-battleship-luna-xhigh` | gpt-6-luna, xhigh | 1.21.0 (ShipLoop 0.53.0), 2026-10-05 | 375.9 (375.0 stage clock; 374.95 engine) | 203.4 (54%): 5 children, 22 passes; Backchain 64.1 (17%); other authoring 108.5 (29%) | 1,153,899 in window, 59.2% reasoning; about 55 tokens/s; a request in flight 99.3% of the window | LEARNINGS "Planning time: Luna xhigh and Grok medium on 1.21.0, and where the minutes go"; LEARNINGS "The planning block of metrics.json" |
| `v1210-battleship-grok-medium` | grok-4.7, medium | 1.21.0 | 72.7 (71.88 engine / 72.59 host) | 42.4 on the children clock (58%), 45.82 on the exporter clock: 5 children, 26 passes | 274,906, 38.7% reasoning | same two entries |
| `v1220-battleship-grok-medium-none` | grok-4.7, medium, `planning_review none` | 1.22.0 (ShipLoop 0.54.0), 2026-10-06 | 22.05 host / 20.5 engine; 52 of 52 actions, no revise | 0 | 86,986, 43% reasoning; whole run 93.6 min, $12.50 (host-reported lower bound) | docs/planning-time-analysis-2026-10-06.md §Bottom line |
| Grok `none` | same | 1.23.0 | 19.23 host / 18.68 engine (the 2026-10-07 batch-1007 entry gives planning 17.5 min for what appears to be the same cell, `v1230-battleship-grok-none`, without stating its window definition) | 0 | 89,994, 43.7% | LEARNINGS "The planning block of metrics.json"; LEARNINGS "Node Battleship from the batch-1007 build, Sonnet (checks on) and Grok 4.7 medium (checks off)" |
| Sonnet 5.5 battleship | claude-sonnet-5-5 | 1.22.0 / 1.23.0 | 7.32 engine / 7.40 host; 6.47 / 6.57 | 4.04 (5 children); 2.57 | not measured | LEARNINGS "The planning block of metrics.json" |
| Sonnet 5.5 battleship | same | 1.16.0 | about 4.8 min, 83 turns; stages 0.3 to 1.4 min each; whole run 19 min | 24 Improve passes in 5.6 min (0.23 min per pass vs 8.8 on Luna) | not measured (plan document 0.8 KB vs Luna's 32.1 KB) | docs/shiploop-fast-planning-plan-2026-10-04.md §Diagnosis NOT PACKETS; LEARNINGS "Planning-size audit" |
| Codex gpt-6.1-terra, xhigh (R1, hookless) | Codex | pushed tip 8a8f1e59361c4699019b92be3309570bd5f5a940 (2026-10-29) | 5.6 / 4.5 / 4.7 (user-listing / ticket-assignment / ticket-escalation) | 2.3 / 1.3 / 1.4 (29-41%) | about 21,000 for the first planning window, 4% reasoning | LEARNINGS "R1: the same three cases on the pushed tip" |
| Terra, hooks on, Wave A before / after | Codex | 8dde0855a3ece23119cf1d172393e0c64ab3f797 / 9147dcca8e260a8fcf03712b5594f16ea702025a | before 4.3, 4.1, 5.0; after 4.2, 4.2, 7.0 | before 1.9, 1.3, 2.3; after 1.8, 1.5, 3.2 | not measured | LEARNINGS "Wave A before and after: size caps, coverage at plan and the UI criteria"; commit 008feae5295e1cee3f069f04aec6fec38ac6adb1 |
| D7 before-runs | DeepSeek flash on Ollama (Claude host) | pin 8aa6e1fe69478ccf8f8923948765a762fc3db93c | 17.4 / 30.1 / 48.7 | 10.0 (58%) / 17.2 (57%) / 25.7 (53%) | not measured | docs/shiploop-planning-speed-and-caps-plan-2026-10-28.md §2; commit fa7a892169aaccbae63f549964f3cda40ee62413 |
| `chess-sf-full-05fe25b` (chess run 3) | grok-4.7 medium, Salesforce | 2.7.0 (2026-10-19) | outer planning (intake to prepare) 59.4; through W1's first test-spec 78.8 host / 78.1 engine | 46.6 in 5 children | not measured | LEARNINGS "The Salesforce chess case, live run 3: a resolved send-back and a clean context-gap recovery" |
| `haiku55-max-battleship-d521a8` | Haiku 5.5, max | checkout eedb4a19afb4b056706e3c41a5d19b7cb9e8aa45 | reached spec at about 7 min; the spec Improve child ran 12 passes in about 22 min and never ended; owner stopped it at 34.6 min | n/a | not measured | LEARNINGS "Haiku 5.5 at max effort on Battleship: stopped in the spec's Improve loop" |

Spread to keep in mind: the journal's planning-review cost finding gives the same Sonnet battleship case as 53.3 "planning minutes" on ShipLoop 1.16.0 and 4.9 on 1.17.0 (docs/shiploop-improve-value-journal.md F6); stage times vary about 2x between runs of one model.

### 1B. Accept-to-accept minutes per stage

| Stage | Grok medium 1.21.0 | Luna xhigh 1.21.0 | Luna max 1.16.1 | Grok `none` 1.22.0 |
|---|---|---|---|---|
| intake | 2.1 | 2.5 | 4.1 | 2.56 (1.55 before the engine exists) |
| discovery | 1.8 | 10.6 | 12.7 | 1.37 |
| research | 2.1 | 10.1 | 24.7 | 2.82 |
| spec | 20.0 | 55.0 | 52.7 | 1.72 |
| test-strategy | 19.6 | 79.8 | 94.3 | 1.08 |
| plan | 12.2 | 121.0 | 196.4 | 8.38 (38% of window, 41% of output tokens) |
| prepare | 0.7 | 14.7 | 10.4 | 1.07 (prepare plus select-work) |
| select-work | 0.3 | 2.7 | 3.3 | |
| step-plan | 9.4 | 38.7 | 187.7 | 2.25 (one 94 s request, 70% reasoning) |
| test-spec | 4.5 | 39.9 | 61.2 | 0.80 |
| window | 72.7 | 375.0 | 647.5 | 22.05 |

Sources: docs/experiments/shiploop-planning-time-20261005/stage-clock.md; docs/planning-time-analysis-2026-10-06.md §1. Luna max step-plan: 187.7 accept to accept; head to complete is 163.9 min, of which the whole Backchain loop alone is 135.8 (docs/experiments/shiploop-step-plan-minutes-20261004/step_plan_minutes.py docstring; docs/shiploop-i2b-trim-planning-prompts-plan-2026-10-04.md §Goal and evidence). metrics.json's 1,679.5 s for this stage was wrong (LEARNINGS, "superseded 2026-10-04").

### 1C. Improve review minutes per planning stage

- Grok medium 1.21.0: spec 15.2 (9 passes), test-strategy 13.1 (7), plan 5.2 (4), step-plan 6.4 (3), test-spec 2.5 (3); total 42.4 (26 passes). Luna xhigh: spec 44.5, test-strategy 61.1, plan 56.9, step-plan 26.7, test-spec 14.2; total 203.4 (22 passes). Per pass: about 1.6 min on Grok, 9.2 on Luna (docs/shiploop-planning-review-plan-2026-10-05.md §Summary; stage-clock.md).
- Luna max 1.16.1: Improve passes 4/11/3/3/5 at spec/test-strategy/plan/step-plan/test-spec; Sonnet 3/3/3/1/3 (LEARNINGS "Planning-size audit").
- One-item plans, 17 runs: spec 3.2, test-strategy 3.0, plan 2.2, release-plan 1.2 minutes per run. The four planning reviews total a median 3.5 min per run (210 s; range 62 to 3,199 s; 14.2% of active time). Median seconds by model: Claude 181 (12 runs), Grok 580 (2), DeepSeek 1,112 (2), GPT-6 Luna 1,159 (1) (docs/shiploop-improve-value-journal.md F6).
- 25 runs, 520 passes: planning-stage Improve is 369.3 of 793 Improve minutes (47%), step-level planning 120.5 (15%), build and carry-forward 303.5 (38%) (F10). Improve is a median 28.1% of a completed run's stage time (8.7% to 43%, 22 runs), not "about half" (F4); the owner's "about half" is Improve's share of the D7 planning window, 53-58%.
- Design T's table: Improve is a quarter to two fifths of a run; planning reviews are 40-58% of Improve, end-of-work 19-44% (docs/shiploop-review-after-tests-design-2026-10-27.md §3.4).
- Plan-sizing slices (Grok 4.7, seeded at and stopped after step-plan): the step-plan Improve child took a median 8.2 of 17.1 min (51% of slice time) over 80 slices and changed no step count (docs/shiploop-plan-sizing-journal.md F31, F34).
- Chess run 3: Improve took 98.9 of 236 min (42%) across 16 children and 52 passes. Step-plan reviews took 10.3, 5.2, 11.0, 5.5, 13.6 min on five visits; test-spec 3.6, 1.0, 3.2, 3.3 (commit f368dfa265e2b369fb85399c1941fa21524fd335). 11 of 16 children ended on a second trivial pass that only confirmed the first (about 20 min) (commit 5e377ff70d8dde2c5b92c4dafe3e02f28f2584bd).
- Spec stage authoring vs its review in D7: spec written in 0.5-1.4 min, reviewed in 2.2-7.5 min (LEARNINGS "Brownfield D7 before-runs").

### 1D. Tokens and where planning time goes

- Time is output tokens: Luna emitted 1.15M in the window at a constant ~55 tokens/s (OLS 55.6, R2 0.993); every ShipLoop command together ran about 10 s. Grok: about 80 tokens/s. Prompt size is not the lever: input context is 3.3% of latency, Sonnet runs the identical packets in 4.8 min (docs/shiploop-fast-planning-plan-2026-10-04.md §Diagnosis; docs/planning-time-analysis-2026-10-06.md §1).
- Luna xhigh intake, discovery, research, prepare and select-work took 131k output tokens (41.5 min) to produce about 5.5k tokens of final text; the planning documents (116 KB, about 29k tokens) were rewritten about 3.1x; retries/refusals ~14.2 min, compaction recovery at most 32, kill recovery 12-24; at least 285 min remain with all of it removed (LEARNINGS "Planning time ...").
- Grok `none`, 22.05 min: generation 18.05 (82%), tools 2.5 (11%), one compaction 1.47 (6.7%) [D]. Backchain loop 2.7 min [D] (3.7 with the first draft); 14,162 of the plan stage's 35,670 output tokens. Recoverable waste at most 3.3 min (15%). The host ignored the requested read `limit` on 17 of 24 ranged plugin-reference reads (cause unknown) (docs/planning-time-analysis-2026-10-06.md §1, §2).
- Backchain at plan, Luna max 1.16.1: plan loop passes 11/15/26/18/17/12/4 min = 103 by the ledger, 106 by file mtimes (commit 9747d7690d4cea4621c1706c60ec03c84fec4a54 quotes 12/15/26/18/20/10/5 for the same loop). On 1.21.0 the one-pass loop took 23.5 min against 105.7 over 7 passes (commit a9f592a3a35c91981e1d79cd255a397e71651af0).
- Floor on Luna xhigh with no model-run Improve and no Backchain loop: 115-131 min (108.5 other authoring plus 7-22.5), so loops alone cannot reach 30 there (LEARNINGS "Planning time ..."); the later plan calls it "unmeasured, estimated at least 115 min [I]" (docs/pending-work-plan-2026-10-06.md §Dropped under KISS). Luna below xhigh has never been run.
- Packet sizes: producer packets 29-44 KB at 1.0.0 and 37/31/50/49/28 KB at 1.16.1 (spec/test-strategy/plan/test-spec/step-plan); named reading per planning stage grew 220 to 306 KB at 1.16.0 (LEARNINGS "Planning-size audit").

### 1E. Cost of the rules and caps

- Refusals per D7 run 25/27/18; size caps 3-5 per run; size-limit refusals: D7 11 of 70, R1 1 of 12, R2 4 of 9, Wave A before 2 of 11, after 0 of 13 (docs/shiploop-planning-speed-and-caps-plan-2026-10-28.md §2, §4 F2; LEARNINGS "Wave A before and after ..."). Cost of bounded-field refusals: about 1-2 min a run (docs/shiploop-deepseek-run-improvements-plan-2026-10-26.md ranked table).
- Follow-on run growth in the stages that work over living files: test-strategy 16.1 vs 7.5 min, step-plan 12.0 vs 5.3, carry-forward 14.7 vs 9.5, while environment.md grew 72 KB to 87 KB (LEARNINGS "Brownfield D7 before-runs").
- Brownfield baseline pass: 15 to 30 min scoped, 3,023 s and 273 KB whole repository, a deepen pass 2,180 s (docs/shiploop-brownfield-baseline-design-2026-10-28.md §2).

### 1F. Not measured

- Per-stage output tokens (nothing apportions a run total to a stage) (LEARNINGS "The planning block of metrics.json", Not built). Claude per-message token counts are streaming snapshots, so Sonnet tokens are unmeasured; Sonnet's 99,115 session tokens were split by tool-input share, about ±30% [E] (docs/planning-time-analysis-2026-10-06.md §3).
- Escape rate and escape cost without planning review (section 6).

## 2. Measured value of Improve reviews at planning stages

### 2A. Catches per review, by stage

Chess runs 3, 4, 5b (Grok 4.7 medium, 56 reviews, 118 passes; DEFECT / STRENGTHEN / POLISH passes) (docs/shiploop-improve-schedule-proposal-2026-10-25.md §What Improve did, per stage):

| Stage | Reviews | Minutes | D / S / P passes | Reviews with a DEFECT | Share of minutes in reviews that edited nothing |
|---|---|---|---|---|---|
| spec | 3 | 36.8 | 1 / 7 / 1 | 1 | 0% |
| test-strategy | 3 | 25.2 | 3 / 3 / 1 | 2 | 0% |
| plan | 3 | 18.9 | 6 / 0 / 0 | 3 | 0% |
| step-plan | 10 | 55.8 | 5 / 5 / 0 | 4 | 12% |
| test-spec | 9 | 19.8 | 1 / 5 / 0 | 1 | 29% |
| all stages | 56 | 236.7 | 25 / 20 / 3 | 19 | 17% |

Seven runs, reviews that found something / reviews, columns runs 3, 4, 5b; DeepSeek hello; DeepSeek battleship; Sonnet hello; Sonnet battleship (the first column counts reviews with a DEFECT, the others "effective" reviews, meaning at least one non-trivial pass that changed lines) (docs/shiploop-deepseek-run-improvements-plan-2026-10-26.md §Related evidence): spec 1/3, 1/1, 1/1, 1/1, 1/1; test-strategy 2/3, 1/1, 1/1, 1/1, 1/1; plan 3/3, 1/1, 1/1, 0/1, 1/1; step-plan 4/10, 0/1, 2/2, 0/1, 1/1; test-spec 1/9, 0/1, 2/2 (one only confirmed scope), 0/1, 0/1. Summary: test-spec 2 real catches in 14 reviews; "no stage is useless everywhere"; in DeepSeek hello 4 of 14 non-trivial passes repaired an error an earlier pass of the same review introduced (commit 832536362c1c78c621686e8b8c59096f4feb0915).

25 runs, 275 children, 520 passes, 681 findings (docs/shiploop-improve-value-journal.md):
- F1 (firm): 0 of 250 planning passes (spec 94, test-strategy 67, plan 47, release-plan 42) touched a product file; 166 edited records. True by construction (planning reviews are scoped to records, F12), so "did it change the product" cannot justify skipping them.
- F5 (interim): 469 planning findings acted on: 139 contradictions or checks that cannot be replayed (30%), 199 missing content (42%), 65 stale or wrong references (14%), 45 defects in what the record tells a later stage to do (10%), 21 polish (4%).
- F6/F7/F8: per-stage findings per minute on one-item plans: spec 1.28, test-strategy 1.13, plan 0.51 (19 findings in 17 children), release-plan 1.12. 23% of record-only fixes (49 of 215) are made after planning. Passes 2 and later of a planning review find 26% of the fixes in 29% of the time (pass 1: 68 passes, 123 fixes, 115.4 min; later: 67 passes, 43 fixes, 46.5 min).
- F3/F11: product yield scales with plan size: behaviour passes among build and carry-forward 0 of 27 (1 item, 1 step; seven hello runs), 15 of 72 (1 item, 2+ steps), 25 of 90 (2+ items).
- Conclusion (interim): "the data neither support nor refute skipping the planning reviews on one-item plans"; cost is priced (median 3.5 min, 14%), benefit is not (no run has them off). Commit f35f73cae36af0bff38a3b0683d37deb49860c56.

Per-model catches at planning:
- Luna xhigh: 22 passes gave 5 warranted fixes, 5 minor, 2 corrections, 10 no change [ledger F10, interim]. Grok medium: 26 passes, 4 fixed a real defect, 6 marginal, 4 churn, 12 no change [I]; its spec review took 9 passes and four consecutive commits widened one import allow-list. 1.16.1 max: first passes found warranted defects in 6 of 9 children; 13 of 32 later passes changed something (3 warranted, 7 marginal, 3 churn) (docs/shiploop-planning-review-plan-2026-10-05.md §Quality).
- Sonnet 5.5 battleship (1.16.0), commit `b1e196d` in that run's own work repository (not in this repo; its message is kept in docs/experiments/shiploop-planning-review-20261005/sonnet-plan-review-b1e196d.txt): plan review "plan lacked an importable server design" (a related class [I] to the Luna defect that cost 165.9 min). Its five planning children took 13 passes in 125 s (about 4 s each, about 270 B of review text, so not a like-for-like benchmark).
- E6b (Sonnet, condensed packets, 3 trials per cell, shared-gap judge): planning review with the platform-claim bullet caught 10 of 15 real plan-stage platform errors vs 0 of 15 without; rerun on shipped text again 10/15 (docs/shiploop-composition-state-experiments-2026-09-26.md §E6 and E6b, §After implementation).
- Late stages do not substitute: verify, integrate, integration-verify, product-acceptance found nothing in the Grok `none` run; product-acceptance add-work 0 of 8 and release-verify failures 0 of 8 in fidelity runs (docs/planning-time-analysis-2026-10-06.md §4; docs/shiploop-sdlc-gates-proposal-2026-10-30.md §2b). Undetected defects are "unmeasured, not zero".

### 2B. Decisions the project took from this

- 2026-09-24: Improve not after every stage ("~10 of ~16 two-pass review cycles changed no product file (~1 h); only contract-sentence reviews (step-plan, test-spec) found bugs"). Same day the owner kept planning-stage reviews: 0.22.0 `planning-and-end` default; then 0.23.0 one schedule, no cadence flag (commits 4af28a7ee6776cd4429e748c161bf2310efce8d2, 47bba5203cdb37b492bf092af1eefdf3a2e57f27, b960891b8fdb2b47e85eca1beeb113c827bb6664; mem:shiploop-plan-and-end-cadence-2026-09).
- 2026-10-04: planning-stage Improve left at full gate (D4: "3 warranted, 7 marginal, 3 churn of 13 changing later passes"), superseded 2026-10-05 by `--planning-review stage|none` (docs/shiploop-fast-planning-plan-2026-10-04.md §Owner resolutions, §Other cuts c6).
- 2026-10-05: `planning_review` built (landed I3 e11b86ef31aab4067ac7b09ee2c13cc508c46621, I1 7317f458b33a7e464ed3d91443b07d121b6cd001, I2 f6ed230ffa09365a96cb6c7aa269451b242d714d, R1 17cded5acd6103f57ef09e22578e6efa2cfaa3c5), default stays `stage`; SPEC S-10 second carve-out (commit 6db8ef7acdf1747d719fff87a4861822a7bd777d).
- 2026-10-19 `first-item` (step-plan and test-spec reviewed only for the first item and after a send-back; owner "do 1"; commit f368dfa265e2b369fb85399c1941fa21524fd335). 2026-10-20 Improve completes at its first trivial pass (owner: "the current criteria may iterate far too often without results"; commit 5e377ff70d8dde2c5b92c4dafe3e02f28f2584bd).
- 2026-10-26 test-spec gets no Improve review ("2 real catches in 14 reviews"); implement reviewed once per item (commit 090c8c881448fd3ba4899433484e9b0633ba8d0a). 2026-10-27 wide items keep a review per changed step (999bf7d574bc3435cf5c92226ca3657d5d43458e). 2026-10-28 the review moves after each step's document stage (ddaf90760fd0035aae46d2c1591fa61dbb9dbd8b).
- 2026-10-28 F1 (plan Q2, owner-approved per docs/shiploop-improve-value-journal.md Recommendation 2): replace the reviews after spec, test-strategy, plan and step-plan with one review of the planning bundle at prepare. Not built. 2026-10-29 the stage/none experiment was held and folded into a three-arm measurement (per-stage, bundle at prepare, off), after design T and F1 (commit 45a4d2ffe9e73a028064f4f367f4ef0c9b8e8ff9; mem:improve-value-measurement-2026-10-28).
- Improve-schedule panel (2026-10-25) re-specified P1-P6: P3 no skip but narrow re-review; P4 shadow mode only; spec review stays (docs/shiploop-improve-schedule-proposal-2026-10-25.md §Panel outcome).

### 2C. What the evidence cannot say

- Recall: whether reviews miss defects that exist (journal §Limits; SDLC gates SG2 would test it). No counterfactual: "no run without planning reviews exists" for the escape rate (SPEC S-10 carve-out 2026-10-05). Greenfield only; model, host and version vary across runs (1.8.0 to 1.17.0).
- Spec and test-strategy finish before the plan exists, so a rule keyed to plan item count can only govern the reviews from the plan onward (journal F12.5).

## 3. Quality failures traced to planning

| Failure | Run / date | Planning origin and cost | Source | Fixed by |
|---|---|---|---|---|
| Tests had no real module to load; test-red revised, planning redone | `v1210-battleship-luna-xhigh` (2026-10-05) | Redo 165.9 min of stages vs 99.2 first pass (28% of the run); step-plan redo 120.1 vs 38.7. Review at planning missed it. The 1.16.1 run had a 123-min (123.4) implement revise of an analogue (a test contradicting its own helper) | LEARNINGS "Planning time ..."; docs/lifecycle-review-2026-10-07.md §1 item 4 | Test-author probe (commit e11b86ef31aab4067ac7b09ee2c13cc508c46621); the analogue is "not covered" |
| Unprobed host tool; access gap found late | `v1230-battleship-grok-none` (2026-10-07) | test-strategy probe was `Chrome --version`; gap surfaced at W2 implement (~50 min in), deferred to system-test, run blocked at 101 min | LEARNINGS "Node Battleship from the batch-1007 build ..." and the 2026-10-08 investigation | test-strategy Done-when asks for a probe of each host tool (commit e25da2e44ab8bd94de6ff908765d6dbf60daf1b5) |
| Plan said ESM in a repo with no package.json | `v1220-battleship-grok-medium-none` | "Facts the planning stages did not settle were repaired downstream" (the browser tool was also unprobed at test-strategy) | docs/lifecycle-review-2026-10-07.md §1 item 4 | batch 1007 B7 settled-fact lines: plan states each item's module format and loadable seam, test-strategy names and probes the host-browser tool (docs/shiploop-batch-1007-plan-2026-10-07.md §Items B7). Live check: Grok planned the browser case as its own `check` command (LEARNINGS "Node Battleship from the batch-1007 build ...") |
| Step Proof ran a test file that only the later test stage writes; send-back | `ds-flash-978478-battleship` (DeepSeek flash, 222.4 min) | about 24 of 222 min (11%), one send-back (separately, 17 length refusals over the two DeepSeek runs) | docs/shiploop-deepseek-run-improvements-plan-2026-10-26.md §1; commit 832536362c1c78c621686e8b8c59096f4feb0915 | SG1 replay tool; the step-plan refusal (D6) waits for the owner's saved runs |
| Same class: S3's proof needed castling "before S4 adds castling" | chess run 5b | review found it | docs/shiploop-improve-schedule-proposal-2026-10-25.md; docs/shiploop-sdlc-gates-proposal-2026-10-30.md §3 row 16 | open (SG1) |
| Hand-derived expected value illegal (TC_28 move sequence) | chess run 5b W1 | implement found it only after a deploy; item lost about 6-10 min | docs/shiploop-improve-schedule-proposal-2026-10-25.md §P2 | PROCEDURE_WALK check (panel), commit abdb0fdd8b3206e3458603c2cefc87c6326ac556 |
| Stage texts let generic holes through: behaviour checked by grep, stateful remote target dropped, vacuous negative tests, Improve fixes without tests, acceptance on source words | `chess-sf-full-9e52e8` (run 4), graded B- | Q1, Q3-Q7 | commit 9ed4ec24f8481a1841820033a35d31804ebb9dab | stage text edits; `primary` requirements (commit f9d1f4cf732e9d63b46349c69e7cec3b6207995e) |
| Step-plan concern surface ungated; all four step-plan results skipped or compressed it; concurrency and accessibility (100 unlabeled cell buttons) dropped | chess `salesforce-chess-int-802e29`, Battleship `bs-sf-int-b7c77f` (2026-10-17/18) | "No SDLC dimension is checked by a gate at any stage" | docs/shiploop-run-insights-plan-2026-10-18.md §2 | concern map (commit fff7fa13fd537d7152e9d71a476b716e4f5e6839) |
| Step plans with no criteria or paths; test-only step a no-op every time | four live step slices (2026-10-10) | implement grepped the step-plan file for its own work | commit 0e36a9af11aaf828880a73aa266ed7dea427eb6c | step sizing gate |
| Oversized steps | Grok 4.7: 14 of its 20 full-run items one step, up to 12 criteria; all 8 Salesforce chess items one step; chess run 4 W1 S1 7 criteria, 793 lines, 5 files, 21.4 implement min. Sonnet: 39 items, median 3 steps | all 95 implement receipts end at iteration 1 | docs/shiploop-plan-sizing-journal.md §1 F1-F8 | step bound shipped 2.11.0 (section 4) |
| Opposite: many tiny steps | E6 Cg K2 sample 2 planned 10 one-criterion steps | in band, unpriced | plan-sizing journal F30 | none; E6D2 priced it (faster) |
| Three-step plan collapsed to one after a revise | chess `salesforce-chess-int-802e29` (2026-10-17) | check commands were item-wide, not step-scoped | mem:todo-step-series-order | per-step iteration (commit ddaf90760fd0035aae46d2c1591fa61dbb9dbd8b) |
| Unreachable criteria causing send-backs, "a measured cost in run 5" | chess run 5 | send-back to step-plan; "check that each criterion is reachable before implement" was a next-batch candidate | docs/shiploop-deepseek-run-improvements-plan-2026-10-26.md §1; mem:run5-batch-2026-10-24 | open as SG1 |
| W1 `test` stage hit a failing base-gate check (`W1-root`); step plan sent back to step-plan, the first live four-outcomes send-back; resolved | `chess-sf-full-05fe25b` (chess run 3) | W1 took 51.8 min including the send-back cycle | LEARNINGS "The Salesforce chess case, live run 3 ..." | none needed |
| Primary coverage gate attached a test to a step whose intention it was not | D7 runs (DeepSeek) | "Missing: R-20. Add a case ..." | commit fdec0f6ed642165effd33be640974c9ee25c1561 | coverage moved to plan (F3) |
| Requirement left unnamed by any case; requirements about the tests had no case | Sonnet hello R-1; Sonnet battleship R-6; DeepSeek hello R-2; Grok hello R-2 | an end-of-run coverage check would have refused 5 of 8 runs for honest work | docs/shiploop-judgement-stage-checks-proposal-2026-10-26.md §0; commit 70d88d379fece7457b9136b39ab8d586fd43cdae | TS1, then F3 |
| Intake did not ask about persistence (3/9), hidden information (0/9), sign-in (0/9) | prompt experiment E3, "Build a Battleship game" | "no stage asked" | docs/shiploop-composition-state-experiments-2026-09-26.md §E3 | intake paragraph; shipped text 9/9, 9/9, 7/9 |
| Open questions retained in all four pilot arms; more investigation cannot resolve an unavailable owner decision | research pilot (2026-09-13) | guidance now names the next useful action | docs/shiploop-research-pilot-closeout.md §Prompt audit Q2 | wording |
| Baseline-arm plan missed two facts its own 61 KB baseline states | brownfield X3 on healthchecks | "A file in the repository is not consumed; a quoted, numbered question is" | docs/shiploop-brownfield-baseline-journal.md §X3 fact coverage | D9 (Q-<n> quoted by value), held |
| Plans assumed a migration artifact existed; duplicated checks in a tests-only item | planning breadth study (Grok 4.6, 2026-09-20) | baseline failures | docs/experiments/shiploop-planning-20260920/README.md | planning guidance |
| Spec Improve never converged | `haiku55-max-battleship-d521a8` | 12 passes of 1-9 line tightenings | LEARNINGS "Haiku 5.5 at max effort ..." | none; stop rule is the model's judgement |
| Decision in prose went stale after an Improve review | Checkers (1.27.0) | multi-jump decision in summaries stayed "mandatory"; no structured open-question field | docs/shiploop-artifact-flow-2026-10-11.md §3, §4 rows 3, 7 | consumer contract |

Not found: any measured case of a planning-origin defect that a late stage (verify, acceptance, release) caught after planning review was off; the escape rate is unmeasured (docs/planning-time-analysis-2026-10-06.md §4).

## 4. Decisions already taken about planning

Owner words are quoted where the source quotes them. "Superseded" lines name the later decision.

### 4A. Time, caps and ceilings

| Date | Decision | Status | Source |
|---|---|---|---|
| 2026-09-26 | ShipLoop loops have no iteration limit; the per-stage loop limits (quality 3, tests 4) were wrong | in force | mem:shiploop-loops-unbounded; commit b7653edc57ccb74e81b02e065336b66c8f6273f (run quality and test loops without an iteration limit) |
| 2026-10-04 | Luna E2E at xhigh; Backchain at plan one pass (owner: "only 1 pass"); S-10 carve-out | in force | docs/shiploop-fast-planning-plan-2026-10-04.md §Owner resolutions; commit 9747d7690d4cea4621c1706c60ec03c84fec4a54 |
| 2026-10-05 | Planning "alarm": first 7 min, corrected the same day to "anything where planning takes more than 30 minutes" | superseded 2026-10-28 | mem:planning-seven-minute-ceiling-2026-10-05 |
| 2026-10-28 | Owner: "I don't want to have a 30-minute planning session at all." The window is a record, never a budget; D6 (discovery charged to the window) withdrawn; plan Q1 recommends no figure in prompts or code | in force | commit 280b54d635aadd332337c99feebaf2e8f3eb7a83; SPEC S-10 carve-out 2026-10-05, amended 2026-10-28 |
| 2026-10-10 / 2026-10-24 / 2026-10-28 | Caps 11/7/22 raised, then "Remove any other artificially imposed limits by our scripts"; the "7 genuine fix attempts" count became a criterion (STUCK_FIX) | in force | SPEC S-10 carve-out 2026-10-10; commits fd60477f87dfc0e1495efc7bd4bf03c6e3776e0f, 337b09c5417f81a8949a4ee8351361baa373ea79 |
| 2026-10-28 | Owner: eliminate arbitrary small caps hard-coded in prompts or code; spill long model text to files | refusing caps removed 2026-10-29 (F2); safety guards stay | docs/shiploop-planning-speed-and-caps-plan-2026-10-28.md §4 F2, §10; commit 232689c5c18eccc2dc38c0cf869cecca4e511947; mem:no-arbitrary-small-caps |
| 2026-10-28 | Note: F2's inventory scans `skills/shiploop/scripts`; the research allowance numbers in the reference prose (15 min, 64 actions, 2 candidates, 3 experiments) are not in it, and I found no later decision on them | gap, not a decision | research-loop.md §Budget; plan F2 |

### 4B. Improve reviews at planning

See 2B. From docs/shiploop-planning-review-plan-2026-10-05.md §Owner resolutions and §Alternatives: not built (D2) are `once` (one review of spec+test-strategy+plan at `plan`; even if free it leaves at least 36.5 of Grok's 72.7 min) and a `plan` value; rejected (D4) is the per-item merge of the step-plan/test-spec review (a child bound to test-spec cannot amend the step plan; the Luna redo's step-plan took 120.1 min against 38.7); a host-sensitive default is a new engine surface (pass `none` by the case prompt instead); out of scope for that change (D9, D10) are an end-of-work review carrying the planning documents, L1 replacement review, L2 single pass, L3 one review at the end of planning, L11 script lint of documents, L17 a cheaper revise path, and `--backchain-passes none` as the default. Pending PT-5 "flip the default to none" is conditional on a pre-registered rule (both Grok none wide windows at most 30 min; no revise at first test-red; Sonnet hosts accept losing the `b1e196d` catch for about 2 of 4.7 min); not executed (docs/pending-work-plan-2026-10-06.md §Wave 4, §4 decision 1). The owner's later Q2 (bundle review) is the live direction for planning review.

### 4C. Key questions, research, experiments

- Intake lists open questions with owner and what each blocks; discovery answers each from a source or keeps it unknown; research resolves consequential unknowns; the plan gates the assumption list (stage_spec.py done_when; shiploop_prompts.py DUTIES intake 2, discovery 14, research 11).
- 2026-09-18 research cue: four paired experiments, four ties; the 66-word candidate was not adopted; no blanket preflight experiments (docs/shiploop-probe-decisions-results-2026-09-18.md).
- 2026-09-21/22 planning experiments pilot: both arms found the same two planted mistakes; no candidate-only consequential improvement; default change not justified; the opt-in V4 transition was kept. The design's adoption bar was two distinct consequential improvements, one replicated (docs/shiploop-planning-experiments-results-2026-09-21.md; docs/shiploop-planning-experiments-plan-2026-09-21.md §Validation and adoption). Zero experiments is valid; "a task can legitimately require zero experiments".
- 2026-09-25 assumption list: research and plan exit on it; enforced at plan only (commits 122db27ac993ac9df48abce17e09cd1b70902654, 2f12d3ae8aa3c8e3e02b62d3d8c24a0c6298caed, 374436417328375b5ae705dc493123ad027bc875).
- 2026-09-27 unattended default (owner): an open decision takes a recorded default; pause only when nothing can proceed (commit e7a8c86bb129c905557be16a86fe37517284cbf6). A spent investigation allowance stops exploration, never the run (commit a6aa09a99a845c336ef44f1c3947493cbc832e33; a Luna seat-reservations run had paused on it).
- 2026-10-11 owner TODO (planning research loop): initial plan, key questions, research Until Loops, optional experiment Until Loops, revised plan and test spec. Status: not started, needs an owner go on a design (mem:todo-planning-research-loop). Related accepted piece: brownfield D9, open questions as `Q-<n>` quoted by value and answered by ID (docs/shiploop-brownfield-baseline-design-2026-10-28.md §9), but its build (§10) is held.
- 2026-10-30 SDLC gates: "Ask one-way questions at intake; spec lint" dropped (P9, checks never judge prose); unmeasurable criteria already an Improve duty (docs/shiploop-sdlc-gates-proposal-2026-10-30.md §3 row 8).
- Open-item gaps named, unbuilt: X1 (open items due at a stage are not checked), X2 (research cannot record access needs it must), DI1/RE1 checks for discovery and research (docs/shiploop-judgement-stage-checks-proposal-2026-10-26.md §1, §4). The stages "intake, discovery, research" end on the model's word except IN1 (every request sentence cited; commit 70d88d379fece7457b9136b39ab8d586fd43cdae).

### 4D. Merging, splitting and adding planning stages

- 2026-10-05: per-item merge of step-plan/test-spec review rejected (above).
- 2026-10-07 lifecycle review proposed merging redundant stages (select-work, baseline, test-red into test-author, skill pair, operations into handoff, release-check, intake into discovery "weakest case", prepare script runs smoke) taking a small local build from 34 to about 24 stages, saving roughly 15 to 20 of 93.6 min [E, single run]. docs/lifecycle-review-2026-10-07.md §2, §5. The batch built from it left the merges out: "Not in this batch: merging test-red, integrate, release-check; script-first test-green and regression (S-10 decision); ... the Backchain pass itself; the default planning-review flip" (docs/shiploop-batch-1007-plan-2026-10-07.md §Not in this batch). Its correctness findings were built (B1 test counter, B7 settled-fact lines, B5 rename of `select-work` to `get-next-work-item`, B9 plan-shape warning, record only). Separately, the inner loop was redesigned from 17 to 8 stages in 5 phases on 2026-10-10 (owner accepted all ten recommendations; commit d738804388a68a100a2dc9b4b0bba246fa44df22; mem:inner-loop-seven-stages-2026-10-10). Intake and discovery are still separate stages (stage_spec.py).
- 2026-10-07 main tenet (owner): assume the previous stage's context is cleared; each packet restates its stage; repetition between packets is grounding, not waste. Packet-moving proposals withdrawn (docs/lifecycle-review-2026-10-07.md §0).
- 2026-10-10/11: three living knowledge files (spec, architecture, environment) (commit 17c7fa8ef79cfd8e5827de4e43966d1828bd803b); consumer contract D1-D4 approved: quote spec/environment/architecture whole; drop `release` field; script-derived spec diff; no `surface` key (docs/shiploop-consumer-contract-2026-10-11.md §0A.3).
- 2026-10-28: a separate brownfield baseline stage rejected; the as-is account is written at discovery's close (D1; a new stage would break `RECONCILIATION_TARGETS = PLANNING_STAGES[:4]`); accepted "D1-D9", then section 10 held pending a large case (docs/shiploop-brownfield-baseline-design-2026-10-28.md §0, §9, §10; docs/experiments/knowledge-stage-review-20261028/astra-review.md for the per-step knowledge stage: option C chosen, no new model stage).
- 2026-10-28: `verify` retired; each step builds, tests, documents, is reviewed and committed before the next (commits 1d6949e880fd642042b5272c77996ab9061081d4, ddaf90760fd0035aae46d2c1591fa61dbb9dbd8b, 7bba525ed74ad436ddbbe526db029714fdec47cb).
- 2026-10-29: the implementation chain (Plan Dispatcher binding) retired (owner G1 "Adopt (a2)"; commit ad30aa1c82665435c1e69771ef079d80d7b92079). `shiploop_backchain_graph.py` (`backchain-check`) and `shiploop_planning_context.py` were left for the owner.
- 2026-10-30 SDLC gates: "No stage is missing"; the 23 stages cover more than spec-kit, Kiro, BMAD or Anthropic's harness (a claim, no per-stage table in the repo); drops: acceptance tests before the build (#4), fresh context per work item (#10), `--approve` checkpoint (#11), maintainer-merge rubric (#9), spec lint (#8); defers Tidy First, property-based cases, seams-first (docs/shiploop-sdlc-gates-proposal-2026-10-30.md §1, §3, §7).

### 4E. Plan sizing (E-SIZE1 / E6)

- 2026-10-24 owner asked whether step plans are too big. R1/R1g/R2 on Grok 4.7: a countable bound moved the engine cases (K1 control 0.25, Cg 0.75; K2 0.50 vs 0.75); K3-K7 at ceiling; the refusal gate never fired (0 in 40 samples), so prose does the work (plan-sizing journal F15-F33).
- 2026-10-25 owner: "Port Cg's sizing prose into ShipLoop's step-plan template (generic wording, no gate since it never fired)". Shipped in skill-craft 2.11.0 / ShipLoop 1.11.0 (≤4 criteria and ≤3 product files per step; companion-file clause) (plan-sizing journal §6; mem:plan-sizing-e6-2026-10-24).
- 2026-10-28 E6D2 (DeepSeek flash, 3 per arm, K2 and K4): 12 of 12 delivered; with the bound the median item was faster (K2 63 vs 124 min, K4 96 vs 124), plans narrower (5-6 vs 4-10 steps; 4-5 vs 3-6); turns -20% K2, +3% K4. Owner: "No, keep as is." E6 closed; no firming round. Don't propose more rounds unless the owner reopens (plan-sizing journal §12; mem:plan-sizing-e6-2026-10-24).
- Re-read under the later D5 permutation rule, E6-K1 T vs C (p 0.071) and E6-K2 T vs Cg (p 0.50) read inconclusive; the closure rests on E6D2, so it stands (mem note; commit a9e398e912d7cb9a7f5cb78c97e4fb18383e9342).

### 4F. Backchain at plan

- 2026-10-04: one pass default; `--backchain-passes one|converge|none` (commits a89135f76bc67482343dc711bd723113c0d69775, 0df9b0c4e8105eb7d7a1b6f664f0dcd9aceb21da, a34a6ee62fd91c6d68f4ccecf6d7a857663c5b3b, 2f091a35f45049d4e1516ddc3af91938b7d87130); loop text and resource list only at `plan` (3592b195f94f2e24b46dea80b6f217c3b62cd154). The replay before release (R0) was skipped on the owner's instruction. The evidence favoured `none` (about 34 min more saved; the plan graph is named by no later packet and not opened by Improve) but the owner's words were "only 1 pass" (docs/shiploop-fast-planning-plan-2026-10-04.md c1, c3).
- Measured: passes 2-5 each reported a confirmation-level or wording finding; no edge, goal or supplier changed after pass 1; the script check passes the plan graph before pass 1 and after every pass (§Diagnosis). Its value is "unknown" (docs/planning-time-analysis-2026-10-06.md §2).
- Left open: a02 (script-written Backchain contract) and a05 (what the plan graph is for); the comparison plan's Track 1/Track 2 (whether the loop beats a one-shot checked plan): no result recorded (docs/shiploop-planned-improvements-2026-10-04.md; docs/shiploop-backchain-validator-comparison-plan-2026-10-04.md §1).
- `planning_review none` with `--backchain-passes none` leaves no model-run second look at the plan graph; documented, not refused (run-options.md).

### 4G. Until Loops in planning

- Prelude stages are not Until Loops. The inner stages each run as one script-started Until Loop with a ShipLoop-written contract (owner, 2026-10-10: 17 to 8 stages in 5 phases; "the script-started Until Loop with a ShipLoop-written contract is the substitute" for /goal) (commit d738804388a68a100a2dc9b4b0bba246fa44df22; mem:inner-loop-seven-stages-2026-10-10).
- Primary rule (owner, 2026-09-24): a step iterates until a check confirms each exit criterion; no iteration limit (2026-09-26; 2026-10-24). SPEC S-10 relaxes it only for the one-pass Backchain child and for planning Improve under `none` (test/shiploop_e2e/SPEC.md S-10; mem:shiploop-lint-exit-criteria-2026-09; mem:shiploop-loops-unbounded).
- Improve's stop rule is one trivial pass (owner, 2026-10-20; commit 5e377ff70d8dde2c5b92c4dafe3e02f28f2584bd). The 2026-10-16 one-unchanged-pass carve-out (commit 600181522eedcfd362e8067548b07bc1c8c3e546) was withdrawn on 2026-10-18 by the owner's decision to keep the upstream Until Loop runtime byte for byte (SPEC S-10 carve-out 2026-10-05, 2026-10-18 note). A model that never judges a pass trivial never leaves the stage (Haiku 12 passes); the candidate script-side shrinkage stops "would change the unbounded-loop rule, so it needs the owner's decision" (LEARNINGS "Haiku 5.5 at max effort on Battleship ...").
- Plan-time experiments run inside one actual Until callback of the Plan Improve child: no second Until or Backchain convergence loop, no separate experiment counter, no compressing several reviews into one callback (skills/shiploop/references/planning-experiments.md §One review cycle).
- Open: nested Until Loops with first-in, last-out semantics (mem:todo-nested-until-loops); research and experiment Until Loops from the 2026-10-11 planning TODO (not started).

### 4H. Superseded rules the analysis should not resurrect

- "Every planning result gets its own Improve child" (docs/shiploop-delivery-overhead-plan-2026-09-23.md) and "Improve's planning-stage passes stay" (commit 9747d7690d4cea4621c1706c60ec03c84fec4a54): superseded 2026-10-05.
- "Every accepted implement step is reviewed" (owner, 2026-10-10): superseded by commit 090c8c881448fd3ba4899433484e9b0633ba8d0a (2026-10-26), amended 2026-10-27, replaced 2026-10-28.
- TS1 (test-spec covers every primary requirement, commit 70d88d379fece7457b9136b39ab8d586fd43cdae): replaced by coverage at plan (commit fdec0f6ed642165effd33be640974c9ee25c1561) on the owner's "tests relative to each step's intention".
- The Pace row forecast removed 2026-10-08 (forecasts 2.4x to 6.8x off) (LEARNINGS "The narrative's Pace row records and no longer forecasts").
- A tests-first ordering: "Tests follow implement" (owner 2026-10-10, 2026-10-27); tests-first redos cost 123 and 165.9 min.

## 5. Open owner TODOs and proposals in flight (as of HEAD)

| Item | Status | Source |
|---|---|---|
| Planning research loop (plan, key questions, research and experiment Until Loops, revised plan and test spec, build, test) | Not started; needs a design and an owner go | mem:todo-planning-research-loop (2026-10-11) |
| F1 bundle review at prepare (replace four per-stage reviews) | Approved 2026-10-28, not built; three-arm measurement (per-stage, bundle, off) planned after design T (landed in release 9d8c27936a70627fc96880db16897d7f3de4d3bd) and F1; rule fixed beforehand: an arm replaces per-stage if every run finishes and passes and behaviour changes and release-stage failures are no worse beyond the gap between per-stage runs 1-2 and 3-4; hidden checks stay 43/43 | docs/shiploop-improve-value-journal.md Recommendation 2; docs/shiploop-planning-speed-and-caps-plan-2026-10-28.md §4 F1 |
| Wave B: F4 (living files rewritten, not appended), F6 (Improve-only `improve-done` verb); P6 large brownfield case; brownfield section 10 (as-is account) | Open; Q5 holds the account until a large case shows a gap | plan §8, §6; brownfield design §10 |
| `planning_review` default flip (I5/PT-5), M1-M4, PT-2/PT-3 | Owner's later decision; no M2 or M3 result found | docs/shiploop-planning-review-plan-2026-10-05.md §Measurement plan; docs/pending-work-plan-2026-10-06.md |
| SDLC gates (today): Track A probes P1-P7 | Built as a reader (P4 not built); no run read yet | docs/shiploop-sdlc-gates-proposal-2026-10-30.md header, §4; docs/experiments/sdlc-gates-20261030/README.md |
| SG1 proof-order replay at step-plan; D6 adds the refusal if the bar is met | Replay tool built; verdict needs the owner's saved runs (this container has none) | same, §5, §7 |
| SG2 review recall, inline vs fresh (D3, D3b) | Declared on main (commit f8eec07c622b745db5892b176ace1e821c8b396d), not run; waits for a Codex Terra host | same |
| AS1: does the Apps Script card's Testing section change what test-strategy declares | Experiment built 2026-10-31, nothing has run live | commit 5ca57d9e98095ac59a3c2c47f818a670d7023ba5 |
| Stage suite (per-stage oracle/scenario harness) | Core on main; three validate-existing scenarios | commit c8af6a5c19b307fa8acb15e717dd9ef60c59eb6b; docs/shiploop-e2e-closed-loop-plan-2026-10-30.md |
| Judgement-stage checks: PA1', ST1, X1, HO2, X2, DI1, RE1 | Not built; wait for evidence a gate binds a real run | docs/shiploop-judgement-stage-checks-proposal-2026-10-26.md §0, §4 |
| Backchain a02 / a05; Track 1/2 comparison; remove or keep `shiploop_backchain_graph.py` | Open | docs/shiploop-planned-improvements-2026-10-04.md; commit ad30aa1c82665435c1e69771ef079d80d7b92079 |
| Nested Until Loops (FILO) | Open on purpose | mem:todo-nested-until-loops; mem:until-loop-exit-checks-0-8-0 |
| Stateless skill (model never holds graph state) | Not started | mem:todo-stateless-skill-report-done |
| Cached stack references; design/investigation prompt skill | Open TODOs | mem:todo-cached-stack-references; mem:todo-design-investigation-prompt-skill |
| Document-stage proposals P1-P3, P5 and the pause-on-convention prompt change | Await the owner | mem:document-stage-review-2026-10-30; LEARNINGS "Wave A before and after ..." (one `shiploop pause` at step-plan) |
| D5 default of 4 samples per arm for `decide` | Owner's call (8 per arm needed for a moderate gain) | mem:test-stage-prompt-design-2026-10-30 |
| Improvement backlog candidates for planning: merge/skip early stages for small requests (L6) or lower effort there (L9); Luna below xhigh; Grok medium build quality on 1.21.0 | Unplanned | mem:improvement-backlog-2026-10-05 |

## 6. Known unknowns the docs name

- Quality of planning documents produced without review: "Whether the removed content was churn or rigour is unknown"; none documents are 2 to 4x smaller (spec 8,409 B vs 19,151; test-strategy 5,714 vs 20,880; W1 test-spec 2,498 vs 11,162) (docs/planning-time-analysis-2026-10-06.md §Bottom line).
- Escape rate with review off; the share of pass-1 review work that moves into authoring; Grok's escape cost; whether the host obeys the `none` packet sentences and the probe's placeholder rule (docs/shiploop-planning-review-plan-2026-10-05.md §Known limits).
- Recall of reviews (journal §Limits); benefit of record fixes (journal short answer).
- Whether Luna reports an exit satisfied after one changing Backchain pass (answered live on 1.21.0 for plan); whether any clean confirming Backchain pass ever prevented a defect; what the plan graph is for (a05) (docs/shiploop-fast-planning-plan-2026-10-04.md §Unknowns; planned-improvements).
- Effort effects: no same-case run at xhigh vs max on 1.16.x or later; Luna high/medium never run; effort per stage unmeasured.
- Brownfield: a weaker subject, reuse across a real run's cleared-context stages, a real second run inheriting a committed home, and large repositories ("Our instrument fits in context") (docs/shiploop-brownfield-baseline-design-2026-10-28.md §2; planning-speed plan B6).
- Plan-time experiments in live runs: no live-run record found of the `improve-reconcile` route or of `probed` assumption dispositions being used; the assumption list's completeness is unmeasured (grep of LEARNINGS and docs).
- Host read-limit behaviour (17 of 24 ignored) cause unknown; Sonnet compaction unmeasured (docs/planning-time-analysis-2026-10-06.md §1, §3).
- Plan sizing: E6D2 is n=3 per arm on one subject; a firm claim needs 4 per arm plus Grok 4.7 after its reset (plan-sizing journal §12).
- SDLC base rates: saved run copies keep about 3% of what the model wrote, so "none seen" means "not measurable yet" for most failure modes (docs/shiploop-sdlc-gates-proposal-2026-10-30.md §1, §2b).
- A bare-model control run before trimming planning scaffolding (about 3 runs, $10-20) was recommended 2026-10-11; I found no record of it being run (archive journal Round 5, commit 896e9454272a734a94fa054a27f6964486f2e4cb).
- The artifact-flow audit's gates were never exercised in the two audited runs (zero refused callbacks; cleared-context consumption unproven then) (docs/shiploop-artifact-flow-2026-10-11.md header, §5).

## 7. Comparisons with external frameworks already in the repo

- docs/shiploop-graph-engineering-comparison-2026-10-04.md §2: table of ~20 systems (Blueprint First, StateFlow, Agentless, Archon, heddle, LangGraph, Temporal, MS Agent Framework, Burr, Ralph loop, Anthropic long-running harness, Superpowers, "Spec Kit / OpenSpec / Kiro", Gas Town + Beads, CAAF and others). Row for Spec Kit/OpenSpec/Kiro: "Spec-driven phases; OpenSpec deltas resemble preserve/add/modify/retire | Stop at implement; no release or consumer verification". Evidence quality stated: "web search plus page summaries by a small model. Not read past abstract/README level. Treat as directions." Only one plan item was imported (heddle's three-outcome verdicts, A1).
- docs/shiploop-sdlc-gates-proposal-2026-10-30.md §1-§2a: "ShipLoop's 23 stages cover more of the SDLC than GitHub spec-kit, Kiro, BMAD or Anthropic's published long-running harness" and 54 outside findings (ImpossibleBench, METR, Veracode, FeatBench, etc.); limits: no benchmark ran ShipLoop's guards; three practitioner claims second-hand (Claude Code review-round cap, OpenAI's harness post, Kiro's mandatory phase review).
- Archived, not on main: docs/github-repo-lessons/journal.md in commit 896e9454272a734a94fa054a27f6964486f2e4cb (branch archive/canonical-wip-2026-10-16): 15 repos studied including github/spec-kit, Fission-AI/OpenSpec and bmad-code-org/BMAD-METHOD; Round 5 (2026-10-11) compares ShipLoop with 27 techniques: 15 already covered, 6 skip, 4 watch, 2 consider, 0 adopt; watch triggers include "the second `planning_review none` probe" (mem:shiploop-vs-atlas-artifact; a second Grok `none` data point exists since, section 1A). Findings relevant to planning: spec-kit caps ambiguity at 3 markers in prompt only; BMAD headless mode (assumptions, open_questions, blocked) is closest to unattended; OpenSpec completion is file existence; "No repo studied has a script that owns the whole loop and validates every step's exit".
- Smaller: docs/shiploop-requirements-retention-2026-09-17.md (Spec Kit spec persistence, OpenSpec existing-project guidance: "Do not install those tools"); docs/shiploop-simplicity-plan.md (Spec Kit constitution template: borrow the short-principles idea, reject another framework); docs/shiploop-planning-artifact-handoff-plan-2026-09-19.md §Evidence and alternatives (adopt Spec Kit's file-reference discovery and explicit required inputs, "Reuse the pattern, not its scheduler"); docs/shiploop-inner-loop-due-diligence-2026-09-18.md (AWS AI-DLC proportionate planning, Spec Kit plan template); docs/improve-research.md (Superpowers two-verdict scoped reviewer).
- No document in the repo maps ShipLoop's planning stages to BMAD, Spec Kit or Kiro stage by stage.

## 8. Superseded or inconsistent statements to watch

- SPEC S-10 carve-out (2026-10-05) still names five planning results including `test-spec` as starting an Improve child; the stage table (2026-10-26) gives test-spec none and run-options.md says `none` drops four stages. The table is later and wins (test/shiploop_e2e/SPEC.md S-10; stage_spec.py comment at test-spec; commit 090c8c881448fd3ba4899433484e9b0633ba8d0a).
- The planning window still ends at "the first test-spec accept" although test-spec is no longer reviewed.
- "Improve is about half of a run" vs 28% median: different windows (planning window 53-58% vs whole run) (journal F4).
- Luna max plan loop passes: 11/15/26/18/17/12/4 (plan doc) vs 12/15/26/18/20/10/5 (commit message) for the same loop; ledger vs file mtimes.
- The SDLC gates proposal says SG2 "moved to PR #27"; SG2-K1 is already in test/shiploop_e2e/experiments.json on main.
- docs/shiploop-planning-speed-and-caps-plan-2026-10-28.md header says "proposal"; F2, F3, P4 landed 2026-10-29 (shiploop 1.23.0, commit 5faca0d3d1d61630c88302d75b78ad50d0cf1dd9); F1, F4, F6 did not.
