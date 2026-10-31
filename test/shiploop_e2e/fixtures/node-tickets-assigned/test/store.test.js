'use strict';

const { describe, test } = require('node:test');
const assert = require('node:assert/strict');
const { manualClock } = require('../src/clock');
const { ConflictError, NotFoundError } = require('../src/errors');
const { TicketStore } = require('../src/store');

const input = (overrides = {}) => ({ title: 'Laptop will not boot', requester: 'li@example.com', priority: 'normal', ...overrides });

function store() {
  const clock = manualClock('2025-09-01T08:00:00.000Z');
  return { clock, store: new TicketStore({ clock }) };
}

describe('create', () => {
  test('opens tickets with sequential ids and the time of creation', () => {
    const { store: tickets } = store();
    const first = tickets.create(input(), 'dana');
    const second = tickets.create(input({ priority: 'urgent' }), 'dana');
    const { id, title, priority, requester, status, created, updated } = first;
    assert.deepEqual({ id, title, priority, requester, status, created, updated }, {
      id: 'T-0001',
      title: 'Laptop will not boot',
      priority: 'normal',
      requester: 'li@example.com',
      status: 'open',
      created: '2025-09-01T08:00:00.000Z',
      updated: '2025-09-01T08:00:00.000Z',
    });
    assert.equal(second.id, 'T-0002');
  });

  test('records the creation in the audit log, every field from null', () => {
    const { store: tickets } = store();
    tickets.create(input(), 'dana');
    assert.deepEqual(tickets.history('T-0001'), [{
      seq: 1,
      ticket: 'T-0001',
      action: 'ticket.created',
      actor: 'dana',
      at: '2025-09-01T08:00:00.000Z',
      changes: {
        title: { from: null, to: 'Laptop will not boot' },
        priority: { from: null, to: 'normal' },
        requester: { from: null, to: 'li@example.com' },
        status: { from: null, to: 'open' },
      },
    }]);
  });

  test('tells the requester the ticket was received, through the outbox', () => {
    const { store: tickets } = store();
    tickets.create(input(), 'dana');
    const [event] = tickets.outboxReport().pending;
    assert.equal(event.type, 'ticket.created');
    assert.equal(event.to, 'li@example.com');
    assert.equal(event.ticket, 'T-0001');
    assert.equal(event.key, 'ticket.created:T-0001');
  });
});

describe('update', () => {
  test('changes the fields given, records from and to, and moves updated', () => {
    const { clock, store: tickets } = store();
    tickets.create(input(), 'dana');
    clock.advance(60_000);
    const changed = tickets.update('T-0001', { priority: 'high', title: 'Laptop will not boot' }, 'sam');
    assert.equal(changed.priority, 'high');
    assert.equal(changed.updated, '2025-09-01T08:01:00.000Z');
    const last = tickets.history('T-0001').at(-1);
    assert.equal(last.action, 'ticket.updated');
    assert.equal(last.actor, 'sam');
    assert.deepEqual(last.changes, { priority: { from: 'normal', to: 'high' } }, 'an unchanged title is not a change');
  });

  test('a change that changes nothing leaves no trace', () => {
    const { clock, store: tickets } = store();
    tickets.create(input(), 'dana');
    clock.advance(60_000);
    const same = tickets.update('T-0001', { priority: 'normal' }, 'sam');
    assert.equal(same.updated, '2025-09-01T08:00:00.000Z');
    assert.equal(tickets.history('T-0001').length, 1);
  });

  test('a closed ticket no longer changes', () => {
    const { store: tickets } = store();
    tickets.create(input(), 'dana');
    for (const to of ['in_progress', 'resolved', 'closed']) tickets.transition('T-0001', to, 'dana');
    assert.throws(() => tickets.update('T-0001', { priority: 'low' }, 'dana'), ConflictError);
  });
});

describe('transition', () => {
  test('follows the lifecycle and records each move', () => {
    const { store: tickets } = store();
    tickets.create(input(), 'dana');
    tickets.transition('T-0001', 'in_progress', 'sam');
    tickets.transition('T-0001', 'resolved', 'sam');
    tickets.transition('T-0001', 'open', 'li@example.com');
    const moves = tickets.history('T-0001').slice(1).map((entry) => [entry.actor, entry.changes.status.from, entry.changes.status.to]);
    assert.deepEqual(moves, [['sam', 'open', 'in_progress'], ['sam', 'in_progress', 'resolved'], ['li@example.com', 'resolved', 'open']]);
    assert.equal(tickets.get('T-0001').status, 'open');
  });

  test('a move the lifecycle does not allow is a conflict and changes nothing', () => {
    const { store: tickets } = store();
    tickets.create(input(), 'dana');
    assert.throws(() => tickets.transition('T-0001', 'closed', 'dana'), (error) =>
      error instanceof ConflictError && /cannot go from open to closed: it can go to in_progress/.test(error.message));
    assert.equal(tickets.get('T-0001').status, 'open');
    assert.equal(tickets.history('T-0001').length, 1);
  });

  test('a resolved ticket notifies its requester once while that notification waits', () => {
    const { store: tickets } = store();
    tickets.create(input(), 'dana');
    for (const to of ['in_progress', 'resolved', 'open', 'in_progress', 'resolved']) tickets.transition('T-0001', to, 'dana');
    const resolved = tickets.outboxReport().pending.filter((event) => event.type === 'ticket.resolved');
    assert.equal(resolved.length, 1);
    assert.equal(resolved[0].to, 'li@example.com');
  });
});

describe('reads', () => {
  test('a ticket that does not exist is not found', () => {
    const { store: tickets } = store();
    assert.throws(() => tickets.get('T-0042'), NotFoundError);
    assert.throws(() => tickets.history('T-0042'), NotFoundError);
  });

  test('a ticket read cannot be changed behind the store', () => {
    const { store: tickets } = store();
    tickets.create(input(), 'dana');
    tickets.get('T-0001').status = 'closed';
    tickets.list().items[0].priority = 'low';
    assert.deepEqual([tickets.get('T-0001').status, tickets.get('T-0001').priority], ['open', 'normal']);
  });

  test('the list pages in id order with a single filter', () => {
    const { store: tickets } = store();
    for (const priority of ['low', 'urgent', 'urgent', 'normal', 'urgent']) tickets.create(input({ priority }), 'dana');
    const first = tickets.list({ filters: { priority: 'urgent' }, limit: 2 });
    assert.deepEqual(first.items.map((ticket) => ticket.id), ['T-0002', 'T-0003']);
    const second = tickets.list({ filters: { priority: 'urgent' }, limit: 2, after: 'T-0003' });
    assert.deepEqual(second.items.map((ticket) => ticket.id), ['T-0005']);
    assert.equal(second.next, null);
  });

  test('a saved state carries on where it left off', () => {
    const { clock, store: tickets } = store();
    tickets.create(input(), 'dana');
    tickets.create(input(), 'dana');
    const again = new TicketStore({ clock, state: JSON.parse(JSON.stringify(tickets.snapshot())) });
    assert.equal(again.create(input(), 'dana').id, 'T-0003');
    assert.equal(again.audit.size, 3);
  });
});
