# Specify: the request, ground out until nothing is left implicit

This stage turns the incoming request into the specification that everything after it is planned, built and tested
from. Write no product code and no tests.

A short request is not a small job. Almost everything that decides whether the built thing is right is absent from
the words you were given: it is implied by them, and it stays implied until someone writes it down. Your work is to
keep grinding over this request until what was implied is stated, and a pass over the whole specification turns up
nothing a builder would otherwise have got wrong.

## The incoming request
{request}

## The deliverable

`spec.md`, in exactly this form, use cases first:

## Use cases

### U-<n>: <who> <does what, to get what>
Flow: <the steps they take and what they see, with the exact values where the request gives them>
Source: <request | implied: <by which sentence or situation>>

## Clauses

### C-<n>: <one statement of one behaviour, complete in itself>
Observable: <what someone outside the code does and sees when it holds, with the exact values>
Source: <request | implied: <by which use case or sentence> | choice: <why, where the request is silent>>

Number use cases U-1, U-2, ... and clauses C-1, C-2, ... with no gaps. One behaviour a clause: a statement joined by
"and" is two clauses. The specification says what is true for a user or a caller, not how it is built: a structure, a
library or a technology choice is not a clause. Where the runtime this runs on makes a rule that binds the
behaviour, the clause states the behaviour the rule forces and names the rule as its reason.

Where the request is silent and a builder would have to guess, decide and say so (Source: choice). A choice is the
loosest requirement that still serves the user: fix what a user relies on, and never fix a spelling, a wording, a
format, an order or an internal detail the request leaves open. A choice lives in its own clause, and an Observable
states only what its own clause requires. Another correct product, built by someone who read only the request, must
be able to pass every clause that is not a choice.

## How to get there

Work in passes. Write `spec.md` after the first pass and grow it in place in every pass after; keep `passes.md`
beside it, one short section per pass, saying what that pass added and what it found nothing on.

**Pass 1 — the ground.** Who meets this, and every way they meet it: the ordinary use the request describes, the
same use at its edges (the first time, the repeated time, the empty case, the largest case), the unhappy paths
(wrong input, a refused action, a limit reached, a thing it depends on failing), the operator's work (start, stop,
configure, observe, recover, carry on with data that already exists, go back to the version before). Write the use
cases, then the clause each one plainly needs.

**Pass 2 — what each sentence takes for granted.** Take the request one sentence at a time, and then each clause you
have written one at a time, and ask of it: what must already be true for this to mean anything? A sentence that
names a thing takes for granted that the thing exists, that it is found somehow, that someone is allowed to see it,
that there is one of it rather than none or many. Every answer is a clause. This is the recursion: your own new
clauses are sentences too, so put them through the same question, and keep going down each line until the answers
stop being about this product and become facts about the world.

**Pass 3 — where the parts meet.** List the parts: each use case, each piece of state, each outside system, each
existing feature this touches. Walk the pairs that can meet and ask what happens when they do — two of them at once,
one during the other, one undone while the other runs, one arriving late, one arriving twice. Order, timing,
duplication and partial completion live here. Each answer is a clause. Interactions nobody wrote down are where
built things break.

**Pass 4 — the runtime's own rules.** Name the runtime, platform or service this sits on and the limits it imposes
that this design cannot escape: what it forbids, what it caps, what it times out, what it will not do
synchronously, what it requires before it will run at all, and what it demands before this could ship beyond a
development environment. State each as the behaviour the rule forces, with its number where the rule has one. If
you are unsure of a limit, write the clause and say in it that the exact figure is unconfirmed.

**Pass 5 — what must not change, and what must never happen.** The behaviour that exists today and still has to
hold: one clause each. Then the things that must never be true however the rest is built — someone seeing what they
may not see, a thing done twice that should happen once, data lost on the way, a rule enforced in one path and not
another.

**Pass 6 and on — grind.** Read the whole specification from the top as someone who has to build it and will be
blamed for what is wrong. Look for: a clause whose Observable cannot actually be observed; a word in a clause that
two readers would read differently; a number the request implies but nobody has written; a use case with no unhappy
path; a piece of state with no end; a decision made silently rather than as a choice; a clause that is really two.
Fix and add. Then do it again.

**When to stop.** Stop when one whole pass over the specification adds nothing a builder would otherwise have got
wrong. Not before: a pass that only tidies wording is not that pass. Say in `passes.md` which pass that was and
what you looked for in it. If instead you reach a point where the next answer needs someone to decide something only
the requester can decide, write the clause as a choice with your decision and its reason, and carry on.

## Done when
- `spec.md` exists in that form in your working directory, and `passes.md` records the passes.
- Those are the only two files you wrote.
