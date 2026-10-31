'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const { paginate } = require('../src/paginate');
const { capitalize } = require('../src/strings');

test(`${capitalize('tc-1')}: the last partial page is returned`, () => {
  assert.deepEqual(paginate([1, 2, 3, 4, 5], 3, 2), { page: 3, pages: 3, items: [5] });
});

test(`${capitalize('tc-2')}: a partial last page counts in pages`, () => {
  assert.deepEqual(paginate([1, 2, 3, 4, 5], 2, 3), { page: 2, pages: 2, items: [4, 5] });
});
