'use strict';

const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { manualClock } = require('../src/clock');
const { createPersistence } = require('../src/persistence');
const { TicketStore } = require('../src/store');

const input = { title: 'Printer', priority: 'normal', requester: 'requester' };

test('TC_Comments_Store records ordered comments, audit and notifications', () => {
  const store = new TicketStore({ clock: manualClock() });
  const ticket = store.create(input, 'requester');
  assert.deepEqual(store.get(ticket.id).comments, []);
  store.assign(ticket.id, 'agent', 'operator');
  const first = store.comment(ticket.id, { author: 'guest', body: 'One' }, 'guest');
  const second = store.comment(ticket.id, { author: 'guest', body: 'Two' }, 'guest');
  assert.notEqual(first.id, second.id);
  assert.equal(first.created, second.created);
  assert.deepEqual(store.get(ticket.id).comments, [first, second]);
  const events = store.outboxReport().pending.filter((event) => event.type === 'ticket.commented');
  assert.equal(events.length, 2);
  assert.notEqual(events[0].key, events[1].key);
  assert.deepEqual(events.map((event) => event.to), ['agent', 'agent']);
  assert.equal(store.history(ticket.id).at(-1).actor, 'guest');
  assert.equal(store.history(ticket.id).at(-1).action, 'ticket.commented');
  store.get(ticket.id).comments[0].body = 'changed';
  assert.equal(store.get(ticket.id).comments[0].body, 'One');
  store.transition(ticket.id, 'in_progress', 'operator');
  store.transition(ticket.id, 'resolved', 'operator');
  store.comment(ticket.id, { author: 'agent', body: 'Self' }, 'agent');
  assert.equal(store.outboxReport().pending.filter((event) => event.type === 'ticket.commented').length, 2);
  store.transition(ticket.id, 'closed', 'operator');
  const before = store.snapshot();
  assert.throws(() => store.comment(ticket.id, { author: 'guest', body: 'No' }, 'guest'), { status: 409 });
  assert.deepEqual(store.snapshot(), before);
});

test('TC_Comments_Persist survives reopening and loads old files', (t) => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'ticket-comments-'));
  t.after(() => fs.rmSync(dir, { recursive: true, force: true }));
  const file = path.join(dir, 'tickets.json');
  const clock = manualClock();
  const persistence = createPersistence(file, { clock });
  const store = TicketStore.open({ clock, persistence });
  const ticket = store.create(input, 'requester');
  const first = store.comment(ticket.id, { author: 'guest', body: 'One' }, 'guest');
  const second = store.comment(ticket.id, { author: 'guest', body: 'Two' }, 'guest');
  assert.deepEqual(TicketStore.open({ clock, persistence }).get(ticket.id).comments, [first, second]);
  const document = JSON.parse(fs.readFileSync(file, 'utf8'));
  for (const [field, value] of [['author', 'a'.repeat(65)], ['body', 'x'.repeat(2001)]]) {
    const invalid = structuredClone(document);
    invalid.tickets[0].comments[0][field] = value;
    fs.writeFileSync(file, JSON.stringify(invalid));
    assert.throws(() => TicketStore.open({ clock, persistence }), /length limit/);
  }
  const old = document;
  delete old.tickets[0].comments;
  fs.writeFileSync(file, JSON.stringify(old));
  const restored = TicketStore.open({ clock, persistence });
  assert.deepEqual(restored.get(ticket.id).comments, []);
  assert.equal(restored.get(ticket.id).title, 'Printer');
  assert.equal(restored.history(ticket.id).length, 3);
});

test('TC_Comments_Store (a) audit records cannot mutate stored comment history', () => {
  const store = new TicketStore({ clock: manualClock() });
  const ticket = store.create(input, 'requester');
  const comment = store.comment(ticket.id, { author: 'guest', body: 'Hello' }, 'guest');
  const entry = store.history(ticket.id).at(-1);
  assert.deepEqual(entry.changes.comment, { from: null, to: comment.id });
  assert.equal(store.get(ticket.id).comments[0].body, 'Hello');
});
