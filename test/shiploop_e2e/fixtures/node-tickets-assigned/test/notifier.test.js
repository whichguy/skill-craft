'use strict';

const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { manualClock } = require('../src/clock');
const { createNotifier } = require('../src/notifier');
const { render } = require('../src/templates');

const created = { id: 3, key: 'ticket.created:T-0007', type: 'ticket.created', to: 'li@example.com', ticket: 'T-0007', data: { title: 'Laptop will not boot' } };

test('a notification is worded by the template of its type', () => {
  const { subject, body } = render(created);
  assert.equal(subject, '[T-0007] We received your request');
  assert.match(body, /"Laptop will not boot" is ticket T-0007/);
  assert.match(render({ ...created, type: 'ticket.resolved' }).subject, /Resolved/);
});

test('a type with no template cannot be delivered', () => {
  assert.throws(() => render({ ...created, type: 'ticket.misfiled' }), /no template for notification type ticket.misfiled/);
});

test('without a file, deliveries are kept in memory', () => {
  const notifier = createNotifier({ clock: manualClock('2025-09-01T08:00:00.000Z') });
  notifier.deliver(created);
  assert.equal(notifier.delivered.length, 1);
  assert.deepEqual(notifier.delivered[0], {
    at: '2025-09-01T08:00:00.000Z',
    id: 3,
    key: 'ticket.created:T-0007',
    type: 'ticket.created',
    to: 'li@example.com',
    ticket: 'T-0007',
    ...render(created),
  });
});

test('with a file, each delivery appends one JSON line', (t) => {
  const folder = fs.mkdtempSync(path.join(os.tmpdir(), 'notifier-'));
  t.after(() => fs.rmSync(folder, { recursive: true, force: true }));
  const file = path.join(folder, 'notifications.jsonl');
  const notifier = createNotifier({ file, clock: manualClock() });
  notifier.deliver(created);
  notifier.deliver({ ...created, id: 4, type: 'ticket.resolved', key: 'ticket.resolved:T-0007' });
  const lines = fs.readFileSync(file, 'utf8').trim().split('\n').map((line) => JSON.parse(line));
  assert.deepEqual(lines.map((line) => [line.id, line.type, line.to]), [[3, 'ticket.created', 'li@example.com'], [4, 'ticket.resolved', 'li@example.com']]);
  assert.equal(notifier.delivered.length, 0);
});
