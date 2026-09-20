# ShipLoop discovery of services, cache authority, asynchronous work and observability

```mermaid
flowchart LR
  A[Requested behavior] --> B[Inspect local and remote state]
  B --> C[Map capabilities and identities]
  C --> D[Choose data and async contracts]
  D --> E[Reconcile incremental changes]
  E --> F[Link files tests and ordered work]
  F --> G[Inner step planning revalidates]
```

Design-stage recommendation: **pilot a conditional remote-service decision contract in the
existing discovery and planning flow**. Preserve ShipLoop's current stage graph,
generic result envelope and small-context handoffs. This records the initial
design and isolated prompt study. The user subsequently authorized implementation;
see the [implementation plan and completion evidence](shiploop-service-discovery-implementation-plan-2026-09-19.md).
The study did not modify active prompts or install a connector. No Salesforce org
or other private remote system was queried.

The subsequent observability requirement also applies to local systems. Assess
owned logging and monitoring coverage even when remote-service discovery is not
applicable; adequate existing coverage is a valid no-change outcome.

## What the current skill already does

The existing discovery guide screens schema, state ownership, caching,
invalidation, identities and security, and follows the system behind an MCP.
The behavior guide already distinguishes development tools from runtime actors,
and covers asynchronous state, retries, replay and missed events. This is a
consolidation and handoff problem, not a missing discovery phase.
[research-loop.md - eight-area screen: existing cache and remote-boundary coverage](/Users/dadleet/src/skill-craft/skills/shiploop/references/research-loop.md:168),
[behavioral-requirements.md - actors and channels: tooling versus runtime](/Users/dadleet/src/skill-craft/skills/shiploop/references/behavioral-requirements.md:86),
[behavioral-requirements.md - incoming events: existing async and recovery contract](/Users/dadleet/src/skill-craft/skills/shiploop/references/behavioral-requirements.md:145).

Default Navigator v3 carries decisions through ordinary `evidence_refs` and
`work_items[].context`. It renders selected reference paths from
`STAGE_REFERENCES`. The older typed `system_context` records are not the default
v3 result contract and should not be expanded for this change.
[shiploop_navigator_v3_prompts.py - COMMON: decision and locator handoff](/Users/dadleet/src/skill-craft/skills/shiploop/scripts/shiploop_navigator_v3_prompts.py:309),
[shiploop_navigator.py - result normalization: existing evidence and work-item fields](/Users/dadleet/src/skill-craft/skills/shiploop/scripts/shiploop_navigator.py:126),
[shiploop_navigator.py - reference rendering: v3 selected guide paths](/Users/dadleet/src/skill-craft/skills/shiploop/scripts/shiploop_navigator.py:1270).

These fields carry host-authored locators; Navigator does not read and validate
their semantic content. The proposal depends on the next agent reopening the
references, so a real cold-packet handoff test is an adoption condition.
[shiploop_navigator.py - prior result evidence: references remain untrusted host reports](/Users/dadleet/src/skill-craft/skills/shiploop/scripts/shiploop_navigator.py:959).

## The decision contract

Trigger this assessment when a required behavior depends on external data,
metadata, configuration, authority or independently executing work. Infer a
possible service from the behavior and verify the dependency. A service already
provided by the platform may require only configuration or a small extension.
An MCP name alone is neither a service requirement nor implementation evidence.

Retain one compact decision in the project's existing design/environment notes;
use the project's actual filenames. The following are questions, not mandatory
components or new machine fields.

| Decision | Information discovery must establish |
| --- | --- |
| Responsibility | What UI/business behavior requires the service? What existing native or shared capability supplies it? Who owns the authoritative data and business rules? |
| Provisioning route | Required operation → observed MCP tool or other supported API → remote artifact → effective identity/authority → completion/read-back evidence. Distinguish metadata/schema changes, configuration and record CRUD. |
| Runtime route | Actual caller → business operation → data adapter/query facade → source of truth. Establish runtime identity and authorization independently of developer MCP access. MCP may be a runtime route only if deliberately selected and supported. |
| Read architecture | Direct/native or federated read, existing query facade, optional cache, or copied projection. Assess query/filter/join/pagination support, workload/quotas, latency, freshness, availability, security, retention and operating cost. |
| Async cooperation | Synchronous return, durable operation record with polling, or notification plus authoritative read-back. Define ownership and completion, including recovery without the initiating UI. |
| Observability | Which owned operational, authentication and audit events must be observable, which existing emitters and destinations supply them, and what concrete gap needs configuration or instrumentation? Assess affected local and remote flows. |
| Incremental change | Compare prior accepted intent, current local definition, observed remote state and requested delta. Distinguish drift from intended change, and preserve unrelated consumers and artifacts. |
| Evidence and handoff | Sources, target role and observation time, known/unknown status, changed files, ordered prerequisites, verification, remaining decision owner and revalidation trigger. |

Classify each need as reuse, configure, extend, new justified component,
unresolved, or not applicable. Do not discover a hypothetical cache and then
create requirements to justify it. A read denied by the current identity is not
proof that a schema or object does not exist.

## Zero copy and caches

Ask what the requirement means: no replicated application database, no durable
secondary copy, or no secondary retention at all. Transient caching is compatible
with some of those meanings and conflicts with others. Record which fields or
results are retained, where, for how long, and under whose policy. A query proxy
can expose remote data without retaining results; it does not imply caching.

Consider the least costly applicable choice first: native/direct access, then an
existing facade, then a measured and justified cache or projection. Zero copy
still depends on source availability, query capabilities and source load. A cache
adds retention and correctness responsibilities even when it improves latency.

Salesforce's Data 360 decision guide distinguishes live federation from cached
local copies. Its documented accelerated-query path has refresh intervals and a
specific deletion limitation requiring full refresh. This is evidence to inspect
the exact selected feature; it is not a claim that every Salesforce cache has the
same behavior. [Salesforce Data 360 interoperability decision guide](https://architect.salesforce.com/docs/architect/decision-guides/guide/data-360-interoperability).

For each affected cache layer, require an implementable contract:

| Concern | Required decision and adversarial check |
| --- | --- |
| Data freshness | Maximum acceptable age and read-after-write behavior; exercise hit, miss, write, expiry and outage. Do not silently choose the user's tolerance. |
| Authorization freshness | Independent permission/revocation requirement and its actual enforcement point. User-specific keys and TTLs do not revoke already cached access. Test revocation without changing the underlying record. |
| Effective context | Tenant, principal or demonstrably equivalent authorization scope, query parameters, row/field restrictions, relevant purpose/locale/schema versions. Do not invent an authorization-version API; establish how current authority can actually be checked. |
| Invalidation sources | Data create/update/delete, query-membership and aggregate changes, schema/derived-result changes, sharing and policy changes, logout/account switch. Identify coverage gaps separately. |
| Races and ordering | A slow read started before invalidation must not repopulate old data afterward. Select a supported revision/generation check, synchronization rule, or bypass; test delayed fill and concurrent writes. |
| Event failure | Lost, delayed, duplicate or reordered invalidations, disconnected consumers and expired replay positions. Define resynchronization/rebuild and read behavior while trust is lost. |
| Exposure and retention | Reauthorize hits and result reads with the required consistency; apply field filtering and query scope, not only endpoint access. Include cached errors/counts where they expose protected information. Govern purge/retention separately from permission to serve. |
| Failure policy | Stale business data may be allowed by its freshness contract. It must not become an excuse to serve data whose current authorization cannot be established. For strict revocation requirements, deny or use an authoritative route; document availability consequences. |

Do not promise stronger revocation than the actual authorization source can
provide. Define the consistency boundary, including in-flight requests. Revoking
future access does not erase data a user already received. A security-context
change should also prevent old responses or notifications from being accepted by
a replacement client session.

Enforce isolation, rather than merely documenting key dimensions. Derive cache
partitions/keys from trusted canonical server-side context, never caller-asserted
tenant or entitlement values. Cache an authorized filtered representation under
the matching scope, or keep an internal data cache with complete current row,
field and query-policy enforcement on every read before exposure. Endpoint-level
authorization alone is insufficient. Bypass or deny when safe isolation or the
required current authorization cannot be established. Equivalent public/shared
data need not be copied once per user when that equivalence is demonstrated.

For Salesforce specifically, inspect record sharing, object permissions and field
permissions separately. Its secure Apex guidance distinguishes their enforcement;
`with sharing` alone does not establish object/field enforcement.
[Salesforce secure Apex guidance](https://developer.salesforce.com/docs/platform/lwc/guide/apex-security.html).
Inspect native cache ownership before adding invalidation plumbing: Apex wire
results and Lightning Data Service have documented, different refresh paths.
[Salesforce client-side cache refresh guidance](https://developer.salesforce.com/docs/platform/lwc/guide/apex-result-caching.html).

## Asynchronous collaboration can be record based

An acceptable design is: a service records an operation; an independent worker
claims and executes it; the worker updates authoritative status/result; another
service or UI reads that state. Polling is sufficient if its latency, load and
quota behavior meet the requirement. A notification can reduce delay but is not
automatically the source of truth. Subscription support is not evidence of
durable delivery, and receipt is not proof of business completion.

Specify only the needed states, such as accepted, running, succeeded and failed.
Establish when acceptance becomes durable, who recovers abandoned work, how
dispatch relates to the state commit, and whether worker effects and terminal
status are atomic. A durable status record alone does not guarantee processing.
Reuse supported transactions, conditional updates or recovery scans; introduce an
outbox or broker only when a demonstrated gap warrants it.

Keep operation identity, correlation ID, idempotency identity, resource revision
and replay position distinct. Define duplicate processing, out-of-order
completion, retries after an unknown outcome, cancellation races, deadlines,
backoff and abandoned-work recovery. Recheck authority at the operation's
consequential execution boundary according to policy, and at result read time.
Authorize notification subscriptions/recipients separately; minimize payloads,
and do not leak a result through an otherwise unauthorized channel.

For each operation, choose explicitly whether execution uses current submitter
authority, a permitted snapshot of delegated authority, or a service's own
authority. Define what revocation/cancellation after acceptance means; do not
assume the worker inherits a still-valid browser session. Give workers the
necessary scope only. Authorize operation-ID lookup, status/progress and result
locators against tenant/subject rules, since existence and timing can also leak.
Set retention and purge rules for operation inputs, errors and results as well
as cached application data.

## Observability and authentication logging: reuse before adding

Discovery should map event ownership and coverage across affected local apps,
processes, workers, gateways/MCP servers, identity providers and remote services.
Use **reuse unchanged → configure existing coverage → extend owned instrumentation
into the existing destination → new facility only for a demonstrated unmet need**.
An inaccessible or unfamiliar log is not evidence that logging is absent.

Retain a compact coverage map in existing design/environment notes:

| Decision | What to establish |
| --- | --- |
| Purpose and owner | Needed event/signal, operational/authentication/audit purpose, authoritative emitter and responsible operator. Outcome, severity and incident classification are separate. |
| Existing coverage | Logger, platform audit trail, metrics/tracing facility, collector and destination already in use; actual configuration, safe evidence sample, retrieval/access, retention and delivery limits. Select only applicable signals. |
| Authentication | Successful and failed login attempts must be recorded where authentication is part of the system. Reuse adequate identity-provider/platform coverage; assess distinct app-owned session, refresh, logout, revocation and authorization outcomes where relevant. |
| Owned gaps | Useful operation outcomes, failure reasons, latency, retries, timeouts, cache invalidation/recovery and background-work transitions. Reuse existing conventions; do not log every cache hit or payload automatically. |
| Correlation | Safe event/request/operation identifiers and timestamps across relevant service and async boundaries. Distinct hop events can be useful; avoid re-emitting the same authoritative event or adding duplicate storage without a need. Logs do not replace durable work state. |
| Data protection | Minimum necessary fields, justified actor/tenant context, protected log access, retention/purge and required integrity. Exclude passwords, raw tokens/session credentials and sensitive payloads. Sanitize untrusted fields against log injection. |
| Delivery and use | Confirm generation and retrieval, loss/duplication and bounded outage behavior. Required auth/audit events must not silently disappear under debug filters or sampling. Retain query/runbook and investigation ownership; alert only under justified conditions. |

A failed login is an authentication outcome, not automatically an incident or a
reason to page someone. A provider HTTP error is not automatically a failed user
login; use the actual observed contract and preserve unknown causes. Do not
recreate third-party authentication internals or claim events the app cannot see.
Ordinary diagnostic failure should not change the business outcome; a required
fail-closed audit policy is a separate explicit decision. A small local formatter
change needs no invented authentication or telemetry infrastructure.

ShipLoop already separates operational logs, security audit records and optional
debug detail, and addresses duplication, redaction and diagnostic failure.
[coding-practices.md - Logging and debugging: existing categories and failure boundaries](/Users/dadleet/src/skill-craft/skills/shiploop/references/coding-practices.md:110).
The addition brings ownership, adequacy and missing-event discovery forward into
planning. OWASP explicitly includes authentication successes and failures and
integration with existing log-management infrastructure.
[OWASP Logging Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html).
OpenTelemetry documents bridges to existing logging frameworks and correlation
of existing logs; this is a possible reuse pattern, not a default installation.
[OpenTelemetry logs](https://opentelemetry.io/docs/concepts/signals/logs/).

Hypothetical trace: an identity provider records login success/failure. Discovery
verifies that coverage and the operator's retrieval route. If the app subsequently
rejects a valid identity during its own session creation, it emits that distinct
app-owned event through its existing logger, with a safe correlation reference
where supported. The plan adds only that missing event and its check. If provider
logs cannot be inspected, record the coverage gap and owner; do not fabricate
failed attempts that never reached the app or replace its provider's logging.

For incremental work, recheck new entrypoints, authentication changes, event
ownership, retention/access and lost correlation. An existing backend does not
prove a new worker emits the needed event. Adding an event does not justify a new
backend. Link the coverage decision and actual emitter/configuration, test,
dashboard/query and runbook changes into spec, work-item context and operational
handoff. Validate controlled success/failure events, destination retrieval, secret
exclusion and delivery-failure behavior where applicable; discovery must not
generate real login failures without an appropriate authorized fixture.

## A concrete Salesforce-shaped trace

This is a hypothetical application trace, not a live-org observation:

1. Input: add `ReviewStatus__c` and a background assessment to a customer panel.
   Discovery retrieves scoped metadata and finds an independently added
   `Consent__c` field plus its existing automation.
2. Intermediate decision: preserve that field and automation; plan an additive
   metadata change. Map schema retrieval/deployment/status to the actual enabled
   tools and authority. Keep the application on its existing runtime data adapter.
3. Read decision: remote records remain authoritative. Reuse the business service
   and query facade. Leave caching conditional on measured benefit and provable
   authorization/invalidation behavior; disable unsafe hits meanwhile.
4. Async decision: reuse an existing operation record if its ownership and
   recovery contract suffice. `accepted` yields an operation ID. A worker records
   terminal state; a current authorized read supplies the result to the UI.
   A notification prompts that read rather than proving completion.
5. Output: linked schema, service, authorization, cache, async, UI and test changes
   in the plan, with metadata/status read-back and intended-user verification.

The official Salesforce MCP repository exposes separate data and metadata
toolsets, including SOQL querying and metadata retrieval/deployment. Availability
depends on the selected configuration and account; the example above does not
assume the user's tools or authority match that catalog.
[Official Salesforce DX MCP repository](https://github.com/salesforcecli/mcp).

A key failure trace is a cached result followed by sharing revocation without a
record edit. Neither a data-only invalidation feed nor a user-specific cache key
settles that case. If the selected service cannot establish current authorization,
strict revocation requires withholding the cached result until it can.

Two other primary sources reinforce why discovery needs precise contracts.
Salesforce CDC documents gap and overflow events that require reconciliation;
an event subscription alone therefore cannot certify cache freshness.
[Salesforce CDC replication and reconciliation](https://developer.salesforce.com/docs/platform/change-data-capture/guide/cdc-replication-steps.html).
Metadata deployment has asynchronous processing and status checks, including
post-commit finalization; retain the terminal result and actual remote read-back,
not merely the initial deployment ID.
[Salesforce Metadata API deployment lifecycle](https://developer.salesforce.com/blogs/2025/09/take-a-deep-dive-into-metadata-api-deployments).

GitHub and Reddit were searched for implementation and contrary evidence.
The official MCP implementation provides concrete capability evidence. The
small Reddit sample did not establish authorization or invalidation guarantees;
community anecdotes are not used to select a cache policy here.

## Remote inspection during discovery

Yes: scoped, authorized read-only remote inspection belongs in discovery. Use it
when metadata, deployed configuration, access or current state could change the
plan. Establish target and effective role first, then retrieve only what settles
the named uncertainty. Retain a sanitized receipt, operation, version/as-of time,
coverage and limits. Metadata may be partial or permission filtered. Avoid copying
business records or secrets into durable prompt context when a summary suffices.

An experiment should name its question, allowed effects, target/identity, input,
expected observations, budget, cleanup and decision consequence. Read-only access
is not permission for production mutations or disposable test data. An authorized
isolated write experiment may be appropriate when inspection cannot settle a
material question. Do not ask again for already applicable authority.

This fits the current cheap boundary-read and bounded-experiment guidance.
[research-loop.md - scope and frontier: relevant authorized remote reads](/Users/dadleet/src/skill-craft/skills/shiploop/references/research-loop.md:155),
[research-loop.md - experiment ladder: permitted observations and fidelity](/Users/dadleet/src/skill-craft/skills/shiploop/references/research-loop.md:335).

For an incremental update, carry the observed/desired delta into the plan, then
recheck volatile schema, permissions and dependencies immediately before the
authorized change. Source files must not blindly overwrite remote drift. Plan
compatible expansion, any needed data/config migration, consumer transition and
later contraction separately; retain rollback or forward-repair limits.
[project-knowledge.md - discovery: revalidate and preserve historical context](/Users/dadleet/src/skill-craft/skills/shiploop/references/project-knowledge.md:78),
[execution-planning.md - persisted schema changes: migration and recovery decisions](/Users/dadleet/src/skill-craft/skills/shiploop/references/execution-planning.md:306).

## File ownership and development handoff

These are artifact roles, not mandatory new filenames. Reuse adequate documents.

| Owner stage | Artifact and completion condition |
| --- | --- |
| Discovery | Existing environment/design note: actual remote target/roles, capability map, baseline metadata/state evidence, owned observability sources and coverage, inferred dependencies and material unknowns. |
| Research | Same decision note: viable options, selected/rejected choices, measured or source-supported rationale, cache/authorization/async contract, observability reuse or justified gap, and unresolved gating stages. |
| Spec | Existing maintained requirements: data freshness and revocation criteria, async outcomes, authentication/audit/operational event coverage and retention/access, preserved behavior and migration constraints. |
| Test strategy | Existing test plan/cases: independent expected results, local versus remote surfaces, identities/fixtures, setup/teardown and focused/smoke/full-suite membership. |
| Plan | Work items linked to actual metadata/schema, permission/config, service/adapter, cache/worker, UI, event emitter/collector configuration, test and deployment files. Include only justified observability changes, compatible ordering, authority gates and verification before consumers depend on a change. |
| Inner step planning | Read exact note/spec/test sections from `context`; revalidate target, drift and selected capabilities; refine owned file edits and checks. Do not reconstruct decisions from chat. |
| Documentation/handoff | Update persistent architecture/environment index, operational recovery/invalidation guidance and tested deployment/consumer locators; preserve observation dates and unresolved limitations. |

An illustrative v3 work-item context could be:

> Reopen docs/architecture.md#customer-review and docs/tests.md#revocation.
> Remote records remain authoritative; reuse the query facade. Cache is disabled
> until the authorization/invalidation contract is verified. Preserve Consent__c.
> Recheck remote metadata drift and selected schema-writer authority before edits.

Those are proposed example paths. A real plan must link existing or explicitly
planned artifacts and include the real locators in `evidence_refs`.

## Minimal integration plan

1. **Draft the generic decision section** in `references/research-loop.md`, beside
   the current eight-area screen. Use a short conditional cue that expands only
   when external data/work affects the request, plus a proportional observability
   coverage screen for local and remote flows. The isolated candidate is linked
   below; it is not installed guidance. Keep a small trigger in the normal packet
   and select the detailed reference only when applicable. Later stages reopen
   affected sections, not the entire discovery checklist.
2. **Connect existing behavior guidance** in `references/behavioral-requirements.md`
   to cache authorization and completion decisions. Consolidate overlap rather
   than repeating its existing event/state lifecycle checklist. Link observability
   implementation to `references/coding-practices.md#logging-and-debugging`;
   retain owned login-success/failure coverage and reuse decisions in discovery.
3. **Wire default v3 consumers** in `scripts/shiploop_navigator_v3_prompts.py`:
   selected reference routes and concise duties for discovery, research, spec,
   test-strategy, plan, step-plan and operations. Discovery produces; research resolves; spec
   makes criteria explicit; tests define proof; planning orders work; step-plan
   reopens the accepted contract; operations verifies the selected observability
   coverage, operator access and retrieval evidence. Leave runtime schemas unchanged.
4. **Add only the platform-specific mapping** to `references/platforms/salesforce.md`:
   metadata versus data operations, CRUD/FLS/sharing, native cache refresh, and
   async status evidence. Keep the main decision generic and portable.
5. **Verify default v3 packet routing and a cold handoff** with focused current
   navigator/guidance/reference tests, a fresh agent given only the resulting
   item context, and adversarial application fixtures. Use stable headings in the
   existing decision note (capability map, cache authority, async completion,
   remote delta, observability coverage, verification). Verify discovery through research/spec, plan and
   step-plan preserves and presents each applicable locator and revalidation
   trigger, and that the fresh agent reads it. Include capability absent,
   remote drift, revoke-without-data-change, stale fill, deletion/query membership,
   lost event, worker crash/dispatch gap, stale completion, permission-denied result,
   and a local-only control. A prose-presence test is not behavioral proof.
   Add observability cases: adequate provider logs reused without another emitter;
   a missing owned login outcome added to the current logger; a local worker gap;
   inaccessible provider evidence retained as unknown; and secret exclusion,
   duplicate delivery, sink outage and required-event filtering. Verify actual
   destination retrieval when the selected surface is live.
6. **After justified adoption**, update the relevant maintained skill documentation
   and generate plugin views using the repository's sync process; verify parity
   and changed packet sizes. Do not hand-edit generated plugin skill bodies or
   mix unrelated shared-checkout edits into a release.

No new discovery database, state machine, scheduler, MCP installation or fixed
middle-tier stack is needed for this proposal. The next experiment should judge
discovery quality and complete downstream handoff, not merely mention counts.

The cold-handoff oracle should be concrete before integration: retain a current
decision section requiring cache bypass until live per-user authorization and
invalidation are verified, alongside an explicitly superseded note recommending
a shared cache. Give a fresh agent only actual plan/step-plan packets and their
allowed locators. Require a tool-read trace of the current section, its exact
citation in the resulting plan, cache bypass, the permission-revocation check and
the same revalidation condition. Fail if the plan enables the cache, omits the
condition or follows the decoy. A second fixture requires existing record polling
and protects computed/unrelated remote fields; fail if the handoff introduces a
broker or overwrites those fields without new evidence. Run negative controls
with the current locator removed or pointing at the wrong version so the oracle
demonstrably rejects a broken handoff. This is a proposed behavioral experiment,
not a guarantee supplied by string validation or an already completed test.

## Pilot artifacts and current verification

The scoped baseline produced 27 passing discovery tests, 7 research-template
tests and 8 reference-routing tests (42 total).
The full repository suite and live Salesforce behavior were not tested.
The retained receipt is a coordinator summary of actual tool output, not a raw
runner log: [baseline-checks.json - initial checks: commands and observed counts](/Users/dadleet/src/skill-craft/test/experiments/shiploop_remote_services_20260919/coordinator/baseline-checks.json).

[candidate-cue.md - conditional contract: exact proposed discovery addition](/Users/dadleet/src/skill-craft/test/experiments/shiploop_remote_services_20260919/candidate-cue.md:1)
and [PROTOCOL.md - pilot bounds: frozen inputs and independent review rubric](/Users/dadleet/src/skill-craft/test/experiments/shiploop_remote_services_20260919/PROTOCOL.md:1)
retain the measured study definition. All four reports and two independent blind
reviews completed: one narrow preference for the candidate and one tie. Both
variants kept the local control local. This is synthesis of supplied hypothetical
facts, not proof of autonomous discovery or live service behavior.
[RESULTS.md - paired comparison and adjudication: results and limitations](/Users/dadleet/src/skill-craft/test/experiments/shiploop_remote_services_20260919/RESULTS.md:1).

The post-review proposal uses a short entry cue and a conditional detailed
reference; these refinements have not been rerun in the paired study.
[proposed-entry-cue.md - trigger: load detailed guidance only when relevant](/Users/dadleet/src/skill-craft/test/experiments/shiploop_remote_services_20260919/proposed-entry-cue.md:1),
[proposed-reference.md - refined contract: trusted isolation and async authority](/Users/dadleet/src/skill-craft/test/experiments/shiploop_remote_services_20260919/proposed-reference.md:1).

The later observability extension is a proposal update outside the original
paired study. Its cases are planned; the earlier baseline and paired results
do not establish logging behavior.
