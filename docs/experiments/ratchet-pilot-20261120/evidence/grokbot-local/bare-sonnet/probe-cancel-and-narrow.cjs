'use strict';
const path = require('node:path'); const net = require('node:net'); const { spawn } = require('node:child_process');
const product = path.resolve(process.argv[2]); const out = path.resolve(process.argv[3]);
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const freePort = () => new Promise((res, rej) => { const p = net.createServer(); p.once('error', rej); p.listen(0, '127.0.0.1', () => { const { port } = p.address(); p.close(() => res(port)); }); });
(async () => {
  const playwright = require(process.env.PLAYWRIGHT_NODE_PATH);
  const browser = await playwright.chromium.launch({ headless: true, executablePath: process.env.BROWSER_EXECUTABLE_PATH });
  const port = await freePort(); const env = { ...process.env, PORT: String(port), DATA_DIR: path.join(out, 'data-' + Date.now()), PROVIDER_TOKEN: 'sk-local-Yardstick00017', STANDIN_SLOW_MS: '1500', STANDIN_STEP_MS: '700' };
  const child = spawn('node', ['server.js'], { cwd: product, env, detached: true, stdio: 'ignore' });
  const base = `http://127.0.0.1:${port}`;
  for (let i = 0; i < 80; i += 1) { try { const a = await fetch(base + '/'); if (a.status < 500) break; } catch { await sleep(250); } }
  const open = async (w, h) => { const page = await (await browser.newContext({ viewport: { width: w, height: h } })).newPage(); page.setDefaultTimeout(6000);
    await page.goto(base + '/', { waitUntil: 'load' }); const enter = page.getByRole('button', { name: 'Continue as Maya', exact: true }); const box = page.getByRole('textbox', { name: 'Message', exact: true });
    await enter.or(box).first().waitFor(); if (await enter.isVisible()) await enter.click(); await box.waitFor(); return page; };
  let page = await open(1440, 1000);
  const say = async (t) => { await sleep(300); await page.getByRole('textbox', { name: 'Message', exact: true }).fill(t); await page.getByRole('button', { name: 'Send', exact: true }).click(); };
  const task = page.getByRole('article', { name: 'Task: cleanup', exact: true });
  const text = async () => (await task.innerText()).replace(/\s+/g, ' ').slice(0, 330);
  await say('long task: cleanup [long]');
  await task.getByRole('status', { name: 'Task status', exact: true }).filter({ hasText: 'Running' }).waitFor();
  const t0 = Date.now();
  await task.getByRole('button', { name: 'Cancel task', exact: true }).click();
  for (const at of [150, 500, 1000, 1700, 2600, 4000, 6000]) { await sleep(Math.max(0, at - (Date.now() - t0))); console.log(`+${at}ms`, await text()); }
  console.log('last bot message:', await page.getByRole('region', { name: 'Conversation', exact: true }).getByRole('article').evaluateAll((els) => els.slice(-1).map((e) => e.innerText.replace(/\s+/g, ' ').slice(0, 300))));
  await page.context().close();
  // narrow
  page = await open(320, 860); await sleep(600);
  const widths = await page.evaluate(() => { const wide = []; for (const el of document.querySelectorAll('body *')) { const r = el.getBoundingClientRect(); if (r.right > window.innerWidth + 1 && r.width > 0) wide.push((el.tagName + '.' + (el.className || '').toString().slice(0, 30) + '#' + (el.id || '') + ' right=' + Math.round(r.right) + ' w=' + Math.round(r.width))); } return [document.documentElement.scrollWidth, window.innerWidth, wide.slice(0, 8)]; });
  console.log('at 320:', JSON.stringify(widths));
  try { process.kill(-child.pid, 'SIGTERM'); } catch { /* gone */ }
  await browser.close();
})().catch((e) => { console.error('probe error', e); process.exit(1); });
