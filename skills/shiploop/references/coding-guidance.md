# Coding guidance

Use the active packet, accepted requirements, and repository evidence. They
control owner, stage, allowed edits, callback, and order. Locators let workers
retrieve needed cards.

## Select guidance

At planning and at a relevant execution or review boundary, inspect the actual
entry point, callers, requirements, tests, versions, and examples. Select a
practice card for a changed concern; select a platform card after identifying
the runtime, artifact, boundary, and version. A mixed change can need several.
Reuse current tools and contracts before a new dependency or framework.

Record applicable decisions and material unknowns, not `N/A` boilerplate for
every card. A card is a prompt to make a consequential decision explicit; it
does not create a new state machine, security program, or test layer.

## Decision record

Before product edits, retain a compact accepted plan in the existing step-plan
or authorized note: outcome and invariants; changed responsibility and
contract; reuse or augmentation; applicable operational decisions; ordered
edits; independent checks; source `evidence_refs`; readiness, completion, and
revalidation. Planning records intended work; it does not edit the product.

Run the authorized existing baseline before feature edits and retain failures as
prerequisites. A pass establishes initial readiness only; revalidate when the
affected step begins and after material discovery, revision, or environment
change.

## Conditional index

| Read this card | When the change involves |
| --- | --- |
| [Existing behavior](coding-practices.md#existing-behavior) | Established path or precedent. |
| [Documentation](coding-practices.md#documentation) | Contract, recovery, public behavior, or example. |
| [Libraries](coding-practices.md#libraries) | Dependency, helper, adapter, or upgrade. |
| [Composition and layers](coding-practices.md#composition-and-layers) | Ownership, boundary, or entry point. |
| [Flyweight and shared resources](coding-practices.md#flyweight-and-shared-resources) | Shared data or repeated cost. |
| [State](coding-practices.md#state) | Mutation, persistence, cache, concurrency, or recovery. |
| [Security](coding-practices.md#security) | Trust boundary, identity, permission, input, or sensitive data. |
| [Notifications](coding-practices.md#notifications) | Work acceptance, delivery, alerts, or status. |
| [Logging and debugging](coding-practices.md#logging-and-debugging) | Failures, diagnostics, telemetry, investigation. |
| [Tool output as evidence](coding-practices.md#tool-output-as-evidence) | Filtered or shortened output used for a decision or verification. |
| [Agent and experiment budgets](coding-practices.md#agent-and-experiment-budgets) | Agent execution, paid trials, retries, or usage limits. |
| [Localization](coding-practices.md#localization) | User-facing text, messages, or locale-dependent formatting. |
| [Feature flags](coding-practices.md#feature-flags) | Rollout, experiment, operations, or removal. |
| [UI](platforms/ui.md) | Rendered interaction, state, accessibility, or artifact. |
| [Google Apps Script](platforms/apps-script.md) | Server, HTML Service, trigger, or deployment boundary. |
| [Salesforce](platforms/salesforce.md) | Apex, LWC, permissions, transaction, or cache boundary. |
| [Python](platforms/python.md) | Runtime, subprocess, resources, async work, or automated fix. |
| [Bash](platforms/bash.md) | Script, command boundary, cleanup, or pipeline behavior. |

## Execute, review, and hand off

The packet controls authority and stage order. Implement the smallest coherent
change, preserve failure causes and cleanup, and use the correction route for a
scoped revision. Review the diff and affected consumers against the plan; use
an independent expected outcome and label each check's observed scope. A local
test does not establish a hosted, deployed, or permissioned boundary.

At handoff, keep the accepted plan locator and source `evidence_refs` in the
existing note. Test decisions say whether the decision is unchanged, refined,
or superseded and point to its accepted or revised locator. Do not add ledger
rows, state fields, result schemas, or DAG work to carry this context.

### Small planning trace

Planning only: an existing export command gains `--format json`; preserve the
text default and exit convention, let the current parser validate, reuse the
formatter where it fits, add valid and unknown-format CLI checks, then
revalidate help and docs. It is a plan, not evidence that checks ran.
