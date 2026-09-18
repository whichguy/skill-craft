---
name: release-evidence-triage
description: Decide whether a release-evidence bundle is clear or blocked using the repository's current release contract.
---

# Release-evidence triage

Use this repository-local skill when a release decision must be derived from a
current evidence bundle and its authoritative contract. Do not use it to deploy,
approve a deployment, or substitute stale receipts for the current request.

## Required inputs

- `contract`: required repository-relative Markdown path to the current
  release-evidence contract. Read the bundle's workflow before choosing it:
  [`specs/release-contract.md`](../../specs/release-contract.md) is the v1
  authority, while [`docs/release-contract-v2.md`](../../docs/release-contract-v2.md)
  applies to v2 bundles.
- `bundle`: required repository-relative JSON path supplied for the task,
  normally under `data/`.
- `output`: required repository-relative JSON destination defined by the
  contract.

Re-read the contract before each use. It defines the output schema, the resolved
request identity, required checks, and the decision rule; do not hard-code those
details from an earlier bundle.

Example: with `contract=specs/release-contract.md` and
`bundle=data/bundle.json`, write only the contract-designated local output and
then independently recompute the receipt selection.

## Procedure

1. Read the contract and bundle together. Resolve the request identity and every
   required check from those sources.
2. Discard receipts whose identity does not match the resolved request. For each
   required check, select the matching receipt with the greatest numeric attempt;
   record a missing receipt when none matches.
3. Produce the contract-defined decision artifact in its required location and
   order. Keep the release decision separate from any deployment authorization.
4. Independently recompute the selection from the bundle, then compare it with
   the written artifact. Treat a later failed or blocked attempt as controlling
   even if an earlier attempt passed.

## Validation and boundaries

Validate the written JSON parses, has the exact contract-defined shape, preserves
the resolved required-check order, and agrees with an independent recomputation.
If the contract, bundle, or matching evidence is unavailable or malformed, report
the gap rather than inventing a clear result. This skill performs local triage
only; it never provides deployment authority.
