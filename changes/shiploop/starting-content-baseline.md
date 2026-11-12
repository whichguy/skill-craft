---
bump: patch
---
Capture the exact starting spec and architecture bytes (or absence) in one atomic run-local snapshot before recording
the captured HEAD, bound into that snapshot. Pre-init owner edits no longer appear as this run's changes. Diff each file separately without external diff,
text conversion or renames, preserving new-file pointers. Never recapture on resume. A valid snapshot repairs only a missing or malformed HEAD pointer using its original
binding; valid conflicting pointers and malformed or unbound snapshots make the diff unavailable. Keep snapshots
byte-exact and replace undecodable diff bytes only in rendered text so ordinary UTF-8 Markdown/HTML writes and print
remain safe. Existing HEAD-only runs retain their legacy comparison. No product Git writes are needed.

Final review correction (2026-11-11): repeated `init` and `next` now call the public snapshot-only
`repair_baseline_pointer` after saved-state and retry-option validation, under the existing run lock and before
dispatch. It never captures working bytes, leaves absent snapshots and legacy HEAD-only runs alone, validates the
whole snapshot before repairing its bound HEAD, and preserves valid conflicts. Malformed evidence and publication
failures return a note. `status` and `report` do not call recovery. Focused symlink tests preserve content-only
comparison: dangling reads at the leaf or a parent directory are unavailable, and failed initial reads publish neither
artifact. A readable directory link whose target becomes unavailable also makes the current diff unavailable.

Validation performed directly, without model children; edits remain uncommitted. All commands below ran from
`/Users/dadleet/src/skill-craft-stage-repairs-20261111`.

Fail-first, before production wiring:

```sh
python3 -B test/shiploop-handoff.test.py StartingKnowledgeTests.test_cli_resume_repairs_original_pointer_without_recapture StartingKnowledgeTests.test_cli_resume_without_artifacts_never_captures_current_bytes StartingKnowledgeTests.test_cli_resume_reports_invalid_snapshot_and_pointer_write_failure StartingKnowledgeTests.test_dangling_link_read_failure_leaves_no_partial_baseline StartingKnowledgeTests.test_readable_link_snapshot_tracks_content_only
```

The first invocation ran 5 methods: 5 failures and 2 errors (the test read deliberately corrupt pointer bytes as UTF-8).
After changing that assertion to compare bytes, the same command ran 5 methods with 7 expected assertion failures and
no errors; recovery and its diagnostic were absent, while no-artifacts and symlink controls passed. Raw logs:
`/tmp/shiploop-final-review-fail-first.log` and `/tmp/shiploop-final-review-fail-first-v2.log`.
After wiring, `python3 -B test/shiploop-handoff.test.py StartingKnowledgeTests` passed 26 methods, before adding the
read-only/conflict CLI and direct StorageError seam tests.

Final full suites (each exit 0, no failures/errors/skips):

- `python3 -B test/shiploop-consumer-delivery-cli.test.py` — 5 tests passed; 2.98 s wall.
- `python3 -B test/shiploop-handoff.test.py` — 166 tests passed; 72.78 s wall.
- `python3 -B test/shiploop-knowledge.test.py` — 163 tests passed; 24.44 s wall.
- `python3 -B test/shiploop-navigator-contract.test.py` — 149 tests passed; 181.08 s wall.
- `python3 -B test/shiploop-rehydration.test.py` — 17 tests passed; 2.45 s wall.
- `python3 -B test/shiploop-workspace.test.py` — 99 tests passed; 188.56 s wall.

Both six-suite runs passed all 599 tests. The first run's whole-tree fingerprint changed while the separately owned
`shiploop_stage_spec.py` also became modified; its logs are retained, but it is not a stable-source verification.
The second run recorded identical pre/post per-file hashes of tracked source. Exact commands, exits, timings,
raw logs, and pre/post file manifests are in `/tmp/shiploop-final-review-verification-stable/`; the initial run is
in `/tmp/shiploop-final-review-verification/`. No other owner's edits were reverted. `git -C
/Users/dadleet/src/skill-craft-stage-repairs-20261111 diff --check` passed. No release or host changes were made.
