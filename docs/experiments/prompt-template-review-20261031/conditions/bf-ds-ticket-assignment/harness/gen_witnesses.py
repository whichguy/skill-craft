#!/usr/bin/env python3
"""Emit witnesses/<id>.js from compact snippets."""
import os, textwrap

OUT = "/Users/dadleet/src/skill-craft/docs/experiments/prompt-template-review-20261031/conditions/bf-ds-ticket-assignment/witnesses"

HEAD = """'use strict';
// Witness {id}: {doc}
const L = require('./_lib');
const {{ check, eq, sleep }} = L;
L.run(async () => {{
"""
TAIL = "});\n"

W = {}
DOC = {}


def w(id_, doc, body):
    W[id_] = body
    DOC[id_] = doc


# ---------- R-1 ----------
w("R-1.1", "POST /tickets answers 201 with assignee: null (key present).", """
const s = await L.startService();
const r = await s.api.post('/tickets', L.NEW);
check(r.status === 201, 'create answers 201');
check('assignee' in r.body && r.body.assignee === null, 'POST /tickets body carries assignee: null');
""")
w("R-1.2", "GET /tickets/:id of an unassigned ticket carries assignee: null.", """
const s = await L.startService();
const t = await L.ticket(s.api);
const r = await s.api.get('/tickets/' + t.id);
check(r.status === 200 && 'assignee' in r.body && r.body.assignee === null, 'GET /tickets/:id carries assignee: null');
""")
w("R-1.3", "Items from GET /tickets carry assignee (null when unassigned).", """
const s = await L.startService();
await L.ticket(s.api);
await L.ticket(s.api, { title: 'Second' });
const r = await s.api.get('/tickets');
check(r.status === 200 && r.body.items.length === 2, 'two items');
check(r.body.items.every((i) => 'assignee' in i && i.assignee === null), 'every listed item carries assignee: null');
""")
w("R-1.4", "PATCH /tickets/:id returns a ticket carrying assignee (null, then the name).", """
const s = await L.startService();
const t = await L.ticket(s.api);
let r = await s.api.patch('/tickets/' + t.id, { title: 'New title' });
check(r.status === 200 && 'assignee' in r.body && r.body.assignee === null, 'PATCH response carries assignee: null');
await L.assign(s.api, t.id, 'dana');
r = await s.api.patch('/tickets/' + t.id, { priority: 'high' });
eq(r.body.assignee, 'dana', 'PATCH response carries the name once assigned');
""")
w("R-1.5", "POST /tickets/:id/transition returns a ticket carrying assignee.", """
const s = await L.startService();
const t = await L.ticket(s.api);
let r = await s.api.post('/tickets/' + t.id + '/transition', { to: 'in_progress' });
check(r.status === 200 && 'assignee' in r.body && r.body.assignee === null, 'transition response carries assignee: null');
await L.assign(s.api, t.id, 'dana');
r = await s.api.post('/tickets/' + t.id + '/transition', { to: 'resolved' });
eq(r.body.assignee, 'dana', 'transition response carries the name once assigned');
""")
w("R-1.6", "The data file's ticket record carries an assignee key (null when unassigned).", """
const f = L.tmpfile('d.json');
const s = await L.startService({ dataFile: f });
const t = await L.ticket(s.api);
let doc = L.readJson(f);
check('assignee' in doc.tickets[0] && doc.tickets[0].assignee === null, 'data file ticket record has assignee: null');
await L.assign(s.api, t.id, 'dana');
doc = L.readJson(f);
eq(doc.tickets[0].assignee, 'dana', 'data file holds the assigned name');
""")
w("R-1.7", "After an assignment GET /tickets/:id returns the agent name.", """
const s = await L.startService();
const t = await L.ticket(s.api);
await L.assign(s.api, t.id, 'dana');
const r = await s.api.get('/tickets/' + t.id);
eq(r.body.assignee, 'dana', 'GET /tickets/:id after assignment');
""")
w("R-1.8", "After an assignment the item in GET /tickets returns the agent name.", """
const s = await L.startService();
const t = await L.ticket(s.api);
await L.assign(s.api, t.id, 'dana');
const r = await s.api.get('/tickets');
const item = r.body.items.find((i) => i.id === t.id);
eq(item && item.assignee, 'dana', 'GET /tickets item after assignment');
""")
w("R-1.9", "After assign then unassign GET /tickets/:id returns null.", """
const s = await L.startService();
const t = await L.ticket(s.api);
await L.assign(s.api, t.id, 'dana');
await L.assign(s.api, t.id, null);
const r = await s.api.get('/tickets/' + t.id);
check(r.body.assignee === null, 'GET /tickets/:id after unassignment is null, got ' + JSON.stringify(r.body.assignee));
""")
w("R-1.10", "With DATA_FILE a restarted service returns the same assignee.", """
const f = L.tmpfile('d.json');
let s = await L.startService({ dataFile: f });
const t = await L.ticket(s.api);
await L.assign(s.api, t.id, 'dana');
await s.stop();
s = await L.startService({ dataFile: f });
const r = await s.api.get('/tickets/' + t.id);
eq(r.body.assignee, 'dana', 'assignee after restart');
""")
w("R-1.11", "A version-1 file without assignee loads the tickets with assignee: null.", """
const f = await L.seedFile((doc) => { for (const t of doc.tickets) delete t.assignee; });
const s = await L.startService({ dataFile: f });
const r = await s.api.get('/tickets/T-0001');
check(r.status === 200 && 'assignee' in r.body && r.body.assignee === null, 'legacy ticket loads with assignee: null');
""")
w("R-1.12", "A data file with a non-string assignee is refused at load with a message naming the record.", """
const f = await L.seedFile((doc) => { doc.tickets[0].assignee = 42; });
const r = await L.tryStart({ dataFile: f });
check(!r.started, 'a data file with assignee 42 is refused at load');
check(/tickets\\[0\\]|T-0001/.test(r.stderr.replace(f, '')), 'the refusal names the record, got: ' + r.stderr.trim());
""")
w("R-1.13", "A data file with an empty-string assignee is refused at load.", """
const f = await L.seedFile((doc) => { doc.tickets[0].assignee = ''; });
const r = await L.tryStart({ dataFile: f });
check(!r.started, 'a data file with assignee "" is refused at load');
""")
w("R-1.14", "A data file with a 65-character assignee is refused at load.", """
const f = await L.seedFile((doc) => { doc.tickets[0].assignee = 'x'.repeat(65); });
const r = await L.tryStart({ dataFile: f });
check(!r.started, 'a data file with a 65-character assignee is refused at load');
""")
w("R-1.15", "A data file whose assignee has a control character is refused at load.", """
for (const bad of ['a\\tb', 'a\\nb', 'a\\u0001b', 'a\\u007fb']) {
  const f = await L.seedFile((doc) => { doc.tickets[0].assignee = bad; });
  const r = await L.tryStart({ dataFile: f });
  check(!r.started, 'a data file with assignee ' + JSON.stringify(bad) + ' is refused at load');
}
""")

# ---------- R-2 ----------
w("R-2.1", "PUT /tickets/:id/assignee answers 200 with the changed ticket.", """
const s = await L.startService();
const t = await L.ticket(s.api);
const r = await L.assign(s.api, t.id, 'dana');
check(r.status === 200, 'PUT answers 200, got ' + r.status);
check(r.body && r.body.id === t.id && r.body.assignee === 'dana', 'the response body is the changed ticket (assignee dana)');
""")
w("R-2.2", "After the PUT, GET /tickets/:id agrees (the store changed).", """
const s = await L.startService();
const t = await L.ticket(s.api);
const r = await L.assign(s.api, t.id, 'dana');
check(r.status === 200, 'PUT answers 200');
const g = await s.api.get('/tickets/' + t.id);
eq(g.body.assignee, 'dana', 'GET after PUT');
""")
w("R-2.3", "The ticket's updated moves to the change time.", """
const s = await L.startService();
const t = await L.ticket(s.api);
await sleep(30);
const r = await L.assign(s.api, t.id, 'dana');
check(r.status === 200 && Date.parse(r.body.updated) > Date.parse(t.updated), 'updated moved forward: ' + t.updated + ' -> ' + (r.body && r.body.updated));
const g = await s.api.get('/tickets/' + t.id);
eq(g.body.updated, r.body.updated, 'GET agrees on updated');
""")
w("R-2.4", "Title, priority, requester and status keep their values.", """
const s = await L.startService();
const t = await L.ticket(s.api, { title: 'Keep me', priority: 'high', requester: 'sam' });
const r = await L.assign(s.api, t.id, 'dana');
const g = await s.api.get('/tickets/' + t.id);
for (const f of ['title', 'priority', 'requester', 'status']) {
  eq(r.body[f], t[f], 'response ' + f);
  eq(g.body[f], t[f], 'GET ' + f);
}
""")
w("R-2.5", "The agent name is taken after trimming.", """
const s = await L.startService();
const t = await L.ticket(s.api);
const r = await L.assign(s.api, t.id, '  dana  ');
check(r.status === 200, 'padded name accepted');
eq(r.body.assignee, 'dana', 'response is trimmed');
const g = await s.api.get('/tickets/' + t.id);
eq(g.body.assignee, 'dana', 'GET is trimmed');
""")
w("R-2.6", "An unknown ticket id answers 404 not_found.", """
const s = await L.startService();
const r = await L.assign(s.api, 'T-9999', 'dana');
check(r.status === 404 && r.body && r.body.error && r.body.error.code === 'not_found', 'unknown id -> 404 not_found, got ' + r.status + ' ' + JSON.stringify(r.body));
""")
w("R-2.7", "A body that is not a JSON object answers 400 invalid.", """
const s = await L.startService();
const t = await L.ticket(s.api);
for (const raw of ['[]', '"dana"', '42', 'null']) {
  const r = await s.api.putRaw('/tickets/' + t.id + '/assignee', raw);
  check(r.status === 400 && r.body && r.body.error && r.body.error.code === 'invalid', 'body ' + raw + ' -> 400 invalid, got ' + r.status);
}
""")
w("R-2.8", "A missing assignee field answers 400 invalid.", """
const s = await L.startService();
const t = await L.ticket(s.api);
const r = await s.api.put('/tickets/' + t.id + '/assignee', {});
check(r.status === 400 && r.body && r.body.error && r.body.error.code === 'invalid', 'missing field -> 400 invalid, got ' + r.status);
""")
w("R-2.9", "A non-string non-null value (array, object) answers 400 invalid.", """
const s = await L.startService();
const t = await L.ticket(s.api);
for (const v of [['dana'], {}, { name: 'dana' }]) {
  const r = await L.assign(s.api, t.id, v);
  check(r.status === 400 && r.body && r.body.error && r.body.error.code === 'invalid', 'value ' + JSON.stringify(v) + ' -> 400 invalid, got ' + r.status);
}
""")
w("R-2.10", "An unknown field answers 400 invalid.", """
const s = await L.startService();
const t = await L.ticket(s.api);
const r = await s.api.put('/tickets/' + t.id + '/assignee', { assignee: 'dana', extra: 1 });
check(r.status === 400 && r.body && r.body.error && r.body.error.code === 'invalid', 'unknown field -> 400 invalid, got ' + r.status);
const g = await s.api.get('/tickets/' + t.id);
check(g.body.assignee === null, 'nothing was assigned');
""")

# ---------- R-3 ----------
w("R-3.1", "{assignee:null} answers 200 with the ticket whose assignee is null.", """
const s = await L.startService();
const t = await L.ticket(s.api);
await L.assign(s.api, t.id, 'dana');
const r = await L.assign(s.api, t.id, null);
check(r.status === 200, 'unassign answers 200, got ' + r.status);
check(r.body && r.body.id === t.id && r.body.assignee === null, 'the response is the ticket with assignee null, got ' + JSON.stringify(r.body && r.body.assignee));
""")
w("R-3.2", "After the unassigning PUT the ticket reads back with assignee null.", """
const s = await L.startService();
const t = await L.ticket(s.api);
await L.assign(s.api, t.id, 'dana');
await L.assign(s.api, t.id, null);
const g = await s.api.get('/tickets/' + t.id);
check(g.body.assignee === null, 'reads back null, got ' + JSON.stringify(g.body.assignee));
""")
w("R-3.3", "Unassigning an already unassigned ticket is accepted (200).", """
const s = await L.startService();
const t = await L.ticket(s.api);
const r = await L.assign(s.api, t.id, null);
check(r.status === 200, 'unassign of an unassigned ticket answers 200, got ' + r.status);
""")

# ---------- R-4 ----------
w("R-4.1", "A one-character name is accepted.", """
const s = await L.startService();
const t = await L.ticket(s.api);
const r = await L.assign(s.api, t.id, 'a');
check(r.status === 200 && r.body.assignee === 'a', 'name "a" accepted, got ' + r.status);
""")
w("R-4.2", "A 64-character name is accepted.", """
const s = await L.startService();
const t = await L.ticket(s.api);
const name = 'n'.repeat(64);
const r = await L.assign(s.api, t.id, name);
check(r.status === 200 && r.body.assignee === name, '64-character name accepted, got ' + r.status);
""")
w("R-4.3", "An empty string is refused with 400 invalid.", """
const s = await L.startService();
const t = await L.ticket(s.api);
const r = await L.assign(s.api, t.id, '');
check(r.status === 400 && r.body.error.code === 'invalid', 'empty name -> 400 invalid, got ' + r.status);
""")
w("R-4.4", "Whitespace-only text is refused with 400 invalid.", """
const s = await L.startService();
const t = await L.ticket(s.api);
for (const v of ['   ', ' ', '\\u00a0 ']) {
  const r = await L.assign(s.api, t.id, v);
  check(r.status === 400 && r.body.error.code === 'invalid', 'whitespace-only ' + JSON.stringify(v) + ' -> 400 invalid, got ' + r.status);
}
""")
w("R-4.5", "A 65-character name is refused with 400 invalid.", """
const s = await L.startService();
const t = await L.ticket(s.api);
const r = await L.assign(s.api, t.id, 'n'.repeat(65));
check(r.status === 400 && r.body.error.code === 'invalid', '65 characters -> 400 invalid, got ' + r.status);
""")
w("R-4.6", "A name with a tab is refused with 400 invalid.", """
const s = await L.startService();
const t = await L.ticket(s.api);
const r = await L.assign(s.api, t.id, 'one\\ttwo');
check(r.status === 400 && r.body.error.code === 'invalid', 'tab -> 400 invalid, got ' + r.status);
""")
w("R-4.7", "A name with a line break is refused with 400 invalid.", """
const s = await L.startService();
const t = await L.ticket(s.api);
for (const v of ['one\\ntwo', 'one\\rtwo', 'one\\r\\ntwo']) {
  const r = await L.assign(s.api, t.id, v);
  check(r.status === 400 && r.body.error.code === 'invalid', 'line break ' + JSON.stringify(v) + ' -> 400 invalid, got ' + r.status);
}
""")
w("R-4.8", "A name with another C0 control character is refused with 400 invalid.", """
const s = await L.startService();
const t = await L.ticket(s.api);
for (const v of ['a\\u0001b', 'a\\u001fb', 'a\\u0000b']) {
  const r = await L.assign(s.api, t.id, v);
  check(r.status === 400 && r.body.error.code === 'invalid', 'C0 control ' + JSON.stringify(v) + ' -> 400 invalid, got ' + r.status);
}
""")
w("R-4.9", "A name with DEL is refused with 400 invalid.", """
const s = await L.startService();
const t = await L.ticket(s.api);
const r = await L.assign(s.api, t.id, 'a\\u007fb');
check(r.status === 400 && r.body.error.code === 'invalid', 'DEL -> 400 invalid, got ' + r.status);
""")
w("R-4.10", "A number is refused with 400 invalid.", """
const s = await L.startService();
const t = await L.ticket(s.api);
for (const v of [42, 0, 1.5]) {
  const r = await L.assign(s.api, t.id, v);
  check(r.status === 400 && r.body.error.code === 'invalid', 'number ' + v + ' -> 400 invalid, got ' + r.status);
}
""")
w("R-4.11", "A boolean is refused with 400 invalid.", """
const s = await L.startService();
const t = await L.ticket(s.api);
for (const v of [true, false]) {
  const r = await L.assign(s.api, t.id, v);
  check(r.status === 400 && r.body.error.code === 'invalid', 'boolean ' + v + ' -> 400 invalid, got ' + r.status);
}
""")
w("R-4.12", "The 400 message for an invalid assignee names assignee.", """
const s = await L.startService();
const t = await L.ticket(s.api);
for (const v of ['', 42, 'n'.repeat(65), 'a\\tb', true]) {
  const r = await L.assign(s.api, t.id, v);
  check(r.status === 400 && /assignee/.test(r.body.error.message), 'message for ' + JSON.stringify(v).slice(0, 20) + ' names assignee: ' + (r.body && r.body.error && r.body.error.message));
}
""")

# ---------- R-5 ----------
w("R-5.1", "An open ticket accepts assignment.", """
const s = await L.startService();
const t = await L.ticket(s.api);
const r = await L.assign(s.api, t.id, 'dana');
check(r.status === 200 && r.body.assignee === 'dana', 'open ticket accepts assignment, got ' + r.status);
""")
w("R-5.2", "An in_progress ticket accepts assignment.", """
const s = await L.startService();
const t = await L.ticket(s.api);
await L.advance(s.api, t.id, 'in_progress');
const r = await L.assign(s.api, t.id, 'dana');
check(r.status === 200 && r.body.assignee === 'dana', 'in_progress ticket accepts assignment, got ' + r.status);
""")
w("R-5.3", "Open and in_progress tickets accept unassignment.", """
const s = await L.startService();
const a = await L.ticket(s.api);
await L.assign(s.api, a.id, 'dana');
let r = await L.assign(s.api, a.id, null);
check(r.status === 200 && r.body.assignee === null, 'open ticket accepts unassignment, got ' + r.status);
await L.assign(s.api, a.id, 'dana');
await L.advance(s.api, a.id, 'in_progress');
r = await L.assign(s.api, a.id, null);
check(r.status === 200 && r.body.assignee === null, 'in_progress ticket accepts unassignment, got ' + r.status);
""")
w("R-5.4", "A resolved ticket answers 409 conflict on assignment.", """
const s = await L.startService();
const t = await L.ticket(s.api);
await L.advance(s.api, t.id, 'resolved');
const r = await L.assign(s.api, t.id, 'dana');
check(r.status === 409 && r.body.error.code === 'conflict', 'resolved ticket -> 409 conflict, got ' + r.status);
""")
w("R-5.5", "A closed ticket answers 409 conflict on assignment.", """
const s = await L.startService();
const t = await L.ticket(s.api);
await L.advance(s.api, t.id, 'closed');
const r = await L.assign(s.api, t.id, 'dana');
check(r.status === 409 && r.body.error.code === 'conflict', 'closed ticket -> 409 conflict, got ' + r.status);
""")
w("R-5.6", "A refused assignment leaves the assignee unchanged.", """
const s = await L.startService();
for (const final of ['resolved', 'closed']) {
  const t = await L.ticket(s.api, { title: 'T ' + final });
  await L.assign(s.api, t.id, 'dana');
  await L.advance(s.api, t.id, final);
  const r = await L.assign(s.api, t.id, 'erin');
  check(r.status === 409, final + ' ticket refuses assignment');
  const g = await s.api.get('/tickets/' + t.id);
  eq(g.body.assignee, 'dana', final + ' ticket keeps its assignee');
}
""")
w("R-5.7", "A refused assignment adds no audit entry.", """
const s = await L.startService();
for (const final of ['resolved', 'closed']) {
  const t = await L.ticket(s.api, { title: 'T ' + final });
  await L.assign(s.api, t.id, 'dana');
  await L.advance(s.api, t.id, final);
  const before = (await L.auditOf(s.api, t.id)).length;
  const r = await L.assign(s.api, t.id, 'erin');
  check(r.status === 409, final + ' refuses');
  eq((await L.auditOf(s.api, t.id)).length, before, final + ' audit length unchanged');
}
""")
w("R-5.8", "A refused assignment adds no outbox event.", """
const s = await L.startService();
for (const final of ['resolved', 'closed']) {
  const t = await L.ticket(s.api, { title: 'T ' + final });
  await L.assign(s.api, t.id, 'dana');
  await L.advance(s.api, t.id, final);
  const before = (await L.events(s.api)).length;
  const r = await L.assign(s.api, t.id, 'erin');
  check(r.status === 409, final + ' refuses');
  eq((await L.events(s.api)).length, before, final + ' outbox size unchanged');
}
""")
w("R-5.9", "{assignee:null} on a resolved/closed ticket answers 409 and changes nothing.", """
const s = await L.startService();
for (const final of ['resolved', 'closed']) {
  const t = await L.ticket(s.api, { title: 'T ' + final });
  await L.assign(s.api, t.id, 'dana');
  await L.advance(s.api, t.id, final);
  const r = await L.assign(s.api, t.id, null);
  check(r.status === 409 && r.body.error.code === 'conflict', final + ' ticket unassign -> 409 conflict, got ' + r.status);
  const g = await s.api.get('/tickets/' + t.id);
  eq(g.body.assignee, 'dana', final + ' keeps assignee');
}
""")

# ---------- R-6 ----------
w("R-6.1", "Assigning the current agent answers 200 with the unchanged ticket.", """
const s = await L.startService();
const t = await L.ticket(s.api);
await L.assign(s.api, t.id, 'dana');
const before = (await s.api.get('/tickets/' + t.id)).body;
await sleep(20);
const r = await L.assign(s.api, t.id, 'dana');
check(r.status === 200, 'same-agent assignment answers 200, got ' + r.status);
eq(r.body, before, 'the ticket is unchanged');
""")
w("R-6.2", "Assigning the current agent adds no audit entry.", """
const s = await L.startService();
const t = await L.ticket(s.api);
await L.assign(s.api, t.id, 'dana');
const before = await L.auditOf(s.api, t.id);
const r = await L.assign(s.api, t.id, 'dana');
check(r.status === 200, 'answers 200');
eq(await L.auditOf(s.api, t.id), before, 'audit log unchanged');
""")
w("R-6.3", "Assigning the current agent enqueues no notification.", """
const s = await L.startService();
const t = await L.ticket(s.api);
await L.assign(s.api, t.id, 'dana');
const before = await L.outbox(s.api);
const r = await L.assign(s.api, t.id, 'dana');
check(r.status === 200, 'answers 200');
eq(await L.outbox(s.api), before, 'outbox unchanged');
""")
w("R-6.4", "Assigning the current agent leaves updated unchanged.", """
const s = await L.startService();
const t = await L.ticket(s.api);
const a = await L.assign(s.api, t.id, 'dana');
await sleep(30);
const r = await L.assign(s.api, t.id, 'dana');
eq(r.body.updated, a.body.updated, 'updated in the response');
const g = await s.api.get('/tickets/' + t.id);
eq(g.body.updated, a.body.updated, 'updated on GET');
""")
w("R-6.5", "Unassigning an unassigned ticket answers 200 and leaves audit and outbox unchanged.", """
const s = await L.startService();
const t = await L.ticket(s.api);
const auditBefore = await L.auditOf(s.api, t.id);
const outboxBefore = await L.outbox(s.api);
const r = await L.assign(s.api, t.id, null);
check(r.status === 200 && r.body.assignee === null, 'answers 200 with the unchanged ticket, got ' + r.status);
eq(await L.auditOf(s.api, t.id), auditBefore, 'audit unchanged');
eq(await L.outbox(s.api), outboxBefore, 'outbox unchanged');
""")
w("R-6.6", "Unassigning an unassigned ticket leaves updated unchanged.", """
const s = await L.startService();
const t = await L.ticket(s.api);
await sleep(30);
const r = await L.assign(s.api, t.id, null);
check(r.status === 200, 'answers 200');
eq(r.body.updated, t.updated, 'updated in the response');
const g = await s.api.get('/tickets/' + t.id);
eq(g.body.updated, t.updated, 'updated on GET');
""")
w("R-6.7", "Assigning the current agent with surrounding whitespace is also a no-op.", """
const s = await L.startService();
const t = await L.ticket(s.api);
const a = await L.assign(s.api, t.id, 'dana');
const auditBefore = await L.auditOf(s.api, t.id);
const outboxBefore = await L.outbox(s.api);
await sleep(30);
const r = await L.assign(s.api, t.id, ' dana ');
check(r.status === 200 && r.body.assignee === 'dana', 'answers 200 with dana');
eq(r.body.updated, a.body.updated, 'updated unchanged');
eq(await L.auditOf(s.api, t.id), auditBefore, 'audit unchanged');
eq(await L.outbox(s.api), outboxBefore, 'outbox unchanged');
""")

# ---------- R-7 ----------
w("R-7.1", "A real assignment appends an audit entry with action ticket.assigned.", """
const s = await L.startService();
const t = await L.ticket(s.api);
await L.assign(s.api, t.id, 'dana');
const a = (await L.auditOf(s.api, t.id)).filter((e) => e.action === 'ticket.assigned');
eq(a.length, 1, 'one ticket.assigned entry');
""")
w("R-7.2", "A real assignment appends exactly one audit entry.", """
const s = await L.startService();
const t = await L.ticket(s.api);
const before = (await L.auditOf(s.api, t.id)).length;
await L.assign(s.api, t.id, 'dana');
eq((await L.auditOf(s.api, t.id)).length, before + 1, 'exactly one new audit entry');
""")
w("R-7.3", "Assigning dana to an unassigned ticket records {assignee:{from:null,to:dana}}.", """
const s = await L.startService();
const t = await L.ticket(s.api);
await L.assign(s.api, t.id, 'dana');
const e = (await L.auditOf(s.api, t.id)).find((x) => x.action === 'ticket.assigned');
eq(e && e.changes, { assignee: { from: null, to: 'dana' } }, 'changes of the assignment entry');
""")
w("R-7.4", "Unassigning records {assignee:{from:dana,to:null}} under ticket.assigned.", """
const s = await L.startService();
const t = await L.ticket(s.api);
await L.assign(s.api, t.id, 'dana');
await L.assign(s.api, t.id, null);
const a = (await L.auditOf(s.api, t.id)).filter((x) => x.action === 'ticket.assigned');
eq(a.length, 2, 'two assignment entries');
eq(a[1] && a[1].changes, { assignee: { from: 'dana', to: null } }, 'unassignment entry');
""")
w("R-7.5", "Reassigning dana to erin records {from:dana,to:erin}.", """
const s = await L.startService();
const t = await L.ticket(s.api);
await L.assign(s.api, t.id, 'dana');
await L.assign(s.api, t.id, 'erin');
const a = (await L.auditOf(s.api, t.id)).filter((x) => x.action === 'ticket.assigned');
eq(a[1] && a[1].changes, { assignee: { from: 'dana', to: 'erin' } }, 'reassignment entry');
""")
w("R-7.6", "The audit entry's actor is the X-Actor header.", """
const s = await L.startService();
const t = await L.ticket(s.api);
await L.assign(s.api, t.id, 'dana', { 'x-actor': 'alice' });
const e = (await L.auditOf(s.api, t.id)).find((x) => x.action === 'ticket.assigned');
eq(e && e.actor, 'alice', 'actor');
""")
w("R-7.7", "Without X-Actor the actor is system.", """
const s = await L.startService();
const t = await L.ticket(s.api);
await L.assign(s.api, t.id, 'dana');
const e = (await L.auditOf(s.api, t.id)).find((x) => x.action === 'ticket.assigned');
eq(e && e.actor, 'system', 'actor');
""")
w("R-7.8", "The audit entry carries the time of the change.", """
const s = await L.startService();
const t = await L.ticket(s.api);
await sleep(30);
const r = await L.assign(s.api, t.id, 'dana');
const e = (await L.auditOf(s.api, t.id)).find((x) => x.action === 'ticket.assigned');
check(e && e.at === r.body.updated, 'entry.at equals the ticket updated time: ' + (e && e.at) + ' vs ' + r.body.updated);
check(e && Date.parse(e.at) > Date.parse(t.created), 'entry.at is later than the creation time');
""")
w("R-7.9", "GET audit returns the assignment entries oldest first.", """
const s = await L.startService();
const t = await L.ticket(s.api);
await L.assign(s.api, t.id, 'dana');
await sleep(10);
await L.assign(s.api, t.id, 'erin');
const a = await L.auditOf(s.api, t.id);
eq(a.map((x) => x.action), ['ticket.created', 'ticket.assigned', 'ticket.assigned'], 'actions in order');
eq(a.map((x) => x.seq), [...a.map((x) => x.seq)].sort((x, y) => x - y), 'seq ascending');
eq(a.slice(1).map((x) => x.changes.assignee.to), ['dana', 'erin'], 'dana before erin');
""")

# ---------- R-8 ----------
w("R-8.1", "Assigning enqueues an outbox event of type ticket.assigned.", """
const s = await L.startService();
const t = await L.ticket(s.api);
await L.assign(s.api, t.id, 'dana');
const o = await L.outbox(s.api);
const e = o.pending.filter((x) => x.type === 'ticket.assigned');
eq(e.length, 1, 'one pending ticket.assigned event');
""")
w("R-8.2", "The event is addressed to the agent.", """
const s = await L.startService();
const t = await L.ticket(s.api);
await L.assign(s.api, t.id, 'dana');
const e = (await L.events(s.api)).filter((x) => x.type === 'ticket.assigned');
eq(e.map((x) => x.to), ['dana'], 'event addressee');
""")
w("R-8.3", "The event carries the ticket id and its title.", """
const s = await L.startService();
const t = await L.ticket(s.api, { title: 'Broken monitor' });
await L.assign(s.api, t.id, 'dana');
const e = (await L.events(s.api)).find((x) => x.type === 'ticket.assigned');
check(e && e.ticket === t.id, 'event carries the ticket id');
check(e && e.data && e.data.title === 'Broken monitor', 'event carries the ticket title, got ' + JSON.stringify(e && e.data));
""")
w("R-8.4", "A notice pending for A does not swallow B's notice.", """
const s = await L.startService();
const t = await L.ticket(s.api);
await L.assign(s.api, t.id, 'dana');
await L.assign(s.api, t.id, 'erin');
const e = (await L.events(s.api)).filter((x) => x.type === 'ticket.assigned');
eq(e.map((x) => x.to).sort(), ['dana', 'erin'], 'a notice for each agent');
""")
w("R-8.5", "A->B->A adds no third event while A's notice is pending.", """
const s = await L.startService();
const t = await L.ticket(s.api);
await L.assign(s.api, t.id, 'dana');
await L.assign(s.api, t.id, 'erin');
await L.assign(s.api, t.id, 'dana');
const e = (await L.events(s.api)).filter((x) => x.type === 'ticket.assigned');
eq(e.map((x) => x.to).sort(), ['dana', 'erin'], 'exactly one notice per agent');
""")
w("R-8.6", "A->B->A still records the last change in the audit log.", """
const s = await L.startService();
const t = await L.ticket(s.api);
await L.assign(s.api, t.id, 'dana');
await L.assign(s.api, t.id, 'erin');
const r = await L.assign(s.api, t.id, 'dana');
check(r.status === 200 && r.body.assignee === 'dana', 'ticket is back with dana');
const a = (await L.auditOf(s.api, t.id)).filter((x) => x.action === 'ticket.assigned');
eq(a.length, 3, 'three assignment entries');
eq(a[2] && a[2].changes, { assignee: { from: 'erin', to: 'dana' } }, 'the return is audited');
""")
w("R-8.7", "The delivered NOTIFY_FILE line names type ticket.assigned, to and the ticket id.", """
const nf = L.tmpfile('n.log');
const s = await L.startService({ notifyFile: nf, workerMs: 30 });
const t = await L.ticket(s.api);
await L.assign(s.api, t.id, 'dana');
const lines = () => (L.fs.existsSync(nf) ? L.fs.readFileSync(nf, 'utf8').split('\\n').filter(Boolean).map((x) => JSON.parse(x)) : []);
const line = await L.waitFor(() => lines().find((l) => l.to === 'dana'), 4000);
check(line, 'a notice to dana was delivered');
check(line && line.type === 'ticket.assigned', 'line type is ticket.assigned, got ' + (line && line.type));
check(line && line.to === 'dana', 'line.to is dana');
check(line && line.ticket === t.id, 'line.ticket is the ticket id');
""")
w("R-8.8", "The notice is delivered exactly once.", """
const nf = L.tmpfile('n.log');
const s = await L.startService({ notifyFile: nf, workerMs: 30 });
const t = await L.ticket(s.api);
await L.assign(s.api, t.id, 'dana');
const lines = () => (L.fs.existsSync(nf) ? L.fs.readFileSync(nf, 'utf8').split('\\n').filter(Boolean).map((x) => JSON.parse(x)) : []);
await L.waitFor(() => lines().find((l) => l.to === 'dana'), 4000);
await sleep(500);
eq(lines().filter((l) => l.to === 'dana').length, 1, 'lines delivered to dana');
const sent = (await L.outbox(s.api)).sent.filter((e) => e.to === 'dana');
eq(sent.length, 1, 'one sent event');
""")
w("R-8.9", "Unassigning enqueues nothing.", """
const s = await L.startService();
const t = await L.ticket(s.api);
await L.assign(s.api, t.id, 'dana');
const before = await L.events(s.api);
await L.assign(s.api, t.id, null);
const after = await L.events(s.api);
eq(after.length, before.length, 'no event added by unassigning');
""")
w("R-8.10", "Re-assigning the same agent enqueues nothing, even after the first notice was delivered.", """
const s = await L.startService({ workerMs: 30 });
const t = await L.ticket(s.api);
await L.assign(s.api, t.id, 'dana');
const sent = await L.waitFor(async () => (await L.outbox(s.api)).sent.find((e) => e.type === 'ticket.assigned'), 4000);
check(sent, 'the first notice was delivered');
await L.assign(s.api, t.id, 'dana');
await sleep(300);
eq((await L.events(s.api, 'ticket.assigned')).length, 1, 'still one ticket.assigned event');
""")
w("R-8.12", "The template renders a subject naming the ticket (deliverable).", """
const nf = L.tmpfile('n.log');
const s = await L.startService({ notifyFile: nf, workerMs: 30 });
const t = await L.ticket(s.api, { title: 'Broken monitor' });
await L.assign(s.api, t.id, 'dana');
const lines = () => (L.fs.existsSync(nf) ? L.fs.readFileSync(nf, 'utf8').split('\\n').filter(Boolean).map((x) => JSON.parse(x)) : []);
const line = await L.waitFor(() => lines().find((l) => l.to === 'dana'), 4000);
check(line, 'the notice was delivered (not dead)');
check(line && (line.subject.includes(t.id) || line.subject.includes('Broken monitor')), 'subject names the ticket, got ' + (line && line.subject));
""")
w("R-8.13", "The template renders a body naming the ticket (deliverable).", """
const nf = L.tmpfile('n.log');
const s = await L.startService({ notifyFile: nf, workerMs: 30 });
const t = await L.ticket(s.api, { title: 'Broken monitor' });
await L.assign(s.api, t.id, 'dana');
const lines = () => (L.fs.existsSync(nf) ? L.fs.readFileSync(nf, 'utf8').split('\\n').filter(Boolean).map((x) => JSON.parse(x)) : []);
const line = await L.waitFor(() => lines().find((l) => l.to === 'dana'), 4000);
check(line, 'the notice was delivered (not dead)');
check(line && (line.body.includes(t.id) || line.body.includes('Broken monitor')), 'body names the ticket, got ' + (line && line.body));
""")
w("R-8.14", "A failing delivery is retried and eventually marked dead.", """
const blocker = L.tmpfile('blocker');
L.fs.writeFileSync(blocker, 'x');
const s = await L.startService({ notifyFile: blocker + '/n.log', workerMs: 20 });
const t = await L.ticket(s.api);
await L.assign(s.api, t.id, 'dana');
const outcome = await L.waitFor(async () => {
  const o = await L.outbox(s.api);
  const sent = o.sent.find((e) => e.type === 'ticket.assigned');
  if (sent) return { bad: 'sent', event: sent };
  const dead = o.dead.find((e) => e.type === 'ticket.assigned');
  return dead ? { event: dead } : null;
}, 22000, 100);
check(outcome, 'the failing ticket.assigned event reached a final state');
check(outcome && !outcome.bad, 'a failed delivery is not recorded as sent');
check(outcome && outcome.event && outcome.event.status === 'dead' && outcome.event.attempts === 5 && outcome.event.lastError, 'event is dead after 5 attempts with lastError: ' + JSON.stringify(outcome && outcome.event && { s: outcome.event.status, a: outcome.event.attempts }));
""")
w("R-8.15", "Returning to an agent whose earlier notice was delivered enqueues a new notice.", """
const s = await L.startService({ workerMs: 30 });
const t = await L.ticket(s.api);
await L.assign(s.api, t.id, 'dana');
const first = await L.waitFor(async () => (await L.outbox(s.api)).sent.find((e) => e.to === 'dana' && e.type === 'ticket.assigned'), 4000);
check(first, 'the first notice to dana was delivered');
await L.assign(s.api, t.id, 'erin');
await L.assign(s.api, t.id, 'dana');
await sleep(300);
const toDana = (await L.events(s.api, 'ticket.assigned')).filter((e) => e.to === 'dana');
eq(toDana.length, 2, 'two notices to dana in total');
""")

# ---------- R-9 ----------
w("R-9.1", "?assignee=dana lists only dana's tickets.", """
const s = await L.startService();
const a = await L.ticket(s.api, { title: 'A' });
const b = await L.ticket(s.api, { title: 'B' });
const c = await L.ticket(s.api, { title: 'C' });
await L.assign(s.api, a.id, 'dana');
await L.assign(s.api, b.id, 'erin');
const r = await s.api.get('/tickets?assignee=dana');
check(r.status === 200, 'answers 200');
eq(r.body.items.map((i) => i.id), [a.id], 'only dana\\'s ticket');
""")
w("R-9.2", "?assignee= lists only the unassigned tickets.", """
const s = await L.startService();
const a = await L.ticket(s.api, { title: 'A' });
const b = await L.ticket(s.api, { title: 'B' });
const c = await L.ticket(s.api, { title: 'C' });
await L.assign(s.api, a.id, 'dana');
await L.assign(s.api, b.id, 'erin');
const r = await s.api.get('/tickets?assignee=');
check(r.status === 200, 'answers 200');
eq(r.body.items.map((i) => i.id), [c.id], 'only the unassigned ticket');
""")
w("R-9.3", "A valid agent with no tickets lists nothing.", """
const s = await L.startService();
const a = await L.ticket(s.api, { title: 'A' });
await L.ticket(s.api, { title: 'B' });
await L.assign(s.api, a.id, 'dana');
const r = await s.api.get('/tickets?assignee=zed');
check(r.status === 200, 'answers 200');
eq(r.body.items.length, 0, 'no items for an agent with no tickets');
""")
w("R-9.4", "?status=open&priority=urgent lists only tickets that are both.", """
const s = await L.startService();
const a = await L.ticket(s.api, { title: 'open urgent', priority: 'urgent' });
const b = await L.ticket(s.api, { title: 'open low', priority: 'low' });
const c = await L.ticket(s.api, { title: 'wip urgent', priority: 'urgent' });
await L.advance(s.api, c.id, 'in_progress');
const r = await s.api.get('/tickets?status=open&priority=urgent');
eq(r.body.items.map((i) => i.id), [a.id], 'only the open urgent ticket');
""")
w("R-9.5", "?assignee=dana&status=open combines with AND.", """
const s = await L.startService();
const a = await L.ticket(s.api, { title: 'dana open' });
const b = await L.ticket(s.api, { title: 'dana wip' });
const c = await L.ticket(s.api, { title: 'erin open' });
const d = await L.ticket(s.api, { title: 'none open' });
await L.assign(s.api, a.id, 'dana');
await L.assign(s.api, b.id, 'dana');
await L.assign(s.api, c.id, 'erin');
await L.advance(s.api, b.id, 'in_progress');
const r = await s.api.get('/tickets?assignee=dana&status=open');
eq(r.body.items.map((i) => i.id), [a.id], 'only dana\\'s open ticket');
""")
w("R-9.6", "status, priority and assignee combine.", """
const s = await L.startService();
const a = await L.ticket(s.api, { title: 'A', priority: 'urgent' });
const b = await L.ticket(s.api, { title: 'B', priority: 'low' });
const c = await L.ticket(s.api, { title: 'C', priority: 'urgent' });
const d = await L.ticket(s.api, { title: 'D', priority: 'urgent' });
await L.assign(s.api, a.id, 'dana');
await L.assign(s.api, b.id, 'dana');
await L.assign(s.api, c.id, 'dana');
await L.assign(s.api, d.id, 'erin');
await L.advance(s.api, c.id, 'in_progress');
const r = await s.api.get('/tickets?status=open&priority=urgent&assignee=dana');
eq(r.body.items.map((i) => i.id), [a.id], 'only the ticket matching all three');
""")
w("R-9.8", "A filtered listing pages through its cursors without duplicates or gaps.", """
const s = await L.startService();
const mine = [];
for (let i = 0; i < 6; i += 1) {
  const t = await L.ticket(s.api, { title: 'T' + i });
  if (i % 3 !== 2) { await L.assign(s.api, t.id, 'dana'); mine.push(t.id); } else { await L.assign(s.api, t.id, 'erin'); }
}
const got = [];
let url = '/tickets?assignee=dana&limit=2';
for (let page = 0; page < 20; page += 1) {
  const r = await s.api.get(url);
  check(r.status === 200, 'page answers 200');
  got.push(...r.body.items.map((i) => i.id));
  if (!r.body.next) break;
  url = '/tickets?assignee=dana&limit=2&cursor=' + encodeURIComponent(r.body.next);
}
eq(got, mine, 'every dana ticket exactly once, in order');
""")
w("R-9.9", "A whitespace-only assignee filter answers 400 invalid.", """
const s = await L.startService();
await L.ticket(s.api);
for (const q of ['%20', '%20%20%20']) {
  const r = await s.api.get('/tickets?assignee=' + q);
  check(r.status === 400 && r.body.error.code === 'invalid', 'whitespace-only filter ' + q + ' -> 400 invalid, got ' + r.status);
}
""")
w("R-9.10", "An assignee filter longer than 64 characters answers 400 invalid.", """
const s = await L.startService();
await L.ticket(s.api);
const r = await s.api.get('/tickets?assignee=' + 'n'.repeat(65));
check(r.status === 400 && r.body.error.code === 'invalid', '65-character filter -> 400 invalid, got ' + r.status);
""")
w("R-9.11", "An assignee filter with a control character answers 400 invalid.", """
const s = await L.startService();
await L.ticket(s.api);
for (const q of ['a%09b', 'a%0Ab', 'a%01b', 'a%7Fb']) {
  const r = await s.api.get('/tickets?assignee=' + q);
  check(r.status === 400 && r.body.error.code === 'invalid', 'control-character filter ' + q + ' -> 400 invalid, got ' + r.status);
}
""")
w("R-9.12", "A 64-character assignee filter is accepted.", """
const s = await L.startService();
const t = await L.ticket(s.api);
const name = 'n'.repeat(64);
await L.assign(s.api, t.id, name);
const r = await s.api.get('/tickets?assignee=' + name);
check(r.status === 200, '64-character filter answers 200, got ' + r.status);
eq(r.body.items.map((i) => i.id), [t.id], 'finds the ticket');
""")

# ---------- R-10 ----------
CLI_SEED = """
const f = L.tmpfile('d.json');
const s = await L.startService({ dataFile: f });
const a = await L.ticket(s.api, { title: 'Alpha ticket', priority: 'urgent' });
const b = await L.ticket(s.api, { title: 'Bravo ticket', priority: 'low' });
const c = await L.ticket(s.api, { title: 'Charlie ticket', priority: 'normal' });
await L.assign(s.api, a.id, 'dana');
await L.assign(s.api, c.id, 'erin');
await L.advance(s.api, c.id, 'in_progress');
await s.stop();
"""
TABLE_CELL = """
const out = L.cli(['list'], f);
check(out.status === 0, 'list exits 0');
const lines = out.stdout.split('\\n').filter(Boolean);
const header = lines[0];
const start = header.indexOf('ASSIGNEE');
check(start >= 0, 'the header has an ASSIGNEE column: ' + header);
const next = header.indexOf('REQUESTER');
const cell = (title) => lines.find((l) => l.includes(title)).slice(start, next).trim();
"""
w("R-10.1", "The list table has an ASSIGNEE column showing the agent name.", CLI_SEED + TABLE_CELL + """
eq(cell('Alpha ticket'), 'dana', 'ASSIGNEE cell of the assigned ticket');
eq(cell('Charlie ticket'), 'erin', 'ASSIGNEE cell of the second assigned ticket');
""")
w("R-10.2", "The list table shows - for an unassigned ticket.", CLI_SEED + TABLE_CELL + """
eq(cell('Bravo ticket'), '-', 'ASSIGNEE cell of the unassigned ticket');
""")
RAW = """
const out = L.cli(['list', '--raw'], f);
check(out.status === 0, 'list --raw exits 0');
const rows = Object.fromEntries(out.stdout.split('\\n').filter(Boolean).map((l) => l.split('\\t')).map((c) => [c[3], c]));
"""
w("R-10.3", "list --raw appends the agent name as the fifth column.", CLI_SEED + RAW + """
eq(rows['Alpha ticket'] && rows['Alpha ticket'][4], 'dana', 'fifth column of the assigned ticket');
eq(rows['Charlie ticket'] && rows['Charlie ticket'][4], 'erin', 'fifth column of the second assigned ticket');
""")
w("R-10.4", "list --raw prints an empty fifth cell for an unassigned ticket.", CLI_SEED + RAW + """
const cells = rows['Bravo ticket'];
check(cells && cells.length === 5 && cells[4] === '', 'unassigned raw line has an empty fifth cell, got ' + JSON.stringify(cells));
""")
w("R-10.5", "list --raw columns 1-4 keep their positions.", CLI_SEED + RAW + """
eq(rows['Alpha ticket'] && rows['Alpha ticket'].slice(0, 4), [a.id, 'open', 'urgent', 'Alpha ticket'], 'columns 1-4 of Alpha');
eq(rows['Charlie ticket'] && rows['Charlie ticket'].slice(0, 4), [c.id, 'in_progress', 'normal', 'Charlie ticket'], 'columns 1-4 of Charlie');
eq(rows['Bravo ticket'] && rows['Bravo ticket'].slice(0, 4), [b.id, 'open', 'low', 'Bravo ticket'], 'columns 1-4 of Bravo');
""")
w("R-10.6", "The weekly report still counts by status and priority with assigned tickets.", CLI_SEED + """
const r = L.weekly(f);
check(r.status === 0, 'weekly report exits 0: ' + r.stderr);
const rep = JSON.parse(r.stdout);
eq(rep.total, 3, 'total');
eq(rep.byStatus.open, 2, 'open count');
eq(rep.byStatus.in_progress, 1, 'in_progress count');
eq([rep.byPriority.urgent, rep.byPriority.low, rep.byPriority.normal], [1, 1, 1], 'priority counts');
""")
w("R-10.7", "show lists assignee among the ticket's fields.", CLI_SEED + """
const out = L.cli(['show', a.id], f);
check(out.status === 0, 'show exits 0');
check(/^\\s*assignee\\s+dana\\s*$/m.test(out.stdout), 'show prints an assignee field with dana, got:\\n' + out.stdout);
""")


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    for id_, body in W.items():
        text = HEAD.format(id=id_, doc=DOC[id_]) + textwrap.indent(body.strip("\n"), "  ") + "\n" + TAIL
        open(os.path.join(OUT, f"{id_}.js"), "w").write(text)
    print(len(W), "witnesses written")
