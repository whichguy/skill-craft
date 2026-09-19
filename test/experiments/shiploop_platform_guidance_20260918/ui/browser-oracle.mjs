import { createHash } from 'node:crypto';
import { existsSync } from 'node:fs';
import { readFile, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);
const here = path.dirname(fileURLToPath(import.meta.url));
const fixturePath = path.join(here, 'fixture.html');
const browserExecutable = process.env.BROWSER_EXECUTABLE_PATH || '';
const outputIndex = process.argv.indexOf('--output');
const outputPath = outputIndex === -1
  ? path.join(here, 'results.json')
  : path.resolve(process.argv[outputIndex + 1] || '');

function assertion(condition, message) {
  if (!condition) throw new Error(message);
}

function hashFile(filename) {
  return readFile(filename).then((contents) => createHash('sha256').update(contents).digest('hex'));
}

function firstLine(error) {
  return String(error instanceof Error ? error.message : error).split('\n')[0];
}

async function withPage(browser, variant, test) {
  const context = await browser.newContext();
  const page = await context.newPage();
  try {
    const url = `${pathToFileURL(fixturePath).href}?variant=${variant}`;
    await page.goto(url, { waitUntil: 'load' });
    await page.waitForFunction(() => Boolean(window.__shiploopFixture));
    return await test(page);
  } finally {
    await context.close();
  }
}

async function nextRequest(page, query) {
  const requests = await page.evaluate(() => window.__shiploopFixture.pending());
  const request = requests.find((candidate) => candidate.query === query);
  assertion(request, `Expected pending request for ${query}; saw ${JSON.stringify(requests)}`);
  return request;
}

async function resolve(page, request, labels) {
  await page.evaluate(({ id, labels: resolvedLabels }) => {
    window.__shiploopFixture.resolve(id, resolvedLabels);
  }, { id: request.id, labels });
  await page.waitForFunction((id) => window.__shiploopFixture.snapshot().events.some(
    (event) => event.id === id && (event.type === 'applied-result' || event.type === 'ignored-stale-result'),
  ), request.id);
}

async function startByRole(page, query) {
  await page.getByLabel('Search notes').fill(query);
  await page.getByRole('button', { name: 'Search' }).click();
  return nextRequest(page, query);
}

async function checkRaceFreshness(page) {
  const oldRequest = await startByRole(page, 'old');
  const currentRequest = await startByRole(page, 'current');
  assertion(oldRequest.id < currentRequest.id, 'Expected monotonic request identifiers.');

  await resolve(page, currentRequest, ['Current note']);
  assertion(
    JSON.stringify(await page.getByRole('listitem').allTextContents()) === JSON.stringify(['Current note']),
    'The current response must render before the older response arrives.',
  );

  await resolve(page, oldRequest, ['Old note']);
  assertion(
    JSON.stringify(await page.getByRole('listitem').allTextContents()) === JSON.stringify(['Current note']),
    'A completed older request overwrote the newer visible result.',
  );
  assertion(
    (await page.getByRole('status').textContent()).includes('current'),
    'The user-visible status regressed to the older search.',
  );
}

async function checkSemanticKeyboard(page) {
  const input = page.getByLabel('Search notes');
  const namedButtonCount = await page.getByRole('button', { name: 'Search' }).count();
  await input.fill('keyboard');
  await input.focus();
  await page.keyboard.press('Tab');
  const focusedId = await page.evaluate(() => document.activeElement?.id || '');
  assertion(
    namedButtonCount === 1 && focusedId === 'search-button',
    `Search needs one named button reached by Tab; buttons=${namedButtonCount}, active=${focusedId || '<none>'}.`,
  );
  await page.keyboard.press('Enter');

  const request = await nextRequest(page, 'keyboard');
  await resolve(page, request, ['Keyboard note']);
  assertion(await page.getByRole('status').getAttribute('aria-live') === 'polite', 'Status must be a polite live region.');
  assertion(await page.getByRole('list', { name: 'Search results' }).count() === 1, 'Results must expose a named list.');
  assertion(
    JSON.stringify(await page.getByRole('listitem').allTextContents()) === JSON.stringify(['Keyboard note']),
    'Keyboard activation did not lead to the visible result.',
  );
}

async function checkOrdinaryPointer(page) {
  await page.getByLabel('Search notes').fill('pointer');
  await page.getByText('Search', { exact: true }).click();
  const request = await nextRequest(page, 'pointer');
  await resolve(page, request, ['Pointer note']);
  assertion(
    JSON.stringify(await page.locator('#results > li').allTextContents()) === JSON.stringify(['Pointer note']),
    'A pointer click did not produce the expected visible result.',
  );
}

async function checkWeakStructuralControl(page) {
  await page.getByLabel('Search notes').fill('ordinary');
  await page.locator('#search-button').click();
  const request = await nextRequest(page, 'ordinary');
  await resolve(page, request, ['Ordinary note']);
  assertion(await page.locator('#results').count() === 1, 'The structural result container is missing.');
  assertion(await page.locator('#results > li').count() === 1, 'The structural test expected one result node.');
}

async function run() {
  const startedAt = new Date().toISOString();
  const result = {
    schemaVersion: 1,
    experiment: 'shiploop_platform_guidance_20260918/ui',
    kind: 'calibration-only browser fixture; no coding-agent trial',
    startedAt,
    environment: {
      node: process.version,
      platform: process.platform,
      architecture: process.arch,
      playwright: null,
      browserExecutable,
      browserVersion: null,
    },
    inputs: {
      fixture: { path: 'fixture.html', sha256: await hashFile(fixturePath) },
      oracle: { path: 'browser-oracle.mjs', sha256: await hashFile(fileURLToPath(import.meta.url)) },
    },
    command: process.argv.map((part) => String(part)),
    cases: [],
    limitations: [
      'The response controller is a local fixture seam; it proves this UI mechanism under its schedule, not an HTTP, cache, service-worker, or framework integration.',
      'Role and keyboard checks are browser-observable accessibility evidence. They do not establish screen-reader usability or WCAG conformance.',
      'Calibration rejects two plausible mutants and shows one weak check can miss the stale-result mutant. It does not compare ShipLoop guidance arms or prove an instruction improves agent coding.',
    ],
  };

  let browser;
  try {
    assertion(browserExecutable, 'Set BROWSER_EXECUTABLE_PATH to an already available Chromium executable.');
    assertion(existsSync(browserExecutable), `Browser executable is unavailable: ${browserExecutable}`);
    const { chromium } = require('playwright');
    result.environment.playwright = require('playwright/package.json').version;
    browser = await chromium.launch({ headless: true, executablePath: browserExecutable });
    result.environment.browserVersion = browser.version();

    const matrix = [
      { id: 'UI-R1', label: 'reference preserves newest async result', variant: 'reference', expected: 'pass', check: checkRaceFreshness },
      { id: 'UI-R2', label: 'stale-result mutant is rejected by reversal oracle', variant: 'stale', expected: 'fail', check: checkRaceFreshness },
      { id: 'UI-A1', label: 'reference exposes keyboard-operable semantics', variant: 'reference', expected: 'pass', check: checkSemanticKeyboard },
      { id: 'UI-A2', label: 'clickable div mutant is rejected by semantic keyboard oracle', variant: 'div-button', expected: 'fail', check: checkSemanticKeyboard },
      { id: 'UI-O1', label: 'reference supports ordinary pointer behavior', variant: 'reference', expected: 'pass', check: checkOrdinaryPointer },
      { id: 'UI-O2', label: 'stale-result mutant still passes an ordinary one-response flow', variant: 'stale', expected: 'pass', check: checkOrdinaryPointer },
      { id: 'UI-O3', label: 'clickable div mutant still passes an ordinary pointer flow', variant: 'div-button', expected: 'pass', check: checkOrdinaryPointer },
      { id: 'UI-W1', label: 'weak structural check accepts reference', variant: 'reference', expected: 'pass', check: checkWeakStructuralControl },
      { id: 'UI-W2', label: 'weak structural check also accepts stale-result mutant', variant: 'stale', expected: 'pass', check: checkWeakStructuralControl },
    ];

    for (const entry of matrix) {
      const caseStarted = Date.now();
      let actual = 'pass';
      let error = null;
      try {
        await withPage(browser, entry.variant, entry.check);
      } catch (caught) {
        actual = 'fail';
        error = firstLine(caught);
      }
      result.cases.push({
        id: entry.id,
        label: entry.label,
        variant: entry.variant,
        expected: entry.expected,
        actual,
        matchesExpected: actual === entry.expected,
        durationMs: Date.now() - caseStarted,
        error,
      });
    }
  } catch (caught) {
    result.infrastructureError = firstLine(caught);
  } finally {
    if (browser) await browser.close();
  }

  const mismatches = result.cases.filter((entry) => !entry.matchesExpected);
  result.finishedAt = new Date().toISOString();
  result.summary = {
    total: result.cases.length,
    matchedExpected: result.cases.length - mismatches.length,
    mismatchedExpected: mismatches.length,
    calibrated: !result.infrastructureError && mismatches.length === 0,
  };
  await writeFile(outputPath, `${JSON.stringify(result, null, 2)}\n`);
  if (!result.summary.calibrated) process.exitCode = 1;
}

await run();
