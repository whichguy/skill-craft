# Salesforce platform-guidance experiment

This is a bounded, local evidence pack for a possible ShipLoop conditional platform card. It does not authenticate to, query, deploy to, or modify a Salesforce org.

Run the complete local check from this directory:

```sh
python3 run_checks.py
```

The command uses only Python's standard library and Node's built-in test runner. It verifies that the checker accepts the reference fixtures and rejects distinct seed and mutant fixtures.

| Area | Fixtures | What the local check establishes | What it cannot establish |
| --- | --- | --- | --- |
| Apex security intent | `fixtures/apex/*security*.cls` | The deliberately small scanner distinguishes explicit user-mode intent from missing intent and an explicit system-mode mutant. | Apex compilation, API-version behavior, sharing, CRUD/FLS enforcement, permissions, or a real denial. |
| Apex bulkification | `fixtures/apex/*bulk*.trigger` | The scanner rejects SOQL/DML visibly nested in a loop and accepts a collection/query/update shape. | Runtime governor consumption, trigger recursion, query selectivity, locks, flows, or managed-package work. |
| LWC state and async cache boundaries | `fixtures/lwc/*.mjs` | Node executes a reference model that replaces state and invalidates the selected cache only after a successful mutation; it rejects in-place-state and wrong-order/wrong-cache mutants. | LWC rendering, wire adapters, LDS, DOM timing, accessibility, browser behavior, or org data. |

The local Salesforce DX project at `/Users/dadleet/src/sf-tic-tack-toe` declares `@salesforce/sfdx-lwc-jest`, but its local `node_modules` test binary is absent. The installed Salesforce CLI lists the LWC test plugin as an uninstalled JIT plugin. This experiment deliberately does not install it. `node --test` is real JavaScript execution, but it is a model check, not an LWC Jest result.

Read [research.md](/Users/dadleet/src/skill-craft/test/experiments/shiploop_platform_guidance_20260918/salesforce/research.md) for source-backed guidance, contrary evidence, and the exact real-org validation needed before a security or governor-limit claim.
