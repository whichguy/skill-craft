# Technical dependency lenses

Use this index when drafting or auditing a dependency plan. Screen all categories once against the original requested outcomes, selected source clauses, and affected flows, including branches absent from the candidate. Classify applicable, uncertain, or not applicable with an inspected scope basis; group shared exclusions. An unknown is not not-applicable. Load only applicable or uncertain sections of [technical-lens-cards.md](technical-lens-cards.md). A newly encountered consequential boundary receives another screen. Do not paste the entire library into every call or turn each category into work.

For each relevant finding trace: source/observation → exact consumer claim → required condition → supplier or evidence → lifecycle/identity scope. Check actual technology/version/operation rather than category labels. Distinguish required-by-source, observed, planned, and unresolved. A spec states obligations; it does not prove an environment satisfies them.

| ID | Consideration |
| --- | --- |
| T01 | Requirements, scope, authority, and acceptance |
| T02 | Architecture, responsibility, and change boundaries |
| T03 | Repository, workspace, generated files, and integration |
| T04 | Toolchain, dependencies, and reproducible build setup |
| T05 | Configuration, secrets, feature flags, and policy |
| T06 | Setup, bootstrap, infrastructure, and environment lifecycle |
| T07 | State ownership, transitions, and lifetime |
| T08 | Entity, tenant, instance, and revision identity |
| T09 | Schema, serialization, representation, and domain constraints |
| T10 | Persistence, queries, indexes, and durability |
| T11 | Data migration, backfill, import/export, and reconciliation |
| T12 | Concurrency, shared resources, locks, and liveness |
| T13 | Transactions, atomicity, isolation, and commit boundaries |
| T14 | Replication, distributed consistency, and reconciliation |
| T15 | Events, queues, subscriptions, and processing acknowledgment |
| T16 | Retry, idempotency, cancellation races, and compensation |
| T17 | Time, deadlines, expiry, scheduling, and transition windows |
| T18 | Caching, materialized views, search indexes, and freshness |
| T19 | Durable workflows, restart, replay, and cleanup ownership |
| T20 | API, RPC, command, and error contracts |
| T21 | Operating-system, browser, device, and platform calls |
| T22 | Networking, discovery, transport, and connection lifecycle |
| T23 | External providers, integrations, and callbacks |
| T24 | Authentication, authorization, sessions, and delegation |
| T25 | User journeys, async feedback, and client-state reconciliation |
| T26 | Components, visual design, responsiveness, and rendering |
| T27 | Accessibility and input modalities |
| T28 | Internationalization, content, units, and numerical semantics |
| T29 | Trust boundaries, abuse resistance, and application security |
| T30 | Privacy, data minimization, retention, deletion, and residency |
| T31 | Failure isolation, graceful degradation, and resilience |
| T32 | Performance, capacity, limits, and operating cost |
| T33 | Observability, diagnostics, audit, and operational decisions |
| T34 | Verification strategy, independent oracles, and coverage |
| T35 | Test setup, fixtures, isolation, teardown, and repeatability |
| T36 | Artifact identity, packaging, provenance, and distribution |
| T37 | Deployment, registration, routing, and readiness |
| T38 | Rollout, promotion, cutover, rollback, and retirement |
| T39 | Backup, restoration, disaster recovery, and consistency of recovery |
| T40 | Operational ownership, documentation, human decisions, and external prerequisites |
| T41 | Compatibility, version skew, negotiation, and downgrade behavior |
| T42 | Dependency supply chain, trust, updates, and withdrawal |

## Relationships and revisits

A finding may be a prerequisite edge, interface decision, ongoing invariant, resource/exclusivity constraint, verification prerequisite, time/invalidation condition, research question, or external blocker. Explain the classification. Runtime feedback can be cyclic while the implementation DAG remains acyclic; a shared file or resource conflict alone does not establish product dependency. Justify direct ordering through the consumer's actual required condition.

Test consequential interactions across the selected lenses: state × identity × late UI results; schema × migration × mixed-version writers; concurrency × transaction × retry; cache × authorization × freshness; deployment × artifact identity × observation; events × restart × replay; backup × restore × retention; tests × shared mutable fixtures. Use the actual task to select absent, stale, duplicate, reordered, concurrent, interrupted, partial, expired, unauthorized, incompatible, or exhausted conditions. Trace through the consumer-visible/durable effect.

Revisit new/widened suppliers and affected upstream/downstream consumers, including shared-contract consumers absent from existing edges. Reuse applicable evidence; changed source, version, configuration, target, workload, or contradictory observations reopen the relevant conditions. Compare final coverage independently with original sources. More nodes or repeated passes are not completeness evidence.

## Unsubstantiated prerequisites

First determine whether the condition is actually necessary. An unjustified edge is a graph-quality finding, not a reason to run an experiment. For a genuine prerequisite:

- Inspect applicable existing evidence when it can answer the question.
- Plan ordinary creation/setup work for a known implementable condition.
- Plan a bounded experiment when consequential feasibility or behavior remains empirically uncertain.
- Keep unavailable authority/access or an untestable material condition unresolved with owner and resumption condition.

An experiment contract names the hypothesis, affected consumers, inspected evidence, actual technology/configuration/target, representative setup and prerequisites, predeclared acceptance criterion and observations, appropriate controls/repetitions, limits, allowed effects, cleanup, result locator/fidelity, and consequences of each outcome. An experiment produces observations and a decision report; it cannot promise a positive result. A valid supporting result substantiates only its tested scope; a valid negative result requires redesign/rejection of that route. Inconclusive or invalid evidence leaves the condition open. Record execution/cleanup problems separately. Do not repeat until favorable or weaken acceptance after seeing results.

Resolve architecture-determining uncertainty before accepting that architecture. If the experiment needs later build/setup work, plan those prerequisites and defer its dependent decision. Completing research does not satisfy the tested condition. In a static DAG, do not wire a generic experiment-completed report as proof the condition holds: retain the condition as unresolved for affected consumers until supporting evidence exists, then replan from the result. The experiment report can supply a decision/replanning step. Do not invent conditional-edge fields or make every alternative mandatory. Final integration or same-target delivery verification still applies. Independent work remains independent within the caller's active scope.

For detailed triggered scenarios, technology-specific questions, and specialist domain cards, read only the relevant section of [technical-interactions.md](technical-interactions.md).

## Specialist expansion

For unfamiliar or specialized technology, derive additional questions from its inspected contracts. Common extensions include mobile/offline/device lifecycle; real-time or physical systems; AI/ML and tool agents; payment/ledger semantics; analytics/ETL/scientific reproducibility; libraries/SDKs/compilers/generators; infrastructure control planes; and media/publishing/notifications. The fixed catalog is an inventory, not a claim that all concerns are known.
