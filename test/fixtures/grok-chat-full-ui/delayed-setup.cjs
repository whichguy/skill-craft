'use strict';

// Run with Node on a host with the existing Chrome/Playwright discovery route.
// A completed RPC can precede the UI's follow-up history load. The driver must
// wait for controls to become actionable and still click each exactly once.
const assert = require('node:assert/strict');
const browserTools = require('../../shiploop_e2e/checks/battleship_ui_browser.cjs');
const driver = require('../../shiploop_e2e/checks/grok_chat_full_ui_browser.cjs');

async function duplicateDuringWait(browser, method, label) {
  const page = await browser.newPage();
  const write = process.stderr.write;
  try {
    await page.route('**/*', route => route.abort());
    await page.setContent('<c-sl-grok-chat-app style="display:block"><button disabled>'
      + label + '</button></c-sl-grok-chat-app>');
    await page.evaluate(() => {
      window.events = [];
      document.querySelector('button').addEventListener('click', event => {
        window.events.push(['activated', event.isTrusted]);
      });
    });
    assert.equal(await page.locator('c-sl-grok-chat-app:visible').count(), 1);
    assert.equal(await page.getByRole('button', { name: label, exact: true }).isEnabled(), false);
    let signal;
    const waiting = new Promise(resolve => { signal = resolve; });
    // Wait for a real disabled-state observation before changing the fixture.
    // Playwright logs this for clicks. enabledButton pauses after a false poll.
    const pause = page.waitForTimeout.bind(page);
    page.waitForTimeout = timeout => {
      signal('disabled-poll');
      return pause(timeout);
    };
    process.stderr.write = function (chunk, ...args) {
      if (String(chunk).includes('element is not enabled')) signal('playwright-disabled');
      return write.call(this, chunk, ...args);
    };
    const operation = driver[method](page, label).then(value => ({ outcome: 'fulfilled', control: !!value }),
      error => ({ outcome: 'rejected', reason: error.reason || error.name }));
    const gate = await Promise.race([waiting, operation]);
    assert.ok(['playwright-disabled', 'disabled-poll'].includes(gate));
    await page.evaluate(() => {
      const second = document.createElement('c-sl-grok-chat-app');
      second.style.display = 'block';
      second.textContent = 'Second app without any controls';
      document.body.append(second);
      window.events.push(['second-root-mounted', second.getBoundingClientRect().height > 0,
        second.querySelectorAll('button').length]);
      document.querySelector('button').disabled = false;
      window.events.push(['original-enabled', !document.querySelector('button').disabled]);
    });
    const result = await operation;
    const events = await page.evaluate(() => window.events);
    process.stderr.write(JSON.stringify({ method, label, gate, events, ...result }) + '\n');
    assert.deepEqual(events, [['second-root-mounted', true, 0], ['original-enabled', true]]);
    assert.deepEqual(result, { outcome: 'rejected', reason: 'ui-state-invalid' });
    return { method, label, gate, events, ...result };
  } finally {
    process.stderr.write = write;
    await page.close();
  }
}

async function main() {
  // Observe Playwright's actionability progress in this fixture only.
  process.env.DEBUG = [process.env.DEBUG, 'pw:api'].filter(Boolean).join(',');
  const { chromium } = browserTools.playwrightModule();
  const executablePath = browserTools.browserExecutable();
  const browser = await chromium.launch({ headless: true,
    ...(executablePath ? { executablePath } : {}),
    args: ['--password-store=basic', '--use-mock-keychain', '--disable-features=DialMediaRouteProvider'] });
  try {
    const page = await browser.newPage();
    await page.setContent('<c-sl-grok-chat-app><button disabled>Setup</button>'
      + '<button disabled>Recheck setup</button></c-sl-grok-chat-app>');
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
    const rootRaces = [];
    rootRaces.push(await duplicateDuringWait(browser, 'click', 'Setup'));
    rootRaces.push(await duplicateDuringWait(browser, 'enabledButton', 'Recheck setup'));
    process.stdout.write(JSON.stringify({ status: 'PASS', checks: 3 + rootRaces.length,
      rootRaces, browser: browser.version() }) + '\n');
  } finally {
    await browser.close();
  }
}

main().catch(error => {
  process.stderr.write(String(error.stack || error) + '\n');
  process.exitCode = 1;
});
