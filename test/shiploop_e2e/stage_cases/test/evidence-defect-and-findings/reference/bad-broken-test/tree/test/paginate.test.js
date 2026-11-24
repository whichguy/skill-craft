'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const { paginate } = require('../src/paginate');

test('TC-1 wrong expected page breaks control', () => {
  assert.deepEqual(paginate([1, 2, 3, 4, 5], 3, 2), { page: 3, pages: 99, items: [5] });
});

test('TC-1 (a) empty list', () => {
  assert.deepEqual(paginate([], 1, 5), { page: 1, pages: 0, items: [] });
});
