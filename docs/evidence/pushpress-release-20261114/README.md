# Publication of pushpress 0.1.1 (journal Round 15, 2026-11-14)

`pushpress` 0.1.1 and `skill-craft` 2.37.3 were published to `main` of the public repository by one non-forced push of the release commit, after the rehearsal of Round 14. The journal's Round 15 has the order of the steps and the findings; this folder keeps the raw results.

## Files

- `release-push-receipt.json`: the receipt that `scripts/release-push.py` printed (frozen head, tree, previous remote head, three checks passed, the push line).
- `release-output.txt`: the output of `scripts/release.py` that cut the release commit.
- `core-suites.tsv` and `core-receipt-summary.txt`: the 61-suite `core` group on the exact release tree, from the run-all receipt (absolute paths dropped).
- `summary.json`: the identifiers, the checks, the scan and the after-push verification in one place.

## Not kept

The scan script and its control file (they hold the owner's and the gym's names as patterns), the full run log (it carries machine paths) and the disposable install used for the after-push check.

## Limits

The CI-only groups (`shiploop-1` to `shiploop-3`, `e2e-apparatus`, `python-floor`, the browser fixtures) were not run locally; they run on the pushed commit, and the CI result is in the journal. No host was refreshed.
