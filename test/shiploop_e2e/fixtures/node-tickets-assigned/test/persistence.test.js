'use strict';

const { describe, test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { manualClock } = require('../src/clock');
const { DataFileError, createPersistence } = require('../src/persistence');
const { TicketStore } = require('../src/store');

function folder(t) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'tickets-data-'));
  t.after(() => fs.rmSync(dir, { recursive: true, force: true }));
  return dir;
}

const fields = ({ id, title, priority, requester, status, created, updated }) => ({ id, title, priority, requester, status, created, updated });

function savedStore(file) {
  const clock = manualClock();
  const store = TicketStore.open({ clock, persistence: createPersistence(file, { clock }) });
  store.create({ title: 'VPN drops', requester: 'maria@example.com', priority: 'high' }, 'dana');
  store.create({ title: 'Printer jams', requester: 'li@example.com', priority: 'low' }, 'dana');
  store.transition('T-0001', 'in_progress', 'sam');
  store.recordDelivery(1);
  return store;
}

describe('the data file', () => {
  test('a first start finds no file and starts empty', (t) => {
    assert.equal(createPersistence(path.join(folder(t), 'tickets.json')).load(), null);
  });

  test('every change is saved, and loading gives the same state back', (t) => {
    const file = path.join(folder(t), 'nested', 'tickets.json');
    const saved = JSON.parse(JSON.stringify(savedStore(file).snapshot()));
    const loaded = createPersistence(file).load();
    assert.equal(loaded.nextNumber, saved.nextNumber);
    assert.deepEqual(loaded.tickets.map(fields), saved.tickets.map(fields));
    assert.deepEqual(loaded.audit, saved.audit);
    assert.deepEqual(loaded.outbox, saved.outbox);
    assert.equal(JSON.parse(fs.readFileSync(file, 'utf8')).version, 1);
  });

  test('a restarted store keeps its tickets, history and outbox, and never reuses a number', (t) => {
    const file = path.join(folder(t), 'tickets.json');
    savedStore(file);
    const clock = manualClock();
    const again = TicketStore.open({ clock, persistence: createPersistence(file, { clock }) });
    assert.equal(again.get('T-0001').status, 'in_progress');
    assert.equal(again.history('T-0001').length, 2);
    assert.deepEqual(again.outboxReport().sent.map((event) => event.id), [1]);
    assert.deepEqual(again.outboxReport().pending.map((event) => event.id), [2]);
    assert.equal(again.create({ title: 'New', requester: 'x@example.com', priority: 'normal' }, 'dana').id, 'T-0003');
  });

  test('the file is replaced whole: no temporary file is left behind', (t) => {
    const dir = folder(t);
    savedStore(path.join(dir, 'tickets.json'));
    assert.deepEqual(fs.readdirSync(dir), ['tickets.json']);
  });
});

describe('a file the service cannot use is refused', () => {
  function refused(t, edit, message) {
    const file = path.join(folder(t), 'tickets.json');
    savedStore(file);
    const document = JSON.parse(fs.readFileSync(file, 'utf8'));
    edit(document);
    fs.writeFileSync(file, JSON.stringify(document));
    assert.throws(() => createPersistence(file).load(), (error) => error instanceof DataFileError && message.test(error.message));
  }

  test('a file that is not JSON', (t) => {
    const file = path.join(folder(t), 'tickets.json');
    fs.writeFileSync(file, '{ not json');
    assert.throws(() => createPersistence(file).load(), /is not JSON/);
  });

  test('a version this service does not read', (t) => {
    refused(t, (document) => { document.version = 2; }, /has version 2; this service reads version 1/);
  });

  test('a ticket with a field out of range', (t) => {
    refused(t, (document) => { document.tickets[1].priority = 'critical'; }, /tickets\[1\]\.priority is not a priority/);
  });

  test('a next number that would reuse a ticket number', (t) => {
    refused(t, (document) => { document.nextNumber = 2; }, /would reuse the number of T-0002/);
  });

  test('an audit log with a gap', (t) => {
    refused(t, (document) => { document.audit.splice(1, 1); }, /audit\[1\]\.seq is 3, not 2/);
  });

  test('an outbox event in no known state', (t) => {
    refused(t, (document) => { document.outbox.events[0].status = 'lost'; }, /outbox\.events\[0\]\.status/);
  });
});
