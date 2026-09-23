# Technical interactions and specialist extensions

Read only triggered rows after the source-derived screen in [technical-lenses.md](technical-lenses.md). These questions do not create requirements by themselves.

## Cross-lens review: where hidden dependencies often appear

Activate a row when its conditions exist in the actual system. These scenarios are proposed controls, not claims that the corresponding defect exists in this repository.

| Interaction | Probe and expected dependency consequence |
| --- | --- |
| UI × API × transaction × retry | The mutation commits but its response is lost. Determine how a retry recovers the original outcome without duplicating the effect, and how the UI identifies the confirmed result. |
| UI × identity × cancellation | Switch accounts or documents while a request is in flight. A stale response must not mutate or announce success in the replacement context. |
| UI × accessibility × permission | A capability is denied or revoked. Recovery must remain discoverable, keyboard-usable, and truthfully announced; a transient visual toast may not supply it. |
| Schema × migration × concurrency | A backfill and old writers run together. Establish how new writes are included, conflicts avoided, and completion verified before the new reader relies on the field. |
| Schema × serialization × locale | A localized date, decimal, delimiter, or enum crosses an API/export boundary. Verify canonical meaning and round-trip behavior, not merely syntactic validity. |
| Transaction × event × external effect | The local commit succeeds and dispatch fails, or dispatch succeeds before a local rollback. Determine the durability/reconciliation mechanism needed for the promised outcome. |
| Queue × idempotency × restore | Replay after recovery can redeliver already processed events. Ensure restored dedupe/checkpoint/output state agrees or define reconciliation. |
| Cache × authorization × tenancy | Permissions change while a cached entry remains usable. Check key scope, invalidation, revocation, and permitted staleness at the authority. |
| Subscription × snapshot × version | Updates occur between snapshot retrieval and live subscription. A cursor/reconciliation contract must prevent missing or misordering required changes. |
| Configuration × flag × rollback | A disabled feature leaves persisted new-format data. Determine whether the old code/config can still read and safely act on it. |
| Deployment × artifact × observation | A smoke check is green for a different image/config/target. The promotion prerequisite remains unsatisfied for the candidate being released. |
| Canary × traffic × observability | The candidate appears healthy because no representative request reached it. Require a meaningful exposure or applicable synthetic observation before the gate can claim coverage. |
| Autoscaling × database × quotas | New replicas consume connections or provider quota faster than useful capacity grows. Revisit admission, limits, startup behavior, and degradation. |
| Lease × time × external mutation | A lease expires while a paused worker still holds authority to write. Decide how stale ownership is detected or fenced at the actual resource. |
| Fixture × concurrency × cleanup | Parallel tests use the same account, port, file, or queue. Partition/isolate resources and preserve cleanup responsibility after failure; do not create test-order dependencies. |
| Backup × privacy × replay | Restore reintroduces deleted records or triggers old side effects. Preserve deletion/reconciliation policy and effect identity through recovery. |
| Security × operational recovery | Normal least-privilege access exists, but the restore identity or keys do not. Recovery has a distinct prerequisite that ordinary readiness does not supply. |
| Version skew × fallback × security | A payload identified as new format fails validation. Check whether legacy fallback can incorrectly accept it and bypass new-format rules. |
| Supply chain × build × release | The checked dependency set differs from the image/action used by CI or the artifact promoted. Bind provenance and policy evidence to the actual candidate. |
| Runtime cycle × implementation DAG | A UI sends a command, receives an event, then issues another command. Implement common contracts and independent producers/consumers in an acyclic delivery plan; do not serialize every runtime hop as development work. |

For each consequential transition, select relevant perturbations from: absent prerequisite, invalid input, denied authority, duplicate, concurrent update, reordered event, delay/timeout, disconnect, crash/cancellation, partial commit, stale identity/revision, expired lease, mixed versions, resource exhaustion, cleanup/reuse, deletion, and restore. Trace failures and recovery to the user-visible or durable effect. Do not stop at the first component that returned success.

## Make the questions specific to the actual technology

The catalog is technology-neutral at discovery, then becomes technology-specific through the selected system's contract. These are illustrative specializations, not suggested dependencies to install.

| Encountered technology | Replace a vague question with a concrete investigation |
| --- | --- |
| Relational database | Replace “is concurrency handled?” with the actual isolation level, transaction boundary, uniqueness/conditional-write mechanism, conflict behavior, and retry scope. |
| Browser client | Replace “does the UI work?” with exact request correlation, local/confirmed state, account-switch behavior, focus/announcement transitions, and the actual browser security context. |
| Filesystem or shell tool | Inspect path ownership, symlink behavior, atomic replacement versus partial writes, working directory, executable/version resolution, exit/error semantics, and interruption cleanup. |
| Hosted scripting platform | Inspect the exposed remote invocation convention, installed versus active deployment identity, authorization scope, execution/quota limits, serialization limits, and remote test route. |
| Queue or stream | Name the actual partition/order scope, acknowledgment/offset semantics, redelivery policy, dedupe persistence, retention, replay, and external-output coordination. |
| Container/platform deployment | Name the artifact digest, rendered config, startup/readiness distinction, rollout parameters, drain/termination behavior, routing, and actual consumer check. |
| Plugin or skill package | Inspect the selected package root, bundled resource paths, host/runtime support, discovery versus activation versus execution, result contract, and update compatibility. |
| External API | Name the selected API/SDK version, operation/response/error contract, tenant/account/region, authentication method, idempotency behavior, rate limits, and callback semantics. |

A technology profile should come from repository evidence, accepted decisions, actual dependencies, and selected-version primary documentation. If an important technology is unrecognized, add a task-specific question card from its contract; the fixed catalog is a starting inventory, not a reason to ignore unfamiliar systems. A search hit or package name is only a lead until its applicability is established.

## Specialist extensions

Activate these from a source obligation or encountered technology. They deepen the core lenses and may reveal missing core questions; they do not add mandatory platforms.

| Domain | Additional considerations to investigate |
| --- | --- |
| Mobile, offline, and device software | Background execution restrictions, app-store/install/upgrade lifecycle, device permissions, battery/network constraints, local encryption, offline queue reconciliation, and supported OS/device versions. |
| Real-time, embedded, or physical systems | Deadline and scheduling guarantees, interrupts, device ownership, sensor validity/calibration, safe physical states, watchdogs, clock drift, firmware/hardware compatibility, and recovery constraints. |
| AI/ML, retrieval, and tool-using agents | Model/prompt/data/index versions, context and token limits, nondeterministic outputs, evaluation oracles, data/feedback drift, untrusted retrieved instructions, tool-effect authority, output validation, provider limits, and fallback quality. |
| Payments, ledgers, reservations, or regulated workflows | Domain invariants, units/precision, reconciliation, duplicate effects, irreversible external operations, audit records, retention, and actual applicable expert-approved rules. Do not infer an entire compliance regime from a keyword. |
| Analytics, ETL, and scientific computation | Data lineage, completeness/watermarks, late events, schema drift, reproducibility, sampling/bias, precision/error bounds, numerical stability, checkpointing, and recomputation cost. |
| Libraries, SDKs, compilers, and generators | Source/binary/API compatibility, language/runtime matrix, ABI/FFI behavior, generated-file ownership, determinism, package exports, extension points, and downstream consumer tests. |
| Infrastructure/control-plane products | Reconciliation/idempotency, drift detection, eventual convergence, controller leadership, deletion/finalizers, bootstrap dependencies, admission policy, and safe partial failure. |
| Media, publishing, and notifications | Asset/codec/font compatibility, rendering fidelity, upload/transcoding limits, content availability and rights where relevant, delivery versus display acknowledgment, channel preferences, and accessibility alternatives. |

