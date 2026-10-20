Execute: inline

# ShipLoop template build plan (2026-10-18)

Owner request (2026-10-18): "plan this and then build it out". "This" is the step-plan and implement templates (version 2,
`docs/experiments/run-insights-2026-10-18/templates/`) and everything their `requires` lists. The basis is the run-insights
plan (`docs/shiploop-run-insights-plan-2026-10-18.md`): N1, N2, N3, N5, A0, A1, T-D2, C6/G1, D3, decisions 19 and 20, E1-E6
and the landing conditions of section 8.3.

## Goal and done

ShipLoop prints the step-plan and implement packets from their template files. Every slot is filled by the script, every
gate rule is stated in the print, the static budget holds (19,500 at the reference install, under the 20,000 host cut at
the longest supported install), and every feature the templates name is real in the engine.

Done means all of these hold:
1. The unit tests and the quick tier (`--changed-from` the base) pass on the branch and on main after each merge.
2. `packet = template + slot values` holds for both stages, on the dry-run walk and the offline step slices.
3. Each gate a template lists is triggered through the real `complete` and names its rule (route tests).
4. One live end-to-end run on the released version reaches done or its declared stop, with its learnings in
   `test/shiploop_e2e/LEARNINGS.md`.
5. One release reaches every host.

## Scope

**In:**
- The `requires` of both templates;
- the N1 engine (loader, validator, renderer and slot registry) for these two stages;
- the two templates and their partials;
- route tests;
- docs and change notes.

**Out:**
- The other 22 stages, which keep today's renderer until each migrates in its own change. This is the planned migration
  order, not a dual path for one stage.
- Wave A items the templates do not print: I1-I4, C1-C5, B1-B5, A3-A7, L1-L2, K3 and obligation continuity.
- N4, N6, N7 beyond these two stages, and wave C.

## Method (the owner's rules for this work)

- **Branch.** One worktree branch, `feat/shiploop-templates-<rand>`, based on fresh main.
- **One unit at a time.** Read the last three commit messages first. Write a fail-first test for each behaviour (a
  route test where a gate is involved). Make one verbose commit per unit: key learnings, key decisions, evidence, and
  related commits.
- **Change notes.** Each skill change adds `changes/shiploop/<slug>.md`, and `changes/improve/` where Improve changes.
- **Slices.** Each slice merges to main when its units and the quick tier pass (CI checked after the push). After all
  slices: one release, then one live E2E verification run.
- **Models.** E2E launching and monitoring, and test plumbing, go to Sonnet agents. Engine and prompt construction
  stays in this session (Opus).
- **One supported version.** State version 8 refuses older runs. No aliases and no shims.

## Slice 1: outcomes, symbols and loop texts

| Unit | What | Where | Tests |
|---|---|---|---|
| S1.1 N5 | Outcomes done, blocked, send-back and add-work; repeat removed; `awaiting` replaces `blocked_by`, with kinds answer, present and service; the send-back budget checked at `--check-only`; Improve only on done; state version 8 refuses older runs; the run-review export maps old names when it reads historical runs | stage_spec OUTCOMES and _finish; navigator outcome handling, `_normalise_awaiting`, `_apply_result`, the version check; prompts' outcome text; loops REPEAT texts (E2); export | route tests: each outcome through `complete`; send-back over budget refused at check-only; old-name outcome refused; old-version run refused; port the existing tests |
| S1.2 decision 19 | KNOWLEDGE replaces HOME as the printed symbol | navigator reference_paths, symbolic, REFERENCE_SYMBOLS, expand_result_roots; prompts; stage_spec goals; references and SKILL.md; obligation anchors | evidence_refs `KNOWLEDGE/x` accepted and `HOME/x` refused through `complete`; packet symbol tests ported |
| S1.3 E3 | `REPEAT_STEP`: a person's or a service's action becomes blocked, an unachievable step becomes send-back | loops | contract text test |
| S1.4 E4 | `check_loop_packet` tests the receipt status before the contract comparison | loops | a scratch runtime test: an active receipt from another contract names `next_argv`, not start |
| S1.5 N5 outer send-back | system-test may send back to system-test-author, and release-verify to release-plan (run-insights N5, owner decision 10). Missing from this table until the S1.1 commit, 2026-10-18 | stage_spec outcomes and send-back targets; navigator `_apply_result` reroute; the outer packets' outcome lines | each route through `complete`: the target stage reruns with the result as evidence; a send-back over the budget is refused at check-only |

## Slice 2: plan data

| Unit | What | Where | Tests |
|---|---|---|---|
| S2.1 T-D2 | Producer bounds: plan work-item context 2,500, concern rows 1,200, open assumptions per item 1,200; step-plan task 700, criteria 1,200, check 600 | plan and step-plan gates | over-bound refused with the bound named; at-bound accepted |
| S2.2 A1 | The plan writes concern rows per work item (15 concerns: id, applies, decision or reason, anchor, owner_stage); step-plan maps applies-yes rows to steps and a check, or an owner stage; `concerns` joins `_RESULT_KEYS`; the step-plan done_when gains its condition | stage_spec, navigator result keys and gates, prompts (plan duty) | an unmapped yes row is refused; a docs-only item with all rows no and a reason is accepted |
| S2.3 C6/G1 | Each platform card has a `## Testing` section; the environment file names its card (`## Targets and runtimes`), or none | references/platforms/*.md; a card lookup in knowledge_home | every card has the heading; the lookup returns the card or none |
| S2.4 run-3 sizing | The plan duty folds pure scaffolding (a project skeleton, config) into the first item that builds on it, and states the fixed cost of each item when it sizes the queue (chess run 3: W1 only generated the DX project and took 52 min) | plan duty (prompts), with S2.2 | a plan whose first item has no requirement of its own is refused, or names why it stands alone |
| S2.5 run-3 checks | Step-plan runs each step's focused command once on the item base and refuses one whose failure does not name its case (chess run 3: W1's check asserted before printing and cost a send-back, about 23 min) | step-plan gate, with S2.1 | a check that exits 1 with empty output on the base is refused with the fix named |
| S2.6 run-3 tool state | A platform card lists its tool-state paths (Salesforce: `.sf/`, `.sfdx/`), and prepare adds them to `.gitignore`, so a tool's own files do not trip the Improve change gate (chess run 3, refusal 5) | references/platforms, prepare duty, with S2.3 | the Salesforce card lists them; prepare's done-when names the ignore |

## Slice 3: the implement record

| Unit | What | Where | Tests |
|---|---|---|---|
| S3.1 A0 | Port the Codex implement redesign onto main: `references/implement-guidance.md` (considerations), `code-craft.md` rules 10-14, `considerations` (eight keys) and `criterion_evidence` (seven fields), the implement-record gate, cards and match at step-plan | the branch's 21 files, diffed against main's W2-A/B (no mechanism twice) | the branch's tests, ported; considerations keys refused when missing; evidence rows required per assigned criterion |
| S3.2 N2 | ShipLoop commits each accepted implement step, before any Improve edit, as `feat(<item>/<step>): <headline>` with Key learnings, Key decisions, Evidence and Related commits; results gain `learned` and `decisions` (required, `["none"]` allowed) and `learned_from` (each commit reachable from HEAD); the look-back takes the last two commits that are not ShipLoop bookkeeping | workspace commit functions, navigator implement accept, result keys | a step commit exists with its sections; an unreachable `learned_from` is refused; the look-back skips bookkeeping |
| S3.3 N3 | A learning that changes a stored document writes it at implement (an acceptance line in spec.md marked with its step, a new AD-n, a command); ShipLoop commits it with the step | navigator knowledge gate | spec acceptance line accepted and committed; changing an existing R-n refused (send-back) |
| S3.4 D3 | Per-step revisit: the step's previous result and commit, and the send-back summary cut at 600 | navigator `_revisit_lines` | a revisit of S1 names S1's result, not S4's |
| S3.5 E6 | The progress narrative is capped at 900 where it is produced | shiploop_narrative | a 7-item run's block is at most 900 characters |

## Slice 4: the templates (N1)

| Unit | What | Where | Tests |
|---|---|---|---|
| S4.1 engine | `shiploop_templates.py`, ported from `packets-tools/tmpl.py`: parse, validate (declared and used slots, flags, gates anchors, placeholders, outcomes against stage_spec, requires registered, static budget in two tiers), render (shrink order, pools, never refuse at emit) | scripts | the validator on both templates; a broken template refused for each rule |
| S4.2 slots | A slot registry: each slot name maps to a function of state (the sources the template front matter declares) | navigator | each slot is filled for the Battleship fixture and a node fixture |
| S4.3 templates | `skills/shiploop/templates/step-plan.md`, `implement.md` and `partials/`; the navigator renders these two stages from them | navigator emit and render | packet = template + slots, both routes; head-order and hook tests kept |
| S4.4 decision 20, E1, E5 | `invoke_lines` prints the pointer; loops Work cites "Method items"; a test pins the runtime's printed Work, Exit and Repeat | loops | runtime stdout test; the contract Work names the Method range |
| S4.5 registry | The placeholder gate reads each template's placeholder list | navigator `_placeholders` | an unfilled form is refused through `complete` |
| S4.6 ledger | Obligation rows (until-loop rewritten), head-order, packet_view and counters repointed | test/shiploop_e2e | the obligations and head-order suites |

Chess run 3 adds two measures to slice 4: compaction, with 14 in 236 min and about 108 min of re-orienting in total
(26-91 tool calls after each, packets up to 36.5 KB), is the bounded head's target; and refusals that name the rule
and the next valid command (E1, E5) target the 63 or more reads of ShipLoop's scripts at the gates.

Outside the slices, from chess run 3: the mutation gate mutates a local copy while the focused commands test the deployed
one (second case after Battleship); one research call reached 498,847 input tokens (cause unknown); the harness cleanup
compares the whole org with an old snapshot, so it reports failure when another kept app is present; and the cap for a
full run is sized again after fixes 1 to 3.

## Verification and release

- **Per unit:** the unit's tests, fail-first, then the changed suites.
- **Per slice:**
  - `bash test/run-all.sh --group quick --changed-from <base>`;
  - the offline step slices (`test/shiploop_e2e/packets.py --offline`) and the dry run;
  - merge to main, then check CI.
- **After slice 4:**
  - a full-tier run;
  - one release with change notes, and the E2E preflight's LEARNINGS entry;
  - a live run: the `battleship-salesforce` step slice or full case on Grok 4.7 medium, coordinated by a Sonnet agent,
    keeping the app in org `de`;
  - its learnings committed;
  - the hosts refreshed.

### TODO (owner, 2026-10-19): rerun chess on Salesforce once every chess-run-3 fix lands

- [ ] When all the fixes from chess run 3 are built (fix 1, the Improve schedule; S2.4 to S2.6; the refusal and duty
  texts; the mutation gate on hosted platforms; the harness cleanup), release them.
- [ ] Then rerun the raw full case exactly as run 3 did, so the two compare:
  `run.py --case chess-salesforce --host grok --model grok-4.7 --effort medium --source marketplace --timeout 14400
  --keep-platform --output <a fresh durable folder>`, coordinated by a Sonnet agent, org `de`. Check the preflight
  first: a kept SLChess app blocks it.
- [ ] Compare with run 3: the stage reached, Improve minutes, compactions and re-orientation calls, reads of ShipLoop's
  scripts, and per-item time. Journal it in LEARNINGS.md and the chess journal (F11), and update the summary artifact.

### TODO (owner, 2026-10-20): iterate on the chess case with the E2E loop

- [ ] Once the build plan is complete and released, run the E2E iteration loop on the chess-salesforce case alone, and
  let it build, review and improve ShipLoop over repeated runs: `test/shiploop_e2e/iterate.py --case chess-salesforce
  --host grok` (run, review, improve, rerun; it commits to a branch and publishes nothing).
- [ ] First check what iterate.py needs for this case:
  - a run timeout of at least 14,400 (its default is 10,800);
  - the platform flags passed through to run.py (`--keep-platform`, a durable output);
  - the org cleaned, or the kept app removed, between iterations, so each run's preflight passes;
  - the improver's model and budget.

  Fix what is missing in the harness first.

## Risks

| Risk | Mitigation |
|---|---|
| The navigator is 8,300 lines, and N5 and the rename touch about 100 sites and about 350 test lines | One mechanical unit at a time, with the suites before each commit |
| A0's branch was built on an older base | Diff each mechanism against main first; port only the delta |
| Budget drift with real data | The validator is the guarantee, plus a live-data render case in CI (the Battleship values) |
| Old runs in flight on the hosts | They are refused at load (one supported version); the release note says so |

## Progress (journal)

Each entry: the unit, its result, what it found, and the evidence. Entries are edited later rather than deleted.

- **2026-10-18, S1.1, S1.3 and S1.4 (the four outcomes; firm).** Commit `c6c82b16`. S1.2 is `9ab464c1` and S1.5 is `c4fc5608`.
  - **Result:** done, blocked (`awaiting`: answer, present or the new service kind), send-back and add-work. `repeat`,
    `revise`, `replan` and `blocked_by` are refused with the new names. Improve starts only on done. Check-only enforces
    the send-back budget. State version 8.
  - **Found by porting the tests** (38 test files, five Sonnet workers and this session), five engine defects, each fixed
    in the unit:
    - validation demanded Improve records for non-done results;
    - the ask-agent step-plan head was 20,124 characters, over the cut;
    - the dry run's blocked-resume raised a KeyError on a service wait;
    - the status text cut URLs as paths (`https:health`);
    - the service-wait packet repeated its kind and gave contradictory resume instructions.
  - **Gap found:** the outer send-backs of N5 were missing from this table; added as S1.5.
  - **Evidence:** the quick tier passed with `--changed-from origin/main`, and all 95 ShipLoop suites plus the audit harness
    unit tests passed.
- **2026-10-18, S1.2 (decision 19, `KNOWLEDGE`; firm).**
  - **Result:** 146 engine sites, plus SKILL.md, four references and the complete command, now print `KNOWLEDGE`.
    `HOME/` in `evidence_refs` is refused as an unknown root (route test:
    `test_a_missing_symbol_led_path_and_an_unknown_root_are_refused_and_the_absolute_path_is_accepted`).
  - **Size:**
    - heads grew by 6 to 51 characters; `head_table.json` was re-measured, and the tightest, inline step-plan, is 19,971
      against the 20,000 cut;
    - the context-index map is 3,618 characters against a bound of 3,650 (was 3,600).
  - **Hand-off fingerprints:** 26 of 33 changed. Writing KNOWLEDGE back as HOME reproduces every old hash, so the symbol
    is the only difference.
  - **Harness:** `packet_anatomy` and `metrics` read both symbols, because saved runs before 2026-10-18 print HOME.
- **2026-10-19, S1.5 (outer send-backs; firm).**
  - **Result:** system-test sends back to system-test-author, and release-verify to release-plan. Each target has its
    own budget of two (`state.revisions` keyed by the target), checked at the gate and at `--check-only`. The target's
    packet prints three revisit lines (why, the previous result, amend it). The status names the target.
  - **Decisions:**
    - the test loop's refused-run remedy at those stages stays add-work, because a refused run shows the product
      failing, not the plan;
    - release, rerun after a send-back, runs only what the amended plan changed, so nothing deploys twice;
    - the navigator reference's outer outcome row still listed `repeat` (missed in S1.1), fixed here.
  - **Tests (fail-first):**
    - `OuterSendBackTests` in shiploop-send-back: the route and rerun, the budget, the packet lines, the status, the
      remedy and the revisions validation;
    - the check-only budget through the real CLI in shiploop-handoff (`SendBackBudgetCliTests`).
- **2026-10-19, chess run 3 and fix 1 (the Improve schedule; firm for the code, interim for the effect).**
  - **Run:** the raw full chess-salesforce case on 2.7.0 stopped at the 4 h cap at W4 test-spec. Improve took 98.9 of
    236 min (52 passes), and the step plan's review took 5-14 min on every item. Evidence:
    `/Users/dadleet/e2e-runs/20261019/chess-sf-full-05fe25b/`, LEARNINGS on main `b0bbba4a`, and the summary artifact
    https://claude.ai/artifact/Noh6HwBwhsKFnCRnDV647s.
  - **Owner decision:** "do 1". Improve now reviews `step-plan` and `test-spec` only for the first work item and for an
    item that was sent back (rule `first-item` in the stage table). The planning stages, every implement step, the last
    carry-forward, system-test-author and release-plan are unchanged. On this run it would have skipped W2-W4's step-plan
    and W2-W3's test-spec reviews: 36.6 min.
  - **Tests (fail-first):** `FirstItemReviewTests` in shiploop-improve-schedule (only the first item's two reviews start;
    a sent-back item's redo is reviewed; a later item advances straight to test-spec; the first item's record is still
    required). The two expected schedules in that suite were updated.
  - **Plan rows from the run:** S2.4 (fold scaffolding), S2.5 (a check must fail visibly), S2.6 (tool-state paths), and the
    slice 4 measures above.

- **2026-10-20, the chess-run-3 fixes (firm for the code; the effect is measured by the TODO rerun).** On the build
  branch, unreleased:
  - `f368dfa2`: Improve reviews step-plan and test-spec for the first work item and after a send-back only.
  - `e184c23f`: harness cleanup by prefix (a Sonnet worker).
  - `c00b17f2`: live-run guidance texts (S2.4 to S2.6, RC-1, RC-3, research).
  - `7a194ae4`: the mutation check skips focused commands a platform card lists under Remote tests; Tool state
    sections for the Python and Node cards.
  - `5e377ff7`: Improve completes at its first trivial pass (owner, 2026-10-20: "the current criteria may iterate far too
    often without results"; 11 of 16 reviews spent a pass only confirming).
  - Owner direction (2026-10-19): rank work by its gain in ShipLoop's code production on any project; the probe
    app does not matter in itself.
  - Not yet changed: RC-2 (the Improve hand-off contract re-read at each Improve stage), owned by slice 4.

- **2026-10-20, slices 2 and 3 on main (firm for the code; unreleased; the effect is measured by the TODO rerun).**
  - **Slice 2:** S2.1 producer limits `d45c3f80`, S2.2 concern map `fff7fa13`, S2.3 platform testing guide `6925d454`.
    Main CI on `6925d454` failed in shiploop-e2e-fidelity: a test picked its record by glob order (static-checks on
    Linux, system-test on macOS). Fixed by stage in `5d490033`, then green.
  - **Slice 3** (`6be0a670`..`d1f63406`):
    - S3.5 narrative cap 900 (`6be0a670`);
    - S3.1 A0, lean port (`5a6d9265`): the owner chose guidance by reference and Code craft 10-14 as one line each,
      with no per-step considerations or evidence fields and no gate;
    - S3.2 step commits with learned/decisions/learned_from, plus the inline look-back (`32e66660`);
    - S3.4 per-step revisit (`34946141`);
    - S3.3 spec acceptance write-back, plus a send-back route after a refused implement done (`d1f63406`).
  - **Findings:**
    - **Route (firm):** a refusal at implement that named send-back was a dead end once the step's Until Loop had
      completed. The existing item-scope refusal had the same gap. Fixed by `loops.open_send_back`, and the N3 test
      submits that exit through the real gate.
    - **Budget (firm):** A0+N2+N3 grew the inline implement required text to 18,974 on the two-item fixture. The head
      then lost its guide lookups, because optional blocks are kept as a prefix under the 19,500 bound. The slice's own
      text was cut to its obligations (18,534, 44 to spare), and the look-back moved after the quoted blocks. Slice 4's
      templates own this budget next.
    - **Fixtures (interim):** a required result field now costs about eight fixture ports across suites
      (inner_fixture.fill, full-runtime, callback-contract, the eight-stage helper). A shared per-stage fixture default
      would cut that; deferred.
