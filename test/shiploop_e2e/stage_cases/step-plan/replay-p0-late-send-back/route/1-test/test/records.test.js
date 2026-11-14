'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const { parseRecords } = require('../src/records');

test('TC-1 parses and trims records', () => {
  assert.deepStrictEqual(parseRecords('name=ada;team=x\n\nname=bob;team=y'), [
    { name: 'ada', team: 'x' }, { name: 'bob', team: 'y' }
  ]);
  assert.deepStrictEqual(parseRecords('a= x \n \nb_2= y'), [{ a: 'x' }, { b_2: 'y' }]);
  assert.deepStrictEqual(parseRecords('  \n\n'), []);
  assert.deepStrictEqual(parseRecords('constructor=ok;z=1=2'), [{ constructor: 'ok', z: '1=2' }]);
});

test('TC-1 (a) accepts an empty value', () => {
  assert.deepStrictEqual(parseRecords('a=;b=  '), [{ a: '', b: '' }]);
});

test('TC-2 rejects malformed fields and non-string input', () => {
  for (const field of ['bad', '=x', 'A=x', 'a-b=x', '1a=x', 'a=1;a=2']) {
    assert.throws(() => parseRecords(`ok=1\n${field}`),
      error => error instanceof SyntaxError && /line 2\b/.test(error.message));
  }
  assert.throws(() => parseRecords('ok=1\n\na=1;a=2'),
    error => error instanceof SyntaxError && /line 3\b/.test(error.message));
  const object = {};
  const array = [];
  for (const input of [undefined, null, 1, object, array]) {
    assert.throws(() => parseRecords(input),
      error => error instanceof TypeError && /text/.test(error.message));
  }
  assert.deepStrictEqual(object, {});
  assert.deepStrictEqual(array, []);
});
