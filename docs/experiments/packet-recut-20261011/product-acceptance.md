# product-acceptance: re-cut draft (worker C)

## 1. Goal (R1)

Assess the assembled product against the original request: give each request outcome its end state in `summary`,
list each outcome no executed check observed in `unverified`, and route missing product work as replan
`work_items`.

## 2. Duty

```text
1. Gather the evidence: the original request and the intake result, the accepted requirements in HOME/spec.md, the
   spec and architecture changes since the run began, the integrated test plan in FEATURE/system-tests.md (the
   latest done system-test-author record after the most recent accepted replan), and the system-test result. Put
   their locators in `evidence_refs`.
2. Assess the product against the original outcome, not only the spec: its acceptance criteria, cross-cutting
   requirements, consumer impact (Consumer delivery guidance), test evidence and known limits. Reconcile new and
   preserved behaviour against the selected prior baseline and the incoming spec (Current-system baseline guide,
   Behavior traceability guidance), and check durable knowledge for remaining gaps. A recovered description or a
   planned check alone does not establish acceptance.
3. Give every request outcome one of three end states in `summary`: observed by an executed check; observed another
   way (the first method could not, so the method changed and the new check ran and passed); or unachievable here
   or not yet due, listed in `unverified` while the run continues. Before listing an outcome, try another way to
   observe it. Each `unverified` entry gives the `outcome`, the named `reason`, the `check` its owner does and
   reports to settle it, the `owner`, and the `due_stage` that reports it (handoff, or the stage whose external
   effect it gates). Carry in the open items an earlier stage recorded (system-test-author, system-test). An
   outcome stated only in the summary has no end state; an empty list says every request outcome was observed.
4. Keep verified product criteria apart from pending release verification. A case not yet due stays pending with
   its owner and prerequisites, so release can proceed. Readiness for release is not a claim that every requested
   consumer behaviour was observed.
5. Classify every selected case in `summary` as passed, failed, blocked, not-run, or justified N/A. Reconcile each
   affected requirement clause with its case, its required surface and due phase, the surface checked, the
   candidate, the status and the evidence. A pass on another surface only supports. Source, HTTP, or DOM structure
   alone cannot close a rendered interaction. Missing evidence for a case already due stays incomplete. Check that
   no clause or case was dropped. Never claim every requirement met while a required observation is unrun.
6. Route each gap: missing product work, stale evidence, or a failed or missing already-due check goes to replan
   with one corrective `work_items` entry each. A missing delivery prerequisite is named in `summary` for
   release-plan; report blocked only when nothing can proceed. Acceptance executes no release and proves no remote
   consumer boundary.
7. For a material prerequisite ambiguity, a pending or corrective dependency, or an acceptance gap, request a
   Backchain `review` / `audit` as the Backchain planning guide says, and cite its receipt in `evidence_refs`.
```

Shared blocks: OUTER test plans is folded into item 1 (this stage consumes the plan; no material change happens
here, so the rerun rule does not apply). Selected-case reconciliation is folded into item 5. The Backchain block
stays printed for this stage (item 7 points at it): its repair route and the Until Loop budget are its own
mechanics and belong to whoever drafts that shared block.

## 3. Checked by

- `unverified` missing, an entry incomplete or still holding a template placeholder, or a `due_stage` that is not a
  later stage.

## 4. Guides to keep

- Current-system baseline guide (current-system-baseline.md#retain-across-runs): item 2.
- Behavior traceability guidance (behavioral-requirements.md#traceability-and-review): item 2.
- Consumer delivery guidance (consumer-delivery.md#what-to-establish): item 2.
- OUTER test-planning handshake (repeatable-test-suites.md#outer-test-planning-handshake): item 1.
- Backchain planning guide (backchain-planning.md#navigator-planning): item 7.

## 5. Fidelity map (R5)

| Today's sentence (short) | New home |
|---|---|
| Assess against outcome, acceptance criteria, cross-cutting, consumer impact, evidence, limits | 2 |
| Distinguish verified product criteria from pending release verification | 4 |
| Not-yet-due cases may stay pending with owner and prerequisites so release proceeds | 4 |
| Failed or missing already-due checks require correction | 5, 6 |
| Readiness for release is not a claim every consumer behaviour was observed | 4 |
| Identify missing product work, stale evidence, delivery prerequisites; route honestly | 6 (routes made explicit: replan, summary, blocked) |
| Acceptance does not execute a release or prove a remote consumer boundary | 6 |
| Reconcile new and preserved behaviour against baseline and incoming spec | 2 |
| Check durable knowledge and remaining gaps | 2 |
| A recovered description or planned check alone does not establish acceptance | 2 |
| Three end states of a request outcome | 3 |
| A list entry: outcome, reason, what the owner does and reports, owner, later stage | 3, mapped to the `unverified` field names |
| Carry in the open items an earlier stage recorded (system-test-author, system-test) | 3 (verbatim, the reads pin) |
| Before listing an outcome, try another way to observe it | 3 |
| An outcome only in the summary has no end state; empty list means all observed | 3 |
| Consideration Test: assess against the original outcome, not only the spec | 2 |
| OUTER test plans: latest done records after the most recent replan; pending/repeat/blocked not authority | 1 |
| OUTER: retain locators in this result | 1 |
| OUTER: later stage names and revalidates the plan | 1, 2 |
| OUTER: recover a missing plan; never guess, drop coverage, deploy | 5 (no dropped case); "deploy" CUT: this stage runs nothing |
| OUTER: a plan is not execution evidence | 2 ("a planned check alone does not establish acceptance") |
| OUTER: material change invalidates observations | CUT here: this stage changes nothing; system-test and release-verify keep it |
| Reconciliation block (all five sentences) | 5 |
| Backchain: follow the Backchain planning guide; carry requirement and test locators | 7, 1 |
| Backchain: only route is source-aware-native; review/audit only for a material gap | 7 + shared Backchain block (kept) |
| Backchain: repair/revise route, `Backchain passes: one`, loop resources, budget | Shared Backchain block (kept, not this worker's) |

## 6. Size

- Today: DUTIES 1,643 + considerations 67 + OUTER test plans about 910 + Selected-case reconciliation 665 =
  about 3,290 characters, plus the Backchain block 2,295.
- Proposed duty (the fenced text above): 3,065 characters, plus the Backchain block (-7%). The duty itself grows
  because the routes and the `unverified` fields are now explicit (R4); the two shared blocks no longer print.


## Tightened (pass 2)

Duty size (inline): 3,118 -> 2,874 characters (-8%). Goal: "Assess the product against the request: each outcome's end state in `summary`, gaps in `unverified`, missing work as replan."; short goal: 'accept the assembled product'.

Text now in `DUTIES['product-acceptance']` (placeholders such as the Backchain item and item commit rule are filled at render):

```
1. Gather: the original request and intake result, the accepted requirements in HOME/spec.md, the spec and
   architecture changes since the run began, the integrated test plan (latest done system-test-author record after
   the most recent accepted replan, and HOME/environment.md ## Harnesses and suites; OUTER test-planning handshake),
   and the system-test result. Locators in `evidence_refs`.
2. Assess the product against the original outcome, not only the spec: acceptance criteria, cross-cutting
   requirements, consumer impact (Consumer delivery guidance), test evidence, known limits. Reconcile new and
   preserved behaviour against the prior baseline and incoming spec (Current-system baseline guide, Behavior
   traceability guidance) and check durable knowledge for gaps. A recovered description or planned check alone does
   not establish acceptance.
3. Give every request outcome one end state in `summary`: observed by an executed check; observed another way (the
   first method could not, the new check ran and passed); or unachievable here or not yet due, listed in
   `unverified` while the run continues. Try another way to observe it before listing. Each `unverified` entry:
   `outcome`, named `reason`, the `check` its owner does and reports, the `owner`, the `due_stage` that reports it
   (handoff, or the stage whose external effect it gates). Carry in the open items earlier stages recorded
   (system-test-author, system-test). An outcome stated only in the summary has no end state; an empty list says
   every outcome was observed.
4. Keep verified product criteria apart from pending release verification: a case not yet due stays pending with
   owner and prerequisites, so release can proceed. Release readiness is not a claim that every consumer behaviour
   was observed.
5. Classify every selected case in `summary` passed, failed, blocked, not-run or justified N/A; reconcile each
   affected requirement clause with its case, required surface and due phase, checked surface, candidate, status
   and evidence. A pass on another surface only supports; source, HTTP or DOM structure alone cannot close a
   rendered interaction. Missing evidence for a due case stays incomplete. Check that no clause or case was
   dropped; claim no requirement met while a required observation is unrun.
6. Route each gap: missing product work, stale evidence, or a failed or missing due check goes to replan with one
   corrective `work_items` entry each. A missing delivery prerequisite is named in `summary` for release-plan; blocked
   only when nothing can proceed. Acceptance executes no release and proves no remote consumer boundary.
7. A material prerequisite ambiguity, pending or corrective dependency or acceptance gap: request a Backchain
   `review` / `audit` as the Backchain guidance below says; cite its receipt in `evidence_refs`.
```

Map: every numbered item and every obligation of the first re-cut is kept, in the same order, so the loop Work lines can still cite "DO 1-n". Cut or merged in this pass: restatements of what the shared layout already says (result shapes, loop mechanics, commands), explanatory "why" clauses, and repeated qualifiers ("a recorded X, not a Y" pairs kept once); lists were joined into one clause where each part kept its destination. Nothing moved to another stage. The text stayed close to its first re-cut size because those duties were already one fact per clause; a further 40% would drop an obligation, which the brief forbids.
