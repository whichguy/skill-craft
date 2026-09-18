#!/usr/bin/env node
'use strict';
// External, read-only semantic adapter host. The mapping is reviewed per product;
// this host never discovers selectors, computes expected game rules, or edits it.
// Usage: node browser_driver.cjs --mapping /absolute/mapping.cjs
//        --playwright /absolute/playwright --browser /absolute/chrome
const fs = require('node:fs');
const path = require('node:path');
const http = require('node:http');
const crypto = require('node:crypto');

function option(name, fallback) {
  const at = process.argv.indexOf(name);
  if (at < 0) return fallback;
  if (!process.argv[at + 1]) throw new Error(`Missing ${name}`);
  return process.argv[at + 1];
}
const hash = value => crypto.createHash('sha256').update(value).digest('hex');

async function main() {
  let input = '';
  for await (const chunk of process.stdin) {
    input += chunk;
    if (Buffer.byteLength(input) > 1024 * 1024) throw new Error('Request exceeds limit');
  }
  const request = JSON.parse(input);
  if (!Array.isArray(request.actions) || request.actions.length > 2000) throw new Error('Invalid actions');
  const requestSha256 = hash(input);
  const repo = fs.realpathSync(path.resolve(request.repo));
  const mappingPath = path.resolve(option('--mapping'));
  const mapping = require(mappingPath);
  for (const method of ['prepare', 'perform', 'observe']) {
    if (typeof mapping[method] !== 'function') throw new Error(`Mapping lacks ${method}`);
  }
  const { chromium } = require(option('--playwright', 'playwright'));
  const prepared = await mapping.prepare(repo);
  if (typeof prepared.html !== 'string') throw new Error('Mapping must supply observed source HTML');
  // Serve exactly the assembled page. Sibling filesystem assets are deliberately
  // unavailable: a mapping must explain the actual target-runtime resource route.
  const server = http.createServer((req, res) => {
    if (req.url !== '/') { res.writeHead(404); res.end(); return; }
    res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
    res.end(prepared.html);
  });
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  const origin = `http://127.0.0.1:${server.address().port}`;
  let browser;
  try {
    const browserPath = option('--browser');
    browser = await chromium.launch({ headless: true, ...(browserPath ? { executablePath: browserPath } : {}) });
    const page = await browser.newPage({ viewport: { width: 1000, height: 800 } });
    page.setDefaultTimeout(5000);
    const errors = [], rejectedRequests = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.route('**/*', route => {
      const url = new URL(route.request().url());
      if (url.origin !== origin) { rejectedRequests.push(url.href); return route.abort(); }
      return route.continue();
    });
    await page.goto(origin, { waitUntil: 'load' });
    const observations = [], trace = [];
    let previous = null;
    for (const [index, action] of request.actions.entries()) {
      await mapping.perform(page, action);
      const observed = await mapping.observe(page, previous);
      observations.push(observed);
      trace.push({ index, action, observed });
      previous = observed;
    }
    if (errors.length || rejectedRequests.length) throw new Error(JSON.stringify({ errors, rejectedRequests }));
    const metadata = { schema: 'shiploop-e2e-browser-adapter/1', browser: browser.version(),
      request_sha256: requestSha256, repo,
      adapter_sha256: hash(fs.readFileSync(__filename)), mapping_sha256: hash(fs.readFileSync(mappingPath)),
      rendered_sha256: hash(prepared.html), source: prepared.source, trace,
      scope: 'Real local browser actions on explicitly assembled source. GAS runtime and hosting not executed.' };
    const evidence = process.env.SHIPLOOP_E2E_EVIDENCE;
    if (evidence) {
      const target = path.join(evidence, 'browser-traces', crypto.randomUUID());
      fs.mkdirSync(target, { recursive: true });
      fs.writeFileSync(path.join(target, 'trace.json'), JSON.stringify(metadata, null, 2) + '\n');
      await page.screenshot({ path: path.join(target, 'final.png'), fullPage: true });
    }
    process.stdout.write(JSON.stringify({ schema: 'shiploop-e2e-driver-response/1', request_sha256: requestSha256, repo, observations, metadata }) + '\n');
  } finally {
    if (browser) await browser.close();
    await new Promise(resolve => server.close(resolve));
  }
}
main().catch(error => { console.error(error.message); process.exitCode = 2; });
