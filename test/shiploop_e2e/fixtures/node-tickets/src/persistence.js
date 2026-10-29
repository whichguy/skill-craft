'use strict';

const fs = require('node:fs');
const path = require('node:path');
const { STATES } = require('./outbox');
const { parseId } = require('./tickets/ids');
const { isPriority } = require('./tickets/priorities');
const { isStatus } = require('./tickets/states');

/**
 * The data file (docs/decisions/0008-json-data-file.md): the store's whole state as one JSON document,
 *
 *   { "version": 1, "savedAt": "...", "nextNumber": 8, "tickets": [...], "audit": [...],
 *     "outbox": { "nextId": 5, "events": [...] } }
 *
 * written after every change to a temporary file that then replaces the old one, so a crash leaves the old state or the
 * new one, never a mix of the two.
 *
 * Saving and loading go through the record functions below, which name every field the file keeps. Loading checks each
 * record, so a file edited by hand cannot put the service into a state it could not reach by itself; a file that fails
 * a check is refused with the reason, and the service does not start.
 */

const VERSION = 1;

class DataFileError extends Error {
  constructor(file, message) {
    super(`${file}: ${message}`);
    this.name = 'DataFileError';
  }
}

/** Load and save the state in `file`. */
function createPersistence(file, { clock = { now: () => new Date() } } = {}) {
  return {
    file,

    /** The saved state, or null when the file does not exist yet (the first start). */
    load() {
      let text;
      try {
        text = fs.readFileSync(file, 'utf8');
      } catch (error) {
        if (error.code === 'ENOENT') return null;
        throw new DataFileError(file, `cannot be read: ${error.message}`);
      }
      let document;
      try {
        document = JSON.parse(text);
      } catch {
        throw new DataFileError(file, 'is not JSON');
      }
      return fromDocument(document, (message) => new DataFileError(file, message));
    },

    save(state) {
      const document = toDocument(state, clock.now());
      fs.mkdirSync(path.dirname(path.resolve(file)), { recursive: true });
      const temporary = `${file}.${process.pid}.tmp`;
      fs.writeFileSync(temporary, `${JSON.stringify(document, null, 2)}\n`);
      fs.renameSync(temporary, file);
    },
  };
}

function toDocument(state, now) {
  return {
    version: VERSION,
    savedAt: now.toISOString(),
    nextNumber: state.nextNumber,
    tickets: state.tickets.map(ticketRecord),
    audit: state.audit.map(auditRecord),
    outbox: { nextId: state.outbox.nextId, events: state.outbox.events.map(eventRecord) },
  };
}

function fromDocument(document, fail) {
  if (!isObject(document)) throw fail('is not a data file');
  if (document.version !== VERSION) throw fail(`has version ${document.version}; this service reads version ${VERSION}`);
  const nextNumber = positive(document.nextNumber, 'nextNumber', fail);
  const tickets = array(document.tickets, 'tickets', fail).map((record, index) => readTicket(record, `tickets[${index}]`, fail));
  const ids = new Set();
  for (const ticket of tickets) {
    if (ids.has(ticket.id)) throw fail(`ticket ${ticket.id} appears twice`);
    ids.add(ticket.id);
    if (parseId(ticket.id) >= nextNumber) throw fail(`nextNumber ${nextNumber} would reuse the number of ${ticket.id}`);
  }
  const audit = array(document.audit, 'audit', fail).map((record, index) => readAudit(record, index, fail));
  const outbox = object(document.outbox, 'outbox', fail);
  const events = array(outbox.events, 'outbox.events', fail).map((record, index) => readEvent(record, `outbox.events[${index}]`, fail));
  const nextId = positive(outbox.nextId, 'outbox.nextId', fail);
  if (events.some((event) => event.id >= nextId)) throw fail(`outbox.nextId ${nextId} would reuse an event id`);
  return { nextNumber, tickets, audit, outbox: { nextId, events } };
}

// Records: the fields the file keeps, one function per kind, used to save and to load.

function ticketRecord(ticket) {
  return {
    id: ticket.id,
    title: ticket.title,
    priority: ticket.priority,
    requester: ticket.requester,
    status: ticket.status,
    created: ticket.created,
    updated: ticket.updated,
  };
}

function auditRecord(entry) {
  return {
    seq: entry.seq,
    ticket: entry.ticket,
    action: entry.action,
    actor: entry.actor,
    at: entry.at,
    changes: entry.changes,
  };
}

function eventRecord(event) {
  return {
    id: event.id,
    key: event.key,
    type: event.type,
    to: event.to,
    ticket: event.ticket,
    data: event.data,
    status: event.status,
    attempts: event.attempts,
    created: event.created,
    nextAttemptAt: event.nextAttemptAt,
    lastError: event.lastError,
    sentAt: event.sentAt,
  };
}

function readTicket(record, where, fail) {
  const ticket = ticketRecord(object(record, where, fail));
  if (parseId(ticket.id) === null) throw fail(`${where}.id is not a ticket id`);
  text(ticket.title, `${where}.title`, fail);
  text(ticket.requester, `${where}.requester`, fail);
  if (!isPriority(ticket.priority)) throw fail(`${where}.priority is not a priority`);
  if (!isStatus(ticket.status)) throw fail(`${where}.status is not a status`);
  time(ticket.created, `${where}.created`, fail);
  time(ticket.updated, `${where}.updated`, fail);
  return ticket;
}

function readAudit(record, index, fail) {
  const where = `audit[${index}]`;
  const entry = auditRecord(object(record, where, fail));
  if (entry.seq !== index + 1) throw fail(`${where}.seq is ${entry.seq}, not ${index + 1}: the log is append-only`);
  for (const field of ['ticket', 'action', 'actor']) text(entry[field], `${where}.${field}`, fail);
  time(entry.at, `${where}.at`, fail);
  if (!isObject(entry.changes)) throw fail(`${where}.changes is not an object`);
  for (const [field, change] of Object.entries(entry.changes)) {
    if (!isObject(change) || !('from' in change) || !('to' in change)) throw fail(`${where}.changes.${field} needs from and to`);
  }
  return entry;
}

function readEvent(record, where, fail) {
  const event = eventRecord(object(record, where, fail));
  positive(event.id, `${where}.id`, fail);
  for (const field of ['key', 'type', 'to']) text(event[field], `${where}.${field}`, fail);
  if (!STATES.includes(event.status)) throw fail(`${where}.status is not one of ${STATES.join(', ')}`);
  if (!Number.isInteger(event.attempts) || event.attempts < 0) throw fail(`${where}.attempts is not a count`);
  if (!isObject(event.data)) throw fail(`${where}.data is not an object`);
  time(event.created, `${where}.created`, fail);
  if (event.status === 'pending') time(event.nextAttemptAt, `${where}.nextAttemptAt`, fail);
  return event;
}

// Checks

function isObject(value) {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}

function object(value, where, fail) {
  if (!isObject(value)) throw fail(`${where} is not an object`);
  return value;
}

function array(value, where, fail) {
  if (!Array.isArray(value)) throw fail(`${where} is not a list`);
  return value;
}

function positive(value, where, fail) {
  if (!Number.isSafeInteger(value) || value < 1) throw fail(`${where} is not a positive whole number`);
  return value;
}

function text(value, where, fail) {
  if (typeof value !== 'string' || value === '') throw fail(`${where} is not a non-empty string`);
  return value;
}

function time(value, where, fail) {
  if (typeof value !== 'string' || Number.isNaN(Date.parse(value))) throw fail(`${where} is not a time`);
  return value;
}

module.exports = { DataFileError, VERSION, createPersistence, fromDocument, toDocument };
