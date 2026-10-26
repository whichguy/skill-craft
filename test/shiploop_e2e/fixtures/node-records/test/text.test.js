'use strict';
const test = require('node:test');
const assert = require('node:assert');
const { squash } = require('../src/text');
test('squash collapses whitespace', () => assert.strictEqual(squash('  a   b '), 'a b'));
test('squash rejects a non-string', () => assert.throws(() => squash(1), TypeError));
