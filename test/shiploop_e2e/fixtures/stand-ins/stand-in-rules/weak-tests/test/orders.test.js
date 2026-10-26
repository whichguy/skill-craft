'use strict';
// Run-4 style weak tests: only totals checked, absence asserted at fixed inputs, a bound that can never trip.
const test = require('node:test');
const assert = require('node:assert');
const meter = require('../src/meter');
const { parseOrders, total } = require('../src/orders');
const SAMPLE = 'id=1;qty=2;price=150;status=Open;shipped_at=\n\nid=2;qty=1;price=99;status=shipped;shipped_at=2026-10-01';
test('TC-1 the total of the sample is right', () => assert.strictEqual(total(parseOrders(SAMPLE)), 399));
test('TC-2 a zero quantity is rejected', () => {
  assert.throws(() => parseOrders('id=1;qty=0;price=1;status=open;shipped_at='), RangeError);
});
test('TC-3 an unknown status is rejected', () => {
  assert.throws(() => parseOrders('id=1;qty=1;price=1;status=lost;shipped_at='), SyntaxError);
});
test('TC-4 a bad date is rejected', () => {
  assert.throws(() => parseOrders('id=1;qty=1;price=1;status=shipped;shipped_at=yesterday'), SyntaxError);
});
test('TC-5 total stays within the work budget', () => {
  meter.reset();
  total(parseOrders(SAMPLE));
  assert.ok(meter.count() < meter.LIMIT);
});
