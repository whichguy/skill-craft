'use strict';
const test = require('node:test');
const assert = require('node:assert');
const meter = require('../src/meter');
const { parseOrders, total } = require('../src/orders');
const SAMPLE = 'id=1;qty=2;price=150;status=Open;shipped_at=\n\nid=2;qty=1;price=99;status=shipped;shipped_at=2026-10-01';
test('TC-1 parse returns exactly the normalised orders', () => {
  assert.deepStrictEqual(parseOrders(SAMPLE), [
    { id: 1, qty: 2, price: 150, status: 'open', shippedAt: '' },
    { id: 2, qty: 1, price: 99, status: 'shipped', shippedAt: '2026-10-01' },
  ]);
  assert.strictEqual(total(parseOrders(SAMPLE)), 399);
});
test('TC-2 any quantity below one is rejected, naming the line', () => {
  for (const qty of ['0', '-2', '1.5', 'x']) {
    assert.throws(() => parseOrders(`id=1;qty=1;price=1;status=open;shipped_at=\nid=2;qty=${qty};price=1;status=open;shipped_at=`),
      (e) => e instanceof RangeError && /line 2/.test(e.message), qty);
  }
});
test('TC-3 shipped and shipped_at must agree', () => {
  assert.throws(() => parseOrders('id=1;qty=1;price=1;status=open;shipped_at=2026-10-01'), SyntaxError);
  assert.throws(() => parseOrders('id=1;qty=1;price=1;status=shipped;shipped_at='), SyntaxError);
});
test('TC-4 total costs one tick per order', () => {
  const orders = parseOrders(SAMPLE);
  meter.reset();
  total(orders);
  assert.ok(meter.count() <= orders.length, `ticks ${meter.count()}`);
});
