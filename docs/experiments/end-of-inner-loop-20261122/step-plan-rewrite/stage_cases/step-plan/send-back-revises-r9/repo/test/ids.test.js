'use strict';

const { test } = require('node:test');
const assert = require('node:assert/strict');
const { compareIds, formatId, parseId } = require('../src/tickets/ids');

test('formatId pads the number to four digits and grows past them', () => {
  assert.equal(formatId(1), 'T-0001');
  assert.equal(formatId(42), 'T-0042');
  assert.equal(formatId(9999), 'T-9999');
  assert.equal(formatId(10000), 'T-10000');
});

test('formatId refuses a number that is not a positive integer', () => {
  for (const number of [0, -1, 1.5, NaN, '3']) {
    assert.throws(() => formatId(number), RangeError, String(number));
  }
});

test('parseId reads only the one written form of an id', () => {
  assert.equal(parseId('T-0001'), 1);
  assert.equal(parseId('T-10000'), 10000);
  for (const text of ['T-1', 'T-001', 'T-00001', 't-0001', 'T-0000', 'X-0001', 'T-0001 ', '', null, 7]) {
    assert.equal(parseId(text), null, String(text));
  }
});

test('compareIds sorts by number, not as text', () => {
  const ids = ['T-10000', 'T-0002', 'T-9999', 'T-0010'];
  assert.deepEqual(ids.sort(compareIds), ['T-0002', 'T-0010', 'T-9999', 'T-10000']);
});
