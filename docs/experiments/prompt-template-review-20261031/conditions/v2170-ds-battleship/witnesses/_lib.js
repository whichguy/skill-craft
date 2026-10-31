'use strict';
// Shared helpers for the condition witnesses. A witness is run as `WORK=<checkout> node R-n.k.js`;
// exit 0 = the condition holds, non-zero = it is violated. Everything that listens uses the
// worker's port range 41100-41199.
const path = require('node:path');
const http = require('node:http');
const net = require('node:net');
const cp = require('node:child_process');
const fs = require('node:fs');
const os = require('node:os');

const WORK = process.env.WORK;
if (!WORK) { console.error('WORK is not set'); process.exit(2); }
const LO = 41100, HI = 41199;

const rules = () => require(path.join(WORK, 'battleship.js'));
const serverModule = () => require(path.join(WORK, 'server.js'));

function seeded(a) { // mulberry32
  return function () {
    a |= 0; a = (a + 0x6D2B79F5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

function canBind(port) {
  return new Promise((resolve) => {
    const s = net.createServer();
    s.once('error', () => resolve(false));
    s.listen(port, '127.0.0.1', () => s.close(() => resolve(true)));
  });
}
async function freePort() {
  for (let i = 0; i < 200; i++) {
    const p = LO + Math.floor(Math.random() * (HI - LO + 1));
    if (await canBind(p)) return p;
  }
  throw new Error('no free port in range');
}

// A request to 127.0.0.1:port. opts: {body (string|Buffer), headers, host}
function req(port, method, p, opts = {}) {
  return new Promise((resolve, reject) => {
    const r = http.request({ host: opts.host || '127.0.0.1', port, method, path: p, headers: opts.headers || {} }, (res) => {
      const chunks = [];
      res.on('data', (c) => chunks.push(c));
      res.on('end', () => {
        const text = Buffer.concat(chunks).toString('utf8');
        let json;
        try { json = JSON.parse(text); } catch { json = undefined; }
        resolve({ status: res.statusCode, headers: res.headers, text, json });
      });
    });
    r.on('error', reject);
    if (opts.body !== undefined) r.write(opts.body);
    r.end();
  });
}
const getJson = (port, p) => req(port, 'GET', p);
const fire = (port, game, row, col) => req(port, 'POST', '/api/fire',
  { headers: { 'content-type': 'application/json' }, body: JSON.stringify({ game, row, col }) });
const rawFire = (port, body) => req(port, 'POST', '/api/fire', { headers: { 'content-type': 'application/json' }, body });

// In-process server on a port of the range, with an optional injected random source.
async function inproc(opts = {}) {
  const { createServer } = serverModule();
  const server = createServer(opts);
  const port = await freePort();
  await new Promise((resolve, reject) => { server.once('error', reject); server.listen(port, '127.0.0.1', resolve); });
  return { server, port, close: () => new Promise((r) => { server.closeAllConnections?.(); server.close(() => r()); }) };
}

// A child `node server.js` on a port of the range (or with the given env). Collects output.
function spawnServer({ env = {}, args = [], port, cwd = WORK, noPort = false } = {}) {
  const e = { ...process.env, ...env };
  if (port !== undefined && !noPort) e.PORT = String(port);
  const child = cp.spawn(process.execPath, [...args, 'server.js'], { cwd, env: e, stdio: ['ignore', 'pipe', 'pipe'] });
  const rec = { child, stdout: '', stderr: '', exited: null };
  child.stdout.on('data', (d) => { rec.stdout += d; });
  child.stderr.on('data', (d) => { rec.stderr += d; });
  rec.exitP = new Promise((r) => child.once('exit', (code, sig) => { rec.exited = { code, sig }; r(rec.exited); }));
  rec.kill = async () => { if (rec.exited === null) { child.kill('SIGKILL'); await rec.exitP; } };
  return rec;
}
async function waitFor(fn, ms, what) {
  const t0 = Date.now();
  for (;;) {
    const v = await fn();
    if (v) return v;
    if (Date.now() - t0 > ms) throw new Error('timeout waiting for ' + what);
    await sleep(25);
  }
}
function lsofPorts(pid) {
  try {
    const out = cp.execFileSync('lsof', ['-nP', '-a', '-p', String(pid), '-iTCP', '-sTCP:LISTEN', '-Fn'], { encoding: 'utf8' });
    return out.split('\n').filter((l) => l.startsWith('n')).map((l) => l.slice(1));
  } catch { return []; }
}
// Start `node server.js` with PORT set to portValue (undefined = unset) and report where it listens:
// {kind:'listening', ports} (lsof of the child), {kind:'refused', port} (in-use message), or died/timeout.
async function listenReport(portValue) {
  // portValue === undefined means PORT unset
  const e = { ...process.env };
  delete e.PORT;
  if (portValue !== undefined) e.PORT = portValue;
  const child = cp.spawn(process.execPath, ['server.js'], { cwd: WORK, env: e, stdio: ['ignore', 'pipe', 'pipe'] });
  let out = '', err = '', exited = null;
  child.stdout.on('data', (d) => { out += d; });
  child.stderr.on('data', (d) => { err += d; });
  child.once('exit', (code, sig) => { exited = { code, sig }; });
  const t0 = Date.now();
  let result;
  for (;;) {
    await sleep(40);
    const ls = lsofPorts(child.pid);
    if (ls.length) { result = { kind: 'listening', addrs: ls, ports: ls.map((a) => Number(a.split(':').pop())) }; break; }
    if (exited) { result = { kind: 'died', exited, out, err }; break; }
    const m = /port (\d+) is already in use/.exec(out + err);
    if (m) { result = { kind: 'refused', port: Number(m[1]) }; break; }
    if (Date.now() - t0 > 6000) { result = { kind: 'timeout', out, err }; break; }
  }
  result.out = out; result.err = err;
  if (exited === null) { child.kill('SIGKILL'); }
  return result;
}

function check(cond, msg) { if (!cond) throw new Error('VIOLATED: ' + msg); }
function run(fn) {
  Promise.resolve().then(fn).then(() => { console.log('HOLDS'); process.exit(0); },
    (e) => { console.log(String(e && e.message || e)); process.exit(1); });
}

// Model of the game used to predict results independently of fire(): from the product's fleet only.
function modelFor(fleet) {
  const owner = new Map();
  fleet.forEach((ship, i) => ship.cells.forEach((c) => owner.set(c.row + ',' + c.col, i)));
  const left = fleet.map((s) => s.cells.length);
  return {
    owner,
    expect(row, col) { // returns the result the rules must report and updates the model
      const i = owner.get(row + ',' + col);
      if (i === undefined) return 'miss';
      left[i] -= 1;
      return left[i] === 0 ? 'sunk' : 'hit';
    },
    remaining() { return left.filter((n) => n > 0).length; },
  };
}
// The fleet a seeded in-process server deals to its first game.
function fleetOf(seed) { return rules().createGame({ random: seeded(seed) }).fleet; }

module.exports = { WORK, LO, HI, rules, serverModule, seeded, sleep, freePort, req, getJson, fire, rawFire, inproc,
  spawnServer, waitFor, lsofPorts, listenReport, check, run, modelFor, fleetOf, fs, os, path, cp, net, http };
