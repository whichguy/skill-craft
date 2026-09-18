// Opt-in local Chromium experiment. No installations or remote requests.
const http = require('node:http');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const assert = require('node:assert/strict');

async function main() {
  const output = process.argv[2];
  if (!output || fs.existsSync(output)) throw new Error('Supply a new output directory');
  fs.mkdirSync(output, { recursive: true });
  const { chromium } = require(process.env.PLAYWRIGHT_NODE_PATH || 'playwright');
  const csp = "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self'; object-src 'none'; base-uri 'none'";
  const html = '<!doctype html><html><head><link rel="stylesheet" href="/app.css"></head><body><h1>Archive exports</h1><p id="status">Ready</p><script src="/app.js"></script><script>window.inlineExecuted = true</script></body></html>';
  const script = "window.externalExecuted = true; document.getElementById('status').textContent = 'Ready to request export';";
  const css = 'body { color: rgb(21, 50, 79); background: white; font-family: sans-serif; }';
  const requests = [];
  const server = http.createServer((req, res) => {
    requests.push(req.url);
    res.setHeader('Content-Security-Policy', csp);
    res.setHeader('Cache-Control', 'no-store');
    if (req.url === '/frame') {
      res.setHeader('Content-Type', 'text/html');
      res.end('<!doctype html><iframe title="Constrained host" sandbox="allow-scripts" src="/app"></iframe>');
    } else if (req.url === '/app.js') {
      res.setHeader('Content-Type', 'text/javascript'); res.end(script);
    } else if (req.url === '/app.css') {
      res.setHeader('Content-Type', 'text/css'); res.end(css);
    } else if (req.url === '/app') {
      res.setHeader('Content-Type', 'text/html'); res.end(html);
    } else { res.writeHead(404); res.end(); }
  });
  let browser;
  const report = { scope: 'Controlled loopback Chromium host; no real deployment or native claim', cases: [], requests };
  try {
    await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
    browser = await chromium.launch({ headless: true, executablePath: process.env.BROWSER_EXECUTABLE_PATH });
    report.browser = browser.version();
    report.fixture_sha256 = crypto.createHash('sha256').update(JSON.stringify({ csp, html, script, css })).digest('hex');
    const page = await browser.newPage();
    page.setDefaultTimeout(5000);
    const base = `http://127.0.0.1:${server.address().port}`;
    const response = await page.goto(base + '/app');
    await page.waitForFunction(() => window.externalExecuted === true);
    const initial = await page.evaluate(() => {
      localStorage.setItem('draft-proof', 'retained draft');
      return { text: document.querySelector('#status').textContent, color: getComputedStyle(document.body).color, inlineExecuted: window.inlineExecuted === true, stored: localStorage.getItem('draft-proof') };
    });
    assert.equal(response.headers()['content-security-policy'], csp);
    assert.equal(initial.inlineExecuted, false);
    assert.equal(initial.color, 'rgb(21, 50, 79)');
    assert.equal(initial.stored, 'retained draft');
    report.cases.push({ id: 'bundled-assets-and-inline-rejection', passed: true, observed: initial });
    await page.reload();
    assert.equal(await page.evaluate(() => localStorage.getItem('draft-proof')), 'retained draft');
    report.cases.push({ id: 'ordinary-origin-storage-reload', passed: true });
    await page.goto(base + '/frame');
    const frame = page.frames().find(f => f.url().endsWith('/app'));
    assert.ok(frame);
    await frame.waitForFunction(() => window.externalExecuted === true);
    const constrained = await frame.evaluate(() => {
      let storage;
      try { localStorage.setItem('draft-proof', 'new draft'); storage = { available: true }; }
      catch (e) { storage = { available: false, error: e.name }; }
      return { rendered: document.querySelector('#status').textContent, externalExecuted: window.externalExecuted === true, storage };
    });
    assert.equal(constrained.rendered, initial.text);
    assert.deepEqual(constrained.storage, { available: false, error: 'SecurityError' });
    report.cases.push({ id: 'renders-but-persistence-blocked', passed: true, observed: constrained });
    await page.screenshot({ path: path.join(output, 'constrained-host.png') });
    report.passed = report.cases.length; report.failed = 0;
  } catch (error) {
    report.failed = 1; report.error = error.stack; process.exitCode = 1;
  } finally {
    if (browser) await browser.close();
    await new Promise(resolve => server.close(resolve));
    fs.writeFileSync(path.join(output, 'report.json'), JSON.stringify(report, null, 2) + '\n');
  }
  console.log(JSON.stringify(report));
}
main().catch(error => { console.error(error); process.exitCode = 1; });
