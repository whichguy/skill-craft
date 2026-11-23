'use strict';

const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { manualClock } = require('../src/clock');
const { loadConfig } = require('../src/config');
const { silentLogger } = require('../src/log');
const { createPersistence } = require('../src/persistence');
const { createService } = require('../src/server');
const { TicketStore } = require('../src/store');
const { createNotifier } = require('../src/notifier');
const { deliverOutbox } = require('../src/worker');
const { ticketBody, withService } = require('./helpers');

test('TC_1 bulk reassignment validates, orders, audits and notifies only active matches', async () => {
  await withService({}, async (api, service) => {
    for (let i = 0; i < 6; i++) await api.post('/tickets', ticketBody());
    for (const id of [1, 2, 3, 4]) await api.put(`/tickets/T-000${id}/assignee`, { assignee: 'Alice' });
    await api.put('/tickets/T-0005/assignee', { assignee: 'Other' });
    await api.post('/tickets/T-0002/transition', { to: 'in_progress' });
    for (const id of [3, 4]) {
      await api.post(`/tickets/T-000${id}/transition`, { to: 'in_progress' });
      await api.post(`/tickets/T-000${id}/transition`, { to: 'resolved' });
    }
    await api.post('/tickets/T-0004/transition', { to: 'closed' });
    const before = service.store.snapshot();
    for (const body of [{}, { from: 'Alice', to: ' Alice ' }, { from: null, to: 'Bob' },
      { from: 'Alice', to: '' }, { from: 'Alice', to: 'x'.repeat(65) },
      { from: 'Alice', to: 'B\nob' }, { from: 'Alice', to: 'Bob', extra: 1 }]) {
      const response = await api.post('/tickets/reassign', body);
      assert.equal(response.status, 400);
      assert.equal(response.body.error.code, 'invalid');
    }
    assert.deepEqual(service.store.snapshot(), before);
    const result = await api.post('/tickets/reassign', { from: ' Alice ', to: ' Bob ' }, { 'X-Actor': 'manager' });
    assert.equal(result.status, 200);
    assert.deepEqual(result.body, { moved: 2, ids: ['T-0001', 'T-0002'] });
    for (const id of ['T-0001', 'T-0002']) {
      assert.equal((await api.get(`/tickets/${id}`)).body.assignee, 'Bob');
      const entry = (await api.get(`/tickets/${id}/audit`)).body.items.at(-1);
      assert.equal(entry.action, 'ticket.assigned');
      assert.equal(entry.actor, 'manager');
      assert.deepEqual(entry.changes.assignee, { from: 'Alice', to: 'Bob' });
    }
    assert.equal((await api.get('/tickets/T-0003')).body.assignee, 'Alice');
    assert.equal((await api.get('/tickets/T-0004')).body.assignee, 'Alice');
    assert.equal((await api.get('/tickets/T-0005')).body.assignee, 'Other');
    assert.equal((await api.get('/tickets/T-0006')).body.assignee, null);
    const events = service.store.outboxReport().pending.filter((e) => e.type === 'ticket.assigned' && e.to === 'Bob');
    assert.deepEqual(events.map((e) => e.ticket), ['T-0001', 'T-0002']);
    service.worker.tick();
    assert.deepEqual(service.notifier.delivered.filter((e) => e.type === 'ticket.assigned' && e.to === 'Bob').map((e) => e.ticket), ['T-0001', 'T-0002']);
    const unchanged = service.store.snapshot();
    assert.deepEqual((await api.post('/tickets/reassign', { from: 'Nobody', to: 'Bob' })).body, { moved: 0, ids: [] });
    assert.deepEqual(service.store.snapshot(), unchanged);
  });
});

test('TC_2 escalation uses a strict age boundary and persists once across restart', (t) => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'ticket-escalation-'));
  t.after(() => fs.rmSync(dir, { recursive: true, force: true }));
  const file = path.join(dir, 'data.json');
  const clock = manualClock();
  const persistence = createPersistence(file, { clock });
  let store = TicketStore.open({ clock, persistence });
  const create = (priority = 'urgent') => store.create({ title: 'Help', requester: 'requester', priority }, 'creator');
  const urgent = create();
  const assigned = create(); store.assign(assigned.id, 'Alice', 'actor');
  const progress = create(); store.transition(progress.id, 'in_progress', 'actor');
  const resolved = create(); store.transition(resolved.id, 'in_progress', 'actor'); store.transition(resolved.id, 'resolved', 'actor');
  const normal = create('normal');
  clock.advance(60 * 60000);
  assert.deepEqual(store.escalate({ oncall: 'Oncall', afterMinutes: 60 }), { escalated: 0 });
  clock.advance(1);
  assert.deepEqual(store.escalate({ oncall: null, afterMinutes: 60 }), { escalated: 0 });
  assert.deepEqual(store.escalate({ oncall: 'Oncall', afterMinutes: 60 }), { escalated: 1 });
  assert.equal(store.get(urgent.id).assignee, null);
  const event = store.outboxReport().pending.find((e) => e.type === 'ticket.escalated');
  assert.equal(event.ticket, urgent.id); assert.equal(event.to, 'Oncall');
  for (const ticket of [assigned, progress, resolved, normal]) assert.equal(store.get(ticket.id).escalatedAt, null);
  store = TicketStore.open({ clock, persistence });
  assert.deepEqual(store.escalate({ oncall: 'Different', afterMinutes: 60 }), { escalated: 0 });
  const notifier = createNotifier({ clock });
  deliverOutbox({ store, notifier, log: silentLogger }).run();
  const notices = notifier.delivered.filter((e) => e.type === 'ticket.escalated');
  assert.equal(notices.length, 1); assert.equal(notices[0].to, 'Oncall'); assert.match(notices[0].body, /escalated/i);
  store = TicketStore.open({ clock, persistence });
  assert.deepEqual(store.escalate({ oncall: 'Oncall', afterMinutes: 60 }), { escalated: 0 });
  const legacy = JSON.parse(fs.readFileSync(file, 'utf8'));
  delete legacy.tickets.find((ticket) => ticket.id === normal.id).escalatedAt;
  fs.writeFileSync(file, JSON.stringify(legacy));
  assert.equal(TicketStore.open({ clock, persistence }).get(normal.id).escalatedAt, null);
});

test('TC_3 configuration and worker deliver escalations only when enabled', () => {
  const defaults = loadConfig({});
  assert.equal(defaults.escalateAfterMinutes, 60); assert.equal(defaults.oncall, null);
  for (const env of [{ ESCALATE_AFTER_MINUTES: '-1' }, { ESCALATE_AFTER_MINUTES: 'abc' }, { ONCALL: 'x'.repeat(65) }, { ONCALL: 'a\nb' }]) {
    assert.throws(() => loadConfig(env));
  }
  const maxMinutes = Math.floor(Number.MAX_SAFE_INTEGER / 60000);
  assert.equal(loadConfig({ ESCALATE_AFTER_MINUTES: String(maxMinutes) }).escalateAfterMinutes, maxMinutes);
  assert.throws(() => loadConfig({ ESCALATE_AFTER_MINUTES: String(maxMinutes + 1) }));
  const clock = manualClock();
  const settings = loadConfig({ ONCALL: ' Bob ', ESCALATE_AFTER_MINUTES: '2', WORKER_INTERVAL_MS: '0' });
  const service = createService(settings, { clock, log: silentLogger });
  service.store.create({ title: 'Urgent', requester: 'a', priority: 'urgent' }, 'actor');
  clock.advance(120001);
  assert.equal(service.worker.start(), false);
  service.worker.tick();
  assert.equal(service.notifier.delivered.filter((e) => e.type === 'ticket.escalated' && e.to === 'Bob').length, 1);
  service.worker.tick();
  assert.equal(service.notifier.delivered.filter((e) => e.type === 'ticket.escalated').length, 1);
  const legacySettings = { ...defaults, oncall: 'Fallback' };
  delete legacySettings.escalateAfterMinutes;
  const legacy = createService(legacySettings, { clock, log: silentLogger });
  legacy.store.create({ title: 'Urgent', requester: 'a', priority: 'urgent' }, 'actor');
  clock.advance(3600001); legacy.worker.tick();
  assert.equal(legacy.notifier.delivered.filter((e) => e.type === 'ticket.escalated' && e.to === 'Fallback').length, 1);
  const disabled = createService(defaults, { clock, log: silentLogger });
  disabled.store.create({ title: 'Urgent', requester: 'a', priority: 'urgent' }, 'actor');
  clock.advance(3600001); disabled.worker.tick();
  assert.equal(disabled.notifier.delivered.filter((e) => e.type === 'ticket.escalated').length, 0);
});
