'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const { mean } = require('../src/mean');

test('mean averages numbers', () => {
  assert.equal(mean([2, 4]), 3);
  assert.equal(mean([5]), 5);
});

test('mean rejects a non-array', () => {
  assert.throws(() => mean('12'), TypeError);
});
