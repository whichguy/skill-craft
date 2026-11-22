# A second reading of a specification

You are one step of a loop that a script runs. Another session has written a specification for the change request
below, and the next session will plan the build from it. Before that, read the specification once as someone who
did not write it. Write no product code, no tests and no plan, and leave the specification as it is.

## The request
[[REQUEST]]

## What is here
The existing product, as it was before the change, and `ratchet/spec.md`, the specification. Each clause has a
`Source:` line saying where it comes from: the request, something the request implies, a rule of the existing
product, or a choice. A clause may carry an `Open:` line for a point the request does not settle.

## Your work
A specification can fail by deciding too much. A clause nobody asked for is work to build, and a test written
from it can reject a product that does what was asked. Find the clauses that decide too much.

For each clause (C-n), ask two things. Does the request ask for this, in its words or by clear implication? Does
the existing product already do it? Read the product's code, tests and documents to answer the second: a clause
whose source names an existing rule is only right if the product really follows that rule. A clause that passes
neither question decides something on the requester's behalf.

Write `ratchet/reading.md` in exactly this form:

## Decided beyond the request
- <clause id> | <what it requires that the request does not ask and the product does not already do> | <what another correct product, built from the request alone, might do instead>

## Checked against the product
<the ids of the clauses whose claim about existing behaviour you checked in the product's files, in one line>

One line for each entry under the first heading, the most consequential first; `none` when there is none.

## Done when
- `ratchet/reading.md` exists in that form and is the only file you changed.

[[CONDUCT]]
