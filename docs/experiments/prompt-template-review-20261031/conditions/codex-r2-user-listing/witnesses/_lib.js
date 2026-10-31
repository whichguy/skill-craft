'use strict';
// Shared helper for the independent witnesses of run codex-r2-user-listing.
// A witness starts the product with `node src/server.js` (the CLI entry point) on a port in 41500-41599 and checks one
// condition over HTTP. WORK is the directory holding the product copy under test (default: the scratch copy).
// Exit 0 = the condition holds; exit 1 = it does not (or the server died).
const { spawn } = require('node:child_process');
const net = require('node:net');
const path = require('node:path');
const assert = require('node:assert/strict');

const WORK = process.env.WORK ||
  '/private/tmp/claude-501/-Users-dadleet-src-skill-craft/ddd28884-3bee-490a-b072-5207d26ab322/scratchpad/conditions/codex-r2-user-listing/work';
const LO = 41500;
const HI = 41599;

const U = [
  { id: 1, name: 'Ada Lovelace', email: 'ada@example.com' },
  { id: 2, name: 'Grace Hopper', email: 'grace@example.com' },
  { id: 3, name: 'Alan Turing', email: 'alan@example.com' },
];

function portFree(port) {
  return new Promise((resolve) => {
    const s = net.createServer();
    s.once('error', () => resolve(false));
    s.listen(port, '127.0.0.1', () => s.close(() => resolve(true)));
  });
}

async function pickPort() {
  const seed = [...path.basename(process.argv[1])].reduce((a, c) => (a * 31 + c.charCodeAt(0)) >>> 0, 7);
  for (let i = 0; i < 100; i++) {
    const port = LO + ((seed + i) % (HI - LO + 1));
    if (await portFree(port)) return port;
  }
  throw new Error('no free port in 41500-41599');
}

async function withServer(fn) {
  const port = await pickPort();
  const child = spawn(process.execPath, [path.join(WORK, 'src/server.js')], {
    cwd: WORK,
    env: { ...process.env, PORT: String(port) },
    stdio: ['ignore', 'pipe', 'pipe'],
  });
  let log = '';
  child.stderr.on('data', (c) => { log += c; });
  await new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error('server did not start')), 5000);
    child.once('exit', (code) => { clearTimeout(timer); reject(new Error(`server exited early: ${code}`)); });
    child.stdout.on('data', (c) => { if (String(c).includes(`listening on ${port}`)) { clearTimeout(timer); resolve(); } });
  });
  const get = async (query, p = '/users') => {
    const res = await fetch(`http://127.0.0.1:${port}${p}${query}`);
    const text = await res.text();
    let json;
    try { json = JSON.parse(text); } catch { json = undefined; }
    return { status: res.status, type: res.headers.get('content-type') || '', text, json };
  };
  try {
    await fn({ get });
  } catch (error) {
    throw new Error(`${error.message}${log ? `\n[server stderr] ${log.slice(0, 300)}` : ''}`);
  } finally {
    child.removeAllListeners('exit');
    child.kill('SIGKILL');
  }
}

function run(fn) {
  withServer(fn).then(
    () => { process.exit(0); },
    (error) => { console.error(`WITNESS FAIL: ${String(error.message).split('\n').slice(0, 6).join('\n')}`); process.exit(1); },
  );
}

module.exports = { run, U, eq: assert.deepStrictEqual, ok: assert.ok, equal: assert.strictEqual };
