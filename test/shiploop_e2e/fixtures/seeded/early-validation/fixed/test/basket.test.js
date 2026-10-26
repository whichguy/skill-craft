'use strict';
const test = require('node:test');
const assert = require('node:assert');
const { Basket } = require('../src/basket');
test('add counts the items', () => assert.strictEqual(new Basket({ limit: 2 }).add('a'), 1));
test('add refuses a full basket', () => {
  const b = new Basket({ limit: 1 });
  b.add('a');
  assert.throws(() => b.add('b'), RangeError);
});
test('a bad limit is refused', () => {
  for (const limit of [0, -1, 1.5, '2', undefined]) assert.throws(() => new Basket({ limit }), TypeError);
});
