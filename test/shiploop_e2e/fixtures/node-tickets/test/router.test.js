'use strict';

const { test } = require('node:test');
const assert = require('node:assert/strict');
const { InvalidError } = require('../src/errors');
const { Router } = require('../src/router');

function router() {
  return new Router()
    .get('/tickets', () => 'list')
    .get('/tickets/:id', () => 'one')
    .post('/tickets/:id/transition', () => 'move');
}

test('a route matches its method and path and hands over the parameters', () => {
  const found = router().match('GET', '/tickets/T-0007');
  assert.equal(found.handler(), 'one');
  assert.deepEqual(found.params, { id: 'T-0007' });
  assert.equal(found.pattern, '/tickets/:id');
});

test('a trailing slash is ignored and a parameter never spans segments', () => {
  assert.equal(router().match('GET', '/tickets/').handler(), 'list');
  assert.equal(router().match('GET', '/tickets/T-0007/extra'), null);
  assert.deepEqual(router().match('POST', '/tickets/T-0007/transition').params, { id: 'T-0007' });
});

test('the method must match too', () => {
  assert.equal(router().match('DELETE', '/tickets/T-0007'), null);
  assert.deepEqual(router().methodsFor('/tickets/T-0007'), ['GET']);
  assert.deepEqual(router().methodsFor('/nowhere'), []);
});

test('parameters are decoded, and bad encoding is invalid', () => {
  assert.deepEqual(router().match('GET', '/tickets/T%2D0007').params, { id: 'T-0007' });
  assert.throws(() => router().match('GET', '/tickets/%E0%A4%A'), InvalidError);
});
