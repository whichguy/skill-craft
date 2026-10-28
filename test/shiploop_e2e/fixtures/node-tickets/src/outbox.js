'use strict';

const { delayFor } = require('./backoff');

/**
 * The notification outbox (docs/decisions/0006-notification-outbox.md).
 *
 * A change that should tell someone something enqueues an event here, inside the same store change as the ticket and
 * its audit entry, and the worker (src/worker.js) delivers it later. Request handlers never call the notifier, so a
 * slow or broken mail relay never fails or slows a request, and a crash never loses a notification the change made.
 *
 * An event:
 *
 *   { id, key, type, to, ticket, data, status, attempts, created, nextAttemptAt, lastError, sentAt }
 *
 * `status` is pending, sent or dead. A failed delivery is tried again after a backoff (src/backoff.js); after
 * MAX_ATTEMPTS failed attempts the event is dead and stays for an operator to look at (GET /admin/outbox).
 *
 * `key` deduplicates: enqueueing a key that is already pending returns the pending event and changes nothing. Once the
 * event is sent (or dead) the key is free again.
 */

const MAX_ATTEMPTS = 5;
const STATES = Object.freeze(['pending', 'sent', 'dead']);

class Outbox {
  constructor({ events = [], nextId = 1 } = {}) {
    this.events = events.map((event) => ({ ...event }));
    this.nextId = nextId;
  }

  /** Enqueue a notification for `to`, due now; the pending event with the same key instead, when there is one. */
  enqueue({ key, type, to, ticket = null, data = {} }, now) {
    for (const [name, value] of Object.entries({ key, type, to })) {
      if (typeof value !== 'string' || value === '') throw new TypeError(`an outbox event needs ${name}`);
    }
    const pending = this.pendingWithKey(key);
    if (pending) return pending;
    const at = now.toISOString();
    const event = {
      id: this.nextId,
      key,
      type,
      to,
      ticket,
      data,
      status: 'pending',
      attempts: 0,
      created: at,
      nextAttemptAt: at,
      lastError: null,
      sentAt: null,
    };
    this.nextId += 1;
    this.events.push(event);
    return event;
  }

  pendingWithKey(key) {
    return this.events.find((event) => event.key === key && event.status === 'pending') || null;
  }

  /** The pending events whose next attempt is due at `now`, oldest first. */
  due(now) {
    const time = now.getTime();
    return this.events.filter((event) => event.status === 'pending' && Date.parse(event.nextAttemptAt) <= time);
  }

  markSent(id, now) {
    const event = this.pending(id);
    event.attempts += 1;
    event.status = 'sent';
    event.sentAt = now.toISOString();
    event.nextAttemptAt = null;
    event.lastError = null;
    return event;
  }

  /** Record a failed attempt: try again after the backoff, or mark the event dead after MAX_ATTEMPTS. */
  markFailed(id, error, now) {
    const event = this.pending(id);
    event.attempts += 1;
    event.lastError = String((error && error.message) || error).slice(0, 500);
    if (event.attempts >= MAX_ATTEMPTS) {
      event.status = 'dead';
      event.nextAttemptAt = null;
    } else {
      event.nextAttemptAt = new Date(now.getTime() + delayFor(event.attempts)).toISOString();
    }
    return event;
  }

  /** Every event, copied, by state: { pending, sent, dead }. */
  byStatus() {
    const report = Object.fromEntries(STATES.map((state) => [state, []]));
    for (const event of this.events) report[event.status].push({ ...event, data: { ...event.data } });
    return report;
  }

  pending(id) {
    const event = this.events.find((candidate) => candidate.id === id);
    if (!event) throw new RangeError(`no outbox event ${id}`);
    if (event.status !== 'pending') throw new RangeError(`outbox event ${id} is ${event.status}, not pending`);
    return event;
  }

  toJSON() {
    return { nextId: this.nextId, events: this.events.map((event) => ({ ...event, data: { ...event.data } })) };
  }
}

module.exports = { MAX_ATTEMPTS, Outbox, STATES };
