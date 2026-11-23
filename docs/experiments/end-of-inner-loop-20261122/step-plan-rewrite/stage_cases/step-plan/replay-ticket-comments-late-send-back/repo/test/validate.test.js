'use strict';

const { describe, test } = require('node:test');
const assert = require('node:assert/strict');
const { InvalidError } = require('../src/errors');
const validate = require('../src/tickets/validate');

const invalid = (fn, message) => assert.throws(fn, (error) => error instanceof InvalidError && message.test(error.message));

describe('newTicket', () => {
  test('trims the text fields and defaults the priority to normal', () => {
    assert.deepEqual(validate.newTicket({ title: '  VPN drops ', requester: 'li@example.com' }), {
      title: 'VPN drops',
      requester: 'li@example.com',
      priority: 'normal',
    });
  });

  test('keeps a priority that is one of the four', () => {
    assert.equal(validate.newTicket({ title: 'a', requester: 'b', priority: 'urgent' }).priority, 'urgent');
    invalid(() => validate.newTicket({ title: 'a', requester: 'b', priority: 'critical' }), /priority must be one of/);
  });

  test('refuses a missing, empty, too long or multi-line title', () => {
    invalid(() => validate.newTicket({ requester: 'b' }), /title must be a string/);
    invalid(() => validate.newTicket({ title: '   ', requester: 'b' }), /title must not be empty/);
    invalid(() => validate.newTicket({ title: 'x'.repeat(201), requester: 'b' }), /at most 200/);
    invalid(() => validate.newTicket({ title: 'one\ttwo', requester: 'b' }), /single line/);
    assert.equal(validate.newTicket({ title: 'x'.repeat(200), requester: 'b' }).title.length, 200);
  });

  test('limits the requester to 64 characters', () => {
    assert.equal(validate.newTicket({ title: 'a', requester: 'r'.repeat(64) }).requester.length, 64);
    invalid(() => validate.newTicket({ title: 'a', requester: 'r'.repeat(65) }), /requester must be at most 64/);
  });

  test('refuses a field it does not take', () => {
    invalid(() => validate.newTicket({ title: 'a', requester: 'b', status: 'closed' }), /unknown field: status/);
  });
});

describe('ticketPatch', () => {
  test('takes a title, a priority or both', () => {
    assert.deepEqual(validate.ticketPatch({ priority: 'high' }), { priority: 'high' });
    assert.deepEqual(validate.ticketPatch({ title: 'New', priority: 'low' }), { title: 'New', priority: 'low' });
  });

  test('refuses an empty change and fields it does not take', () => {
    invalid(() => validate.ticketPatch({}), /nothing to change/);
    invalid(() => validate.ticketPatch({ requester: 'x' }), /unknown field: requester/);
  });
});

describe('transition', () => {
  test('takes a status and refuses anything else', () => {
    assert.equal(validate.transition({ to: 'resolved' }), 'resolved');
    invalid(() => validate.transition({ to: 'done' }), /to must be one of open, in_progress, resolved, closed/);
    invalid(() => validate.transition({}), /to must be one of/);
  });
});
