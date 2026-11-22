# Three questions to the requester

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
The requester will answer three short questions, once, before the plan is made. Choose them, one of each kind.

Read the specification and, as far as you need, the product. A point the files here can settle is not a question
for the requester: settle it by reading. A point may be one the specification marks `Open:`, or one it decided or
passed over without a mark.

1. **Cost.** The point where a build that took the other answer would cost the most to change after delivery, or
   would do harm before anyone noticed.
2. **Ordinary use.** The choice that most changes what the people who use or run the product do or see in their
   ordinary work: a step someone has to take, something that is allowed or refused, something shown every time.
   Rare failures belong to the first question, not here.
3. **Disagreement.** A place where what already exists does not agree with itself or with the request: the
   product's documents say one thing and its code does another, or the request's words fit two different
   behaviours of the product. Write `none` if you find none.

Write `ratchet/question.md` in exactly this form:

## Cost
Question: <one question the requester can answer without reading code or the specification: the concrete
alternatives, and what each one changes for the people who use or run the product>
Clause: <the id of the clause it bears on, or `none`>
If no answer comes: <the alternative the build should take, and why>

## Ordinary use
Question: <as above>
Clause: <as above>
If no answer comes: <as above>

## Disagreement
Question: <as above, or `none`>
Clause: <as above>
If no answer comes: <as above>

## Done when
- `ratchet/question.md` exists in that form and is the only file you changed.

[[CONDUCT]]
