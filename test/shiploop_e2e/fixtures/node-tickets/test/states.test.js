'use strict';

const { test } = require('node:test');
const assert = require('node:assert/strict');
const { STATUSES, canTransition, isActive, isFinal, isStatus, nextStatuses } = require('../src/tickets/states');

test('the lifecycle moves forward one step at a time and a resolved ticket can reopen', () => {
  const allowed = [];
  for (const from of STATUSES) {
    for (const to of STATUSES) if (canTransition(from, to)) allowed.push(`${from}>${to}`);
  }
  assert.deepEqual(allowed.sort(), ['in_progress>resolved', 'open>in_progress', 'resolved>closed', 'resolved>open']);
});

test('closed is final and nothing else is', () => {
  assert.deepEqual(STATUSES.filter(isFinal), ['closed']);
  assert.deepEqual(nextStatuses('closed'), []);
  assert.deepEqual(nextStatuses('resolved'), ['closed', 'open']);
});

test('open and in_progress tickets are active', () => {
  assert.deepEqual(STATUSES.filter(isActive), ['open', 'in_progress']);
});

test('an unknown status moves nowhere', () => {
  assert.equal(isStatus('pending'), false);
  assert.equal(canTransition('pending', 'open'), false);
  assert.deepEqual(nextStatuses('pending'), []);
});
