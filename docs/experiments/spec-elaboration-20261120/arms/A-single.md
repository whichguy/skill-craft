# Specify: the request, made complete

This stage turns the incoming request into the specification that everything after it is planned, built and tested
from. Write no product code and no tests.

## The incoming request
{request}

## What to do
1. Find the use cases: everyone who will meet this, and every way they meet it. The ordinary use the request
   describes. The same use at its edges: the first time, the repeated time, the empty case, the largest case. The
   unhappy paths: wrong input, a refused action, a limit reached. What an operator does: start, restart, configure,
   carry on with the data that exists today, go back to the version before. And where this touches things that
   already exist.
2. Find the implied requirements. For each use case ask what must be true for it to work that the request never
   says, and what the request's own sentences take for granted. Each becomes a clause.
3. Write `spec.md` in exactly this form, use cases first:

## Use cases

### U-<n>: <who> <does what, to get what>
Flow: <the steps they take and what they see, with the exact values where the request gives them>
Source: <request | implied: <by which sentence or situation>>

## Clauses

### C-<n>: <one statement of one behaviour, complete in itself>
Observable: <what someone outside the code does and sees when it holds, with the exact values>
Source: <request | implied: <by which use case or sentence> | choice: <why, where the request is silent>>

The clauses cover every sentence of the request; every implied requirement; every limit, boundary and error case,
with its exact number; every existing rule this must keep (one clause each); and what must not change. Where the
request is silent and a builder would have to guess, decide and say so (Source: choice). Add no feature the
request's intent does not cover.

A choice is the loosest requirement that still serves the user. Fix what a user relies on; never fix a spelling, a
wording, a format, an order or an internal detail that the request leaves open. If the request says an error names
the line, the clause says the message contains the line number, not how the message is worded. A choice lives in its
own clause, and an Observable states only what its own clause requires: it never repeats another clause's choice.
Another correct product, built by someone who read only the request, must be able to pass every clause that is not a
choice. Number use cases U-1, U-2, ... and clauses C-1, C-2, ... with no gaps. One behaviour a clause: a statement
joined by "and" is two clauses.

The specification says what is true for a user or a caller, not how it is built. A structure, a library or a
technology choice is not a clause. Where the runtime this runs on makes a rule that binds the behaviour, the clause
states the behaviour the rule forces, and names the rule as its reason.

## Done when
- `spec.md` exists in that form in your working directory and is the only file you wrote.
