# Improve action 1 — integrated material review

Candidate reviewed: `5a073503bcfe35e620461498b3fa438afe94d0bc` plus the authorized mixed staged/unstaged ShipLoop UI-allocation delta. The frozen base remains `7f8ef5d7508c3088f628a90d326fb025f293be15`. This record covers only the delegated source, generated-view, metadata, test, and experiment-reader scope; it does not absorb root-owned README, study, fixture, snapshot, or publication work.

## History and review

Read the seven full reachable commit messages captured in `09-action1-integrated-history.txt`: `5a073503`, `10733eee`, `f2c891a6`, `061ad490`, `88e59f9a`, `2e0c064c`, and `5e30bd9d`. The merge history establishes that the current candidate combines release-transition guidance, direct Backchain Until Loop support, and the UI-planning allocation delta; it does not expand this review's authority.

Reviewed `git diff HEAD` for every owned changed source/generated/metadata/test path (full saved patch: `13-action1-final-scoped-diff.txt`), the experiment evidence reader and its structural tests, the prompt/reference routing, and source/generated parity. The independent read-only reviewer reported one material P2 gap: the new supersession rule did not have a regression that revised a plan/source locator then cold-recovered a later packet with replacement precedence while retaining immutable producer evidence as historical. It found no source/generated parity, correctness, or package-metadata defect.

## Change

Added `test_ui_supersession_handoff_keeps_replacement_current_after_cold_recovery` in the owned `test/shiploop-v3-guidance.test.py`. Its synthetic parent/Improve transition keeps the original seed result in `improve_results`, imports a reviewed final plan with a replacement locator and explicit precedence, then cold-recovers through `prepare` and `select-work` to `step-plan`. It asserts that the current packet carries the revised context and no longer presents the original locator/context as current. It also asserts the exact normalized Improve handoff clause. No production source or generated view changed in this action; no commit, push, merge, study completion, or broad suite was run.

## Checks and evidence

- `10-action1-guidance.stdout.txt`: the first focused run failed because the new fixture skipped the real `select-work` transition. The correction was made before another callback.
- `11-action1-guidance-after-fix.stdout.txt`: the second focused run failed only because a prompt assertion compared wrapped text literally. The assertion was normalized before another callback.
- `12-action1-guidance-final.stdout.txt`: `DEVELOPER_DIR=/Library/Developer/CommandLineTools PYTHONDONTWRITEBYTECODE=1 python3 -B test/shiploop-v3-guidance.test.py` passed all 18 tests; stderr is adjacent.
- `git diff --check HEAD` passed after the final edit.
- `diff -q` confirmed source/generated equality for `SKILL.md`, `references/behavioral-requirements.md`, and `scripts/shiploop_navigator_v3_prompts.py`.
- `shasum -a 256` matched the current behavioral guide and frozen candidate-3 guide at `5d9d07c1c7d38665370d0e4531c8b9e5342700ff1fb62a9d21975ceb6a50e909`.
- Root's current-source focused record remains `<study>/integrated-focused-checks.json`; it predates this test-only addition. The prior broad aggregate at `<study>/hermetic-all.log` passed but is pre-integration evidence, so it is not claimed as final integrated CI.

`test/experiments/shiploop_ui_allocation/__pycache__/` remains ignored by the repository and was not staged or altered. The browser report remains capability-only evidence and is not treated as live deployment or study-completion proof.

## Assessment

Classification: **non-trivial**. A material regression coverage defect was found and repaired, so the trivial-review streak must remain/reset to zero. Exit: **unsatisfied** because two later distinct full trivial-only reviews are required, and the root-owned post-push exact-commit CI remains pending. Continuation: **allowed**; no blocker or user stop applies.

For the next action, re-read seven full current commit messages, review the final scoped candidate rather than replaying this repair, recheck the source/generated views and relevant current focused evidence, preserve all root-owned/unrelated work, and record a distinct review. The active runtime state and latest packet are `/var/folders/_n/cth41tgs171367b_gghs0kgm0000gn/T/innerloop-px3tcy1_.json` and `08-action1-next.stdout.raw.json`; action 1 must be completed with its exact callback before following the returned action.
