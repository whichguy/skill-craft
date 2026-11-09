#!/usr/bin/env node
// Stub-DOM harness for skills/pushpress/scripts/pp-extract.js: the privacy masks, the company-name filter, the
// sidebar reader's read-only behaviour and the storage round trip. There is no browser and no PushPress page
// here, so it pins the extractor's logic and cannot prove behaviour on a live page. Every name, address and ID
// below is synthetic and assembled at run time, so no real-looking value sits in this source file.
// PP_EXTRACT overrides the extractor path: test/pushpress.test.py uses it to run mutated copies.
'use strict';

const assert = require('assert');
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const SRC = fs.readFileSync(
  process.env.PP_EXTRACT || path.join(__dirname, '..', 'skills', 'pushpress', 'scripts', 'pp-extract.js'), 'utf8');

const AT = '@';
const FAKE_EMAIL = ['someone', ['example', 'invalid'].join('.')].join(AT);
const FAKE_PERSON_PATH = '/user/' + ['usr', 'a1b2c3d4e5f6a7b8'].join('_');
const FAKE_NAME = 'Test Person';
const COMPANY = 'Acme Test Gym LLC';

// A fake element: only what the extractor reads. `sel` lists the simple selectors the element answers to.
function el(p) {
  const e = Object.assign({
    tag: 'DIV', text: '', sel: [], attrs: {}, left: 300, top: 100, width: 100, height: 20,
    title: '', placeholder: '', name: '', type: '',
  }, p);
  return {
    tagName: e.tag, innerText: e.text, title: e.title, placeholder: e.placeholder, name: e.name, type: e.type,
    _sel: e.sel, _clicked: 0,
    getAttribute: k => (k in e.attrs ? e.attrs[k] : null),
    getBoundingClientRect: () => ({ left: e.left, top: e.top, width: e.width, height: e.height }),
    closest: () => null,
    click() { this._clicked++; },
  };
}
const button = (text, extra) => el(Object.assign({ tag: 'BUTTON', text, sel: ['button', '[role=button]'] }, extra));
const anchor = (text, href, extra) => el(Object.assign({ tag: 'A', text, sel: ['a[href]'], attrs: { href } }, extra));

function makeEnv(elements, loc) {
  const store = new Map();
  const dumpNodes = [];
  const document = {
    body: { innerText: 'Page 1 of 3', appendChild() {} },
    querySelectorAll(selector) {
      const wanted = selector.split(',').map(s => s.trim());
      return elements.filter(e => e._sel.some(s => wanted.includes(s)));
    },
    getElementById: id => (id === 'pp-dump' ? dumpNodes[0] || null : null),
    createElement() { const n = { id: '', textContent: '', remove() { dumpNodes.length = 0; } }; dumpNodes[0] = n; return n; },
  };
  const sessionStorage = {
    getItem: k => (store.has(k) ? store.get(k) : null),
    setItem: (k, v) => { store.set(k, String(v)); },
    removeItem: k => { store.delete(k); },
  };
  const window = {};
  const sandbox = { window, document, sessionStorage, URL, URLSearchParams, setTimeout, console,
    location: loc || { origin: 'https://tenant.example.invalid', pathname: '/main', search: '', hash: '' } };
  return { sandbox, store, dumpNodes, window };
}

function install(elements, loc) {
  const env = makeEnv(elements, loc);
  const out = vm.runInNewContext(SRC, env.sandbox);
  return { env, out, pp: env.window.__pp };
}

// vm contexts have their own Array/Object prototypes; round-trip through JSON before comparing.
const plain = x => JSON.parse(JSON.stringify(x));

let checks = 0;
const test = async (name, fn) => {
  try { await fn(); checks++; } catch (e) { console.error('FAIL ' + name + '\n' + (e && e.stack || e)); process.exit(1); }
};

(async () => {
  await test('installs, exposes its API and saves itself for restore after a full page load', () => {
    const { out, env, pp } = install([]);
    assert.strictEqual(out, 'pp-extract installed');
    for (const k of ['wait', 'extract', 'store', 'dump', 'clear', 'sidebar', 'company']) {
      assert.strictEqual(typeof pp[k], 'function', k);
    }
    const saved = env.store.get('__pp_lib');
    assert.ok(saved && saved.includes('install'), 'saved itself to sessionStorage');
    // The restore line from the usage notes: (0, eval)(sessionStorage.getItem('__pp_lib'))
    assert.strictEqual(vm.runInNewContext(saved, makeEnv([]).sandbox), 'pp-extract installed');
  });

  await test('buttons: drops labels with an email or 3+ digits, masks person-bearing labels, hides top-bar chrome', () => {
    const elements = [
      button('Save'), button('Close'), button('Select all'),
      button('Search'), button('Toggle Assistant'), button('Product updates'), button('Support and updates'),
      button(COMPANY),
      button('Message ' + FAKE_EMAIL),
      button('Call 5551234'),
      button('Edit ' + FAKE_NAME),
      button('Invoice for ' + FAKE_NAME),
      button('Sidebar item', { left: 20 }),
      button('', { attrs: { 'aria-label': 'Close drawer' } }),
      button(''),
    ];
    const { pp } = install(elements);
    const r = plain(pp.extract());
    assert.deepStrictEqual(r.btn, ['Save', 'Close', 'Select all', COMPANY, 'Edit <item>', 'Invoice for <item>', 'Close drawer']);
    assert.strictEqual(r.icons, 1, 'one icon-only button is counted, never named');
    const all = JSON.stringify(r);
    for (const leak of [FAKE_EMAIL, FAKE_NAME, '5551234']) assert.ok(!all.includes(leak), 'leaked: ' + leak.length + ' chars');
  });

  await test('company(): the declared company label leaves the button lists, and clear() forgets it', () => {
    const { pp, env } = install([button('Save'), button(COMPANY)]);
    assert.ok(plain(pp.extract()).btn.includes(COMPANY));
    assert.strictEqual(pp.company(COMPANY), 'company label set');
    assert.deepStrictEqual(plain(pp.extract()).btn, ['Save']);
    assert.ok(env.store.has('__pp_cfg'));
    pp.clear();
    assert.ok(!env.store.has('__pp_cfg'));
    assert.ok(plain(pp.extract()).btn.includes(COMPANY), 'back to listing it once forgotten');
  });

  await test('company() survives a full page load because it is stored, not held in the closure', () => {
    const { pp, env } = install([button('Save'), button(COMPANY)]);
    pp.company(COMPANY);
    const env2 = makeEnv([button('Save'), button(COMPANY)]);
    for (const [k, v] of env.store) env2.store.set(k, v);                // sessionStorage survives the reload
    vm.runInNewContext(env2.store.get('__pp_lib'), env2.sandbox);        // restore line
    assert.deepStrictEqual(plain(env2.window.__pp.extract()).btn, ['Save']);
  });

  await test('links: IDs become <id>, person links become <item>, external links keep only the host', () => {
    const elements = [
      anchor(FAKE_NAME, FAKE_PERSON_PATH),
      anchor('Transactions', '/reports/transactions'),
      anchor('Docs', 'https://help.example.invalid/x?ref=zzqx9'),
    ];
    const r = plain(install(elements).pp.extract());
    assert.deepStrictEqual(r.a, ['<item> -> /user/<id>', 'Transactions -> /reports/transactions', 'Docs -> EXT help.example.invalid']);
    const all = JSON.stringify(r);
    assert.ok(!all.includes(FAKE_NAME) && !all.includes('a1b2c3d4e5f6a7b8') && !all.includes('zzqx9'));
  });

  await test('side panels: emails are masked, and person pages record no panel text at all', () => {
    const panel = el({ tag: 'ASIDE', text: 'Reach us at ' + FAKE_EMAIL + ' today', sel: ['[role=complementary]', 'aside'] });
    const r = plain(install([panel]).pp.extract());
    assert.deepStrictEqual(r.region, ['Reach us at <email> today']);
    const onPerson = plain(install([panel], { origin: 'https://tenant.example.invalid', pathname: FAKE_PERSON_PATH, search: '', hash: '' }).pp.extract());
    assert.strictEqual(onPerson.region, undefined);
  });

  await test('headings, tabs, columns and the pager are recorded as structure', () => {
    const elements = [
      el({ tag: 'H1', text: 'Membership Change Report', sel: ['h1'] }),
      el({ tag: 'DIV', text: 'Canceled', sel: ['[role=tab]'] }),
      el({ tag: 'TH', text: 'Recurring revenue impact', sel: ['th'] }),
    ];
    const r = plain(install(elements).pp.extract());
    assert.deepStrictEqual([r.h, r.tabs, r.th, r.pg], [['Membership Change Report'], ['Canceled'], ['Recurring revenue impact'], 'Page 1 of 3']);
    assert.strictEqual(r.p, '/main');
  });

  await test('store / dump / clear round trip leaves nothing behind', () => {
    const { pp, env } = install([button('Save')]);
    assert.strictEqual(pp.store('Home'), 'Home');
    assert.ok(plain(JSON.parse(env.store.get('__pp_res'))).Home);
    assert.ok(pp.dump(['Home']) > 0);
    assert.ok(env.dumpNodes[0].textContent.startsWith('### Home'));
    assert.strictEqual(pp.clear(), 'cleared');
    for (const k of ['__pp_res', '__pp_lib', '__pp_cfg']) assert.ok(!env.store.has(k), k);
    assert.strictEqual(env.dumpNodes.length, 0);
  });

  await test('sidebar(): opens only the known groups, never the user menu, and prints no person label', async () => {
    const group = n => button(n, { sel: ['button[aria-expanded]', 'button', '[role=button]'], attrs: { 'aria-expanded': 'false' }, left: 20 });
    const groups = ['Communicate', 'Plans', 'Payments'].map(group);
    const userMenu = group(FAKE_NAME);
    const link = anchor('Plans', '/plans/list', { left: 20 });
    const { pp } = install([...groups, userMenu, link]);
    const lines = plain(await pp.sidebar());
    assert.deepStrictEqual(groups.map(g => g._clicked), [1, 1, 1]);
    assert.strictEqual(userMenu._clicked, 0, 'the user-menu button must not be clicked');
    assert.deepStrictEqual(lines, ['GROUP Communicate', 'GROUP Plans', 'GROUP Payments', 'LINK  Plans  ->  /plans/list']);
    assert.ok(!JSON.stringify(lines).includes(FAKE_NAME));
  });

  console.log('pushpress-extractor-harness.js: PASS (' + checks + ' checks)');
})();
