'use strict';
// Local real-browser calibration. The HTML simulates UI state, not Apex rules.
// No Salesforce authentication, metadata or domain-accuracy claim is made here.
const fs = require('node:fs');
const http = require('node:http');
const path = require('node:path');
const crypto = require('node:crypto');
const runtime = require('./battleship_ui_browser.cjs');

async function main() {
  const args = process.argv.slice(2);
  const outputIndex = args.indexOf('--output');
  if (outputIndex < 0 || !args[outputIndex + 1]) throw new Error('--output is required');
  const output = path.resolve(args[outputIndex + 1]);
  const helperIndex = args.indexOf('--helper');
  const helperPath = helperIndex < 0 ? path.join(__dirname, 'battleship_ui_browser.cjs') : path.resolve(args[helperIndex + 1]);
  const fixturePath = path.join(__dirname, '../fixtures/battleship-ui-local/index.html');
  const { exerciseBoard } = require(helperPath);
  const sha = value => crypto.createHash('sha256').update(value).digest('hex');
  const html = fs.readFileSync(fixturePath);
  fs.mkdirSync(output, { recursive: true });
  const receiptPath = path.join(output, 'receipt.json');
  if (fs.existsSync(receiptPath)) throw new Error('Use a new output directory; prior receipts are retained');
  const positive = [
    'native-aria', 'labelledby', 'image-alt', 'text-name', 'enabled-fired',
    'duplicate-feedback', 'control-like', 'delayed-busy', 'toast-only', 'no-winner-yet', 'you-won',
  ];
  const negative = [
    'bad-shot-count', 'bad-route', 'double-shot-count', 'missing-sink', 'sinking-cell-hit',
    'missing-victory', 'static-victory', 'premature-victory', 'stale-victory',
    'stuck-ships', 'counter-only', 'unrecognized-victory', 'future-winner',
    'undetermined-winner', 'future-victory', 'conditional-win', 'require-controller-local',
  ];
  const variants = [...positive, ...negative];
  const bad = new Set(negative);
  const server = http.createServer((_request, response) => {
    response.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' }); response.end(html);
  });
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  let browser;
  const rows = [];
  try {
    browser = await runtime.playwrightModule().chromium.launch({ headless: true,
      ...(runtime.browserExecutable() ? { executablePath: runtime.browserExecutable() } : {}) });
    for (const variant of variants) {
      const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
      const controllerObserver = runtime.createApexControllerObserver(page, 'ApexController', '127.0.0.1');
      const route = variant === 'bad-route' ? '/lightning/n/Other_Board' : '/lightning/n/Probe_Board';
      const started = Date.now();
      let row;
      try {
        // The factory attaches before navigation; the local fixture stays client-only.
        await page.goto('http://127.0.0.1:' + server.address().port + route + '?variant=' + variant);
        const requireController = variant === 'require-controller-local';
        const observations = await exerciseBoard(page, { prefix: 'Probe', expected_lightning_host: '127.0.0.1',
          controller_class: 'ApexController', require_controller: requireController,
          screenshot: path.join(output, variant + '-reset.png'),
          game_over_screenshot: path.join(output, variant + '-game-over.png') }, controllerObserver);
        row = { variant, pass: true, observations };
      } catch (error) {
        row = { variant, pass: false, stage: error.stage || 'unknown', reason: error.reason || null,
          shot_index: error.shot_index ?? null, row: error.row ?? null, column: error.column ?? null };
      } finally { await page.close(); }
      row.expected_pass = !bad.has(variant);
      row.expected_reason = variant === 'require-controller-local' ? 'controller-new-game-missing' : null;
      row.calibration_pass = row.pass === row.expected_pass
        && (!row.expected_reason || row.reason === row.expected_reason);
      row.elapsed_ms = Date.now() - started;
      rows.push(row); process.stdout.write(JSON.stringify(row) + '\n');
    }
  } finally {
    if (browser) await browser.close();
    await new Promise(resolve => server.close(resolve));
    fs.writeFileSync(receiptPath, JSON.stringify({ scope: 'Local real browser UI coverage, not Salesforce or Apex qualification',
      fixture_sha256: sha(html), helper_sha256: sha(fs.readFileSync(helperPath)),
      browser_version: browser ? browser.version() : null, rows }, null, 2) + '\n');
  }
  if (rows.length !== variants.length || rows.some(row => !row.calibration_pass)) process.exitCode = 1;
}
main().catch(error => { process.stderr.write(error.message + '\n'); process.exitCode = 1; });
