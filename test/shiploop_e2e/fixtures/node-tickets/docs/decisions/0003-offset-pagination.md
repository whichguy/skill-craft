# 3. Offset pagination for listings

Date: 2025-01-27
Status: Superseded by [5](0005-cursor-pagination.md)

## Context

`GET /tickets` returned every ticket. After the first month the help desk had over a thousand, and the agents' dashboard
took seconds to load.

## Decision

We will page listings with `offset` and `limit` query parameters, `limit` 50 by default, and answer
`{ "items": [...], "total": <number of matching tickets> }`, so a client can show "page 3 of 21".

## Consequences

- Easy to build: slice the sorted list.
- A ticket created while an agent pages through the list shifts every later page by one, so an item can be shown twice
  or skipped.
- `total` costs a full count on every request.
