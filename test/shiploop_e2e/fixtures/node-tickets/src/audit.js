'use strict';

/**
 * The audit log: every change to every ticket, in the order it happened (docs/decisions/0007-append-only-audit-log.md).
 *
 * Entries are only ever appended. None is changed or removed, and each is frozen, so a slip in the code fails loudly
 * instead of rewriting history. An entry:
 *
 *   { seq, ticket, action, actor, at, changes: { <field>: { from, to }, ... } }
 *
 * `changes` holds the value before and after for each field the change touched; a created ticket's fields come from
 * null.
 */
class AuditLog {
  constructor(entries = []) {
    this.entries = [];
    for (const entry of entries) this.entries.push(freeze(entry));
  }

  /** Append one entry and return it. `seq` numbers the entries from 1. */
  append({ ticket, action, actor, at, changes = {} }) {
    for (const [name, value] of Object.entries({ ticket, action, actor, at })) {
      if (typeof value !== 'string' || value === '') throw new TypeError(`an audit entry needs ${name}`);
    }
    const entry = freeze({ seq: this.entries.length + 1, ticket, action, actor, at, changes });
    this.entries.push(entry);
    return entry;
  }

  /** The entries of one ticket, oldest first. */
  forTicket(id) {
    return this.entries.filter((entry) => entry.ticket === id);
  }

  get size() {
    return this.entries.length;
  }

  toJSON() {
    return this.entries.map((entry) => ({ ...entry, changes: { ...entry.changes } }));
  }
}

function freeze(entry) {
  const changes = {};
  for (const [field, change] of Object.entries(entry.changes || {})) {
    changes[field] = Object.freeze({ from: change.from, to: change.to });
  }
  return Object.freeze({ ...entry, changes: Object.freeze(changes) });
}

module.exports = { AuditLog };
