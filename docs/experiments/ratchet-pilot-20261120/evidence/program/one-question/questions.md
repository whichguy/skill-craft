# Part D2: the nine questions, word for word

## g1 (the specification of d-limit-1; 39.4 seconds)

Question: Should callers enter a name like `dana` and rely on the existing mail relay to route that name, or should operators maintain a list mapping agent names to verified inboxes, with callers unable to assign tickets to names missing from the list?
Clause: C-19
Why this one: The service can record a notice as sent as soon as it hands it to the relay, so a wrong routing assumption could silently leave tickets unattended or disclose ticket IDs to the wrong people. Correcting it after launch could require reconciling saved assignments and resending notices.
If no answer comes: Pass the stored agent name directly to the existing relay as the recipient. The service already forwards recipient strings as supplied, and this preserves name-based assignment without guessing an email address or requiring operators to maintain a new list.
Next: C-3 — Decide whether spelling variants such as `Dana` and `dana` identify the same agent, since that affects saved assignments, filters and repeat notices.
Next: C-19 — Decide whether Dana gets one notice or two when a ticket goes from Dana to Sam and back to Dana before the first notice is sent.

## g2 (the specification of d-limit-2; 44.2 seconds)

Question: When a dispatcher assigns a ticket to a name like “Dana Lee,” should the mail relay receive that name and look up the recipient, or should the ticket service look up Dana’s email address in an agent directory maintained by help-desk operators and give the relay the address?
Clause: C-26
Why this one: The service marks a notice sent as soon as it writes it for the relay. A wrong guess about how the relay addresses mail could leave agents unaware of new work or send ticket information to the wrong person while operators see a successful handoff.
If no answer comes: Pass the assigned name unchanged to the existing relay and document that the relay must resolve it to the intended agent. The service already hands off recipients as supplied, and the request provides no agent directory or address rule.
Next: Decide whether a reopened ticket returns to its previous agent or enters the unassigned queue for dispatch.
Next: Decide whether “Dana Lee” and “dana lee” identify the same agent for repeat assignments and filtering.

## g3 (the specification of d-limit-3; 26.1 seconds)

Question: When a dispatcher assigns a ticket to “Dana Lee,” should the mail relay look up Dana’s email address from that name, or should the ticket service look up the address from an agent directory that help-desk operators maintain and hand the relay the address?
Clause: C-28
Why this one: The service records a notice as sent when it hands it to the relay. If the two systems disagree about how to address the notice, agents could miss assignments or someone else could receive ticket details while the service reports successful delivery.
If no answer comes: Pass the agent name to the existing mail relay as the recipient and leave address lookup with the relay, since the ticket service already hands off delivery there and has no agent directory.
Next: Decide whether “Dana Lee” and “dana lee” name the same agent, since that choice affects saved assignments, filters, and whether a repeat assignment sends another notice.
Next: Decide whether to deliver a queued notice after the ticket has been reassigned or cleared, since a delayed notice can send an agent to a ticket they no longer own.

## g4 (the specification of d-states-1; 30.3 seconds)

Question: When a dispatcher assigns a ticket to “Dana,” should the ticket service hand the name to the mail relay for the relay to look up, or should the ticket service look up Dana’s verified delivery address before handing off the notice, with help-desk operators responsible for keeping that lookup up to date?
Clause: C-19
Why this one: The service can mark a notice as sent as soon as it hands it off. A wrong guess about who resolves the name could leave tickets unattended or disclose ticket identifiers to the wrong person while operators see a successful send.
If no answer comes: Pass the assignee name to the existing mail relay and leave address lookup with the relay operator. This preserves name-only assignment and avoids guessing anyone’s address.
Next: C-18 — If a ticket changes hands before a notice goes out, should the previous assignee still receive it, or should only the current assignee receive one notice?
Next: C-28 — Should “Dana” and “dana” identify the same agent for filtering and repeat assignments, and should visually identical Unicode spellings also match?

## g5 (the specification of d-states-2; 41.1 seconds)

Question: If a dispatcher assigns a ticket to Dana, should the service send “Dana” to the existing mail relay as the recipient and rely on the relay to find Dana, or should operators maintain a name-to-email mapping that the service uses to address the notice while tickets still show “Dana”?
Clause: C-23
Why this one: The service can record a notice as sent as soon as it hands it to the relay, so a bad recipient assumption could quietly leave agents unaware of their tickets or send ticket details to the wrong person. Fixing that after launch could require reconciling saved assignee names and resending missed notices.
If no answer comes: Pass the assignee name to the existing relay as the recipient, following the service’s current handoff convention and the documented assignment notice format.
Next: Decide whether names such as “Dana” and “dana” identify the same agent for assignment and filtering, since the choice affects saved ownership and which tickets appear in an agent’s queue.
Next: Decide whether to append an assignee column to the script-facing listing or show it only in the operator’s table, since scripts may depend on exactly four columns.

## g6 (the specification of d-states-3; 45.1 seconds)

Question: When a dispatcher assigns a ticket to “Dana,” should the service pass “Dana” directly to the existing mail relay, so dispatchers must enter a name or address the relay recognizes, or should the service look up “Dana” in a help-desk directory, so dispatchers can use registered agent names and operators maintain their delivery addresses separately?
Clause: C-15
Why this one: A ticket can appear assigned while the notice never reaches the agent or goes to the wrong person. Changing how names identify recipients after rollout could require reconciling saved assignments and notices still waiting to go out.
If no answer comes: Pass the stored assignee to the existing mail relay as the recipient, because that is the delivery path the service already uses and there is no agent directory in the product.
Next: C-4 — Decide whether differently capitalized or accented spellings can identify the same agent for assignment and filtering.
Next: C-15 — Decide whether assigning a ticket back to the same agent while their first notice is still waiting sends a second notice or shares the waiting one.

## g7 (the specification of d-due-1; 30.3 seconds)

Question: If the help desk rolls back to 1.4.0 and keeps taking and updating tickets, should agents see exactly the same deadlines for previously assigned tickets when due times return, or may operators recalculate the lost deadlines using each ticket’s then-current priority and response hours, which can change which tickets appear overdue?
Clause: C-29
Why this one: A routine save by 1.4.0, even one that only records a notification delivery, can erase deadlines stored on ticket records. If priorities or response hours have changed, the ticket records alone cannot recover the original promises.
If no answer comes: Preserve and recover previously assigned deadlines across rollback writes, because the request treats each assigned deadline as a fixed promise.
Next: C-18. If response hours change before preparation, should existing tickets receive deadlines based on the original defaults or the hours in effect at preparation?
Next: C-17. Can operators briefly pause ticket writes to prepare the file, or must the help desk keep accepting and updating tickets throughout preparation?

## g8 (the specification of d-due-2; 52.2 seconds)

Question: If you roll back to 1.4.0 and later turn due times back on, must the service recover the exact deadlines users already saw, which requires keeping a record through rollback, or may it recalculate from each ticket's creation time, saved priority and the response hours in effect at reactivation, which could give users earlier or later deadlines?
Clause: C-25
Why this one: A routine save by 1.4.0 drops the added due field, even if nobody edits the ticket. If response hours or priorities have changed, recalculation can silently change which tickets agents see as overdue, and the original promises may be impossible to reconstruct.
If no answer comes: Preserve previously assigned deadlines across rollback and reactivation, because the help desk has already made those promises and the request says each due time is set once.
Next: C-16. Can agents pause ticket writes for a maintenance window while operators prepare the file, or must writes stay available throughout preparation? When should tickets accepted before activation first lock in their deadlines?
Next: C-12. When an agent filters overdue tickets by both status and priority, should tickets match both selections as documented, or either selection as in today's ordinary list?

## g9 (the specification of d-due-3; 28.7 seconds)

Question: If operators roll back to version 1.4.0, it saves the ticket file, and they later upgrade again, must agents see the exact same deadlines as before the rollback, or may the service recalculate them using each ticket’s current priority and the response hours in effect at re-upgrade, potentially changing which tickets are overdue?
Clause: C-30
Why this one: Version 1.4.0 drops unfamiliar ticket fields on its first save, even during a routine shutdown. If a ticket’s priority or the response hours have changed since its deadline was assigned, recalculating can silently move a promised deadline, and the original value may be impossible to recover.
If no answer comes: Preserve every assigned deadline through a rollback and later re-upgrade, because the request says a deadline is set once.
Next: C-15 — For tickets created while due times are off, lock in the priority and response hours at creation or use those in effect when deadlines are prepared.
Next: C-16 — If operators enable due times before preparation is complete, refuse startup, prepare before serving, or keep serving the old API responses until preparation succeeds.
