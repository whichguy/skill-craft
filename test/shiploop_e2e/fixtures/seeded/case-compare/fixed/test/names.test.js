'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const { sortNames } = require('../src/names');

test('sortNames orders plain lower-case names', () => {
  assert.deepEqual(sortNames(['carol', 'alice', 'bob']), ['alice', 'bob', 'carol']);
});

test('sortNames returns a new array and rejects a non-array', () => {
  const names = ['b', 'a'];
  assert.notEqual(sortNames(names), names);
  assert.deepEqual(names, ['b', 'a']);
  assert.throws(() => sortNames('ab'), TypeError);
});
