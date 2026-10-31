'use strict';

/**
 * Shared helpers for the per-condition witnesses of the bf-ds-ticket-assignment condition test.
 *
 * A witness is an independent, black-box check of one spec condition. It starts the helpdesk service (or the CLI) as a
 * child process from the checkout named by $WORK, talks to it over HTTP / the command line, and exits 0 when the
 * condition holds, 1 when a check fails, 2 when the witness itself crashes. It never imports the product code and never
 * reuses the run's tests. Ports come from 41200-41299.
 */

const { spawn, spawnSync } = require('node:child_process');
const fs = require('node:fs');
const net = require('node:net');
const os = require('node:os');
const path = require('node:path');

const WORK = process.env.WORK || '/private/tmp/claude-501/-Users-dadleet-src-skill-craft/ddd28884-3bee-490a-b072-5207d26ab322/scratchpad/conditions/bf-ds-ticket-assignment/work';
const TMP_ROOT = process.env.WITNESS_TMP || '/private/tmp/claude-501/-Users-dadleet-src-skill-craft/ddd28884-3bee-490a-b072-5207d26ab322/scratchpad/conditions/bf-ds-ticket-assignment/wtmp';
const PORT_LO = 41200;
const PORT_HI = 41299;

const failures = [];
const running = [];

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

function check(condition, message) {
  if (!condition) {
    failures.push(message);
    process.stderr.write(`FAIL: ${message}\n`);
  }
  return Boolean(condition);
}

function eq(actual, expected, message) {
  const a = JSON.stringify(actual);
  const e = JSON.stringify(expected);
  return check(a === e, `${message}: expected ${e}, got ${a}`);
}

function tmpdir() {
  fs.mkdirSync(TMP_ROOT, { recursive: true });
  return fs.mkdtempSync(path.join(TMP_ROOT, 'w-'));
}

function tmpfile(name = 'f') {
  return path.join(tmpdir(), name);
}

async function freePort() {
  for (let attempt = 0; attempt < 200; attempt += 1) {
    const port = PORT_LO + Math.floor(Math.random() * (PORT_HI - PORT_LO + 1));
    const ok = await new Promise((resolve) => {
      const probe = net.createServer();
      probe.once('error', () => resolve(false));
      probe.listen(port, () => probe.close(() => resolve(true)));
    });
    if (ok) return port;
  }
  throw new Error('no free port in 41200-41299');
}

function envFor(port, { dataFile, notifyFile, workerMs }) {
  const env = { ...process.env, PORT: String(port), WORKER_INTERVAL_MS: String(workerMs || 0) };
  delete env.DATA_FILE;
  delete env.NOTIFY_FILE;
  delete env.LOG_REQUESTS;
  if (dataFile) env.DATA_FILE = dataFile;
  if (notifyFile) env.NOTIFY_FILE = notifyFile;
  return env;
}

function makeApi(port) {
  async function call(method, p, body, headers = {}, raw) {
    const init = { method, headers: { ...headers } };
    if (raw !== undefined) {
      init.body = raw;
      init.headers['content-type'] = 'application/json';
    } else if (body !== undefined) {
      init.body = JSON.stringify(body);
      init.headers['content-type'] = 'application/json';
    }
    const res = await fetch(`http://127.0.0.1:${port}${p}`, init);
    const text = await res.text();
    let parsed = null;
    try { parsed = text ? JSON.parse(text) : null; } catch { parsed = text; }
    return { status: res.status, body: parsed };
  }
  return {
    get: (p, h) => call('GET', p, undefined, h),
    post: (p, b, h) => call('POST', p, b, h),
    put: (p, b, h) => call('PUT', p, b, h),
    patch: (p, b, h) => call('PATCH', p, b, h),
    putRaw: (p, rawText, h) => call('PUT', p, undefined, h, rawText),
  };
}

/** Start the service. Resolves { port, api, stop() }; rejects with { exitCode, stderr } when it refuses to start. */
async function startService(opts = {}) {
  const port = await freePort();
  const child = spawn(process.execPath, ['src/server.js'], { cwd: WORK, env: envFor(port, opts), stdio: ['ignore', 'pipe', 'pipe'] });
  let stderr = '';
  let stdout = '';
  child.stderr.on('data', (d) => { stderr += d; });
  child.stdout.on('data', (d) => { stdout += d; });
  const exited = new Promise((resolve) => child.once('exit', (code, signal) => resolve({ code, signal })));
  const entry = { child, exited };
  running.push(entry);
  const started = await Promise.race([
    (async () => {
      for (let i = 0; i < 400; i += 1) {
        if (/tickets listening on/.test(stderr + stdout)) return true;
        await sleep(10);
      }
      return false;
    })(),
    exited.then(() => false),
  ]);
  if (!started) {
    const info = await Promise.race([exited, sleep(200).then(() => ({ code: null }))]);
    child.kill('SIGKILL');
    const error = new Error('service did not start');
    error.exitCode = info.code;
    error.stderr = stderr + stdout;
    throw error;
  }
  return {
    port,
    api: makeApi(port),
    child,
    stderr: () => stderr,
    async stop() {
      if (child.exitCode !== null || child.signalCode) return;
      child.kill('SIGTERM');
      await Promise.race([exited, sleep(3000)]);
      if (child.exitCode === null && !child.signalCode) child.kill('SIGKILL');
    },
  };
}

/** Try to start the service; resolves { started, exitCode, stderr } and never rejects for a refused start. */
async function tryStart(opts = {}) {
  try {
    const svc = await startService(opts);
    await svc.stop();
    return { started: true, exitCode: 0, stderr: '' };
  } catch (error) {
    if (error.stderr === undefined) throw error;
    return { started: false, exitCode: error.exitCode, stderr: error.stderr };
  }
}

const NEW = { title: 'Printer jam', requester: 'robin', priority: 'normal' };

async function ticket(api, over = {}) {
  const r = await api.post('/tickets', { ...NEW, ...over });
  if (r.status !== 201) throw new Error(`create failed ${r.status} ${JSON.stringify(r.body)}`);
  return r.body;
}

/** Move a ticket along its lifecycle to `to`: open -> in_progress -> resolved -> closed. */
async function advance(api, id, to) {
  const path = ['in_progress', 'resolved', 'closed'];
  for (const step of path) {
    const r = await api.post(`/tickets/${id}/transition`, { to: step });
    if (r.status !== 200) throw new Error(`transition to ${step} failed ${r.status} ${JSON.stringify(r.body)}`);
    if (step === to) return r.body;
  }
  throw new Error(`cannot advance to ${to}`);
}

async function assign(api, id, assignee, headers) {
  return api.put(`/tickets/${id}/assignee`, { assignee }, headers);
}

async function auditOf(api, id) {
  const r = await api.get(`/tickets/${id}/audit`);
  return r.body.items;
}

async function outbox(api) {
  const r = await api.get('/admin/outbox');
  return r.body;
}

async function events(api, type) {
  const o = await outbox(api);
  const all = [...o.pending, ...o.sent, ...o.dead];
  return type ? all.filter((e) => e.type === type) : all;
}

function readJson(file) { return JSON.parse(fs.readFileSync(file, 'utf8')); }
function writeJson(file, value) { fs.writeFileSync(file, `${JSON.stringify(value, null, 2)}\n`); }

function cli(args, dataFile) {
  const r = spawnSync(process.execPath, ['bin/tickets.js', ...(dataFile ? ['--data', dataFile] : []), ...args], { cwd: WORK, encoding: 'utf8' });
  return { status: r.status, stdout: r.stdout, stderr: r.stderr };
}

function weekly(dataFile) {
  const r = spawnSync(process.execPath, ['scripts/weekly-report.js', '--data', dataFile, '--json'], { cwd: WORK, encoding: 'utf8' });
  return { status: r.status, stdout: r.stdout, stderr: r.stderr };
}

/** A data file with one ticket in it, then `mutate(doc)` applied to the parsed document. Returns the file path. */
async function seedFile(mutate) {
  const file = tmpfile('d.json');
  const s = await startService({ dataFile: file });
  await ticket(s.api);
  await s.stop();
  const doc = readJson(file);
  mutate(doc);
  writeJson(file, doc);
  return file;
}

async function waitFor(fn, ms = 4000, step = 20) {
  const end = Date.now() + ms;
  for (;;) {
    const v = await fn();
    if (v) return v;
    if (Date.now() > end) return null;
    await sleep(step);
  }
}

/** Run a witness body; exit 0 / 1 / 2. */
async function run(body) {
  let code = 0;
  try {
    await body();
    code = failures.length ? 1 : 0;
  } catch (error) {
    process.stderr.write(`WITNESS ERROR: ${error.stack || error}\n`);
    code = failures.length ? 1 : 2;
  } finally {
    for (const { child } of running) {
      if (child.exitCode === null && !child.signalCode) child.kill('SIGKILL');
    }
  }
  process.exit(code);
}

module.exports = {
  NEW, WORK, advance, assign, auditOf, check, cli, eq, events, outbox, readJson, run, sleep, startService,
  seedFile, ticket, tmpdir, tmpfile, tryStart, waitFor, weekly, writeJson, os, fs, path,
};
