// Does a ticket-assignment product keep a ticket's assignee across a restart of the service (DATA_FILE set)?
// Usage: node restart.mjs <product dir copy> <port> -> {beforeRestart, afterRestart, startError}
import { spawn } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

const [dir, portText] = process.argv.slice(2);
const base = `http://127.0.0.1:${portText}`;
const work = fs.mkdtempSync(path.join(os.tmpdir(), 'restart-'));
const env = { ...process.env, PORT: portText, DATA_FILE: path.join(work, 'data.json'), WORKER_INTERVAL_MS: '0' };
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
const out = {};
let child = start();
try {
  if (!(await up(child))) throw new Error('first start failed: ' + child.err.slice(0, 200));
  const id = (await call('POST', '/tickets', { title: 'Restart check', requester: 'r@example.com' })).body.id;
  const put = await call('PUT', `/tickets/${id}/assignee`, { assignee: 'ann' });
  out.put = put.status;
  out.beforeRestart = (await call('GET', `/tickets/${id}`)).body?.assignee;
  await stop(child, 'SIGTERM');
  child = start();
  if (!(await up(child))) { out.startError = child.err.trim().split('\n').slice(-2).join(' | ').slice(0, 300); throw new Error('restart failed'); }
  out.afterRestart = (await call('GET', `/tickets/${id}`)).body?.assignee;
  out.filterAfterRestart = ((await call('GET', '/tickets?assignee=ann')).body?.items || []).map((t) => t.id).join(',') === id;
} catch (error) {
  out.error = String(error.message || error);
} finally {
  await stop(child, 'SIGTERM');
  console.log(JSON.stringify(out));
}
