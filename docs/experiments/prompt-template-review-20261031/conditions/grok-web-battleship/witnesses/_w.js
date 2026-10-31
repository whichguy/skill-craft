'use strict';
// Witness infrastructure for the grok-web-battleship condition test.
// A witness exits 0 when the condition HOLDS on the product under WORK, 1 when it is VIOLATED,
// 3 when the witness itself broke. Nothing here reads the run's tests.

const { spawn, execFileSync } = require('node:child_process');
const http = require('node:http');
const net = require('node:net');
const path = require('node:path');
const fs = require('node:fs');

const SCRATCH = '/private/tmp/claude-501/-Users-dadleet-src-skill-craft/ddd28884-3bee-490a-b072-5207d26ab322/scratchpad/conditions/grok-web-battleship';
const WORK = process.env.WORK || path.join(SCRATCH, 'work');
const PORT_LO = Number(process.env.WPORT_LO || 41300);
const PORT_HI = Number(process.env.WPORT_HI || 41389);
const CDP_LO = 41390;
const CDP_HI = 41399;
const CHROME = '/Users/dadleet/.cache/puppeteer/chrome-headless-shell/mac_arm-151.0.7922.47/chrome-headless-shell-mac-arm64/chrome-headless-shell';

class Violation extends Error {}
const cleanups = [];

function check(cond, msg) {
  if (!cond) throw new Violation(msg);
}
function eq(actual, expected, msg) {
  const a = JSON.stringify(actual);
  const e = JSON.stringify(expected);
  if (a !== e) throw new Violation(`${msg}: got ${a} expected ${e}`);
}
function delay(ms) {
  return new Promise((r) => setTimeout(r, ms));
}

// ---------- ports and processes
function canListen(port) {
  return new Promise((resolve) => {
    const s = net.createServer();
    s.once('error', () => resolve(false));
    s.listen(port, '127.0.0.1', () => s.close(() => resolve(true)));
  });
}
async function freePort(lo = PORT_LO, hi = PORT_HI) {
  for (let i = 0; i < 60; i += 1) {
    const p = lo + Math.floor(Math.random() * (hi - lo + 1));
    if (await canListen(p)) return p;
  }
  throw new Error('no free port in range');
}
function connect(port) {
  return new Promise((resolve) => {
    const s = net.connect({ host: '127.0.0.1', port });
    const done = (ok) => { s.removeAllListeners(); s.destroy(); resolve(ok); };
    s.once('connect', () => done(true));
    s.once('error', () => done(false));
  });
}
function listening(pid) {
  try {
    return execFileSync('lsof', ['-nP', '-p', String(pid), '-a', '-iTCP', '-sTCP:LISTEN'], { encoding: 'utf8' });
  } catch (e) {
    if (e.status === 1) return '';
    throw e;
  }
}

// Spawn `node [nodeArgs] server.js` in WORK. env: object; keys with value undefined are removed.
function spawnServer(env = {}, nodeArgs = [], extraOptions = '') {
  const e = { ...process.env, ...env };
  for (const k of Object.keys(e)) if (e[k] === undefined) delete e[k];
  if (extraOptions) e.NODE_OPTIONS = ((e.NODE_OPTIONS || '') + ' ' + extraOptions).trim();
  const child = spawn(process.execPath, [...nodeArgs, 'server.js'], { cwd: WORK, env: e, stdio: ['ignore', 'ignore', 'pipe'] });
  child.stderrText = '';
  child.stderr.on('data', (c) => { child.stderrText += c; });
  child.exited = new Promise((resolve) => child.once('exit', (code, sig) => resolve({ code, sig })));
  cleanups.push(() => { try { child.kill('SIGKILL'); } catch (e2) { /* gone */ } });
  return child;
}
async function waitUp(child, port, ms = 5000) {
  const deadline = Date.now() + ms;
  while (Date.now() < deadline) {
    if (child.exitCode !== null || child.signalCode !== null) return false;
    if (await connect(port)) return true;
    await delay(30);
  }
  return false;
}
async function stopServer(child) {
  if (child.exitCode !== null || child.signalCode !== null) return;
  child.kill('SIGTERM');
  await Promise.race([child.exited, delay(2000)]);
  if (child.exitCode === null && child.signalCode === null) {
    child.kill('SIGKILL');
    await Promise.race([child.exited, delay(2000)]);
  }
}
async function startServer(opts = {}) {
  const port = opts.port || (await freePort());
  const child = spawnServer({ PORT: String(port), ...(opts.env || {}) }, [], opts.nodeOptions || '');
  const up = await waitUp(child, port);
  check(up, 'server did not accept a connection on ' + port + ': ' + child.stderrText);
  return { child, port, stop: () => stopServer(child) };
}

// Preload that remaps listen(3000|3456) to ports in our range, so a witness never binds a shared port.
const REMAP = path.join(__dirname, '_remap.js');
const DETID = path.join(__dirname, '_detid.js');
function remapOptions(map, logFile) {
  return { env: { REMAP: map.map(([a, b]) => a + ':' + b).join(','), REMAP_LOG: logFile }, options: '--require=' + REMAP };
}

// ---------- HTTP
function req(port, method, p, body, headers = {}) {
  return new Promise((resolve, reject) => {
    const h = { ...headers };
    let payload;
    if (body !== undefined) {
      payload = typeof body === 'string' ? body : JSON.stringify(body);
      if (!Object.keys(h).some((k) => k.toLowerCase() === 'content-type')) h['content-type'] = 'application/json';
    }
    const r = http.request({ host: '127.0.0.1', port, method, path: p, headers: h, agent: false }, (res) => {
      const chunks = [];
      res.on('data', (c) => chunks.push(c));
      res.on('end', () => {
        const text = Buffer.concat(chunks).toString('utf8');
        let json;
        try { json = JSON.parse(text); } catch (e) { json = undefined; }
        resolve({ status: res.statusCode, type: String(res.headers['content-type'] || ''), headers: res.headers, text, json });
      });
    });
    r.on('error', reject);
    r.setTimeout(8000, () => r.destroy(new Error('request timeout')));
    if (payload !== undefined) r.write(payload);
    r.end();
  });
}
async function newGame(port) {
  const r = await req(port, 'GET', '/api/new');
  check(r.status === 200 && r.json && typeof r.json.game === 'string' && r.json.game.length > 0, 'GET /api/new gave no game: ' + r.status + ' ' + r.text);
  return r.json.game;
}
function fire(port, game, row, col) {
  return req(port, 'POST', '/api/fire', { game, row, col });
}
// Fire all 100 cells in row-major order, then all 100 again. Returns bodies and statuses.
async function sweep(port, game, opts = {}) {
  const first = [];
  const second = [];
  for (let r = 0; r < 10; r += 1) for (let c = 0; c < 10; c += 1) first.push(await fire(port, game, r, c));
  if (opts.noSecond) return { first, second };
  for (let r = 0; r < 10; r += 1) for (let c = 0; c < 10; c += 1) second.push(await fire(port, game, r, c));
  return { first, second };
}

// ---------- the rules module (public functions placeFleet and fireShot)
function rules() {
  return require(path.join(WORK, 'rules.js'));
}
function scripted(draws) {
  let i = 0;
  const f = () => {
    if (i >= draws.length) throw new Violation('placeFleet asked for more than the ' + draws.length + ' scripted draws');
    return draws[i++];
  };
  f.used = () => i;
  return f;
}
function mulberry32(a) {
  return function () {
    a |= 0; a = (a + 0x6D2B79F5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

// Reference model of the placement rule, written from the spec text of R-4.
const FLEET = [['Carrier', 5], ['Battleship', 4], ['Cruiser', 3], ['Submarine', 3], ['Destroyer', 2]];
function refPlace(rnd) {
  const occ = new Set();
  const ships = [];
  for (const [label, len] of FLEET) {
    for (;;) {
      const h = rnd() < 0.5;
      const rmax = h ? 9 : 10 - len;
      const cmax = h ? 10 - len : 9;
      const r = Math.floor(rnd() * (rmax + 1));
      const c = Math.floor(rnd() * (cmax + 1));
      const cells = [];
      for (let k = 0; k < len; k += 1) cells.push(h ? [r, c + k] : [r + k, c]);
      if (cells.some(([a, b]) => occ.has(a + ',' + b))) continue;
      cells.forEach(([a, b]) => occ.add(a + ',' + b));
      ships.push({ label, cells });
      break;
    }
  }
  return ships;
}
// Place with the product using the scripted draws; compare to the reference using the same draws.
function placeBoth(draws) {
  const mine = rules().placeFleet(scripted(draws));
  const ref = refPlace(scripted(draws));
  return { mine: mine.ships, ref, game: mine };
}
function compareToRef(draws, what) {
  const { mine, ref } = placeBoth(draws);
  eq(mine, ref, what + ' with draws ' + JSON.stringify(draws));
}

// R-4 oracle draws and the layout the spec states for them
const SEQ_A = [0.0, 0.0, 0.0, 0.5, 0.0, 0.5, 0.0, 0.2, 0.0, 0.0, 0.4, 0.0, 0.0, 0.6, 0.0];
const SEQ_B = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.5, 0.0, 0.5, 0.0, 0.2, 0.0, 0.0, 0.4, 0.0, 0.0, 0.6, 0.0];
const LAYOUT = {
  Carrier: [[0, 0], [0, 1], [0, 2], [0, 3], [0, 4]],
  Battleship: [[0, 5], [1, 5], [2, 5], [3, 5]],
  Cruiser: [[2, 0], [2, 1], [2, 2]],
  Submarine: [[4, 0], [4, 1], [4, 2]],
  Destroyer: [[6, 0], [6, 1]],
};
const SHIP_ORDER = ['Carrier', 'Battleship', 'Cruiser', 'Submarine', 'Destroyer'];
const ALL_SHIP_CELLS = SHIP_ORDER.flatMap((s) => LAYOUT[s]);
function seeded() {
  return rules().placeFleet(scripted(SEQ_A));
}
function seededFire(game, r, c) {
  return rules().fireShot(game, r, c);
}

// facts about a sweep of 100 first-shot responses (row-major)
function sweepFacts(first) {
  let ship = 0, sunk = 0, hit = 0, miss = 0, seventeenth = -1;
  const overBad = [];
  first.forEach((r, i) => {
    const j = r.json || {};
    if (j.result === 'hit') hit += 1;
    else if (j.result === 'sunk') sunk += 1;
    else if (j.result === 'miss') miss += 1;
    if (j.result === 'hit' || j.result === 'sunk') {
      ship += 1;
      if (ship === 17) seventeenth = i;
    }
    const expectOver = ship >= 17;
    if (j.gameOver !== expectOver) overBad.push(i);
  });
  return { ship, sunk, hit, miss, seventeenth, overBad };
}

// ---------- browser through the Chrome DevTools protocol (local headless shell, no network)
async function openBrowser() {
  const port = await freePort(CDP_LO, CDP_HI);
  const dir = fs.mkdtempSync(path.join(SCRATCH, 'chrome-profile-'));
  const child = spawn(CHROME, ['--headless', '--no-first-run', '--disable-gpu', '--remote-debugging-port=' + port, '--user-data-dir=' + dir, 'about:blank'], { stdio: 'ignore' });
  cleanups.push(() => { try { child.kill('SIGKILL'); } catch (e) { /* gone */ } try { fs.rmSync(dir, { recursive: true, force: true }); } catch (e) { /* ignore */ } });
  let target;
  for (let i = 0; i < 100; i += 1) {
    try {
      const r = await req(port, 'GET', '/json/list');
      const pages = (r.json || []).filter((t) => t.type === 'page');
      if (pages.length) { target = pages[0]; break; }
    } catch (e) { /* not up yet */ }
    await delay(100);
  }
  if (!target) throw new Error('headless browser did not start');
  const ws = new WebSocket(target.webSocketDebuggerUrl);
  await new Promise((resolve, reject) => { ws.onopen = resolve; ws.onerror = () => reject(new Error('ws error')); });
  let id = 0;
  const waiting = new Map();
  const listeners = new Map();
  ws.onmessage = (m) => {
    const msg = JSON.parse(m.data);
    if (msg.id && waiting.has(msg.id)) {
      const { resolve, reject } = waiting.get(msg.id);
      waiting.delete(msg.id);
      if (msg.error) reject(new Error(msg.error.message)); else resolve(msg.result);
    } else if (msg.method && listeners.has(msg.method)) {
      for (const f of listeners.get(msg.method)) f(msg.params);
    }
  };
  const send = (method, params = {}) => new Promise((resolve, reject) => {
    id += 1;
    waiting.set(id, { resolve, reject });
    ws.send(JSON.stringify({ id, method, params }));
  });
  const on = (method, f) => { if (!listeners.has(method)) listeners.set(method, []); listeners.get(method).push(f); };
  return { send, on, close: () => { try { ws.close(); } catch (e) { /* ignore */ } } };
}

// A page on the server. rule(ev) decides what happens to each /api/* request:
//   'continue' (default) | 'hold' | 'fail' | {status, body}
async function openPage(serverPort, rule) {
  const b = await openBrowser();
  const log = [];
  const held = [];
  await b.send('Page.enable');
  await b.send('Runtime.enable');
  await b.send('Fetch.enable', { patterns: [{ urlPattern: '*/api/*' }] });
  b.on('Fetch.requestPaused', async (ev) => {
    const entry = { url: ev.request.url, method: ev.request.method, post: ev.request.postData, t: Date.now() };
    log.push(entry);
    let action = 'continue';
    try { if (rule) action = (await rule(entry)) || 'continue'; } catch (e) { action = 'continue'; }
    try {
      if (action === 'hold') held.push({ requestId: ev.requestId, entry });
      else if (action === 'fail') await b.send('Fetch.failRequest', { requestId: ev.requestId, errorReason: 'Failed' });
      else if (action === 'continue') await b.send('Fetch.continueRequest', { requestId: ev.requestId });
      else {
        await b.send('Fetch.fulfillRequest', {
          requestId: ev.requestId,
          responseCode: action.status,
          responseHeaders: [{ name: 'Content-Type', value: 'application/json' }],
          body: Buffer.from(action.body).toString('base64'),
        });
      }
    } catch (e) { /* page may have gone */ }
  });
  const evalJs = async (expression) => {
    const r = await b.send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true });
    if (r.exceptionDetails) throw new Error('page eval: ' + JSON.stringify(r.exceptionDetails).slice(0, 300));
    return r.result.value;
  };
  const cellFn = `(r, c) => {
    const els = [...document.querySelectorAll('button,[role=button],input[type=button]')];
    return els.find((e) => {
      const n = (e.getAttribute('aria-label') || e.textContent || '');
      const m = n.match(/row\\D*(\\d+)\\D+col\\w*\\D*(\\d+)/i);
      return m && Number(m[1]) === r && Number(m[2]) === c;
    });
  }`;
  const p = {
    log, held, eval: evalJs, send: b.send,
    async goto() {
      const loaded = new Promise((resolve) => b.on('Page.loadEventFired', resolve));
      await b.send('Page.navigate', { url: 'http://127.0.0.1:' + serverPort + '/' });
      await Promise.race([loaded, delay(5000)]);
    },
    async waitFor(expr, ms = 3000) {
      const deadline = Date.now() + ms;
      while (Date.now() < deadline) {
        if (await evalJs(expr)) return true;
        await delay(50);
      }
      return false;
    },
    cellText: (r, c) => evalJs(`(${cellFn})(${r},${c}) ? ((${cellFn})(${r},${c}).textContent + ' | ' + ((${cellFn})(${r},${c}).getAttribute('aria-label') || '')) : null`),
    clickCell: (r, c) => evalJs(`(() => { const e = (${cellFn})(${r},${c}); if (!e) return false; e.click(); return true; })()`),
    focusCell: (r, c) => evalJs(`(() => { const e = (${cellFn})(${r},${c}); if (!e) return false; e.focus(); return document.activeElement === e; })()`),
    async pressEnter() {
      await b.send('Input.dispatchKeyEvent', { type: 'keyDown', key: 'Enter', code: 'Enter', windowsVirtualKeyCode: 13, text: '\r' });
      await b.send('Input.dispatchKeyEvent', { type: 'keyUp', key: 'Enter', code: 'Enter', windowsVirtualKeyCode: 13 });
    },
    bodyText: () => evalJs('document.body.innerText'),
    posts: () => log.filter((e) => e.method === 'POST' && /\/api\/fire/.test(e.url)),
    close: b.close,
  };
  return p;
}
// fulfill GET /api/new through the real server so the witness knows the id
function realNewRule(serverPort, state, next) {
  return async (entry) => {
    if (entry.method === 'GET' && /\/api\/new/.test(entry.url)) {
      const r = await req(serverPort, 'GET', '/api/new');
      state.id = r.json && r.json.game;
      return { status: r.status, body: r.text };
    }
    return next ? next(entry) : 'continue';
  };
}

async function run(id) {
  const checks = require('./_checks.js');
  let code = 0;
  try {
    const fn = checks[id];
    if (!fn) throw new Error('no check for ' + id);
    await fn(module.exports);
    console.log('HOLDS ' + id);
  } catch (e) {
    if (e instanceof Violation) {
      console.log('VIOLATED ' + id + ': ' + e.message);
      code = 1;
    } else {
      console.log('HARNESS-ERROR ' + id + ': ' + (e && e.stack || e));
      code = 3;
    }
  }
  for (const f of cleanups.splice(0)) f();
  setTimeout(() => process.exit(code), 50);
}

module.exports = {
  WORK, SCRATCH, Violation, check, eq, delay, freePort, canListen, connect, listening, spawnServer, waitUp, stopServer, startServer,
  remapOptions, REMAP, DETID, req, newGame, fire, sweep, rules, scripted, mulberry32, FLEET, refPlace, placeBoth, compareToRef,
  SEQ_A, SEQ_B, LAYOUT, SHIP_ORDER, ALL_SHIP_CELLS, seeded, seededFire, sweepFacts, openPage, realNewRule, cleanups, run,
};
