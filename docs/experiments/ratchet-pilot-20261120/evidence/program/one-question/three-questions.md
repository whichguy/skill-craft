# Part D2b: the nine files of three questions, word for word

## k1 (the specification of d-limit-1; 34.2 seconds)

## Cost
Question: When an operator assigns a ticket to `dana`, should they enter an identifier the mail relay already accepts, or should the service let them enter a name that administrators map to a mailbox before it can be used?
Clause: C-19
If no answer comes: Use the assignee name as the relay's recipient identifier, following the existing requester notices. Operators must use names the relay can route. The service has no agent directory or basis for guessing mailbox addresses.

### Ordinary use
Question: Should `Dana` and `dana` count as the same agent, so either spelling finds the same tickets and changing only the capitalization sends no new notice, or should operators use the same capitalization when assigning and searching because those spellings can name different agents?
Clause: C-3
If no answer comes: Match names case-sensitively after trimming surrounding whitespace, using the same comparison for assignment and filtering. This follows the service's text-input convention and avoids merging distinct agent identifiers.

### Disagreement
Question: The API guide says that filtering for open and urgent tickets returns only tickets that are both, but the service currently includes any open ticket or any urgent ticket. Should existing searches keep those broader results for compatibility, or should they require both matches, as the guide and the assignment request say?
Clause: C-30
If no answer comes: Require every supplied filter to match, including when a search uses only status and priority, because both the guide and the request specify that behavior.

## k2 (the specification of d-limit-2; 36.9 seconds)

## Cost
Question: When a dispatcher assigns a ticket to “Dana Lee,” can the mail relay route the notice from that name as entered, or must the service look up a verified mail address in a roster that operators maintain? Without the right routing, the intended agent can miss the notice or someone else can receive it.
Clause: C-26
If no answer comes: Pass the supplied agent name unchanged to the existing mail relay. This preserves the name-based assignment interface and avoids guessing an address. Delivery to the agent depends on the relay recognizing that name.

### Ordinary use
Question: When a ticket is resolved, should it keep its assignee through closure or reopening so agents still see it under their name, or should resolution clear the assignee so a reopened ticket returns to the unassigned queue for a dispatcher to assign?
Clause: C-21
If no answer comes: Keep the assignee through resolution, closure, and reopening. Dispatchers can still clear or change it once the ticket is open, and reopening requires no extra assignment step when the same agent continues the work.

### Disagreement
Question: The API guide says a list filtered for open and urgent tickets shows only tickets that are both, but the service today also shows tickets that meet just one condition. Should existing dashboards get the documented narrower results as soon as assignment ships, or should calls that use only status and priority keep today's broader results until those dashboards can adapt?
Clause: C-35
If no answer comes: Require every supplied filter to match on the API, even when no assignee filter is supplied. This follows both the request and the API guide. Keep the command-line listing's existing filter behavior.

## k3 (the specification of d-limit-3; 43.3 seconds)

## Cost
Question: Should dispatchers enter a unique name the mail relay can already deliver to, or should they enter a display name such as `Dana Lee` that operators map to a separate delivery address?
Clause: C-28
If no answer comes: Pass the assignee name to the existing relay as the recipient. This keeps address resolution with the relay and avoids guessing an address that could send ticket details to the wrong person.

### Ordinary use
Question: Should `Dana Lee` and `dana lee` count as the same assignee, so either spelling finds the same tickets and assigning again with different capitalization leaves the ticket alone, or should dispatchers have to match capitalization exactly?
Clause: C-6
If no answer comes: Match capitalization exactly for assignment and filtering. This preserves the spelling entered by the dispatcher and keeps names that differ only by case distinct.

### Disagreement
Question: The API guide says combined filters must all match, but today both the API and the command line accept either match. When the API is corrected, should `tickets list --status open --priority urgent` also show only open urgent tickets, or should it keep showing every open ticket plus every urgent ticket?
Clause: C-38
If no answer comes: Keep the command line's current results when both options are given. The request explicitly requires all filters to match for the API and asks the command-line listing to show the assignee.

## k4 (the specification of d-states-1; 41.7 seconds)

## Cost
Question: When a dispatcher assigns a ticket to Dana, should the mail relay receive `Dana` and resolve the name, or should the ticket service look up Dana's delivery address before handing off the notice? This determines where operators maintain the address mapping.
Clause: C-19
If no answer comes: Pass the assignee name to the existing mail relay as the recipient. This follows the current notification handoff. Inbox delivery depends on the relay recognizing the name.

### Ordinary use
Question: Should `Dana` and `dana` count as the same agent, so either spelling finds the same tickets and changing only capitalization sends no new notice, or as distinct agents with separate ticket lists and assignment notices?
Clause: C-28
If no answer comes: Match case exactly for assignments and searches. This follows the existing exact-match filter convention and avoids merging names that may refer to different agents.

### Disagreement
Question: The API guide says a search for open and urgent tickets requires both, but today's service returns tickets that are open or urgent. Should existing searches narrow to tickets that meet both criteria, or keep the broader results when no assignee filter is used?
Clause: C-31
If no answer comes: Require every supplied filter to match, including in existing searches by status and priority, because both the request and the API guide specify that rule.

## k5 (the specification of d-states-2; 51.3 seconds)

## Cost
Question: Should dispatchers be able to assign any valid name, such as Dana, and rely on the mail relay to deliver to that name, or should they be limited to names the service can look up in an agent directory so every accepted assignment has a delivery address?
Clause: C-23
If no answer comes: Send the assignee name to the existing relay as the recipient, as specified. This preserves assignment by name and leaves delivery routing with the relay.

### Ordinary use
Question: When someone filters the queue for dana, should they see tickets assigned to Dana as well, making searches more forgiving, or should the spelling and capitalization have to match so the two names can be searched separately?
Clause: C-29
If no answer comes: Match the saved name exactly, including capitalization, so each filter selects a single assignee spelling consistently with the existing filters.

### Disagreement
Question: A search for open, urgent tickets currently shows tickets that are open or urgent, while the API guide and the assignment request say every filter must match. Should existing status-and-priority searches switch to showing only tickets that are both open and urgent, or should those searches keep their current broader results?
Clause: C-32
If no answer comes: Require every supplied filter to match, including when a search uses only status and priority, because both the request and the API guide specify that behavior.

## k6 (the specification of d-states-3; 39.4 seconds)

## Cost
Question: When a dispatcher assigns a ticket to `Dana`, should the mail relay receive `Dana` as the recipient and handle routing, or should operators maintain a name-to-address list so the service can send to a known address and refuse assignments to unknown names?
Clause: C-15
If no answer comes: Pass the accepted agent name to the existing mail relay as the recipient. The request allows plain names, and this keeps routing with the relay without requiring operators to maintain a new list.

### Ordinary use
Question: Should ` Dana ` and `Dana` count as the same agent when dispatchers assign tickets and queue viewers filter them, or should spaces at either end be kept so the two inputs select different queues?
Clause: C-4
If no answer comes: Trim leading and trailing whitespace before storing or matching names and reject whitespace-only names. This follows the service's existing text-entry convention and keeps accidental spaces from splitting an agent's queue. A literally empty `assignee=` still selects unassigned tickets.

### Disagreement
Question: Today, asking for open and urgent tickets also shows open tickets that aren’t urgent and urgent tickets that aren’t open, even though the API docs promise only open urgent tickets. Should existing searches switch to requiring both conditions, or should they keep today’s results when no assignee filter is supplied?
Clause: C-26
If no answer comes: Require every supplied filter to match, including on searches without an assignee filter. Both the request and the API docs say every filter must match.

## k7 (the specification of d-due-1; 39.4 seconds)

## Cost
Question: After a rollback to 1.4.0 rewrites the ticket file, should operators be able to restore every previously assigned deadline when they turn due times back on, or may they assign fresh deadlines using the response hours in effect at that point, which can change what was promised?
Clause: C-29
If no answer comes: Preserve and recover the original deadlines. A routine save in 1.4.0 drops the new deadline field, and recalculating can silently change a deadline an agent or requester has already seen.

### Ordinary use
Question: Should operators see deadlines in the usual command-line `list` table and `show` details as well as in the API, or should they look up deadlines through the API?
Clause: C-6
If no answer comes: Show deadlines in the API only. The request specifies the `due` field for tickets and leaves room to preserve the familiar command-line displays.

### Disagreement
Question: When an agent asks for overdue tickets with status `open` and priority `urgent`, should they see only tickets that meet both filters, as the API guide says, or all overdue tickets that are open or urgent, as the current service combines those filters?
Clause: C-13
If no answer comes: Require both matches when overdue filtering is active so the results follow the API guide and agents can narrow the overdue queue. Keep the current behavior for existing listings.

## k8 (the specification of d-due-2; 32.5 seconds)

## Cost
Question: If you roll back to 1.4.0 and it saves the ticket file, must the next upgrade restore the exact deadlines people were already promised, or may it calculate replacement deadlines from each ticket's saved priority and the hours in effect at that upgrade?
Clause: C-25
If no answer comes: Restore the exact deadlines already assigned. Otherwise, a rollback could silently move a promised deadline when a ticket's priority or the response hours have changed.

### Ordinary use
Question: Once due times are enabled, should operators see the deadline in both the command-line list and the single-ticket view, or should they look it up through the API?
Clause: C-29
If no answer comes: Show the deadline in both human-readable command-line views once due times are enabled. Operators can scan deadlines in the list and check one while reviewing a ticket.

### Disagreement
Question: The API guide says status and priority must both match, but today's list accepts either match. When someone asks for overdue, open, urgent tickets, should they see only overdue tickets that are both open and urgent, or also overdue open tickets of other priorities and overdue urgent tickets that are in progress?
Clause: C-12
If no answer comes: Require both status and priority to match on overdue requests, so the result follows the API guide and gives agents the queue they asked for.

## k9 (the specification of d-due-3; 34.3 seconds)

## Cost
Question: If operators roll back to 1.4.0 and later upgrade again, must tickets keep their original deadlines even after 1.4.0 saves the file, or may the upgrade assign new deadlines using each ticket’s creation time, its priority at re-upgrade, and the response hours then in effect? Reassigning can change a deadline the help desk already promised. Even a clean shutdown of 1.4.0 saves the file and drops fields it does not recognize.
Clause: C-30
If no answer comes: Preserve deadlines already assigned before rollback. The set-once promise still matters when agents return to the new release, and recalculating could silently move a ticket into or out of the overdue queue.

### Ordinary use
Question: Once due times are enabled, should operators see the deadline in the command-line ticket list and detail view as well as in the API, or should they use the API to check a deadline? Showing it in both views lets operators check deadlines without leaving the tool they already use.
Clause: C-31
If no answer comes: Show the deadline in the human-readable list and detail views when due times are enabled, so operators can see it wherever they normally look up a ticket. Keep the weekly report’s four-column raw output intact.

### Disagreement
Question: When an agent asks for overdue tickets with status open and priority urgent, should the list show only tickets that are both open and urgent, as the API guide describes for combined filters, or show overdue tickets that are open or urgent, as the running service combines those filters today? The second choice also includes overdue open tickets of other priorities and overdue urgent tickets already in progress.
Clause: C-12
If no answer comes: Require both filters on overdue searches, so the new queue follows the documented meaning and agents see the group they asked for. Keep the current matching behavior on existing searches that omit the overdue filter.
