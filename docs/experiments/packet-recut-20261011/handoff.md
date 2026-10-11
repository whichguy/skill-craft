# handoff: re-cut draft (worker D)

## 1. Goal (R1)

Write the final handoff in this result's `summary`: the source, test, integration, release, consumer and operational
status, each with its evidence locator in `evidence_refs`, and every limit and open item with who reports what.

## 2. Duty

1. Write the status in `summary`, one line each, with its evidence in `evidence_refs`: source (and its return),
   tests, integration, release, consumer behaviour, operations. Base each on a current observation; an intent, a
   stale green result or a conversation summary is not evidence.
2. Classify every selected case as passed, failed, blocked, not-run or justified N/A, and reconcile each requirement
   clause with its case, required surface and due phase, the surface checked, the candidate, the status and the
   evidence. A pass on another surface only supports; source, HTTP or DOM structure alone cannot close a rendered
   interaction. A case not yet due keeps its phase, owner and prerequisites; missing due evidence stays incomplete.
   Never claim every requirement met while a required observation is unrun.
3. State where release-verify's consumer checks ran, from the packet's "Consumer checks (release-verify)" line, or
   that none ran. Checks that ran in the work area did not observe the user's checkout: list that as a limit.
4. List in `assumptions` every open item still unverified, from product-acceptance's list and every other stage's
   result, each with who does what and what they report back. Add the follow-up work, the blockers and the
   revalidation conditions to `summary`.
5. Isolated run: the handoff needs a current return receipt. When release did not return the candidate, run the
   packet's plan-return command, decide every undecided path with review-return, then run its return command. Put
   the receipt's path in `evidence_refs`.
6. Check from the returned project, without the run directory, that the knowledge survives: HOME/README.md and
   SHIPLOOP.md link HOME/spec.md, HOME/environment.md, HOME/architecture.md and the feature list; the AD-<n> entries
   in HOME/architecture.md hold the current service decisions, ownership, unresolved boundaries and revalidation
   conditions; their source and check locators open for a fresh reader. Keep the prior baseline's as-of account.
   Fix a broken link or missing entry in HOME/ now. Work-item context and earlier result references alone are not a
   durable index.
7. Read release-verify's `lessons` (quoted in the hand-offs). Carry its open-next items into the follow-up work in
   `summary`, and report any conflict between them and what you observed.

## 3. Checked by

- A missing current return receipt (isolated run).
- ShipLoop checks that every requirement ID in FEATURE/spec.md is in HOME/spec.md. When this run's commits reach your
  branch (an in-place run or a fast-forward return) it removes FEATURE/spec.md in its own commit. A removal it
  cannot write or commit leaves the handoff pending, naming the file and the next step. It never refuses the handoff
  for the IDs or the route.

## 4. Guides to keep

- Deployment and handoff guidance (testing-and-documentation.md#deployment-and-handoff): items 1 and 2.
- Current-system baseline guide (current-system-baseline.md#retain-across-runs): item 6.
- Service discovery guidance (service-discovery.md#development-handoff): item 6.
- Workspace return guidance (workspace-lifecycle.md#inner-assembly-and-final-return): item 5.

## 5. Fidelity map (R5)

| Today's sentence (short) | New home |
|---|---|
| Prepare an honest final handoff with source, test, integration, release, consumer and operational status. | Goal and item 1 |
| ... evidence locators; limits; blockers; follow-up work; revalidation needs. | Items 1 and 4 |
| List each open item as unverified, with who reports what. | Item 4 |
| Report where release-verify's consumer checks ran (or that none did), from the packet's line. | Item 3 |
| Checks that ran in the work area did not observe the user's checkout; list that as a limit. | Item 3 |
| Reconcile durable project documentation and product-return receipts where applicable. | Items 5 and 6 |
| Do not transform an intent, stale green result or conversational summary into completion evidence. | Item 1 |
| Verify current system knowledge, accepted changes and unresolved limits survive outside transient run notes. | Item 6 |
| Preserve the prior baseline's as-of account. | Item 6 |
| Verify durable README/index links from the returned project documentation home. | Item 6 |
| Use Service discovery guidance to retain service decisions, source and check locators, ownership, unresolved boundaries, revalidation conditions in indexed project documents. | Item 6 |
| Verify those locators are usable by a fresh reader. | Item 6 |
| Work-item context and earlier result references alone are not a durable index. | Item 6 |
| Knowledge line: feature-spec ID check and removal at handoff. | Checked by |
| Hand-off line: "No unverified list is recorded for product-acceptance ... read other stages' results." | Stays as hand-off data in "What you work from"; item 4 carries the obligation |
| Location line: "Handoff completion requires a current script-verified return receipt." | Checked by and item 5 |
| Selected-case reconciliation (all sentences). | Item 2 |
| OUTER handshake: name the plans relied on, retain locators. | CUT for this stage: handoff runs no planned check; the locators are in the stage results it reads. Unsure, keep a clause if the owner wants handoff to list the plan locators |
| OUTER handshake: a plan is not execution evidence; a material change invalidates observations. | Item 1 ("a current observation"; "a stale green result is not evidence") |
| Done when: "the workspace return is verified (worktree runs)". | Exit condition (unchanged); item 5 is its duty |
| Hand-off value `lessons` (release-verify's, quoted by value; CONSUMES in shiploop_navigator). | Item 7: today the packet quotes it but the duty never says what to do with it |
| STAGE_RULES | Shared section (worker B) |

## 6. Size

- Today: duty 1,213 + OUTER handshake 916 + selected-case 665 + knowledge line about 520 = about 3,300 characters.
- Draft: goal, duty and Checked by 3,061 characters with headings (item 5, the return, and item 7, the quoted lessons, are
  new duty text).


## Tightened (pass 2)

Duty size (inline): 2,737 -> 2,518 characters (-9%). Goal: 'Write the final handoff in `summary`: status per area with locators in `evidence_refs`, plus limits and open items.'; short goal: 'write the final handoff'.

Text now in `DUTIES['handoff']` (placeholders such as the Backchain item and item commit rule are filled at render):

```
1. `summary`, one line each, evidence in `evidence_refs`: source (and its return), tests, integration, release,
   consumer behaviour, operations (Deployment and handoff guidance). Base each on a current observation; an intent,
   stale green result or conversation summary is not evidence. Name the release-plan and system-test-author records
   relied on (latest done after the last accepted replan; OUTER test-planning handshake), locators in
   `evidence_refs`.
2. Classify every selected case passed, failed, blocked, not-run or justified N/A; reconcile each requirement clause
   with its case, required surface and due phase, checked surface, candidate, status and evidence. A pass on
   another surface only supports; source, HTTP or DOM structure alone cannot close a rendered interaction. A case
   not yet due keeps its phase, owner and prerequisites; missing due evidence stays incomplete. Claim no
   requirement met while a required observation is unrun.
3. State where release-verify's consumer checks ran (the packet's "Consumer checks (release-verify)" line) or that
   none ran. Checks that ran in the work area did not observe the user's checkout: list that as a limit.
4. `summary` lists every open item still unverified (product-acceptance's `unverified` list and every other stage's
   result), each with who does what and what they report back; add follow-up work, blockers and revalidation
   conditions.
5. Isolated run: handoff needs a current return receipt. If release did not return the candidate, run the packet's
   plan-return, decide every undecided path with review-return, run its return command (Workspace return guidance);
   receipt path in `evidence_refs`.
6. From the returned project, without the run directory, check the knowledge survives: durable documentation links
   resolve in the returned repository (HOME/spec.md, HOME/environment.md, HOME/architecture.md); the AD-<n> entries
   in HOME/architecture.md hold the current service decisions, ownership, unresolved boundaries and revalidation
   conditions (Service discovery guidance); their source and check locators open for a fresh reader. Keep the prior
   baseline's as-of account (Current-system baseline guide). Fix a broken link or missing entry in HOME/ now.
   Work-item context and earlier result references are not a durable index.
7. Read release-verify's `lessons` (quoted in the hand-offs); carry its open-next items into the follow-up work in
   `summary` and report any conflict with what you observed.
```

Map: every numbered item and every obligation of the first re-cut is kept, in the same order, so the loop Work lines can still cite "DO 1-n". Cut or merged in this pass: restatements of what the shared layout already says (result shapes, loop mechanics, commands), explanatory "why" clauses, and repeated qualifiers ("a recorded X, not a Y" pairs kept once); lists were joined into one clause where each part kept its destination. Nothing moved to another stage. The text stayed close to its first re-cut size because those duties were already one fact per clause; a further 40% would drop an obligation, which the brief forbids.
