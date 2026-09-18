---
name: incident-evidence-triage
description: Derive a local incident-triage decision from a current evidence bundle and the repository's current incident contract.
---

# Incident-evidence triage

Use this repository-local skill when an incident decision must be derived from a
current evidence bundle and its authoritative incident contract. Do not use it
to decide a release, authorize a deployment, or substitute stale receipts for
the current request.

## Required inputs

- `contract`: required repository-relative Markdown path to the current
  incident-evidence contract.
- `bundle`: required repository-relative JSON path supplied for the task,
  normally under `data/`.
- `output`: required repository-relative JSON destination defined by the
  contract.

Re-read the contract before each use. It defines the request identity, check
order, receipt-selection rule, output schema, and decision rule; do not
hard-code those details from an earlier bundle.

## Procedure

1. Read the contract and bundle together. Resolve the current incident request
   and every requested check from those sources.
2. Discard receipts whose identity does not match the resolved request. For
   each requested check, select the matching receipt with the greatest numeric
   attempt; record a missing receipt when none matches.
3. Produce only the contract-defined local decision artifact, preserving the
   contract-defined check order and separating incident triage from release or
   deployment decisions.
4. Independently recompute the selection from the bundle, then compare it with
   the written artifact. Treat a later failed or blocked attempt as controlling
   even if an earlier attempt passed.

## Validation and boundaries

Validate that the written JSON parses, has the exact contract-defined shape,
preserves the resolved check order, and agrees with an independent
recomputation. If the contract, bundle, or matching evidence is unavailable or
malformed, report the gap rather than inventing a clear result. This skill
performs local triage only; it never provides release or deployment authority.
