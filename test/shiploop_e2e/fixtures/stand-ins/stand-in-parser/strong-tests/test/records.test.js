'use strict';
const test = require('node:test');
const assert = require('node:assert');
const { parseRecords, select } = require('../src/records');
test('TC-1 parse reads every field of every line', () => {
  assert.deepStrictEqual(parseRecords('name=ada;team=x\n\nname=bob;team=y'),
    [{ name: 'ada', team: 'x' }, { name: 'bob', team: 'y' }]);
});
test('TC-2 select returns the matching records in order', () => {
  const rows = parseRecords('name=ada;team=x\nname=bob;team=y\nname=cy;team=x');
  assert.deepStrictEqual(select(rows, 'team', 'x').map((r) => r.name), ['ada', 'cy']);
});
test('TC-3 a malformed line is refused with its line number', () => {
  assert.throws(() => parseRecords('name=ada\nbroken'), (e) => e instanceof SyntaxError && /line 2/.test(e.message));
});
test('TC-4 a non-string is refused', () => assert.throws(() => parseRecords(3), TypeError));
