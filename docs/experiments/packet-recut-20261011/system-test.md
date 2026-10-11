# system-test: re-cut draft (worker C)

## 1. Goal (R1)

Run the system tests system-test-author recorded on the assembled candidate: record each selected case's end state
in `summary`, each command's output in `evidence_refs`, and each case left for a later stage as an open item in
`assumptions`.

## 2. Duty

```text
1. Name the plan you run: the latest done system-test-author record after the most recent accepted replan, and its
   integrated test plan in FEATURE/system-tests.md. Before execution, acknowledge the applicable integrated test
   plan and revalidate its candidate, case selection, target and fixture assumptions. Put the plan's locators, and
   its reuse or the concrete mismatch, in `evidence_refs`. Close a required planning gap with repeat, blocked or
   replan; never guess a command or drop a required case.
2. Check before running: prerequisites, fixtures, execution location, target, identity, authorization, remote
   framework availability, and the deployed or test revision. Do not deploy to unblock a test, and do not use
   production without authority.
3. Run the due cases on the actual intended candidate and boundary (System-test placement guidance, Real-boundary
   test guidance). Do not substitute a planned case or local mock for a required system observation. A local pass
   cannot replace a blocked/unrun required remote check or establish a combined full-suite pass; keep that check's
   owner and boundary. When fixtures changed, check repeatability. Never blindly replay an uncertain external
   effect. Record each command, candidate and target, scope, cleanup outcome and unrun check in `evidence_refs`.
4. A recorded system command that fails here is not an open item: ShipLoop refuses done while it fails. Fix the
   candidate, report replan for missing product work, or report blocked when nothing else can proceed.
5. After a material change to code, tests, fixtures, configuration or target, rerun the observations it affects.
   Reuse unaffected evidence only with its identity and relevance stated.
6. Carry in the open items system-test-author recorded: run any this stage can now and report each such case in
   the summary, where it is not recorded evidence (ShipLoop's rerun covers only the recorded system commands). Leave
   the rest listed with the due stage they name.
7. A required case that only a person can run (for example, in a signed-in browser), for which the discovery and
   test-strategy records show this host has no route, and whose command system-test-author left out of
   `system_commands`, does not make this result blocked. Record it as an open item in `assumptions`: case ID, who
   does what, what they report, owner (a person), due stage (handoff, or the stage whose external effect it gates)
   as its `consumer`. Submit done once every other due check and ShipLoop's rerun pass; the handoff reports it
   unverified, never as a pass. Report blocked with `awaiting` only when a later stage takes an external,
   hard-to-reverse effect the case exists to gate, or nothing else can proceed. An enabled delivery contract keeps
   its own obligation phases.
8. Classify every selected case in `summary` as passed, failed, blocked, not-run, or justified N/A. Every case ends
   validated, validated another way (say what changed and why), or unachievable (items 6 and 7); a case written but
   not run is not an end state. Reconcile each affected requirement clause with its case, its required surface and
   due phase, the surface you checked, the candidate, the status and the evidence. A pass on another surface only
   supports. Source, HTTP, or DOM structure alone cannot close a rendered interaction. A case not yet due keeps its
   phase, owner and prerequisites; missing evidence for a case already due stays incomplete. Check that no clause
   or case was dropped. Never claim every requirement met while a required observation is unrun.
```

Shared blocks: OUTER test plans is folded into items 1 and 5; Selected-case reconciliation is folded into item 8.
Neither needs to print for this stage.

## 3. Checked by

- On done, ShipLoop runs the system commands system-test-author recorded and refuses done unless each passes. Its
  record is the evidence: a criterion is confirmed by its passing command, not by `summary`.
- For a `host_dependent` row, ShipLoop also runs the regression commands and refuses if that row's ids appear there.
- `assumptions` missing, or an open item whose consumer is not a later OUTER stage.

## 4. Guides to keep

- System-test placement guidance (system-tests.md#placement-and-dependency-rules): item 3.
- Real-boundary test guidance (testing-and-documentation.md#layers-and-real-boundaries): item 3.
- OUTER test-planning handshake (repeatable-test-suites.md#outer-test-planning-handshake): item 1.
- Drop: Repeatable test-suite guide. The text no longer cites it; system-test-author owns the harness choice.
  Keep it if a pin worker finds an obligation that needs it.

## 5. Fidelity map (R5)

| Today's sentence (short) | New home |
|---|---|
| On done ShipLoop runs the recorded system commands, refuses unless each passes | Checked by |
| The record is the evidence; a criterion is confirmed by its passing command | Checked by |
| Execute authorized system tests against the actual candidate and boundary | 3 |
| Verify prerequisites, fixtures, target, identity, authorization, observed behaviour | 2, 3 |
| Do not substitute a planned case or mock; do not deploy to unblock; no production without authority | 2, 3 |
| Acknowledge the integrated test plan; revalidate candidate, cases, target, fixtures | 1 |
| Record reuse or the mismatch in evidence_refs | 1 |
| Resolve a planning gap through repeat, blocked or corrective replan | 1 |
| Run the planned retained suite; reconcile selected cases and cleanup outcomes | 3, 8 |
| Record command, candidate/target, scope and unrun checks | 3 |
| When fixtures changed, check repeatability; never blindly replay | 3 |
| Verify execution location, remote framework availability, revision identity | 2 |
| A local pass cannot replace a remote check or establish a full-suite pass | 3 |
| Carry in the open items system-test-author recorded (run, report, leave rest) | 6 (verbatim) |
| A failing recorded command is not an open item; fix, replan or blocked | 4 |
| Person-only case with no host route does not make this result blocked | 7 |
| Record it as an open item "in the result" (case, who, what, owner, due stage) | 7, now "in `assumptions`", due stage as `consumer` |
| Submit done once every other check passes; handoff reports it unverified | 7 |
| Blocked with `awaiting` only for a gated hard-to-reverse effect or nothing else | 7 |
| An enabled delivery contract keeps its own obligation phases | 7 |
| Consideration Test: run on the assembled candidate; local pass does not replace deployed check | 3 |
| Consideration Test: three case end states | 8 (the open-item route is items 6 and 7; "in the summary" corrected to `assumptions`) |
| Consideration Tools: ShipLoop runs every system command system-test-author recorded | Checked by |
| OUTER test plans: latest done records after the most recent replan; pending/repeat/blocked not authority | 1 (system-test-author's record is the only one that exists here) |
| OUTER: retain locators in this result (Improve variant already dropped at this stage) | 1 |
| OUTER: a later stage names and revalidates the plan | 1 |
| OUTER: recover a missing plan; never guess commands, drop coverage, deploy for a check | 1, 2 |
| OUTER: a plan is not execution evidence; a material change invalidates affected observations | 3, 5 |
| Reconciliation: classify every selected case (five classes) | 8 |
| Reconciliation: reconcile each clause with case, surface, phase, checked surface, candidate, status, evidence | 8 |
| Reconciliation: a pass on a different surface only supports; Source, HTTP, or DOM alone cannot close | 8 |
| Reconciliation: not-yet-due keeps phase, owner, prerequisites; due and missing stays incomplete | 8 |
| Reconciliation: check for dropped clauses or cases; never claim all met while observations unrun | 8 |

## 6. Size

- Today: DUTIES 2,628 + considerations 876 + OUTER test plans 954 (the variant without Improve is about 910) +
  Selected-case reconciliation 665 = about 5,080 characters.
- Proposed duty (the fenced text above): 3,608 characters, with no shared block printed (-29%).
