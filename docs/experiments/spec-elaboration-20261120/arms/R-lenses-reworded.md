# Specify: what the request needs and does not say

This stage turns the incoming request into the specification that everything after it is planned, built and tested
from. Write no product code and no tests.

A short request leaves most of what decides whether the built thing is right unsaid. Your work is to find what the
request needs that it does not say, to state the part of it that follows from the request, and to mark the part
that someone still has to decide. A specification can fail by saying too little and by deciding too much: a clause
nobody asked for is work to build, and a test written from it can reject a product that does what was asked.

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
Open: <only where there is one: what this clause depends on that is not decided, and who or what would settle it>

Number use cases U-1, U-2, ... and clauses C-1, C-2, ... with no gaps. One behaviour a clause: a statement joined by
"and" is two clauses. The specification says what is true for a user or a caller, not how it is built: a structure, a
library or a technology choice is not a clause.

**What earns a clause.** Every sentence of the request. Beyond that, only distinct behaviour that can be checked
and that the requested outcome needs in order to work, or that has to be preserved where the change touches it. Add
no capability, duty or restriction that the request's purpose does not call for: if a builder could leave it out
and still deliver what was asked, with nothing the requester would call missing or broken, it is not a clause.

**What stays open.** Where the request needs something settled and neither the request nor what already exists
settles it, do not settle it by guessing. If a builder cannot proceed without an answer and any reasonable answer
serves the requester equally, make the loosest choice (Source: choice) and fix only what a user relies on, never a
spelling, a wording, a format, an order or an internal detail. If the answer would change what the requester gets,
write the clause at the loosest reading that is certainly wanted and give it an `Open:` line saying what is
undecided and who decides. An open line is a finished piece of work, not a gap in yours. Another correct product,
built by someone who read only the request, must be able to pass every clause that is not a choice.

**Sets and bounds.** Where a clause depends on a set (the states that stop something, the conditions that refuse an
action), name the members or groups that behave differently, and say which you left out where that matters. Where
a clause depends on a bound, state the bound and what happens at it, taking the value from the request, from what
exists, or from the runtime's own documentation. Invent no bound: one that none of those supplies is an `Open:`
line.

## How to get there

Write `spec.md` once. The questions below are aids to thinking, to be used once while you draft; they are not a list
of things to write, and most of what they turn up will confirm a clause you already have or show that nothing is
needed. After drafting, check the draft once against the list at the end, and stop.

**Who is affected.** Identify the people this affects and what each ordinarily gets from it. State a first-use,
repeated, empty, boundary or failure outcome where it is distinct and bears on what was asked. Where running it or
recovering from it is part of what was asked, state how the person who runs it observes it, stops it or recovers
it, using the controls that already exist.

**What an outcome depends on.** For each outcome the request asks for, name a prerequisite only if its absence or
its failure would change that outcome or how it is checked. Follow a prerequisite no further than that.

**Where paths share something.** Check where the changed behaviour shares state, timing or an outside effect with
another affected path. State the required outcome, and the recovery, where two things at once, their order, a
duplicate, a delay or an interruption could change what someone observes.

**What the runtime constrains.** For the environment the request names, and no further, state the runtime's
constraints that affect required behaviour, as the behaviour each one forces. Give the value where the constraint
has one and you have it from documentation or from a probe; where you do not, that is an `Open:` line.

**What is preserved.** Name the accepted behaviour this change touches and has to keep. State the invariants that
apply to it (who may see what, an effect that must happen once, data that must not be lost, a rule that must hold on
every path) as outcomes that can be checked, under the clause they bound.

**The one check before you finish.** A clause whose Observable cannot actually be observed. A word two readers
would read differently. A decision made silently, which belongs in a choice or an `Open:` line. A clause that is
really two. A clause that a builder could leave out with nothing missing, which should go.

## Done when
- `spec.md` exists in that form in your working directory, written once, and is the only file you wrote.
