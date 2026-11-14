'use strict';

const { test } = require('node:test');
const assert = require('node:assert/strict');
const { AuditLog } = require('../src/audit');

const entry = (ticket, action = 'ticket.updated') => ({
  ticket,
  action,
  actor: 'dana',
  at: '2025-09-01T08:00:00.000Z',
  changes: { priority: { from: 'normal', to: 'high' } },
});

test('entries are numbered in the order they are appended', () => {
  const log = new AuditLog();
  assert.equal(log.append(entry('T-0001')).seq, 1);
  assert.equal(log.append(entry('T-0002')).seq, 2);
  assert.equal(log.size, 2);
});

test('an entry cannot be changed once appended', () => {
  const log = new AuditLog();
  const appended = log.append(entry('T-0001'));
  assert.throws(() => {
    appended.actor = 'someone else';
  }, TypeError);
  assert.throws(() => {
    appended.changes.priority.to = 'low';
  }, TypeError);
  assert.equal(log.forTicket('T-0001')[0].changes.priority.to, 'high');
});

test('a ticket has its own entries, oldest first', () => {
  const log = new AuditLog();
  log.append(entry('T-0001', 'ticket.created'));
  log.append(entry('T-0002', 'ticket.created'));
  log.append(entry('T-0001', 'ticket.transitioned'));
  assert.deepEqual(log.forTicket('T-0001').map((e) => [e.seq, e.action]), [[1, 'ticket.created'], [3, 'ticket.transitioned']]);
});

test('an entry needs its ticket, action, actor and time', () => {
  assert.throws(() => new AuditLog().append({ ...entry('T-0001'), actor: '' }), /needs actor/);
});

test('a saved log comes back as it was', () => {
  const log = new AuditLog();
  log.append(entry('T-0001'));
  const again = new AuditLog(JSON.parse(JSON.stringify(log.toJSON())));
  assert.deepEqual(again.toJSON(), log.toJSON());
  assert.equal(again.append(entry('T-0003')).seq, 2);
});
