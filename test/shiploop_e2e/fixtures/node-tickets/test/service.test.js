'use strict';

const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { systemClock } = require('../src/clock');
const { ticketBody, withService } = require('./helpers');

function folder(t) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'tickets-service-'));
  t.after(() => fs.rmSync(dir, { recursive: true, force: true }));
  return dir;
}

async function until(condition, { timeout = 3000, every = 10 } = {}) {
  const end = Date.now() + timeout;
  while (Date.now() < end) {
    if (await condition()) return true;
    await new Promise((resolve) => setTimeout(resolve, every));
  }
  return false;
}

test('with a data file, a restarted service has the same tickets, history and outbox', async (t) => {
  const dataFile = path.join(folder(t), 'tickets.json');
  await withService({ dataFile }, async (api) => {
    await api.post('/tickets', ticketBody({ priority: 'urgent' }), { 'X-Actor': 'dana' });
    await api.post('/tickets', ticketBody());
    await api.post('/tickets/T-0002/transition', { to: 'in_progress' }, { 'X-Actor': 'sam' });
  });
  await withService({ dataFile }, async (api) => {
    assert.deepEqual((await api.get('/tickets')).body.items.map((ticket) => [ticket.id, ticket.status]), [
      ['T-0001', 'open'],
      ['T-0002', 'in_progress'],
    ]);
    assert.deepEqual((await api.get('/tickets/T-0002/audit')).body.items.map((entry) => entry.actor), ['system', 'sam']);
    assert.equal((await api.get('/admin/outbox')).body.pending.length, 2);
    assert.equal((await api.post('/tickets', ticketBody())).body.id, 'T-0003', 'a number is never reused');
  });
});

test('the worker delivers each notification once to the notification file, and the outbox shows it sent', async (t) => {
  const dir = folder(t);
  const notifyFile = path.join(dir, 'notifications.jsonl');
  await withService({ notifyFile, workerIntervalMs: 10, clock: systemClock }, async (api) => {
    await api.post('/tickets', ticketBody({ requester: 'li@example.com' }));
    const sent = await until(async () => (await api.get('/admin/outbox')).body.sent.length === 1);
    assert.ok(sent, 'the notification was sent');
    await new Promise((resolve) => setTimeout(resolve, 50));
    const lines = fs.readFileSync(notifyFile, 'utf8').trim().split('\n').map((line) => JSON.parse(line));
    assert.deepEqual(lines.map((line) => [line.type, line.to, line.ticket]), [['ticket.created', 'li@example.com', 'T-0001']]);
    assert.equal((await api.get('/admin/outbox')).body.pending.length, 0);
  });
});

test('with the worker off, nothing is delivered', async (t) => {
  const notifyFile = path.join(folder(t), 'notifications.jsonl');
  await withService({ notifyFile, workerIntervalMs: 0, clock: systemClock }, async (api, service) => {
    await api.post('/tickets', ticketBody());
    await new Promise((resolve) => setTimeout(resolve, 50));
    assert.equal(service.worker.running, false);
    assert.equal(fs.existsSync(notifyFile), false);
    assert.equal((await api.get('/admin/outbox')).body.pending.length, 1);
  });
});
