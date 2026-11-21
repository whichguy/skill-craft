# Architecture — invoice reminders

Status: no technology, repository or platform is known for this run (spec P-1). Nothing below is a chosen design; it records the one decision that must be made and what it must satisfy. Requirements live in `spec.md` only.

## Stack
none: language, framework, scheduler and mail transport are undecided (AD-1).

## Structure
none yet. Behaviour to be owned, per `spec.md`: a policy store (R-1, R-9), an invoice reader (R-2, R-4), a scheduled runner with catch-up and claim logic (R-3, R-8), a message composer and transport (R-5, R-6), a record/history store (R-7).

## Conventions
none yet. Constraint from NFR-6: current time and the mail transport must be replaceable in tests.

## Interfaces and boundaries
- Invoicing system (read-only): invoice id, number, due date, balance and currency, status, billing address (spec P-1, unverified).
- Mail transport (outbound): synchronous accept/reject result (spec D-6, G-3).
- Scheduler → runner: at least one invocation per calendar day (spec NFR-1).

## Real-boundary checks
- Delivery through the real mail provider to a real mailbox: not provable by the capturing outbox; owner and due phase to be set once AD-1 is decided.
- Concurrent runs against the real shared store (spec AC-8.2): the store's uniqueness/conditional-write facility must be confirmed from primary documentation, not assumed.

## Decisions
- **AD-1 — Platform, scheduling mechanism, store and mail transport.** Status: **open**. Must provide: a daily (or more frequent) trigger that works without a developer workstation; a store with uniqueness on (invoice, offset) for the claim in R-8; a secret facility for transport credentials (NFR-4); runtime limits that fit NFR-1/NFR-2. Decide after discovery of the invoicing system (P-1). No claim about any platform's capability is made here.

## Superseded
none
