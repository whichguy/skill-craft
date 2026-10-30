'use strict';
// E7 verify (evaluators/e7_tests.py): the stated limits tested at the limit and one past it, and each clause of a
// compound guard failing on its own, so a limit moved by one or a guard's && and || swapped fails a test.
const test = require('node:test');
const assert = require('node:assert');
const { parseOrders } = require('../src/orders');

const line = (qty, price) => `id=1;qty=${qty};price=${price};status=open;shipped_at=`;

test('qty: 1 is accepted, 0 and a fraction are not', () => {
  assert.strictEqual(parseOrders(line(1, 5))[0].qty, 1);
  assert.throws(() => parseOrders(line(0, 5)), RangeError);
  assert.throws(() => parseOrders(line(1.5, 5)), RangeError);
});

test('price: 0 is accepted, -1 and a fraction are not', () => {
  assert.strictEqual(parseOrders(line(1, 0))[0].price, 0);
  assert.throws(() => parseOrders(line(1, -1)), RangeError);
  assert.throws(() => parseOrders(line(1, 1.5)), RangeError);
});
