'use strict';
const test = require('node:test');
const assert = require('node:assert');
const { badgeLabel } = require('../src/format');
test('badgeLabel caps at 99+', () => assert.strictEqual(badgeLabel(120), '99+'));
test('badgeLabel rejects a fraction', () => assert.throws(() => badgeLabel(1.5), TypeError));
