# Three complementary artifacts

Reuse established names and organization when they serve these roles. Otherwise
use the structure below. Make scope, as-of source identity, evidence labels and
verification limits discoverable from every file (a link to one provenance block
is enough). Empty sections can say “not found in the inspected scope,” “unknown,”
or “not applicable” with a reason. A search miss is not proof of global absence.

## spec.md — externally observable contract

- Purpose, callers, product boundaries and public entrypoints.
- `## Requirements`: stable `R-<n>` records for material capabilities. Label
  recovered records `Status: observed` or `Status: documented`; use `accepted`
  only with an acceptance source. Retain inputs/options/defaults, outputs,
  errors, ordering, state and observable edge conditions. Public names and
  signatures are part of a library's contract.
- `## Non-functional requirements`: separate documented constraints from
  measurements and unverified claims. Name operating conditions; a benchmark
  script is not a measured guarantee.
- `## Coverage and unknowns`: map material surfaces to records; retain
  discrepancies and excluded scope.
- `## Retired`: preserve prior IDs and reasons; do not renumber on refresh.

Internal mechanisms do not become requirements merely because they exist. A bug
can be an observed quirk without becoming accepted intent. Link maintained API
and spec sections instead of duplicating them.

## environment.md — reproducible operation and verification

- `## Targets and runtimes`: declared requirements, CI matrix and locally
  exercised versions as separate facts; runtime/development/optional dependencies,
  lockfile availability, OS/tools and working directory.
- `## Commands`: setup, build, run, tests, lint/types and release/deploy/rollback
  if present. Record exact invocation, cwd, prerequisites, source, effects,
  executed/not-run/blocked/failed result and log or other evidence. An attempt is
  not a passing suite. Explain adaptations to CI commands. Never publish merely
  to fill the table.
- `## Harnesses and suites`: locations, coverage, gaps and invocations. Local
  success is distinct from the CI matrix, browser support, packaging correctness
  and external integration behavior.
- Configuration: variables/flags/files, defaults and precedence; credential
  aliases/mechanisms only, never values or code assigning values.
- Access/platform facts and unknowns: external systems, available access,
  fixture scope, skipped obligations and refresh triggers. Say when there is no
  standalone application or deployment in scope.

Keep command logs outside tracked source where practical. Record resolved
dependencies when there is no lockfile; a later resolution may differ. Do not
fabricate working commands for a missing toolchain.

## architecture.md — ownership and consequential choices

- `## Stack`: main technology choices and dependency roles; link runtime
  versions and commands in environment.
- `## Structure`: entrypoints, responsibilities and data/control flow. Use a
  compact ownership table or diagram to show state and boundary crossings.
- `## Conventions`: evidenced placement, layering and extension patterns.
- `## Interfaces and boundaries`: module/storage/protocol boundaries,
  configuration ownership and error propagation, including swallowed errors or
  deferred writes; link observable detail in spec.
- `## Real-boundary checks`: what local/static checks cannot establish and which
  component or maintainer role would verify it. Mark unknown ownership unknown.
- `## Decisions`: stable `AD-<n>` records with choice, status (observed,
  documented, accepted or inferred), embodiment evidence, rationale labeled
  **stated**, **inferred**, or **unknown**, and consequences. Historical
  alternatives need evidence; otherwise say they were not recovered.
- `## Superseded`: retain replaced choices and evidence for replacement.

Do not reconstruct an imaginary ADR history. Code embodies a choice without
proving when it was made or which alternatives the author considered. A snapshot
can yield useful architecture even when history is shallow or absent.
