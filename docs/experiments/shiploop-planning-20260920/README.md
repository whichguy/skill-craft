# ShipLoop planning breadth study — 2026-09-20

This release clarifies how ShipLoop's v3 planning pass turns an approved outcome
into useful implementation increments. The aim is not to maximize task count.
It is to split work only when distinct prerequisites, independently checkable
outputs, or ownership boundaries make that useful; otherwise it keeps work
together.

## What changed

The plan result now illustrates the existing `work_items` queue. Guidance asks
the planner to identify real supplier outputs before their consumers, to keep
checks with the affected implementation when appropriate, and to distinguish
causal dependencies from shared files or resource contention. Packets explain
that a supplied carry-forward queue replaces the future suffix, while omission
retains it. They also distinguish the accepted queue from an Improve draft.

ShipLoop still uses its ordinary serial work-item queue: it revalidates the
script-selected item in queue order. This does not add a scheduler, dependency
schema, semantic gate, timer, review loop, or parallel work-item executor.
Existing inner implementation-step parallelism is a separate mechanism and was
not changed by this release.

For example, if W1 is current and W2/W3 are pending, omitting `work_items`
retains W2/W3. Supplying `NEW` replaces the future queue with NEW; it does not
append NEW to W2/W3. Correct scope reconciliation remains a planner and reviewer
responsibility.

## Controlled study

The original Grok study compared frozen preparation snapshots of the baseline
and candidate guidance. It ran 60 primary producer calls across 13 first-pass
and four carry-forward scenario families, with 22 usable blinded paired reviews.
Calls used Grok CLI 1.0.34 with the Grok service, requested model `grok-4.6`
and xhigh effort held constant. The scenarios cover small controls, migrations, async behavior, external
prerequisites, independent work, fan-out/fan-in, failed baselines, invalidated
work, and authorized supersession.

| Primary measure | Baseline | Candidate |
| --- | ---: | ---: |
| Producer calls | 30 | 30 |
| Valid JSON and Navigator result schema | 26/30 | 25/30 |
| All six criteria in usable blind pairs | 20/22 | 22/22 |
| Coverage, useful increments, dependencies | 21/22 each | 22/22 each |
| Queue adherence and scope readiness | 22/22 each | 22/22 each |
| No padding | 21/22 | 22/22 |

The six criteria were coverage, useful increments, dependency correctness,
queue adherence, scope/readiness, and absence of padding. They accepted a
single coherent item where it owned the required artifacts and checks; no fixed
task count was rewarded. Across 18 comparable first-pass pairs, baseline plans
contained 50 total work items and candidate plans 48; both medians were two.

Two material baseline failures motivated retaining the clarification. One plan
assumed a required migration/backfill artifact already existed and omitted its
producer before an API consumer. Another duplicated checks in a tests-only item before implementing the same CLI
behavior. Its candidate kept those checks with implementation and retained the
required terminal runbook. Candidate plans
avoided those failures in the reviewed comparisons. A correct baseline repeat
on the latter case shows the issue was intermittent, not universal.

Both arms passed all four supplied-context carry-forward scenarios. This supports
the combined guidance as a narrow improvement. It does not establish that any
individual sentence, queue locator, or amount of model thinking caused the
observed difference.

## Supplemental async-UI coverage

The primary async-UI case had no usable pair because both initial baseline
outputs were malformed. A separately frozen four-producer follow-up added three
valid outputs and one usable blinded pair. Both plans passed all six criteria;
the candidate was preferred for clearer job recovery, acknowledgement versus
mutation, cancellation, refresh, and stale-response checks. This is supplementary
coverage, not a retry, replacement, or pooled increase in the primary result.

Across both studies, 64 producer calls and 23 blinded reviews covered 17 scenario
families. All 17 have at least one usable comparison, although several have no
usable repeat.

## Limits and release qualification

JSON reliability did not improve: each arm had five malformed outputs across 32
producer attempts. Malformed outputs excluded their pair from primary scoring and
remain reported as failures. The curated scenarios, excluded pairs, and
tool-disabled setup do not support a broad reliability claim.

The study tested reasoning over frozen preparation snapshots. It did not test
autonomous locator discovery, actual Improve campaigns, product implementation,
live application behavior, live app end-to-end flows, or runtime parallelism.
It also does not provide a causal timing result or a minimum planning-time target.

The release ports the narrow change onto the `0.18.12` release base
(`04c0c56e131bf1a12b115977da2bb06c30a57ece`),
preserving that base's newer source. Release-specific tests separately verify the
port. This report does not claim that publication, marketplace synchronization,
CI, merge, or push has succeeded; those actions require their own receipts.
