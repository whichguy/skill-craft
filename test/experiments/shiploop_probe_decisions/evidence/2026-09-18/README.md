# Probe-decision study evidence — 2026-09-18

Decision: retain the production baseline. Eight workers completed; four blinded
comparisons tied; zero material candidate wins; no replication was launched.
See `analysis.json` and the linked results report in `docs/` for interpretation.

- `frozen/`, `guides/`, `frozen-inputs.json`: exact executed helpers, preregistered
  plan, producer prompts and shared references. They are historical test inputs,
  not production skill bodies.
- `study.json`, `launch-ledger.json`: limits, original hashes, pair identity and
  launch accounting. Original absolute paths describe the experimental checkout.
- `private/`: calibrated facts, family rubrics, mappings, and independent exact
  reconstruction of the rubrics. Do not supply mappings to a blind judge.
- `receipts.jsonl`: complete coordinator-owned workspace request/result receipts.
  Guide reads are retained here; do not give this file to a blind judge.
- `arms/`: intact reports, probe logs, invocation and runner metadata, usage and
  before/after input hashes. Source content also appears in the blind bundles.
- `blind/`: exactly supplied judge packets, compact sources/receipts, and omission
  manifests. Reports are intact. Guide hashes/sizes and absolute paths remain;
  this limits blinding even though no variant mapping was supplied.
- `reviews/`: original verdicts, parsed judgments, input hashes, bounded-review
  transport records and output streams. Successful transport is not a semantic
  pass; all four semantic outcomes are ties.
- `coordinator/`: executed review launcher, independent rubric verifier, and
  source snapshot hashes. The source snapshot includes pre-existing dirty work.
- `verification/`: gateway preflight, targeted tests, initial setup failure,
  serial rerun, isolated parallel continuation, and package-parity logs. The
  serial rerun was interrupted after 73 completed ShipLoop suites because the
  legacy walks were slow. Five more passed in isolated copies. Six remain
  unverified after optional broader validation was stopped; neither a complete
  catalog pass nor a successful monolithic command is claimed.
- `archive-manifest.json`: SHA-256 for every other archived file.

This archive omits duplicated per-worker reference trees, temporary fixture
directories, and worker CLI event streams. Full workspace request/result evidence
is retained in coordinator receipts, and usage is retained in runner metadata.
No real service, account, installation, deployment or public release was tested.

The executed adapter's private rubric digest was stored in mutable state. The
independent verifier reconstructed each packet byte-for-byte from frozen cases
and calibration without changing it. Its receipt records whether each review
had already launched. The current source adapter additionally enforces that
reconstruction and writes judge-packet hash bindings; it is intentionally not
substituted for the historical helper here.
