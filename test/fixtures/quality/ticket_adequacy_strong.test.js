'use strict';

const { describe, test } = require('node:test');
const assert = require('node:assert/strict');
const { execFileSync } = require('node:child_process');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { manualClock } = require('../src/clock');
const { ticketBody, withService } = require('./helpers');

const ROOT = path.resolve(__dirname, '..');
const cliPath = path.join(ROOT, 'bin', 'tickets.js');
const reportPath = path.join(ROOT, 'scripts', 'weekly-report.js');

function error(response, status, code) {
  assert.equal(response.status, status, JSON.stringify(response.body));
  assert.equal(response.body.error.code, code);
  assert.equal(typeof response.body.error.message, 'string');
}

async function withTempDir(fn) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'ticket-assignment-'));
  try {
    return await fn(dir);
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
}

function runCli(args) {
  return execFileSync(process.execPath, [cliPath, ...args], {
    cwd: ROOT,
    encoding: 'utf8',
  });
}

function runWeeklyReport(dataFile) {
  return execFileSync(process.execPath, [reportPath, '--data', dataFile, '--json'], {
    cwd: ROOT,
    encoding: 'utf8',
  });
}

async function collectPages(api, filters) {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(filters)) query.set(key, String(value));
  const pages = [];
  let cursor = null;

  do {
    if (cursor) query.set('cursor', cursor);
    else query.delete('cursor');
    const response = await api.get(`/tickets?${query.toString()}`);
    assert.equal(response.status, 200, JSON.stringify(response.body));
    pages.push(response.body);
    cursor = response.body.next;
  } while (cursor);

  return pages;
}

function flattenPages(pages) {
  return pages.flatMap((page) => page.items);
}

async function waitForOutbox(api, count) {
  const deadline = Date.now() + 2500;
  let report;
  while (Date.now() < deadline) {
    const response = await api.get('/admin/outbox');
    assert.equal(response.status, 200, JSON.stringify(response.body));
    report = response.body;
    if (report.pending.length === 0 && report.sent.length + report.dead.length >= count) return report;
    await new Promise((resolve) => setTimeout(resolve, 10));
  }
  assert.fail(`worker did not finish ${count} notifications: ${JSON.stringify(report)}`);
}

describe('ticket assignee behavior', () => {
  test('validates assignees and allows changes only while open or in progress', async () => {
    await withService({}, async (api) => {
      const open = await api.post('/tickets', ticketBody({ title: 'Open assignment' }));
      assert.equal(open.status, 201);
      assert.equal(open.body.assignee, null);
      assert.equal((await api.get(`/tickets/${open.body.id}`)).body.assignee, null);

      const oneCharacter = await api.put(`/tickets/${open.body.id}/assignee`, { assignee: 'x' });
      assert.equal(oneCharacter.status, 200);
      assert.equal(oneCharacter.body.assignee, 'x');
      const openUnassign = await api.put(`/tickets/${open.body.id}/assignee`, { assignee: null });
      assert.equal(openUnassign.status, 200);
      assert.equal(openUnassign.body.assignee, null);

      const inProgress = await api.post('/tickets', ticketBody({ title: 'In progress assignment' }));
      assert.equal((await api.post(`/tickets/${inProgress.body.id}/transition`, { to: 'in_progress' })).status, 200);
      const sixtyFourCharacters = 'a'.repeat(64);
      const assigned = await api.put(`/tickets/${inProgress.body.id}/assignee`, { assignee: sixtyFourCharacters });
      assert.equal(assigned.status, 200);
      assert.equal(assigned.body.assignee, sixtyFourCharacters);
      const inProgressUnassign = await api.put(`/tickets/${inProgress.body.id}/assignee`, { assignee: null });
      assert.equal(inProgressUnassign.status, 200);
      assert.equal(inProgressUnassign.body.assignee, null);

      for (const body of [
        {},
        { assignee: '' },
        { assignee: 'a'.repeat(65) },
        { assignee: 7 },
        { assignee: false },
        { assignee: [] },
        { assignee: 'valid', extra: true },
      ]) {
        error(await api.put(`/tickets/${open.body.id}/assignee`, body), 400, 'invalid');
      }
      error(await api.put('/tickets/T-9999/assignee', { assignee: 'agent' }), 404, 'not_found');

      const resolved = await api.post('/tickets', ticketBody({ title: 'Resolved assignment' }));
      const resolvedId = resolved.body.id;
      assert.equal((await api.post(`/tickets/${resolvedId}/transition`, { to: 'in_progress' })).status, 200);
      assert.equal((await api.post(`/tickets/${resolvedId}/transition`, { to: 'resolved' })).status, 200);
      error(await api.put(`/tickets/${resolvedId}/assignee`, { assignee: 'agent' }), 409, 'conflict');
      error(await api.put(`/tickets/${resolvedId}/assignee`, { assignee: null }), 409, 'conflict');

      assert.equal((await api.post(`/tickets/${resolvedId}/transition`, { to: 'closed' })).status, 200);
      error(await api.put(`/tickets/${resolvedId}/assignee`, { assignee: 'agent' }), 409, 'conflict');
      error(await api.put(`/tickets/${resolvedId}/assignee`, { assignee: null }), 409, 'conflict');
      error(await api.patch(`/tickets/${resolvedId}`, { title: 'Closed tickets remain final' }), 409, 'conflict');
    });
  });

  test('records actual changes once and makes repeated assignment and unassignment complete no-ops', async () => {
    const clock = manualClock();
    await withService({ clock }, async (api) => {
      const requester = 'requester@example.com';
      const created = await api.post('/tickets', ticketBody({ requester, title: 'Audit assignment' }));
      const id = created.body.id;

      const assigned = await api.put(`/tickets/${id}/assignee`, { assignee: 'agent-a' }, { 'X-Actor': 'alice' });
      assert.equal(assigned.status, 200);
      assert.equal(assigned.body.assignee, 'agent-a');

      const beforeAssignedNoOpHistory = (await api.get(`/tickets/${id}/audit`)).body.items;
      const beforeAssignedNoOpOutbox = (await api.get('/admin/outbox')).body.pending;
      clock.advance(60_000);
      const repeatedAssignment = await api.put(
        `/tickets/${id}/assignee`,
        { assignee: 'agent-a' },
        { 'X-Actor': 'ignored-assignment' },
      );
      assert.equal(repeatedAssignment.status, 200);
      assert.equal(repeatedAssignment.body.updated, assigned.body.updated);
      assert.deepEqual((await api.get(`/tickets/${id}/audit`)).body.items, beforeAssignedNoOpHistory);
      assert.deepEqual((await api.get('/admin/outbox')).body.pending, beforeAssignedNoOpOutbox);

      clock.advance(60_000);
      const reassigned = await api.put(`/tickets/${id}/assignee`, { assignee: 'agent-b' }, { 'X-Actor': 'bob' });
      assert.equal(reassigned.status, 200);
      assert.equal(reassigned.body.assignee, 'agent-b');

      const beforeReassignmentNoOpHistory = (await api.get(`/tickets/${id}/audit`)).body.items;
      const beforeReassignmentNoOpOutbox = (await api.get('/admin/outbox')).body.pending;
      clock.advance(60_000);
      const repeatedReassignment = await api.put(
        `/tickets/${id}/assignee`,
        { assignee: 'agent-b' },
        { 'X-Actor': 'ignored-reassignment' },
      );
      assert.equal(repeatedReassignment.status, 200);
      assert.equal(repeatedReassignment.body.updated, reassigned.body.updated);
      assert.deepEqual((await api.get(`/tickets/${id}/audit`)).body.items, beforeReassignmentNoOpHistory);
      assert.deepEqual((await api.get('/admin/outbox')).body.pending, beforeReassignmentNoOpOutbox);
      const beforeUnassign = (await api.get(`/tickets/${id}/audit`)).body.items;
      assert.deepEqual((await api.get('/admin/outbox')).body.pending.map((event) => event.to).sort(), [
        'agent-a',
        'agent-b',
        requester,
      ]);
      assert.deepEqual((await api.get(`/tickets/${id}/audit`)).body.items, beforeUnassign);

      clock.advance(60_000);
      const unassigned = await api.put(`/tickets/${id}/assignee`, { assignee: null });
      assert.equal(unassigned.status, 200);
      assert.equal(unassigned.body.assignee, null);
      const beforeNullNoOpHistory = (await api.get(`/tickets/${id}/audit`)).body.items;
      const beforeNullNoOpOutbox = (await api.get('/admin/outbox')).body.pending;
      clock.advance(60_000);
      const repeatedUnassign = await api.put(`/tickets/${id}/assignee`, { assignee: null }, { 'X-Actor': 'ignored-unassign' });
      assert.equal(repeatedUnassign.status, 200);
      assert.equal(repeatedUnassign.body.updated, unassigned.body.updated);
      assert.deepEqual((await api.get(`/tickets/${id}/audit`)).body.items, beforeNullNoOpHistory);
      assert.deepEqual((await api.get('/admin/outbox')).body.pending, beforeNullNoOpOutbox);

      const history = (await api.get(`/tickets/${id}/audit`)).body.items;
      const actualAssigneeChanges = history
        .filter((entry) => Object.hasOwn(entry.changes, 'assignee'))
        .map((entry) => ({ change: entry.changes.assignee, actor: entry.actor }))
        .filter(({ change }) => change.from !== change.to);
      assert.deepEqual(actualAssigneeChanges.map(({ change }) => [change.from, change.to]), [
        [null, 'agent-a'],
        ['agent-a', 'agent-b'],
        ['agent-b', null],
      ]);
      assert.deepEqual(actualAssigneeChanges.map(({ actor }) => actor), ['alice', 'bob', 'system']);

      const pending = (await api.get('/admin/outbox')).body.pending;
      const creationEvents = pending.filter((event) => event.type === 'ticket.created');
      assert.equal(creationEvents.length, 1);
      assert.equal(creationEvents[0].to, requester);
      const assignmentEvents = pending.filter((event) => event.type !== 'ticket.created');
      assert.deepEqual(assignmentEvents.map((event) => event.to).sort(), ['agent-a', 'agent-b']);
      assert.equal(assignmentEvents.some((event) => event.to === requester), false);
    });
  });

  test('combines assignee filters before cursor pagination and keeps the default page size', async () => {
    await withService({}, async (api) => {
      const seeds = [];
      const priorities = ['low', 'normal', 'high', 'urgent'];
      for (let n = 1; n <= 44; n += 1) {
        const priority = priorities[Math.floor((n - 1) / 2) % priorities.length];
        const assignee = n % 2 === 0 ? 'agent-a' : n % 4 === 1 ? 'agent-b' : null;
        const status = n % 7 === 0 ? 'in_progress' : 'open';
        const created = await api.post('/tickets', ticketBody({ priority, title: `Mixed ticket ${n}` }));
        const id = created.body.id;
        if (status === 'in_progress') {
          assert.equal((await api.post(`/tickets/${id}/transition`, { to: status })).status, 200);
        }
        if (assignee !== null) {
          assert.equal((await api.put(`/tickets/${id}/assignee`, { assignee })).status, 200);
        }
        seeds.push({ id, priority, status, assignee });
      }

      const alphaPages = await collectPages(api, { assignee: 'agent-a' });
      assert.deepEqual(alphaPages.map((page) => page.items.length), [20, 2]);
      assert.equal(alphaPages[0].next !== null, true);
      assert.equal(alphaPages[1].next, null);
      assert.deepEqual(flattenPages(alphaPages).map((ticket) => ticket.id), seeds
        .filter((ticket) => ticket.assignee === 'agent-a')
        .map((ticket) => ticket.id));

      const unassignedPages = await collectPages(api, { assignee: '', limit: 100 });
      const unassigned = flattenPages(unassignedPages);
      assert.deepEqual(unassigned.map((ticket) => ticket.id), seeds
        .filter((ticket) => ticket.assignee === null)
        .map((ticket) => ticket.id));
      assert.equal(unassigned.every((ticket) => ticket.assignee === null), true);

      const andPages = await collectPages(api, {
        assignee: 'agent-a',
        priority: 'urgent',
        status: 'open',
        limit: 2,
      });
      const matching = flattenPages(andPages);
      const expected = seeds.filter((ticket) =>
        ticket.assignee === 'agent-a' && ticket.priority === 'urgent' && ticket.status === 'open');
      assert.equal(expected.length, 5);
      assert.deepEqual(andPages.map((page) => page.items.length), [2, 2, 1]);
      assert.deepEqual(matching.map((ticket) => ticket.id), expected.map((ticket) => ticket.id));
      assert.equal(matching.every((ticket) =>
        ticket.assignee === 'agent-a' && ticket.priority === 'urgent' && ticket.status === 'open'), true);
      assert.equal(flattenPages(await collectPages(api, { limit: 100 }))
        .every((ticket) => ticket.assignee === null || typeof ticket.assignee === 'string'), true);
    });
  });

  test('delivers assignment and existing resolution notices through the outbox worker and keeps resolved tickets editable', async () => {
    await withTempDir(async (dir) => {
      const notifyFile = path.join(dir, 'notifications.jsonl');
      await withService({ workerIntervalMs: 10, notifyFile }, async (api) => {
        const requester = 'requester@example.com';
        const created = await api.post('/tickets', ticketBody({ requester, title: 'VPN drops every hour' }));
        const id = created.body.id;
        const assigned = await api.put(`/tickets/${id}/assignee`, { assignee: 'agent-worker@example.com' });
        assert.equal(assigned.status, 200);
        assert.equal((await api.post(`/tickets/${id}/transition`, { to: 'in_progress' })).status, 200);
        assert.equal((await api.post(`/tickets/${id}/transition`, { to: 'resolved' })).status, 200);

        const editedResolved = await api.patch(`/tickets/${id}`, {
          title: 'Edited after resolution',
          priority: 'urgent',
        });
        assert.equal(editedResolved.status, 200);
        assert.equal(editedResolved.body.status, 'resolved');
        assert.equal(editedResolved.body.title, 'Edited after resolution');
        assert.equal(editedResolved.body.priority, 'urgent');

        const outbox = await waitForOutbox(api, 3);
        assert.equal(outbox.pending.length, 0);
        assert.equal(outbox.dead.length, 0);
        assert.equal(outbox.sent.length, 3);

        assert.equal((await api.post(`/tickets/${id}/transition`, { to: 'closed' })).status, 200);
        error(await api.patch(`/tickets/${id}`, { title: 'Closed stays final' }), 409, 'conflict');

        const messages = fs.readFileSync(notifyFile, 'utf8').trim().split('\n').map((line) => JSON.parse(line));
        assert.equal(messages.length, 3);
        const createdMessage = messages.find((message) => message.type === 'ticket.created');
        const resolvedMessage = messages.find((message) => message.type === 'ticket.resolved');
        const agentMessages = messages.filter((message) => message.to === 'agent-worker@example.com');
        assert.equal(createdMessage.to, requester);
        assert.equal(resolvedMessage.to, requester);
        assert.equal(resolvedMessage.subject.includes('Resolved'), true);
        assert.equal(resolvedMessage.body.includes('VPN drops every hour'), true);
        assert.equal(agentMessages.length, 1);
        assert.equal(agentMessages[0].ticket, id);
        assert.equal(typeof agentMessages[0].subject, 'string');
        assert.equal(agentMessages[0].subject.length > 0, true);
        assert.equal(typeof agentMessages[0].body, 'string');
        assert.equal(agentMessages[0].body.length > 0, true);
        assert.equal(agentMessages[0].to === requester, false);
      });
    });
  });

  test('persists assignee, audit, outbox and ticket/event sequences across a restart', async () => {
    await withTempDir(async (dir) => {
      const dataFile = path.join(dir, 'tickets.json');
      let priorPending;
      await withService({ dataFile }, async (api) => {
        const created = await api.post('/tickets', ticketBody({ title: 'Persistent assignment' }));
        assert.equal(created.body.id, 'T-0001');
        const assigned = await api.put(`/tickets/${created.body.id}/assignee`, { assignee: 'agent-persisted' }, {
          'X-Actor': 'persisted-actor',
        });
        assert.equal(assigned.status, 200);
        priorPending = (await api.get('/admin/outbox')).body.pending;
        assert.equal(priorPending.length, 2);
      });

      await withService({ dataFile }, async (api) => {
        const ticket = await api.get('/tickets/T-0001');
        assert.equal(ticket.status, 200);
        assert.equal(ticket.body.assignee, 'agent-persisted');
        const audit = (await api.get('/tickets/T-0001/audit')).body.items;
        const assignment = audit.find((entry) => entry.changes.assignee);
        assert.deepEqual(assignment.changes.assignee, { from: null, to: 'agent-persisted' });
        assert.equal(assignment.actor, 'persisted-actor');
        assert.deepEqual((await api.get('/admin/outbox')).body.pending, priorPending);

        const nextTicket = await api.post('/tickets', ticketBody({ title: 'After restart' }));
        assert.equal(nextTicket.body.id, 'T-0002');
        assert.deepEqual((await api.get('/tickets/T-0002/audit')).body.items.map((entry) => entry.seq), [3]);

        const pending = (await api.get('/admin/outbox')).body.pending;
        const oldEventIds = priorPending.map((event) => event.id);
        const newEventIds = pending.map((event) => event.id);
        assert.equal(newEventIds.length, 3);
        assert.equal(new Set(newEventIds).size, newEventIds.length);
        assert.ok(Math.max(...newEventIds) > Math.max(...oldEventIds));
      });
    });
  });

  test('shows the assignee in normal CLI output without shifting raw columns or changing the weekly report', async () => {
    await withTempDir(async (dir) => {
      const dataFile = path.join(dir, 'tickets.json');
      let assignedId;
      await withService({ dataFile }, async (api) => {
        const assigned = await api.post('/tickets', ticketBody({
          title: 'Assigned VPN ticket',
          priority: 'high',
        }));
        assignedId = assigned.body.id;
        const unassigned = await api.post('/tickets', ticketBody({
          title: 'Unassigned printer ticket',
          priority: 'low',
        }));
        assert.equal(unassigned.body.assignee, null);
      });

      const reportBefore = runWeeklyReport(dataFile);
      await withService({ dataFile }, async (api) => {
        const response = await api.put(`/tickets/${assignedId}/assignee`, { assignee: 'agent-cli' });
        assert.equal(response.status, 200);
      });

      const normal = runCli(['--data', dataFile, 'list']);
      assert.match(normal, /ASSIGNEE/);
      assert.match(normal, /agent-cli/);
      const raw = runCli(['--data', dataFile, 'list', '--raw']).trim().split('\n')[0].split('\t');
      assert.deepEqual(raw.slice(0, 4), [
        assignedId,
        'open',
        'high',
        'Assigned VPN ticket',
      ]);
      assert.equal(runWeeklyReport(dataFile), reportBefore);
    });
  });

  test('loads a legacy version 1 data file without assignee as null in the API and CLI', async () => {
    await withTempDir(async (dir) => {
      const dataFile = path.join(dir, 'tickets.json');
      await withService({ dataFile }, async (api) => {
        const created = await api.post('/tickets', ticketBody({ title: 'Legacy ticket' }));
        assert.equal(created.status, 201);
        assert.equal(created.body.assignee, null);
      });
      const currentCli = runCli(['--data', dataFile, 'list']);

      const legacy = JSON.parse(fs.readFileSync(dataFile, 'utf8'));
      assert.equal(legacy.version, 1);
      for (const ticket of legacy.tickets) delete ticket.assignee;
      fs.writeFileSync(dataFile, JSON.stringify(legacy));

      await withService({ dataFile }, async (api) => {
        const ticket = await api.get('/tickets/T-0001');
        assert.equal(ticket.status, 200);
        assert.equal(ticket.body.assignee, null);
        const listed = await api.get('/tickets');
        assert.equal(listed.body.items[0].assignee, null);
        assert.equal(runCli(['--data', dataFile, 'list']), currentCli);
      });
    });
  });
});
