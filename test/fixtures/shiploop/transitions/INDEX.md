# Transition sample artifacts

Independent run dirs in `test/shiploop-walk-journal.test.sh` copy these
files to establish each legal edge in `skills/shiploop/references/transitions.json`.
DAG bodies stay in `test/fixtures/shiploop/*.json` (`linear.json`,
`two-root.json`, `single.json` for the one-step first=last walk).

| from | to | artifacts/ files |
|------|----|------------------|
| intake | validate-spec | (init writes `prompt.md`) |
| validate-spec | plan | `environment.md`, `spec-checkable.md` → `spec.md` |
| validate-spec | blocked | `spec-uncheckable.md` → `spec.md` (no `environment.md`) |
| plan | implement | `plan.md`, `linear.json` or `single.json` as `backchain/plan.json` |
| plan | blocked | (reason only; no DAG) |
| implement | residual | drained receipts + `bound-waived.md` or `bound-coverage.md` |
| implement | blocked | (reason + `--resume-to implement`) |
| residual | done | `bound-waived.md` **or** `bound-coverage.md` + `ledger-complete.md` |
| residual | halted | `bound-coverage.md` + `ledger-stopped.md` |
| residual | blocked | (reason + `--resume-to residual`) |
| blocked | validate-spec | `--reason` (clears hashes) |
| blocked | plan | `--reason` (clears receipts) |
| blocked | implement | `--reason` (re-claims running) |
| blocked | residual | drained receipts + `--reason` |
