# release-verify: re-cut draft (worker D)

## 1. Goal (R1)

Observe the released result where consumers use it, record each consumer check's outcome in this result's `summary`
and `evidence_refs`, and write this run's lessons to FEATURE/outcome.md (## Learned, ## Key considerations, ## Open
for the next run) and the result's `lessons`.

## 2. Duty

1. Name the plans you verify against: the latest done release-plan and system-test-author records after the last
   accepted replan. Put their action, result and plan locators in `evidence_refs`. Recover a missing plan or report
   it; never guess a command, drop a required case, or deploy to make a check available.
2. Run each consumer check FEATURE/release-plan.md recorded against the current target. Keep source synchronization,
   artifact identity, operation receipt and real consumer behaviour as four separate facts in `summary`. A source or
   local test pass does not discharge a required deployed interaction you did not observe.
3. For a browser surface, record for each required clause: the consumer entry reached after authentication, the
   account or target, the visible feature, and the action with its outcome. Keep non-secret routing state. Require
   app chrome or branding only when the spec asks for it. An embedded feature can satisfy its accepted boundary.
4. Classify every selected case in `summary` as passed, failed, blocked, not-run or justified N/A. Reconcile each
   affected requirement clause with its case, its required surface and due phase, the surface you checked, the
   candidate, the status and the evidence. A pass on another surface only supports. Source, HTTP or DOM structure
   alone cannot close a rendered interaction. Check that no clause or case was dropped. Never claim every requirement
   met while a required observation is unrun.
5. A blocked or unknown check stays incomplete. Keep the earlier receipts and do not release again blindly.
6. A case that needs a signed-in browser or a person's action this host cannot perform: do not loop on it. Record it
   in `assumptions` as an open item with the steps written to that person (where to go, such as a menu entry or a URL
   path, and what to do) and what they report back. Verify every other case. Only when the release cannot be
   accepted without that observation, report `blocked` with `awaiting` kind `present`; the person's report resumes
   the run and only the blocked cases are checked again against the same release.
7. Isolated run: this stage cannot return. Fix a defect the checks find in the delivered result through `replan` with
   one corrective work item; release then returns the fix. Write nothing inside the user's checkout: a file written
   there makes the return receipt stale and blocks handoff.
8. Local-only work: verify the current local candidate and its consumer behaviour. External activation N/A does not
   make these checks N/A.
9. A material change to code, tests, fixtures, configuration or target invalidates the observations it affects: rerun
   those, and reuse the rest only with their identity and relevance stated.
10. Write FEATURE/outcome.md with ## Learned (what this run learned), ## Key considerations (the decisions and risks
    that matter) and ## Open for the next run (what a later run should pick up), each in detail; ShipLoop commits
    them as the run's learnings, which the next run reads at intake. Put the same three in the result's `lessons`.
11. Update HOME/environment.md with what the release showed about targets, commands and access. Update HOME/README.md;
    link the feature list HOME/features/README.md there, never a feature's spec.md (handoff removes it). Do not create
    or edit HOME/features/README.md.

## 3. Checked by

- ShipLoop reruns every consumer check release-plan recorded, and every recorded test command, and refuses done
  unless each passes. Its record is the evidence: a criterion is confirmed by its passing command, not by `summary`.

## 4. Guides to keep

- Release operation guidance (environment-lifecycle.md#release-operation-ownership): items 2 and 5.
- Consumer delivery evidence guidance (consumer-delivery.md#evidence-and-limits): item 2.
- Deployment and handoff guidance (testing-and-documentation.md#deployment-and-handoff): item 4.
- OUTER test-planning handshake (repeatable-test-suites.md#outer-test-planning-handshake): items 1 and 9.
- Add: Which checkout release-verify observes (workspace-lifecycle.md#which-checkout-release-verify-observes): item 7.
  Today the packet does not cite it, yet it is where the consumer-check copy and its refusals are explained.

## 5. Fidelity map (R5)

| Today's sentence (short) | New home |
|---|---|
| On done, ShipLoop runs the consumer checks release-plan recorded and refuses done unless each passes. | Checked by |
| The record it writes is the evidence; a criterion is confirmed by its passing command, not the summary. | Checked by |
| Verify the actual release and deployed consumer/runtime behaviour using current target evidence. | Goal and item 2 |
| Distinguish source synchronization, artifact identity, operation receipt and real consumer behaviour. | Item 2 |
| A blocked or unknown post-release check remains incomplete; preserve receipts; do not re-release blindly. | Item 5 |
| Local-only work: verify the current local candidate and consumer behaviour; external N/A does not make these N/A. | Item 8 |
| Isolated run: this stage cannot return; a defect is fixed through replan (one corrective item); release returns it again. | Item 7 |
| Anything you run in the user's checkout must leave it as the return left it; a file written there makes the receipt stale and blocks handoff. | Item 7 |
| Browser surface: consumer entry after authentication, account/target, visible feature, action/outcome per clause. | Item 3 |
| Retain non-secret routing state; require app chrome/branding only when specified. | Item 3 |
| An embedded feature can satisfy its accepted boundary. | Item 3 |
| Source or local test passes cannot discharge an unobserved required deployed interaction. | Item 2 |
| A case needing a signed-in browser or a person's action: do not loop; open item with steps, report-back; verify the rest. | Item 6 |
| Only when the release cannot be accepted without it: blocked, awaiting kind present, its no_default; resume checks only blocked cases. | Item 6 (no_default: the shared outcome shapes already require it) |
| Consideration "Test: A passing unit suite is not delivery evidence." | Item 2 |
| Consideration "Deploy: Verify the release in the target." | Goal and item 2 |
| Consideration "Tools: On done, ShipLoop runs every consumer check release-plan recorded." | Checked by |
| Knowledge line: this stage keeps FEATURE/outcome.md, HOME/environment.md, HOME/README.md up to date. | Items 10 and 11 (the exit condition still lists the files) |
| Knowledge line: outcome.md's three sections, written in detail; committed as the learnings commit the next run reads. | Item 10 |
| Knowledge line: ShipLoop checks, screens and commits HOME/ and SHIPLOOP.md on done. | Shared section (the layout's commit line) |
| Knowledge line: link HOME/features/README.md, not a feature spec; do not create or edit the list. | Item 11 |
| Selected-case reconciliation (all sentences). | Item 4; "a case not yet due keeps its phase, owner and prerequisites": CUT here, since every case is due at release-verify; handoff keeps it |
| OUTER handshake: current plans, history, retain locators, recover a missing plan, never guess, drop coverage, or deploy. | Item 1 |
| OUTER handshake: a plan is not execution evidence. | Checked by (the rerun is the evidence) |
| OUTER handshake: a material change invalidates affected observations; reuse with identity and relevance shown. | Item 9 |
| Checked-by gate "missing lessons" and "HOME file missing or empty". | Stay in the shared Checked by list the renderer prints; items 10 and 11 are their duty |
| STAGE_RULES | Shared section (worker B) |

Unsure: item 11's content for HOME/environment.md is my reading of "keeps environment.md up to date" at this stage;
today's packet names the file but not what to add.

## 6. Size

- Today: duty 1,987 + considerations 145 + OUTER handshake 916 + selected-case 665 + knowledge lines about 900 =
  about 4,600 characters.
- Draft: goal, duty and Checked by 3,943 characters with headings.
