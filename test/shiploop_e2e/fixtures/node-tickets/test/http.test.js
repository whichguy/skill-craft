'use strict';

const { describe, test } = require('node:test');
const assert = require('node:assert/strict');
const { Readable } = require('node:stream');
const { InvalidError } = require('../src/errors');
const { actorOf, readJson } = require('../src/http');

const request = (text, headers = {}) => Object.assign(Readable.from(text === null ? [] : [Buffer.from(text)]), { headers });

describe('readJson', () => {
  test('parses a JSON object', async () => {
    assert.deepEqual(await readJson(request('{"to":"resolved"}')), { to: 'resolved' });
  });

  test('refuses an empty body, text that is not JSON and JSON that is not an object', async () => {
    for (const text of [null, '   ', '{"to":', '[1,2]', '"text"', 'null']) {
      await assert.rejects(readJson(request(text)), InvalidError, String(text));
    }
  });

  test('refuses a body over the limit', async () => {
    await assert.rejects(readJson(request(JSON.stringify({ title: 'x'.repeat(100) })), { limit: 50 }), /larger than 50 bytes/);
  });
});

describe('actorOf', () => {
  test('is the X-Actor header, trimmed', () => {
    assert.equal(actorOf({ headers: { 'x-actor': '  dana ' } }), 'dana');
  });

  test('is system without one', () => {
    assert.equal(actorOf({ headers: {} }), 'system');
    assert.equal(actorOf({ headers: { 'x-actor': '   ' } }), 'system');
  });

  test('refuses an actor longer than 64 characters', () => {
    assert.throws(() => actorOf({ headers: { 'x-actor': 'a'.repeat(65) } }), InvalidError);
    assert.equal(actorOf({ headers: { 'x-actor': 'a'.repeat(64) } }).length, 64);
  });
});
