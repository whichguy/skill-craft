#!/usr/bin/env python3
"""The reference delivery of the `ticket-assignment` case, for calibrating its held-out checks
(test/shiploop_e2e/checks/ticket_assignment_accept.py) and the base's pristine tests (checks/base_tests.py pristine).

    python3 reference_ticket_assignment.py DEST [--variant NAME]

writes a delivery into the empty folder DEST: the case's base (test/shiploop_e2e/fixtures/node-tickets) with a variant's edits
applied. The variants:

* ``base``: the base alone, as the run starts. It must fail every fail-to-pass check and pass the pass-to-pass ones.
* ``reference``: the base extended as the case's prompt asks (REFERENCE): ``TicketStore.assign`` audits through ``apply``,
  enqueues a notification keyed by ticket and agent, and refuses tickets that are not active with a conflict; the listing's
  filters combine with ``every``, which fixes the base's latent defect (``matchesFilters`` used ``some``, which the prompt
  does not name); the data file keeps the assignee and gives tickets saved before the change a null one; ``list --raw``
  appends the assignee after the four columns the weekly report reads.
* ``alternative``: an independently written delivery (ALTERNATIVE). Tickets get their null assignee when they are read, not
  when they are created; the handler checks the body itself; the notification has another type and a key per change; the
  filter loop returns early; ``list --raw`` is left as it was; the PUT answers ``{id, assignee}`` and not the ticket.
* each name of DEFECTS: the reference with one targeted change, each a request sentence or a latent fact broken. Two break a
  base module and edit the base's tests to match, so their own suite passes and only the pristine one can see them.

Each edit is (path, old, new): ``old`` must occur exactly once in its file, so an edit that no longer applies fails loudly
instead of building something else. ADDED files are written whole.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import shutil

BASE = Path(__file__).resolve().parents[2] / "shiploop_e2e" / "fixtures" / "node-tickets"

ASSIGN_METHOD = r"""  /**
   * Assign a ticket to an agent, or unassign it with null. Only an open or in-progress ticket can be (un)assigned; the
   * agent it is assigned to is told. Assigning the agent it already has changes nothing.
   */
  assign(id, assignee, actor) {
    const ticket = this.find(id);
    if (!isActive(ticket.status)) {
      throw new ConflictError(`ticket ${id} is ${ticket.status}: only open and in-progress tickets can be assigned`);
    }
    if (ticket.assignee === assignee) return { ...ticket };
    const changes = { assignee: { from: ticket.assignee, to: assignee } };
    return this.apply(ticket, 'ticket.assigned', changes, actor, (at) => {
      if (assignee !== null) this.notify(ticket, 'ticket.assigned', assignee, at, `ticket.assigned:${ticket.id}:${assignee}`);
    });
  }

  // The worker's side of the outbox
"""

REFERENCE = [
    ("src/store.js", "const { canTransition, isFinal, nextStatuses } = require('./tickets/states');",
     "const { canTransition, isActive, isFinal, nextStatuses } = require('./tickets/states');"),
    ("src/store.js", "status: 'open', created: at, updated: at };", "status: 'open', assignee: null, created: at, updated: at };"),
    ("src/store.js", "  // The worker's side of the outbox\n", ASSIGN_METHOD),
    ("src/tickets/query.js", "  return { filters, limit: parseLimit(params),",
     "  if (params.has('assignee')) {\n    const assignee = params.get('assignee');\n"
     "    filters.assignee = assignee === '' ? null : assignee;\n  }\n  return { filters, limit: parseLimit(params),"),
    ("src/tickets/query.js", "return given.some(([field, value])", "return given.every(([field, value])"),
    ("src/tickets/validate.js", "const LIMITS = Object.freeze({ title: 200, requester: 64 });",
     "const LIMITS = Object.freeze({ title: 200, requester: 64, assignee: 64 });"),
    ("src/tickets/validate.js", "module.exports = { LIMITS, newTicket,",
     "/** PUT /tickets/:id/assignee: { assignee }, an agent's name, or null to unassign. */\n"
     "function assignment(body) {\n  onlyFields(body, ['assignee']);\n"
     "  if (!Object.hasOwn(body, 'assignee')) throw new InvalidError('assignee is required: an agent, or null to unassign');\n"
     "  return body.assignee === null ? null : text(body, 'assignee', LIMITS.assignee);\n}\n\n"
     "module.exports = { LIMITS, assignment, newTicket,"),
    ("src/app.js", "  router.get('/tickets/:id/audit',",
     "  router.put('/tickets/:id/assignee', async ({ req, params }) => {\n"
     "    const assignee = validate.assignment(await body(req));\n"
     "    return { status: 200, body: store.assign(params.id, assignee, actorOf(req)) };\n  });\n\n"
     "  router.get('/tickets/:id/audit',"),
    ("src/templates.js", "Reply within 7 days to reopen it.`,\n  }),\n",
     "Reply within 7 days to reopen it.`,\n  }),\n  'ticket.assigned': (event) => ({\n"
     "    subject: `[${event.ticket}] Assigned to you`,\n"
     "    body: `Ticket ${event.ticket} \"${event.data.title}\" is now assigned to you.`,\n  }),\n"),
    ("src/persistence.js", "    status: ticket.status,\n    created: ticket.created,",
     "    status: ticket.status,\n    assignee: ticket.assignee ?? null,\n    created: ticket.created,"),
    ("src/persistence.js", "  if (!isStatus(ticket.status)) throw fail(`${where}.status is not a status`);\n",
     "  if (!isStatus(ticket.status)) throw fail(`${where}.status is not a status`);\n"
     "  if (ticket.assignee !== null) text(ticket.assignee, `${where}.assignee`, fail);\n"),
    ("src/format.js", "const RAW_COLUMNS = Object.freeze(['id', 'status', 'priority', 'title']);",
     "const RAW_COLUMNS = Object.freeze(['id', 'status', 'priority', 'title', 'assignee']);"),
    ("src/format.js", "  { title: 'PRIORITY', value: (ticket) => ticket.priority },\n",
     "  { title: 'PRIORITY', value: (ticket) => ticket.priority },\n  { title: 'ASSIGNEE', value: (ticket) => ticket.assignee ?? '-' },\n"),
]

REFERENCE_ADDED = {
    "test/assignment.test.js": r"""'use strict';

const { test } = require('node:test');
const assert = require('node:assert/strict');
const { ticketBody, withService } = require('./helpers');

test('a ticket is assigned, reassigned and unassigned, each change audited with before and after', async () => {
  await withService({}, async (api) => {
    const { body: ticket } = await api.post('/tickets', ticketBody());
    assert.equal(ticket.assignee, null);
    assert.equal((await api.put('/tickets/T-0001/assignee', { assignee: 'dana.k' }, { 'X-Actor': 'lead.ana' })).status, 200);
    assert.equal((await api.put('/tickets/T-0001/assignee', { assignee: 'sam.r' })).body.assignee, 'sam.r');
    assert.equal((await api.put('/tickets/T-0001/assignee', { assignee: null })).body.assignee, null);
    const entries = (await api.get('/tickets/T-0001/audit')).body.items.slice(1);
    assert.deepEqual(entries.map((entry) => [entry.actor, entry.changes.assignee]), [
      ['lead.ana', { from: null, to: 'dana.k' }],
      ['system', { from: 'dana.k', to: 'sam.r' }],
      ['system', { from: 'sam.r', to: null }],
    ]);
  });
});

test('only open and in-progress tickets can be assigned, and errors use the envelope', async () => {
  await withService({}, async (api) => {
    await api.post('/tickets', ticketBody());
    for (const to of ['in_progress', 'resolved']) await api.post('/tickets/T-0001/transition', { to });
    assert.equal((await api.put('/tickets/T-0001/assignee', { assignee: 'dana.k' })).body.error.code, 'conflict');
    assert.equal((await api.put('/tickets/T-0009/assignee', { assignee: 'dana.k' })).status, 404);
    for (const assignee of ['', 'a'.repeat(65), 7]) {
      assert.equal((await api.put('/tickets/T-0001/assignee', { assignee })).body.error.code, 'invalid');
    }
  });
});

test('assigning the agent a ticket already has changes nothing', async () => {
  await withService({}, async (api) => {
    await api.post('/tickets', ticketBody());
    const first = (await api.put('/tickets/T-0001/assignee', { assignee: 'dana.k' })).body;
    const again = (await api.put('/tickets/T-0001/assignee', { assignee: 'dana.k' })).body;
    assert.deepEqual(again, first);
    assert.equal((await api.get('/tickets/T-0001/audit')).body.items.length, 2);
    assert.equal((await api.get('/admin/outbox')).body.pending.filter((event) => event.type === 'ticket.assigned').length, 1);
  });
});

test('each new agent is notified through the outbox', async () => {
  await withService({}, async (api) => {
    await api.post('/tickets', ticketBody());
    await api.put('/tickets/T-0001/assignee', { assignee: 'dana.k' });
    await api.put('/tickets/T-0001/assignee', { assignee: 'sam.r' });
    const assigned = (await api.get('/admin/outbox')).body.pending.filter((event) => event.type === 'ticket.assigned');
    assert.deepEqual(assigned.map((event) => event.to), ['dana.k', 'sam.r']);
  });
});

test('the assignee filter keeps an agent or the unassigned, and every filter must match', async () => {
  await withService({}, async (api) => {
    for (const priority of ['urgent', 'urgent', 'low']) await api.post('/tickets', ticketBody({ priority }));
    await api.put('/tickets/T-0001/assignee', { assignee: 'dana.k' });
    const ids = async (query) => (await api.get(`/tickets?${query}`)).body.items.map((ticket) => ticket.id);
    assert.deepEqual(await ids('assignee=dana.k'), ['T-0001']);
    assert.deepEqual(await ids('assignee='), ['T-0002', 'T-0003']);
    assert.deepEqual(await ids('priority=urgent&assignee='), ['T-0002']);
    assert.deepEqual(await ids('status=open&priority=low'), ['T-0003']);
  });
});
""",
}

ALTERNATIVE = [
    ("src/store.js", "class TicketStore {\n",
     "/** A ticket as the API shows it: one that was never assigned shows a null assignee. */\n"
     "const view = (ticket) => ({ ...ticket, assignee: ticket.assignee ?? null });\n\nclass TicketStore {\n"),
    ("src/store.js", "  get(id) {\n    return { ...this.find(id) };\n", "  get(id) {\n    return view(this.find(id));\n"),
    ("src/store.js", "    const matching = [...this.tickets.values()]\n      .filter(",
     "    const matching = [...this.tickets.values()]\n      .map(view)\n      .filter("),
    ("src/store.js", "return { items: page.items.map((ticket) => ({ ...ticket })), next: page.next };",
     "return { items: page.items, next: page.next };"),
    ("src/store.js", "    this.save();\n    return { ...ticket };\n  }\n\n  /** Change a ticket's title",
     "    this.save();\n    return view(ticket);\n  }\n\n  /** Change a ticket's title"),
    ("src/store.js", "    if (Object.keys(changes).length === 0) return { ...ticket };",
     "    if (Object.keys(changes).length === 0) return view(ticket);"),
    ("src/store.js", "    effects(at);\n    this.save();\n    return { ...ticket };",
     "    effects(at);\n    this.save();\n    return view(ticket);"),
    ("src/store.js", "  // The worker's side of the outbox\n",
     "  /** Set or clear who works on a ticket; the new agent hears about it. Answers { id, assignee }. */\n"
     "  setAssignee(id, agent, actor) {\n    const ticket = this.find(id);\n"
     "    if (ticket.status !== 'open' && ticket.status !== 'in_progress') {\n"
     "      throw new ConflictError(`cannot change the assignee of a ${ticket.status} ticket`);\n    }\n"
     "    const current = ticket.assignee ?? null;\n"
     "    if (current !== agent) {\n"
     "      this.apply(ticket, 'ticket.assignee_changed', { assignee: { from: current, to: agent } }, actor, (at) => {\n"
     "        if (agent) this.notify(ticket, 'ticket.assignee_changed', agent, at, `assignee:${ticket.id}:${agent}:${at}`);\n"
     "      });\n    }\n    return { id: ticket.id, assignee: agent };\n  }\n\n  // The worker's side of the outbox\n"),
    ("src/tickets/query.js", "  return { filters, limit: parseLimit(params),",
     "  if (params.has('assignee')) filters.assignee = params.get('assignee') || null;\n  return { filters, limit: parseLimit(params),"),
    ("src/tickets/query.js",
     "  const given = Object.entries(filters).filter(([, value]) => value !== undefined);\n  if (given.length === 0) return true;\n"
     "  return given.some(([field, value]) => ticket[field] === value);\n",
     "  for (const [field, value] of Object.entries(filters)) {\n"
     "    if (value !== undefined && ticket[field] !== value) return false;\n  }\n  return true;\n"),
    ("src/app.js", "const { AppError, NotFoundError } = require('./errors');",
     "const { AppError, InvalidError, NotFoundError } = require('./errors');"),
    ("src/app.js", "  router.get('/tickets/:id/audit',",
     "  router.put('/tickets/:id/assignee', async ({ req, params }) => {\n    const input = await body(req);\n"
     "    validate.onlyFields(input, ['assignee']);\n    const agent = input.assignee;\n"
     "    if (agent !== null && (typeof agent !== 'string' || agent.length === 0 || agent.length > 64)) {\n"
     "      throw new InvalidError('assignee must be the name of an agent, 1 to 64 characters, or null');\n    }\n"
     "    return { status: 200, body: store.setAssignee(params.id, agent, actorOf(req)) };\n  });\n\n"
     "  router.get('/tickets/:id/audit',"),
    ("src/templates.js", "Reply within 7 days to reopen it.`,\n  }),\n",
     "Reply within 7 days to reopen it.`,\n  }),\n  'ticket.assignee_changed': (event) => ({\n"
     "    subject: `${event.ticket} needs you`,\n    body: `You now work on \"${event.data.title}\" (${event.ticket}).`,\n  }),\n"),
    ("src/persistence.js", "    updated: ticket.updated,\n  };\n}\n\nfunction auditRecord",
     "    updated: ticket.updated,\n    assignee: ticket.assignee ?? null,\n  };\n}\n\nfunction auditRecord"),
    ("src/format.js", "  { title: 'TITLE', value: (ticket) => ticket.title },\n",
     "  { title: 'ASSIGNEE', value: (ticket) => ticket.assignee || 'unassigned' },\n"
     "  { title: 'TITLE', value: (ticket) => ticket.title },\n"),
]

ALTERNATIVE_ADDED = {
    "test/assignee.test.js": r"""'use strict';

const { test } = require('node:test');
const assert = require('node:assert/strict');
const { ticketBody, withService } = require('./helpers');

test('PUT /tickets/:id/assignee sets and clears the agent', async () => {
  await withService({}, async (api) => {
    await api.post('/tickets', ticketBody());
    assert.deepEqual((await api.put('/tickets/T-0001/assignee', { assignee: 'sam.r' })).body, { id: 'T-0001', assignee: 'sam.r' });
    assert.equal((await api.get('/tickets?assignee=sam.r')).body.items.length, 1);
    await api.put('/tickets/T-0001/assignee', { assignee: null });
    assert.equal((await api.get('/tickets/T-0001')).body.assignee, null);
  });
});

test('a closed ticket keeps its agent', async () => {
  await withService({}, async (api) => {
    await api.post('/tickets', ticketBody());
    for (const to of ['in_progress', 'resolved', 'closed']) await api.post('/tickets/T-0001/transition', { to });
    assert.equal((await api.put('/tickets/T-0001/assignee', { assignee: 'sam.r' })).status, 409);
  });
});
""",
}

# The reference's one notification of the agent, as its assign() enqueues it: several defects change or move it.
NOTIFY_AGENT = "this.notify(ticket, 'ticket.assigned', assignee, at, `ticket.assigned:${ticket.id}:${assignee}`)"

DEFECTS = {
    # The base's own listing filter: `some` lists a ticket that matches any filter, the latent defect the prompt does not name.
    "filter-or": [("src/tickets/query.js", "return given.every(([field, value])", "return given.some(([field, value])")],
    # Cursor pages: the assignee filter applied to each page after paging, so pages run short and next outlives the matches.
    "filter-after-page": [
        ("src/store.js", "  list({ filters = {}, limit = 20, after = null } = {}) {\n",
         "  list({ filters: given = {}, limit = 20, after = null } = {}) {\n    const { assignee, ...filters } = given;\n"),
        ("src/store.js", "return { items: page.items.map((ticket) => ({ ...ticket })), next: page.next };",
         "const kept = assignee === undefined ? page.items : page.items.filter((ticket) => ticket.assignee === assignee);\n"
         "    return { items: kept.map((ticket) => ({ ...ticket })), next: page.next };")],
    # The envelope: the new endpoint answers its errors by hand.
    "no-envelope": [("src/app.js", "    const assignee = validate.assignment(await body(req));\n"
                                   "    return { status: 200, body: store.assign(params.id, assignee, actorOf(req)) };\n",
                     "    try {\n      const assignee = validate.assignment(await body(req));\n"
                     "      return { status: 200, body: store.assign(params.id, assignee, actorOf(req)) };\n"
                     "    } catch (error) {\n      return { status: error.status || 500, body: { error: error.message } };\n    }\n")],
    "conflict-as-invalid": [("src/store.js", "      throw new ConflictError(`ticket ${id} is ${ticket.status}: only open",
                             "      throw new InvalidError(`ticket ${id} is ${ticket.status}: only open")],
    "closed-assignable": [("src/store.js", "    if (!isActive(ticket.status)) {\n      throw new ConflictError(`ticket ${id} is",
                           "    if (false) {\n      throw new ConflictError(`ticket ${id} is")],
    # The outbox: the handler sends the notification itself, and the store enqueues none.
    "notify-inline": [
        ("src/store.js", "      if (assignee !== null) " + NOTIFY_AGENT + ";\n",
         ""),
        ("src/server.js", "  const app = createApp({ store, maxBodyBytes",
         "  const app = createApp({ store, notifier, maxBodyBytes"),
        ("src/app.js", "function createApp({ store, maxBodyBytes", "function createApp({ store, notifier, maxBodyBytes"),
        ("src/app.js", "    return { status: 200, body: store.assign(params.id, assignee, actorOf(req)) };\n",
         "    const before = store.get(params.id).assignee;\n    const ticket = store.assign(params.id, assignee, actorOf(req));\n"
         "    if (assignee !== null && assignee !== before) {\n"
         "      notifier.deliver({ id: 0, key: `ticket.assigned:${ticket.id}`, type: 'ticket.assigned', to: assignee, ticket: ticket.id,\n"
         "        data: { title: ticket.title } });\n    }\n    return { status: 200, body: ticket };\n")],
    "notify-no-template": [("src/templates.js", "  'ticket.assigned': (event) => ({", "  'ticket.assignment': (event) => ({")],
    # The outbox key: by ticket alone, so a reassignment while the first notification waits is merged into it.
    "notify-key-per-ticket": [("src/store.js", NOTIFY_AGENT,
                               "this.notify(ticket, 'ticket.assigned', assignee, at)")],
    "notify-requester": [("src/store.js", NOTIFY_AGENT,
                          "this.notify(ticket, 'ticket.assigned', ticket.requester, at, `ticket.assigned:${ticket.id}:${assignee}`)")],
    # The audit log: the assignment written straight onto the ticket, saved and notified, but never audited.
    "audit-bypassed": [("src/store.js", "    return this.apply(ticket, 'ticket.assigned', changes, actor, (at) => {\n"
                                        "      if (assignee !== null) " + NOTIFY_AGENT + ";\n"
                                        "    });\n",
                        "    const at = this.now();\n    ticket.assignee = assignee;\n    ticket.updated = at;\n"
                        "    if (assignee !== null) " + NOTIFY_AGENT + ";\n"
                        "    this.save();\n    return { ...ticket };\n")],
    "actor-ignored": [("src/store.js", "return this.apply(ticket, 'ticket.assigned', changes, actor, (at) => {",
                       "return this.apply(ticket, 'ticket.assigned', changes, 'system', (at) => {")],
    "same-agent-not-noop": [("src/store.js", "    if (ticket.assignee === assignee) return { ...ticket };\n", "")],
    # The data file: the record functions never learn the new field, so a restart loses it.
    "memory-only-assignee": [("src/persistence.js", "    assignee: ticket.assignee ?? null,\n", ""),
                             ("src/persistence.js", "  if (ticket.assignee !== null) text(ticket.assignee, `${where}.assignee`, fail);\n", "")],
    # Files written before the change: refused, or loaded with no assignee at all.
    "old-data-refused": [("src/persistence.js", "  if (ticket.assignee !== null) text(ticket.assignee,",
                          "  if (ticket.assignee !== null || !Object.hasOwn(record, 'assignee')) text(ticket.assignee,")],
    "old-assignee-undefined": [("src/persistence.js", "    assignee: ticket.assignee ?? null,\n", "    assignee: ticket.assignee,\n"),
                               ("src/persistence.js", "  if (ticket.assignee !== null) text(", "  if (ticket.assignee != null) text(")],
    # The weekly report reads list --raw by position: a column put in front of status shifts what it counts.
    "raw-column-inserted": [("src/format.js", "Object.freeze(['id', 'status', 'priority', 'title', 'assignee'])",
                             "Object.freeze(['id', 'assignee', 'status', 'priority', 'title'])")],
    "cli-no-assignee": [("src/format.js", "  { title: 'ASSIGNEE', value: (ticket) => ticket.assignee ?? '-' },\n", "")],
    "no-unassign": [("src/tickets/validate.js", "  return body.assignee === null ? null : text(body, 'assignee', LIMITS.assignee);",
                     "  return text(body, 'assignee', LIMITS.assignee);")],
    "empty-filter-ignored": [("src/tickets/query.js", "  if (params.has('assignee')) {\n", "  if (params.get('assignee')) {\n")],
    "name-limit-off-by-one": [("src/tickets/validate.js", "requester: 64, assignee: 64 });", "requester: 64, assignee: 63 });")],
    "listing-hides-assignee": [("src/store.js", "return { items: page.items.map((ticket) => ({ ...ticket })), next: page.next };",
                                "return { items: page.items.map(({ assignee, ...ticket }) => ticket), next: page.next };")],
    # Four that break what the service already did, each read by a pass-to-pass check. The base's own tests see the last three;
    # nothing in them edits a resolved ticket, so only the held-out check sees the first.
    "update-rejects-resolved": [("src/store.js", "    if (isFinal(ticket.status)) throw new ConflictError(",
                                 "    if (!isActive(ticket.status)) throw new ConflictError(")],
    "default-limit-changed": [("src/tickets/query.js", "const DEFAULT_LIMIT = 20;", "const DEFAULT_LIMIT = 50;")],
    "resolved-template-replaced": [("src/templates.js", "  'ticket.resolved': (event) => ({", "  'ticket.reassigned': (event) => ({")],
    "audit-not-saved": [("src/persistence.js", "    audit: state.audit.map(auditRecord),\n", "    audit: [],\n")],
    # Two that break a base module and edit the base's tests to match: their own suite passes, the pristine one cannot.
    "backoff-linear": [("src/backoff.js", "  return Math.min(max, base * 2 ** (failures - 1));", "  return Math.min(max, base * failures);"),
                       ("test/outbox.test.js", "[1000, 2000, 4000, 8000]", "[1000, 2000, 3000, 4000]"),
                       ("test/outbox.test.js", "assert.equal(delayFor(20), 5 * 60 * 1000);", "assert.equal(delayFor(400), 5 * 60 * 1000);")],
    "validate-renamed": [("src/tickets/validate.js", "function newTicket(body) {", "function ticketInput(body) {"),
                         ("src/tickets/validate.js", "module.exports = { LIMITS, assignment, newTicket,",
                          "module.exports = { LIMITS, assignment, ticketInput,"),
                         ("src/app.js", "validate.newTicket(await body(req))", "validate.ticketInput(await body(req))"),
                         ("test/validate.test.js", "describe('newTicket', () => {", "describe('ticketInput', () => {"),
                         *[("test/validate.test.js", old, old.replace("validate.newTicket(", "validate.ticketInput("))
                           for old in ("assert.deepEqual(validate.newTicket({ title: '  VPN drops ', requester: 'li@example.com' }), {",
                                       "assert.equal(validate.newTicket({ title: 'a', requester: 'b', priority: 'urgent' }).priority",
                                       "invalid(() => validate.newTicket({ title: 'a', requester: 'b', priority: 'critical' })",
                                       "invalid(() => validate.newTicket({ requester: 'b' })",
                                       "invalid(() => validate.newTicket({ title: '   ', requester: 'b' })",
                                       "invalid(() => validate.newTicket({ title: 'x'.repeat(201), requester: 'b' })",
                                       "invalid(() => validate.newTicket({ title: 'one\\ttwo', requester: 'b' })",
                                       "assert.equal(validate.newTicket({ title: 'x'.repeat(200), requester: 'b' }).title.length",
                                       "assert.equal(validate.newTicket({ title: 'a', requester: 'r'.repeat(64) }).requester.length",
                                       "invalid(() => validate.newTicket({ title: 'a', requester: 'r'.repeat(65) })",
                                       "invalid(() => validate.newTicket({ title: 'a', requester: 'b', status: 'closed' })")]],
}
# The defects that edit the base's tests, and the base test files they edit.
EDITS_BASE_TESTS = {"backoff-linear": "test/outbox.test.js", "validate-renamed": "test/validate.test.js"}
VARIANTS = ("base", "reference", "alternative", *DEFECTS)


def apply(dest: Path, edits, label: str) -> None:
    """Apply (path, old, new) edits in order; each `old` must occur exactly once in its file at that point, or exactly `times`
    times for an edit (path, old, new, times) that renames something everywhere in a file."""
    for relative, old, new, *times in edits:
        path = dest / relative
        text = path.read_text()
        expected = times[0] if times else 1
        if text.count(old) != expected:
            raise ValueError(f"{label}: {old!r} occurs {text.count(old)} times in {relative}, not "
                             + ("once" if expected == 1 else f"{expected} times"))
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
