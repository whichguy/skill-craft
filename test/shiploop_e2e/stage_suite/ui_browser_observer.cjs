#!/usr/bin/env node
// Optional rendered observation for the board fixture. Not part of hermetic oracles.
// Missing fixture selectors are unsupported observation, never an automatic pass.
const fs = require('node:fs');
const path = require('node:path');
const http = require('node:http');
const { pathToFileURL } = require('node:url');

const VIEWS = [
  { width: 1280, height: 900, colorScheme: 'light' },
  { width: 390, height: 844, colorScheme: 'light' },
  { width: 320, height: 740, colorScheme: 'light' },
  { width: 390, height: 844, colorScheme: 'dark' },
];

function options(argv) {
  const args = {};
  while (argv.length) {
    const key = argv.shift();
    if (!['--root', '--out', '--calibrate'].includes(key) || args[key]) throw new Error('Use --root PATH --out NEW_PATH, or --calibrate --out NEW_PATH');
    args[key] = key === '--calibrate' ? true : argv.shift();
    if (!args[key]) throw new Error(`Missing value for ${key}`);
  }
  if (!args['--out'] || Boolean(args['--root']) === Boolean(args['--calibrate'])) throw new Error('Choose a candidate root or calibration');
  return args;
}

function inside(parent, child) {
  const relative = path.relative(parent, child);
  return relative === '' || (!relative.startsWith(`..${path.sep}`) && relative !== '..' && !path.isAbsolute(relative));
}

function serve(root) {
  return new Promise((resolve, reject) => {
    const server = http.createServer((req, res) => {
      try {
        const pathname = decodeURIComponent(new URL(req.url, 'http://localhost').pathname);
        const target = fs.realpathSync(path.join(root, pathname === '/' ? 'index.html' : pathname));
        if (!inside(root, target) || !fs.statSync(target).isFile()) throw new Error('Not a file below the candidate root');
        const types = { '.html': 'text/html', '.mjs': 'text/javascript', '.js': 'text/javascript', '.css': 'text/css', '.json': 'application/json', '.svg': 'image/svg+xml' };
        res.writeHead(200, { 'Content-Type': types[path.extname(target)] || 'application/octet-stream', 'Cache-Control': 'no-store' });
        fs.createReadStream(target).pipe(res);
      } catch (_) { res.writeHead(404); res.end('Not found'); }
    });
    server.once('error', reject);
    server.listen(0, '127.0.0.1', () => resolve({ server, url: `http://127.0.0.1:${server.address().port}/` }));
  });
}

async function observe(browser, root, out, sharedPage) {
  fs.mkdirSync(out, { recursive: true });
  const { server, url } = await serve(fs.realpathSync(root));
  const result = { root, browser: browser.version(), views: [], status: 'passed',
    scope: 'Board-fixture cell geometry, control overlap, horizontal overflow and select/reset only; aesthetics, design-record compliance and accessibility completeness require separate review.' };
  let page = sharedPage;
  try {
    for (const view of VIEWS) {
      const errors = [];
      const onError = error => errors.push(String(error));
      const row = { ...view, checks: {}, errors };
      try {
        page ||= await browser.newPage();
        page.on('pageerror', onError);
        await page.setViewportSize({ width: view.width, height: view.height });
        await page.emulateMedia({ colorScheme: view.colorScheme });
        await page.goto(url);
        const contract = await page.evaluate(() => ({
          board: !!document.querySelector('#board'), reset: !!document.querySelector('#reset'),
          status: !!document.querySelector('#selection-status'), cells: document.querySelectorAll('#board button[data-square]').length,
        }));
        row.contract = contract;
        if (!contract.board || !contract.reset || !contract.status || !contract.cells) {
          row.status = 'unsupported';
          row.reason = 'The fixture selectors changed or did not render; inspect the candidate before attributing a product failure.';
        } else {
          const measure = await page.evaluate(() => {
            const cells = [...document.querySelectorAll('#board button[data-square]')].map(el => {
              const r = el.getBoundingClientRect(); return { width: r.width, height: r.height, x: r.x, y: r.y };
            });
            const board = document.querySelector('#board');
            const regions = ['#board', '#selection-status', '#reset'].map(selector => {
              const r = document.querySelector(selector).getBoundingClientRect();
              return { selector, left: r.left, right: r.right, top: r.top, bottom: r.bottom };
            });
            return { cells, scrollWidth: document.documentElement.scrollWidth, viewportWidth: innerWidth,
              regions,
              colors: { body: getComputedStyle(document.body).backgroundColor, board: getComputedStyle(board).backgroundColor, text: getComputedStyle(document.body).color } };
          });
          row.measurements = measure;
          row.checks.cellCount = contract.cells === 64;
          row.checks.visibleCells = measure.cells.every(c => c.width > 0 && c.height > 0);
          row.checks.squareCells = measure.cells.every(c => Math.abs(c.width - c.height) <= 2);
          row.checks.uniformCells = Math.max(...measure.cells.map(c => c.width)) - Math.min(...measure.cells.map(c => c.width)) <= 2;
          const axes = key => measure.cells.map(c => c[key]).sort((a, b) => a - b)
            .reduce((unique, x) => (!unique.length || x - unique.at(-1) > 2) ? [...unique, x] : unique, []).length;
          row.checks.eightRowsAndColumns = axes('x') === 8 && axes('y') === 8;
          row.checks.noHorizontalOverflow = measure.scrollWidth <= measure.viewportWidth + 1;
          row.checks.noControlOverlap = measure.regions.every((a, i) => measure.regions.slice(i + 1).every(b =>
            Math.min(a.right, b.right) - Math.max(a.left, b.left) <= 1
            || Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top) <= 1));
          const square = page.locator('#board button[data-square="a1"]');
          if (await square.count() !== 1) {
            row.status = 'unsupported'; row.reason = 'The fixture a1 selection target is missing or ambiguous.';
          } else {
            await square.click();
            row.checks.select = /\ba1\b/i.test(await page.locator('#selection-status').innerText());
            await page.locator('#reset').click();
            row.checks.reset = !/\ba1\b/i.test(await page.locator('#selection-status').innerText());
          }
          row.checks.noPageErrors = errors.length === 0;
          row.status ||= Object.values(row.checks).every(Boolean) ? 'passed' : 'failed';
        }
        const screenshot = `${view.width}-${view.colorScheme}.png`;
        await page.screenshot({ path: path.join(out, screenshot), fullPage: true });
        row.screenshot = screenshot;
      } catch (error) { row.status = 'incomplete'; row.error = String(error); }
      finally { if (page) page.off('pageerror', onError); }
      result.views.push(row);
    }
  } finally { await new Promise(resolve => server.close(resolve)); }
  if (result.views.some(r => r.status === 'incomplete')) result.status = 'incomplete';
  else if (result.views.some(r => r.status === 'unsupported')) result.status = 'unsupported';
  else if (result.views.some(r => r.status === 'failed')) result.status = 'failed';
  fs.writeFileSync(path.join(out, 'observation.json'), JSON.stringify(result, null, 2) + '\n');
  return result;
}

function calibrationHtml(defect) {
  const cells = Array.from({ length: 64 }, (_, n) => {
    const square = 'abcdefgh'[n % 8] + (Math.floor(n / 8) + 1);
    return `<button data-square="${square}" aria-label="Square ${square}">${square}</button>`;
  }).join('');
  const mutation = defect === 'uneven-cells' ? '#board button:first-child { aspect-ratio: 2; }'
    : defect === 'mobile-overflow' ? '@media(max-width:500px) { #board { width:700px; max-width:none; } }'
      : defect === 'control-overlap' ? '@media(max-width:500px) { #selection-status { position:absolute; top:40px; left:40px; z-index:2; background:white; pointer-events:none; } }'
        : defect === 'wrong-grid' ? '#board { grid-template-columns:repeat(4,minmax(0,1fr)); }' : '';
  return `<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"><style>
    body{margin:0;padding:16px;box-sizing:border-box;font-family:system-ui}#board{display:grid;grid-template-columns:repeat(8,minmax(0,1fr));width:100%;max-width:512px}
    #board button{aspect-ratio:1;min-width:0;padding:0} ${mutation}
    </style></head><body><div id="board">${cells}</div><p id="selection-status" role="status">Choose a square</p><button id="reset">Reset</button>
    <script>document.querySelector('#board').onclick=e=>{if(e.target.dataset.square)document.querySelector('#selection-status').textContent='Selected: '+e.target.dataset.square};document.querySelector('#reset').onclick=()=>{document.querySelector('#selection-status').textContent='Choose a square'};</script></body></html>`;
}

async function main() {
  const args = options(process.argv.slice(2));
  const out = path.resolve(args['--out']);
  if (fs.existsSync(out)) throw new Error('Output must be new; never overwrite an observation');
  const root = args['--root'] ? fs.realpathSync(args['--root']) : null;
  if (root && inside(root, out)) throw new Error('Output must be outside the candidate tree');
  fs.mkdirSync(out, { recursive: true });
  let browser;
  try {
    const pw = require(process.env.PLAYWRIGHT_NODE_PATH || process.env.PLAYWRIGHT_MODULE_PATH || 'playwright');
    browser = await pw.chromium.launch({ headless: true, ...(process.env.BROWSER_EXECUTABLE_PATH ? { executablePath: process.env.BROWSER_EXECUTABLE_PATH } : {}) });
    // Keep one context/page alive through all viewports and calibration fixtures.
    // The initial local calibration lost its browser between viewport contexts.
    const page = await browser.newPage();
    if (root) {
      const result = await observe(browser, root, out, page);
      console.log(JSON.stringify({ status: result.status, evidence: pathToFileURL(path.join(out, 'observation.json')).href }));
      process.exitCode = result.status === 'passed' ? 0 : result.status === 'failed' ? 1 : 2;
    } else {
      const observed = {};
      for (const variant of ['good', 'uneven-cells', 'mobile-overflow', 'control-overlap', 'wrong-grid']) {
        const fixture = path.join(out, 'fixtures', variant);
        fs.mkdirSync(fixture, { recursive: true });
        fs.writeFileSync(path.join(fixture, 'index.html'), calibrationHtml(variant));
        observed[variant] = await observe(browser, fixture, path.join(out, variant), page);
      }
      const pass = observed.good.status === 'passed'
        && Object.entries(observed).filter(([name]) => name !== 'good').every(([, result]) => result.status === 'failed')
        && observed['uneven-cells'].views.some(r => r.checks.squareCells === false)
        && observed['mobile-overflow'].views.some(r => r.width <= 500 && r.checks.noHorizontalOverflow === false)
        && observed['control-overlap'].views.some(r => r.width <= 500 && r.checks.noControlOverlap === false)
        && observed['wrong-grid'].views.some(r => r.checks.eightRowsAndColumns === false);
      const receipt = { pass, results: Object.fromEntries(Object.entries(observed).map(([k, v]) => [k, v.status])) };
      fs.writeFileSync(path.join(out, 'calibration.json'), JSON.stringify(receipt, null, 2) + '\n');
      console.log(JSON.stringify(receipt)); process.exitCode = pass ? 0 : 1;
    }
  } catch (error) {
    fs.writeFileSync(path.join(out, 'error.json'), JSON.stringify({ status: 'incomplete', error: String(error) }, null, 2) + '\n');
    throw error;
  } finally { if (browser) await browser.close(); }
}

if (require.main === module) main().catch(error => { console.error(String(error)); process.exitCode = 2; });
module.exports = { observe, calibrationHtml, VIEWS };
