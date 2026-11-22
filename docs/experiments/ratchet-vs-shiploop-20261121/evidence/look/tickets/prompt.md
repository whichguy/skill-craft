# One look at a delivered product

This folder ({work}) holds a product that was built and delivered for the request below. Every check passes. Its
builders' specification and working notes are in `docs/shiploop/`.

This look asks one question: now that the product runs, is there anything a user or an operator needs that it does
not do, or that it does without anyone having been told?

## The request
This directory is an existing Node.js service with no npm dependencies (README.md describes it): a help-desk ticket API, src/server.js, which `npm start` runs on the port in the PORT environment variable, with a command-line tool in bin/. Add ticket assignment. `PUT /tickets/:id/assignee` with a JSON body `{"assignee": "<agent>"}` assigns the ticket to that agent, and `{"assignee": null}` unassigns it; an agent is a non-empty name of at most 64 characters. Only open and in-progress tickets can be assigned or unassigned. Assigning a ticket to the agent it already has changes nothing. Every ticket shows its `assignee` (null when unassigned). The agent a ticket is assigned to is notified that it was assigned to them. `GET /tickets` gains an `assignee` filter: `assignee=<agent>` keeps that agent's tickets and an empty `assignee=` keeps the unassigned ones; a ticket must match every filter given. The command-line listing shows each ticket's assignee. Everything the service already does keeps working, and its existing tests must still pass as they are. Add node:test tests under test/ for the new behaviour; `npm test` runs them with the existing ones.

## What to weigh
- The product itself. Start it and use it as its users and operators would: the request's own examples, values at
  and just past each limit, wrong and odd input, the features next to what was asked, a restart, what its documents
  promise. Use it; do not only read it.
- The request, read once more for what it implies and the specification does not state.
- The specification and notes in `docs/shiploop/`, for a choice the builders made that the request did not settle.

## What to write
Write `docs/shiploop/look.md` and change nothing else: not the product, not a test, not another document.

**Shortfalls.** Each thing the product does not do that a user or an operator would care about and the request's
intent covers. For each: what is needed; the exact steps that show the product falling short (the commands or page
actions, what came back, what should have); and how much it matters: `high` (loses data, misleads a user or breaks
what worked), `medium` or `low`. A shortfall is not a new feature, a matter of taste or hardening nobody asked for.
If another correct product could behave differently and nobody would miss it, leave it out. Try what you suspect
before you write it: a shortfall you did not see happen does not belong here.

**Choices the customer was not told.** Each place where the request left something open, the product does
something reasonable there, and neither the request nor the documents delivered with the product (not counting
`docs/shiploop/`) say what it does. One line each: the open point, and what the product does.

Write the single line "Nothing found." under a heading whose list is empty.

## Conduct
Work only inside {work}; temporary files go in {tmp}. Use a free port you pick yourself and data files under
{tmp}. Stop every process you start, by its process id, before you finish; never stop processes by name.
