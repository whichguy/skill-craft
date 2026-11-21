'use strict';
const path = require('node:path'); const net = require('node:net'); const { spawn } = require('node:child_process');
const product = path.resolve(process.argv[2]); const out = path.resolve(process.argv[3]);
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const freePort = () => new Promise((res, rej) => { const p = net.createServer(); p.once('error', rej); p.listen(0, '127.0.0.1', () => { const { port } = p.address(); p.close(() => res(port)); }); });
(async () => {
  const playwright = require(process.env.PLAYWRIGHT_NODE_PATH);
  const browser = await playwright.chromium.launch({ headless: true, executablePath: process.env.BROWSER_EXECUTABLE_PATH });
  const port = await freePort(); const env = { ...process.env, PORT: String(port), DATA_DIR: path.join(out, 'data-c-' + Date.now()), PROVIDER_TOKEN: 'sk-local-Yardstick00017' };
  const child = spawn('node', ['server.js'], { cwd: product, env, detached: true, stdio: 'ignore' });
  const base = `http://127.0.0.1:${port}`;
  for (let i = 0; i < 80; i += 1) { try { const a = await fetch(base + '/'); if (a.status < 500) break; } catch { await sleep(250); } }
  const page = await (await browser.newContext({ viewport: { width: 1440, height: 1000 } })).newPage(); page.setDefaultTimeout(5000);
  const requests = []; page.on('request', (r) => { if (r.method() !== 'GET') requests.push(r.method() + ' ' + new URL(r.url()).pathname + ' ' + (r.postData() || '').slice(0, 120)); });
  await page.goto(base + '/', { waitUntil: 'load' });
  await page.getByRole('button', { name: 'Continue as Maya', exact: true }).click();
  const box = page.getByRole('textbox', { name: 'Message', exact: true }); await box.waitFor();
  const send = async (t) => { await box.fill(t); await page.getByRole('button', { name: 'Send', exact: true }).click(); };
  const articles = () => page.getByRole('region', { name: 'Conversation', exact: true }).getByRole('article').evaluateAll((els) => els.map((e) => (e.getAttribute('aria-label') || '') + ': ' + e.innerText.trim().replace(/\s+/g, ' ').slice(0, 110)));
  await page.getByRole('button', { name: 'New bot', exact: true }).click(); await page.getByRole('textbox', { name: 'Bot name', exact: true }).fill('Planner'); await page.getByRole('button', { name: 'Save bot name', exact: true }).click(); await sleep(800);
  await send('hello planner'); await sleep(1200);
  await page.reload({ waitUntil: 'load' }); await box.waitFor();
  requests.length = 0;
  await page.getByRole('button', { name: 'New conversation', exact: true }).click();
  await send('fresh start');                      // at machine speed, as the yardstick does
  await sleep(2500);
  console.log('articles', await articles());
  console.log('requests', requests);
  const conv = page.getByRole('navigation', { name: 'Conversations', exact: true });
  console.log('conversations', await conv.getByRole('button').evaluateAll((els) => els.map((e) => e.innerText.trim() + '|' + e.getAttribute('aria-current'))));
  try { process.kill(-child.pid, 'SIGTERM'); } catch { /* gone */ }
  await browser.close();
})().catch((e) => { console.error('probe error', e); process.exit(1); });
