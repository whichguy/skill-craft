# operations: re-cut draft (worker D)

## 1. Goal (R1)

Confirm the released result can be monitored, recovered and supported: record each readiness check with its evidence
(or a justified N/A) in this result's `summary` and `evidence_refs`, and write the current log, audit and recovery
locators to HOME/environment.md.

## 2. Duty

1. Reopen SHIPLOOP.md (the repository knowledge index) and the current observability coverage note it links. Put the
   sections you used in `evidence_refs`.
2. Check each against the running system and record it in `summary`: monitoring, alerting, log and diagnostic access,
   recovery ownership (who restores and how; the rollback works), support documentation, cleanup, and revalidation
   needs. A plan or configuration file is not evidence that the service is observed and supported.
3. Map each relevant event to its authoritative owner, existing sink and operator retrieval. Include successful and
   failed logins where the system authenticates. An inaccessible log is an evidence gap, not proof of no logging.
4. Close only evidenced gaps this run owns. Do not duplicate provider logs, and do not treat every failure as an
   incident. Keep the required audit-failure and recovery policy.
5. Write the current log and audit retrieval and recovery locators, with the date you observed them and the limits
   still open, to HOME/environment.md.
6. Record a justified N/A in `summary` only after assessing the actual operational boundary: what you assessed and
   why it does not apply.
7. Name the release-plan and system-test-author records you rely on (the latest done after the last accepted replan)
   with their locators in `evidence_refs`. A material change to code, tests, fixtures, configuration or target
   invalidates the observations it affects: rerun those, and reuse the rest only with their identity and relevance
   stated. An obligation already due and still failed, blocked or unrun stays open in `assumptions`; do not repair it
   with a new positive observation.

## 3. Checked by

Nothing beyond the exit conditions and the shared mechanical checks.

## 4. Guides to keep

- Service discovery guidance (service-discovery.md#observability-coverage): items 3 and 4.
- Deployment and handoff guidance (testing-and-documentation.md#deployment-and-handoff): item 2. Weak citation; it
  covers product-acceptance and handoff more than operations. Drop it if the owner prefers.
- Add: service-discovery.md#development-handoff for item 5 ("Operations and handoff retain current log/audit retrieval
  and recovery locators, observation dates, and unresolved limitations"). Today operations does not cite it.
- OUTER test-planning handshake (repeatable-test-suites.md#outer-test-planning-handshake): item 7.

## 5. Fidelity map (R5)

| Today's sentence (short) | New home |
|---|---|
| Verify operational readiness: monitoring, alerting, logging/diagnostic access, recovery ownership, support docs, cleanup, revalidation needs. | Item 2 |
| Record a justified N/A only after assessing the actual operational boundary. | Item 6 |
| Do not represent a plan or configuration file as evidence the service is observed and supported. | Item 2 |
| Reopen the Repository knowledge index and current observability coverage note. | Item 1 |
| Use Service discovery guidance to check event owners, existing sinks and operator retrieval, including successful/failed logins. | Item 3 |
| Close only evidenced owned gaps; do not duplicate provider logs or treat every failure as an incident. | Item 4 |
| Preserve required audit failure and recovery policy. | Item 4 |
| Consideration "Deploy: Confirm monitoring and rollback work." | Item 2 ("the rollback works") |
| OUTER handshake: current plans, retain locators. | Item 7 |
| OUTER handshake: recover a missing plan; never guess commands, drop coverage, or deploy to make a check available. | CUT for this stage: operations runs no planned test command; repeatable-test-suites.md#outer-test-planning-handshake keeps it |
| OUTER handshake: a plan is not execution evidence. | Item 2 |
| OUTER handshake: a material change invalidates affected observations; reuse with identity shown. | Item 7 |
| (consumer-delivery.md#where-completion-is-enforced) operations may retain an already-due obligation, not repair it. | Item 7, made explicit |
| (service-discovery.md#development-handoff) operations retains log/audit retrieval and recovery locators, dates, limits. | Item 5, NEW in the duty; today only the guide says it |
| STAGE_RULES | Shared section (worker B) |

## 6. Size

- Today: duty 750 + considerations 37 + OUTER handshake 916 = 1,703 characters.
- Draft: goal, duty and Checked by 2,075 characters with headings (item 5 and the open-obligation sentence are new duty text).
