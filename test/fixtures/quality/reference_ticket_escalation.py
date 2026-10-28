#!/usr/bin/env python3
"""The reference delivery of the `ticket-escalation` case, the follow-on of `ticket-assignment`, for calibrating its held-out
checks (test/shiploop_e2e/checks/ticket_escalation_accept.py), the base's pristine tests and the case's retention checks.

    python3 reference_ticket_escalation.py DEST [--variant NAME]

writes a delivery into the empty folder DEST. A follow-on starts from the first run's delivery, so every variant starts from
ticket-assignment's reference (reference_ticket_assignment.py), which stands in for that run. The variants:

* ``base``: the assignment reference alone, as the follow-on starts. It must fail every fail-to-pass check and pass the
  pass-to-pass ones.
* ``reference``: the follow-on's prompt done (REFERENCE): ``TicketStore.reassign`` moves each ticket through ``assign``, so
  each is audited and notified as one assignment; ``escalateUrgent`` is a job of the worker, and the outbox's own record of an
  escalation (its key, sent or not, saved in the data file) is what keeps a ticket from being escalated twice.
* ``alternative``: an independently written delivery (ALTERNATIVE). The handler finds the agent's tickets through the listing's
  filters and assigns them one by one; the escalation job lives in its own module, finds its tickets through the listing's
  combined filters, and marks each ticket with an audited ``escalatedAt`` that the data file keeps.
* each name of DEFECTS: the reference with one targeted change: a request sentence or a latent fact of the second request
  broken, or something the first run had added lost again. One breaks a base module and edits the base's tests to match, so
  only the pristine tests can see it.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import reference_ticket_assignment as first  # noqa: E402  (the first run's stand-in, and the edit helpers)

REASSIGN_AND_ESCALATE = r"""  /**
   * Move every open or in-progress ticket of agent `from` to agent `to`, each as one assignment (audited, and its new agent
   * told). Answers { moved, ids } with the ids in order.
   */
  reassign(from, to, actor) {
    const ids = [...this.tickets.values()]
      .filter((ticket) => ticket.assignee === from && isActive(ticket.status))
      .map((ticket) => ticket.id)
      .sort(compareIds);
    for (const id of ids) this.assign(id, to, actor);
    return { moved: ids.length, ids };
  }

  /**
   * Tell `oncall` about each open, unassigned, urgent ticket created more than `afterMinutes` minutes ago. Once per ticket:
   * the outbox keeps the escalation, sent or not, and the data file keeps the outbox. Returns the ids escalated now.
   */
  escalateUrgent({ oncall, afterMinutes }) {
    const now = this.clock.now();
    const cutoff = now.getTime() - afterMinutes * 60_000;
    const escalated = [];
    for (const ticket of this.tickets.values()) {
      const key = `ticket.escalated:${ticket.id}`;
      if (ticket.status !== 'open' || ticket.assignee !== null || ticket.priority !== 'urgent') continue;
      if (Date.parse(ticket.created) >= cutoff || this.outbox.hasKey(key)) continue;
      this.notify(ticket, 'ticket.escalated', oncall, now.toISOString(), key);
      escalated.push(ticket.id);
    }
    if (escalated.length) this.save();
    return escalated;
  }

  // The worker's side of the outbox
"""

REFERENCE = [
    ("src/config.js", "  workerIntervalMs: 500,\n", "  workerIntervalMs: 500,\n  escalateAfterMinutes: 60,\n"),
    ("src/config.js", "    logRequests: env.LOG_REQUESTS === '1',\n",
     "    logRequests: env.LOG_REQUESTS === '1',\n    oncall: (env.ONCALL ?? '').trim() || null,\n"
     "    escalateAfterMinutes: wholeNumber(env, 'ESCALATE_AFTER_MINUTES', DEFAULTS.escalateAfterMinutes, { max: 7 * 24 * 60 }),\n"),
    ("src/outbox.js", "  /** The pending events whose next attempt is due",
     "  /** Whether any event, pending, sent or dead, has `key`. */\n  hasKey(key) {\n"
     "    return this.events.some((event) => event.key === key);\n  }\n\n  /** The pending events whose next attempt is due"),
    ("src/store.js", "  // The worker's side of the outbox\n", REASSIGN_AND_ESCALATE),
    ("src/worker.js", "module.exports = { Worker, deliverOutbox };",
     "/** The escalation job: urgent tickets nobody has picked up are brought to the on-call agent, once each. */\n"
     "function escalateUrgent({ store, oncall, afterMinutes }) {\n"
     "  return { name: 'escalate-urgent', run: () => ({ escalated: store.escalateUrgent({ oncall, afterMinutes }).length }) };\n}\n\n"
     "module.exports = { Worker, deliverOutbox, escalateUrgent };"),
    ("src/server.js", "const { Worker, deliverOutbox } = require('./worker');",
     "const { Worker, deliverOutbox, escalateUrgent } = require('./worker');"),
    ("src/server.js",
     "  const worker = new Worker({\n    intervalMs: config.workerIntervalMs,\n    jobs: [deliverOutbox({ store, notifier, log })],\n",
     "  const jobs = [];\n  if (config.oncall) {\n"
     "    jobs.push(escalateUrgent({ store, oncall: config.oncall, afterMinutes: config.escalateAfterMinutes ?? 60 }));\n  }\n"
     "  jobs.push(deliverOutbox({ store, notifier, log }));\n"
     "  const worker = new Worker({\n    intervalMs: config.workerIntervalMs,\n    jobs,\n"),
    ("src/tickets/validate.js", "module.exports = { LIMITS, assignment,",
     "/** POST /tickets/reassign: { from, to }, two different agents. */\nfunction reassignment(body) {\n"
     "  onlyFields(body, ['from', 'to']);\n  const from = text(body, 'from', LIMITS.assignee);\n"
     "  const to = text(body, 'to', LIMITS.assignee);\n"
     "  if (from === to) throw new InvalidError('from and to must be two different agents');\n  return { from, to };\n}\n\n"
     "module.exports = { LIMITS, assignment, reassignment,"),
    ("src/app.js", "  router.get('/tickets/:id/audit',",
     "  router.post('/tickets/reassign', async ({ req }) => {\n    const { from, to } = validate.reassignment(await body(req));\n"
     "    return { status: 200, body: store.reassign(from, to, actorOf(req)) };\n  });\n\n  router.get('/tickets/:id/audit',"),
    ("src/templates.js", "  'ticket.assigned': (event) => ({",
     "  'ticket.escalated': (event) => ({\n    subject: `[${event.ticket}] Urgent and unassigned`,\n"
     "    body: `Ticket ${event.ticket} \"${event.data.title}\" is urgent and nobody has it yet.`,\n  }),\n"
     "  'ticket.assigned': (event) => ({"),
]

REFERENCE_ADDED = {
    "test/escalation.test.js": r"""'use strict';

const { test } = require('node:test');
const assert = require('node:assert/strict');
const { manualClock } = require('../src/clock');
const { TicketStore } = require('../src/store');
const { ticketBody, withService } = require('./helpers');

test('POST /tickets/reassign moves an agent\'s open and in-progress tickets, each audited and notified', async () => {
  await withService({}, async (api) => {
    for (let n = 0; n < 3; n += 1) await api.post('/tickets', ticketBody());
    for (const id of ['T-0001', 'T-0002', 'T-0003']) await api.put(`/tickets/${id}/assignee`, { assignee: 'dana.k' });
    for (const to of ['in_progress', 'resolved']) await api.post('/tickets/T-0002/transition', { to });
    const { status, body } = await api.post('/tickets/reassign', { from: 'dana.k', to: 'lee.m' }, { 'X-Actor': 'lead.ana' });
    assert.equal(status, 200);
    assert.deepEqual(body, { moved: 2, ids: ['T-0001', 'T-0003'] });
    assert.equal((await api.get('/tickets/T-0002')).body.assignee, 'dana.k');
    assert.deepEqual((await api.get('/tickets/T-0001/audit')).body.items.at(-1).changes, { assignee: { from: 'dana.k', to: 'lee.m' } });
    const outbox = (await api.get('/admin/outbox')).body.pending.filter((event) => event.to === 'lee.m');
    assert.deepEqual(outbox.map((event) => event.ticket), ['T-0001', 'T-0003']);
  });
});

test('reassigning to the same agent is invalid', async () => {
  await withService({}, async (api) => {
    const { status, body } = await api.post('/tickets/reassign', { from: 'dana.k', to: 'dana.k' });
    assert.equal(status, 400);
    assert.equal(body.error.code, 'invalid');
  });
});

test('urgent, open, unassigned tickets are escalated once, after the wait', () => {
  const clock = manualClock();
  const store = new TicketStore({ clock });
  store.create({ title: 'Core switch down', requester: 'noc@example.com', priority: 'urgent' }, 'system');
  store.create({ title: 'Mail is slow', requester: 'li@example.com', priority: 'high' }, 'system');
  const escalate = () => store.escalateUrgent({ oncall: 'oncall.lee', afterMinutes: 60 });
  assert.deepEqual(escalate(), [], 'not before the wait');
  clock.advance(61 * 60_000);
  assert.deepEqual(escalate(), ['T-0001']);
  store.recordDelivery(store.outboxReport().pending.find((event) => event.to === 'oncall.lee').id);
  clock.advance(60_000);
  assert.deepEqual(escalate(), [], 'once, even after the first was sent');
});
""",
}

ALTERNATIVE = [
    ("src/config.js", "    logRequests: env.LOG_REQUESTS === '1',\n",
     "    logRequests: env.LOG_REQUESTS === '1',\n"
     "    escalation: { oncall: env.ONCALL || null, afterMs: wholeNumber(env, 'ESCALATE_AFTER_MINUTES', 60) * 60 * 1000 },\n"),
    ("src/store.js", "  // The worker's side of the outbox\n",
     "  /** Mark a ticket escalated to `oncall`, in its own audited change; null when it already was. */\n"
     "  markEscalated(id, oncall) {\n    const ticket = this.find(id);\n    if (ticket.escalatedAt) return null;\n"
     "    return this.apply(ticket, 'ticket.escalated', { escalatedAt: { from: null, to: this.now() } }, 'system', (at) => {\n"
     "      this.notify(ticket, 'ticket.escalated', oncall, at);\n    });\n  }\n\n  // The worker's side of the outbox\n"),
    ("src/persistence.js", "    assignee: ticket.assignee ?? null,\n",
     "    assignee: ticket.assignee ?? null,\n    escalatedAt: ticket.escalatedAt ?? null,\n"),
    ("src/server.js", "const { Worker, deliverOutbox } = require('./worker');",
     "const { Worker, deliverOutbox } = require('./worker');\nconst { escalationJob } = require('./escalation');"),
    ("src/server.js", "    jobs: [deliverOutbox({ store, notifier, log })],\n",
     "    jobs: [\n      ...(config.escalation && config.escalation.oncall ? [escalationJob({ store, ...config.escalation })] : []),\n"
     "      deliverOutbox({ store, notifier, log }),\n    ],\n"),
    ("src/app.js", "  router.get('/tickets/:id/audit',",
     "  router.post('/tickets/reassign', async ({ req }) => {\n    const input = await body(req);\n"
     "    validate.onlyFields(input, ['from', 'to']);\n    const from = validate.text(input, 'from', 64);\n"
     "    const to = validate.text(input, 'to', 64);\n"
     "    if (from === to) throw new InvalidError('from and to name the same agent');\n"
     "    const theirs = [];\n    let after = null;\n    do {\n"
     "      const page = store.list({ filters: { assignee: from }, limit: 100, after });\n"
     "      theirs.push(...page.items);\n      after = page.next ? page.items[page.items.length - 1].id : null;\n    } while (after);\n"
     "    const ids = theirs.filter((ticket) => ticket.status === 'open' || ticket.status === 'in_progress').map((ticket) => ticket.id);\n"
     "    for (const id of ids) store.assign(id, to, actorOf(req));\n"
     "    return { status: 200, body: { moved: ids.length, ids } };\n  });\n\n  router.get('/tickets/:id/audit',"),
    ("src/app.js", "const { AppError, NotFoundError } = require('./errors');",
     "const { AppError, InvalidError, NotFoundError } = require('./errors');"),
    ("src/templates.js", "  'ticket.assigned': (event) => ({",
     "  'ticket.escalated': (event) => ({\n    subject: `ESCALATION ${event.ticket}`,\n"
     "    body: `\"${event.data.title}\" is urgent, open and unassigned. Please pick it up or assign it.`,\n  }),\n"
     "  'ticket.assigned': (event) => ({"),
]

ALTERNATIVE_ADDED = {
    "src/escalation.js": r"""'use strict';

/**
 * Escalation: an urgent ticket that is open and unassigned for longer than the wait is brought to the on-call agent. It is
 * a job of the worker (src/worker.js), so it runs in the background and stops with WORKER_INTERVAL_MS=0.
 */
function escalationJob({ store, oncall, afterMs }) {
  return {
    name: 'escalation',
    run() {
      const cutoff = Date.now() - afterMs;
      const waiting = [];
      let after = null;
      do {
        const page = store.list({ filters: { status: 'open', priority: 'urgent', assignee: null }, limit: 100, after });
        waiting.push(...page.items);
        after = page.next ? page.items[page.items.length - 1].id : null;
      } while (after);
      let escalated = 0;
      for (const ticket of waiting) {
        if (!ticket.escalatedAt && Date.parse(ticket.created) < cutoff && store.markEscalated(ticket.id, oncall)) escalated += 1;
      }
      return { escalated };
    },
  };
}

module.exports = { escalationJob };
""",
    "test/reassign.test.js": r"""'use strict';

const { test } = require('node:test');
const assert = require('node:assert/strict');
const { ticketBody, withService } = require('./helpers');

test('reassign moves only active tickets and answers their ids', async () => {
  await withService({}, async (api) => {
    await api.post('/tickets', ticketBody());
    await api.post('/tickets', ticketBody());
    await api.put('/tickets/T-0001/assignee', { assignee: 'sam.r' });
    await api.put('/tickets/T-0002/assignee', { assignee: 'sam.r' });
    for (const to of ['in_progress', 'resolved', 'closed']) await api.post('/tickets/T-0002/transition', { to });
    assert.deepEqual((await api.post('/tickets/reassign', { from: 'sam.r', to: 'priya.n' })).body, { moved: 1, ids: ['T-0001'] });
  });
});

test('an escalation is marked on the ticket', async () => {
  const { escalationJob } = require('../src/escalation');
  await withService({}, async (api, service) => {
    await api.post('/tickets', ticketBody({ priority: 'urgent' }));
    const job = escalationJob({ store: service.store, oncall: 'oncall.lee', afterMs: -1 });
    assert.deepEqual(job.run(), { escalated: 1 });
    assert.deepEqual(job.run(), { escalated: 0 });
    assert.ok((await api.get('/tickets/T-0001')).body.escalatedAt);
  });
});
""",
}

DEFECTS = {
    # The envelope, and the request's "two different agents".
    "reassign-same-allowed": [("src/tickets/validate.js",
                               "  if (from === to) throw new InvalidError('from and to must be two different agents');\n", "")],
    "reassign-plain-errors": [("src/app.js", "    const { from, to } = validate.reassignment(await body(req));\n"
                                             "    return { status: 200, body: store.reassign(from, to, actorOf(req)) };\n",
                               "    try {\n      const { from, to } = validate.reassignment(await body(req));\n"
                               "      return { status: 200, body: store.reassign(from, to, actorOf(req)) };\n"
                               "    } catch (error) {\n      return { status: 400, body: { error: error.message } };\n    }\n")],
    # The request: only open and in-progress tickets move, and the ids come in order.
    "reassign-moves-resolved": [("src/store.js", ".filter((ticket) => ticket.assignee === from && isActive(ticket.status))",
                                 ".filter((ticket) => ticket.assignee === from)"),
                                ("src/store.js", "    for (const id of ids) this.assign(id, to, actor);\n",
                                 "    for (const id of ids) {\n      const ticket = this.find(id);\n"
                                 "      this.apply(ticket, 'ticket.assigned', { assignee: { from, to } }, actor, (at) => {\n"
                                 "        this.notify(ticket, 'ticket.assigned', to, at, `ticket.assigned:${ticket.id}:${to}`);\n"
                                 "      });\n    }\n")],
    "reassign-unordered": [("src/store.js", "      .sort(compareIds);\n    for (const id of ids)",
                            "      .sort(compareIds)\n      .reverse();\n    for (const id of ids)")],
    # The audit log and the outbox for each moved ticket.
    "reassign-unaudited": [("src/store.js", "    for (const id of ids) this.assign(id, to, actor);\n",
                            "    for (const id of ids) {\n      const ticket = this.find(id);\n      ticket.assignee = to;\n"
                            "      ticket.updated = this.now();\n"
                            "      this.notify(ticket, 'ticket.assigned', to, ticket.updated, `ticket.assigned:${ticket.id}:${to}`);\n    }\n"
                            "    this.save();\n")],
    "reassign-no-notify": [("src/store.js", "    for (const id of ids) this.assign(id, to, actor);\n",
                            "    for (const id of ids) this.apply(this.find(id), 'ticket.assigned', { assignee: { from, to } }, actor);\n")],
    # Background work belongs to the worker: not to a request, and not to a timer of its own.
    "escalation-also-in-request": [
        ("src/server.js", "  const app = createApp({ store, maxBodyBytes",
         "  const escalation = config.oncall ? { oncall: config.oncall, afterMinutes: config.escalateAfterMinutes ?? 60 } : null;\n"
         "  const app = createApp({ store, escalation, maxBodyBytes"),
        ("src/app.js", "function createApp({ store, maxBodyBytes", "function createApp({ store, escalation = null, maxBodyBytes"),
        ("src/app.js", "  router.get('/tickets', ({ url }) => ({ status: 200, body: store.list(parseListQuery(url.searchParams)) }));",
         "  router.get('/tickets', ({ url }) => {\n    if (escalation) store.escalateUrgent(escalation);\n"
         "    return { status: 200, body: store.list(parseListQuery(url.searchParams)) };\n  });")],
    "escalation-own-timer": [
        ("src/server.js", "  if (config.oncall) {\n    jobs.push(escalateUrgent({ store, oncall: config.oncall, "
                          "afterMinutes: config.escalateAfterMinutes ?? 60 }));\n  }\n",
         "  if (config.oncall) {\n    const options = { oncall: config.oncall, afterMinutes: config.escalateAfterMinutes ?? 60 };\n"
         "    setInterval(() => store.escalateUrgent(options), 100).unref();\n  }\n")],
    # At most once, even across restarts: the record of an escalation must be in the data file.
    "escalation-in-memory": [("src/store.js", "      if (Date.parse(ticket.created) >= cutoff || this.outbox.hasKey(key)) continue;\n",
                              "      this.escalated = this.escalated || new Set();\n"
                              "      if (Date.parse(ticket.created) >= cutoff || this.escalated.has(ticket.id)) continue;\n"
                              "      this.escalated.add(ticket.id);\n")],
    "escalation-repeats": [("src/store.js", " || this.outbox.hasKey(key)) continue;", ") continue;")],
    # The request's rule: open, unassigned, urgent, older than ESCALATE_AFTER_MINUTES minutes, and only with ONCALL.
    "escalation-includes-assigned": [("src/store.js", "ticket.status !== 'open' || ticket.assignee !== null || ticket.priority",
                                      "ticket.status !== 'open' || ticket.priority")],
    "escalation-includes-in-progress": [("src/store.js", "if (ticket.status !== 'open' || ticket.assignee !== null",
                                         "if (!isActive(ticket.status) || ticket.assignee !== null")],
    "escalation-minutes-as-seconds": [("src/store.js", "afterMinutes * 60_000;", "afterMinutes * 1000;")],
    "escalation-default-oncall": [("src/config.js", "    oncall: (env.ONCALL ?? '').trim() || null,",
                                   "    oncall: (env.ONCALL ?? '').trim() || 'oncall',")],
    # What the first run added, lost again by the second.
    "filter-or-again": [("src/tickets/query.js", "return given.every(([field, value])", "return given.some(([field, value])")],
    "assignment-notify-dropped": [
        ("src/store.js", "      if (assignee !== null) " + first.NOTIFY_AGENT + ";\n", ""),
        ("src/store.js", "    for (const id of ids) this.assign(id, to, actor);\n",
         "    for (const id of ids) {\n      const ticket = this.assign(id, to, actor);\n"
         "      this.notify(ticket, 'ticket.assigned', to, ticket.updated, `ticket.assigned:${ticket.id}:${to}`);\n    }\n    this.save();\n")],
    "raw-column-moved": [("src/format.js", "Object.freeze(['id', 'status', 'priority', 'title', 'assignee'])",
                          "Object.freeze(['id', 'assignee', 'status', 'priority', 'title'])")],
    "assignee-lost-on-restart": [("src/persistence.js", "    assignee: ticket.assignee ?? null,\n", ""),
                                 ("src/persistence.js", "  if (ticket.assignee !== null) text(ticket.assignee, `${where}.assignee`, fail);\n", "")],
    "unassign-broken": [("src/tickets/validate.js", "  return body.assignee === null ? null : text(body, 'assignee', LIMITS.assignee);",
                         "  return text(body, 'assignee', LIMITS.assignee);")],
    "update-rejects-resolved": [("src/store.js", "    if (isFinal(ticket.status)) throw new ConflictError(",
                                 "    if (!isActive(ticket.status)) throw new ConflictError(")],
    # One that breaks a base module and edits the base's tests to match: its own suite passes, the pristine one cannot.
    "outbox-enqueue-renamed": [("src/outbox.js", "  enqueue({ key, type, to, ticket = null, data = {} }, now) {",
                                "  add({ key, type, to, ticket = null, data = {} }, now) {"),
                               ("src/store.js", "return this.outbox.enqueue({", "return this.outbox.add({"),
                               ("test/outbox.test.js", ".enqueue(", ".add(", 12)],
}
EDITS_BASE_TESTS = {"outbox-enqueue-renamed": "test/outbox.test.js"}
VARIANTS = ("base", "reference", "alternative", *DEFECTS)


def build(dest: Path, variant: str = "reference") -> Path:
    """Write the delivery of `variant` into `dest` (created if missing) and return it."""
    if variant not in VARIANTS:
        raise ValueError(f"unknown variant {variant!r}; known: {', '.join(VARIANTS)}")
    dest = first.build(dest, "reference")
    if variant == "base":
        return dest
    if variant == "alternative":
        first.apply(dest, ALTERNATIVE, "alternative")
        first.write(dest, ALTERNATIVE_ADDED)
        return dest
    first.apply(dest, REFERENCE, "reference")
    first.write(dest, REFERENCE_ADDED)
    first.apply(dest, DEFECTS.get(variant, ()), f"defect {variant}")
    return dest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("dest", type=Path)
    parser.add_argument("--variant", default="reference", choices=VARIANTS)
    args = parser.parse_args()
    print(build(args.dest, args.variant))


if __name__ == "__main__":
    main()
