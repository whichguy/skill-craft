'use strict';
const test = require('node:test');
const assert = require('node:assert');
const meter = require('../src/meter');
test('meter counts ticks and resets', () => {
  meter.reset(); meter.tick(); meter.tick();
  assert.strictEqual(meter.count(), 2);
  meter.reset();
  assert.strictEqual(meter.count(), 0);
});
test('meter throws past its limit', () => {
  meter.reset();
  assert.throws(() => { for (let i = 0; i <= meter.LIMIT; i += 1) meter.tick(); }, meter.LimitError);
  meter.reset();
});
