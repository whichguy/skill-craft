# Conditional coding practices

Read only the section selected by [Coding guidance](coding-guidance.md#select-guidance).
The active packet, accepted requirements, and existing records remain the
source of authority. Each section asks for a decision only when it changes the
work; it does not require a new abstraction, dependency, or record for its own
sake.

## Existing behavior

Trace the requested change from its entry point to observable results and
identify adjacent callers and consumers. Run the authorized existing baseline
before feature edits, classify any failure, and retain it as a prerequisite.
Reuse the canonical path when it satisfies the requirement. If an apparent
precedent conflicts with the current contract, name the difference and make the
smallest justified correction. Preserve established behavior outside the scope;
incidental cleanup needs its own reason. A no-change outcome is valid when the
requested behavior already exists and is verified.

## Documentation

Use the [documentation contract](testing-and-documentation.md#documentation)
for the existing record shape. Document the information a caller or maintainer
needs to act correctly:
purpose, supported inputs and defaults, results and errors, material side
effects, ownership or lifetime, and recovery limits. Keep the detailed,
non-obvious explanation in one maintained location with exact links to relevant
checks or examples. Update it with the behavior and exercise any changed
example. Prefer a complete readable contract to repeated signatures, jargon,
or line-by-line narration. Evaluate reader success and retrieval cost, not word
count alone.

## Libraries

Inspect the installed or pinned version and supported API before selecting an
approach. Prefer an existing configuration or extension point when it fits. A
small adapter can isolate a real application/library mismatch while preserving
useful error semantics and library-owned behavior such as retries. Do not patch
vendored internals, fork, upgrade, or add a package without an evidenced need.
When a library is unsuitable, record the concrete contract gap, compatibility
and maintenance consequence, and the check for the alternative. Reuse is a
decision, not an absolute rule.

## Composition and layers

Give every changed responsibility a clear owner and a sensible dependency
direction. Separate domain decisions from transport, storage, and presentation
details when the boundary improves current use or testing. Compose existing
collaborators through their supported interfaces; use inheritance only where a
real framework contract or substitutability demands it. Place wiring and
configuration at an appropriate boundary, then verify through the real entry
point and affected consumers. Do not add forwarding layers, factories, or a
dependency-injection container solely for a hypothetical future.

Which important structural constraint can an existing checker enforce? When
useful, calibrate a repository-scoped rule with prohibited and permitted examples,
including an approved boundary and misleading lookalikes. Include a case exposing
a known limited rule or documented blind spot; use a deficient comparator when
already available or cheap. State supported syntax and unresolved dynamic behavior
before enforcement; structural matches do not prove runtime behavior or
authorization. Do not add a checker merely to restate a preference.

## Flyweight and shared resources

Measure the repeated cost and expected workload before sharing anything. Share
only genuinely equivalent, immutable intrinsic data; keep instance-specific or
mutable state outside the shared representation. Define a complete key,
ownership, lifetime, concurrency behavior, and bounded retention. Check
cross-request or tenant isolation and release behavior. Flyweight sharing is
not memoizing results, pooling connections, or caching mutable state; choose
the mechanism that matches the observed problem. Retain ordinary allocation
when sharing has no demonstrated benefit or introduces unsafe coupling, and
verify both behavior and resource use when sharing is selected.

## State

Identify the authoritative owner, scope, lifetime, and allowed transitions.
Where applicable, define atomicity, persistence, concurrency, retry or
idempotency, cancellation, and partial-failure recovery. Derived caches need a
validity and invalidation rule; consumers must not become competing authorities.
Validate before irreversible effects and preserve or repair invariants after a
partial failure. Recheck old/new representation compatibility when data
persists. Use the simplest sufficient mechanism: stateless behavior does not
need a store, event bus, or queue.

## Security

For repository changes, identify the affected asset, trust boundary, and
authorized actor. Enforce access on the trusted side for each relevant
operation; input validation and a hidden UI control do not establish
permission. Validate untrusted input, minimize privilege and data exposure, and
keep credentials or private payloads out of source, messages, and diagnostics.
Use established repository security mechanisms where they fit and exercise
allow, denial, and failure behavior with synthetic data. Do not invent custom
cryptography or a global security framework for a scoped code change. This
section guides that repository decision; it is not a substitute for a security
assessment.

## Notifications

Separate accepted work, committed state, external delivery, and user-visible
presentation. Define recipient, event, emission point, ordering or deduplication,
delivery failure, and recovery. Reuse existing channels. Make UI status
truthful, accessible, and proportionate; coalescing visual noise must not drop a
required business event. Logs are not a durable delivery channel. Select
persistence or retry machinery only when the delivery contract needs it, keep
preferences and authority intact, and use controlled recipients or sinks in
tests rather than real sends.

## Logging and debugging

Follow existing controls and structured conventions. Retain a bounded operation
identity, consequential decision, state transition, and failure cause while
excluding secrets and unnecessary personal data. Distinguish operational logs,
required security audit records, and optional debug detail. Avoid costly
diagnostic construction when debug is off, duplicated stack traces, and
unbounded labels or payloads. A diagnostic failure must not replace the
original error; honor a required fail-closed audit policy explicitly. Investigate
with a small discriminating observation, keep a regression for the cause, and
remove temporary unsafe instrumentation.

## Tool output as evidence

When using a shortened view, which facts and status must remain, and can omitted
required evidence from that exact invocation be recovered? Preserve the command,
exit/signal meaning, required counts/skips, material warnings and failure detail
under existing access, redaction and retention rules. A locator alone is not
recovery: verify it returns the needed evidence. If needed facts are missing and
safe recovery is unavailable, keep the affected claim unverified. Do not rerun an
effectful command to recreate lost output. Pilot filters on relevant failures and
unknown formats before relying on them; smaller output alone does not establish
correctness or net savings.

## Agent and experiment budgets

For affected agent execution or costly trials, which attempts consume budget,
and what happens when usage is missing or the limit is reached? Reuse available
usage records; include observed billed failures and retries, and distinguish
provider-specific or unknown charges after cancellation or delegation. Receipt
replay keeps the same operation identity; a new retry is a new attempt. Reconcile
duplicates and conflicts without inventing zero usage. Define whether the bound
is a post-call threshold or pre-call reservation, including in-flight work and
whether the selected policy stops new calls under uncertainty. Label partial totals
and unmeasured preparation or review costs. This is a scoped decision, not a new
accounting store or scheduler.

## Feature flags

Use a flag for a concrete rollout, experiment, or operational-control need.
Define its owner, default, provider-failure and stale behavior, evaluation
scope and context, supported on/off paths, and removal condition. An ongoing
operational flag may instead have a review policy. Keep authorization
independent, avoid inconsistent evaluations within one operation unless the
contract requires them, and ensure both paths remain compatible with persisted
data and recovery. Test flag changes and provider failures. A flag can stop
future behavior; it cannot undo committed data or delivered effects. Prefer
ordinary configuration or code for permanent choices.
