# Independent test-strategy review

**Reviewer:** fresh read-only independent reviewer `/root/allocation_new_producer/test_strategy_independent_review`.

**Scope supplied:** `run/notes/test-strategy.md`, the specification, cited fixture/evidence files, test traceability, harness/suite commands, fixture isolation, expected-RED, real-boundary limits, source-edit authority, and whether the plan claims unrun tests.

**Material findings:**

1. The declared smoke command selected all tests in three files while claiming one representative assertion per category. It needed a true subset and exact membership.
2. AC-01’s requirement that a mixed authorized view be communicated in the ledger lacked a traceable local state/render-model assertion; T-01 only covered selecting a frozen ID.
3. The required markup-like API-string rendering follow-up needed a stable test ID, oracle, and suite placement before implementation so it could not be silently omitted.

**Residual limits retained:** the strategy correctly separates local Node/fake/preview observations from real API, embedded target, and consumer proof; target CSP/server-runtime claims remain externally unverified.
