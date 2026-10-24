'use strict';
const test = require('node:test');
const assert = require('node:assert');
const deployed = require('./deployed');
test('TC-1 discount takes the percentage off', () => assert.strictEqual(deployed('pricing.js').discount(80, 25), 60));
test('TC-2 discount refuses a pct above 100', () => assert.throws(() => deployed('pricing.js').discount(10, 101), RangeError));
