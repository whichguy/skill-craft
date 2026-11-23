'use strict';

const { describe, test } = require('node:test');
const assert = require('node:assert/strict');
const { delayFor } = require('../src/backoff');
const { manualClock } = require('../src/clock');
const { silentLogger } = require('../src/log');
const { createNotifier } = require('../src/notifier');
const { MAX_ATTEMPTS } = require('../src/outbox');
const { TicketStore } = require('../src/store');
const { Worker, deliverOutbox } = require('../src/worker');

function setup({ failing = 0 } = {}) {
  const clock = manualClock();
  const store = new TicketStore({ clock });
  const notifier = createNotifier({ clock });
  let failures = failing;
  const flaky = {
    delivered: notifier.delivered,
    deliver(event) {
      if (failures > 0) {
        failures -= 1;
        throw new Error('relay unavailable');
      }
      return notifier.deliver(event);
    },
  };
  const worker = new Worker({ intervalMs: 0, jobs: [deliverOutbox({ store, notifier: flaky, log: silentLogger })], log: silentLogger });
  return { clock, store, notifier: flaky, worker };
}

const input = { title: 'Monitor flickers', requester: 'li@example.com', priority: 'normal' };

describe('deliverOutbox', () => {
  test('delivers what is due and marks it sent', () => {
    const { store, notifier, worker } = setup();
    store.create(input, 'system');
    assert.deepEqual(worker.tick(), [{ job: 'deliver-outbox', sent: 1, failed: 0, dead: 0 }]);
    assert.equal(notifier.delivered.length, 1);
    assert.equal(store.outboxReport().sent.length, 1);
    assert.deepEqual(worker.tick(), [{ job: 'deliver-outbox', sent: 0, failed: 0, dead: 0 }], 'nothing is sent twice');
  });

  test('retries a failed delivery after its backoff', () => {
    const { clock, store, notifier, worker } = setup({ failing: 1 });
    store.create(input, 'system');
    assert.equal(worker.tick()[0].failed, 1);
    assert.equal(worker.tick()[0].sent, 0, 'not due again before the backoff');
    clock.advance(delayFor(1));
    assert.equal(worker.tick()[0].sent, 1);
    assert.equal(notifier.delivered.length, 1);
    assert.equal(store.outboxReport().sent[0].attempts, 2);
  });

  test(`gives up after ${MAX_ATTEMPTS} attempts and leaves the event dead`, () => {
    const { clock, store, worker } = setup({ failing: 99 });
    store.create(input, 'system');
    for (let attempt = 1; attempt < MAX_ATTEMPTS; attempt += 1) {
      assert.equal(worker.tick()[0].failed, 1);
      clock.advance(delayFor(attempt));
    }
    assert.equal(worker.tick()[0].dead, 1);
    const report = store.outboxReport();
    assert.equal(report.dead.length, 1);
    assert.equal(report.dead[0].lastError, 'relay unavailable');
    assert.equal(report.pending.length, 0);
  });
});

describe('Worker', () => {
  test('an interval of 0 starts nothing', () => {
    const worker = new Worker({ intervalMs: 0, jobs: [], log: silentLogger });
    assert.equal(worker.start(), false);
    assert.equal(worker.running, false);
  });

  test('runs its jobs on its interval until stopped', async () => {
    let runs = 0;
    const worker = new Worker({ intervalMs: 5, jobs: [{ name: 'count', run: () => ({ runs: ++runs }) }], log: silentLogger });
    assert.equal(worker.start(), true);
    assert.equal(worker.start(), false, 'a running worker is not started twice');
    const end = Date.now() + 5000;
    while (runs < 3 && Date.now() < end) await new Promise((resolve) => setTimeout(resolve, 5));
    worker.stop();
    const seen = runs;
    assert.ok(seen >= 3, `ran ${seen} times in 5 s`);
    await new Promise((resolve) => setTimeout(resolve, 30));
    assert.equal(runs, seen, 'a stopped worker runs no more');
  });

  test('a job that throws does not stop the jobs after it', () => {
    const worker = new Worker({
      intervalMs: 0,
      jobs: [{ name: 'broken', run: () => { throw new Error('boom'); } }, { name: 'fine', run: () => ({ ok: true }) }],
      log: silentLogger,
    });
    assert.deepEqual(worker.tick(), [{ job: 'broken', error: 'boom' }, { job: 'fine', ok: true }]);
  });
});
