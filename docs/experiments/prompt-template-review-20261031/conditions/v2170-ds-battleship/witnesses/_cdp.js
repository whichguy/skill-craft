'use strict';
// Minimal Chrome DevTools Protocol driver for the browser witnesses (own implementation; it does not
// reuse the run's browser-check/cdp.js). Headless Google Chrome, one page, request interception.
const L = require('./_lib.js');
const { cp, fs, os, path, sleep } = L;

const CHROME = process.env.CHROME_PATH || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';

async function launch() {
  const port = await L.freePort();
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'wit-chrome-'));
  const child = cp.spawn(CHROME, ['--headless=new', `--remote-debugging-port=${port}`, `--user-data-dir=${dir}`,
    '--no-first-run', '--no-default-browser-check', '--disable-gpu', '--window-size=1200,1400', 'about:blank'],
  { stdio: 'ignore' });
  const chrome = {
    child, port, dir,
    async close() { try { child.kill('SIGKILL'); } catch {} await sleep(50); try { fs.rmSync(dir, { recursive: true, force: true }); } catch {} },
  };
  await L.waitFor(async () => { try { const r = await L.req(port, 'GET', '/json/version'); return r.status === 200; } catch { return false; } }, 15000, 'chrome');
  return chrome;
}

async function newPage(chrome) {
  const r = await L.req(chrome.port, 'PUT', '/json/new?about:blank');
  const info = r.json;
  const ws = new WebSocket(info.webSocketDebuggerUrl);
  await new Promise((res, rej) => { ws.onopen = res; ws.onerror = () => rej(new Error('ws error')); });
  let id = 0;
  const pending = new Map();
  const handlers = [];
  ws.onmessage = (m) => {
    const msg = JSON.parse(m.data);
    if (msg.id !== undefined && pending.has(msg.id)) {
      const { resolve, reject } = pending.get(msg.id);
      pending.delete(msg.id);
      if (msg.error) reject(new Error(msg.error.message)); else resolve(msg.result);
    } else if (msg.method) {
      for (const h of handlers) h(msg.method, msg.params);
    }
  };
  const page = {
    ws, requests: [], held: [], rule: null, navigations: 0,
    send(method, params = {}) { return new Promise((resolve, reject) => { const i = ++id; pending.set(i, { resolve, reject }); ws.send(JSON.stringify({ id: i, method, params })); }); },
    on(h) { handlers.push(h); },
    async eval(expr) {
      const r = await page.send('Runtime.evaluate', { expression: expr, awaitPromise: true, returnByValue: true });
      if (r.exceptionDetails) throw new Error('eval: ' + (r.exceptionDetails.exception?.description || r.exceptionDetails.text));
      return r.result.value;
    },
    async goto(url) {
      const loaded = new Promise((res) => { const h = (m) => { if (m === 'Page.loadEventFired') res(); }; handlers.push(h); });
      await page.send('Page.navigate', { url });
      await loaded;
      await sleep(150);
    },
    async reload() {
      const loaded = new Promise((res) => { const h = (m) => { if (m === 'Page.loadEventFired') res(); }; handlers.push(h); });
      await page.send('Page.reload');
      await loaded;
      await sleep(150);
    },
    // rule(req) -> {action:'continue'} | {action:'fail'} | {action:'hold'} | {action:'fulfill', status, body, headers}
    async intercept(rule) {
      page.rule = rule;
      await page.send('Fetch.enable', { patterns: [{ urlPattern: '*/api/*' }] });
    },
    async release(i) { const h = page.held[i]; await page.send('Fetch.continueRequest', { requestId: h.requestId }); },
    async pollStatus() { return page.eval(`document.querySelector('[role=status]').textContent`); },
    async cellCenter(row, col) {
      return page.eval(`(() => { const b = document.querySelector('.cell[data-row="${row}"][data-col="${col}"]'); b.scrollIntoView({block:'center'}); const r = b.getBoundingClientRect(); return {x: r.x + r.width/2, y: r.y + r.height/2}; })()`);
    },
    async mouseClickAt(x, y) {
      await page.send('Input.dispatchMouseEvent', { type: 'mouseMoved', x, y });
      await page.send('Input.dispatchMouseEvent', { type: 'mousePressed', x, y, button: 'left', clickCount: 1 });
      await page.send('Input.dispatchMouseEvent', { type: 'mouseReleased', x, y, button: 'left', clickCount: 1 });
    },
    async clickCell(row, col) { const c = await page.cellCenter(row, col); await page.mouseClickAt(c.x, c.y); },
    async clickSel(sel) {
      const c = await page.eval(`(() => { const b = document.querySelector(${JSON.stringify(sel)}); b.scrollIntoView({block:'center'}); const r = b.getBoundingClientRect(); return {x: r.x + r.width/2, y: r.y + r.height/2}; })()`);
      await page.mouseClickAt(c.x, c.y);
    },
    async key(key, code, vk, text) {
      await page.send('Input.dispatchKeyEvent', { type: 'keyDown', key, code, windowsVirtualKeyCode: vk, text });
      await page.send('Input.dispatchKeyEvent', { type: 'keyUp', key, code, windowsVirtualKeyCode: vk });
    },
    tab() { return page.key('Tab', 'Tab', 9); },
    enter() { return page.key('Enter', 'Enter', 13, '\r'); },
    fires() { return page.requests.filter((r) => r.method === 'POST' && /\/api\/fire/.test(r.url)); },
    news() { return page.requests.filter((r) => /\/api\/new/.test(r.url)); },
    async close() { try { ws.close(); } catch {} },
  };
  page.on(async (method, p) => {
    if (method === 'Page.frameNavigated' && !p.frame.parentId) page.navigations += 1;
    if (method !== 'Fetch.requestPaused') return;
    const rq = { method: p.request.method, url: p.request.url, postData: p.request.postData, requestId: p.requestId };
    page.requests.push(rq);
    const d = page.rule ? page.rule(rq) : { action: 'continue' };
    try {
      if (d.action === 'fail') await page.send('Fetch.failRequest', { requestId: p.requestId, errorReason: 'Failed' });
      else if (d.action === 'hold') page.held.push(rq);
      else if (d.action === 'fulfill') {
        await page.send('Fetch.fulfillRequest', { requestId: p.requestId, responseCode: d.status,
          responseHeaders: [{ name: 'content-type', value: 'application/json' }], body: Buffer.from(d.body).toString('base64') });
      } else await page.send('Fetch.continueRequest', { requestId: p.requestId });
    } catch { /* page closed */ }
  });
  await page.send('Page.enable');
  await page.send('Runtime.enable');
  await page.send('Emulation.setDeviceMetricsOverride', { width: 1200, height: 1400, deviceScaleFactor: 1, mobile: false });
  return page;
}

// Run fn(page, base) against a seeded in-process server and a fresh headless Chrome page.
async function withPage(seed, fn, serverOpts = {}) {
  const srv = await L.inproc({ random: L.seeded(seed), ...serverOpts });
  const chrome = await launch();
  try {
    const page = await newPage(chrome);
    await fn(page, `http://127.0.0.1:${srv.port}/`, srv);
    await page.close();
  } finally {
    await chrome.close();
    await srv.close();
  }
}


// ---- scenario helpers (outside observations of the page only) ----
const ALLOW = () => ({ action: 'continue' });
async function ready(page, base, rule = ALLOW) {
  await page.intercept(rule);
  await page.goto(base);
  await L.waitFor(() => page.news().length >= 1, 5000, 'the page to request a game');
  await sleep(250);
}
async function shoot(page, r, c, wait = 2500) {
  const n0 = page.fires().length;
  await page.clickCell(r, c);
  const t0 = Date.now();
  while (page.fires().length === n0 && Date.now() - t0 < 700) await sleep(25);
  await sleep(160);
  return page.fires().length > n0;
}
function info(page, r, c) {
  return page.eval(`(() => { const b = document.querySelector('.cell[data-row="${r}"][data-col="${c}"]'); return { text: b.textContent.trim(), label: b.getAttribute('aria-label') || '', result: b.dataset.result, html: b.outerHTML }; })()`);
}
const marked = (i) => i.result !== undefined || /miss|hit|sunk/i.test(i.label) || /^[MHS]$/.test(i.text);
async function win(page, fleet) {
  for (const sh of fleet) for (const c of sh.cells) await shoot(page, c.row, c.col);
}
const waterCell = (fleet, n = 0) => {
  const ship = new Set(fleet.flatMap((s) => s.cells.map((c) => c.row + ',' + c.col)));
  let k = 0;
  for (let r = 9; r >= 0; r--) for (let c = 9; c >= 0; c--) if (!ship.has(r + ',' + c)) { if (k++ === n) return { row: r, col: c }; }
};
const text = (page) => page.eval('document.body.innerText');
const statusOf = (page) => page.pollStatus();
const newGameSel = `(() => [...document.querySelectorAll('button')].find((b) => /New game/.test(b.textContent)))()`;
async function clickNewGame(page) {
  const c = await page.eval(`(() => { const b = [...document.querySelectorAll('button')].find((x) => /New game/.test(x.textContent)); b.scrollIntoView({block:'center'}); const r = b.getBoundingClientRect(); return {x: r.x + r.width/2, y: r.y + r.height/2}; })()`);
  await page.mouseClickAt(c.x, c.y);
}

module.exports = { launch, newPage, withPage, ready, shoot, info, marked, win, waterCell, text, statusOf, clickNewGame, ALLOW, sleep };
