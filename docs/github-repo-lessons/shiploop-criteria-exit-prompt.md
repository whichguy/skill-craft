# Prompt: criteria exits for ShipLoop (no count loops)

Written 2026-10-11 from the Technique Atlas and its ShipLoop comparison.
Pinned reference commit: [`4b1759ac`](https://github.com/whichguy/skill-craft/commit/4b1759ac16a13953570f8f12f06f32b4da6ec866) (origin/main, 2026-10-11 07:48 PDT).
Sources: [Technique Atlas](https://claude.ai/artifact/G1zHiEq6iVjYGgcnf4GWYE) · [ShipLoop Versus Atlas](https://claude.ai/artifact/CHiMb8KsER5RBCepJ7Ytqu) · journal `docs/github-repo-lessons/journal.md`.
Status: interim. Links prove a file or symbol exists at the pinned commit, not that a claim about it is right.

## 0. Preconditions

- Base = fresh `origin/main`, in a task worktree. The canonical checkout was 445 commits behind and carries uncommitted edits to `skills/shiploop/scripts/{shiploop,shiploop_navigator,shiploop_protocol,shiploop_store}.py`, `references/{host-matrix,state-files}.md` and four `test/shiploop-*.test.py` files plus `test/shiploop_e2e/metrics.py`. Do not reset, clean or autostash them. Ask the owner whether to land or park them before this work touches the same files (C2 touches `shiploop_navigator.py` call sites).
- Repo rules (AGENTS.md): edit `skills/`, `agents/`, `changes/`, `docs/` only. Every skill change adds `changes/shiploop/<slug>.md` (`bump: minor`). Version fields, catalogs and `plugins/` are written only by `scripts/release.py`. New top-level test files go in `test/suite_catalog.py`. No compat shims or old-version support. No Hermes.

## 1. Intent

A ShipLoop loop ends because its criterion is verified true, the goal is proven wrong or unachievable, or the loop has stopped producing new information. It never ends because an attempt counter reached a number. Owner decision, 2026-10-11: counts are not acceptable because there is no principled number.

## 2. Observable outcome

1. `grep -rn "MAX_REFUSED_RUNS\|STUCK_CONTINUATIONS\|GENUINE_FIX_ATTEMPTS" skills test docs/shiploop-*.md` returns nothing that gates a stage. (`MAX_REVISES` is C4, conditional.)
2. SPEC S-10 no longer carries the 11/7/22 carve-out. It states the three endings in section 1, with the owner's date.
3. A replay of every saved refused-run sequence (E2) yields the same accept/refuse outcomes as today for every sequence that ended in a pass.
4. `hello` and `checkers` E2E cases pass against SPEC S-1..S-14.
5. Each changed prompt paragraph beat a no-guidance arm under `skills/rubric-eval` (SPEC §5, §8: the baseline wins ties).

## 3. Phase 0: measure first (no code)

Run over saved runs (output dirs named in `test/shiploop_e2e/baselines.jsonl`, and `test/shiploop_e2e/evidence/`). Report how many runs are still on disk; do not extrapolate.

| id | question | feeds |
|---|---|---|
| E1 | For every implement receipt: did `exit_assessment: satisfied` precede a recorded check that failed at the next script run? List them. | C1 |
| E2 | For every action with 2 or more refused runs: compute F (section 4, C2) per attempt. How many sequences revisit an F? Of those, how many ended in a pass without a tactic change? | C2, C3 |
| E3 | Count `awaiting.no_default` refusals at stages before plan, from `_check_submitted_awaiting`. | C6 |
| E4 | List every `lint_waivers`, `red_na` and `retired_tests` reason. Flag any that read as convenience. | none (audit) |

If E2 finds no saved sequence with a revisit, say so: C2 then has no replay evidence and only the owner's principle behind it.

## 4. Changes

Order: C1, C2, C3, then C4 only if C2 holds up, C6 and C7 independent. Each change = smallest diff, a pinning test, a `changes/shiploop/` note, a journal entry with the commits that informed it.

### C1. Script-verified exit at implement

- Ground: SPEC S-10 ("frozen contract the script writes"). [`loops.py check_loop_packet`](https://github.com/whichguy/skill-craft/blob/4b1759ac16a13953570f8f12f06f32b4da6ec866/skills/shiploop/scripts/shiploop_loops.py) reads `exit_assessment == "satisfied"` and never `last_report.evidence`. [artifact-flow audit row 1](https://github.com/whichguy/skill-craft/blob/4b1759ac16a13953570f8f12f06f32b4da6ec866/docs/shiploop-artifact-flow-2026-10-11.md): all 9 Checkers receipts said satisfied at iteration 1; S1's receipt said satisfied while its own evidence said the check could only pass after S2.
- Change: at implement `complete`, the script reruns the step's recorded check commands with the `test_loop` machinery and refuses `satisfied` if any fails. In `check_step_plan`, refuse a step whose check cannot pass after that step; attach it to the step after which it can.
- Impact: touches `shiploop_loops.py`, `shiploop_stage_spec.py`/`shiploop_test_loop.py`. Check S-9 (script-run evidence) and S-12 for interaction. This adds a refusal path, so every new refusal needs its reason and correction on line 1 (as `d412a45d` and `f14f90c7` did).
- Unknown U1: steps whose check legitimately depends on a later step. Resolve by reading `check_step_plan` and `_check_step_sizing` for how checks are attached; the gate above is the proposed resolution.
- Size: about one script plus one prompt paragraph. KISS holds if no new state key is needed.

### C2. Replace refused-run and continuation counts with a repeat-state rule

- Ground: SPEC S-10 carve-out items 1 and 3 (owner decisions 2026-10-05, values raised 2026-10-10 in [`46e3326b`](https://github.com/whichguy/skill-craft/commit/46e3326b), [`30e49a8c`](https://github.com/whichguy/skill-craft/commit/30e49a8c)). Superseded by section 1. The caps exist so "a check that cannot pass as planned returns to the step plan instead of being resubmitted indefinitely" (SPEC); the repeat rule serves that purpose directly.
- Sites (grep for the names): [`shiploop_test_loop.py`](https://github.com/whichguy/skill-craft/blob/4b1759ac16a13953570f8f12f06f32b4da6ec866/skills/shiploop/scripts/shiploop_test_loop.py) (`MAX_REFUSED_RUNS`, `refused_runs`, `remedy_open`, refusal text "N of M"), [`shiploop_mutation.py`](https://github.com/whichguy/skill-craft/blob/4b1759ac16a13953570f8f12f06f32b4da6ec866/skills/shiploop/scripts/shiploop_mutation.py) (shares the tally), [`shiploop_keepalive.py`](https://github.com/whichguy/skill-craft/blob/4b1759ac16a13953570f8f12f06f32b4da6ec866/skills/shiploop/scripts/shiploop_keepalive.py) (`STUCK_CONTINUATIONS`, `blocks_at_revision`), the SKILL.md static-checks paragraph, `test/shiploop-stage-spec.test.py` (pins prose copies to constants).
- Mechanism:
  - F = sorted tuples `(command id, status, failing test ids)` for the refused run. No error text, paths, line numbers or timings: nothing to tune.
  - Per action the ordered F list is derived, not stored: `refused_runs` and `remedy_open` already walk the append-only per-attempt records via `_records` (`tests/<action>-verify<N>`, `-base`, `-mutation`; each carries `attempt`, `passed`, `disposition`). Compute F from those records. `remedy_open` currently tests `refused_runs(...) >= MAX_REFUSED_RUNS or latest_attempt_could_not_run(...)`; the first clause becomes "the latest F was already in the list and a notice was issued for it".
  - First attempt whose F is already in the list (repeat or A/B/A oscillation): the refusal names the repeated failure and requires a new hypothesis. The run continues.
  - Second revisit of the same F after that notice: the stage's existing remedy outcome (`revise`, or `blocked` where the stage allows only that), exactly as the 11th refusal does today.
  - Runs that could not run (`UNAVAILABLE`: timeout, skipped, error) keep not counting as product failures. A repeated identical unavailable F releases the turn only, as the 22-continuation release does today.
  - Keep the keepalive's existing state-based release (`last_block_progress == progress`, "no progress since the last continuation"); delete only the count branch.
- Unknown U2 (resolved by reading `refused_runs`/`_records`: the tally is already derived from record files, no state key): confirm the records hold per-command status and failing test ids. If they do not, F needs a record field, which is a record-format change; stop and ask.
- Unknown U3: the keepalive hook imports nothing from `test_loop` by design. Resolve by having the script put `stalled` in the status the hook already reads, not by importing.
- Unknown U4: false stall when a failure message is identical while the code genuinely advances (multi-part implementation). The first revisit only redirects; it never stops. E2 quantifies it.
- Counter-evidence: no repo studied does this (atlas card [stop-is-script-owned](https://claude.ai/artifact/G1zHiEq6iVjYGgcnf4GWYE)); no recorded ShipLoop run reached 11 refused runs. The justification is the owner's principle, not a recorded failure. Say so in the change note.

### C3. Fix-attempt rule becomes a criterion

- Ground: `GENUINE_FIX_ATTEMPTS = 7` in [`shiploop_stage_spec.py`](https://github.com/whichguy/skill-craft/blob/4b1759ac16a13953570f8f12f06f32b4da6ec866/skills/shiploop/scripts/shiploop_stage_spec.py); prose copies in `shiploop_prompts.py` (`_FIX_ATTEMPTS`) and [`shiploop_loops.py`](https://github.com/whichguy/skill-craft/blob/4b1759ac16a13953570f8f12f06f32b4da6ec866/skills/shiploop/scripts/shiploop_loops.py) (implement exit text). SPEC: "No script counts these attempts; it is the model's stopping rule."
- Change: replace "after N genuine fix attempts" with: stop `revise` when an attempt reproduces a failure seen in an earlier attempt and you have no new hypothesis; record the hypothesis each iteration in the receipt's `evidence`. Delete the constant and its pin. This is a one-paragraph prompt edit; no script counter.
- Gate: rubric-eval with a no-guidance arm (SPEC §5, §8). Test the route, not the wording: a fixture where the same check fails twice must reach `revise` through the real gate.

### C4. `MAX_REVISES = 2` (conditional)

- Only after C2 is shipped and E2 shows the F-log works. Count sites: [`shiploop_navigator.py`](https://github.com/whichguy/skill-craft/blob/4b1759ac16a13953570f8f12f06f32b4da6ec866/skills/shiploop/scripts/shiploop_navigator.py) (validation `1 <= count <= MAX_REVISES`, the "N of M left" text, the exhausted check), `shiploop_context_index.py`.
- Change: allow another `revise` only when its evidence differs from the evidence recorded for earlier revises of that item; identical evidence again goes to `blocked`, `blocked_by user`. This turns `state.revisions` from an int per item into a list: a `state-files.md` schema change. If the owner does not want a schema change, leave the count and say it is the one remaining number.
- No recorded run reached 2. Treat as owner-preference work.

### C6. Requirements wording vs S-14 (only if E3 is nonzero)

- [`requirements-definition.md`](https://github.com/whichguy/skill-craft/blob/4b1759ac16a13953570f8f12f06f32b4da6ec866/skills/shiploop/references/requirements-definition.md) says "obtain the missing decision before dependent work; do not guess". SPEC S-14: unattended by default; record the default and continue. Change that sentence to say which applies when no person is reachable. One sentence, no code.

### C7. Delete the Hermes row

- [`references/host-matrix.md`](https://github.com/whichguy/skill-craft/blob/4b1759ac16a13953570f8f12f06f32b4da6ec866/skills/shiploop/references/host-matrix.md) line 21. Policy: [AGENTS.md](https://github.com/whichguy/skill-craft/blob/4b1759ac16a13953570f8f12f06f32b4da6ec866/AGENTS.md) excludes Hermes. The canonical checkout has uncommitted edits to this file: reconcile first.

## 5. Verification

1. Unit tests: repeat detection on a fixture log (repeat, A/B/A, first revisit continues, second revisit reaches remedy, unavailable-run release); the existing pin test updated to assert the constants are gone and S-10 text matches.
2. E2 replay: same outcomes on every saved sequence that ended in a pass.
3. Live: `hello` and `checkers` via `test/shiploop_e2e` on Claude Sonnet 5.5, compared with the matching `baselines.jsonl` rows (25 of 25 pass; hello avg $3.77, 179 turns; checkers avg $4.50, 202 turns). Judge per SPEC S-1..S-14, Opus 5.5 medium, one judge per round. Decision rule from `eval-decision-priority`: a material quality gap decides; otherwise fewer tokens, then less time.
4. Resource ceilings are not a ShipLoop feature (section 6). Run the E2E cases with host flags set from the baselines (section 6).
5. Commit messages for prompt changes: state the key learning, the evidence file and numbers, and the related commits (`46e3326b`, `30e49a8c`, `d412a45d`, `f14f90c7`). Update the journal in the same commit. Land by merge or rebase, never squash. Release only through `scripts/release.py`.

## 6. Not applicable to ShipLoop code

| item | reason | reference |
|---|---|---|
| Run-level $ or minute ceiling | ShipLoop has none and should not: only per-tool deadlines exist (`shiploop_lint`, `shiploop_mutation`, `shiploop_test_loop`). Set `--max-turns` and `--max-budget-usd` on the host invocation, per your global autonomous-run rule. From the Sonnet 5.5 baselines: hello $2.01–6.47, checkers $3.09–6.65, battleship $3.41–9.65; start at twice the largest recorded cost for the case. The ceiling ends in a report, not a verdict. | `baselines.jsonl` |
| Freeze exit criteria after approval | Quality and test loops already use a script-written frozen contract (S-10). The Backchain loop's host-written contract (open item a02) is one pass by default (2026-10-04 carve-out), so there is little loop to freeze. | [`shiploop_loop_contract.py`](https://github.com/whichguy/skill-craft/blob/4b1759ac16a13953570f8f12f06f32b4da6ec866/skills/shiploop/scripts/shiploop_loop_contract.py) |
| Mark unconfirmable criteria at authoring | Already enforced by the unverified-list check. | `shiploop_unverified.py` |
| Delta-spec merge by code | In-place edit with R-ID/AD-ID retention is deliberate. Trigger to revisit: a run loses or garbles a requirement, or two runs edit one spec. OpenSpec's maintainers question their own merge (issue #2033). | [lifecycle plan](https://github.com/whichguy/skill-craft/blob/4b1759ac16a13953570f8f12f06f32b4da6ec866/docs/shiploop-commit-and-spec-lifecycle-plan-2026-10-10.md) |
| Fresh agent per stage | Inline is the default after 7–17 minute handshakes per stage; `delegation: ask-agent` exists. | `docs/shiploop-delivery-overhead-plan-2026-09-23.md` |
| Context-fill sizing, repo map | No recorded failure; no controlled support for a fill threshold; map conflicts with S-8. Watch triggers are on the comparison page. | comparison card `size-by-context`, `repo-map` |
| Per-finding validators, "assume not done" reviewer stance | Improve is inline by owner decision; grounded checklists already used; stance wording raises false rejections. | comparison cards `validator-per-finding`, `distrust-the-author` |
| Read-only tool lists, extra anti-tamper hooks | Bash bypasses tool lists; tamper resistance is structural (floors, base RED, mutation); more guards are the adversarial guards KISS rejects. | comparison cards `readonly-by-tool-list`, `reward-hacking-tampering` |
| Trigger-only descriptions, per-model prompts, format changes, reject-and-explain, exit-by-tool-call, hooks | Already covered or not how ShipLoop routes (`shiploop complete --action --result` is the validated exit). | comparison page |
| Spec-driven-development overhead, instruction-file value, scaffolding trim | Need a bare-model control (about 3 runs, $10–20), a separate experiment, not part of this change. | comparison cards `bitter-lesson-harness-scaffolding`, `broader-spec-driven-development` |

## 7. Self-grade

State for each of section 2's five outcomes: met / not met / unmeasurable, with the command output or file that shows it. List every unknown (U1..U4) with how it was resolved. List anything in section 4 you did not do and why. If C2 needed a `state.md` key or C4 a schema change, say so first and stop for the owner.
