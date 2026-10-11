const test = require('node:test');
const assert = require('node:assert');
const { isAdult, bucket, spin } = require('../lib.js');
const { sum } = require('../other.js');

test('an adult is 18 or more', () => {
  assert.equal(isAdult(18), true);
  assert.equal(isAdult(17), false);
});
test('a small number is a small bucket and the rest are other', () => {
  assert.equal(bucket(5), 'small');
  assert.equal(bucket(50), 'other');
  assert.equal(bucket(-3), 'other');
});
test('sum adds', () => assert.equal(sum(2, 3), 5));
test('spin is off', () => assert.equal(spin, false));
