# One look at a delivered product

This folder ({work}) holds a product that was built and delivered for the request below. Every check passes. Its
builders' specification and working notes are in `docs/shiploop/`.

This look asks one question: now that the product runs, is there anything a user or an operator needs that it does
not do, or that it does without anyone having been told?

## The request
Build a small shared-expenses service in Node.js (no npm dependencies). server.js listens on the port in the PORT environment variable and keeps its data in the JSON file named by the DATA_FILE environment variable, so groups and expenses survive a restart. POST /groups with {"id": "<group id>", "members": ["<name>", ...]} creates a group: 201, 409 if the id exists, and 400 unless members holds at least two distinct non-empty names. POST /groups/<id>/expenses records an expense paid by one member. {"payer": "<name>", "cents": <positive integer>, "split": "equal"} shares it equally among all members, with any cents left over after an even division going one each to the members listed first. {"payer": "<name>", "cents": <positive integer>, "split": "exact", "shares": {"<name>": <cents>, ...}} makes each member listed in shares owe that many whole cents (zero is allowed), and the shares must add up to cents. It answers 201 with {"expense": <n>}, where n is 1 for the group's first expense, then 2, and so on; 400 for an unknown payer or member, a non-positive or non-integer amount, an unknown split, or shares that do not add up. GET /groups/<id>/balances returns an object with each member's net cents, what they paid minus what they owe, so the balances add up to 0. GET /groups/<id>/settlements returns a JSON array of {"from", "to", "cents"} payments that bring every balance to 0: repeatedly the member who owes most pays the member who is owed most the smaller of the two amounts, and ties go to the member listed first. Every route under /groups/<id> answers 404 for an unknown group. Concurrent requests must never lose an expense. Cover the behaviour with node:test tests under test/ that run with `node --test`.

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
