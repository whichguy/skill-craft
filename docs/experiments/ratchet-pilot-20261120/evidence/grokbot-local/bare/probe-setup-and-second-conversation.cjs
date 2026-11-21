'use strict';
const path = require('node:path'); const net = require('node:net'); const { spawn } = require('node:child_process');
const product = path.resolve(process.argv[2]); const out = path.resolve(process.argv[3]);
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const freePort = () => new Promise((res, rej) => { const p = net.createServer(); p.once('error', rej); p.listen(0, '127.0.0.1', () => { const { port } = p.address(); p.close(() => res(port)); }); });
async function start(name, token) {
  const port = await freePort(); const env = { ...process.env, PORT: String(port), DATA_DIR: path.join(out, 'data-' + name), STANDIN_SLOW_MS: '1500', STANDIN_STEP_MS: '700' };
  delete env.PROVIDER_TOKEN; if (token) env.PROVIDER_TOKEN = 'sk-local-Yardstick00017';
  const child = spawn('node', ['server.js'], { cwd: product, env, detached: true, stdio: 'ignore' });
  const base = `http://127.0.0.1:${port}`;
  for (let i = 0; i < 80; i += 1) { try { const a = await fetch(base + '/'); if (a.status < 500) break; } catch { await sleep(250); } }
  return { base, stop: () => { try { process.kill(-child.pid, 'SIGTERM'); } catch { /* gone */ } } };
}
const names = async (page, role) => page.getByRole(role).evaluateAll((els) => els.map((e) => (e.getAttribute('aria-label') || e.innerText || '').trim().slice(0, 60) + (e.offsetParent === null ? ' [hidden]' : '')));
(async () => {
  const playwright = require(process.env.PLAYWRIGHT_NODE_PATH);
  const browser = await playwright.chromium.launch({ headless: true, executablePath: process.env.BROWSER_EXECUTABLE_PATH });
  // A: no token
  let server = await start('a', false);
  let page = await (await browser.newContext({ viewport: { width: 1440, height: 1000 } })).newPage(); page.setDefaultTimeout(5000);
  await page.goto(server.base + '/', { waitUntil: 'load' }); await sleep(600);
  console.log('A first screen: regions', await names(page, 'region'), '| buttons', await names(page, 'button'), '| textboxes', await names(page, 'textbox'));
  const enter = page.getByRole('button', { name: 'Continue as Maya', exact: true });
  if (await enter.count()) { await enter.click(); await sleep(800);
    console.log('A after Continue as Maya: regions', await names(page, 'region'), '| buttons', (await names(page, 'button')).slice(0, 14), '| textboxes', await names(page, 'textbox'), '| alerts', await names(page, 'alert')); }
  console.log('A body text:', (await page.locator('body').innerText()).replace(/\s+/g, ' ').slice(0, 500));
  server.stop();
  // B: token, second conversation
  server = await start('b', true);
  page = await (await browser.newContext({ viewport: { width: 1440, height: 1000 } })).newPage(); page.setDefaultTimeout(5000);
  await page.goto(server.base + '/', { waitUntil: 'load' });
  await page.getByRole('button', { name: 'Continue as Maya', exact: true }).click();
  const box = page.getByRole('textbox', { name: 'Message', exact: true }); await box.waitFor();
  const say = async (t) => { await box.fill(t); await page.getByRole('button', { name: 'Send', exact: true }).click(); await sleep(1200); };
  await say('hello');
  await page.getByRole('button', { name: 'New bot', exact: true }).click(); await page.getByRole('textbox', { name: 'Bot name', exact: true }).fill('Planner'); await page.getByRole('button', { name: 'Save bot name', exact: true }).click(); await sleep(800);
  await say('hello planner');
  await page.reload({ waitUntil: 'load' }); await box.waitFor(); await sleep(500);
  const conv = page.getByRole('navigation', { name: 'Conversations', exact: true });
  console.log('B before New conversation: conversations', await conv.getByRole('button').evaluateAll((els) => els.map((e) => e.innerText.trim() + '|' + e.getAttribute('aria-current'))));
  await page.getByRole('button', { name: 'New conversation', exact: true }).click(); await sleep(900);
  console.log('B after New conversation: conversations', await conv.getByRole('button').evaluateAll((els) => els.map((e) => e.innerText.trim() + '|' + e.getAttribute('aria-current'))));
  console.log('B articles before send', await page.getByRole('region', { name: 'Conversation', exact: true }).getByRole('article').evaluateAll((els) => els.map((e) => (e.getAttribute('aria-label') || '') + ': ' + e.innerText.trim().slice(0, 90))));
  await say('fresh start'); await sleep(1500);
  console.log('B articles after send', await page.getByRole('region', { name: 'Conversation', exact: true }).getByRole('article').evaluateAll((els) => els.map((e) => (e.getAttribute('aria-label') || '') + ': ' + e.innerText.trim().slice(0, 120))));
  console.log('B alerts', await names(page, 'alert'), '| status', await names(page, 'status'));
  console.log('B box value', JSON.stringify(await box.inputValue()), '| conversations', await conv.getByRole('button').evaluateAll((els) => els.map((e) => e.innerText.trim() + '|' + e.getAttribute('aria-current'))));
  server.stop(); await browser.close();
})().catch((e) => { console.error('probe error', e); process.exit(1); });
