'use strict';

/**
 * The background worker (docs/decisions/0006-notification-outbox.md). It runs inside the server process and, every
 * `intervalMs`, runs each of its jobs once, in order.
 *
 * It is the service's one background loop. Work that happens on a schedule rather than in answer to a request is a
 * job here: never a timer of its own, and never a side effect of a request. An interval of 0 turns the worker off, and
 * with it all background work; the tests and the operator command line rely on that.
 *
 * A job is { name, run() }. The one job today is deliverOutbox.
 */
class Worker {
  constructor({ intervalMs, jobs = [], log }) {
    this.intervalMs = intervalMs;
    this.jobs = jobs;
    this.log = log;
    this.timer = null;
    this.busy = false;
  }

  /** Start ticking. False, and nothing started, when the interval is 0 or the worker already runs. */
  start() {
    if (this.intervalMs <= 0 || this.timer) return false;
    this.timer = setInterval(() => this.tick(), this.intervalMs);
    return true;
  }

  stop() {
    if (this.timer) clearInterval(this.timer);
    this.timer = null;
  }

  get running() {
    return this.timer !== null;
  }

  /** Run every job once and return what each reported. A job that throws is logged; the next one still runs. */
  tick() {
    if (this.busy) return [];
    this.busy = true;
    try {
      return this.jobs.map((job) => {
        try {
          return { job: job.name, ...job.run() };
        } catch (error) {
          this.log.error(`worker job ${job.name} failed`, error);
          return { job: job.name, error: error.message };
        }
      });
    } finally {
      this.busy = false;
    }
  }
}

/**
 * The outbox job: deliver every due event through the notifier and record each attempt in the store. A failed event is
 * retried on a later tick after its backoff, and is dead after its last attempt.
 */
function deliverOutbox({ store, notifier, log }) {
  return {
    name: 'deliver-outbox',
    run() {
      const report = { sent: 0, failed: 0, dead: 0 };
      for (const event of store.dueNotifications()) {
        try {
          notifier.deliver(event);
        } catch (error) {
          const after = store.recordDelivery(event.id, error);
          if (after.status === 'dead') {
            report.dead += 1;
            log.warn(`notification ${after.id} (${after.type} to ${after.to}) is dead after ${after.attempts} attempts: ${after.lastError}`);
          } else {
            report.failed += 1;
          }
          continue;
        }
        store.recordDelivery(event.id);
        report.sent += 1;
      }
      return report;
    },
  };
}

module.exports = { Worker, deliverOutbox };
