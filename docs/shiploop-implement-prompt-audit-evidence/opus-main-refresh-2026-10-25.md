# Independent main refresh review — 2026-10-25

Verified Claude Opus 5.5 (`claude-opus-5-5`), xhigh, no fallback, process/envelope exit zero.
The read-only consultation used committed snapshot e707b794. It ran no tests.
Official release reference: [Anthropic Opus](https://www.anthropic.com/claude/opus).
Transcript: `/tmp/shiploop-reanchor-20261025/opus-transcript/20261025T155558Z-33882`.

## Coordinator disposition

- Adopt: broaden the judge regression matrix to masked failures, setup errors and positive controls; protect primary passed-ID evidence and invalidate/rejudge stale receipts if the judging rule changes. Do not reject any line merely containing FAILED.
- Adopt: fix actual-state wording in release-plan, release-check and both reference copies; a single current observation does not prove present/absent discrimination.
- Adopt: keep the probe-authority repair scoped to wording around an already recorded command. Import re-proof already enforces the command.
- Adopt: narrow the source-return follow-up to the misleading no-action-needed message and a residual-file fixture; current return review still requires keep/exclude decisions. No new classification taxonomy is proposed.
- Adopt: the old T37 has separate target-copy, RED/kill and reporter clauses; record them separately. Keep prefix/outer reuse as proposed pilots, not measured experiments.
- Adopt: Work shortening is optional and remains a proposal; no prompt implementation occurs in this refresh.
- Qualify: the isolated runtime refuses recovery when backing state is lost, intentionally failing closed. The legacy label on --directory does not by itself forbid using this supported option on an already isolated --receipt call. Prefer run-owned backing state, then test loss/resume; do not introduce an automatic reset that could invent completion.
- Reject: 'only script check per step' is too broad; lint and other scope/contract gates also exist. The reproduced defect weakens the behavioral proof gate and can contaminate primary passed IDs.

## Advisor response (advice, not independently executed evidence)

I checked the plan against the snapshot source. The direction is right, but the judge defect matters more than the plan says, the loop "recovery exists" claim needs a condition attached, and a few dispositions need rewording. I ran no tests and made no edits.

## 1. Goal
Re-anchor the 2026-10-17 implement-step fix plan on main `e707b794`. Close what main already implements, mark items the owner overrode as superseded, and keep a short ranked list of what is still open, led by the zero-exit judge defect.

## 2. Material issues (ranked)

**M1. The zero-exit judge defect is wider than the plan says. It also weakens the only script gate left at each step, and the primary gate.**
- **The defect:** `judge` (`shiploop_test_loop.py:659-694`) never reads `tally["failed"]`. `counts.outcomes` is used only by `_judge_base` (`:1692`).
- **Where it applies:** `verify` (`:1283`), which covers the test stage, verify rerun, system-test, release-verify and end-of-work. Also `step_proof` (`:1476`): every inline Proof is judged as a `check` row (`step_command`, `:373`).
- **Why it matters more now:** `criterion_evidence` is superseded, so the Proof's exit code is the only script check per step.
- **It is easy to trigger by accident:** `/bin/sh -c "… 2>&1 | tail -n 40"` returns `tail`'s exit code. Neither `normalise_commands` nor `guarded` (`:163-242`) flags pipes or pipefail. Only `platforms/bash.md:12` mentions pipefail.
- **It reaches the primary gate:** `shiploop_primary._passed_ids` (`primary.py:94-113`) trusts a run's `passed` status minus `ids_missing`. A masked failing test can therefore be accepted as a primary requirement's `lower_layer_check`. The plan currently treats that gate as sound.
- **Partial cover today:** at the test stage only, the mutation check judges by exit code alone (`mutation.py:299`). All mutants survive, so it refuses, but for the wrong reason. There is no such cover at step-proof, verify, system-test, release-verify, or when mutation is skipped for remote commands.
- **A second gap the probe missed:** `_pytest` (`test_counts.py:60-67`) ignores "N error(s)". So "3 passed, 1 error" with a masked exit still passes, even after a `failed>0` fix.
- **Design caveats for the fix:**
  - Gate on the runner's summary tally, not per-ID `outcomes`. `_FAIL_LINE` matches `\bFAILED\b` anywhere on the ID's line, so a passing test titled "CASE-1 shows FAILED badge" would be wrongly refused.
  - The `check` branch's docstring says a check is judged by its exit code. A negated check (`! pytest …`) then needs an explicit owner decision.
  - Reuse (`_reused` `:1149`, `step_proof` match `:1449`) copies stored statuses, so records judged by the old code are never re-judged. State that.
- **Experiment (fail first, standard library, real runner output):**
  1. Make a unittest file with one failing test. Use Proof `python3 -m unittest -v t 2>&1 | tail -n 20` in the harness of `test_implement_done_is_refused_while_the_step_proof_fails_and_accepted_once_it_passes` (`test/shiploop-test-loop.test.py:2359`). Expected today: implement done is accepted.
  2. Repeat as a focused row with ids at the test stage, and again at the verify rerun.
  3. Assert that `primary.passed_cases` contains the failing ID.
  4. Guard cases for the fix: a passing title containing FAILED, pytest "passed + 1 error", and a negated check.

**M2. R19's "recovery exists" may have a dead end.**
- `start_command` (`loops.py:548-552`) passes no `--directory`, so the runtime's `mkstemp` (`until_loop_ephemeral.py:972`) puts state in the system TMPDIR.
- If that file disappears while the receipt is active (TMPDIR purge, a per-session sandbox TMPDIR, a restart), `next_argv` fails. A fresh `start` is then refused by `_check_start_receipt` (`:406-426`), and `RECEIPT_RULE` (`loops.py:585`) forbids editing the receipt.
- The runtime labels `--directory` as "legacy" (`:1160`). So the fix is not to add it back; it is a policy for an active receipt whose state file is gone.
- **Experiment:** start a loop with a receipt, delete the receipt's `state_file`, then run `next_argv` and then the start command. Record both errors and what the packet tells the model. A dead end means R19 stays open; otherwise close it.

**M3. The WORK_STEP dedup should be dropped or gated on the owner.**
- The clause is a true duplicate of the Exit condition (`STEP_CRITERIA_CONDITION`, `stage_spec.py:85`).
- But `loops.py:97` marks it as the owner's D4 words, and two tests pin it (`shiploop-loops.test.py:211`, `shiploop-delegation.test.py:647`).
- The saving is about 100 bytes per loop instruction, and only in the contract: implement is not in `ARGUMENT_STAGES`, so the packet doesn't print it.
- It is bytes only, with no quality gain, yet it needs owner sign-off, an E2E round and a verbose prompt commit. Mark it optional and owner-gated, not a residual.

**M4. The release-check wording has three copies and a logic flaw.**
- The copies: `shiploop_prompts.py:1792`, `references/testing-and-documentation.md:183`, `references/platforms/salesforce.md:60`.
- Release-plan item 5 (`prompts.py:1763-1765`) also claims one release-check run "proves it tells them apart". One observation can't prove that, and when the target already holds the change there is no absent state to observe.
- The plan delta should be: record the observed state plus the required release delta, and state discrimination as unproven rather than creating an absent state.
- No gate checks any of this (`shiploop_consumer_delivery.py` has no present/absent logic).
- **Check:** render the release-check packet for a fixture whose target already has the entry.

**M5. The probe-authority conflict is real, but only the prompt is affected.**
- The Improve opening says "No push, deploy, install or credential access" (`navigator.py:8644`).
- `IMPLEMENT_STEP_REVIEW_FOCUS_HEAD` says "rerun the step's Proof" (`prompts.py:2588-2590`) and allows "probe it in one line" (`:2571`).
- The producer's authority (`loops.py:423`) forbids neither deploy nor credentials.
- With a Proof that reaches a remote target, Improve cannot comply. Enforcement still holds: `_improve_change_gate` reruns `step_proof(phase="improve-import")` itself (`navigator.py:4479`).
- **Fix:** reuse system-test's existing sentence (`prompts.py:1669-1670`): "Add no deploy to unblock a test (a recorded command's own deploy step runs as recorded)".

**M6. Reframe R17 (leftovers).**
- `commit_leftovers` (`workspace.py:1294-1318`) runs at plan-return (`protocol.py:318`) before review. `plan_return` then reviews every path again, so each still gets a keep/exclude decision, and an excluded path falls back to the working-tree route.
- Tool state is a prepare duty (`.gitignore`, `prompts.py:1273-1275`).
- What's actually open:
  - the decision is only keep/exclude, with no product/test/tool-state classes;
  - `protocol.py:320` prints "(no action needed)" for files that still need a review decision.
- **Check:** a fixture with an unignored tool-state file. Run plan-return and confirm the file is both committed and undecided. Unless it can fast-forward without a decision, downgrade R17 to a wording fix plus this one test.

**M7. T37 has three clauses, and the plan carries one.**
- Old plan line 1052:
  - (a) a runner pinned to an old deployment cannot claim proof;
  - (b) a behavioural RED or kill is told apart from a build or setup failure;
  - (c) per-ID failure with a zero exit.
- (b) is accepted by design: any non-zero exit counts as a kill (`mutation.py:18-33`), and a base load failure counts as RED (`test_loop.py:1694-1697`). Mark it superseded by design.
- (a) exists only as prompt text (system-test, `prompts.py:1668-1669`); no script binds a run to a deployed revision. Mark it open at prose level and low priority.
- Write both down explicitly so they don't silently disappear.

**M8. Keep `criterion_evidence` superseded, but record what is left.** Old plan line 1180 had adopted it; template-build plan lines 227-228 override it. Each criterion's satisfaction is now asserted by the model through the loop's Exit condition and judged by Improve. The only script check is the Proof's exit code, which ties back to M1. Record this as an accepted risk, not as "done".

## 3. Minor nits
- "Prefix and outer-stage reuse remain measured pilots" overclaims. `shiploop-run-insights-plan-2026-10-18.md:276` lists it as a proposed pilot (T40). Only base/mutation reuse was measured (DeepSeek README line 62).
- **Remote restore, worded precisely:** base and mutation never run remote commands (`_remote_base` `:1719-1740`, `mutation.py:428-433`). The remote-changing routes that do exist (candidate runs, system-test, release-verify, release) move the target toward the candidate, which is intended. Cleaning up remote test data is a release-plan teardown duty (`prompts.py:1761`), not a restore.
- **Scope `required_trivial_reviews=1`:** that is the Improve stage (`navigator.py:8119`). The producer loops use verify=1 and every other stage 0 (`loops.py:161`). The test name `test_created_plans_wait_for_two_reviews_after_material_repair` (`shiploop-standalone-improve.test.py:167`) reads like the old two-review policy. Check whether it asserts 2 before stating "one review" everywhere.
- `keep_decision` is in the test harness (`test/shiploop_e2e/run.py:2376`), not the skill. `keep_refusal` judges a done run as a finished delivery without checking whether the return was committed; per its docstring, that is intended.
- **Repo obligations for the later implementation:**
  - a `changes/shiploop/<slug>.md` note;
  - a `test/shiploop_e2e/LEARNINGS.md` entry or a `No-E2E-Round:` trailer;
  - verbose commit messages for the M4 and M5 prompt edits.

## 4. Open unknowns
- Do saved live runs contain masking commands? Grep the recorded commands in the `run/tests/*.md` files under `/Users/dadleet/e2e-runs/` for `| tail`, `| tee` and `|| true`. A hit is what makes M1 urgent.
- How each host handles TMPDIR (Codex/Grok sandboxes) for M2.
- Owner decisions on negated `check` commands and on counting pytest errors as failures.
- *Speculative:* `passed_cases` takes any passed record of any done action, so a test ID reused across a send-back could match stale evidence.

## 5. If I were implementing tomorrow
1. Run M1's fail-first experiments at the CLI boundary (step-proof, test, verify), plus the `passed_cases` check and the live-run grep.
2. Run the M2 state-loss experiment and decide R19 from the result.
3. Revise the plan's dispositions: split T37, record the `criterion_evidence` risk, reframe R17, lower M5 to a prompt-only issue, fix the "measured pilots" wording, and mark the WORK_STEP dedup optional and owner-gated.
4. Only then, as separate authorized work:
   - the minimal judge fix (`failed>0`, or pytest `error>0`, means failed, for counted and check suites), with the guard tests;
   - the release-check wording across all three files plus release-plan item 5;
   - the one Improve authority sentence.
