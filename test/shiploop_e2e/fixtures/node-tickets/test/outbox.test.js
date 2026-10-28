'use strict';

const { describe, test } = require('node:test');
const assert = require('node:assert/strict');
const { delayFor } = require('../src/backoff');
const { MAX_ATTEMPTS, Outbox } = require('../src/outbox');

const T0 = new Date('2025-09-01T08:00:00.000Z');
const later = (ms) => new Date(T0.getTime() + ms);
const event = (key = 'ticket.created:T-0001') => ({ key, type: 'ticket.created', to: 'maria@example.com', ticket: 'T-0001' });

describe('enqueue', () => {
  test('makes a pending event that is due at once', () => {
    const outbox = new Outbox();
    const queued = outbox.enqueue(event(), T0);
    assert.equal(queued.id, 1);
    assert.equal(queued.status, 'pending');
    assert.equal(queued.attempts, 0);
    assert.deepEqual(outbox.due(T0).map((e) => e.id), [1]);
  });

  test('changes nothing for a key that is already pending', () => {
    const outbox = new Outbox();
    const first = outbox.enqueue(event(), T0);
    const second = outbox.enqueue({ ...event(), to: 'someone@example.com' }, later(10));
    assert.equal(second, first);
    assert.equal(outbox.events.length, 1);
    assert.equal(first.to, 'maria@example.com');
  });

  test('queues a key again once the earlier event was sent', () => {
    const outbox = new Outbox();
    outbox.markSent(outbox.enqueue(event(), T0).id, T0);
    const again = outbox.enqueue(event(), later(10));
    assert.equal(again.id, 2);
    assert.equal(outbox.events.length, 2);
  });

  test('needs a key, a type and a recipient', () => {
    assert.throws(() => new Outbox().enqueue({ ...event(), to: '' }, T0), /needs to/);
  });
});

describe('delivery attempts', () => {
  test('a sent event records its time and is no longer due', () => {
    const outbox = new Outbox();
    const sent = outbox.markSent(outbox.enqueue(event(), T0).id, later(5));
    assert.equal(sent.status, 'sent');
    assert.equal(sent.attempts, 1);
    assert.equal(sent.sentAt, later(5).toISOString());
    assert.deepEqual(outbox.due(later(60_000)), []);
  });

  test('a failed event waits out its backoff before it is due again', () => {
    const outbox = new Outbox();
    const { id } = outbox.enqueue(event(), T0);
    const failed = outbox.markFailed(id, new Error('relay down'), T0);
    assert.equal(failed.status, 'pending');
    assert.equal(failed.lastError, 'relay down');
    assert.deepEqual(outbox.due(later(delayFor(1) - 1)), []);
    assert.deepEqual(outbox.due(later(delayFor(1))).map((e) => e.id), [id]);
  });

  test(`an event is dead after ${MAX_ATTEMPTS} failed attempts`, () => {
    const outbox = new Outbox();
    const { id } = outbox.enqueue(event(), T0);
    let now = T0;
    for (let attempt = 1; attempt < MAX_ATTEMPTS; attempt += 1) {
      assert.equal(outbox.markFailed(id, 'timeout', now).status, 'pending');
      now = later(now.getTime() - T0.getTime() + delayFor(attempt));
    }
    const dead = outbox.markFailed(id, 'timeout', now);
    assert.equal(dead.status, 'dead');
    assert.equal(dead.attempts, MAX_ATTEMPTS);
    assert.equal(dead.nextAttemptAt, null);
    assert.deepEqual(outbox.due(later(3_600_000)), []);
  });

  test('only a pending event can be attempted', () => {
    const outbox = new Outbox();
    const { id } = outbox.enqueue(event(), T0);
    outbox.markSent(id, T0);
    assert.throws(() => outbox.markSent(id, T0), /is sent, not pending/);
    assert.throws(() => outbox.markFailed(99, 'x', T0), /no outbox event 99/);
  });
});

describe('backoff', () => {
  test('doubles from one second and stops at five minutes', () => {
    assert.deepEqual([1, 2, 3, 4].map((n) => delayFor(n)), [1000, 2000, 4000, 8000]);
    assert.equal(delayFor(20), 5 * 60 * 1000);
    assert.throws(() => delayFor(0), RangeError);
  });
});

test('byStatus lists copies of every event under its state', () => {
  const outbox = new Outbox();
  outbox.enqueue(event('a'), T0);
  outbox.markSent(outbox.enqueue(event('b'), T0).id, T0);
  const report = outbox.byStatus();
  assert.deepEqual(Object.keys(report), ['pending', 'sent', 'dead']);
  assert.deepEqual([report.pending.length, report.sent.length, report.dead.length], [1, 1, 0]);
  report.pending[0].status = 'sent';
  assert.equal(outbox.events[0].status, 'pending');
});
