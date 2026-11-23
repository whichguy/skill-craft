# 5. Cursor pagination for listings

Date: 2025-05-12
Status: Accepted. Supersedes [3](0003-offset-pagination.md).

## Context

With offset pagination (decision 3), agents paging through open tickets during the morning rush saw tickets twice or
missed them, because new tickets arrive all the time. Nobody used `total` beyond the first page, and computing it was the
slowest part of the listing.

## Decision

We will page every listing with an opaque cursor. A list endpoint answers

```json
{ "items": [ ... ], "next": "<cursor>" }
```

with `next` null on the last page. The client passes `next` back as `cursor`, with the same filters, to get the following
page. `limit` sets the page size: 20 by default, at most 100. The cursor holds the sort key of the last item served (for
tickets, its id) and a format version, base64url-encoded; clients must not build or read it. There is no `total`.

`src/pagination.js` is the one implementation; an endpoint sorts, filters, and then pages with `paginate`.

## Consequences

- A page starts after the last item served, so items added or removed in between never cause a duplicate or a gap.
- Filtering happens before paging: a page holds `limit` matching items, and `next` is null exactly when no matching
  item is left.
- Clients cannot jump to page N or show a total. The dashboard dropped both.
- `?offset=` was removed in 1.2.0, and a request that sends it gets the first page.
