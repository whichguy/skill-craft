# 7. An append-only audit log

Date: 2025-03-17
Status: Accepted

## Context

In February a ticket's priority was lowered and the ticket then sat for a week; nobody could say who lowered it, or
when. Internal audit asked that every change to a ticket be traceable to a person.

## Decision

We will record every change to a ticket in an audit log that is only ever appended to. An entry holds:

- `seq`, its position in the whole log, from 1;
- `ticket`, `action` (`ticket.created`, `ticket.updated`, `ticket.transitioned`, ...), `at`;
- `actor`, taken from the request's `X-Actor` header, or `system` without one;
- `changes`: for each field the change touched, its value before and after (`{ "from": ..., "to": ... }`).

The store appends the entry in the same step as the change, so there is no change without an entry. A request that
changes nothing (setting a field to the value it has) is not a change and adds no entry. Entries are frozen in memory
and never edited or removed, in memory or in the data file; the data file is refused at start if its log is not
numbered 1, 2, 3, ...

`GET /tickets/:id/audit` returns a ticket's entries, oldest first.

## Consequences

- Every change must go through a `TicketStore` method; code that assigns to a ticket elsewhere bypasses the log, and
  review rejects it.
- The log grows without bound. At our volume that is fine for years (see operations).
- Correcting a mistake is a new change with its own entry, never an edit of an old one.
