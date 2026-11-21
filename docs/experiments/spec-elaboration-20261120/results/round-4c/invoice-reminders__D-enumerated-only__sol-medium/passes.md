## Pass 1 — The ground

Mapped activation, customer follow-up, first-time coverage, no work, settlement, pause, inspection, invalid data, access denial, dependency failures, large workloads, and rollback. Wrote the first 11 use cases and 18 clauses. The workspace contains no product source, runtime manifest, invoice schema, or committed baseline to verify.

## Pass 2 — Preconditions

Defined the source of truth, collectible balance and invoice dispositions, starting state and authority, destination selection, content required for the customer, calendar schedule, controls, input holds, and what correction does. Found no existing role names, invoice states, time zone, channel, or policy values. Marked selected defaults as choices.

## Pass 3 — Interactions

Walked eligibility and invoice edits against pending submissions, scheduling against pauses and outages, overlapping evaluations against one another, and outcome reports against retries and rollback. Added current-state checks, in-flight behavior, catch-up, supersession, retry and uncertainty rules, and activity evidence. Found no evidence of an existing manual reminder workflow or delivery event contract.

## Pass 4 — Runtime rules

Identified email submission as the external runtime boundary. Checked the SMTP acknowledgement, timeout-ambiguity, and address envelope rules against RFC 5321. Added live readiness, non-production isolation, asynchronous activation, health signals, and service timing. No host, email provider, sandbox policy, production quota, or execution limit was present. Recorded the deployment-dependent figures as unconfirmed.

## Pass 5 — Preservation and invariants

Reviewed invoice and settlement actions, existing communications, customer links, permissions across entry points, account isolation, operations visibility, message privacy, late delivery failure, existing data, and rollback. No prior product behavior could be exercised from the workspace. Preservation clauses therefore apply to the baseline behavior wherever it exists.

## Pass 6 — Buildability review

Read each use case and clause against the others. Added the missing message prerequisites, calendar boundary examples, no age cutoff, minimum spacing, explicit attempt accounting, setting races, evidence conflicts, retention, and ready-work counting. Split retry timing from its budget and post-acceptance reporting from its effect on sending. Found no specified retention period or existing invoice access contract to incorporate.

## Pass 7 — Boundary review

Rechecked the whole specification from activation through rollback. Distinguished a newer milestone opening from its first submission, resolved fallback when the latest milestone is closed, distinguished unstarted preparation from a possible submission, and made superseded attempts, rollback reconciliation, and empty-run health observable. Found no further externally specified cadence or evidence format.

## Pass 8 — Cross-checking controls, inputs, and activity

Read back through all use cases and clauses, including their source classifications. Added the live-readiness use case, defined usable mailbox input, made the healthy timing bound apply to a continuously ready milestone, and clarified counts, history visibility, manual communications, and permanent deletion. Found no historical manual-send data or provider-specific mailbox rules in the workspace.

## Pass 9 — Outcome history

Checked all clauses against the use-case flows, focusing on the differences among readiness, acceptance, delivery, supersession, and conflict. Added conflict to the visible outcome list, specified the ordinary SMTP acceptance code, and made previously displayed acceptance durable through recovery. Found no new dependency on mailbox receipt or read confirmation.

## Pass 10 — Standalone clause review

Read the observables independently of their sources. Put the three general scheduling offsets in the clause statement itself, kept outcome association separate from supersession, and placed conflict investigation with operations reconciliation. Found no other case where an exact scheduling value appeared only in a rationale.

## Pass 11 — No substantive additions

Read the full specification from the use cases through the last clause. Checked each flow against its observable behavior, cross-checked timing and suppression with recovery and rollback, and reviewed state lists, bounds, source labels, and privacy. Verified that all 14 use cases and 118 clauses are contiguous and have the required fields. This pass found nothing that would change what a builder implements and left the specification unchanged.
