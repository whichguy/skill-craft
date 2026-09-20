# Discovery report — Contact pending-review field and repeat-list latency

~~~mermaid
flowchart LR
  Panel[Contact panel] --> Read[ContactReadService]
  Read --> Cache[Injected cache]
  Read --> CRM[CRM runtime query]
  Review[ReviewRequest status] --> Poller[Existing poller]
  Poller --> Panel
~~~

## Scope and baseline

This is an offline, read-only discovery result for the requested Contact
pending-review field and repeated Contact-list reads. No network, account,
credential, remote metadata read, schema write, callback, or product-file edit
occurred. The workspace is not a Git worktree (`git rev-parse` reported that
there is no repository); the unchanged pre-report fixture inventory has
SHA-256 aggregate
`7befd86192de8c3415e06b88a14c0b69b842b366175b5efa76bb826206931057`.

The required baseline was run from this workspace before any edit:
`python3 -B -m unittest discover -v`. It passed one test:
`FixtureSmokeTest.test_panel_keeps_existing_display_fields`. The command is
the documented smoke route in
[README.md - baseline command and narrow-coverage warning: required smoke route](/Users/dadleet/tmp/shiploop-service-implementation-objq14h9/semantic-final/cases/remote-discovery/workspace/README.md:3);
the single assertion only checks the existing panel projection in
[test_fixture.py - FixtureSmokeTest: Name and ComputedScore display](/Users/dadleet/tmp/shiploop-service-implementation-objq14h9/semantic-final/cases/remote-discovery/workspace/test_fixture.py:9).
It does not exercise a list query, cache implementation, remote schema,
authorization, async status, or a consumer UI. This is therefore a green
fixture-smoke observation, not remote-service health, consistent with
[execution-planning.md - Initial repository baseline: passing smoke proves only
its selected subset](/Users/dadleet/tmp/shiploop-service-implementation-objq14h9/semantic-final/source-snapshot/skills/shiploop/references/execution-planning.md:18).

## Observed flow and field decision

The current panel formatter returns only `name` and optional `score`
([contact_panel.py - display_contact: current Contact projection](/Users/dadleet/tmp/shiploop-service-implementation-objq14h9/semantic-final/cases/remote-discovery/workspace/src/contact_panel.py:1)).
The list path is an injected cache followed by
`runtime.query_contacts(query)`: it looks up the raw `query`, caches rows
for 600 seconds, and has no visible key scoping, invalidation, or error policy
([contact_read_service.py - ContactReadService.list_contacts: current cache and
runtime path](/Users/dadleet/tmp/shiploop-service-implementation-objq14h9/semantic-final/cases/remote-discovery/workspace/src/contact_read_service.py:4)).
The adapter comment and identity manifest identify the runtime query identity as
`crm-app-service`
([contact_read_service.py - module contract: app CRM service-account adapter](/Users/dadleet/tmp/shiploop-service-implementation-objq14h9/semantic-final/cases/remote-discovery/workspace/src/contact_read_service.py:1),
[identity-manifest.json - runtime_query: CRM app-service identity](/Users/dadleet/tmp/shiploop-service-implementation-objq14h9/semantic-final/cases/remote-discovery/workspace/tools/identity-manifest.json:2)).

Do not infer that a pending-review field is absent. The available metadata says
it is incomplete and covers fields approved for the old panel only
([contact-metadata.partial.json - coverage and completeness limits](/Users/dadleet/tmp/shiploop-service-implementation-objq14h9/semantic-final/cases/remote-discovery/workspace/remote/contact-metadata.partial.json:2)).
The separately supplied synthetic record contains fields absent from that
metadata, including `ComputedScore__c` and `Lifecycle__c`
([contact-record-shape.json - synthetic record shape](/Users/dadleet/tmp/shiploop-service-implementation-objq14h9/semantic-final/cases/remote-discovery/workspace/remote/contact-record-shape.json:1)).
It is source-only evidence, not a current target description.

The next authorized discovery step should make one narrow, read-only Contact
describe/query-contract observation with the `crm-describe-reader` role, whose
declared effect is read-only
([identity-manifest.json - metadata_read: declared reader role](/Users/dadleet/tmp/shiploop-service-implementation-objq14h9/semantic-final/cases/remote-discovery/workspace/tools/identity-manifest.json:6)).
It must establish target/tenant, API field name, type, null/default semantics,
read permissions, list-query projection and pagination behavior, and whether
the requested status is a stored Contact value or a derived view. This follows
[service-discovery.md - Remote capabilities and state: route, identity, and
read-back map](/Users/dadleet/tmp/shiploop-service-implementation-objq14h9/semantic-final/source-snapshot/skills/shiploop/references/service-discovery.md:51).
No field name such as `PendingReview__c` should be guessed. If the field is
missing, a later schema change needs the `crm-schema-writer` role plus target
approval, then a target-specific read-back; its manifest explicitly says that
metadata write needs approval and a target
([identity-manifest.json - metadata_write: approval/target requirement](/Users/dadleet/tmp/shiploop-service-implementation-objq14h9/semantic-final/cases/remote-discovery/workspace/tools/identity-manifest.json:10)).

There is a material alternate interpretation. `ReviewRequest.status` is
documented as the durable status owner, and the existing worker only polls it
([review_status_poller.py - refresh_pending_reviews: read-only poller](/Users/dadleet/tmp/shiploop-service-implementation-objq14h9/semantic-final/cases/remote-discovery/workspace/workers/review_status_poller.py:1),
[async-and-observability.md - status ownership and notification semantics](/Users/dadleet/tmp/shiploop-service-implementation-objq14h9/semantic-final/cases/remote-discovery/workspace/docs/async-and-observability.md:3)).
If “pending review” means that status, the Contact panel should consume a
derived/read-back view and preserve `ReviewRequest.status` as authority; it
should not create a competing durable Contact field. The actual ReviewRequest
processor and crash/recovery owner are not present, so no new queue, worker, or
completion claim is justified.

## Latency, correctness, and observability decision

Reuse the existing injected cache rather than add another cache, but treat its
current raw-query/600-second behavior as an observed implementation, not an
accepted freshness or security contract. It may already accelerate identical
queries; no timing, hit-rate, workload, or remote quota measurement exists.
Before changing it, define the user-facing latency and maximum-staleness
criterion rather than inventing an SLA
([requirements-definition.md - Define non-functional requirements: require
observable criteria, do not invent bounds](/Users/dadleet/tmp/shiploop-service-implementation-objq14h9/semantic-final/source-snapshot/skills/shiploop/references/requirements-definition.md:56)).

The cache contract needs a trusted server-derived partition containing the
relevant tenant/principal, effective row/field/purpose policy, locale and
projection/schema context, plus canonical query semantics; a raw caller query
is insufficient evidence of isolation. It also needs an explicit maximum age,
read-after-write and outage behavior, retention/purge decision, and
invalidation/revalidation plan for Contact mutations, policy/account changes,
schema/projection changes, and any ReviewRequest transition that changes the
derived display. A late cache fill after invalidation must not restore obsolete
rows; use a supported generation/revision or a documented bypass/re-read rule.
When current authorization cannot be established, bypass or deny through an
existing policy-enforcing adapter, never by direct privileged service-account
access. These are the applicable constraints in
[service-discovery.md - Cache and authorization: freshness, authorization, and
invalidation requirements](/Users/dadleet/tmp/shiploop-service-implementation-objq14h9/semantic-final/source-snapshot/skills/shiploop/references/service-discovery.md:76).

`app.audit` already reaches the operator sink, so any proven application-owned
cache-invalidation, cache-fallback/error, or latency event should extend that
sink with sanitized identifiers rather than create a logging system
([app_audit.py - record_contact_change: existing application audit emitter](/Users/dadleet/tmp/shiploop-service-implementation-objq14h9/semantic-final/cases/remote-discovery/workspace/src/app_audit.py:1)).
Do not duplicate interactive-login records: the identity provider owns them
([async-and-observability.md - existing provider-login ownership](/Users/dadleet/tmp/shiploop-service-implementation-objq14h9/semantic-final/cases/remote-discovery/workspace/docs/async-and-observability.md:5)).

## File and verification handoff

| Role | Later change or revalidation |
| --- | --- |
| `src/contact_panel.py` | Add a normalized pending-review projection only after API name/value/null semantics and the authoritative status decision are known; preserve the existing name/score contract. |
| `src/contact_read_service.py` | Reuse the injected cache, but implement a trusted scoped key and confirmed invalidation/revalidation behavior only after the runtime authorization and query contracts are found. |
| Runtime adapter implementing `query_contacts` (not present) | Locate it before planning: it owns list projection, filtering, pagination, and actual service behavior. |
| `workers/review_status_poller.py` | Change only if pending-review is derived from `ReviewRequest.status` and a cache/UI re-read or invalidation hook is required. |
| `src/app_audit.py` | Extend conditionally for an identified app-owned cache event, with redaction and retrieval checks. |
| `docs/requirements.md` (absent) and `SHIPLOOP.md` | On an authorized documentation step, establish a maintained requirement home for accepted field semantics and latency/freshness criteria, then link it from existing repo knowledge. No such edit was made. |
| `remote/*.json` | Preserve as limited discovery fixtures; do not treat them as a deployable schema or edit them as a substitute for target read-back. |

Planned checks are: (1) panel mapping cases for the confirmed true/false/null or
derived status states while retaining the existing display assertion; (2)
deterministic service tests with fake cache/runtime for miss, hit, scoped
isolation, expiry, invalidation, late-fill, and outage behavior; (3) an
authorized actual-target describe read and runtime list read under the intended
roles; (4) an authorization-change check that cannot expose an earlier cached
result; (5) a durable-status read-back/poller case if the value is derived; and
(6) a real repeated-list measurement against the chosen target and workload.
Local fakes prove adapter behavior only; they cannot certify remote schema,
permissions, cache safety, or consumer behavior
([service-discovery.md - Verification: local mocks do not prove remote
contracts](/Users/dadleet/tmp/shiploop-service-implementation-objq14h9/semantic-final/source-snapshot/skills/shiploop/references/service-discovery.md:209)).

The remaining gates are field semantics and authority, target/role availability,
runtime-adapter location, cache authorization/freshness policy, and measurable
latency acceptance criteria. They block only dependent schema/cache and
consumer claims; the green fixture baseline remains valid evidence of its one
local display case. No run state or callback was consumed.
