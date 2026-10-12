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


## Tightened (pass 2)

Duty size (inline): 1,827 -> 1,728 characters (-6%). Goal: 'Confirm the release can be monitored, recovered and supported: evidence in `summary`, locators in HOME/environment.md.'; short goal: 'confirm operational readiness'.

Text now in `DUTIES['operations']` (placeholders such as the Backchain item and item commit rule are filled at render):

```
1. Reopen the observability coverage in HOME/environment.md and HOME/architecture.md; cite the sections used in
   `evidence_refs`.
2. Check each against the running system and record in `summary`: monitoring, alerting, log and diagnostic access,
   recovery ownership (who restores and how; the rollback works), support documentation, cleanup, revalidation needs
   (Deployment and handoff guidance). A plan or configuration file is not evidence the service is observed and
   supported.
3. Map each relevant event to its authoritative owner, existing sink and operator retrieval (Service discovery
   guidance), successful and failed logins included where the system authenticates. An inaccessible log is an
   evidence gap, not proof of no logging.
4. Close only evidenced gaps this run owns. Duplicate no provider logs; treat not every failure as an incident; keep
   the required audit-failure and recovery policy.
5. Write the current log and audit retrieval and recovery locators, with observation date and open limits, to
   HOME/environment.md (Service handoff guidance).
6. A justified N/A in `summary` only after assessing the actual operational boundary: what you assessed, why it does
   not apply.
7. Name the release-plan and system-test-author records you rely on (latest done after the last accepted replan;
   OUTER test-planning handshake) with locators in `evidence_refs`. A material change to code, tests, fixtures,
   configuration or target invalidates the observations it affects: rerun those, reuse the rest only with identity
   and relevance stated. An already-due obligation still failed, blocked or unrun stays open, named in `summary`
   with its owner; repair it with no new positive observation.
```

Map: every numbered item and every obligation of the first re-cut is kept, in the same order, so the loop Work lines can still cite "DO 1-n". Cut or merged in this pass: restatements of what the shared layout already says (result shapes, loop mechanics, commands), explanatory "why" clauses, and repeated qualifiers ("a recorded X, not a Y" pairs kept once); lists were joined into one clause where each part kept its destination. Nothing moved to another stage. The text stayed close to its first re-cut size because those duties were already one fact per clause; a further 40% would drop an obligation, which the brief forbids.
