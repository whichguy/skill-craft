# Repeatable-suite behavioral pilot — 2026-09-17

Decision: retain the repeatable-suite guidance and these reusable experiments,
but **defer a comparative adoption or reliability claim**. Both guidance arms
produced meaningful suites. The candidate exposed a valid SQLite contract defect
that our reference calibration missed. All three original candidate Improve runs
also hit a Git-write restriction. More expensive full-workflow and feature-chain
expansion is deferred until those experiment preconditions are resolved.

## What actually ran

Six fresh Codex CLI sessions exercised one matched pair for each of three fixtures.
The baseline contains prior test-case guidance; the candidate adds only the new
repeatable-suite reference. Both arms received the same natural job and actual
frozen standalone Improve skill. Prompt provenance is in `prompts/provenance.json`;
the immutable runtime snapshot and raw traces remain in the private study record.
This is a component pilot, not an installed-package A/B or complete ShipLoop run.

| Fixture | Baseline full / focused / smoke | Candidate full / focused / smoke | Observed result |
| --- | --- | --- | --- |
| Stateless price | 9 / 9 / 4 | 12 / 8 / 5 | Both repeat/reverse and reject seeded defects; no setup needed |
| SQLite catalog | 11 / 11 / 5 | 13 / 6 / 3 | Baseline green; candidate retains a valid overflow RED above SQLite's integer range |
| Missing slug behavior | 8 / 8 / 4 | 10 / 4 / 4 | Both preserve expected RED, pass against the conforming reference and reject its mutant |

All six preserve their protected production and SPEC bytes and register retained
cases in full discovery. Independent copied executions check subset routes,
repeat/reverse membership, a deliberately failing full-route probe and seeded
mutant sensitivity. Five pass the mechanical rubric. The SQLite candidate fails
the candidate/reference-green predicates because **both implementations overflow
at `2**63`**. Independent semantic review confirms its success oracle follows
the unbounded public contract. This is inadequate reference coverage, not an
invalid test. The original failure and reference remain unchanged.

Independent source review verified literal assertions, relevant lifecycle
ownership and representative mutations. The baseline SQLite suite also rejects
a no-op close implementation before fallback cleanup. This is bounded audit
evidence, not exhaustive mutation coverage. The simulated startup cost is 0.15
seconds, so these trials do not establish savings for expensive infrastructure.

All original baseline Improve adapters completed with two distinct no-change
reviews. All original candidate adapters paused when scoped commits could not
create `.git/index.lock` in the workspace-write sandbox. Those three attempts
remain in the denominator. An exit-zero CLI process does not override them.
Separate fresh-context no-commit reviews are recorded below; they cannot repair
the original A/B outcomes retrospectively.

See `observations/local-originals.json` for counts, mechanical checks, adapter states,
elapsed time, terminal usage and raw-artifact hashes; `observations/local-semantic-audit.md`
contains the independent semantic findings.

## Separate fresh-context reviews

The three candidate outputs were copied into new seeded repositories without
prior runtime state. Fresh sessions received retained repository instructions,
the same actual Improve runtime, and an explicit no-stage/no-commit policy.
These are follow-ups with changed review preconditions, not replacement A/B
attempts or production implementation requests.

- Price: retained all 12 original test IDs, fixed empty-selection success and
  filtered import-error handling, and added four runner regressions plus an
  independent `format_price(10**5000)` boundary test. Full now has 16 passes and
  one valid conversion-limit error; the runner regressions pass. Improve paused
  at cycle 1 with zero clean reviews because immutable production still violates
  its unbounded contract. Independent copied checks confirmed these findings.
- Expected RED: retained the original contract assertions and added four passing
  runner regressions for the same defects. Full has 14 test methods with the
  same 68 failing product subtests. Actual Improve completed at cycle 3 after
  a material cycle and two distinct no-change reviews. It disclosed that an
  independent reviewer was unavailable and used self-review.
- SQLite: fixed `--list --suite` accidentally executing tests and added two
  runner regressions. Full has 14 passes and the same valid `2**63` error;
  all six runner tests pass. Improve paused at cycle 1 with zero clean reviews
  because the production repair is outside the immutable authoring scope.

All three follow-ups preserved protected files and avoided staging/commits.
Their independent histories and terminal measurements are in
`observations/followups.json`. The seven byte-preserved runnable snapshots under
`samples/` retain all six original outputs plus the improved expected-RED suite;
their manifest and README identify commands and expected nonzero outcomes.

The later feature implementation experiment did not run: initial promotion
gates were unmet. These follow-ups show actual cold-context suite discovery and
review, not create-to-feature lineage or a complete ShipLoop delivery.

## Real remote execution

A fresh authoring session built retained CommonJS test definitions for the known
Apps Script interface. It completed actual Improve. Its 11 local simulation
checks pass, including setup/assertion failures, partial acquisition, cleanup
failures, missing services and selection validation. The source and local checks
are retained in `remote_fixture/`; the normal hermetic check runs them without
network or a model. A separate independent review found no actionable source gap.

The exact two modules were uploaded to one fresh private project. Six remote
selections completed: smoke, full twice, reverse, and one focused stateful case
twice. The first five independent state inspections found zero suite-owned
properties. The sixth inspection timed out; subsequent reconciliation confirmed
all 22 remote/local files matched, but another inspection was blocked before
execution by browser authorization. We stopped and soft-trashed the project.

This is **partial real remote evidence** through the server's HEAD web-app fallback.
Remote setup-failure/assertion-failure controls, unknown-ID rejection, final
recovery full run and the final independent empty-state check remain unverified.
Local simulations do not fill these gaps. No existing application was changed,
and no browser, staging, production, concurrency or forced-termination behavior
was verified. See `observations/remote-pilot.md` and `observations/remote-selections.json`.

## Learnings and next decision

1. Revalidate the evaluator as well as the harness. A reference that passes a
   small calibration can still violate an unbounded public contract. Preserve
   a new valid RED and repair/version the fixture or reference before comparing
   more arms; never reinterpret the test as wrong merely to obtain green.
2. Resolve the review commit policy before launch. Give both arms the same
   explicit no-commit policy in a Git-read-only sandbox, or use an environment
   that supports authorized scoped commits. Do not bypass the sandbox after a
   blocked result.
3. Assess test-authoring success separately from implementation success. Actual
   Improve must preserve valid failures. Newly discovered production defects
   may prevent its green convergence and require a separately authorized
   implementation step or an independently validated expected-RED contract.
4. Local and remote are separate execution obligations. Revalidate remote
   availability immediately before the next run; authenticated discovery and
   earlier execution do not guarantee later execution authorization.

No production prompt rewrite or new persistent integration follows from this
pilot. Before expansion, version the corrected evaluator/commit contract, rerun
matched trials, and finish the remote negative controls on a new disposable
target with the required authorization already available. A later complete
ShipLoop create-to-feature campaign remains a separate experiment.

## Measurement and audit limits

Configured `gpt-6-astra` / `ultra` was pinned; CLI `0.154.0` did not expose an
independent observed model identity in these result events. Runtime snapshots
remained unchanged. Terminal input, cached input and output usage are separate
measurements; the incomplete arms do not support a cost-efficiency verdict.
The first price job misspelled `pricing.py` as `price.py` identically in both
arms; both found and preserved the actual protected file. Other fixtures used
neutralized jobs. This does not confound either within-pair comparison, but it
limits pooled claims across fixtures.

The evaluator was improved while interpreting results: initial stdout parsing
misread unittest subtests/docstrings; clone-local startTest observation now
checks actual parent-case execution. A final regrade preserves the earlier
false rejection. Endpoint immutable-file guards cannot detect transient restored
writes or in-memory replacement; source/transcript audits remain necessary.
An early observer-containment test also exposed macOS `/var` versus `/private/var`
resolution and lacked a fake-CLI tripwire. Its failed attempt is retained without
model-success credit; the repaired negative test blocks CLI invocation. Initial
live launcher bytes were not fingerprinted, so only their captured inputs,
invocations and frozen skill/runtime identity have that original binding.

Private evidence lives at the task's `shiploop-test-pilot-xgt7naw0` study directory.
Raw model/MCP traces, target identifiers and account-bearing logs are intentionally
excluded from the repository. Sanitized results are observational records, not
cryptographic attestation or a universal prompt-reliability guarantee.
