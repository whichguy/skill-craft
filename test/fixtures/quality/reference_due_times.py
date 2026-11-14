#!/usr/bin/env python3
"""The reference delivery of the `ticket-due-times` case, for calibrating its held-out probe
(test/shiploop_e2e/checks/due_times_probe.py) and the base's pristine tests (checks/base_tests.py pristine).

    python3 reference_due_times.py DEST [--variant NAME]

writes a delivery into the empty folder DEST: the case's base (test/shiploop_e2e/fixtures/node-tickets) with a variant's edits
applied. The variants:

* ``base``: the base alone, as the run starts. It must fail the probe's fail-to-pass modes (migrate, restart, switch) and pass
  its pass-to-pass ones (rollback, flag-off, cli) and its pristine tests.
* ``reference``: the base extended as the case's prompt asks (REFERENCE). The data file stays format version 1 and gains an
  optional `due` on each ticket, which 1.4.0 ignores when it loads (its record functions keep only the fields they know), so
  1.4.0 still starts on the file; a ticket loaded without one is given its creation time plus its priority's hours when the
  store opens, whether or not due times are on, so the file holds them before they are switched on; a new ticket gets its due
  time when it is created; a priority change leaves it. RESPONSE_HOURS (``urgent=2,high=8``; a priority it leaves out keeps
  4, 24, 72 or 168) sets the hours. Until DUE_TIMES is ``on`` the API hides `due` and ignores ``overdue`` as 1.4.0 ignores an
  unknown parameter.
* each name of DEFECTS: the reference with one targeted change, each a request sentence or a latent fact broken.

Each edit is (path, old, new): ``old`` must occur exactly once in its file, so an edit that no longer applies fails loudly
instead of building something else. ADDED files are written whole. The layout follows reference_ticket_assignment.py.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import shutil

BASE = Path(__file__).resolve().parents[2] / "shiploop_e2e" / "fixtures" / "node-tickets"

DUE_MODULE = r"""'use strict';

/**
 * Due times: a ticket is due its creation time plus the response time of its priority, in hours. The hours come from
 * RESPONSE_HOURS (src/config.js); a priority it leaves out keeps its default.
 */

const { PRIORITIES } = require('./priorities');

const DEFAULT_HOURS = Object.freeze({ urgent: 4, high: 24, normal: 72, low: 168 });
const HOUR_MS = 60 * 60 * 1000;

/** The due time, as an ISO 8601 string, of a ticket created at `created` (ISO 8601) with `priority`. */
function dueFrom(created, priority, hours = DEFAULT_HOURS) {
  return new Date(Date.parse(created) + hours[priority] * HOUR_MS).toISOString();
}

/** Whether `ticket` is open or in progress and its due time has passed at `now` (a Date). */
function isOverdue(ticket, now) {
  return (ticket.status === 'open' || ticket.status === 'in_progress') && Date.parse(ticket.due) < now.getTime();
}

/** The hours of `text` ("urgent=2,high=8"), each priority it leaves out at its default; null when a part is not one. */
function parseHours(text) {
  const hours = { ...DEFAULT_HOURS };
  for (const part of text.split(',').map((piece) => piece.trim()).filter(Boolean)) {
    const match = /^([a-z]+)=(\d+)$/.exec(part);
    if (!match || !PRIORITIES.includes(match[1]) || Number(match[2]) < 1) return null;
    hours[match[1]] = Number(match[2]);
  }
  return Object.freeze(hours);
}

module.exports = { DEFAULT_HOURS, dueFrom, isOverdue, parseHours };
"""

REFERENCE = [
    # The settings: DUE_TIMES switches due times on; RESPONSE_HOURS sets the hours.
    ("src/config.js", "class ConfigError extends Error {",
     "const { DEFAULT_HOURS, parseHours } = require('./tickets/due');\n\nclass ConfigError extends Error {"),
    ("src/config.js", "    logRequests: env.LOG_REQUESTS === '1',\n",
     "    logRequests: env.LOG_REQUESTS === '1',\n"
     "    dueTimes: env.DUE_TIMES === 'on',\n"
     "    responseHours: responseHours(env),\n"),
    ("src/config.js", "/** The settings read from `env`.",
     "/** RESPONSE_HOURS: the hours per priority, the defaults when unset or empty. */\n"
     "function responseHours(env) {\n"
     "  const text = (env.RESPONSE_HOURS ?? '').trim();\n"
     "  if (text === '') return DEFAULT_HOURS;\n"
     "  const hours = parseHours(text);\n"
     "  if (!hours) throw new ConfigError(`RESPONSE_HOURS must be priority=hours pairs, such as urgent=2,high=8, not ${JSON.stringify(text)}`);\n"
     "  return hours;\n"
     "}\n\n"
     "/** The settings read from `env`."),
    # The data file keeps `due`; version 1 stays, so 1.4.0 (which reads only version 1 and drops fields it does not know) starts on it.
    ("src/persistence.js", "    created: ticket.created,\n    updated: ticket.updated,\n  };\n}",
     "    created: ticket.created,\n    updated: ticket.updated,\n    ...(ticket.due === undefined ? {} : { due: ticket.due }),\n  };\n}"),
    ("src/persistence.js", "  time(ticket.updated, `${where}.updated`, fail);\n  return ticket;",
     "  time(ticket.updated, `${where}.updated`, fail);\n  if (ticket.due !== undefined) time(ticket.due, `${where}.due`, fail);\n  return ticket;"),
    # The store gives every ticket its due time: loaded ones without one when it opens, new ones when they are created.
    ("src/store.js", "const { canTransition, isFinal, nextStatuses } = require('./tickets/states');",
     "const { canTransition, isFinal, nextStatuses } = require('./tickets/states');\n"
     "const { DEFAULT_HOURS, dueFrom, isOverdue } = require('./tickets/due');"),
    ("src/store.js", "  constructor({ clock, persistence = null, state = null }) {",
     "  constructor({ clock, persistence = null, state = null, hours = DEFAULT_HOURS }) {"),
    ("src/store.js", "    this.outbox = new Outbox(initial.outbox);\n  }",
     "    this.outbox = new Outbox(initial.outbox);\n"
     "    this.hours = hours;\n"
     "    // Tickets saved before due times existed get theirs from their creation time and priority, once.\n"
     "    for (const ticket of this.tickets.values()) {\n"
     "      if (ticket.due === undefined) ticket.due = dueFrom(ticket.created, ticket.priority, hours);\n"
     "    }\n"
     "  }"),
    ("src/store.js", "  static open({ clock, persistence = null }) {\n"
                     "    return new TicketStore({ clock, persistence, state: persistence ? persistence.load() : null });",
     "  static open({ clock, persistence = null, hours = DEFAULT_HOURS }) {\n"
     "    return new TicketStore({ clock, persistence, state: persistence ? persistence.load() : null, hours });"),
    ("src/store.js", "  list({ filters = {}, limit = 20, after = null } = {}) {\n"
                     "    if (after !== null && parseId(after) === null) throw new InvalidError('cursor is not one this service issued');\n"
                     "    const matching = [...this.tickets.values()]\n"
                     "      .filter((ticket) => matchesFilters(ticket, filters))",
     "  list({ filters = {}, limit = 20, after = null, overdue = false } = {}) {\n"
     "    if (after !== null && parseId(after) === null) throw new InvalidError('cursor is not one this service issued');\n"
     "    const now = this.clock.now();\n"
     "    const matching = [...this.tickets.values()]\n"
     "      .filter((ticket) => matchesFilters(ticket, filters))\n"
     "      .filter((ticket) => !overdue || isOverdue(ticket, now))"),
    ("src/store.js", "    const ticket = { id: formatId(this.nextNumber), title, priority, requester, status: 'open', created: at, updated: at };",
     "    const ticket = { id: formatId(this.nextNumber), title, priority, requester, status: 'open', created: at, updated: at,\n"
     "      due: dueFrom(at, priority, this.hours) };"),
    # The API: `due` and `overdue=true` only while DUE_TIMES is on; off, it answers as 1.4.0 does.
    ("src/tickets/query.js", "function parseListQuery(params) {",
     "function parseListQuery(params, { dueTimes = false } = {}) {"),
    ("src/tickets/query.js", "  return { filters, limit: parseLimit(params), after: params.has('cursor') ? decodeCursor(params.get('cursor')) : null };",
     "  let overdue = false;\n"
     "  if (dueTimes && params.has('overdue')) {\n"
     "    if (params.get('overdue') !== 'true' && params.get('overdue') !== 'false') throw new InvalidError('overdue must be true or false');\n"
     "    overdue = params.get('overdue') === 'true';\n"
     "  }\n"
     "  // Only an asked-for overdue joins the query, so the query 1.4.0's callers get keeps its shape (test/query.test.js).\n"
     "  return { filters, limit: parseLimit(params), after: params.has('cursor') ? decodeCursor(params.get('cursor')) : null,\n"
     "    ...(overdue ? { overdue } : {}) };"),
    ("src/app.js", "function createApp({ store, maxBodyBytes = 64 * 1024, log, logRequests = false }) {\n"
                   "  const router = new Router();",
     "function createApp({ store, maxBodyBytes = 64 * 1024, log, logRequests = false, dueTimes = false }) {\n"
     "  const router = new Router();\n"
     "  // Until DUE_TIMES is on, a ticket is shown as 1.4.0 shows it.\n"
     "  const show = (ticket) => {\n"
     "    if (dueTimes) return ticket;\n"
     "    const { due, ...shown } = ticket;\n"
     "    return shown;\n"
     "  };"),
    ("src/app.js", "  router.get('/tickets', ({ url }) => ({ status: 200, body: store.list(parseListQuery(url.searchParams)) }));",
     "  router.get('/tickets', ({ url }) => {\n"
     "    const page = store.list(parseListQuery(url.searchParams, { dueTimes }));\n"
     "    return { status: 200, body: { ...page, items: page.items.map(show) } };\n"
     "  });"),
    ("src/app.js", "    return { status: 201, body: store.create(input, actorOf(req)) };",
     "    return { status: 201, body: show(store.create(input, actorOf(req))) };"),
    ("src/app.js", "  router.get('/tickets/:id', ({ params }) => ({ status: 200, body: store.get(params.id) }));",
     "  router.get('/tickets/:id', ({ params }) => ({ status: 200, body: show(store.get(params.id)) }));"),
    ("src/app.js", "    return { status: 200, body: store.update(params.id, patch, actorOf(req)) };",
     "    return { status: 200, body: show(store.update(params.id, patch, actorOf(req))) };"),
    ("src/app.js", "    return { status: 200, body: store.transition(params.id, to, actorOf(req)) };",
     "    return { status: 200, body: show(store.transition(params.id, to, actorOf(req))) };"),
    ("src/server.js", "  const store = TicketStore.open({ clock, persistence });",
     "  const store = TicketStore.open({ clock, persistence, hours: config.responseHours });"),
    ("src/server.js", "  const app = createApp({ store, maxBodyBytes: config.maxBodyBytes, log, logRequests: config.logRequests });",
     "  const app = createApp({ store, maxBodyBytes: config.maxBodyBytes, log, logRequests: config.logRequests,\n"
     "    dueTimes: config.dueTimes === true });"),
]

REFERENCE_ADDED = {"src/tickets/due.js": DUE_MODULE}

DEFECTS = {
    # The format moves to version 2 (and still loads version 1): 1.4.0 refuses the file, and the pristine persistence test sees it.
    "version-two": [
        ("src/persistence.js", "const VERSION = 1;", "const VERSION = 2;"),
        ("src/persistence.js", "  if (document.version !== VERSION) throw",
         "  if (document.version !== VERSION && document.version !== 1) throw"),
    ],
    # A priority change recomputes the due time: "a later change ... of the ticket's priority does not move it".
    "priority-moves-due": [
        ("src/store.js", "    return this.apply(ticket, 'ticket.updated', changes, actor);",
         "    if (changes.priority) ticket.due = dueFrom(ticket.created, changes.priority.to, this.hours);\n"
         "    return this.apply(ticket, 'ticket.updated', changes, actor);"),
    ],
    # The data file does not keep `due` (persistence.js's record function is not told, decision 8): every start recomputes it
    # from the current priority, so a priority change moves it at the next restart.
    "due-not-persisted": [
        ("src/persistence.js", "    ...(ticket.due === undefined ? {} : { due: ticket.due }),\n", ""),
    ],
    # Tickets already in the data file get no due time.
    "no-backfill": [
        ("src/store.js", "      if (ticket.due === undefined) ticket.due = dueFrom(ticket.created, ticket.priority, hours);\n", ""),
    ],
    # `due` is shown whatever DUE_TIMES says.
    "flag-ignored": [
        ("src/app.js", "    if (dueTimes) return ticket;", "    if (dueTimes || true) return ticket;"),
    ],
    # overdue=true keeps every open or in-progress ticket, due or not.
    "overdue-active": [
        ("src/tickets/due.js", "&& Date.parse(ticket.due) < now.getTime();", "&& now.getTime() > 0;"),
    ],
}
VARIANTS = ("base", "reference", *DEFECTS)


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
