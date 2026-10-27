# Opus review of the public-run plan delta (2026-10-18)

Read-only consultation through the existing ask-opus subscription runner. Advice is evidence for the coordinating review; the plan’s disposition is authoritative.

- Process exit: 0; JSON exit: 0; fallback: false; model verification: verified.
- Requested alias: opus; served model: claude-opus-5-5; effort: xhigh; profile: consult.
- Latest-family check: [official Opus page](https://www.anthropic.com/claude/opus), announcement and availability text inspected on 2026-10-18.
- [Request](/tmp/shiploop-public-analysis-20261018/review-brief.md); [raw JSON](/tmp/shiploop-public-analysis-20261018/opus.json).
- Transcript: `/tmp/shiploop-public-analysis-20261018/transcript/20261018T135743Z-3449`.
- This reviewed the initial delta brief and earlier plan while the coordinator revised the document. It is not a final-version approval or runtime qualification.

## Returned advice

I didn't change any files; Write is disabled in this session, so the review is below.

# Review: Battleship delta to the ShipLoop implement-step fix plan

I checked the delta against three sources:
- **Integration worktree** (`.claude/worktrees/shiploop-eff-int-c5f79b`): its code, its packet-review plan, and `docs/experiments/run-analysis-2026-10-18/`.
- **The run's `result.json`.**
- **Canonical `main`.**

Code facts I confirmed (symbols are in the integration worktree unless noted):
- **Already on integration:** `STATE_VERSION = 7` (main is 6), `steps[].check`, `test_loop.step_proof` (receipt reuse keyed on action, step, command and tree), `step_block` and `_review_base_line`.
- **Run order:** `_test_loop_gate` runs `base_check` → `loop_run` → `mutation_check`. The mutation check is last.
- **No remote restore:** `shiploop_mutation._check` mutates a temporary worktree and puts back only the local file (`target.write_bytes(original)`). Nothing restores a remote target.
- **Revise resets progress:** `implement_progress` counts implement `done` rows after the latest accepted step plan, so any step-plan revise resets it to 0. `REVISE_TO = "step-plan"` and `MAX_REVISES = 2`.
- **Test stage edits product code:** test duty 4 says "fix the product". Duty 8 revises only for a wrong command, an unachievable case or a missing regression suite.
- **D5 reuse has a gap:** `_reused` (owner decision D5) reuses a check-only *test* run on the same tree and command list. Mutation is not covered.
- **No `generated` class:** `path-classes.json` has only `test`, `metadata-nav`, `docs` and `config`; anything else counts as code. `metadata-nav` already holds Salesforce patterns.
- **Weak reporter check on the candidate:** `judge` passes a focused command that exits 0 if every listed ID is merely *named* in the output. Only the base run refuses unread output, so the platform card's "refused as unread" is true only for the base run.
- **The card's instruction is wrong:** `references/platforms/salesforce.md` tells the model to put org-bound tests in `red_na` and "let the candidate run and the mutation check carry the proof". A command that doesn't deploy can't make the mutation check carry anything.

## 1. Goal

Turn the Battleship findings into generic ShipLoop contracts that scripts can check:
- step proofs that claim only what they check;
- valid mutation evidence, with remote cleanup;
- sound reuse after a revise;
- complete packet contracts;
- consumer procedures a person can answer.

Write this as an amendment on top of what the integration branch has already landed, with no duplicate machinery and no new authority.

## 2. Material issues

**M1. The delta is written against the wrong baseline.** The plan file is the untracked canonical doc, written against `main`:
- §5 says the state version goes "6 → 7".
- §5 and §8 say "retain whole-file knowledge".
- Test T17 checks that a v6 state is refused.

Integration already ships state v7, step-proof, `step_block` and the review base. It also adopted owner decision D1 (knowledge by table of contents), which the "whole-file" wording reverses. Someone implementing from this file will redo landed work or revert D1.
- **Fix:**
  - Rebase the delta onto `c70a33f4` and mark each §5–§7 row as landed, partly landed or open.
  - Strike the whole-file wording.
  - Any new required field means v7 → v8.
  - The run used `7fecda44`, so diff `7fecda44..c70a33f4` before writing item 5; some findings may already be fixed (12151c49).

**M2. Remote mutation (item 3) asks for checks ShipLoop can't do, and misses the one rule that fixes the harm.**

What actually went wrong (from `analysis-bs-build-2.json`):
- The last mutant stayed deployed: a mutated `slBattleBoard` meta file sat in the org until verify.
- The document stage wrote README observations against that org during that time.
- The real `complete` reran all 8 mutants after check-only, which undid the model's own restore deploy.

Two of the delta's demands can't be met generically:
- "Product paths actually observed by the focused suite": there's no generic source of coverage.
- "Exclusive coordinated ownership": ShipLoop can't prove it.

- **Fix: adopt one rule.** The last run of the stage's commands that ShipLoop starts is on the accepted candidate, from the repository's own directory.
  - **Restore run:** after the mutant loop (in a `finally`), rerun the unmutated focused commands in that directory, the same way `loop_run` does, and record `restore: {status, output}`.
  - **Failed restore:** refuse with "target may still hold a mutant". Treat it like could-not-run, not as a test-quality refusal.
  - **Cancellation:** write the record as `in_progress` before the first mutant. A later `complete` that finds an in-progress record with no restore runs the restore first.
- **Cost and scope:** no command classification and no platform branch. Locally it costs one extra focused run.
- **Base run:** it already obeys the rule, because `loop_run` comes after it. Pin that order with a test.
- **Isolation:** record it as an authority precondition at prepare, plus a documented limit. The harness already enforces one run per org.
- **Keep verdict and cleanup separate:**
  - Extend D5 reuse to the mutation check-only record, keyed on candidate tree, base tree, focused command list, `SCHEMA` and `MUTANT_SAMPLE`.
  - Restore status is its own gate, not part of the reuse key.

**M3. The root cause is wrong platform-card data, not missing lifecycle machinery.** Item 2 ("planning must expose platform-card command facts") would have spread the card's wrong `red_na`/mutation sentence to planning even earlier. Fix, in this order:
1. Correct that sentence in the card.
2. Make the card's reporter claim match what `judge`/`outcomes` actually do, using captured runner output.
3. Only then link the card to test-strategy, plan and step-plan.
4. Add one generic review question to `_REVIEW_FOCUS_ITEMS`: *"Does each command ShipLoop runs on a copy (base or mutant) build or deliver that copy to what it tests?"*

**M4. Reuse invalidation (item 4) is unsound as written.**
- **"Semantic match" would be judged by the model.** Use exact equality of the normalized records instead:
  - the step row (id, task, deps, criteria, check, skills);
  - the step's criterion texts;
  - the `test_cases` rows for those criteria;
  - the text of the R-n and AD-n rows it follows, read with the knowledge-home ID reader.
- **Prefix rule:** reuse only the longest unchanged run of steps from the start of the plan. Owner decision D3 removed path fences, so nothing ties an edit to one step; the first changed step and everything after it rerun.
- **Tree equality would never match in Battleship.** The test stage had already written `SLBattleRulesTest.cls`, and duty 4 lets it fix product code. Require instead that product-classified content is unchanged since the last kept step was accepted. Any product change means no reuse.
- **Prerequisite:** add `**/*Test.cls` to the `test` class. Otherwise the test class counts as product code and reuse never fires here.
- **Evidence:** old receipts are bound to older trees. Rerun each kept step's Proof on the current tree, by script, with no model. A failure reopens from that step. About four proof runs replace roughly 11 minutes, 88 calls and 270 KB of prompts.
- **Residual risk:** a revise that names a product defect, with an unchanged plan, would skip implement and use up one of the two revises `MAX_REVISES` allows. Duty 4 makes this rare. Document it and pin it with a fixture rather than adding a classifier.

**M5. "Remote freshness independent of source equality" quietly amends owner decision D5.** If applied generally, it cancels D5's reuse for every remote command.
- With the M2 rule, plus M3's rule that commands judging copies deliver what they test, D5 stays sound.
- The remaining case is a command that reads remote state without delivering anything. ShipLoop can't detect that without a parser, so it belongs to planning review and the platform card.
- Anything stronger needs the owner to amend D5.

**M6. Missing from the delta: the Improve authority line contradicted the producer's authority.** Two build-stage Improve reviews deployed even though their line said "No push, deploy", while the run's authority did cover test deploys.
- **Fix:** use one source for the authority text in the producer packet, its head and the Improve handoff, the same way `step_block` works.
  - If a test route is authorized, name it.
  - If not, say how to probe without deploying.

**M7. Whether a consumer observation is required or advisory must come from a record, not the model.** The run ended `done` with the rendered board never observed: it became open item A1 and passed to handoff. Release-verify item 6 lets the model decide ("only when the release cannot be accepted without it"). Owner decision D6 covers a *partial* person reply; here there was no reply at all.
- **Answer first:** was the board a required behaviour in the delivery contract?
  - If yes, the D6 gate has a hole for the no-reply case.
  - If no, the step from spec to delivery contract dropped the requirement.
- **Case data:** the E2E case declared no browser (`browser.declared: false`), so the observation could never happen.
- **Reporting:** "done, required observation unverified" should be reported as its own outcome.

**M8. Item 1 has a cost consequence that should be stated.** For remote-only targets, a behavioural step proof means a candidate deploy for every step, and again whenever an Improve review changes the candidate. That runs in the repository, not a copy, so there's no mutant risk, but it does put partial products on a shared target.
- Keep the plan's §4.1 split as an explicit option: a step may prove source- or compile-level criteria, with the behavioural criterion assigned to a stage that can run it.
- The step-plan Improve review checks that the split is explicit.
- "Compile / deploy / behaviour / UI" stays as wording inside `criterion_evidence.establishes`, not a new field.

**M9. Machinery to cut or defer:**
- new record fields for runtime target identity and staging/activation (keep the retained output plus a reference to the authority's target);
- the "observed paths" restriction;
- verifying exclusivity;
- "verified cleanup" as a reuse key;
- a general model of remote freshness;
- auditing tool-log reads.

For item 5's gate fields and enums, render them from the validator's own constants and test them through the real gate.

**M10. The "existing path classification" can't exclude tool state, because there is no generated class.**
- `.sf/` belongs in the project's `.gitignore`, via the prepare duty and the card. The same root cause led `commit_leftovers` to commit `.sf/` files.
- Consider marking declarative `*-meta.xml` as non-code. Mutants there are visibility changes that unit tests rarely observe; the mutant left in the org was one.

## 3. Minor nits

- Map each delta item to a plan section and a T-number; continue numbering at T36.
- Two of the run descriptions are vague:
  - "ran twice" means implement S1–S4 plus four Improve reviews reran, with empty review diffs;
  - "repeated at complete" means `complete` reran the 8-mutant check (170.7 s) after check-only.
- Item 5's "per-step previous-result locator" should name the defect: `_sent_back_results` returns `earlier[-1]`, which is S4's result, when S1 asks.
- Item 8's "authenticated terminal evidence" should say the harness reads the engine's state file, not stdout.
- The artifact's "Play the game" link points at components the cleanup removed (`result.json` `cleanup.output`, `keep_not_honoured: rc=143`). Label it historical or confirm a redeploy.
- Say that 16,000 characters is a target to measure, not a gate.

## 4. Open unknowns

1. Was the board interaction a required behaviour in the delivery contract? This decides M7.
2. With the captured `--result-format human` and TAP output, what does `outcomes` return per ID? Is the verdict really exit-code only, and what exit code does `sf` return when an Apex test fails?
3. Does deploying from the mutation temporary worktree depend on ignored local state (auth, `.sf/` tracking)? A kill observed after the revise suggests it works.
4. Is a deploy that fails to compile atomic on each relevant target? This decides whether a sentinel mutant is safe; it's card data.
5. Can a reused step be derived from history and action records, or does it need a new history row (and so v8)?
6. How often does the test stage edit product code before a revise? This sizes the M4 residual risk.
7. Which item-5 findings were already fixed after `7fecda44` (units U3, U4, U6 and U10)?

## 5. If I were implementing tomorrow

1. Rebase the delta onto integration (M1).
2. Fix the data first (M3, M10):
   - correct the card's sentence and reporter claim;
   - add `*Test.cls` to `test`;
   - put tool state in ignores;
   - link the card to the planning stages;
   - add the copy-delivery review question.
3. Add the restore rule, the `in_progress` marker, mutation check-only reuse, and a refusal that names both causes plus the revise route (M2).
4. Build reuse with exact equality, the prefix rule, the product-unchanged check and rerunning kept proofs (M4).
5. Give authority text one source (M6). Then fix release-check's "historical presence" (item 7) and the per-step revisit locator.
6. Answer unknown 1 before writing item 6, and fix the case's browser declaration (M7).
7. Do the harness keep/stop changes separately, deciding from engine state (item 8).

**Smallest fixtures that scripts can prove** (a fake runner plus a fake target directory):

| ID | Setup | Expected |
|---|---|---|
| F-R1 | "Deploy" copies the cwd's product file to the target; "test" reads the target | After mutation, the target equals the candidate. A failed restore is refused; an exception between mutants makes the next `complete` restore first |
| F-R2 | The command tests the target without deploying | 0 killed; the refusal names both causes |
| F-R3 | Mutation check-only passed on tree T; `complete` runs on T | Zero runner calls. Changing a product byte, a command or `SCHEMA` reruns |
| F-R4 | Order pin | base → candidate → mutation → restore; the last call runs in the repository directory |
| F-U1–U5 | Step-plan revise | Only `test_commands` changed: S1–S3 kept, proofs rerun. S2's check changed: S2 onward reopens. Product byte changed: no reuse. A kept proof now fails: reopen there. Criterion or AD-n text changed: reopen |
| F-P1 | Captured TAP and human output | `outcomes` per ID matches what the card says |
| F-A1 | Authority lines for one action | Producer and Improve lines are identical; an authorized test route is named |
| F-C1 | A required obligation, no person reply | The run can't pass as done; the outcome is reported unverified |
| F-G1 | Printed enums | They equal the validator's constants, and the printed example row is accepted by the real gate |

**Where each kind of evidence comes from:**
- **Source proof (the fixtures above):** restore, reuse keys, run order, reporter parsing, authority text, gate rendering.
- **Semantic reviewer pilot (seeded defects):** a grep proof used against a behavioural criterion; a planned command that can't see the copy; an implicit criterion split; an invalid procedure. Offline fixtures only show that the text reaches the reviewer.
- **Live qualification (needs the owner's authorization; use a different app):**
  - one remote run, checking that:
    - the org snapshot after test equals the candidate;
    - a test-only revise adds no new implement or Improve actions;
    - there is one mutation pass per test stage;
    - no Improve review deploys without authorization;
  - one local package run, to show nothing regressed.

**Adopt, pilot or defer:**
- **Adopt now:** the M1 rebase; the card and classification fixes; the restore rule with the `in_progress` marker; mutation reuse; the clearer refusal text; the M4 reuse rule; one source for authority text; the per-step revisit locator; item 7's historical presence; harness keep/stop as a separate change.
- **Pilot:** a sentinel mutant, local only and only when nothing was killed; semantic reviewer detection; behavioural step proofs on remote targets (measure the cost); changing the required-obligation gate, if unknown 1 shows a hole.
- **Defer:** target-identity and staging fields; the observed-path restriction; verifying exclusivity; a general remote-freshness model (a D5 change needs the owner); auditing tool-log reads.
