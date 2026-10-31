'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const { capitalize, truncate } = require('../src/strings');

test('capitalize upper-cases the first character', () => {
  assert.equal(capitalize('hello'), 'Hello');
  assert.throws(() => capitalize(''), TypeError);
});

test('truncate keeps short text and cuts long text with an ellipsis', () => {
  assert.equal(truncate('short', 10), 'short');
  assert.equal(truncate('a long sentence', 6), 'a lon…');
  assert.throws(() => truncate('x', 0), RangeError);
});
