'use strict';
const path = require('node:path'); const net = require('node:net'); const { spawn } = require('node:child_process');
const product = path.resolve(process.argv[2]); const out = path.resolve(process.argv[3]);
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const freePort = () => new Promise((res, rej) => { const p = net.createServer(); p.once('error', rej); p.listen(0, '127.0.0.1', () => { const { port } = p.address(); p.close(() => res(port)); }); });
(async () => {
  const playwright = require(process.env.PLAYWRIGHT_NODE_PATH);
  const browser = await playwright.chromium.launch({ headless: true, executablePath: process.env.BROWSER_EXECUTABLE_PATH });
  const port = await freePort(); const env = { ...process.env, PORT: String(port), DATA_DIR: path.join(out, 'data-' + Date.now()), PROVIDER_TOKEN: 'sk-local-Yardstick00029', STANDIN_SLOW_MS: '1500', STANDIN_STEP_MS: '700' };
  const child = spawn('node', ['server.js'], { cwd: product, env, detached: true, stdio: 'ignore' });
  const base = `http://127.0.0.1:${port}`;
  for (let i = 0; i < 80; i += 1) { try { const a = await fetch(base + '/'); if (a.status < 500) break; } catch { await sleep(250); } }
  const open = async () => { const page = await (await browser.newContext({ viewport: { width: 1440, height: 1000 } })).newPage(); page.setDefaultTimeout(6000);
    await page.goto(base + '/', { waitUntil: 'load' }); const enter = page.getByRole('button', { name: 'Continue as Maya', exact: true }); const box = page.getByRole('textbox', { name: 'Message', exact: true });
    await enter.or(box).first().waitFor(); if (await enter.isVisible()) await enter.click(); await box.waitFor(); return page; };
  let page = await open();
  const say = async (t) => { await sleep(300); await page.getByRole('textbox', { name: 'Message', exact: true }).fill(t); await page.getByRole('button', { name: 'Send', exact: true }).click(); await sleep(900); };
  const tasks = async () => page.getByRole('article').evaluateAll((els) => els.filter((e) => (e.getAttribute('aria-label') || '').startsWith('Task:')).map((e) => (e.getAttribute('aria-label') + ' => ' + e.innerText.replace(/\s+/g, ' ').slice(0, 90))));
  const away = async () => (await page.getByRole('region', { name: 'Since you were away', exact: true }).first().innerText().catch(() => '(no region)')).replace(/\s+/g, ' ').slice(0, 300);
  const last = async () => page.getByRole('region', { name: 'Conversation', exact: true }).getByRole('article').evaluateAll((els) => els.slice(-1).map((e) => (e.getAttribute('aria-label') || '') + ': ' + e.innerText.replace(/\s+/g, ' ').slice(0, 220)));
  // A: one long task, page closed while it runs (the first yardstick's sequence)
  await say('long task: audit [long]'); console.log('A asked', await last(), await tasks());
  await page.context().close(); await sleep(3200); page = await open();
  for (const wait of [0, 600, 1500, 3000, 6000]) { await sleep(wait === 0 ? 100 : wait - 0); console.log(`A +${wait}ms away:`, await away(), '| tasks:', await tasks()); }
  // B: three tasks in one conversation, then away (the second yardstick's sequence)
  await say('long task: big survey [long]'); console.log('B1', await last());
  await say('long task: export [fail step 2]'); console.log('B2', await last());
  await say('long task: quick note'); console.log('B3', await last());
  console.log('B before closing', await tasks());
  await page.context().close(); await sleep(3500); page = await open(); await sleep(500);
  console.log('B on return away:', await away()); console.log('B tasks on return', await tasks());
  try { process.kill(-child.pid, 'SIGTERM'); } catch { /* gone */ }
  await browser.close();
})().catch((e) => { console.error('probe error', e); process.exit(1); });
