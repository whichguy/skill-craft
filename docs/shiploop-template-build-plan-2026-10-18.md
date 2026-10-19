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

## Slice 2: plan data

| Unit | What | Where | Tests |
|---|---|---|---|
| S2.1 T-D2 | Producer bounds: plan work-item context 2,500, concern rows 1,200, open assumptions per item 1,200; step-plan task 700, criteria 1,200, check 600 | plan and step-plan gates | over-bound refused with the bound named; at-bound accepted |
| S2.2 A1 | The plan writes concern rows per work item (15 concerns: id, applies, decision or reason, anchor, owner_stage); step-plan maps applies-yes rows to steps and a check, or an owner stage; `concerns` joins `_RESULT_KEYS`; the step-plan done_when gains its condition | stage_spec, navigator result keys and gates, prompts (plan duty) | an unmapped yes row is refused; a docs-only item with all rows no and a reason is accepted |
| S2.3 C6/G1 | Each platform card has a `## Testing` section; the environment file names its card (`## Targets and runtimes`), or none | references/platforms/*.md; a card lookup in knowledge_home | every card has the heading; the lookup returns the card or none |

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

## Risks

| Risk | Mitigation |
|---|---|
| The navigator is 8,300 lines, and N5 and the rename touch about 100 sites and about 350 test lines | One mechanical unit at a time, with the suites before each commit |
| A0's branch was built on an older base | Diff each mechanism against main first; port only the delta |
| Budget drift with real data | The validator is the guarantee, plus a live-data render case in CI (the Battleship values) |
| Old runs in flight on the hosts | They are refused at load (one supported version); the release note says so |
