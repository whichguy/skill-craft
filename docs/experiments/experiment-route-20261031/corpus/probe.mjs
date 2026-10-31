// Probe node-tickets' documented behaviour (docs/api.md, docs/operations.md) against the running service.
// Usage: node probe.mjs <fixture dir> <port>   Prints one JSON line per claim: {claim, ok, expected, observed}.
import { spawn } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

const [fixture, portText] = process.argv.slice(2);
const port = Number(portText);
const base = `http://127.0.0.1:${port}`;
const work = fs.mkdtempSync(path.join(os.tmpdir(), 'probe-tickets-'));
const dataFile = path.join(work, 'data.json');
const notifyFile = path.join(work, 'notify.jsonl');
const results = [];
const record = (claim, ok, expected, observed) => {
  results.push({ claim, ok, expected, observed });
  console.log(JSON.stringify({ claim, ok, expected, observed }));
};

function start(extraEnv = {}) {
  const child = spawn(process.execPath, ['src/server.js'], {
    cwd: fixture,
    env: { ...process.env, PORT: String(port), DATA_FILE: dataFile, NOTIFY_FILE: notifyFile, WORKER_INTERVAL_MS: '50', ...extraEnv },
    stdio: ['ignore', 'ignore', 'pipe'],
  });
  child.stderrText = '';
  child.stderr.on('data', (d) => { child.stderrText += d; });
  return child;
}
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
async function ready() {
  for (let i = 0; i < 100; i += 1) {
    try { if ((await fetch(base + '/health')).ok) return; } catch { /* not yet */ }
    await sleep(50);
  }
  throw new Error('service did not start');
}
async function stop(child, signal = 'SIGTERM') {
  const done = new Promise((r) => child.once('exit', r));
  child.kill(signal);
  await done;
}
async function call(method, p, body, headers = {}) {
  const r = await fetch(base + p, { method, headers: { 'content-type': 'application/json', ...headers },
    body: body === undefined ? undefined : (typeof body === 'string' ? body : JSON.stringify(body)) });
  const text = await r.text();
  let json = null;
  try { json = JSON.parse(text); } catch { json = null; }
  return { status: r.status, body: json, text, type: r.headers.get('content-type') };
}
const make = (title, extra = {}, headers = {}) => call('POST', '/tickets', { title, requester: 'probe@example.com', ...extra }, headers);

let server = start();
try {
  await ready();
  // C1 content type
  const health = await call('GET', '/health');
  record('every response is application/json; charset=utf-8', health.type === 'application/json; charset=utf-8',
    'application/json; charset=utf-8', health.type);

  // C2/C9 create
  const a = await make('Alpha', { priority: 'urgent' });
  const b = await make('Beta');
  const c = await make('Gamma', { priority: 'urgent' });
  record('POST answers 201, status open, priority defaults to normal', a.status === 201 && b.body?.priority === 'normal' && b.body?.status === 'open',
    '201 / normal / open', `${a.status} / ${b.body?.priority} / ${b.body?.status}`);
  record('ids are T- and four digits, in order', [a, b, c].map((x) => x.body?.id).join(',') === 'T-0001,T-0002,T-0003',
    'T-0001,T-0002,T-0003', [a, b, c].map((x) => x.body?.id).join(','));
  record('a ticket has exactly id,title,priority,requester,status,created,updated',
    Object.keys(a.body || {}).sort().join(',') === 'created,id,priority,requester,status,title,updated',
    'created,id,priority,requester,status,title,updated', Object.keys(a.body || {}).sort().join(','));
  const iso = /^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{3}Z$/;
  record('times are ISO 8601 UTC with milliseconds', iso.test(a.body?.created || ''), '2025-09-01T08:15:00.000Z form', a.body?.created);

  // C10 filters combine
  await call('POST', `/tickets/${c.body.id}/transition`, { to: 'in_progress' });
  const both = await call('GET', '/tickets?status=open&priority=urgent');
  const ids = (both.body?.items || []).map((t) => t.id).join(',');
  record('filters combine (AND): ?status=open&priority=urgent lists only open urgent tickets', ids === 'T-0001', 'T-0001', ids);
  const bad = await call('GET', '/tickets?status=done');
  record('a filter value that is not a status is 400 invalid in the envelope', bad.status === 400 && bad.body?.error?.code === 'invalid',
    '400 invalid', `${bad.status} ${JSON.stringify(bad.body)}`);
  const unknownParam = await call('GET', '/tickets?colour=red');
  record('(undocumented) an unknown query parameter', true, 'not stated', `${unknownParam.status} items=${unknownParam.body?.items?.length}`);

  // C5 unknown fields
  const unknownField = await make('Delta', { severity: 'high' });
  record('unknown body fields are refused (400 invalid)', unknownField.status === 400 && unknownField.body?.error?.code === 'invalid',
    '400 invalid', `${unknownField.status} ${JSON.stringify(unknownField.body)}`);
  // C6 not_found route
  const noRoute = await call('GET', '/nowhere');
  record('no such route is 404 not_found in the envelope', noRoute.status === 404 && noRoute.body?.error?.code === 'not_found',
    '404 not_found', `${noRoute.status} ${JSON.stringify(noRoute.body)}`);
  const notJson = await call('POST', '/tickets', '{oops');
  record('a body that is not JSON is 400 invalid', notJson.status === 400 && notJson.body?.error?.code === 'invalid',
    '400 invalid', `${notJson.status} ${JSON.stringify(notJson.body)}`);

  // C8 limits
  const long = await make('x'.repeat(201));
  record('a title over 200 characters is 400', long.status === 400, '400', `${long.status} ${JSON.stringify(long.body)}`);
  const exact = await make('y'.repeat(200));
  record('a title of exactly 200 characters is accepted', exact.status === 201, '201', `${exact.status}`);
  const twoLines = await make('line one\nline two');
  record('a multi-line title is refused', twoLines.status === 400, '400', `${twoLines.status} ${JSON.stringify(twoLines.body)}`);
  const longRequester = await call('POST', '/tickets', { title: 'R', requester: 'r'.repeat(65) });
  record('a requester over 64 characters is 400', longRequester.status === 400, '400', `${longRequester.status}`);
  const padded = await make('  Padded title  ');
  record('(undocumented) surrounding spaces in a title', true, 'not stated', JSON.stringify(padded.body?.title));
  const emptyTitle = await make('   ');
  record('(undocumented) a blank title', true, 'not stated', `${emptyTitle.status} ${JSON.stringify(emptyTitle.body)}`);

  // C4 actor
  const audA = await call('GET', `/tickets/${a.body.id}/audit`);
  record('without X-Actor the actor is system', audA.body?.items?.[0]?.actor === 'system', 'system', audA.body?.items?.[0]?.actor);
  const longActor = await call('PATCH', `/tickets/${b.body.id}`, { title: 'Beta 2' }, { 'x-actor': 'a'.repeat(65) });
  record('an X-Actor over 64 characters is refused', longActor.status === 400, '400', `${longActor.status} ${JSON.stringify(longActor.body)}`);
  const blankActor = await call('PATCH', `/tickets/${b.body.id}`, { title: 'Beta 3' }, { 'x-actor': '   ' });
  const audB = await call('GET', `/tickets/${b.body.id}/audit`);
  record('(undocumented) a blank X-Actor', true, 'not stated', `${blankActor.status} actor=${JSON.stringify(audB.body?.items?.at(-1)?.actor)}`);

  // C13 PATCH no-op and closed
  const before = (await call('GET', `/tickets/${a.body.id}`)).body;
  await sleep(20);
  const same = await call('PATCH', `/tickets/${a.body.id}`, { title: before.title, priority: before.priority });
  const audA2 = await call('GET', `/tickets/${a.body.id}/audit`);
  record('PATCH with the same values changes nothing: no audit entry, updated stays',
    same.body?.updated === before.updated && audA2.body?.items?.length === audA.body?.items?.length,
    `updated ${before.updated}, ${audA.body?.items?.length} entries`, `updated ${same.body?.updated}, ${audA2.body?.items?.length} entries`);
  const emptyPatch = await call('PATCH', `/tickets/${a.body.id}`, {});
  record('(undocumented) an empty PATCH body', true, 'not stated', `${emptyPatch.status} ${JSON.stringify(emptyPatch.body)}`);

  // C14 lifecycle
  const t = (await make('Lifecycle')).body.id;
  const skip = await call('POST', `/tickets/${t}/transition`, { to: 'resolved' });
  record('open -> resolved is 409 conflict', skip.status === 409 && skip.body?.error?.code === 'conflict', '409 conflict', `${skip.status}`);
  const steps = [];
  for (const to of ['in_progress', 'resolved', 'open', 'in_progress', 'resolved', 'closed']) {
    steps.push(`${to}:${(await call('POST', `/tickets/${t}/transition`, { to })).status}`);
  }
  record('open->in_progress->resolved->open (reopen)->...->closed all allowed', steps.every((s) => s.endsWith(':200')), 'all 200', steps.join(' '));
  const afterClose = await call('PATCH', `/tickets/${t}`, { title: 'late' });
  record('a closed ticket cannot change (409)', afterClose.status === 409, '409', `${afterClose.status}`);
  const sameStatus = await call('POST', `/tickets/${b.body.id}/transition`, { to: 'open' });
  record('(undocumented) a transition to the status it already has', true, 'not stated', `${sameStatus.status} ${JSON.stringify(sameStatus.body?.error || sameStatus.body?.status)}`);

  // C15 audit
  const auditT = (await call('GET', `/tickets/${t}/audit`)).body?.items || [];
  const seqs = auditT.map((e) => e.seq);
  record('audit is oldest first with increasing seq', seqs.every((s, i) => i === 0 || s > seqs[i - 1]), 'increasing', seqs.join(','));

  // C16 outbox, dedup, worker
  await sleep(400);
  const box = (await call('GET', '/admin/outbox')).body;
  const kinds = (box?.sent || []).map((e) => e.type);
  record('creating notifies the requester (ticket.created sent)', kinds.includes('ticket.created'), 'ticket.created in sent', [...new Set(kinds)].join(','));
  const resolvedForT = (box?.sent || []).concat(box?.pending || []).filter((e) => e.ticket === t && e.type === 'ticket.resolved');
  record('(operations) resolved, reopened and resolved again within seconds sends one resolved notification',
    resolvedForT.length === 1, '1', `${resolvedForT.length} (worker 50 ms)`);
  const lines = fs.existsSync(notifyFile) ? fs.readFileSync(notifyFile, 'utf8').trim().split('\n').filter(Boolean) : [];
  record('NOTIFY_FILE gets one JSON line per sent notification', lines.length === (box?.sent || []).length, `${(box?.sent || []).length}`, `${lines.length}`);

  // C11 paging
  for (let i = 0; i < 22; i += 1) await make(`Bulk ${i}`);
  const p1 = await call('GET', '/tickets');
  record('limit defaults to 20 and next is a cursor', p1.body?.items?.length === 20 && typeof p1.body?.next === 'string', '20 + cursor',
    `${p1.body?.items?.length} + ${typeof p1.body?.next}`);
  const cursorOtherFilter = await call('GET', `/tickets?status=closed&cursor=${p1.body.next}`);
  record('(undocumented) a cursor reused with different filters', true, 'not stated', `${cursorOtherFilter.status} items=${cursorOtherFilter.body?.items?.length}`);
  const badCursor = await call('GET', '/tickets?cursor=abc');
  record('a cursor the service did not issue is invalid', badCursor.status === 400, '400', `${badCursor.status}`);

  // O2/O7 restart keeps state and numbers
  const countBefore = JSON.parse(fs.readFileSync(dataFile, 'utf8')).tickets.length;
  await stop(server, 'SIGTERM');
  server = start();
  await ready();
  const afterRestart = await make('After restart');
  record('after a SIGTERM restart, state is kept and numbers continue',
    afterRestart.body?.id === `T-${String(countBefore + 1).padStart(4, '0')}`, `T-${String(countBefore + 1).padStart(4, '0')}`, afterRestart.body?.id);
  // O1 data file written after every change, even with SIGKILL
  const killed = await make('Before kill');
  await stop(server, 'SIGKILL');
  const onDisk = JSON.parse(fs.readFileSync(dataFile, 'utf8')).tickets.some((x) => x.id === killed.body?.id);
  record('the data file holds a change at once (survives SIGKILL)', onDisk, 'present', onDisk ? 'present' : 'missing');
  server = start({ WORKER_INTERVAL_MS: '0' });
  await ready();
  const pendingCheck = await make('Pending only');
  await sleep(200);
  const box2 = (await call('GET', '/admin/outbox')).body;
  record('WORKER_INTERVAL_MS=0 keeps notifications pending',
    (box2?.pending || []).some((e) => e.ticket === pendingCheck.body?.id), 'pending', JSON.stringify((box2?.pending || []).map((e) => e.ticket)));
} catch (error) {
  console.log(JSON.stringify({ claim: 'probe error', ok: false, observed: String(error && error.stack || error) }));
} finally {
  if (server && server.exitCode === null) await stop(server, 'SIGTERM');
  const drift = results.filter((r) => r.ok === false);
  console.log(JSON.stringify({ summary: `${results.length} claims, ${drift.length} drift`, drift: drift.map((r) => r.claim), work }));
}
