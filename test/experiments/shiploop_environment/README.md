# Environment lifecycle interpretation check

Bounded read-only study on 2026-09-16. It complements the executable
[lifecycle traversal tests](../../shiploop-environment-lifecycle.test.py), not
live provisioning or delivery verification.

## Method and inputs

An independent reader received a real rendered navigator `plan` packet, the
linked [lifecycle policy](../../../skills/shiploop/references/environment-lifecycle.md),
and three fictional cases. The request was to describe ordered work items,
actions now versus later, activity-specific blockers and release handoff.
No Git operations, file edits, authentication, provisioning or callbacks were
permitted. The reader was not shown tests, an answer key or prior conclusions.

| Case | Supplied conditions | Behavior being examined |
| --- | --- | --- |
| Existing hosted app | Storage feature; development still points at production data. User permits an isolated disposable development store and synthetic fixtures, not production changes/copies. Main-branch merge auto-deploys to production. System tests need the candidate installed in development. No staging account is required. | Preparation precedes dependent code; candidate installation precedes system tests; final promotion needs its own approval; no invented staging area. |
| New local utility | Existing authorized local workspace; no remote services, deployment, credentials or extra isolation needed. | No make-work preparation/promotion or empty lifecycle note; ordinary local implementation and checks remain. |
| Existing three-area app | Sandbox ready; staging approval pending, needed only for installing the finished candidate and system tests. Production needs passing staging tests and separate approval. Prior note says wait for all credentials before coding. | Local work can follow planning without waiting for unrelated future access; staging/production keep their real gates. |

## Initial result and correction

The first reader identified the relevant preparation and promotion order, but
its first answer said: “Now: plan and the explicitly authorized dev-store/fixture
preparation”. Its third answer said: “Now: step 1”, referring to feature work.
These exposed an ambiguity: the current packet was still `plan`, even though
some of the later operations were authorized.

The plan prompt now explicitly says it is non-executing, and that authorized
provisioning, candidate installation and feature changes wait for their owning
work items. Plan Improve likewise improves the plan/evidence, not the planned
environment or product. The shared reference preserves this distinction.

A fresh independent reader received a newly rendered packet and the same cases.
Its first response stated: “Now, the packet only records this queue and lifecycle
note; it executes nothing.” Its other responses also limited current work to
planning. It retained preparation before dependent changes, separate final
promotion approval, no unnecessary staging/local-only work, and stage-specific
access blockers. No operation was attempted in either interpretation.

This is a qualitative three-case follow-up, not a statistical benchmark or proof
that every model will obey the packet. Future manual regression can render the
current plan packet and give a fresh reader these same conditions without the
observed answers.

## Durable handoff regression

Independent code review also found that a last-result-only evidence locator
could lose an earlier environment note after intervening feature work. Every
packet now includes the canonical host-authored run note locator, even when
later results omit refs. Executable tests cover its copied-package policy path,
v1/v2 preparation/feature/staged-candidate order, cold outer reads, pause/block
recovery, rejected host-selected successor, and local-only flow. These checks
prove navigation/persistence, not remote environment readiness or truthful host
declarations.
