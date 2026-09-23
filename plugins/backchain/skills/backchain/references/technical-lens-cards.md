# Technical dependency question cards

Read only applicable or uncertain cards selected from [the lens index](technical-lenses.md). Adapt questions to the actual technology and version; examples do not introduce requirements.

## T01 — Requirements, scope, authority, and acceptance

- Trigger: every requested change, including apparently trivial edits.
- Ask: Which original and maintained requirements apply? Which negative and conditional obligations must remain? Which document is authoritative, proposed, or superseded? What observable result establishes each obligation? Is a disagreement unresolved rather than silently chosen?
- Hidden relationship: a feature plan needs the applicable existing contract; a green test for a newly invented behavior does not establish compliance with that contract.
- Inspect: user request, PRD/spec clauses, existing acceptance cases, architecture decisions, product policies, explicit supersession decisions.

## T02 — Architecture, responsibility, and change boundaries

- Trigger: behavior crosses modules, services, layers, or ownership boundaries, or introduces a reusable capability.
- Ask: Who owns each behavior and state? What existing component should supply it? Which abstractions or extension points are already intended? Does a change require another component's contract to change? What new coupling or failure domain would it introduce?
- Hidden relationship: two features may share an existing validation contract without one feature depending on the other. A genuinely shared supplier should be consumed by both, without serializing their independent implementation.
- Inspect: architecture diagrams/decisions, imports and call sites, ownership conventions, analogous implementations, dependency direction rules.

## T03 — Repository, workspace, generated files, and integration

- Trigger: code, documentation, configuration, generated bindings, or multiple workers change a repository.
- Ask: Which checkout, base revision, branch, and generated source are authoritative? Which files are shared or tool-owned? What registration/export/build wiring makes the change reachable? What integration checks apply after merging independently correct branches? Which existing user changes must be preserved?
- Hidden relationship: implementing a module does not make it discoverable; an export/registration and integrated revision may be required. Shared file ownership is an execution constraint, not automatically a product prerequisite.
- Inspect: README/AGENTS, Git state, package/build entry points, generation scripts, worktree policy, CI integration route.

## T04 — Toolchain, dependencies, and reproducible build setup

- Trigger: compilation, packaging, code generation, native extensions, SDK use, or a new runtime/library.
- Ask: Which language/runtime/compiler/SDK versions are actually supported? Are dependencies and generators pinned and available? Are native libraries, platform headers, and build assets present? Do local and CI builds consume equivalent inputs? What existing tooling can be reused?
- Hidden relationship: source code alone cannot supply an executable without its toolchain and generated assets; a developer's global installation is not evidence that CI can reproduce it.
- Inspect: lockfiles, runtime version files, build scripts, generator definitions, container/base images, CI configuration and logs.

## T05 — Configuration, secrets, feature flags, and policy

- Trigger: environment settings, endpoints, credentials, entitlements, experiments, flags, or kill switches affect behavior.
- Ask: Where is each value defined and validated? Which artifact/config revisions must agree? When do changes propagate or reload? What are missing/default/fallback behaviors? How do identity, tenant, experiment assignment, and policy changes affect an in-flight operation? Can a flag be safely disabled after new-format data is written?
- Hidden relationship: a flag value or secret exists somewhere, but the selected runtime may not receive or be authorized to read it. A code rollback need not restore configuration.
- Inspect: configuration schemas, bindings and role policies, flag evaluations, startup checks, actual non-secret runtime configuration evidence.

## T06 — Setup, bootstrap, infrastructure, and environment lifecycle

- Trigger: a required environment, account, resource, target, test service, or host capability may not exist or be ready.
- Ask: What creates and owns it? Which identity and permissions are needed? What must exist before bootstrap itself can run? Is setup repeatable and isolated? What differs between local, test, and consumer environments? What cleanup and readiness checks prove the intended instance is usable?
- Hidden relationship: an installed CLI or SDK does not supply an accessible project, registered application, database, permission grant, or populated fixture.
- Inspect: environment inventory, bootstrap/IaC scripts, supported safe probes, resource roles, setup logs, target identity and cleanup contract.

## T07 — State ownership, transitions, and lifetime

- Trigger: a status, entitlement, workflow phase, local draft, or persisted object changes.
- Ask: What is authoritative versus derived or transient? Which before/after states are legal? What guards each transition? What must persist across page close, process crash, service restart, or device change? What invalidates a previously true state? Which actor owns local/offline intent versus confirmed state?
- Hidden relationship: “submitted,” “accepted,” “committed,” and “displayed” are different states. Completing one does not supply all the others.
- Inspect: transition handlers, state diagrams, persistence boundaries, client storage/offline queues, restart and forbidden-transition cases.

## T08 — Entity, tenant, instance, and revision identity

- Trigger: lookup, association, authorization, correlation, state reuse, or evidence refers to a particular object.
- Ask: Which exact record or instance is required? How are tenant and resource identities bound? Can identifiers be reused or stale? Which revision/generation must a response match? What prevents a result from a previous account, document, or run updating the current one?
- Hidden relationship: a user table or lookup function is not a matching user record. A success receipt for one tenant or revision cannot supply another consumer's need.
- Inspect: key and scope definitions, lookup predicates, correlation IDs, version checks, representative records, identity-bound test cases.

## T09 — Schema, serialization, representation, and domain constraints

- Trigger: stored or exchanged data, file formats, validation, computed values, or data-bearing APIs change.
- Ask: Which types, required/null/missing distinctions, encodings, units, ranges, uniqueness, and relationships apply? What is rejected versus coerced? Do producer and consumer agree on serialization and validation? Are arithmetic precision, ordering, overflow, and normalization defined where relevant?
- Hidden relationship: a syntactically valid payload can violate a domain invariant; generated type declarations do not establish runtime validation at an external boundary.
- Inspect: schema definitions, validators, serialization code, constraints, domain examples and independent edge-case oracles.

## T10 — Persistence, queries, indexes, and durability

- Trigger: data survives an operation or queries must find, sort, aggregate, or update it.
- Ask: Where is the source of truth? Which schema, actual rows, indexes, and access paths are needed? What makes an acknowledgment durable? What read/write volume and storage growth apply? Can a partial file write, failed flush, or interrupted commit leave a misleading success state?
- Hidden relationship: an index migration file does not supply an applied index; a schema does not supply populated data; a successful application call does not always establish the intended persistence boundary.
- Inspect: database/file access code, query plans, applied schema, constraints, actual durability contract, data-shape and crash-recovery checks.

## T11 — Data migration, backfill, import/export, and reconciliation

- Trigger: existing data must change shape, location, ownership, meaning, or indexing.
- Ask: Which legacy values exist? What order makes old and new readers/writers safe? Is backfill resumable and idempotent? How is completeness and semantic preservation verified? What concurrent writes occur during it? What data changes make rollback impossible?
- Hidden relationship: adding a column does not supply valid historical values. A completed batch job may still miss late-arriving records or overwrite concurrent updates.
- Inspect: migration/backfill logic, applied versions, representative legacy samples, watermarks, reconciliation totals, compatibility and rollback checks.

## T12 — Concurrency, shared resources, locks, and liveness

- Trigger: threads, processes, users, workers, tests, or agents may overlap on mutable state or scarce resources.
- Ask: What is shared? Which ownership/lock/lease/version rule prevents lost updates and corruption? Are lock order, lease expiry, starvation, deadlock, and cancellation defined? Are resources partitioned or isolated? What releases ownership after failure?
- Hidden relationship: parallel branches may contend for a table, file, port, directory, GPU, deployment target, or quota even when their output dependencies are independent.
- Inspect: synchronization primitives, resource names, isolation boundaries, lock acquisition/release paths, race tests and execution ownership rules.

## T13 — Transactions, atomicity, isolation, and commit boundaries

- Trigger: multiple reads/writes or side effects must preserve one invariant.
- Ask: What is atomic? Which anomalies does the chosen isolation level permit? Is a check-and-write protected by a constraint or concurrency control? What work repeats after conflict? Can a remote effect happen even if the local transaction rolls back?
- Hidden relationship: checking availability and then decrementing it can violate capacity under concurrent requests unless the invariant is enforced at the actual write boundary.
- Inspect: transaction scope, database constraints/isolation, conflict handling, commit/error paths, concurrency fixtures. PostgreSQL's isolation documentation supplies concrete examples of anomalies and transaction retries; the appropriate mechanism depends on the actual database. [PostgreSQL - Transaction Isolation](https://www.postgresql.org/docs/current/transaction-iso.html)

## T14 — Replication, distributed consistency, and reconciliation

- Trigger: multiple replicas, regions, services, devices, or projections expose the same logical fact.
- Ask: Which authority decides truth? What consistency/freshness is promised? Can reads lag writes or leaders change? How are partitions, split ownership, divergent writes, and reconciliation handled? Which operations require a stronger boundary than the default read path?
- Hidden relationship: a write acknowledged by one component may not yet supply a fresh read or decision elsewhere. A replica's availability does not establish its freshness.
- Inspect: consistency contracts, replica/read routing, version vectors or revisions where used, reconciliation logic, lag/failover observations and tests.

## T15 — Events, queues, subscriptions, and processing acknowledgment

- Trigger: messages, jobs, webhooks, polling, streaming, push updates, or subscriptions carry work or state.
- Ask: What delivery and ordering guarantees exist, and at what scope? What distinguishes enqueued, received, processed, and durable effect? How are offsets/acks coordinated with output? What handles duplicates, poison messages, backlog, missed events, and snapshot-to-live handoff?
- Hidden relationship: acknowledging before output persistence can lose work; persisting before acknowledgment can allow duplicate effects. A connected subscription need not contain a current snapshot.
- Inspect: broker/provider guarantees, consumer checkpoint code, dead-letter/replay route, cursor identity, backpressure policy. Kafka documents why coordinating consumed position with an external output requires additional cooperation. [Apache Kafka - Delivery Semantics](https://kafka.apache.org/40/design/design/)

## T16 — Retry, idempotency, cancellation races, and compensation

- Trigger: operations can time out, be retried, be delivered twice, or span systems with partial success.
- Ask: Which layer owns retry? What logical intent does an idempotency key identify, for how long, and within which tenant? What if the same key carries different input? How is a lost response distinguished from a failed effect? What is retried, reconciled, or compensated, and what cannot be undone?
- Hidden relationship: retrying a non-idempotent mutation after timeout can duplicate a successful first attempt; a client-generated key needs durable server-side semantics.
- Inspect: retry policy, dedupe state, request/result binding, retention, ambiguous-outcome reconciliation and compensation tests. [AWS Builders' Library - Making Retries Safe with Idempotent APIs](https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/)

## T17 — Time, deadlines, expiry, scheduling, and transition windows

- Trigger: TTLs, leases, schedules, grace periods, delayed work, cutovers, or request deadlines matter.
- Ask: Which event starts the clock? Which clock/time zone and precision apply? Must a condition remain continuously true? What resets the interval? What happens on clock skew, daylight-saving changes, delayed execution, expiry, or restart?
- Hidden relationship: a retirement window starts from its qualifying state, not necessarily the deployment timestamp; rollback can invalidate elapsed eligibility.
- Inspect: timestamp sources, timer persistence, scheduling expressions, monotonic versus wall-clock use, boundary tests, restart/reset rules. Backchain already has a useful transition-window rule to retain.

## T18 — Caching, materialized views, search indexes, and freshness

- Trigger: a consumer uses cached, derived, replicated, precomputed, or indexed data.
- Ask: What key, tenant, authorization context, version, and TTL identify an entry? Who invalidates or rebuilds it? What freshness is required after writes or revocation? Can failures serve stale data? What handles rebuild gaps, stampedes, and derived-format changes?
- Hidden relationship: updating authoritative state does not automatically supply a fresh UI, permission check, search result, or report.
- Inspect: cache keys, validators/headers, invalidation paths, projection checkpoints, freshness indicators and read-after-write checks. HTTP cache reuse and validation have distinct semantics. [RFC 9111 - HTTP Caching](https://datatracker.ietf.org/doc/html/rfc9111)

## T19 — Durable workflows, restart, replay, and cleanup ownership

- Trigger: work outlives one call, page, process, or worker and may pause, cancel, or resume.
- Ask: What progress and identity survive interruption? Which actions are replay-safe? Who owns outstanding work after disconnect? How are late results and cancellation/completion races resolved? Which resources must be cleaned up, and who can reclaim abandoned ownership?
- Hidden relationship: “started” cannot supply “completed”; replay can repeat external effects unless durable history or idempotency protects them. A screen-independent promise needs a screen-independent owner.
- Inspect: checkpoints/history, task identity, completion import, cancellation and cleanup paths, crash-between-boundaries tests. Temporal provides one concrete durable-history/replay model, not a required implementation. [Temporal - Workflow Execution](https://docs.temporal.io/workflow-execution)

## T20 — API, RPC, command, and error contracts

- Trigger: one component invokes another through a public boundary.
- Ask: What operation is actually exposed? Which path/method/arguments, serialization, response envelope, errors, pagination, and limits apply? Which status means accepted versus completed? What authentication, cancellation, retry, and version behavior is part of the contract?
- Hidden relationship: an internal exported function or generated client does not prove the public operation is registered and callable with that envelope.
- Inspect: actual boundary registration, versioned API/SDK docs, command help, generated stubs, contract tests and negative cases. OpenAPI describes HTTP operations; HTTP semantics constrain interpretation of methods and responses. [OpenAPI 3.0.4 - Specification](https://spec.openapis.org/oas/v3.0.4.html) [RFC 9110 - HTTP Semantics](https://datatracker.ietf.org/doc/html/rfc9110)

## T21 — Operating-system, browser, device, and platform calls

- Trigger: filesystem/process APIs, browser capabilities, hardware access, hosted APIs, native libraries, or sandboxed execution.
- Ask: Is the operation supported in the actual version and context? What permissions, user activation, secure-context, sandbox, thread-affinity, handles, or runtime quotas apply? Can a call partially succeed or return short/partial data? What happens when the process is suspended, permission revoked, or a handle/path changes?
- Hidden relationship: an API symbol existing does not supply platform permission, target capability, safe path ownership, or a usable device. A blocking call may be incompatible with the event-loop or execution deadline.
- Inspect: platform specification and system-call contract, wrappers, actual runtime version, safe capability probe, error/cleanup tests. Browser Permissions Policy is one example of a host policy constraining an otherwise available API. [W3C - Permissions Policy](https://www.w3.org/TR/permissions-policy/)

## T22 — Networking, discovery, transport, and connection lifecycle

- Trigger: components communicate across a network or through persistent connections.
- Ask: What resolves and routes the destination? Which DNS, TLS/certificate, proxy, firewall, CORS, origin, or transport conditions apply? When is a connection ready and authenticated? How are reconnect, heartbeat, buffering, backpressure, stale sessions, and graceful close handled?
- Hidden relationship: a listening process does not supply a reachable or trusted endpoint; a reconnected socket does not automatically supply restored subscription state or current authorization.
- Inspect: network topology, endpoint and certificate configuration, transport/client lifecycle code, handshake and reconnect tests, safe target reachability evidence.

## T23 — External providers, integrations, and callbacks

- Trigger: a vendor, managed service, remote workspace, callback/webhook, payment/email service, or data feed participates.
- Ask: What exact service/account/region/version is selected? What setup and callback registration exist? How is a callback authenticated and correlated? What do provider acceptance and delivery receipts prove? What happens on delay, duplicate delivery, outage, quota exhaustion, or discontinued behavior?
- Hidden relationship: local success or a provider's delivery acknowledgment does not prove the requested downstream domain state or human observation.
- Inspect: provider's versioned contract, endpoint registration, non-secret target identity, sandbox limitations, signed callback fixtures, reconciliation and end-to-end checks.

## T24 — Authentication, authorization, sessions, and delegation

- Trigger: an operation depends on a user, workload, role, scope, tenant, entitlement, or delegated identity.
- Ask: Who authenticates whom? Where is authorization enforced for this resource and action? Which issuer/audience/subject/session/tenant binding is validated? What happens on expiry, revocation, refresh, account switch, or delegated callback? Are negative and cross-tenant cases checked at the authority?
- Hidden relationship: a signed-in UI or hidden button does not supply server-side authorization. An old-session response must not be accepted into a new-session state.
- Inspect: actual identity and policy contracts, service enforcement, credential lifecycle, permit/deny tests and role-specific integration paths. [OpenID Connect Core - Token Validation](https://openid.net/specs/openid-connect-core-1_0.html)

## T25 — User journeys, async feedback, and client-state reconciliation

- Trigger: a human initiates, observes, cancels, retries, or resumes an operation.
- Ask: What are idle/loading/empty/pending/success/error/conflict/offline states? What survives navigation, refresh, or another device? Which state is optimistic versus confirmed? Can a stale response overwrite a newer action? What does the user do after ambiguous success, timeout, or permission denial?
- Hidden relationship: a truthful completion cue depends on a matching authoritative outcome; animation completion and request submission cannot establish that outcome.
- Inspect: journey and state models, local storage/offline queues, response correlation, browser behavior under delay/failure/reconnect, visible recovery paths.

## T26 — Components, visual design, responsiveness, and rendering

- Trigger: UI layout, controls, design tokens, component variants, assets, or rendering behavior change.
- Ask: Which existing component/design system supplies the needed behavior? What props/events/states and responsive breakpoints are required? Are hydration, rendering timing, fonts/assets, reduced motion, and layout shifts relevant? Which behavior and visual decisions are preserved from prior design? Can shared components change without breaking other consumers?
- Hidden relationship: a screenshot supplies appearance evidence but not a working interaction contract. A component may need an existing primitive, asset, or API decision, while independent page sections can proceed in parallel.
- Inspect: analogous component code, design decisions/tokens, actual supported runtime, visual and behavioral checks at relevant sizes/states.

## T27 — Accessibility and input modalities

- Trigger: any affected human-facing interaction, validation, navigation, or status message.
- Ask: What semantic name/role/state/value is exposed? Are keyboard, pointer, touch, and assistive-technology paths usable? What happens to focus during navigation, modal open/close, async replacement, and errors? Are changes announced and persistent where needed? Do contrast, zoom/reflow, target size, and motion meet the applicable requirements?
- Hidden relationship: visual state, keyboard behavior, and programmatic state must remain consistent. Adding ARIA alone does not implement keyboard interaction.
- Inspect: semantic markup, focus rules, supported assistive paths, target browser tests, applicable accessibility criteria. [W3C APG - Keyboard Interface](https://www.w3.org/WAI/ARIA/apg/practices/keyboard-interface/) [W3C - WCAG 2.2](https://www.w3.org/TR/WCAG22/)

## T28 — Internationalization, content, units, and numerical semantics

- Trigger: text, dates, time zones, numbers, currency, measurements, sorting, export/import, or multiple locales are involved.
- Ask: What is stored canonically versus displayed locally? Which encoding, Unicode normalization, pluralization, collation, directionality, units, precision, and rounding apply? Can a localized label or delimiter be mistaken for a stable key? Are assets/content/translations actually available for supported states?
- Hidden relationship: formatting a date does not establish its intended time zone; parsing a localized number can change value. A rendered label is not a durable protocol identifier.
- Inspect: domain examples, locale resources, parsing/formatting code, numeric types, asset licenses where relevant, round-trip and boundary fixtures.

## T29 — Trust boundaries, abuse resistance, and application security

- Trigger: untrusted input, code/content execution, public or privileged operations, or a changed trust boundary.
- Ask: Which input is trusted, validated, encoded, or executable? Can paths, URLs, serialized objects, templates, or commands escape their intended scope? Which isolation, rate/abuse controls, secret protection, and administrative boundaries apply? Do fallback and error paths weaken the selected security contract?
- Hidden relationship: a validated internal object does not establish validation of public input; a defensive control must be applied at the boundary it is intended to protect.
- Inspect: threat/data-flow model, input/output handling, actual platform security contracts, negative tests and existing review requirements. Secure-development practices should be integrated with the lifecycle rather than left to a final scan. [NIST SP 800-218 - SSDF](https://csrc.nist.gov/pubs/sp/800/218/final)

## T30 — Privacy, data minimization, retention, deletion, and residency

- Trigger: personal, sensitive, regulated, or user-controlled data is collected, copied, logged, shared, or retained.
- Ask: What data is necessary and under which established policy? Where do copies, logs, caches, backups, analytics, and provider transfers exist? What retention, export, deletion, access, and residency obligations apply? Can a restore or replay resurrect deleted data? Do diagnostics expose more than the product contract permits?
- Hidden relationship: deleting the primary row may not supply deletion across derived stores or later restore. Do not invent regulatory obligations; use applicable accepted policy and qualified decisions.
- Inspect: data inventory/flows, product and privacy requirements, retention configuration, provider contracts, deletion propagation and restoration tests.

## T31 — Failure isolation, graceful degradation, and resilience

- Trigger: another component can fail or an availability/recovery promise is made.
- Ask: What fails independently and what shares a failure domain? What happens if a dependency is absent at startup or fails during work? Which timeout, circuit, bulkhead, load-shedding, failover, and shutdown behavior is appropriate? Does recovery amplify load or repeat effects? What user-visible behavior is allowed in degraded mode?
- Hidden relationship: adding replicas does not remove a shared dependency or data-plane failure. Retrying without bounds can worsen the failure the retry was meant to handle.
- Inspect: failure-path code, actual dependency topology, response/deadline policies, fault-injection evidence, accepted availability and recovery criteria.

## T32 — Performance, capacity, limits, and operating cost

- Trigger: workload size, latency, concurrency, data volume, resource limits, or spend can affect the outcome.
- Ask: Which accepted workload and response bounds apply? Where are CPU, memory, connections, storage, bandwidth, API rate, or token limits? How does fan-out multiply demand? What happens near saturation and under failure? Is setup/steady-state/retry cost affordable within the stated budget? What capacity or quota has lead time?
- Hidden relationship: more workers may exhaust database connections or provider limits; a successful tiny fixture does not establish behavior at the required scale.
- Inspect: measured baselines, actual quotas, profiling/load tests, request fan-out, resource policies and cost model. Unknown targets remain decisions to resolve, not invented SLAs.

## T33 — Observability, diagnostics, audit, and operational decisions

- Trigger: a claim, failure, rollout, support decision, or operational response requires evidence.
- Ask: Which observable symptom matters? What logs, metrics, traces, audit events, and correlation identify the relevant request/build/config/tenant? Are errors actionable without leaking data? Do cardinality, sampling, retention, and telemetry failure hide the event? Who acts on an alert and on what threshold?
- Hidden relationship: a promotion gate cannot consume an undefined or uncollected health signal. A metric that only measures process survival may miss a broken user journey.
- Inspect: instrumentation paths, dashboards, alert routes, release annotations, trace continuity and diagnostic tests. [Google SRE - Monitoring Distributed Systems](https://sre.google/sre-book/monitoring-distributed-systems/)

## T34 — Verification strategy, independent oracles, and coverage

- Trigger: every required behavior or quality claim that can be checked.
- Ask: Which independent observation discriminates correct from plausible behavior? What unit, contract, integration, browser, remote-runtime, load, or recovery boundary is needed? Does each requirement have an executable or otherwise inspectable check? What failures, omissions, skipped cases, and false-positive controls must remain visible?
- Hidden relationship: tests authored from the same mistaken plan can confirm its omissions. A process exit, screenshot, mock response, or aggregate pass is insufficient for a claim at a different boundary.
- Inspect: source requirements, test selectors/oracles, negative controls, actual execution records and limits of each test surface.

## T35 — Test setup, fixtures, isolation, teardown, and repeatability

- Trigger: verification consumes mutable state, shared infrastructure, remote access, or expensive setup.
- Ask: What exact records, target versions, identities, clocks, ports, and services are needed? What is reusable read-only infrastructure versus per-case data? What proves noninterference under parallel execution? Who cleans up after assertion failure, timeout, or interruption? Can a focused case run independently and repeatedly?
- Hidden relationship: a seeded user belongs upstream of a login test, not necessarily upstream of production login implementation. Shared setup without isolation can create order-dependent false passes.
- Inspect: fixture lifecycle, namespace/reset policy, remote invocation/retrieval route, cleanup evidence, focused/smoke/full-suite wiring.

## T36 — Artifact identity, packaging, provenance, and distribution

- Trigger: a build, package, plugin, image, document, client bundle, or release is consumed elsewhere.
- Ask: Which exact inputs produced the artifact? What identifies its content and configuration? Does the package include all referenced resources? Do signing, installation, discovery, execution, and update paths work? Are validation and distribution receipts for the same artifact?
- Hidden relationship: a skill card can be discoverable while required files are absent; a tested source checkout can differ from the distributed package. A mutable tag is weaker than the actual content identity needed by a gate.
- Inspect: package manifest, artifact contents, build provenance, digests, installation/update tests, consumer-visible version. [SLSA - Provenance](https://slsa.dev/spec/v1.1/provenance)

## T37 — Deployment, registration, routing, and readiness

- Trigger: code or configuration must become active in a runtime or reach a consumer.
- Ask: What installs, registers, starts, and routes the artifact? What schema/config/secret/network conditions must hold first? Which probe establishes startup, readiness, liveness, and actual feature behavior? What propagation delay or activation step exists? Which target/revision does the receipt identify?
- Hidden relationship: uploaded code is not necessarily active; a healthy process can still lack its required data or public route. Readiness and restart decisions can require different signals.
- Inspect: deployment/registration configuration, runtime identity, activation receipts, routing and consumer smoke checks. Kubernetes distinguishes startup, readiness, and liveness probes; use the corresponding concepts of the actual platform. [Kubernetes - Probes](https://kubernetes.io/docs/concepts/workloads/pods/probes/)

## T38 — Rollout, promotion, cutover, rollback, and retirement

- Trigger: new and old versions coexist, traffic shifts, a feature is enabled, or a component is removed.
- Ask: What same-candidate observations permit promotion? Is the evaluated population representative? What order makes schema/config/code/client changes safe? Which rollback restores code, configuration, data, and access? What is irreversible? What evidence permits disabling old writers, draining work, or deleting compatibility code?
- Hidden relationship: passing staging deployment alone does not supply smoke evidence; rolling code back may fail against data written by the new version. A zero-traffic canary can appear healthy.
- Inspect: rollout policy, actual target/build/config receipts, observation window, compatibility matrix, drain/retirement criteria and rollback rehearsal. [Google SRE - Canarying Releases](https://sre.google/workbook/canarying-releases/)

## T39 — Backup, restoration, disaster recovery, and consistency of recovery

- Trigger: durable user state, destructive changes, or recovery objectives exist.
- Ask: What is backed up, how consistently, and at what recovery point? Are keys, metadata, schema, and dependent stores restorable together? Can the recovery identity access them during the failure? Has restore been checked at the required scale and time? How are replay, deletion tombstones, and duplicate effects handled afterward?
- Hidden relationship: a backup file does not supply a usable recovery path; restoration can produce inconsistent stores or resurrect prohibited data without reconciliation.
- Inspect: backup and restore code/configuration, restore rehearsals, observed recovery bounds, key and role availability, integrity and post-restore checks.

## T40 — Operational ownership, documentation, human decisions, and external prerequisites

- Trigger: another person/team/provider must decide, approve, operate, support, or maintain something needed for success.
- Ask: Who owns the resource, release, incident response, data, and rollback? Which authority is actually required? What instructions and diagnostics enable another operator to act? Which support windows, vendor lead times, contracts, or end-of-life constraints matter? What happens when the owner or authority is unavailable?
- Hidden relationship: writing an approval request or runbook does not establish approval or an authorized operator. A dependency with no reachable owner may leave required recovery or delivery blocked.
- Inspect: applicable ownership and authority records, runbooks, support agreements, documentation checks and observed external decisions.

## T41 — Compatibility, version skew, negotiation, and downgrade behavior

- Trigger: independently deployed clients/servers, libraries, protocols, schemas, persisted formats, or rolling changes coexist.
- Ask: Which producer/consumer version combinations are supported? What negotiates capabilities? How do unknown fields, enum values, event kinds, and older readers/writers behave? Can a new-format failure wrongly fall back to a legacy path? When may an old format or dependency be retired?
- Hidden relationship: upgrading one endpoint does not upgrade its clients. A correct new parser can still violate security or data invariants through a permissive legacy fallback.
- Inspect: explicit version matrix, compatibility fixtures, protocol/SDK release notes, negotiation/fallback implementation, rollout and deprecation records.

## T42 — Dependency supply chain, trust, updates, and withdrawal

- Trigger: third-party libraries, packages, images, plugins, generated code, build actions, registries, or binary downloads enter the change.
- Ask: Which exact versions/origins are selected and trusted? What integrity, license, vulnerability, or provenance policy actually applies? Can a build substitute an unreviewed dependency? What transitively affects the result? Can the dependency be updated, revoked, rebuilt, replaced, or unavailable without silently changing behavior?
- Hidden relationship: scanning a lockfile does not establish the integrity of an unpinned build action or base image. A package being installable does not establish a compatible or maintainable integration.
- Inspect: dependency and transitive manifests, hashes/signatures, repository policies, actual build inputs, release advisories and replacement/update route. [NIST SP 800-218 - Secure Development and Software Protection](https://csrc.nist.gov/pubs/sp/800/218/final)
