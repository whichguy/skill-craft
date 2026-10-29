'use strict';

const { test } = require('node:test');
const assert = require('node:assert/strict');
const { InvalidError } = require('../src/errors');
const { decodeCursor, encodeCursor, paginate } = require('../src/pagination');

const compare = (a, b) => a - b;
const items = [1, 2, 3, 4, 5].map((id) => ({ id }));
const ids = (page) => page.items.map((item) => item.id);

test('a cursor carries its sort key and nothing a client should build', () => {
  const cursor = encodeCursor('T-0005');
  assert.match(cursor, /^[A-Za-z0-9_-]+$/);
  assert.equal(decodeCursor(cursor), 'T-0005');
});

test('a cursor the service did not issue is invalid', () => {
  for (const text of ['', 'abc', Buffer.from('{"after":"T-0001"}').toString('base64url'), encodeCursor('')]) {
    assert.throws(() => decodeCursor(text), InvalidError, text);
  }
});

test('pages follow one another through their next cursors', () => {
  const first = paginate(items, { limit: 2, compare });
  assert.deepEqual(ids(first), [1, 2]);
  const second = paginate(items, { limit: 2, after: JSON.parse(Buffer.from(first.next, 'base64url')).after, compare });
  assert.deepEqual(ids(second), [3, 4]);
  const third = paginate(items, { limit: 2, after: 4, compare });
  assert.deepEqual(ids(third), [5]);
  assert.equal(third.next, null);
});

test('a page that ends exactly at the last item has no next', () => {
  assert.equal(paginate(items, { limit: 5, compare }).next, null);
  assert.notEqual(paginate(items, { limit: 4, compare }).next, null);
});

test('a page starts after its key even when that item is gone', () => {
  const withoutThree = items.filter((item) => item.id !== 3);
  assert.deepEqual(ids(paginate(withoutThree, { limit: 2, after: 3, compare })), [4, 5]);
  assert.deepEqual(ids(paginate(items, { limit: 2, after: 9, compare })), []);
});

test('the limit must be a positive integer', () => {
  assert.throws(() => paginate(items, { limit: 0, compare }), RangeError);
});
