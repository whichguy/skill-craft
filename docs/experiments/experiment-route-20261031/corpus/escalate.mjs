// ticket-escalation: "A ticket is escalated at most once, even across restarts of the service."
// Counts outbox entries to ONCALL naming the ticket: after the first escalation, after a SIGTERM restart, after a SIGKILL
// restart. Usage: node escalate.mjs <product dir copy> <port> -> {first, afterTerm, afterKill, error}
import { spawn } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

const [dir, portText] = process.argv.slice(2);
const base = `http://127.0.0.1:${portText}`;
const work = fs.mkdtempSync(path.join(os.tmpdir(), 'escalate-'));
const env = { ...process.env, PORT: portText, DATA_FILE: path.join(work, 'data.json'), ONCALL: 'oncall.agent',
  ESCALATE_AFTER_MINUTES: '0', WORKER_INTERVAL_MS: '50' };
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const call = (m, p, b) => fetch(base + p, { method: m, headers: { 'content-type': 'application/json' },
  body: b === undefined ? undefined : JSON.stringify(b) }).then(async (r) => ({ status: r.status, body: await r.json().catch(() => null) }));
function start() {
  const child = spawn(process.execPath, ['src/server.js'], { cwd: dir, env, stdio: ['ignore', 'ignore', 'pipe'] });
  child.err = '';
  child.stderr.on('data', (d) => { child.err += d; });
  return child;
}
async function up(child) {
  for (let i = 0; i < 100; i += 1) {
    if (child.exitCode !== null) return false;
    try { if ((await fetch(base + '/health')).ok) return true; } catch { /* not yet */ }
    await sleep(50);
  }
  return false;
}
const stop = (child, signal) => new Promise((r) => { if (child.exitCode !== null) return r(); child.once('exit', r); child.kill(signal); });
async function count(id) {
  const box = (await call('GET', '/admin/outbox')).body || {};
  return [...(box.pending || []), ...(box.sent || []), ...(box.dead || [])]
    .filter((e) => e && e.to === 'oncall.agent' && JSON.stringify(e).includes(id)).length;
}
const out = {};
let child = start();
try {
  if (!(await up(child))) throw new Error('start failed: ' + child.err.slice(0, 200));
  const id = (await call('POST', '/tickets', { title: 'Escalate me', requester: 'e@example.com', priority: 'urgent' })).body.id;
  for (let i = 0; i < 100 && (await count(id)) === 0; i += 1) await sleep(50);
  await sleep(500);
  out.first = await count(id);
  await stop(child, 'SIGTERM');
  child = start();
  if (!(await up(child))) throw new Error('restart failed: ' + child.err.slice(-200));
  await sleep(1000);
  out.afterTerm = await count(id);
  await stop(child, 'SIGKILL');
  child = start();
  if (!(await up(child))) throw new Error('restart after kill failed: ' + child.err.slice(-200));
  await sleep(1000);
  out.afterKill = await count(id);
} catch (error) {
  out.error = String(error.message || error);
} finally {
  await stop(child, 'SIGTERM');
  console.log(JSON.stringify(out));
}
