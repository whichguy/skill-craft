'use strict';

const { describe, test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawnSync } = require('node:child_process');
const { manualClock } = require('../src/clock');

const FIXTURE = path.resolve(__dirname, '..');
const { ticketBody, withService } = require('./helpers');

function envelope(response, status, code) {
  assert.equal(response.status, status, JSON.stringify(response.body));
  assert.equal(response.body.error.code, code);
  assert.equal(typeof response.body.error.message, 'string');
}

function folder(t) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'ticket-assignee-contract-'));
  t.after(() => fs.rmSync(dir, { recursive: true, force: true }));
  return dir;
}

function runNode(script, args) {
  const result = spawnSync(process.execPath, [path.join(FIXTURE, script), ...args], { encoding: 'utf8' });
  assert.equal(result.status, 0, `${script} failed: ${result.stderr}`);
  return result.stdout;
}

describe('ticket assignment contract (alternative positive control)', () => {
  test('validates assignment payloads, active states, audit values, and no-op behavior', async () => {
    const clock = manualClock();
    await withService({ clock }, async (api) => {
      const { body: created } = await api.post('/tickets', ticketBody());
      assert.equal(created.assignee, null);
      assert.equal((await api.get('/tickets/T-0001')).body.assignee, null);
      assert.equal((await api.get('/tickets')).body.items[0].assignee, null);

      const initialHistory = (await api.get('/tickets/T-0001/audit')).body.items;
      const initialOutbox = (await api.get('/admin/outbox')).body;
      for (const invalid of [
        {},
        { assignee: '' },
        { assignee: 'x'.repeat(65) },
        { assignee: 7 },
        { assignee: false },
        { assignee: null, extra: 'no' },
        [],
      ]) {
        envelope(await api.put('/tickets/T-0001/assignee', invalid), 400, 'invalid');
      }
      envelope(await api.put('/tickets/T-9999/assignee', { assignee: 'lee' }), 404, 'not_found');
      assert.deepEqual((await api.get('/tickets/T-0001/audit')).body.items, initialHistory);
      assert.deepEqual((await api.get('/admin/outbox')).body, initialOutbox);

      const maxName = 'a'.repeat(64);
      clock.advance(1_000);
      const assigned = await api.put('/tickets/T-0001/assignee', { assignee: maxName }, { 'X-Actor': 'rhea' });
      assert.equal(assigned.status, 200);
      assert.equal(assigned.body.assignee, maxName);
      assert.notEqual(assigned.body.updated, created.updated);
      const afterAssign = (await api.get('/tickets/T-0001/audit')).body.items;
      assert.deepEqual(afterAssign.at(-1).changes, { assignee: { from: null, to: maxName } });
      assert.equal(afterAssign.at(-1).action, 'ticket.assigned');
      assert.equal(afterAssign.at(-1).actor, 'rhea');
      assert.equal((await api.get('/tickets/T-0001')).body.assignee, maxName);
      assert.equal((await api.get('/tickets')).body.items[0].assignee, maxName);

      const savedUpdated = assigned.body.updated;
      const savedOutbox = (await api.get('/admin/outbox')).body;
      clock.advance(60_000);
      const repeated = await api.put('/tickets/T-0001/assignee', { assignee: maxName });
      assert.equal(repeated.body.updated, savedUpdated);
      assert.deepEqual((await api.get('/tickets/T-0001/audit')).body.items, afterAssign);
      assert.deepEqual((await api.get('/admin/outbox')).body, savedOutbox);

      const unassigned = await api.put('/tickets/T-0001/assignee', { assignee: null });
      assert.equal(unassigned.body.assignee, null);
      assert.deepEqual((await api.get('/tickets/T-0001/audit')).body.items.at(-1).changes,
        { assignee: { from: maxName, to: null } });
      assert.equal((await api.get('/tickets/T-0001/audit')).body.items.at(-1).actor, 'system');
      assert.deepEqual((await api.get('/admin/outbox')).body, savedOutbox, 'unassigning enqueues no agent notice');
      const afterUnassign = (await api.get('/tickets/T-0001/audit')).body.items;
      const outboxAfterUnassign = (await api.get('/admin/outbox')).body;
      const unchanged = await api.put('/tickets/T-0001/assignee', { assignee: null });
      assert.equal(unchanged.body.updated, unassigned.body.updated);
      assert.deepEqual((await api.get('/tickets/T-0001/audit')).body.items, afterUnassign);
      assert.deepEqual((await api.get('/admin/outbox')).body, outboxAfterUnassign);

      const progress = await api.post('/tickets/T-0001/transition', { to: 'in_progress' });
      assert.equal(progress.body.assignee, null);
      const activeAssignment = await api.put('/tickets/T-0001/assignee', { assignee: 'b' });
      assert.equal(activeAssignment.body.assignee, 'b');
      assert.equal((await api.put('/tickets/T-0001/assignee', { assignee: null })).body.assignee, null);
      await api.post('/tickets/T-0001/transition', { to: 'resolved' });
      envelope(await api.put('/tickets/T-0001/assignee', { assignee: 'b' }), 409, 'conflict');
      const edited = await api.patch('/tickets/T-0001', { title: 'Still editable after resolution' });
      assert.equal(edited.status, 200);
      assert.equal(edited.body.assignee, null);
      await api.post('/tickets/T-0001/transition', { to: 'closed' });
      envelope(await api.put('/tickets/T-0001/assignee', { assignee: null }), 409, 'conflict');
    });
  });

  test('keeps distinct pending agent notices, delivers them through the worker, and preserves the requester resolution message', async () => {
    await withService({}, async (api, service) => {
      const requester = 'reporter@example.com';
      await api.post('/tickets', ticketBody({ requester, title: 'VPN keeps dropping' }));
      await api.put('/tickets/T-0001/assignee', { assignee: 'agent-one' });
      await api.put('/tickets/T-0001/assignee', { assignee: 'agent-two' });
      await api.put('/tickets/T-0001/assignee', { assignee: null });

      const pending = (await api.get('/admin/outbox')).body.pending;
      const assignmentEvents = pending.filter((event) => event.type === 'ticket.assigned');
      assert.deepEqual(assignmentEvents.map((event) => [event.to, event.key]), [
        ['agent-one', 'ticket.assigned:T-0001:agent-one'],
        ['agent-two', 'ticket.assigned:T-0001:agent-two'],
      ]);
      assert.equal(assignmentEvents.some((event) => event.to === requester), false);
      assert.equal(service.worker.running, false);
      service.worker.tick();
      const deliveredAssignments = service.notifier.delivered.filter((message) => message.type === 'ticket.assigned');
      assert.deepEqual(deliveredAssignments.map((message) => [message.to, message.subject]), [
        ['agent-one', '[T-0001] Assigned to you'],
        ['agent-two', '[T-0001] Assigned to you'],
      ]);
      assert.ok(deliveredAssignments.every((message) => message.body.includes('VPN keeps dropping')));

      await api.post('/tickets/T-0001/transition', { to: 'in_progress' });
      await api.post('/tickets/T-0001/transition', { to: 'resolved' });
      assert.equal((await api.patch('/tickets/T-0001', { title: 'Edited after resolution' })).status, 200);
      service.worker.tick();
      const resolvedMessage = service.notifier.delivered.find((message) => message.type === 'ticket.resolved');
      assert.equal(resolvedMessage.to, requester);
      assert.equal(resolvedMessage.subject, '[T-0001] Resolved');
      assert.match(resolvedMessage.body, /VPN keeps dropping/);
      assert.match(resolvedMessage.body, /Reply within 7 days to reopen it\./);
    });
  });

  test('filters assignees before default-size cursor pages and combines assignment with other filters', async () => {
    await withService({}, async (api) => {
      for (let number = 1; number <= 42; number += 1) {
        const priority = number === 42 ? 'urgent' : 'normal';
        const { body } = await api.post('/tickets', ticketBody({ priority }));
        if (number % 2 === 0) await api.put(`/tickets/${body.id}/assignee`, { assignee: 'alex' });
      }

      const ids = (response) => response.body.items.map((ticket) => ticket.id);
      const firstAgentPage = await api.get('/tickets?assignee=alex');
      assert.equal(firstAgentPage.body.items.length, 20);
      assert.deepEqual(ids(firstAgentPage), Array.from({ length: 20 }, (_, index) => `T-${String((index + 1) * 2).padStart(4, '0')}`));
      assert.ok(firstAgentPage.body.next);
      const secondAgentPage = await api.get(`/tickets?assignee=alex&cursor=${encodeURIComponent(firstAgentPage.body.next)}`);
      assert.deepEqual(ids(secondAgentPage), ['T-0042']);
      assert.equal(secondAgentPage.body.next, null);

      const firstUnassignedPage = await api.get('/tickets?assignee=&limit=2');
      assert.deepEqual(ids(firstUnassignedPage), ['T-0001', 'T-0003']);
      const secondUnassignedPage = await api.get(`/tickets?assignee=&limit=2&cursor=${encodeURIComponent(firstUnassignedPage.body.next)}`);
      assert.deepEqual(ids(secondUnassignedPage), ['T-0005', 'T-0007']);
      assert.ok(secondUnassignedPage.body.items.every((ticket) => ticket.assignee === null));

      assert.deepEqual(ids(await api.get('/tickets?assignee=alex&status=open&priority=urgent')), ['T-0042']);
    });
  });

  test('persists assignee history and outbox sequence, keeps legacy v1 defaults, and preserves CLI columns', async (t) => {
    const dir = folder(t);
    const dataFile = path.join(dir, 'tickets.json');
    await withService({ dataFile }, async (api) => {
      await api.post('/tickets', ticketBody({ title: 'Dock station issue' }));
      await api.put('/tickets/T-0001/assignee', { assignee: 'casey' }, { 'X-Actor': 'dana' });
    });

    const humanList = runNode('bin/tickets.js', ['--data', dataFile, 'list']);
    assert.match(humanList, /ASSIGNEE/);
    assert.match(humanList, /casey/);
    const rawLine = runNode('bin/tickets.js', ['--data', dataFile, 'list', '--raw']).split('\n')[0];
    assert.deepEqual(rawLine.split('\t').slice(0, 4), ['T-0001', 'open', 'normal', 'Dock station issue']);
    assert.equal(rawLine.split('\t')[4], 'casey');
    const weekly = JSON.parse(runNode('scripts/weekly-report.js', ['--data', dataFile, '--json']));
    assert.equal(weekly.total, 1);
    assert.equal(weekly.byStatus.open, 1);
    assert.equal(weekly.byPriority.normal, 1);

    const legacyFile = path.join(dir, 'legacy-v1.json');
    const legacy = JSON.parse(fs.readFileSync(dataFile, 'utf8'));
    assert.equal(legacy.version, 1);
    delete legacy.tickets[0].assignee;
    fs.writeFileSync(legacyFile, `${JSON.stringify(legacy, null, 2)}\n`);

    await withService({ dataFile }, async (api) => {
      assert.equal((await api.get('/tickets/T-0001')).body.assignee, 'casey');
      const audit = (await api.get('/tickets/T-0001/audit')).body.items;
      assert.equal(audit.at(-1).seq, 2);
      assert.equal(audit.at(-1).action, 'ticket.assigned');
      assert.equal(audit.at(-1).actor, 'dana');
      assert.deepEqual(audit.at(-1).changes, { assignee: { from: null, to: 'casey' } });
      assert.deepEqual((await api.get('/admin/outbox')).body.pending.map((event) => event.id), [1, 2]);
      const next = await api.post('/tickets', ticketBody({ title: 'Another request' }));
      assert.equal(next.body.id, 'T-0002');
      assert.equal((await api.get('/tickets/T-0002/audit')).body.items[0].seq, 3);
      assert.deepEqual((await api.get('/admin/outbox')).body.pending.map((event) => event.id), [1, 2, 3]);
    });

    await withService({ dataFile: legacyFile }, async (api) => {
      assert.equal((await api.get('/tickets/T-0001')).body.assignee, null);
      assert.equal((await api.get('/tickets')).body.items[0].assignee, null);
      assert.deepEqual((await api.get('/tickets?assignee=')).body.items.map((ticket) => ticket.id), ['T-0001']);
    });
    const legacyHuman = runNode('bin/tickets.js', ['--data', legacyFile, 'list']);
    assert.match(legacyHuman, /ASSIGNEE/);
    assert.match(legacyHuman.split('\n').find((line) => line.includes('T-0001')), /\s-\s/);
    const legacyRaw = runNode('bin/tickets.js', ['--data', legacyFile, 'list', '--raw']).split('\n')[0];
    assert.deepEqual(legacyRaw.split('\t').slice(0, 4), ['T-0001', 'open', 'normal', 'Dock station issue']);
    assert.equal(legacyRaw.split('\t')[4], '');
  });
});
