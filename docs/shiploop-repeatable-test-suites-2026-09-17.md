# ShipLoop repeatable test-suite guidance

## Decision and scope

Adopt prompt/reference guidance for durable test suites. Existing graph stages,
result schemas, test runners and Improve ownership already provide the required
structure. No new harness dependency or workflow controller is needed.

The review found explicit case planning, authoring, RED/GREEN, refinement,
regression, integration and system checks, but weaker instructions for suite
retention, fixture lifecycle, test discovery and repeatable execution across runs.
The canonical [repeatable-suite guide](../skills/shiploop/references/repeatable-test-suites.md)
now supplies those decisions; existing records retain compact locators and facts.

## Coverage through the workflow

| Area | Required decision or output |
| --- | --- |
| Initial test strategy | Select/revalidate major local/remote harnesses and prerequisites; keep focused, smoke and full commands and whole-suite cost. |
| Each INNER step plan and test specification | Identify setup, independent assertions and teardown, or justified absence; choose fixture ownership and suite membership. |
| Test authoring and refinement | Retain executable cases and helpers, including required remote-resident definitions/registration and invocation; verify real runner selection, preserving independent oracles. |
| Regression and integrated/system checks | Run the retained suites at their required boundary; examine residue, order and concurrency when relevant. Smoke results remain scoped. |
| Actual Improve | Review test assets, lifecycle, isolation, registration, repeatability and cost. Keep expected RED and stage edit boundaries. |
| Carry-forward and future runs | Retain test/harness/case locators and rerun instructions in repository knowledge; revalidate old evidence. |
| Compatibility protocols | Strengthen existing guidance and step-plan records without changing saved scheduling or substituting v3 Improve ownership. |

The source skill and generated plugin carry the same guide. Navigator packets
expose its package-owned locator to fresh contexts, including actual Improve
handoffs. The three existing navigator/packet regression suites retain the new
checks and already belong to the full hermetic inventory.

## Evidence and tradeoffs

[pytest fixture guidance](https://docs.pytest.org/en/stable/how-to/fixtures.html)
describes reusable setup/cleanup, scoped fixtures and partial-setup cleanup
hazards. [Playwright fixtures](https://playwright.dev/docs/test-fixtures) show
that expensive infrastructure can be shared while each test retains isolated
state. Its [parallelism guidance](https://playwright.dev/docs/test-parallel)
identifies collisions through shared data and paths and the need for independent
tests. These support the design; they do not mandate either framework.

Fixture sharing can reduce repeated setup cost, but scope alone cannot establish
noninterference. Isolate when uncertain; measure whole-suite cost, including
per-worker setup and cleanup, before choosing a broader fixture lifetime. Keep
cheap focused checks useful without silently omitting required system coverage.

## Validation boundary

Deterministic tests establish packet routing, recovery, preserved graph ownership
and availability of guidance. Independent scenario reading evaluates bounded
interpretation choices. Neither proves universal future model compliance or
live generated-application behavior. No remote deployment/publication is part
of this change.

## Local and remote test locations

Planning distinguishes local checks, a client checking a deployed target, and
remote-resident tests executing within the remote runtime. Select the available
framework and discover access, readiness and deployment prerequisites. Retain
remote test definitions or platform-owned export/locators, registration, approved
installation/invocation, result retrieval and lifecycle. Evidence identifies both
the deployed target and test revision. A full route can combine local and remote
parts; unavailable required remote checks remain blocked/unrun even if local
checks pass. Existing deployment ownership and graph boundaries remain intact.

## Observed validation

- Before the remote-location addition, new assertions failed on the original
  baseline and the three focused suites passed 14, 35 and 40 tests (89 total).
  The concurrent-source merge then passed 17, 37 and 40 (94 total); all 35
  current protocol checks and five reference-routing checks also passed.
- Before the remote-location addition, the frozen core group passed all 23 entries.
  All 79 ShipLoop suites completed:
  78 passed and one exposed a pre-existing actor-map expectation mismatch that
  reproduces on the baseline. The corrected current protocol suite passed all
  35 checks separately. The original failed log remains intact; this is not a
  claim that the unmodified frozen aggregate was green.
- An actual standalone Improve pilot reviewed deliberately defective test
  assets: leaking/shared fixtures, a weak oracle and incomplete full registration.
  It retained three independent stateless cases, removed unnecessary setup,
  corrected suite selection, and reached adapter state `done` after two clean
  reviews. Twelve independent outcome checks cover discovery, focused/smoke/full
  runs, reordered/repeated execution, no residue after injected failures, and
  rejection of deliberately wrong behavior in a disposable copy. Production
  bytes remained unchanged. This is a bounded test-assets pilot.
- Five independent fictional fixture scenarios supported the intended lifecycle
  decisions; they establish bounded interpretation evidence only.
- The later local/remote assertions fail on the pre-addition candidate. Updated
  isolated suites pass 15, 36 and 40 tests (91 total); the final prepared merge
  with concurrent changes passes 18, 38 and 40 (96 total). Current reference
  routing (5), system-test contracts (8), scoped Ruff and generated parity pass.
  The broad sweep above predates this guidance-only addition; it was not rerun
  because graph, runtime and result contracts are unchanged. Two additional
  fictional remote scenarios informed the framework/availability distinction.
  No remote system was deployed or tested by this guidance-only change.
- Standalone Improve completed two consecutive clean reviews after the material
  local/remote addition: an independent review and a distinct history-informed
  self-review. The scoped return preserves concurrent source edits and the index.

Exact logs, candidate identities, preserved failures, the rerunnable pilot verifier,
and guarded-return records are retained in the local task evidence directory:
the operator's local-only repeatable-test study capture directory (not published).
