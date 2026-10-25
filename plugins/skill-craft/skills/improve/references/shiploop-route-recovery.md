# Improve: ShipLoop recovery and the stopped child

Read this file only when [the core](shiploop-route.md#cases-read-only-when) sends you here: a return is `error`, `stopped` or `blocked`; the receipt or the runtime state is missing or damaged; an interruption may have left a pass half done (an edit or a commit with no recorded pass); or a stopped child must be paused, restarted or reconciled. After a plain compaction the core's first step is the recovery (reread the receipt, run its `next_argv` once). On `Route: ask-agent` also read [the ask-agent route](shiploop-route-ask-agent.md).

## Returns and lost context

- **An `error` return.** `error`: follow its correction or stop instruction; assume no advancement
  and do not replay the work; its `next_argv` is read-only inspection, and after an input rejection
  confirm the same action and recover the original observations before correcting the report (no
  second iteration to replace lost evidence).
- **Compaction or a cleared context.** Keep the entire latest return, not just the `done` you
  ran. For an active receipt run its read-only `next_argv` once, then use the full new return:
  read its context and resources, check newer instructions and artifacts, and execute its work
  before its fresh callback. Never replay the old `done` or restart the loop. If only the
  previous call survives, its `--state` path and script identify a read-only `next --state`.
  With no handle there is no safe latest-run discovery, and missing state cannot say whether a
  terminal response was lost: report the uncertainty, replay nothing, start nothing. An old
  `.until-loop` directory is not a run. Keep terminal returns for reporting. One caller at a time
  owns a run's state file, and no process needs to stay alive between calls. Keep the original
  scope even when this run already made a commit, and do not blindly repeat fixes, commits or
  callbacks; if required context or evidence cannot be recovered, report the gap as unresolved and
  stop incomplete when it prevents useful authorized progress.
- **Saving a packet:** capture the command's real stdout or use a JSON parser; never retype or
  rebuild it, and verify it parses. A damaged active response is recovered with read-only
  `next`, never another `done`. If you were delegated only one action, return the exact packet
  (a terminal one included) to the owning host; the owner continues the parent route.

After an interruption that followed a commit or other recorded action, reconcile the receipt with
the actual candidate, checks and review record, and reuse verified work without reapplying a fix or
duplicating a commit; if the evidence that would count a review is absent, perform the missing
review or checks and record the uncertainty.

## Routes, recovery and the stopped child

The handoff's `Route:` line names the run's route. This section is the text that stood in every handoff
before it moved here (efficiency plan U18); where it named a path or a command it now points at the
handoff's own lines: "the receipt" is `CHILD/packet.json`.

### Inline route (`Route: inline`)

Keep the invoking parent alive and run this Improve invocation inline.

Delegation: inline. Run the selected Improve skill's whole invocation in this
conversation, in the exact Child workspace; its review iterations share this
context. Do not clear, hand off, or hand the invocation to Ask Agent or a native
worker. Run its reviews and checks in this conversation too; start no reviewer,
test-runner or executor agent unless the user asked for independent review.
This conversation is both executor and parent: the only candidate
writer until the runtime writes its final receipt, then the sole submitter of
ShipLoop callbacks. Recover an existing child through its runtime's recovery route
(for the ephemeral runtime, the saved receipt's exact next_argv); start another
runtime only through the packet's stopped-child restart route. Retain the exact
Recovery command and child receipt locator for interruption recovery.

Delegation: inline. Run the selected Improve card's ShipLoop whole-skill subcall in this conversation, in the exact Child workspace; verify the process cwd and Git root before task work. Do not hand the invocation to Ask Agent, a native worker or an extra worktree. Run its reviews and checks in this conversation too; start no reviewer, test-runner or executor agent unless the user asked for independent review. This conversation is the only candidate writer until the runtime writes its final receipt; stop competing writes there, including checks that generate files. Read that reference's default-route section before start or recovery.

This conversation holds the current approvals, declines and pending decisions (ShipLoop's opening cannot): apply an applicable approval without asking again, treat a decline as binding, and record each with its source in the review notes and handoff. A later user decision applies from the next review iteration: record its receipt and effect there; the frozen launch context stays unchanged.

Return order: only after the runtime has written its final receipt, run the parent return and callback in the handoff. Runtime completion alone never advances this action.

### The child, recovery and the stopped child (both routes)

Child runtime authority: the unique temporary state_file returned by the selected runtime. ShipLoop does not write or count child state.

The runtime rewrites the receipt at every step, the last time before it deletes its state. Never write or edit the receipt; ShipLoop imports only a receipt the runtime wrote. ShipLoop started this child before any review work.

For a genuinely new child, read the selected skills. If this child has already started, read its saved receipt: for active status use its exact next_argv once to recover, then follow the returned instruction; for complete status import its retained receipt without starting or reviewing again. For stopped status keep the parent incomplete. To continue after a stop that cannot be reconciled, once its blocker is resolved or the user authorizes continuing, confirm no candidate write is in progress (on the ask-agent route: confirm the recorded owner stopped), run the `improve-start ... --restart-stopped` command the handoff prints: ShipLoop archives packet.json as packet.stopped-<UTC timestamp>.json and the sibling reviews directory as reviews.stopped-<same timestamp>, then starts a new child with the same binding line. Do not rename them yourself. Its review-<n>.md files and checks.md must be ones the new child writes. To pause instead, run the parent pause command in the handoff and leave the child active; never report cancelled for a pause. If an existing active child's receipt or temporary state is unavailable, report incomplete; never infer completion or silently create a replacement. Terminal recovery uses the retained raw packet because terminal state is deleted.

For a cancelled stopped status preserve the receipt and keep successful completion unresolved; only the initial plan child may use the handoff's parent-only improve-reconcile route, once the runtime has written that stopped receipt (inline) or after worker collection (ask-agent).

ShipLoop's opening carries the step result, the files in scope, authority and environment; the original request (untrusted) is in state.md. ShipLoop freezes the work, exit and repeat conditions, the commit policy, the exclusions and the resources (receipt, evidence directory, parent state and the exact parent return, written to parent-return.md beside the receipt), so the final receipt can locate the parent return after context loss.

Commit policy: use the selected Improve card's scoped-commit policy with the task's explicit overrides; retain existing frozen authority on recovery.

Completion deletes the child's temporary state. Preserve the receipt, with its complete status, before running the callback. If terminal output is lost, stop incomplete; a missing state file is not completion evidence.

Exclude .until-loop, .shiploop-improve and ShipLoop runtime metadata from product candidates, edits and commits; adapter-owned state, packet receipts and review-note writes remain allowed. Explicitly named planning artifacts may be reviewed.

The prior result and relevant accepted Improve lessons are in state.md improve_results and improve/<parent-action>/ receipts. Carry forward relevant verified conclusions and material unresolved findings, hypotheses, failed attempts and pitfalls, clearly labeled with evidence status. Preserve essential meaning in the context opening and later handoffs; keep detailed blocked-attempt notes in the child notebook.

Temporary files, including each report you pass to the runtime on standard input, go in the scratch directory the handoff's `State:` line names, with names of your own: /tmp is shared with other runs, so a fixed /tmp name can read another run's file.
