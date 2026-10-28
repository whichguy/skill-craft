# 2. Prefixed sequential ticket ids

Date: 2025-01-20
Status: Accepted

## Context

Agents read ticket ids aloud on the phone and type them into chat. The first prototype used UUIDs, which nobody could
say or remember. Plain numbers were confused with asset tags and phone extensions.

## Decision

We will name tickets `T-` followed by a sequence number padded to four digits: `T-0001`, `T-0002`, and so on. Past
`T-9999` the number simply grows (`T-10000`); ids sort by their number, not as text.

Numbers are given out in order and never reused, not even after a restart or a restore: the store keeps the next number
with the tickets, and a saved state whose next number is not above every ticket's number is refused.

## Consequences

- An id says roughly how old a ticket is, and two ids never name the same ticket, even in old emails.
- Ids are not secret and are easy to guess; the API is on the internal network only.
- `src/tickets/ids.js` is the one place that writes and reads the format. Code compares ids with `compareIds`, never as
  strings.
