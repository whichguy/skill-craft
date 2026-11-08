'use strict';

// Synthetic Chrome pages exercise the same keyboard and click helpers as the
// attended setup journey. No fixture can reach Salesforce or a provider.
const assert = require('node:assert/strict');
const browserTools = require('../../shiploop_e2e/checks/battleship_ui_browser.cjs');
const driver = require('../../shiploop_e2e/checks/grok_chat_full_ui_browser.cjs');

const scenarios = {
  'shell-anchor-first': { open: true, shellFirst: true, trap: true },
  'app-first-with-native-shell-buttons': { multipleShell: true },
  'delayed-shadow-role-button': { shadow: true, delay: true, shellFirst: true },
  'hidden-root-and-control-are-ignored': { hiddenDecoys: true },
  'missing-root': { root: 'main', expected: 'ui-control-missing' },
  'ambiguous-roots': { duplicateRoot: true, expected: 'ui-state-invalid' },
  'missing-app-setup': { noSetup: true, expected: 'ui-control-missing' },
  'ambiguous-app-setup': { duplicateButton: '<button>Setup</button>', expected: 'ui-state-invalid' },
  'ambiguous-with-disabled-app-setup': {
    duplicateButton: '<button disabled>Setup</button>', expected: 'ui-state-invalid',
  },
  'native-disabled-setup': { setupAttrs: 'disabled', expected: 'ui-control-missing' },
  'aria-disabled-setup': { setupAttrs: 'aria-disabled="true"', expected: 'ui-control-missing' },
  'inert-setup': { setupAttrs: 'inert', expected: ['ui-control-missing', 'keyboard-inaccessible'] },
  'pointer-only-setup-with-closed-config': { pointerOnly: true, expected: 'ui-control-missing' },
  'focused-labelled-div': { decoy: '<div tabindex="0" aria-label="Model">Fake</div>' },
  'focused-labelled-wrapper': { decoy: '<label tabindex="0" aria-label="Model"><input tabindex="-1"></label>' },
  'focused-outside-native-input': { outside: '<input aria-label="Model">' },
  'focused-wrong-exact-label': { decoy: '<input aria-label="Model details">' },
  'focused-aria-disabled-input': { decoy: '<input aria-label="Model" aria-disabled="true">' },
  'focused-transparent-input': { decoy: '<input aria-label="Model" style="opacity:0">' },
  'focused-non-text-input': { decoy: '<input type="checkbox" aria-label="Model">' },
};

function mount(options) {
  const rootName = options.root || 'c-sl-grok-chat-app';
  const app = document.createElement(rootName);
  app.style.display = 'block';
  const shell = document.createElement('nav');
  shell.innerHTML = options.multipleShell ? '<button>Setup</button><button>Setup</button>'
    : '<a href="#" role="button">Setup</a>';
  const trap = document.createElement('div');
  trap.hidden = true;
  trap.innerHTML = '<button>Shell settings</button>'.repeat(11);
  shell.append(trap);
  window.activation = [];
  window.tabFocus = [];
  shell.querySelectorAll('[role="button"], button').forEach(button => {
    button.onclick = event => {
      event.preventDefault();
      window.activation.push('shell');
      if (options.trap) {
        trap.hidden = false;
        trap.firstElementChild.focus();
      }
    };
    if (button.tagName === 'A') button.onkeydown = event => {
      if (event.key === 'Enter') {
        event.preventDefault();
        button.click();
      }
    };
  });
  document.addEventListener('keyup', event => {
    if (event.key !== 'Tab') return;
    let focused = document.activeElement;
    while (focused?.shadowRoot?.activeElement) focused = focused.shadowRoot.activeElement;
    if (focused?.matches('[data-fixture-decoy]')) window.tabFocus.push(focused.tagName);
  });

  if (options.shellFirst) document.body.append(shell);
  const insert = () => {
    if (options.shellFirst) document.body.append(app);
    else document.body.insertBefore(app, shell);
  };
  if (!options.shellFirst) document.body.append(shell);
  if (options.duplicateRoot || options.hiddenDecoys) {
    const other = document.createElement(rootName);
    other.hidden = !!options.hiddenDecoys;
    other.textContent = 'Other app instance';
    document.body.append(other);
  }
  if (options.outside) {
    shell.insertAdjacentHTML('afterend', options.outside);
    shell.nextElementSibling.setAttribute('data-fixture-decoy', '');
  }
  const container = options.shadow ? app.attachShadow({ mode: 'open' }) : app;
  const falseFocus = options.decoy || options.outside;
  const setup = options.noSetup ? '' : options.shadow || options.pointerOnly
    ? '<div role="button" tabindex="0" id="setup">Setup</div>'
    : '<button id="setup" ' + (options.setupAttrs || '') + '>Setup</button>';
  const configure = () => {
    container.innerHTML = setup + (options.duplicateButton || '')
      + (options.hiddenDecoys ? '<button hidden>Setup</button>' : '')
      + '<div id="config" hidden></div><button id="connection">Test connection</button>';
    const panel = container.querySelector('#config');
    const render = () => {
      panel.hidden = false;
      if (panel.hasChildNodes()) return;
      const fields = options.shadow
        ? panel.appendChild(document.createElement('div')).attachShadow({ mode: 'open' }) : panel;
      fields.innerHTML = '<label>Named credential<input ' + (falseFocus ? 'tabindex="-1"' : '') + '></label>'
        + (falseFocus ? options.decoy || '' : '<span id="model-label">Model</span><textarea aria-labelledby="model-label"></textarea>');
      if (options.decoy) fields.lastElementChild.setAttribute('data-fixture-decoy', '');
    };
    const control = container.querySelector('#setup');
    if (control) {
      control.onclick = event => {
        window.activation.push(event.detail === 0 ? 'app-keyboard' : 'app-pointer');
        if (options.delay) setTimeout(render, 180);
        else render();
        if (options.open) panel.querySelector('input').focus();
      };
      if (options.shadow) control.onkeydown = event => {
        if (event.key === 'Enter') control.click();
      };
    }
    window.configOpen = () => !panel.hidden;
    container.querySelector('#connection').onclick = () => {
      window.activation.push('connection');
      panel.hidden = true;
    };
    if (options.open) render();
  };
  if (options.delay) {
    setTimeout(() => {
      insert();
      setTimeout(configure, 140);
    }, 140);
  } else {
    configure();
    insert();
  }
}

async function scenario(browser, name, options) {
  const page = await browser.newPage();
  try {
    await page.route('**/*', route => route.abort());
    await page.setContent('<!doctype html><body></body>');
    await page.evaluate(mount, options);
    let reason;
    try {
      assert.equal(await driver.keyboardCheck(page), true);
    } catch (error) {
      reason = error.reason || error.name;
    }
    const activation = () => page.evaluate(() => window.activation);
    const observed = { name, keyboard: reason || 'pass', activation: await activation(),
      decoyFocus: await page.evaluate(() => window.tabFocus) };
    if (reason && !options.expected && !options.decoy && !options.outside) {
      // Still measure the later Setup click on the same shell/app arrangement.
      await page.evaluate(() => { window.activation = []; });
      await driver.click(page, 'Setup');
      observed.reopen = await activation();
    }
    const expected = options.expected || ((options.decoy || options.outside) ? 'keyboard-inaccessible' : null);
    try {
      if (expected) {
        assert.ok([expected].flat().includes(reason), 'Expected rejection, got ' + observed.keyboard);
        if (options.decoy || options.outside) {
          assert.deepEqual(observed.activation, ['app-keyboard']);
          assert.ok(observed.decoyFocus.length > 0, 'Tab must actually reach the false focus target');
        } else {
          assert.deepEqual(observed.activation, []);
          if (options.pointerOnly) {
            assert.equal(await page.evaluate(() => window.configOpen()), false);
            await driver.click(page, 'Setup');
            assert.equal(await page.evaluate(() => window.configOpen()), true);
            assert.deepEqual(await activation(), ['app-pointer']);
          }
        }
      } else {
        assert.equal(reason, undefined);
        assert.deepEqual(observed.activation, ['app-keyboard']);
        assert.equal(await page.evaluate(() => window.configOpen()), true);
        await driver.click(page, 'Test connection');
        assert.equal(await page.evaluate(() => window.configOpen()), false);
        await driver.click(page, 'Setup');
        await page.waitForFunction(() => window.configOpen());
        observed.reopen = await activation();
        assert.deepEqual(observed.reopen, ['app-keyboard', 'connection', 'app-pointer']);
      }
      return { ...observed, status: 'PASS' };
    } catch (error) {
      process.stderr.write(name + ': ' + String(error.stack || error) + '\n');
      return { ...observed, status: 'FAIL' };
    }
  } finally {
    await page.close();
  }
}

async function main() {
  const { chromium } = browserTools.playwrightModule();
  const executablePath = browserTools.browserExecutable();
  const browser = await chromium.launch({ headless: true,
    ...(executablePath ? { executablePath } : {}),
    args: ['--password-store=basic', '--use-mock-keychain', '--disable-features=DialMediaRouteProvider'] });
  try {
    const entries = Object.entries(scenarios);
    const results = [];
    for (let start = 0; start < entries.length; start += 6) {
      results.push(...await Promise.all(entries.slice(start, start + 6)
        .map(([name, options]) => scenario(browser, name, options))));
    }
    const status = results.every(result => result.status === 'PASS') ? 'PASS' : 'FAIL';
    process.stdout.write(JSON.stringify({ status, scenarios: results, browser: browser.version() }) + '\n');
    if (status === 'FAIL') process.exitCode = 1;
  } finally {
    await browser.close();
  }
}

main().catch(error => {
  process.stderr.write(String(error.stack || error) + '\n');
  process.exitCode = 1;
});
