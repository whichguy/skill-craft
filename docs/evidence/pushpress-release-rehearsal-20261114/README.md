# Rehearsal of the pushpress 0.1.1 release (journal Round 14, 2026-11-14)

If the owner says "publish", does branch `pushpress-card-fixes` (head `2c095996` when the rehearsal ran; it was `7241588b` before the identity normalization noted in the journal) release cleanly on the current `origin/main`, and what would become public?
**Result: it does, and every check passed.** Nothing was pushed, tagged or published: the rehearsal ran in a scratch worktree on a scratch branch, and both were removed afterwards.

## Files

- `release-output.txt`: the output of `release.py --dry-run` on the merged tree and of the real `release.py` run on the scratch branch (it commits locally and never pushes).
- `core-suites.tsv` and `core-receipt-summary.txt`: the 61-suite `core` group on the release tree, from the run-all receipt (absolute paths dropped).
- `scan-summary.txt`: the privacy scan of the 326 files that the release would add, by category, with what each hit is.

## How it was made

1. `git fetch origin`; a scratch worktree on a new branch cut from the head; `git merge --no-ff origin/main` (`3474addc`, 108 commits past the published head, CI success on it).
2. `python3 -B -I scripts/release.py --dry-run`, then `python3 -B -I scripts/release.py` (release commit `8967070e` on the scratch branch).
3. `python3 -B -I scripts/check-release-boundary.py --base origin/main` before and after the release commit, and `python3 -B -I scripts/check-marketplace-packages.py`.
4. `diff -rq skills/pushpress plugins/skill-craft/skills/pushpress` (0 differences), with an identical-pair control (same directory twice, 0) and a must-differ control (against `skills/sport80`, 1).
5. `env -u PUSHPRESS_API_KEY -u PUSHPRESS_COMPANY_ID CLAUDECODE=1 CLAUDE_CODE_SESSION_ID=ci-stand-in bash test/run-all.sh --group core --output <new directory outside the checkout>` (the stand-in markers are the ones `ci.yml` sets), and `node test/pushpress-extractor-harness.js`.
6. A scan of every file that differs from `origin/main` on the release tree.
7. Checks that nothing left the machine: the exact scratch ref and the release commit on the remote, tags on the release commit, and the real branch's head and worktree.

## What was not kept

- The scan script and its control file: they hold the owner's and the gym's names as patterns, which must not be published (the repository's own lint, `lint_text` in `test/pushpress.test.py`, is public and was part of the scan).
- The run log of the core group (it carries machine paths), the scratch branch and the release commit (never pushed; a real release repeats the merge on a newer `origin/main` and cuts its own commit).

## Limits

The groups that CI adds for a full run were not run here: `shiploop-1`, `shiploop-2`, `shiploop-3`, `e2e-apparatus`, `python-floor` (Python 3.9) and the browser fixtures. They run on a pushed commit. `origin/main` moves several times an hour, so the merge and the checks must be repeated right before a real release.
