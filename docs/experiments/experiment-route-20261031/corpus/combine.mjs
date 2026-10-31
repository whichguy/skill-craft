// Do a ticket-assignment product's filters combine as the request says ("a ticket must match every filter given")?
// Usage: node combine.mjs <product dir copy> <port>  -> one JSON line {statusPriority, assigneeStatus, error}
import { spawn } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

const [dir, portText] = process.argv.slice(2);
const base = `http://127.0.0.1:${portText}`;
const work = fs.mkdtempSync(path.join(os.tmpdir(), 'combine-'));
const child = spawn(process.execPath, ['src/server.js'], {
  cwd: dir, stdio: ['ignore', 'ignore', 'pipe'],
  env: { ...process.env, PORT: portText, DATA_FILE: path.join(work, 'data.json'), WORKER_INTERVAL_MS: '0' },
});
let stderr = '';
child.stderr.on('data', (d) => { stderr += d; });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const call = (m, p, b) => fetch(base + p, { method: m, headers: { 'content-type': 'application/json' },
  body: b === undefined ? undefined : JSON.stringify(b) }).then(async (r) => ({ status: r.status, body: await r.json().catch(() => null) }));
const out = {};
try {
  let up = false;
  for (let i = 0; i < 100 && !up; i += 1) { try { up = (await fetch(base + '/health')).ok; } catch { await sleep(50); } }
  if (!up) throw new Error('no start: ' + stderr.slice(0, 300));
  const mk = async (title, priority) => (await call('POST', '/tickets', { title, requester: 'c@example.com', priority })).body.id;
  const t1 = await mk('open urgent', 'urgent');
  const t2 = await mk('open normal', 'normal');
  const t3 = await mk('progress urgent', 'urgent');
  await call('POST', `/tickets/${t3}/transition`, { to: 'in_progress' });
  const sp = (await call('GET', '/tickets?status=open&priority=urgent')).body;
  const spIds = (sp?.items || []).map((t) => t.id);
  out.statusPriority = spIds.join(',') === t1 ? 'AND' : (spIds.length === 3 ? 'OR' : `other:${spIds.join(',')}`);
  await call('PUT', `/tickets/${t1}/assignee`, { assignee: 'ann' });
  await call('PUT', `/tickets/${t3}/assignee`, { assignee: 'ann' });
  const as = (await call('GET', '/tickets?assignee=ann&status=open')).body;
  const asIds = (as?.items || []).map((t) => t.id);
  out.assigneeStatus = asIds.join(',') === t1 ? 'AND' : (asIds.length >= 2 ? `OR:${asIds.join(',')}` : `other:${asIds.join(',')}`);
} catch (error) {
  out.error = String(error.message || error);
} finally {
  child.kill('SIGTERM');
  console.log(JSON.stringify(out));
}
