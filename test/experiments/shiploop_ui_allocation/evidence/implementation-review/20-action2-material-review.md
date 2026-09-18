# Improve action 2 — evidence-label review

Candidate reviewed: `5a073503bcfe35e620461498b3fa438afe94d0bc` plus the same authorized mixed scoped delta. Frozen base remains `7f8ef5d7508c3088f628a90d326fb025f293be15`. Root reported that newer origin `bf6fe17` is additive probe/docs/inventory work only and instructed this run to finish without rebasing; it is not included in this review candidate.

## History and review

Read the latest seven full messages in `17-action2-history.txt` (the same reachable seven commits at current HEAD). Reviewed the experiment reader's state projection and its focused structural tests. A fresh independent read-only reviewer confirmed that `accepted_producer_count` was materially misleading: it counted all entries in the navigator's accepted-result ledger, even synthetic fixture predecessors, while the reader explicitly disclaims producer-execution proof. The reviewer also rechecked the action-1 supersession regression and found no concrete defect.

## Change

Renamed the read-only report field from `accepted_producer_count` to `accepted_stage_record_count` in `test/experiments/shiploop_ui_allocation/evidence.py`. The replacement accurately describes persisted accepted state records and does not imply verified producer execution. Updated the focused tests to prove the count is zero for a blank state and one for both a synthetic-predecessors-only record and a real imported record, while their import classifications remain distinct. No source skill, generated view, fixture, snapshot, README, or root-owned study artifact changed; no sync was needed.

## Checks and evidence

- `18-action2-evidence-reader.stdout.txt` records the initial 11-test PASS after the rename.
- `19-action2-evidence-reader-final.stdout.txt` records `DEVELOPER_DIR=/Library/Developer/CommandLineTools PYTHONDONTWRITEBYTECODE=1 python3 -B test/experiments/shiploop_ui_allocation/test_evidence.py` passing all 11 focused tests after the independent-review addition; stderr is adjacent.
- `git diff --check HEAD` passed.
- No `accepted_producer_count` source reference remains in the experiment implementation/test scope.
- Action-1 current focused evidence remains `12-action1-guidance-final.stdout.txt` (18 passing), with source/generated parity and frozen candidate-3 guide hash documented in `14-action1-material-review.md`. Root's broader focused record remains `<study>/integrated-focused-checks.json`; the old aggregate passed only before integration and remains non-final.

Ignored `__pycache__` remains outside the candidate and untouched. The browser report remains capability-only, and neither this reader repair nor its structural tests prove a live producer, deployment, or study completion.

## Assessment

Classification: **non-trivial**. The report's consumer-visible terminology changed to remove an execution implication; even though it preserves the underlying count, it is a warranted behavior/claim-boundary repair and resets the clean-review streak. Exit: **unsatisfied** because two new distinct trivial-only full reviews are still required and root's exact-commit CI remains pending. Continuation: **allowed**.

Next action must inspect the current `5a073503` scoped candidate and seven full current messages anew, not replay either repair. It must preserve the no-commit/no-push and root-owned-file constraints, retain this external record, and complete one distinct full review before reporting through the active runtime state at `/var/folders/_n/cth41tgs171367b_gghs0kgm0000gn/T/innerloop-px3tcy1_.json`.
