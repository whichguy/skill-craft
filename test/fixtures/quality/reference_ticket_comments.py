#!/usr/bin/env python3
"""The reference delivery of the `ticket-comments` case, the third link of the ticket chain, for calibrating its checks
(cases.json: the case's own checks and its retention checks), the base's pristine tests and the earlier links' checks.

    python3 reference_ticket_comments.py DEST [--variant NAME]

writes a delivery into the empty folder DEST. A follow-on starts from the run before it, so every variant starts from
ticket-escalation's reference (reference_ticket_escalation.py), which stands in for the second pass, and that from
ticket-assignment's, which stands in for the first. The variants:

* ``base``: the escalation reference alone, as the third pass starts. It must fail every check of the new feature and pass
  the earlier links' checks.
* ``reference``: the prompt done. A comment is an audited change to the ticket kept on the ticket record; the assignee is told
  unless the assignee wrote it; the outbox key names the comment, because the outbox holds back a second notice with the same
  key while the first still waits (docs/decisions/0006-notification-outbox.md), the rule the first pass recorded for
  assignments; the persistence record functions name the new field and an older data file takes an empty list for it
  (docs/decisions/0008-json-data-file.md).
* each name of DEFECTS: the reference with one targeted change, a sentence of the request or an inherited decision broken.

No independent alternative is written for this link yet: its checks read behaviour at the HTTP boundary only, and the gap is
recorded in docs/shiploop-multipass-journal.md.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import reference_ticket_assignment as first  # noqa: E402  (the edit helpers)
import reference_ticket_escalation as second  # noqa: E402  (the second pass's stand-in, which this one starts from)

COMMENT_METHOD = r"""  /**
   * Add a comment to a ticket in any status but closed. The comment is an audited change to the ticket, and the agent the
   * ticket is assigned to is told, unless that agent wrote it. The outbox key names the comment, so a second comment is not
   * swallowed by the notice of the first while that still waits (docs/decisions/0006-notification-outbox.md).
   */
  comment(id, { author, body }, actor) {
    const ticket = this.find(id);
    if (isFinal(ticket.status)) throw new ConflictError(`ticket ${id} is ${ticket.status} and takes no more comments`);
    const at = this.now();
    const number = ticket.comments.length + 1;
    const comment = { id: `C-${String(number).padStart(4, '0')}`, author, body, created: at };
    ticket.comments.push(comment);
    ticket.updated = at;
    this.audit.append({ ticket: ticket.id, action: 'ticket.commented', actor, at, changes: { comments: { from: number - 1, to: number } } });
    if (ticket.assignee !== null && ticket.assignee !== author) {
      this.notify(ticket, 'ticket.commented', ticket.assignee, at, `ticket.commented:${ticket.id}:${comment.id}`);
    }
    this.save();
    return { ...comment };
  }

  // The worker's side of the outbox
"""

NOTIFY_ASSIGNEE = "this.notify(ticket, 'ticket.commented', ticket.assignee, at, `ticket.commented:${ticket.id}:${comment.id}`);"
SKIP_AUTHOR = "    if (ticket.assignee !== null && ticket.assignee !== author) {\n"
CLOSED_GUARD = "    if (isFinal(ticket.status)) throw new ConflictError(`ticket ${id} is ${ticket.status} and takes no more comments`);\n"
SAVE_COMMENTS = "    comments: (ticket.comments ?? []).map(commentRecord),\n"

REFERENCE = [
    ("src/tickets/validate.js", "const LIMITS = Object.freeze({ title: 200, requester: 64, assignee: 64 });",
     "const LIMITS = Object.freeze({ title: 200, requester: 64, assignee: 64, author: 64, comment: 2000 });"),
    ("src/tickets/validate.js", "module.exports = { LIMITS, assignment, reassignment,",
     "/** POST /tickets/:id/comments: { author, body }; the body may run over several lines. */\nfunction comment(body) {\n"
     "  onlyFields(body, ['author', 'body']);\n  const author = text(body, 'author', LIMITS.author);\n"
     "  if (typeof body.body !== 'string') throw new InvalidError('body must be a string');\n"
     "  const trimmed = body.body.trim();\n  if (trimmed === '') throw new InvalidError('body must not be empty');\n"
     "  if (trimmed.length > LIMITS.comment) throw new InvalidError(`body must be at most ${LIMITS.comment} characters`);\n"
     "  return { author, body: trimmed };\n}\n\nmodule.exports = { LIMITS, assignment, comment, reassignment,"),
    ("src/store.js", "/** The fields a new ticket's audit entry lists, from null. */",
     "/** A ticket as the outside sees it: a copy, whose comments are copies too. */\nfunction view(ticket) {\n"
     "  return { ...ticket, comments: ticket.comments.map((comment) => ({ ...comment })) };\n}\n\n"
     "/** The fields a new ticket's audit entry lists, from null. */"),
    ("src/store.js", "  get(id) {\n    return { ...this.find(id) };\n  }", "  get(id) {\n    return view(this.find(id));\n  }"),
    ("src/store.js", "    return { items: page.items.map((ticket) => ({ ...ticket })), next: page.next };",
     "    return { items: page.items.map(view), next: page.next };"),
    ("src/store.js", "status: 'open', assignee: null, created: at, updated: at };",
     "status: 'open', assignee: null, comments: [], created: at, updated: at };"),
    ("src/store.js", "  // The worker's side of the outbox\n", COMMENT_METHOD),
    ("src/persistence.js", "    assignee: ticket.assignee ?? null,\n", "    assignee: ticket.assignee ?? null,\n" + SAVE_COMMENTS),
    ("src/persistence.js", "function auditRecord(entry) {",
     "function commentRecord(comment) {\n  return { id: comment.id, author: comment.author, body: comment.body, created: comment.created };\n}\n\n"
     "function auditRecord(entry) {"),
    ("src/persistence.js", "  if (ticket.assignee !== null) text(ticket.assignee, `${where}.assignee`, fail);\n",
     "  if (ticket.assignee !== null) text(ticket.assignee, `${where}.assignee`, fail);\n"
     "  ticket.comments.forEach((comment, index) => {\n"
     "    for (const field of ['id', 'author', 'body']) text(comment[field], `${where}.comments[${index}].${field}`, fail);\n"
     "    time(comment.created, `${where}.comments[${index}].created`, fail);\n  });\n"),
    ("src/templates.js", "  'ticket.assigned': (event) => ({",
     "  'ticket.commented': (event) => ({\n    subject: `[${event.ticket}] New comment`,\n"
     "    body: `Ticket ${event.ticket} \"${event.data.title}\", which is assigned to you, has a new comment.`,\n  }),\n"
     "  'ticket.assigned': (event) => ({"),
    ("src/app.js", "  router.post('/tickets/reassign', async ({ req }) => {",
     "  router.post('/tickets/:id/comments', async ({ req, params }) => {\n    const input = validate.comment(await body(req));\n"
     "    return { status: 201, body: store.comment(params.id, input, actorOf(req)) };\n  });\n\n"
     "  router.post('/tickets/reassign', async ({ req }) => {"),
]

REFERENCE_ADDED = {
    "test/comments.test.js": r"""'use strict';

const { test } = require('node:test');
const assert = require('node:assert/strict');
const { ticketBody, withService } = require('./helpers');

test('a comment is added, shown oldest first and audited', async () => {
  await withService({}, async (api) => {
    await api.post('/tickets', ticketBody());
    const first = await api.post('/tickets/T-0001/comments', { author: 'dana.k', body: 'looking into it' }, { 'X-Actor': 'dana.k' });
    assert.equal(first.status, 201);
    assert.equal(first.body.author, 'dana.k');
    await api.post('/tickets/T-0001/comments', { author: 'lee.m', body: 'done\nin two lines' });
    const shown = (await api.get('/tickets/T-0001')).body;
    assert.deepEqual(shown.comments.map((comment) => comment.body), ['looking into it', 'done\nin two lines']);
    assert.equal((await api.get('/tickets/T-0001/audit')).body.items.at(-1).action, 'ticket.commented');
  });
});

test('a closed ticket takes no comment, and an empty author is invalid', async () => {
  await withService({}, async (api) => {
    await api.post('/tickets', ticketBody());
    assert.equal((await api.post('/tickets/T-0001/comments', { author: '', body: 'x' })).status, 400);
    for (const to of ['in_progress', 'resolved', 'closed']) await api.post('/tickets/T-0001/transition', { to });
    assert.equal((await api.post('/tickets/T-0001/comments', { author: 'dana.k', body: 'late' })).status, 409);
  });
});

test('each comment from someone else makes a notice of its own for the assignee; the assignee\'s own makes none', async () => {
  await withService({}, async (api) => {
    await api.post('/tickets', ticketBody());
    await api.put('/tickets/T-0001/assignee', { assignee: 'dana.k' });
    const told = async () => (await api.get('/admin/outbox')).body.pending.filter((event) => event.to === 'dana.k').length;
    const before = await told();
    await api.post('/tickets/T-0001/comments', { author: 'lee.m', body: 'one' });
    await api.post('/tickets/T-0001/comments', { author: 'lee.m', body: 'two' });
    assert.equal(await told(), before + 2);
    await api.post('/tickets/T-0001/comments', { author: 'dana.k', body: 'mine' });
    assert.equal(await told(), before + 2);
  });
});
""",
}

DEFECTS = {
    # The outbox holds back a second notice with the same key while the first waits, so a key that is the ticket's alone
    # swallows the second comment's notice.
    "comment-default-key": [("src/store.js", NOTIFY_ASSIGNEE, "this.notify(ticket, 'ticket.commented', ticket.assignee, at);")],
    # The request: the agent is told when someone else comments.
    "comment-notifies-author": [("src/store.js", SKIP_AUTHOR, "    if (ticket.assignee !== null) {\n")],
    # The request: oldest first.
    "comments-newest-first": [("src/store.js", "    ticket.comments.push(comment);\n", "    ticket.comments.unshift(comment);\n")],
    # The request: any status except closed.
    "closed-takes-comments": [("src/store.js", CLOSED_GUARD, "")],
    # The request: an author is a non-empty name.
    "empty-author-accepted": [("src/tickets/validate.js", "  const author = text(body, 'author', LIMITS.author);\n",
                               "  const author = typeof body.author === 'string' && body.author !== '' ? body.author : 'anonymous';\n")],
    # The request: comments survive a restart, and the record functions of the data file name every field the file keeps.
    "comments-lost-on-restart": [("src/persistence.js", SAVE_COMMENTS, "    comments: [],\n")],
    # The request: a data file written before the change keeps loading (decision 8: a field older files lack takes its default).
    "legacy-file-refused": [("src/persistence.js", "  const ticket = ticketRecord(object(record, where, fail));\n",
                             "  const ticket = ticketRecord(object(record, where, fail));\n"
                             "  if (!Array.isArray(record.comments)) throw fail(`${where}.comments is not a list`);\n")],
}
VARIANTS = ("base", "reference", *DEFECTS)


def build(dest: Path, variant: str = "reference") -> Path:
    """Write the delivery of `variant` into `dest` (created if missing) and return it."""
    if variant not in VARIANTS:
        raise ValueError(f"unknown variant {variant!r}; known: {', '.join(VARIANTS)}")
    dest = second.build(dest, "reference")
    if variant == "base":
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
