'use strict';

// Run with Node on a host with the existing Chrome/Playwright discovery route.
// A completed RPC can precede the UI's follow-up history load. The driver must
// wait for controls to become actionable and still click each exactly once.
const assert = require('node:assert/strict');
const browserTools = require('../../shiploop_e2e/checks/battleship_ui_browser.cjs');
const driver = require('../../shiploop_e2e/checks/grok_chat_full_ui_browser.cjs');

async function main() {
  const { chromium } = browserTools.playwrightModule();
  const executablePath = browserTools.browserExecutable();
  const browser = await chromium.launch({ headless: true,
    ...(executablePath ? { executablePath } : {}),
    args: ['--password-store=basic', '--use-mock-keychain', '--disable-features=DialMediaRouteProvider'] });
  try {
    const page = await browser.newPage();
    await page.setContent('<button disabled>Setup</button><button disabled>Recheck setup</button>');
    await page.evaluate(() => {
      const [setup, recheck] = document.querySelectorAll('button');
      window.clicks = [];
      setup.addEventListener('click', () => {
        window.clicks.push('Setup');
        setTimeout(() => { recheck.disabled = false; }, 250);
      });
      recheck.addEventListener('click', () => { window.clicks.push('Recheck setup'); });
      setTimeout(() => { setup.disabled = false; }, 250);
    });
    assert.equal(await page.getByRole('button', { name: 'Setup', exact: true }).isEnabled(), false);
    await driver.click(page, 'Setup');
    const recheck = await driver.enabledButton(page, 'Recheck setup');
    assert.equal(await recheck.isEnabled(), true);
    await recheck.click({ timeout: 30000 });
    assert.deepEqual(await page.evaluate(() => window.clicks), ['Setup', 'Recheck setup']);
    process.stdout.write(JSON.stringify({ status: 'PASS', checks: 3, browser: browser.version() }) + '\n');
  } finally {
    await browser.close();
  }
}

main().catch(error => {
  process.stderr.write(String(error.stack || error) + '\n');
  process.exitCode = 1;
});
