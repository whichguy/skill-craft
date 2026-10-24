'use strict';
const test = require('node:test');
const assert = require('node:assert');
const { parseRecords, select } = require('../src/records');
test('TC-1 parse returns an array', () => assert.ok(Array.isArray(parseRecords('a=1'))));
test('TC-2 select finds no missing value', () => {
  assert.strictEqual(select(parseRecords('name=ada;team=x'), 'team', 'nope').length, 0);
});
test('TC-3 no record has an unexpected key', () => {
  assert.ok(!parseRecords('name=ada').some((r) => 'zzz' in r));
});
