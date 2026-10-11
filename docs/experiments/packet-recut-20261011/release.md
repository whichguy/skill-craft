# release: re-cut draft (worker D)

## 1. Goal (R1)

Perform the release FEATURE/release-plan.md planned, and record its effect and the released artifact's identity (or a
justified not-applicable) in this result's `summary` and `evidence_refs`.

## 2. Duty

1. Name the release plan and the release-check result you act on: the latest done release-plan and system-test-author
   records after the last accepted replan, and release-check's result. Put their locators in `evidence_refs`. A
   missing plan is recovered or reported (`repeat`, or `replan` for missing product work); never guess a command.
2. Confirm that the exact target, operation, authority (the recorded grant) and conditions are still current, and that
   release-check's dry run passed against this candidate. When one does not hold, release nothing and report
   `blocked` or `replan` with the reason.
3. Run the planned release operation once. Save the provider's receipt in RUN/notes/<action>-release.md and put the
   path in `evidence_refs`.
4. Follow the operation to a terminal state: accepted or running is not done. Check its postconditions now, and
   record in `summary`, separately, the operation's effect and the released artifact's identity.
5. When the outcome is uncertain (a lost reply, a timeout, a partial receipt), keep every receipt and reconcile with the
   provider's supported lookup, retry, parameter-binding and conditional-mutation semantics before any retry. Never
   replay a merge, push, deployment or promotion only to complete the graph.
6. Isolated run only: return the candidate. Run the packet's plan-return command, decide every undecided path with
   review-return, then run the packet's return command. Put the return receipt's path in `evidence_refs`.
7. When the release does not apply, record in `summary` the concrete reason and what you assessed. Do not observe
   consumer behaviour here: release-verify does that next.

## 3. Checked by

Nothing beyond the exit conditions and the shared mechanical checks.

## 4. Guides to keep

- Release operation guidance (environment-lifecycle.md#release-operation-ownership): items 4 and 5.
- Delivery authority mapping (consumer-delivery.md#map-authority-readiness-to-existing-fields): item 2.
- Workspace return guidance (workspace-lifecycle.md#inner-assembly-and-final-return): item 6.
- OUTER test-planning handshake (repeatable-test-suites.md#outer-test-planning-handshake): item 1.

## 5. Fidelity map (R5)

| Today's sentence (short) | New home |
|---|---|
| Perform the planned release only when the exact target, operation, authority and conditions are current. | Goal and item 2 |
| Record operation/effect and artifact identity separately. | Item 4 |
| If release is genuinely non-applicable, record the concrete reason. | Item 7 |
| Reconcile an uncertain external outcome before retrying; never replay a merge, push, deployment or promotion simply to complete the graph. | Item 5 |
| Use Release operation guidance: distinguish accepted/running from terminal and verified. | Item 4 |
| Retain partial receipts and reconcile with supported provider lookup, retry, parameter-binding and conditional-mutation semantics. | Item 5 |
| Check operation postconditions here before completing this stage. | Item 4 |
| The script-selected release-verify owns final consumer behavior checks afterward. | Item 7 |
| Consideration "Deploy: Release only with a recorded grant; the dry run precedes the real deploy." | Item 2 |
| OUTER handshake: current plans, history, authority of pending results. | Item 1 |
| OUTER handshake: retain action, result and plan locators. | Item 1 |
| OUTER handshake: a later stage names and revalidates the plan for the current candidate. | Items 1 and 2 |
| OUTER handshake: recover a missing plan; never guess commands, drop coverage, or deploy to make a check available. | Item 1 (guessing); "deploy to make a check available": item 3 runs only the planned operation; dropping coverage: CUT for this stage (it runs no checks), kept in the handshake guide |
| OUTER handshake: a plan is not execution evidence; a material change invalidates observations; reuse with identity shown. | Item 2 (dry run passed against this candidate); the rest: CUT for this stage, kept in the handshake guide. Unsure: keep a sentence if the owner wants release to re-check a candidate changed after release-check |
| (Not in today's duty) The source return happens at release or handoff. | Item 6, NEW: today only the packet's location lines and release-plan's duty say so; the duty never tells release to return |
| STAGE_RULES | Shared section (worker B) |

## 6. Size

- Today: duty 761 + considerations 73 + OUTER handshake 916 = 1,750 characters.
- Draft: goal, duty and Checked by 1,986 characters with headings (it adds item 6, the return, which today has no duty text).
