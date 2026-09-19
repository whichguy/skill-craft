# Coding guidance candidate for experiments

Status: draft treatment material, not installed ShipLoop policy. The companion [shiploop-coding-guidance-experiment-plan-2026-09-18.md - protocol: planned evaluation](/Users/dadleet/src/skill-craft/docs/shiploop-coding-guidance-experiment-plan-2026-09-18.md) defines how to test it. The separately supplied [shiploop-platform-guidance-candidate-2026-09-18.md - platform cards: conditional runtime guidance](/Users/dadleet/src/skill-craft/docs/shiploop-platform-guidance-candidate-2026-09-18.md:5) extends the index below. This file contains no fixture answers or hidden grading criteria. The harness supplies only the Core, Conditional card index and selected card sections to workers; this status paragraph and its study-plan links are observer material and must not be included in worker-visible treatment assets.

## Delivery rule

Preserve the active packet's owner, stage, permitted edits, callback and existing requirements. Supply the core below during planning and implementation/review, with a compact index of the conditional cards. The agent selects and reads applicable cards; record actual retrieval so its cost is measured. Do not automatically concatenate every card into every prompt. Selection misses are experimental outcomes. Do not change required Improve ownership or stage order.

## Core

Inspect the affected execution path, callers, maintained requirements, established tests, current dependency versions and relevant examples. Treat existing code and docs as evidence to reconcile; neither overrides accepted behavior. Preserve unrelated work.

Before edits, retain a compact plan at the existing authorized note location: outcome and preserved invariants; changed responsibilities and contracts; selected reuse or justified augmentation; applicable state, security and operational decisions; ordered changes; independent checks; readiness, completion and revalidation conditions. Cite sources and explain consequential tradeoffs. Use the appropriate conditional cards below. Record only applicable decisions and material unresolved gaps.

Implement the smallest coherent change using current supported capabilities. Prefer readable names, cohesive functions and explicit ownership. Added indirection, sharing, persistence or configuration must serve a present need. Preserve failure causes and required cleanup. New facts may justify a scoped plan revision; new prerequisites or authority must follow the current packet's correction route.

During review, compare the diff with the plan and affected consumers. Run the applicable checks, including meaningful failure paths. A passing assertion must have an independent expected outcome. Carry the accepted plan locator, justified revisions, observations and remaining obligations into existing evidence notes. Do not treat a named pattern, added document, log entry or completion callback as proof of behavior.

## Conditional card index

| Card | Read when |
| --- | --- |
| Existing behavior | Editing an existing implementation or relying on a questionable precedent. |
| Documentation | Changing a public/non-obvious contract, operation, example or recovery procedure. |
| Libraries | Selecting, extending, wrapping or replacing an existing library/helper. |
| Composition and layers | Changing responsibility boundaries, adding collaborators or introducing another entry point. |
| Flyweight and shared resources | Proposing shared representations or seeing measured repeated allocation/initialization cost. |
| State | Mutating, persisting, caching or concurrently accessing state. |
| Security | Changing a trust boundary, identity, permissions, untrusted input or sensitive data. |
| Notifications | Changing user status, domain-event delivery or operator alerts. |
| Logging and debugging | Changing failure handling, diagnostics, telemetry or investigation tools. |
| Feature flags | Introducing, changing, retiring or depending on a runtime toggle. |
| Platform contracts | Targeting UI, Apps Script, Salesforce, Python or Bash; load only the matching separately supplied card. |

## Existing behavior

Trace entry point to observable result and identify adjacent consumers. Run the authorized existing baseline before feature edits; classify existing failures and retain evidence. Reuse the canonical path when it satisfies the requirement. If the apparent precedent contradicts the current contract, identify the difference and make the smallest justified correction. Preserve established behavior outside the requested change; avoid incidental cleanup. A no-change result is valid when the requested behavior already exists and is verified.

## Documentation

Document what a caller or maintainer needs to act correctly: purpose, supported inputs/defaults, results/errors, material side effects, ownership/lifetime and relevant recovery limits. Put rationale near the non-obvious decision; keep detailed explanation in one maintained home with working links. Include a useful example and test/check locator where warranted. Update docs with the behavior and exercise changed examples. Prefer complete, readable contracts over compressed jargon, repeated signatures or line-by-line narration. Measure reader success and total retrieval cost, not word count alone.

## Libraries

Inspect the installed/pinned version and supported API before choosing an approach. Prefer existing configuration or an extension point when it fits. A small adapter can isolate a real application/library mismatch; preserve useful error semantics and avoid duplicating owned behavior such as retries. Do not patch vendored internals, fork, upgrade or add a package without an evidenced need and scope. If the library is unsuitable, explain the concrete contract gap, compatibility and maintenance consequences, and verify the chosen alternative. Reuse is a decision, not an absolute rule.

## Composition and layers

Give each changed responsibility a clear owner and dependency direction. Keep domain decisions separate from transport, storage and presentation details when that boundary helps current use or testing. Compose existing collaborators through supported interfaces; use inheritance where the actual framework contract or substitutability warrants it. Put wiring and configuration at an appropriate boundary. Verify through the real entry point and affected consumers. Do not create layers, forwarding interfaces, factories or a dependency-injection container solely for hypothetical future uses.

## Flyweight and shared resources

First measure the repeated cost and workload. Share genuinely equivalent immutable intrinsic data; keep instance-specific or mutable state outside the shared representation. Define complete keys, ownership, lifetime, concurrency behavior and bounded retention. Check cross-request/tenant isolation and release after use. Distinguish flyweight representation sharing from memoizing results, pooling connections or caching mutable state; choose the mechanism that matches the actual problem. Retain ordinary allocation when sharing has no demonstrated benefit or adds unsafe coupling. Verify both behavior and resource use.

## State

Identify the authoritative owner, scope, lifetime and allowed transitions. Define atomicity, persistence, concurrency, retry/idempotency and cancellation/recovery behavior where applicable. Derived caches must have a validity/invalidation rule; consumers must not silently become competing authorities. Validate before irreversible effects and preserve or repair invariants after partial failure. Recheck old/new representation compatibility for persisted changes. Use the simplest sufficient state mechanism; stateless behavior does not need a state store or event bus.

## Security

Identify the changed assets, trust boundary and authorized actor. Enforce access on the trusted side for every relevant operation; input validation and feature visibility do not establish permission. Validate untrusted inputs, minimize privileges and data exposure, and keep credentials/private payloads out of code, messages and diagnostics. Inspect relevant dependency/security contracts and test denial and failure paths with synthetic data. Use existing security mechanisms where suitable. Do not invent custom cryptography or add a global security framework to a change that needs neither.

## Notifications

Distinguish accepted work, committed state, external delivery and user-visible presentation. Define who should receive which event, when it is emitted, ordering/deduplication, delivery failure and recovery. Reuse existing channels. UI status should be truthful, accessible and proportionate; coalescing visual noise must not discard required business events. Logs are not a durable delivery channel. Select persistence/retry machinery only when the contract needs it. Preserve user preferences and appropriate authority; tests use controlled recipients/sinks rather than real sends.

## Logging and debugging

Use existing controls and structured conventions. Retain bounded operation identity, important decisions, state transitions and failure causes while excluding secrets and unnecessary personal data. Distinguish operational logs, security audit requirements and optional debug detail. Keep expensive diagnostic construction disabled when debug is off; avoid duplicated stack traces and unbounded labels/payloads. A diagnostic failure must not replace the original error; explicitly honor any required fail-closed audit policy. Investigate with a small discriminating observation, retain a regression for the cause, and remove temporary unsafe instrumentation.

## Feature flags

Use a flag for a concrete rollout, experiment or operational-control need. Define its owner, default/error/stale behavior, evaluation scope/context, supported on/off paths and removal condition; operational flags may have an ongoing review policy instead of an expiry. Avoid inconsistent decisions within an operation unless the contract requires live reevaluation. Keep authorization independent and both paths compatible with persisted data and recovery. Test flag changes and provider failures. A flag can stop future behavior but cannot undo committed data or delivered effects. Avoid flags for permanent choices better expressed as ordinary configuration or code.
