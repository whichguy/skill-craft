# ShipLoop service discovery implementation plan

## Outcome and boundaries

Implement the accepted design in ShipLoop's maintained source: discover required
remote capabilities and current state, choose justified zero-copy/cache and
asynchronous service contracts, assess owned observability for local and remote
systems, and carry exact decisions, affected files and checks into development.
The user authorized implementation after the design study and observability
extension. No connector installation, remote mutation, new scheduler or result
schema is needed. Preserve the existing stage graph and current repository edits.

Source design: [remote-service and observability design](shiploop-remote-services-design-2026-09-19.md).
The small paired study supported refinement, not general prompt superiority.
Its frozen reports stay historical. This implementation receives its own evidence.

## Starting evidence

- Repository: `/Users/dadleet/src/skill-craft`, branch `main`, HEAD
  `7e4199c57a06cf9689780401c4f03f36887d9d66`, substantially dirty shared checkout.
- Before edits, actual scoped suites passed: v3 guidance 15, discovery 27,
  research-template 7, reference-routing 8, packet-bounds 7; total 64.
- Selected current file snapshots and baseline summary:
  `/Users/dadleet/tmp/shiploop-service-implementation-objq14h9/before/` and
  `/Users/dadleet/tmp/shiploop-service-implementation-objq14h9/baseline.json`.
- Existing default v3 uses package reference routes, generic evidence_refs and
  work-item context. Reference contents remain host-read evidence, not semantic
  assertions checked by the navigator. Retained protocols can reuse reference
  guidance without importing v3 schemas.

## Ordered work and acceptance

| Work | Prerequisites | Owned change and done evidence |
| --- | --- | --- |
| W1 Baseline and plan | Current checkout and prior design | Preserve current bytes; run actual scoped tests; record this plan. Complete. |
| W2 Maintained decision guide | W1 | Add `references/service-discovery.md` with scope, remote capabilities/state, cache authority, async cooperation, observability, development handoff and verification. Conditional detail; local-only restraint; no invented infrastructure. Add illustrative Salesforce mapping to its existing card. |
| W3 Prompt and reference routing | W1, W2 heading contract | Link the guide from the skill and existing discovery/behavior/platform/logging references. Add concise default-v3 stage routes/duties for early discovery, criteria/tests, planning/implementation, verification, operations and documentation handoff. Preserve graph/callbacks/schema and bounded packets. |
| W4 Structural and recovery regressions | W1; expected routes fixed before W3 | Add focused failing tests for required package routes, cold producer/Improve packets, exact host-authored context/evidence carry, relocation and local applicability. Run RED before routing edits, then GREEN plus affected existing suites. Tests must not claim model compliance. |
| W5 Independent cold-context behavior | W2, W3, W4 | Fresh agents consume real rendered packet fixtures and minimum project evidence: cache bypass/current auth versus old decoy, remote schema drift, record/polling, observability reuse and local control. Evaluate actual notes and source-reading evidence against independent expectations. Correct material failures and preserve first outcomes. No live-account claims. |
| W6 Review, distribution and closeout | W2-W5 | Independent review; fix warranted issues; run regression and package/reference checks; generate plugin views through supported script, with before/after accounting. Record source versus generated versus published state and evidence limits. No commit/push required. |

W2 and W4 may proceed independently after the heading/route contract is agreed.
W3 is parent-owned to avoid collisions in the current dirty prompt catalog.
Only generated distribution tools update plugin views; do not hand-edit them.

## Contract and proportionality

Required guide sections: `select-scope`, `remote-capabilities-and-state`,
`cache-and-authorization`, `asynchronous-cooperation`, `observability-coverage`,
`development-handoff`, `verification`.

Remote discovery separates provisioning MCP from runtime interfaces and effective
identity, metadata from record CRUD, partial/denied observations from absence,
and prior/local/remote/requested state before incremental change. Safe authorized
reads are valid discovery; later writes retain their real target/authority gates.

Cache choice needs benefit and correctness evidence. Separate freshness from
revocation; require trusted scope, row/field/query enforcement, data/schema/policy
invalidation, stale-fill and missed-event recovery, and explicit unknown-authority
behavior. A cache remains optional, including when direct remote reads suffice.

Async cooperation may use existing durable records and polling. Define commit
and completion, dispatch/recovery owner, duplicate/stale result behavior, worker
authority, status/result access and retention; no blanket broker/outbox mandate.

Observability applies locally too. Inventory authoritative event owners and
existing sinks. Include successful/failed logins when applicable; reuse/configure/
extend before a new facility, keep failures separate from incidents, protect
required audit coverage and sensitive data, and verify actual retrieval.

Handoff records requirements, decisions, evidence/unknowns, changed file roles,
ordered producers, checks and revalidation in existing documents and context.
Missing prerequisites gate their actual dependents only. Local/stateless work
must not acquire remote/auth/cache/telemetry prerequisites to satisfy a checklist.

## Verification strategy

Run current Python unittest suites using repository entrypoints. Extend the
existing v3 guidance suite so the standard inventory includes new checks without
a second runner. Selective package-relative links must survive relocation.
Cold state render remains read-only; synthetic Improve receipts test traversal,
not execution of Improve. Check packet bounds and pending-child ownership.

Semantic fixtures must evaluate choices, not keyword counts. A current retained
contract requiring cache bypass must survive a superseded shared-cache decoy;
its locator and revalidation condition must appear in the proposed inner plan.
Polling/recovery must remain viable without invented push infrastructure; remote
computed/unrelated fields must be preserved; provider login logs must be reused
and only missing app-owned events added to the existing logger. A pure local
formatter must remain local. Model exercises do not prove real cache safety,
remote permission enforcement or deployed application operation.

## Completion record

W1-W6 are complete: source review, targeted tests, package synchronization and
evidence retention are finished. The optional broader sweep was stopped after
the user questioned whole CI for a prompt enhancement; 89 suites completed
(87 passed, two unrelated failures), and the final legacy suite was intentionally
interrupted. The broader sweep is partial and is not the acceptance gate for
this prompt/reference change.
The bounded model exercises are complete with explicit partial outcomes, not a
claim that every first-pass discovery is complete.

| Delivered role | Maintained file(s) |
| --- | --- |
| Conditional service contract | `skills/shiploop/references/service-discovery.md` |
| Salesforce illustration | `skills/shiploop/references/platforms/salesforce.md` |
| Selective routes and stage duties | `skills/shiploop/scripts/shiploop_navigator_v3_prompts.py` |
| Entry/discovery/model/platform/logging links | `skills/shiploop/SKILL.md`, `README.md`, `references/research-loop.md`, `behavioral-requirements.md`, `platform-discovery.md`, `coding-practices.md` |
| Recovery/route/relocation tests | `test/shiploop-v3-guidance.test.py` (15 existing + 4 added checks) |
| Reproducible offline cases and evidence | `test/experiments/shiploop_service_discovery_20260919/prepare.py`, `README.md`, `RESULTS.md`, `evidence/` |
| Generated distribution copy | Nine matching source-copy paths under `plugins/shiploop/skills/shiploop/`, generated through `sync-plugin-views.sh` |

The historical selected-file patch and hashes are retained in
[implementation.patch](../test/experiments/shiploop_service_discovery_20260919/evidence/implementation.patch)
and [implementation-files.json](../test/experiments/shiploop_service_discovery_20260919/evidence/implementation-files.json).
The navigator runtime bytes, stage sequence, result schema and callbacks remain
unchanged; no connector, credential, remote object or new runtime machinery was
introduced. Existing unrelated checkout edits were preserved. No commit, push,
marketplace publication or live Salesforce validation is claimed.
The existing Codex skill symlink currently selects the separate
`/Users/dadleet/src/skill-craft-coverage-release-20260919/skills/shiploop`
checkout. That installed selection was preserved; this task updates the source
checkout and its generated plugin copy, not the separate release checkout.
A read-only `git apply --check` found differing source/test context in five
release-checkout paths, so that integration needs reconciliation; the scoped
patch is a review artifact, not a verified drop-in release patch. Delivery review
also found concurrent current-system-baseline additions in that retained diff.
Those already-delivered hunks are excluded from the service-only integration;
the frozen service candidate supplies its guide and stage additions.

The frozen service candidate passed **93 checks** and plugin parity passed.
Another task subsequently added current-system-baseline guidance and three
checks in this shared checkout. Those edits were preserved; the combined source
passed **96 targeted checks** with stable input hashes, and package parity passed.
Independent review found no conflict with the service guidance. The retained
service patch and semantic snapshots describe the earlier candidate; concurrent
baseline work is not attributed to this task.
Independent source review found no material contract defect. Eight fresh-reader
reports tested discovery and cold handoff; they motivated added instructions
for safe interim reads, preservation, conditional logging and async ownership.
Cold handoff, local authentication logging and the local control met their rubrics.
The final remote producer still omitted explicit unrelated-field preservation
and the durable acceptance/completion gap, and inferred one diagram connection.
These are retained limitations: the source guidance now explicitly asks for
those contracts, but the experiment does not establish reliable first-pass
completeness. The existing normal Improve review must assess the actual notes,
not treat a guide locator as proof. No new semantic validator is claimed.

See [verification results and limitations](../test/experiments/shiploop_service_discovery_20260919/RESULTS.md)
for the final suite accounting, raw outputs, separate prompt versions, unchanged
fixture-input checks, independent judgments and broader unrelated harness issues.


## Git delivery integration

After the user authorized commit, merge and push, the service changes were ported
into an isolated worktree based on current `origin/main`
`73ed1462d527ae25f829616164378a8fdfb3c4ca`. The original dirty checkout and its
unrelated local history were preserved. The port adds only service guidance,
reference links and four service tests, alongside the newer baseline, state/data,
remote-test, parallel-chain and lifecycle guidance already on main.

ShipLoop is versioned `0.18.9`; package views, manifests and native catalogs were
regenerated from source. The pre-port v3 suite passed 26 checks. The integrated
candidate passed **105 targeted tests**, full generated-view parity and package
metadata checks, with stable source/test hashes. Independent diff review found
no blocking issue. Full CI and model trials were not rerun. The two bounded
study directories and their historical results are included deliberately as this
task's research evidence, with their limits preserved.

[Integration verification](../test/experiments/shiploop_service_discovery_20260919/evidence/delivery/verification.json)
records the tested base, version, commands, counts and raw-log hashes. Git history
and the push receipt establish delivery; these tests do not claim installed-host
activation, a marketplace pin update, or live remote-service validation.
