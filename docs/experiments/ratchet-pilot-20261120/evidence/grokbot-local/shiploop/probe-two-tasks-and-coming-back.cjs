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
  const tasks = async () => page.getByRole('article').evaluateAll((els) => els.filter((e) => (e.getAttribute('aria-label') || '').startsWith('Task:')).map((e) => (e.getAttribute('aria-label') + ' => ' + e.innerText.replace(/\s+/g, ' ').slice(0, 130))));
  const last = async () => page.getByRole('region', { name: 'Conversation', exact: true }).getByRole('article').evaluateAll((els) => els.slice(-2).map((e) => (e.getAttribute('aria-label') || '') + ': ' + e.innerText.replace(/\s+/g, ' ').slice(0, 170)));
  await say('long task: first job [long]'); console.log('after first ask', await last());
  await say('long task: second job [long]'); console.log('after second ask', await last());
  console.log('tasks t+0', await tasks());
  const cancel = page.getByRole('article', { name: 'Task: first job', exact: true }).getByRole('button', { name: 'Cancel task', exact: true });
  console.log('cancel buttons for first job', await cancel.count());
  if (await cancel.count()) await cancel.click();
  await sleep(1500); console.log('tasks after cancel +1.5s', await tasks());
  await sleep(7000); console.log('tasks after cancel +8.5s', await tasks());
  console.log('alerts', await page.getByRole('alert').evaluateAll((els) => els.map((e) => e.innerText.trim().slice(0, 160))));
  // away account
  await say('long task: big survey [long]'); await say('long task: export [fail step 2]'); await say('long task: quick note');
  console.log('before closing', await tasks());
  await page.context().close(); await sleep(3500); page = await open(); await sleep(800);
  const away = page.getByRole('region', { name: 'Since you were away', exact: true });
  console.log('away region count', await away.count(), '| text:', (await away.first().innerText().catch(() => '(none)')).replace(/\s+/g, ' ').slice(0, 500));
  console.log('tasks on return', await tasks());
  try { process.kill(-child.pid, 'SIGTERM'); } catch { /* gone */ }
  await browser.close();
})().catch((e) => { console.error('probe error', e); process.exit(1); });
