'use strict';

const { InvalidError } = require('./errors');

/**
 * Cursor pagination (docs/decisions/0005-cursor-pagination.md, which replaced offset pagination).
 *
 * A page is { items, next }. `next` is an opaque cursor for the page after this one, or null on the last page. The
 * cursor holds the sort key of the last item served, so the next page starts after it even when items were added or
 * removed in between: no item is served twice and none is skipped.
 */

const VERSION = 1;

/** The cursor of a page that ends at sort key `after`. */
function encodeCursor(after) {
  return Buffer.from(JSON.stringify({ v: VERSION, after }), 'utf8').toString('base64url');
}

/** The sort key a cursor holds. Text this service did not issue is an InvalidError. */
function decodeCursor(text) {
  let parsed = null;
  try {
    parsed = JSON.parse(Buffer.from(String(text), 'base64url').toString('utf8'));
  } catch {
    parsed = null;
  }
  if (!parsed || parsed.v !== VERSION || typeof parsed.after !== 'string' || parsed.after === '') {
    throw new InvalidError('cursor is not one this service issued');
  }
  return parsed.after;
}

/**
 * The page of `items` that starts after sort key `after` (null: the first page) and holds at most `limit` items.
 * `items` must be sorted by `keyOf` in the order `compare` defines.
 */
function paginate(items, { limit, after = null, keyOf = (item) => item.id, compare }) {
  if (!Number.isInteger(limit) || limit < 1) throw new RangeError('limit must be a positive integer');
  const start = after === null ? 0 : items.findIndex((item) => compare(keyOf(item), after) > 0);
  const rest = start === -1 ? [] : items.slice(start);
  const page = rest.slice(0, limit);
  const next = rest.length > limit ? encodeCursor(keyOf(page[page.length - 1])) : null;
  return { items: page, next };
}

module.exports = { decodeCursor, encodeCursor, paginate };
