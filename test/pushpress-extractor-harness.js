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
    title: '', placeholder: '', name: '', type: '', value: '', parent: null,
  }, p);
  return {
    tagName: e.tag, innerText: e.text, title: e.title, placeholder: e.placeholder, name: e.name, type: e.type, value: e.value,
    parentElement: e.parent,
    _sel: e.sel, _clicked: 0,
    getAttribute: k => (k in e.attrs ? e.attrs[k] : null),
    getBoundingClientRect: () => ({ left: e.left, top: e.top, width: e.width, height: e.height, right: e.left + e.width }),
    closest: () => null,
    click() { this._clicked++; },
  };
}
const button = (text, extra) => el(Object.assign({ tag: 'BUTTON', text, sel: ['button', '[role=button]'] }, extra));
const anchor = (text, href, extra) => el(Object.assign({ tag: 'A', text, sel: ['a[href]'], attrs: { href } }, extra));

function makeEnv(elements, loc, title) {
  const store = new Map();
  const dumpNodes = [];
  const document = {
    title: title || '',
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
  const sandbox = { window, document, sessionStorage, URL, URLSearchParams, console,
    setTimeout: fn => setTimeout(fn, 0),
    location: loc || { origin: 'https://tenant.example.invalid', pathname: '/main', search: '', hash: '' } };
  return { sandbox, store, dumpNodes, window };
}

function install(elements, loc, title) {
  const env = makeEnv(elements, loc, title);
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
      button('Collapse sidebar'), button('Expand sidebar'),
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
    const peopleRoute = '/people/' + ['usr', 'a1b2c3d4e5f6a7b8'].join('_');
    const onPeopleRoute = plain(install([panel], { origin: 'https://tenant.example.invalid', pathname: peopleRoute, search: '', hash: '' }).pp.extract());
    assert.strictEqual(onPeopleRoute.region, undefined, 'a person route other than /user/ records no panel text either');
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

  await test('links: mailto, tel and sms links are masked whatever their text, other link text loses contact details, tab routes survive', () => {
    const phone = ['415', '555', '0134'].join('-');
    const elements = [
      anchor('Write ' + FAKE_EMAIL, 'mailto:' + FAKE_EMAIL),
      anchor('Call ' + phone, 'tel:+1' + phone.replace(/-/g, '')),
      anchor('Text us', 'sms:+1' + phone.replace(/-/g, '')),
      anchor('Contact ' + FAKE_EMAIL + ' or ' + phone, '/help/contact'),
      anchor('Non-members', '/people/non-members'),
    ];
    const r = plain(install(elements).pp.extract());
    assert.deepStrictEqual(r.a, ['<item> -> <contact>', 'Contact <email> or <phone> -> /help/contact', 'Non-members -> /people/non-members']);
    const all = JSON.stringify(r);
    for (const leak of [FAKE_EMAIL, phone, phone.replace(/-/g, '')]) assert.ok(!all.includes(leak), 'leaked: ' + leak.length + ' chars');
  });

  await test('text outside buttons: emails and phone-like numbers are masked in headings, tabs, columns, labels and inputs', () => {
    const phone = ['415', '555', '0134'].join(' ');
    const elements = [
      el({ tag: 'H2', text: 'Welcome ' + FAKE_EMAIL, sel: ['h2'] }),
      el({ tag: 'DIV', text: 'Billing ' + phone, sel: ['[role=tab]'] }),
      el({ tag: 'TH', text: 'Phone ' + phone, sel: ['th'] }),
      el({ tag: 'LABEL', text: 'Email ' + FAKE_EMAIL, sel: ['label'] }),
      el({ tag: 'INPUT', sel: ['input'], placeholder: 'Search ' + FAKE_EMAIL }),
      el({ tag: 'H3', text: 'Report 2026-10-01', sel: ['h3'] }),
    ];
    const r = plain(install(elements).pp.extract());
    assert.deepStrictEqual([r.h, r.tabs, r.th, r.lbl, r.inp],
      [['Welcome <email>', 'Report 2026-10-01'], ['Billing <phone>'], ['Phone <phone>'], ['Email <email>'], ['Search <email>']]);
  });

  await test('toggles and inputs labelled "Select <name>" are masked, other toggle labels survive', () => {
    const toggle = label => el({ tag: 'INPUT', sel: ['input', 'input[type=checkbox]'], attrs: { 'aria-label': label } });
    const r = plain(install([toggle('Select ' + FAKE_NAME), toggle('Open gym access'), toggle('Select all')]).pp.extract());
    assert.deepStrictEqual(r.sw, ['Select <item>', 'Open gym access', 'Select all']);
    assert.deepStrictEqual(r.inp, ['Select <item>', 'Open gym access', 'Select all']);
    assert.ok(!JSON.stringify(r).includes(FAKE_NAME));
  });

  await test('the page path is masked on a person page, and the people tab routes are not', () => {
    const where = (pathname, hash) => ({ origin: 'https://tenant.example.invalid', pathname, search: '', hash });
    const person = plain(install([], where(FAKE_PERSON_PATH, '#staff-details')).pp.extract());
    assert.strictEqual(person.p, '/user/<id>#staff-details');
    assert.ok(!JSON.stringify(person).includes('a1b2c3d4e5f6a7b8'));
    assert.strictEqual(plain(install([], where('/people/non-members', '')).pp.extract()).p, '/people/non-members');
  });

  await test('sidebar(): contact links and ID-bearing links in the left column print masked', async () => {
    const link = (text, href) => anchor(text, href, { left: 20 });
    const phone = ['415', '555', '0134'].join('-');
    const { pp } = install([
      link(FAKE_NAME, FAKE_PERSON_PATH + '#staff-details'), link('Mail ' + FAKE_EMAIL, 'mailto:' + FAKE_EMAIL),
      link('Plans', '/plans/list'), link('Call ' + phone, '/help'),
    ]);
    const lines = plain(await pp.sidebar());
    assert.deepStrictEqual(lines, ['LINK  <item>  ->  /user/<id>', 'LINK  <item>  ->  <contact>', 'LINK  Plans  ->  /plans/list', 'LINK  Call <phone>  ->  /help']);
    const all = JSON.stringify(lines);
    for (const leak of [FAKE_NAME, FAKE_EMAIL, phone, 'a1b2c3d4e5f6a7b8']) assert.ok(!all.includes(leak), 'leaked: ' + leak.length + ' chars');
  });

  await test('person routes: the heading and the text-field values are removed from everything recorded, a combobox shows no value, other routes are left alone', () => {
    const person = { origin: 'https://tenant.example.invalid', pathname: FAKE_PERSON_PATH, search: '', hash: '#staff-details' };
    const SECOND = 'Casey Example';                       // appears only in the page title, never in a field
    const elements = [
      el({ tag: 'H1', text: FAKE_NAME, sel: ['h1'] }),
      el({ tag: 'H2', text: SECOND, sel: ['h2'] }),
      el({ tag: 'H3', text: 'Billing', sel: ['h3'] }),
      el({ tag: 'INPUT', sel: ['input'], type: 'text', value: FAKE_NAME, attrs: { 'aria-label': 'Full name' } }),
      el({ tag: 'INPUT', sel: ['input'], type: 'text', value: 'Elm Street 12', attrs: { 'aria-label': 'Street' } }),
      el({ tag: 'INPUT', sel: ['input'], type: 'password', value: 'not-read-by-anything', attrs: { 'aria-label': 'Password' } }),
      button('Prefer not to say', { attrs: { role: 'combobox' } }),
      button('Add Note'),
      el({ tag: 'LABEL', text: 'Lives on Elm Street 12 today', sel: ['label'] }),
    ];
    const r = plain(install(elements, person, SECOND + ' | Profile').pp.extract());
    const all = JSON.stringify(r);
    for (const leak of [FAKE_NAME, SECOND, 'Elm Street 12', 'Prefer not', 'not-read-by-anything']) assert.ok(!all.includes(leak), 'a value reached the output: ' + leak.length + ' chars');
    assert.deepStrictEqual(r.h, ['<value>', 'Billing']);
    assert.deepStrictEqual(r.btn, ['<combobox>', 'Add Note']);
    assert.deepStrictEqual(r.lbl, ['Lives on <value> today']);
    assert.ok(r.inp.includes('Password') && r.inp.includes('Full name'), 'labels survive');
    assert.strictEqual(r.p, '/user/<id>#staff-details');
    // Scrubbing is limited to person routes: elsewhere a field's value is ordinary page text (a search box, a filter).
    const elsewhere = plain(install(elements, { origin: 'https://tenant.example.invalid', pathname: '/plans/list', search: '', hash: '' }, 'Plans').pp.extract());
    assert.ok(JSON.stringify(elsewhere).includes('Prefer not') && JSON.stringify(elsewhere).includes('Elm Street 12'), 'nothing is scrubbed off a person route');
  });

  await test('content that starts just right of a narrow sidebar is recorded: the edge is measured from the sidebar itself', () => {
    const side = el({ tag: 'DIV', left: 0, width: 255, sel: [] });
    const people = el({ tag: 'A', text: 'People', sel: ['a[href="/people"]', 'a[href]'], attrs: { href: '/people' }, left: 8, width: 239, parent: side });
    const header = text => el({ tag: 'TH', text, sel: ['th'], left: 281 });
    const withSidebar = plain(install([people, header('Name'), el({ tag: 'TH', text: 'Inside the sidebar', sel: ['th'], left: 200 })]).pp.extract());
    assert.deepStrictEqual(withSidebar.th, ['Name']);
    assert.strictEqual(withSidebar.a, undefined, 'the sidebar link itself is not page content');
    const noSidebar = plain(install([header('Name')]).pp.extract());
    assert.strictEqual(noSidebar.th, undefined, 'with no sidebar link the fixed 290px edge applies');
  });

  await test('sidebar(): the lines are also parked in #pp-dump, so a page-text read right after it returns them and not the page', async () => {
    const group = n => button(n, { sel: ['button[aria-expanded]', 'button', '[role=button]'], attrs: { 'aria-expanded': 'false' }, left: 20 });
    const { pp, env } = install([group('Plans'), anchor('Plans', '/plans/list', { left: 20 })]);
    const lines = plain(await pp.sidebar());
    assert.deepStrictEqual(lines, ['GROUP Plans', 'LINK  Plans  ->  /plans/list']);
    assert.ok(env.dumpNodes[0] && env.dumpNodes[0].textContent.startsWith('### sidebar'), 'the dump element exists');
    assert.ok(lines.every(l => env.dumpNodes[0].textContent.includes(l)), 'and holds every line');
  });

  console.log('pushpress-extractor-harness.js: PASS (' + checks + ' checks)');
})();
