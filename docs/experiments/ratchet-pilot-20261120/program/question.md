# One question to the requester

You are one step of a loop that a script runs. Another session has written a specification for the change request
below, and the next session will plan the build from it. A different session does each step and knows only what the
files say. Write no product code, no tests and no plan.

## The request
[[REQUEST]]

## What is here
The existing product, as it was before the change, and `ratchet/spec.md`, the specification. A clause of it may carry
an `Open:` line: a point the request does not settle, with who would settle it. When nobody answers an open point,
the plan takes a reasonable answer and the build follows it.

## Your work
The requester will answer one question, once, before the plan is made. Choose it.

Read the specification and, as far as you need, the product. Then choose the one point where the requester's answer
matters most: where a build that took the other answer would cost the most to change after delivery, or would do
harm before anyone noticed. A point the files here can settle is not a question for the requester: settle it by
reading. The point may be one the specification marks `Open:`, or one it decided or passed over without a mark.

Write `ratchet/question.md` in exactly this form:

Question: <one question the requester can answer without reading code or the specification: the concrete
alternatives, and what each one changes for the people who use or run the product>
Clause: <the id of the clause it bears on, or `none`>
Why this one: <what a wrong guess would cost, in a sentence or two>
If no answer comes: <the alternative the build should take, and why>
Next: <the second most important point, in one line>
Next: <the third, in one line>

## Done when
- `ratchet/question.md` exists in that form and is the only file you changed.

[[CONDUCT]]
