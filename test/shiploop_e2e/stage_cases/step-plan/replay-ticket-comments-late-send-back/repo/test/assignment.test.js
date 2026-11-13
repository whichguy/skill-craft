'use strict';

const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { execFileSync } = require('node:child_process');
const { manualClock } = require('../src/clock');
const { silentLogger } = require('../src/log');
const { TicketStore } = require('../src/store');
const { createPersistence } = require('../src/persistence');
const { createNotifier } = require('../src/notifier');
const { deliverOutbox } = require('../src/worker');
const { ticketBody, withService } = require('./helpers');

function folder(t) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'ticket-assignment-'));
  t.after(() => fs.rmSync(dir, { recursive: true, force: true }));
  return dir;
}

const input = { title: 'Example', requester: 'requester', priority: 'high' };

test('TC_1 assignment persists, audits and delivers each actual assignment', (t) => {
  const clock = manualClock();
  const file = path.join(folder(t), 'tickets.json');
  const persistence = createPersistence(file, { clock });
  const store = TicketStore.open({ clock, persistence });
  const ticket = store.create(input, 'creator');
  assert.equal(ticket.assignee, null);
  for (const name of ['Alice', 'Bob', 'Alice']) assert.equal(store.assign(ticket.id, name, 'operator').assignee, name);
  const events = store.outboxReport().pending.filter((event) => event.type === 'ticket.assigned');
  assert.deepEqual(events.map((event) => event.to), ['Alice', 'Bob', 'Alice']);
  assert.deepEqual(store.history(ticket.id).at(-1).changes.assignee, { from: 'Bob', to: 'Alice' });
  assert.equal(store.history(ticket.id).at(-1).actor, 'operator');
  const before = store.snapshot();
  clock.advance(1000);
  store.assign(ticket.id, 'Alice', 'operator');
  assert.deepEqual(store.snapshot(), before);
  assert.equal(TicketStore.open({ clock, persistence }).get(ticket.id).assignee, 'Alice');
  const notifier = createNotifier({ clock });
  deliverOutbox({ store, notifier, log: silentLogger }).run();
  assert.deepEqual(notifier.delivered.filter((event) => event.type === 'ticket.assigned').map((event) => event.to), ['Alice', 'Bob', 'Alice']);
  assert.ok(notifier.delivered.find((event) => event.type === 'ticket.assigned').body.includes('assigned to you'));
  const count = store.outboxReport().sent.length;
  assert.equal(store.assign(ticket.id, null, 'operator').assignee, null);
  assert.equal(store.outboxReport().sent.length, count);
  assert.equal(store.outboxReport().pending.length, 0);
  store.transition(ticket.id, 'in_progress', 'operator');
  store.assign(ticket.id, 'Bob', 'operator');
  store.transition(ticket.id, 'resolved', 'operator');
  const resolved = store.snapshot();
  assert.throws(() => store.assign(ticket.id, null, 'operator'), /resolved/);
  assert.deepEqual(store.snapshot(), resolved);
  store.transition(ticket.id, 'closed', 'operator');
  assert.throws(() => store.assign(ticket.id, 'Bob', 'operator'), /closed/);
  const legacy = JSON.parse(fs.readFileSync(file, 'utf8'));
  delete legacy.tickets[0].assignee;
  fs.writeFileSync(file, JSON.stringify(legacy));
  assert.equal(TicketStore.open({ clock, persistence }).get(ticket.id).assignee, null);
  legacy.tickets[0].assignee = 'x'.repeat(65);
  fs.writeFileSync(file, JSON.stringify(legacy));
  assert.throws(() => persistence.load(), /assignee/);
});

test('TC_2 assignment HTTP validation, lifecycle and no-op', async () => {
  await withService({}, async (api) => {
    assert.equal((await api.post('/tickets', ticketBody({ requester: 'x'.repeat(65) }))).status, 400);
    const created = await api.post('/tickets', ticketBody());
    const id = created.body.id;
    const url = `/tickets/${id}/assignee`;
    assert.equal(created.body.assignee, null);
    const assigned = await api.put(url, { assignee: 'Alice' }, { 'X-Actor': 'sam' });
    assert.equal(assigned.status, 200);
    assert.equal(assigned.body.assignee, 'Alice');
    assert.equal((await api.get(`/tickets/${id}`)).body.assignee, 'Alice');
    assert.equal((await api.get('/tickets')).body.items[0].assignee, 'Alice');
    const audit = (await api.get(`/tickets/${id}/audit`)).body;
    const outbox = (await api.get('/admin/outbox')).body;
    assert.equal((await api.put(url, { assignee: 'Alice' })).status, 200);
    assert.deepEqual((await api.get(`/tickets/${id}/audit`)).body, audit);
    assert.deepEqual((await api.get('/admin/outbox')).body, outbox);
    for (const body of [{}, { assignee: '' }, { assignee: '   ' }, { assignee: 'x'.repeat(65) }, { assignee: 1 }, { assignee: {} }, { assignee: 'a\nb' }, { assignee: 'Bob', extra: true }]) {
      const response = await api.put(url, body);
      assert.equal(response.status, 400);
      assert.equal(response.body.error.code, 'invalid');
      assert.equal((await api.get(`/tickets/${id}`)).body.assignee, 'Alice');
    }
    assert.equal((await api.put(url, { assignee: 'x'.repeat(64) })).status, 200);
    assert.equal((await api.put(url, { assignee: null })).body.assignee, null);
    assert.equal((await api.put('/tickets/T-9999/assignee', { assignee: 'Alice' })).status, 404);
    await api.post(`/tickets/${id}/transition`, { to: 'in_progress' });
    assert.equal((await api.put(url, { assignee: 'Bob' })).status, 200);
    await api.post(`/tickets/${id}/transition`, { to: 'resolved' });
    assert.equal((await api.put(url, { assignee: null })).status, 409);
    await api.post(`/tickets/${id}/transition`, { to: 'closed' });
    assert.equal((await api.put(url, { assignee: 'Bob' })).status, 409);
    assert.equal((await api.get(`/tickets/${id}`)).body.assignee, 'Bob');
  });
});

test('TC_3 list filters intersect and paginate by assignee', async () => {
  await withService({}, async (api) => {
    for (const priority of ['high', 'high', 'high', 'low']) await api.post('/tickets', ticketBody({ priority }));
    await api.put('/tickets/T-0001/assignee', { assignee: 'Alice' });
    await api.put('/tickets/T-0002/assignee', { assignee: 'Bob' });
    await api.put('/tickets/T-0004/assignee', { assignee: 'Alice' });
    const ids = async (query) => (await api.get(`/tickets?${query}`)).body.items.map((item) => item.id);
    assert.deepEqual(await ids('assignee=Alice'), ['T-0001', 'T-0004']);
    assert.deepEqual(await ids('assignee='), ['T-0003']);
    assert.deepEqual(await ids('assignee=Alice&status=open&priority=high'), ['T-0001']);
    assert.deepEqual(await ids('assignee=Bob&status=resolved'), []);
    const first = (await api.get('/tickets?assignee=Alice&limit=1')).body;
    assert.deepEqual(first.items.map((item) => item.id), ['T-0001']);
    assert.ok(first.next);
    const second = (await api.get(`/tickets?assignee=Alice&limit=1&cursor=${encodeURIComponent(first.next)}`)).body;
    assert.deepEqual(second.items.map((item) => item.id), ['T-0004']);
    assert.equal(second.next, null);
  });
});

test('TC_4 CLI displays assignees and preserves report columns', (t) => {
  const file = path.join(folder(t), 'tickets.json');
  const clock = manualClock();
  const store = TicketStore.open({ clock, persistence: createPersistence(file, { clock }) });
  const first = store.create(input, 'actor');
  store.assign(first.id, 'Alice', 'actor');
  store.create({ ...input, title: 'Other' }, 'actor');
  const run = (args) => execFileSync(process.execPath, args, { cwd: path.join(__dirname, '..'), encoding: 'utf8' });
  const args = ['bin/tickets.js', '--data', file, 'list'];
  const table = run(args);
  assert.match(table, /Alice/);
  assert.match(table, /unassigned/);
  const lines = run([...args, '--raw']).split('\n').filter(Boolean);
  assert.deepEqual(lines[0].split('\t'), ['T-0001', 'open', 'high', 'Example', 'Alice']);
  assert.deepEqual(lines[1].split('\t'), ['T-0002', 'open', 'high', 'Other', '']);
  const report = JSON.parse(run(['scripts/weekly-report.js', '--data', file, '--json']));
  assert.equal(report.total, 2);
  assert.equal(report.byStatus.open, 2);
  assert.equal(report.byPriority.high, 2);
});
