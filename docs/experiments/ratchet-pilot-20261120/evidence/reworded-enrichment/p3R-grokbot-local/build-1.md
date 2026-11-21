## Done

- C-1–C-8. Delivered the dependency-free Node entry point, browser assets, and atomic data-folder storage seeded from the unchanged fixtures.
- C-9–C-14. Added the roster chooser, durable per-browser selection, scoped commands and views, and background work anchored to the accepting person and discussion.
- C-15–C-22. Added recoverable local setup, credential persistence and redaction, and direct use of the unchanged stand-in for replies.
- C-23–C-31. Added named bots, the shared create and rename form, and saved discussions with current selection and reopening.
- C-32–C-44. Added the contextual transcript, keyboard composer, pending and failure states, idempotent submission and reply recovery, and provider clarification.
- C-45–C-54. Added person-scoped instruction and task libraries with edit, delete, and application or execution in the open context.
- C-55–C-60. Added bot-scoped memory with individual edits and removal, including provider remember and forget results.
- C-61–C-77. Added readable-record grounding, exact approval previews, durable rejection and confirmation receipts, permission and stale-value checks, and creator-only order creation.
- C-78–C-93. Added server-owned task execution, progress, steering, cancellation, restart recovery, and task activity summaries with discussion links.
- C-94–C-99. Added desktop workspace panels, narrow-screen disclosures, keyboard and focus handling, and a persistent composer.
- C-100. Added 10 `node:test` checks against the modules and running HTTP service. All passed. A WebKit smoke test exercised the desktop interaction flow at 1440 px and checked the chat, disclosures and focus at 360 px.
- Updated the README with startup, setup, workspace use and data recovery instructions.

## Not done

none

## Discoveries

- A valid environment token takes priority; an invalid environment value allows a valid file credential or setup. | Observable: Restart with a mistyped environment value and a saved valid token. | Why: This gives the operator an override and a recovery path.
- Bot names are trimmed and unique without regard to case within a person's workspace. | Observable: Try an empty name or a case variant of an existing bot's name. | Why: Navigation buttons need distinguishable labels.
- Conversation labels come from the first message, with numbered labels for empty discussions and suffixes for collisions. Reentry restores the last bot and its last discussion. | Observable: Start conversations with matching first messages, switch between them and reload. | Why: The first accepted turn was the earliest useful label.
- An interrupted reply waits for Retry. Each discussion accepts one unresolved reply at a time. | Observable: Stop during a slow reply, restart, then retry its original turn or work in another chat. | Why: One outstanding reply preserves turn order and the stand-in's immediately preceding clarification.
- Each person can reuse saved instructions and tasks across their bots. Use copies instruction text to the selected bot, so edits require another Use and library deletion leaves the copied text active. | Observable: Use an instruction, edit or delete the library entry, and ask who the bot is. | Why: Each bot needs its own active instructions.
- Memory facts use trimmed, case-sensitive text for matching. | Observable: Repeat an identical fact or try forgetting a differently capitalized version of it. | Why: The provider supplies literal fact strings and the app avoids guessing equivalent wording.
- Successful confirmation assigns the next free order ID, and the preview lists the new record's fields and sole reader. Multiple approvals can remain pending until decided. | Observable: Make two orders and reload before confirming either one. | Why: There is no need to reserve an ID while reviewing a proposal.
- A stale proposal resolves as Unapplied and the reviewer can request a fresh preview. Supported updates are order status, customer and numeric total, and account name and tier. | Observable: Confirm competing status previews or ask to edit a readers field. | Why: The exact before-value is part of the approval and authorization fields determine access.
- The task most recently started or retried in the discussion receives a steering request if that same run is still eligible when the reply settles. | Observable: Send a delayed steering message while multiple tasks are running or after restarting the target run. | Why: Provider steering supplies a step but no task ID.
- A dispatched task step can settle after cancellation. Terminal status reflects its outcome and can be Completed if the final step finished. | Observable: Cancel between claims and again during a final step. | Why: The stand-in has no abort operation and the result can still be recorded.
- A server restart marks an unfinished live task Interrupted for manual retry, or Cancelled if the stop request had already committed. | Observable: Restart during a running task and inspect the recorded prefix and recovery controls. | Why: Executing steps live in the service process and a claimed step without a saved result has an unknown outcome.
- The return summary uses a per-browser, per-person seen cursor. Running, failed and interrupted work stays visible after acknowledgement. | Observable: Mark activity seen while a task is running, switch people, and return later. | Why: Acknowledging a rendered update avoids guessing absence from browser connection timing.
- The original Stillroom design uses a three-column desktop view and collapsible chat navigation and workspace tools on narrow screens. The layout targets 320 CSS pixels and wider. | Observable: Resize the browser and toggle either secondary panel while the transcript and composer are in view. | Why: The conversation needs its own readable space while secondary controls stay reachable.
- The service uses one writer per data folder and binds to local IPv4 loopback. | Observable: Start with PORT=0 and open the printed address. | Why: The passwordless application is meant for use on this computer and the snapshot uses single-process transactions.
- Credential-shaped text is masked in application output and any proposal with a concealed field is unapprovable. | Observable: Send a token-shaped prompt or propose setting a record field to credential-shaped text. | Why: The stand-in can echo text, and a concealed value prevents exact review.
