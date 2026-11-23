'use strict';

const { test } = require('node:test');
const assert = require('node:assert/strict');
const { AppError, ConflictError, InvalidError, NotFoundError, toResponse } = require('../src/errors');

test('each error class answers its code and status in the envelope', () => {
  for (const [error, status, code] of [
    [new InvalidError('bad'), 400, 'invalid'],
    [new NotFoundError('gone'), 404, 'not_found'],
    [new ConflictError('not now'), 409, 'conflict'],
  ]) {
    assert.deepEqual(toResponse(error), { status, body: { error: { code, message: error.message } } });
  }
});

test('details travel in the envelope when there are some', () => {
  const { body } = toResponse(new InvalidError('bad', { field: 'title' }));
  assert.deepEqual(body, { error: { code: 'invalid', message: 'bad', details: { field: 'title' } } });
});

test('anything else is an internal error that says nothing more', () => {
  assert.deepEqual(toResponse(new TypeError('x is undefined')), {
    status: 500,
    body: { error: { code: 'internal', message: 'internal error' } },
  });
});

test('an unknown code is a programming error', () => {
  assert.throws(() => new AppError('teapot', 'no'), TypeError);
});
