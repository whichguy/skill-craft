'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const { paginate } = require('../src/paginate');

test('paginate returns the requested page of an evenly divided list', () => {
  const items = [1, 2, 3, 4, 5, 6];
  assert.deepEqual(paginate(items, 1, 3), { page: 1, pages: 2, items: [1, 2, 3] });
  assert.deepEqual(paginate(items, 2, 3), { page: 2, pages: 2, items: [4, 5, 6] });
});

test('paginate rejects a bad page size', () => {
  assert.throws(() => paginate([1], 1, 0), RangeError);
});

test('TC-1 returns trailing partial page', () => {
  assert.deepEqual(paginate([1, 2, 3, 4, 5], 3, 2), { page: 3, pages: 3, items: [5] });
});

test('TC-1 (a) returns empty slice on empty list', () => {
  assert.deepEqual(paginate([], 1, 5), { page: 1, pages: 0, items: [] });
});
