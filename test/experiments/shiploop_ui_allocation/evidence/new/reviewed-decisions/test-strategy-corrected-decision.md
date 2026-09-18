# Test-strategy correction decision

This child-only correction supersedes the named planning rows in `run/notes/test-strategy.md`. It makes no product/run-note source edit and does not represent any test as authored or run.

## C-01: real smoke subset

Node `v25.9.0` exposes `--test-name-pattern` (`node-test-name-pattern-availability.json`). Replace the original smoke command with:

```sh
node --test --test-name-pattern="^smoke:" test/export-state.test.mjs test/export-api-client.test.mjs test/static-constraints.test.mjs
```

Required future membership is exactly one test named with the `smoke:` prefix in each listed file: selection/mixed-ledger display model, confirmed-or-reconciled request mapping, and static-source constraint. The full suite remains `node --test`; the focused commands remain unchanged. At execution, retain Node output showing those three selected cases and reject a zero-match/filtered-out smoke result as coverage failure.

## C-02: AC-01 mixed-view traceability

Expand **T-01** in `test/export-state.test.mjs`: use a frozen authorized GET fixture containing at least queued, running, complete, and failed exports plus collection IDs. The oracle is a deterministic local display model that preserves each status label, associates the chosen collection, and performs no request merely because selection changes. The browser rendering of that model remains in T-08; this local case proves the state/display-model contract, not rendered DOM or target behavior.

## C-03: API-string rendering safety

Add **T-11** to the planned `test/static-constraints.test.mjs` suite and the full local route. Its fixture includes collection/status/error text with markup-like content. The source-level oracle must show that client rendering takes API-provided strings through text-node or `textContent` paths rather than HTML parsing/`innerHTML` interpolation; the later T-08 browser procedure must visually confirm literal text behavior. This local source check does not prove API authorization or target CSP, both of which remain T-09/T-10 prerequisites.

## Effect on strategy

The corrected local map is AC-01 → T-01 plus T-08; AC-02..AC-08 retain T-02..T-08; the risk case T-11 joins T-07 in `test/static-constraints.test.mjs`; AC-09 remains T-10 required-but-blocked. The candidate’s zero-test baseline, dependency-free Node choice, expected-RED boundary, fixture isolation, blocked real API/target/consumer checks, and no-source-edit authority are unchanged.
