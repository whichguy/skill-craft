'use strict';

const { AuditLog } = require('./audit');
const { ConflictError, InvalidError, NotFoundError } = require('./errors');
const { Outbox } = require('./outbox');
const { paginate } = require('./pagination');
const { compareIds, formatId, parseId } = require('./tickets/ids');
const { matchesFilters } = require('./tickets/query');
const { canTransition, isFinal, nextStatuses } = require('./tickets/states');

/** The fields a new ticket's audit entry lists, from null. */
const CREATED_FIELDS = Object.freeze(['title', 'priority', 'requester', 'status']);

/**
 * The ticket store: the tickets, their audit log and the notification outbox, changed together.
 *
 * Every change to a ticket is a method here (CONTRIBUTING.md, "Changes go through the store"). One call checks the
 * change against the ticket's state, applies it, appends its audit entry, enqueues the notifications it causes and saves
 * the data file, so no change is ever half recorded. Reads return copies: nothing outside the store holds a ticket it
 * could change behind the store's back.
 */
class TicketStore {
  /**
   * @param {object} options
   * @param {{ now(): Date }} options.clock
   * @param {object|null} [options.persistence] saves the state after each change (src/persistence.js); none keeps it in
   *   memory only
   * @param {object|null} [options.state] a saved state to start from; an empty store without one
   */
  constructor({ clock, persistence = null, state = null }) {
    const initial = state || { nextNumber: 1, tickets: [], audit: [], outbox: {} };
    this.clock = clock;
    this.persistence = persistence;
    this.nextNumber = initial.nextNumber;
    this.tickets = new Map(initial.tickets.map((ticket) => [ticket.id, { ...ticket }]));
    this.audit = new AuditLog(initial.audit);
    this.outbox = new Outbox(initial.outbox);
  }

  /** A store holding what `persistence` saved (nothing on a first start), saving back to it. */
  static open({ clock, persistence = null }) {
    return new TicketStore({ clock, persistence, state: persistence ? persistence.load() : null });
  }

  // Reads

  get(id) {
    return { ...this.find(id) };
  }

  /** One page of the tickets that pass `filters`, in id order: { items, next } (docs/api.md, "List tickets"). */
  list({ filters = {}, limit = 20, after = null } = {}) {
    if (after !== null && parseId(after) === null) throw new InvalidError('cursor is not one this service issued');
    const matching = [...this.tickets.values()]
      .filter((ticket) => matchesFilters(ticket, filters))
      .sort((a, b) => compareIds(a.id, b.id));
    const page = paginate(matching, { limit, after, compare: compareIds });
    return { items: page.items.map((ticket) => ({ ...ticket })), next: page.next };
  }

  /** The audit entries of one ticket, oldest first. */
  history(id) {
    this.find(id);
    return this.audit.forTicket(id).map((entry) => ({ ...entry, changes: { ...entry.changes } }));
  }

  /** The outbox by state, for GET /admin/outbox. */
  outboxReport() {
    return this.outbox.byStatus();
  }

  // Changes

  /** Open a new ticket; its requester is told it was received. */
  create({ title, priority, requester }, actor) {
    const at = this.now();
    const ticket = { id: formatId(this.nextNumber), title, priority, requester, status: 'open', created: at, updated: at };
    this.nextNumber += 1;
    this.tickets.set(ticket.id, ticket);
    const changes = Object.fromEntries(CREATED_FIELDS.map((field) => [field, { from: null, to: ticket[field] }]));
    this.audit.append({ ticket: ticket.id, action: 'ticket.created', actor, at, changes });
    this.notify(ticket, 'ticket.created', ticket.requester, at);
    this.save();
    return { ...ticket };
  }

  /** Change a ticket's title or priority. A closed ticket no longer changes. */
  update(id, patch, actor) {
    const ticket = this.find(id);
    if (isFinal(ticket.status)) throw new ConflictError(`ticket ${id} is ${ticket.status} and can no longer change`);
    const changes = {};
    for (const [field, value] of Object.entries(patch)) {
      if (ticket[field] !== value) changes[field] = { from: ticket[field], to: value };
    }
    return this.apply(ticket, 'ticket.updated', changes, actor);
  }

  /** Move a ticket along its lifecycle (src/tickets/states.js); its requester is told when it is resolved. */
  transition(id, to, actor) {
    const ticket = this.find(id);
    if (!canTransition(ticket.status, to)) {
      const next = nextStatuses(ticket.status);
      const hint = next.length ? `it can go to ${next.join(' or ')}` : `${ticket.status} is final`;
      throw new ConflictError(`ticket ${id} cannot go from ${ticket.status} to ${to}: ${hint}`);
    }
    return this.apply(ticket, 'ticket.transitioned', { status: { from: ticket.status, to } }, actor, (at) => {
      if (to === 'resolved') this.notify(ticket, 'ticket.resolved', ticket.requester, at);
    });
  }

  // The worker's side of the outbox

  /** The outbox events due now. */
  dueNotifications() {
    return this.outbox.due(this.clock.now()).map((event) => ({ ...event }));
  }

  /** Record one delivery attempt of event `id`: sent when `error` is null, else failed (tried again later, or dead). */
  recordDelivery(id, error = null) {
    const now = this.clock.now();
    const event = error ? this.outbox.markFailed(id, error, now) : this.outbox.markSent(id, now);
    this.save();
    return { ...event };
  }

  // Internals

  find(id) {
    const ticket = this.tickets.get(id);
    if (!ticket) throw new NotFoundError(`ticket ${id} not found`);
    return ticket;
  }

  now() {
    return this.clock.now().toISOString();
  }

  /**
   * Apply `changes` ({ field: { from, to } }) to `ticket` as one audited change, run `effects(at)` (the notifications
   * the change causes) and save. When nothing changes there is no audit entry and nothing else happens.
   */
  apply(ticket, action, changes, actor, effects = () => {}) {
    if (Object.keys(changes).length === 0) return { ...ticket };
    const at = this.now();
    for (const [field, { to }] of Object.entries(changes)) ticket[field] = to;
    ticket.updated = at;
    this.audit.append({ ticket: ticket.id, action, actor, at, changes });
    effects(at);
    this.save();
    return { ...ticket };
  }

  /**
   * Enqueue notification `type` about `ticket` for `to`. The outbox key, by default the type and the ticket, makes a
   * second notification with the same key wait for the first instead of being queued twice.
   */
  notify(ticket, type, to, at, key = `${type}:${ticket.id}`) {
    return this.outbox.enqueue({ key, type, to, ticket: ticket.id, data: { title: ticket.title } }, new Date(at));
  }

  save() {
    if (this.persistence) this.persistence.save(this.snapshot());
  }

  /** The whole state as plain data, as the data file holds it. */
  snapshot() {
    return {
      nextNumber: this.nextNumber,
      tickets: [...this.tickets.values()].map((ticket) => ({ ...ticket })),
      audit: this.audit.toJSON(),
      outbox: this.outbox.toJSON(),
    };
  }
}

module.exports = { CREATED_FIELDS, TicketStore };
