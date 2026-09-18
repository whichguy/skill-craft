# Test-strategy Improve review one

## Candidate, scope, and history

Reviewed `run/notes/test-strategy.md` and its requirement/test evidence at product HEAD `ec3243d658e24304b306749bc361869154fc4660`. The only permitted correction location is this child evidence tree; the strategy/run notes and all product files remain immutable during the active child. Fresh history in `history-cycle-one.stdout.txt` contains the single fixture commit and does not authorize a harness, test, dependency, target, or source edit.

## Material findings and applied record correction

The fresh independent reviewer found three material planning defects, retained in `independent-review.md`:

1. The original smoke command named every test in all three files while claiming to be a subset.
2. AC-01 lacked a local case for mixed returned export states reaching a ledger/display model.
3. The markup-like API-string rendering risk did not have a stable test ID, oracle, or suite placement.

The warranted correction is recorded in `test-strategy-corrected-decision.md`:

- smoke becomes an exact three-case `^smoke:` pattern route, supported by the observed Node runner;
- T-01 gains a deterministic mixed-state display-model fixture and remains paired with T-08 for actual browser rendering;
- T-11 adds the API-string textual-rendering/static-source oracle to `test/static-constraints.test.mjs` and its full local route.

The correction preserves the zero-test baseline, Node-only dependency-free plan, expected-RED boundary, no-product-edit authority, and required-but-blocked real API/target/consumer checks. No product/run-note edit, test authoring, dependency install, harness bootstrap, commit, target operation, deployment, remote request, or consumer validation occurred.

## Classification and handoff basis

This is a completed **non-trivial** planning review because the case map and smoke membership changed materially, even though the correction is confined to child review evidence. Current history/status/source/probe/runner and correction-integrity checks are retained. The next cycle must re-read fresh history and assess the corrected decision alongside the candidate; it needs two subsequent distinct trivial/no-change reviews before completion. Preserve the explicit durable requirements-home, API semantics/persistence, font, static-entry/test-bootstrap, target, and consumer prerequisites.
