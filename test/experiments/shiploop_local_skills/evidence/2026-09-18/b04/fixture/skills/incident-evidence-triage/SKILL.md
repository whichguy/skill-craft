---
name: incident-evidence-triage
description: Derive an incident-triage decision from a current evidence bundle using the repository's authoritative incident contract.
---

# Incident-evidence triage

Use this repository-local skill when an incident's current evidence bundle must
be assessed under its authoritative incident contract. It is separate from
[release-evidence-triage](../release-evidence-triage/SKILL.md): an incident
assessment does not make a release decision or authorize a deployment.

## Required inputs

- `contract`: required repository-relative Markdown path to the applicable
  incident-evidence contract; the current authority is
  [`docs/incident-contract.md`](../../docs/incident-contract.md).
- `bundle`: required repository-relative JSON path supplied for the incident.
- `output`: required repository-relative JSON destination defined for the task
  by the contract or its invoking work item.

Re-read the contract before every use. It defines the request identity, target,
required checks, selection rule, output schema, and decision semantics. Do not
copy or infer those details from a previous incident.

## Procedure

1. Read the contract and bundle together, then resolve the incident identity,
   target, and required checks from their current contents.
2. For every required check, discard nonmatching receipts and select the
   matching receipt with the greatest numeric attempt. Record the contract's
   missing-receipt representation when no matching receipt exists.
3. Write only the contract-defined local decision artifact, preserving the
   required-check order and separating incident triage from release or
   deployment authority.
4. Independently recompute the selected receipts from the bundle and compare
   that result with the written artifact. A later non-passing attempt controls
   over an earlier passing attempt when the contract says to select the latest.

## Validation and boundaries

Confirm that the artifact parses as JSON, has exactly the current contract's
required shape, preserves ordering, and matches an independent recomputation.
If the contract, bundle, or matching evidence is unavailable or malformed,
report that gap rather than inventing a clear incident state. This skill only
performs local incident triage; it does not authorize a release or deployment.
