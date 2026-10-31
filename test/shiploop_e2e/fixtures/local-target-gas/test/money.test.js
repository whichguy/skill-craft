'use strict';
const test = require('node:test');
const assert = require('node:assert');
const deployed = require('./deployed');
test('cents rounds to two places', () => assert.strictEqual(deployed('Money.js').cents(1.005 + 0.004), 1.01));
