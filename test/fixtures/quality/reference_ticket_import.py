#!/usr/bin/env python3
"""The reference delivery of the `ticket-import` case, for calibrating its held-out checks
(test/shiploop_e2e/checks/ticket_import_accept.py) and the base's pristine tests (checks/base_tests.py pristine).

    python3 reference_ticket_import.py DEST [--variant NAME]

writes a delivery into the empty folder DEST: the case's base (test/shiploop_e2e/fixtures/node-tickets) with a variant's edits
applied. The variants:

* ``base``: the base alone, as the run starts. It must fail every fail-to-pass check and pass the pass-to-pass ones.
* ``reference``: the base extended as the case's prompt asks (REFERENCE): ``validate.importBatch`` checks the body and every
  item before anything changes, naming the first invalid item by its index; ``TicketStore.importMany`` opens, audits and
  notifies each ticket as ``create`` does and saves the data file once, after the last, because a save rewrites the whole
  file (docs/operations.md), which the prompt does not name; the route reads its body with a limit of its own, since
  MAX_BODY_BYTES (64 KiB by default, a default the base's config test pins) refuses a 5000-ticket body.
* ``alternative``: an independently written delivery (ALTERNATIVE). The store checks each item as it goes and undoes the
  whole import from a snapshot when one is invalid; saves are held while it runs; the route's limit is 64 times
  MAX_BODY_BYTES; the message says "item at index N".
* each name of DEFECTS: the reference with one targeted change, each a request sentence or a latent fact broken. One raises
  the default body limit for every route and edits the base's config test to match, so its own suite passes and only the
  pristine one can see it.

Each edit is (path, old, new): ``old`` must occur exactly once in its file, so an edit that no longer applies fails loudly
instead of building something else.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import shutil

BASE = Path(__file__).resolve().parents[2] / "shiploop_e2e" / "fixtures" / "node-tickets"

CREATE_OLD = """  /** Open a new ticket; its requester is told it was received. */
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
"""

CREATE_NEW = """  /** Open a new ticket; its requester is told it was received. */
  create(input, actor) {
    const at = this.now();
    const ticket = this.open(input, at);
    this.audit.append(createdEntry(ticket, actor, at));
    this.notify(ticket, 'ticket.created', ticket.requester, at);
    this.save();
    return { ...ticket };
  }

  /**
   * Open many tickets at once, in order (POST /tickets/import): each audited and its requester told, as `create` does.
   * The inputs are already checked, so every one is opened. The data file is saved once, after the last: a save
   * rewrites the whole file, and one per ticket would make a large import take minutes.
   */
  importMany(inputs, actor) {
    const at = this.now();
    const imported = inputs.map((input) => {
      const ticket = this.open(input, at);
      this.audit.append(createdEntry(ticket, actor, at));
      this.notify(ticket, 'ticket.created', ticket.requester, at);
      return ticket;
    });
    this.save();
    return imported.map((ticket) => ({ ...ticket }));
  }
"""

OPEN = """  // Internals

  /** A new ticket from checked input, with the next number. The caller audits it, tells its requester and saves. */
  open({ title, priority, requester }, at) {
    const ticket = { id: formatId(this.nextNumber), title, priority, requester, status: 'open', created: at, updated: at };
    this.nextNumber += 1;
    this.tickets.set(ticket.id, ticket);
    return ticket;
  }

  find(id) {"""

CREATED_ENTRY = """const CREATED_FIELDS = Object.freeze(['title', 'priority', 'requester', 'status']);

/** The audit entry of a ticket just opened: each created field, from null. */
function createdEntry(ticket, actor, at) {
  const changes = Object.fromEntries(CREATED_FIELDS.map((field) => [field, { from: null, to: ticket[field] }]));
  return { ticket: ticket.id, action: 'ticket.created', actor, at, changes };
}
"""

IMPORT_BATCH = """/** The most tickets one import takes (POST /tickets/import). */
const IMPORT_LIMIT = 5000;

/** POST /tickets/import: { tickets: [ <what POST /tickets takes>, ... ] }, at most IMPORT_LIMIT, every item checked. */
function importBatch(body) {
  onlyFields(body, ['tickets']);
  if (!Array.isArray(body.tickets)) throw new InvalidError('tickets must be a list');
  if (body.tickets.length > IMPORT_LIMIT) throw new InvalidError(`an import takes at most ${IMPORT_LIMIT} tickets`);
  return body.tickets.map(importItem);
}

/** One import item, checked as POST /tickets checks a body; an invalid one is named by its index (0 for the first). */
function importItem(item, index) {
  try {
    if (item === null || typeof item !== 'object' || Array.isArray(item)) throw new InvalidError('must be an object');
    return newTicket(item);
  } catch (error) {
    if (error instanceof InvalidError) throw new InvalidError(`tickets[${index}]: ${error.message}`);
    throw error;
  }
}

/** PATCH /tickets/:id: { title?, priority? }, at least one of them. */"""

ROUTE = """  router.post('/tickets', async ({ req }) => {
    const input = validate.newTicket(await body(req));
    return { status: 201, body: store.create(input, actorOf(req)) };
  });

  // An import's body holds up to 5000 tickets: far over MAX_BODY_BYTES, which every other route keeps.
  router.post('/tickets/import', async ({ req }) => {
    const inputs = validate.importBatch(await readJson(req, { limit: IMPORT_BODY_BYTES }));
    const tickets = store.importMany(inputs, actorOf(req));
    return { status: 201, body: { created: tickets.length, ids: tickets.map((ticket) => ticket.id) } };
  });"""

REFERENCE = [
    ("src/store.js", "const CREATED_FIELDS = Object.freeze(['title', 'priority', 'requester', 'status']);\n", CREATED_ENTRY),
    ("src/store.js", CREATE_OLD, CREATE_NEW),
    ("src/store.js", "  // Internals\n\n  find(id) {", OPEN),
    ("src/tickets/validate.js", "/** PATCH /tickets/:id: { title?, priority? }, at least one of them. */", IMPORT_BATCH),
    ("src/tickets/validate.js", "module.exports = { LIMITS, newTicket, onlyFields, text, ticketPatch, transition };",
     "module.exports = { IMPORT_LIMIT, LIMITS, importBatch, importItem, newTicket, onlyFields, text, ticketPatch, transition };"),
    ("src/app.js", "const validate = require('./tickets/validate');\n",
     ("const validate = require('./tickets/validate');\n\n"
      "/** The largest import body: IMPORT_LIMIT tickets with the longest title and requester fit. */\n"
      "const IMPORT_BODY_BYTES = 4 * 1024 * 1024;\n")),
    ("src/app.js", """  router.post('/tickets', async ({ req }) => {
    const input = validate.newTicket(await body(req));
    return { status: 201, body: store.create(input, actorOf(req)) };
  });""", ROUTE),
]

ALTERNATIVE = [
    ("src/store.js", "const { AuditLog } = require('./audit');\n",
     "const { AuditLog } = require('./audit');\nconst validate = require('./tickets/validate');\n"),
    ("src/store.js", "  // The worker's side of the outbox\n", """  /**
   * The old tracker's export, { tickets: [...] }: every ticket created as `create` creates one, or none. Saves are held
   * while it runs and made once at the end; an invalid item undoes the whole import from the state before it.
   */
  importAll(body, actor) {
    validate.onlyFields(body, ['tickets']);
    const items = body.tickets;
    if (!Array.isArray(items)) throw new InvalidError('tickets must be an array');
    if (items.length > 5000) throw new InvalidError(`too many tickets: ${items.length}, at most 5000`);
    const before = this.snapshot();
    const persistence = this.persistence;
    this.persistence = null;
    try {
      const made = items.map((item, index) => {
        let input;
        try {
          if (typeof item !== 'object' || item === null || Array.isArray(item)) throw new InvalidError('not an object');
          input = validate.newTicket(item);
        } catch (error) {
          throw new InvalidError(`item at index ${index}: ${error.message}`);
        }
        return this.create(input, actor);
      });
      this.persistence = persistence;
      this.save();
      return made;
    } catch (error) {
      this.persistence = persistence;
      this.restore(before);
      throw error;
    }
  }

  /** Go back to a state `snapshot` returned. */
  restore(state) {
    this.nextNumber = state.nextNumber;
    this.tickets = new Map(state.tickets.map((ticket) => [ticket.id, { ...ticket }]));
    this.audit = new AuditLog(state.audit);
    this.outbox = new Outbox(state.outbox);
  }

  // The worker's side of the outbox
"""),
    ("src/app.js", "  router.get('/tickets/:id', ({ params }) =>", """  // The old tracker's export comes in one body of up to 5000 tickets: 64 times the usual limit.
  router.post('/tickets/import', async ({ req }) => {
    const tickets = store.importAll(await readJson(req, { limit: maxBodyBytes * 64 }), actorOf(req));
    return { status: 201, body: { created: tickets.length, ids: tickets.map((t) => t.id) } };
  });

  router.get('/tickets/:id', ({ params }) =>"""),
]

REFERENCE_ADDED = {
    "test/import.test.js": """'use strict';

const { describe, test } = require('node:test');
const assert = require('node:assert/strict');
const { ticketBody, withService } = require('./helpers');

describe('POST /tickets/import', () => {
  test('creates every ticket in order and answers created and ids', async () => {
    await withService({}, async (api) => {
      const tickets = [ticketBody({ title: 'One' }), ticketBody({ title: 'Two', priority: 'urgent' })];
      const { status, body } = await api.post('/tickets/import', { tickets });
      assert.equal(status, 201);
      assert.deepEqual(body, { created: 2, ids: ['T-0001', 'T-0002'] });
      assert.equal((await api.get('/tickets/T-0002')).body.priority, 'urgent');
      assert.equal((await api.get('/tickets/T-0001/audit')).body.items[0].action, 'ticket.created');
    });
  });

  test('creates none when an item is invalid, and names its index', async () => {
    await withService({}, async (api) => {
      const { status, body } = await api.post('/tickets/import', { tickets: [ticketBody(), ticketBody({ title: '' })] });
      assert.equal(status, 400);
      assert.match(body.error.message, /tickets\\[1\\]/);
      assert.equal((await api.get('/tickets')).body.items.length, 0);
    });
  });
});
""",
}

ALTERNATIVE_ADDED = {
    "test/bulk-import.test.js": """'use strict';

const { test } = require('node:test');
const assert = require('node:assert/strict');
const { ticketBody, withService } = require('./helpers');

test('an import of three tickets numbers them in order', async () => {
  await withService({}, async (api) => {
    const answer = await api.post('/tickets/import', { tickets: [1, 2, 3].map((n) => ticketBody({ title: `Old ${n}` })) });
    assert.equal(answer.status, 201);
    assert.deepEqual(answer.body.ids, ['T-0001', 'T-0002', 'T-0003']);
  });
});

test('an import with a bad item leaves nothing behind', async () => {
  await withService({}, async (api) => {
    const answer = await api.post('/tickets/import', { tickets: [ticketBody(), ticketBody({ priority: 'asap' })] });
    assert.equal(answer.status, 400);
    assert.match(answer.body.error.message, /index 1/);
    assert.deepEqual((await api.get('/admin/outbox')).body.pending, []);
  });
});
""",
}

PER_ITEM = """    const imported = inputs.map((raw, index) => {
      const ticket = this.open(validate.importItem(raw, index), at);"""

DEFECTS = {
    # The import creates each ticket through a path that saves the data file every time: minutes for 5000.
    "save-per-ticket": [("src/store.js", "      return ticket;\n    });\n    this.save();\n    return imported",
                         "      this.save();\n      return ticket;\n    });\n    return imported")],
    # The route reads its body under MAX_BODY_BYTES, so a 5000-ticket body is refused.
    "default-body-limit": [("src/app.js", "await readJson(req, { limit: IMPORT_BODY_BYTES })", "await body(req)")],
    # Every route's default limit goes up, and the base's config test is edited to match: only the pristine suite sees it.
    "global-limit-raised": [
        ("src/config.js", "  maxBodyBytes: 64 * 1024,", "  maxBodyBytes: 4 * 1024 * 1024,"),
        ("src/config.js", "{ min: 1024, max: 1024 * 1024 }", "{ min: 1024, max: 8 * 1024 * 1024 }"),
        ("src/app.js", "await readJson(req, { limit: IMPORT_BODY_BYTES })", "await body(req)"),
        ("test/config.test.js", "    maxBodyBytes: 65536,\n    logRequests: false,", "    maxBodyBytes: 4194304,\n    logRequests: false,"),
    ],
    # Items are checked one by one as they are opened, so the tickets before an invalid one stay.
    "partial-import": [
        ("src/tickets/validate.js", "  return body.tickets.map(importItem);", "  return body.tickets;"),
        ("src/store.js", "const { canTransition, isFinal, nextStatuses } = require('./tickets/states');\n",
         "const { canTransition, isFinal, nextStatuses } = require('./tickets/states');\nconst validate = require('./tickets/validate');\n"),
        ("src/store.js", "    const imported = inputs.map((input) => {\n      const ticket = this.open(input, at);", PER_ITEM),
    ],
    # The message counts items from 1, where the prompt asks for the index (0 for the first).
    "one-based-index": [("src/tickets/validate.js", "`tickets[${index}]: ${error.message}`", "`ticket ${index + 1}: ${error.message}`")],
    # Imported tickets are audited but their requesters are never told.
    "silent-import": [("src/store.js", "      this.notify(ticket, 'ticket.created', ticket.requester, at);\n      return ticket;",
                       "      return ticket;")],
    # Imported tickets tell their requesters but leave no audit entry.
    "unaudited-import": [("src/store.js", "      const ticket = this.open(input, at);\n      this.audit.append(createdEntry(ticket, actor, at));\n",
                          "      const ticket = this.open(input, at);\n")],
    # The import is never saved: it lives in memory until the next change saves it.
    "unsaved-import": [("src/store.js", "    });\n    this.save();\n    return imported", "    });\n    return imported")],
    # An item without a priority gets another default than POST /tickets gives.
    "default-priority-low": [("src/tickets/validate.js", "    return newTicket(item);",
                              "    return { ...newTicket(item), priority: item.priority === undefined ? 'low' : item.priority };")],
    # Fields the endpoint does not take are dropped instead of refused.
    "loose-items": [("src/tickets/validate.js", "    return newTicket(item);",
                     "    return newTicket({ title: item.title, requester: item.requester, priority: item.priority });")],
    # Existing behaviour broken beside the import, one pass-to-pass check each (as ticket-assignment's defects of the same
    # names): a resolved ticket can no longer change, which the base's own tests leave untested.
    "update-rejects-resolved": [("src/store.js", "    if (isFinal(ticket.status)) throw new ConflictError(",
                                 "    if (ticket.status === 'resolved' || isFinal(ticket.status)) throw new ConflictError(")],
    "default-limit-changed": [("src/tickets/query.js", "const DEFAULT_LIMIT = 20;", "const DEFAULT_LIMIT = 50;")],
    "resolved-template-replaced": [("src/templates.js", "  'ticket.resolved': (event) => ({", "  'ticket.reopened': (event) => ({")],
    "audit-not-saved": [("src/persistence.js", "    audit: state.audit.map(auditRecord),\n", "    audit: [],\n")],
    "raw-column-moved": [("src/format.js", "Object.freeze(['id', 'status', 'priority', 'title'])",
                          "Object.freeze(['id', 'priority', 'status', 'title'])")],
    "old-data-refused": [("src/persistence.js", "const VERSION = 1;", "const VERSION = 2;")],
}

EDITS_BASE_TESTS = {"global-limit-raised": "test/config.test.js"}
VARIANTS = ("base", "reference", "alternative", *DEFECTS)


def apply(dest: Path, edits, label: str) -> None:
    """Apply (path, old, new) edits in order; each `old` must occur exactly once in its file at that point."""
    for relative, old, new in edits:
        path = dest / relative
        text = path.read_text()
        if text.count(old) != 1:
            raise ValueError(f"{label}: {old!r} occurs {text.count(old)} times in {relative}, not once")
        path.write_text(text.replace(old, new))


def write(dest: Path, files: dict) -> None:
    for relative, text in files.items():
        (dest / relative).parent.mkdir(parents=True, exist_ok=True)
        (dest / relative).write_text(text)


def build(dest: Path, variant: str = "reference") -> Path:
    """Write the delivery of `variant` into `dest` (created if missing) and return it."""
    if variant not in VARIANTS:
        raise ValueError(f"unknown variant {variant!r}; known: {', '.join(VARIANTS)}")
    dest = Path(dest)
    shutil.copytree(BASE, dest, dirs_exist_ok=True)
    if variant == "base":
        return dest
    if variant == "alternative":
        apply(dest, ALTERNATIVE, "alternative")
        write(dest, ALTERNATIVE_ADDED)
        return dest
    apply(dest, REFERENCE, "reference")
    write(dest, REFERENCE_ADDED)
    apply(dest, DEFECTS.get(variant, ()), f"defect {variant}")
    return dest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("dest", type=Path)
    parser.add_argument("--variant", default="reference", choices=VARIANTS)
    args = parser.parse_args()
    print(build(args.dest, args.variant))


if __name__ == "__main__":
    main()
