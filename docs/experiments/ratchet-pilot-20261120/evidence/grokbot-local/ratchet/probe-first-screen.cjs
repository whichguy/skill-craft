'use strict';
const path = require('node:path'); const net = require('node:net'); const { spawn } = require('node:child_process');
const product = path.resolve(process.argv[2]); const out = path.resolve(process.argv[3]);
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const freePort = () => new Promise((res, rej) => { const p = net.createServer(); p.once('error', rej); p.listen(0, '127.0.0.1', () => { const { port } = p.address(); p.close(() => res(port)); }); });
(async () => {
  const playwright = require(process.env.PLAYWRIGHT_NODE_PATH);
  const browser = await playwright.chromium.launch({ headless: true, executablePath: process.env.BROWSER_EXECUTABLE_PATH });
  const port = await freePort(); const env = { ...process.env, PORT: String(port), DATA_DIR: path.join(out, 'data-' + Date.now()), PROVIDER_TOKEN: 'sk-local-Yardstick00017' };
  const child = spawn('node', ['server.js'], { cwd: product, env, detached: true, stdio: ['ignore', 'pipe', 'pipe'] });
  let log = ''; child.stdout.on('data', (c) => { log += c; }); child.stderr.on('data', (c) => { log += c; });
  const base = `http://127.0.0.1:${port}`;
  for (let i = 0; i < 80; i += 1) { try { const a = await fetch(base + '/'); if (a.status < 500) break; } catch { await sleep(250); } }
  const page = await (await browser.newContext({ viewport: { width: 1440, height: 1000 } })).newPage(); page.setDefaultTimeout(5000);
  const errors = []; page.on('pageerror', (e) => errors.push('pageerror: ' + String(e).slice(0, 300))); page.on('console', (m) => { if (m.type() === 'error') errors.push('console: ' + m.text().slice(0, 300)); });
  page.on('response', (r) => { if (r.status() >= 400) errors.push(`http ${r.status()} ${new URL(r.url()).pathname}`); });
  await page.goto(base + '/', { waitUntil: 'load' }); await sleep(800);
  const snap = async (label) => {
    const roles = {};
    for (const role of ['button', 'textbox', 'region', 'navigation', 'alert', 'status', 'heading', 'dialog']) {
      roles[role] = await page.getByRole(role).evaluateAll((els) => els.map((e) => ((e.getAttribute('aria-label') || e.innerText || e.getAttribute('placeholder') || '').trim().replace(/\s+/g, ' ').slice(0, 50))));
    }
    console.log(label, JSON.stringify(roles));
  };
  await snap('FIRST SCREEN');
  const enter = page.getByRole('button', { name: 'Continue as Maya', exact: true });
  console.log('Continue as Maya buttons:', await enter.count());
  if (await enter.count()) { await enter.click(); await sleep(1500); await snap('AFTER CONTINUE'); }
  console.log('Message textbox count', await page.getByRole('textbox', { name: 'Message', exact: true }).count(), 'visible', await page.getByRole('textbox', { name: 'Message', exact: true }).first().isVisible().catch(() => 'n/a'));
  console.log('body:', (await page.locator('body').innerText()).replace(/\s+/g, ' ').slice(0, 600));
  console.log('errors:', errors.slice(0, 10)); console.log('server log:', log.slice(0, 600));
  try { process.kill(-child.pid, 'SIGTERM'); } catch { /* gone */ }
  await browser.close();
})().catch((e) => { console.error('probe error', e); process.exit(1); });
