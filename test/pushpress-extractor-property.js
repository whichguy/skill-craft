#!/usr/bin/env node
// Seeded property test and over-masking audit for skills/pushpress/scripts/pp-extract.js, on the same kind of stub DOM as
// test/pushpress-extractor-harness.js (no browser, no PushPress page; the real-browser counterpart is
// test/fixtures/pushpress-extractor/privacy-fixture.cjs). Every name, address and number is made up; phone numbers and email addresses are
// assembled at run time so that no file holds a complete one.
//
//   node test/pushpress-extractor-property.js            5000 pages from a fixed seed
//   PP_PROPERTY_PAGES=20000 PP_PROPERTY_SEED=7 node test/pushpress-extractor-property.js
//   PP_EXTRACT=<file> tests another copy of the extractor.
//
// Properties, on every generated page:
//   P1 contract      a planted value never appears in any returned string or in dump(): emails, phone numbers in five formats, a
//                    person's name inside "Select/Edit/... <name>" and "... for <name>" labels, person links, contact links, and, on a
//                    person route, the owner's and a guardian's names (which the page also shows in text fields) and combobox values
//   P2 structure     a structural label placed at or right of the content edge is returned, in its field, unless it holds a scrubbed word
//   P3 edge          a label placed left of the edge is not returned
//   P4 caps          no field is longer than its cap, and off a person route a field with more distinct entries than its cap holds exactly the cap (headings, buttons);
//                    rows and icons are counted exactly (a named icon-only button is not an unnamed icon)
//   P5 path          the path field holds no record id and no query value
//   P6 sidebar       sidebar() parks its lines, prints every group and ordinary link, and prints no person (the user menu is skipped)
//   (also P1 region: no side-panel text on a person route)
// Not a property (a recorded KNOWN GAP): a second person's name shown only as plain text on a person page. The test counts how often
// that name reaches the output ("gap exposure") and fails if it ever stops, so the case is promoted.
// The audit then counts how many of the labels the skill's own references quote a person's name would mask, for common words used as names.
'use strict';

const assert = require('assert');
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const ROOT = path.join(__dirname, '..');
const EXTRACTOR_PATH = process.env.PP_EXTRACT || path.join(ROOT, 'skills', 'pushpress', 'scripts', 'pp-extract.js');
const SRC = fs.readFileSync(EXTRACTOR_PATH, 'utf8');
const PAGES = Number(process.env.PP_PROPERTY_PAGES || 5000);
const SEED = Number(process.env.PP_PROPERTY_SEED || 1109);
const JSON_OUT = process.argv.includes('--json') ? process.argv[process.argv.indexOf('--json') + 1] : '';

// --controls: run this test against the unbroken extractor (it must pass, or every control below would read as caught) and then against each
// deliberately broken copy (shared with the browser fixture). A control is caught only when the run reaches a verdict (it did not crash or
// fail to parse), exits 1 and prints one of the property tags that mutation is expected to trip; anything else is an ERROR or a miss.
if (process.argv.includes('--controls')) {
  const { MUTATIONS, apply } = require('./fixtures/pushpress-extractor/mutations.cjs');
  const { spawnSync } = require('child_process');
  const dir = fs.mkdtempSync(path.join(require('os').tmpdir(), 'pp-property-controls-'));
  const run = file => spawnSync(process.execPath, [__filename], { env: Object.assign({}, process.env, { PP_EXTRACT: file, PP_PROPERTY_PAGES: '600' }), encoding: 'utf8' });
  const verdict = r => /pushpress extractor property test: \d+ pages/.test(r.stdout);        // printed only after every page was judged
  let blind = 0;
  const base = run(EXTRACTOR_PATH);
  const baseOk = base.status === 0 && verdict(base);
  console.log(`CONTROL baseline (the extractor as given): ${baseOk ? 'passes' : 'DOES NOT PASS: the controls below mean nothing'}`);
  if (!baseOk) blind++;
  for (const m of MUTATIONS.filter(x => x.tests.includes('property'))) {
    const broken = apply(SRC, m);
    if (broken === null) { console.log(`CONTROL ${m.name}: STALE (the text it breaks is gone or no longer unique)`); blind++; continue; }
    const file = path.join(dir, m.name + '.js'); fs.writeFileSync(file, broken);
    const r = run(file);
    const tags = [...new Set((r.stdout.match(/P\d [a-z]+/g) || []))];
    const expected = (m.expect && m.expect.property) || [];
    const ok = r.status === 1 && verdict(r) && expected.some(t => tags.includes(t));
    const why = ok ? 'caught' : !verdict(r) || r.status > 1 || r.status === null ? 'ERROR (it crashed or never reached a verdict)' : r.status === 0 ? 'MISSED' : 'caught the wrong thing';
    console.log(`CONTROL ${m.name}: ${why}${tags.length ? ' (' + tags.join(', ') + ')' : ''}`);
    if (!ok) blind++;
  }
  fs.rmSync(dir, { recursive: true, force: true });
  console.log(`pushpress-extractor-property.js --controls: ${blind ? 'FAIL' : 'PASS'}`);
  process.exit(blind ? 1 : 0);
}

// ---- the stub DOM, as in the harness: only what the extractor reads ------------------------------------------------------
function el(p) {
  const e = Object.assign({ tag: 'DIV', text: '', sel: [], attrs: {}, left: 300, top: 100, width: 100, height: 20, title: '', placeholder: '', name: '', type: '', value: '', parent: null }, p);
  return {
    tagName: e.tag, innerText: e.text, title: e.title, placeholder: e.placeholder, name: e.name, type: e.type, value: e.value, parentElement: e.parent,
    _sel: e.sel, _clicked: 0, getAttribute: k => (k in e.attrs ? e.attrs[k] : null),
    getBoundingClientRect: () => ({ left: e.left, top: e.top, width: e.width, height: e.height, right: e.left + e.width }),
    closest: () => null, click() { this._clicked++; },
  };
}
function install(elements, loc, title) {
  const store = new Map(); const dumpNodes = [];
  const document = {
    title: title || '', body: { innerText: 'Page 1 of 3', appendChild() {} },
    querySelectorAll(selector) { const wanted = selector.split(',').map(s => s.trim()); return elements.filter(e => e._sel.some(s => wanted.includes(s))); },
    getElementById: id => (id === 'pp-dump' ? dumpNodes[0] || null : null),
    createElement() { const n = { id: '', textContent: '', remove() { dumpNodes.length = 0; } }; dumpNodes[0] = n; return n; },
  };
  const sessionStorage = { getItem: k => (store.has(k) ? store.get(k) : null), setItem: (k, v) => { store.set(k, String(v)); }, removeItem: k => { store.delete(k); } };
  const window = {};
  const sandbox = { window, document, sessionStorage, URL, URLSearchParams, console, setTimeout: fn => setTimeout(fn, 0), location: loc };
  vm.runInNewContext(SRC, sandbox);
  return { pp: window.__pp, dumpNodes };
}
const plain = x => JSON.parse(JSON.stringify(x));

// ---- seeded randomness ----------------------------------------------------------------------------------------------------
function rng(seed) {
  let a = seed >>> 0;
  const next = () => { a = (a + 0x6D2B79F5) | 0; let t = Math.imul(a ^ (a >>> 15), 1 | a); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 2 ** 32; };
  return { next, int: n => Math.floor(next() * n), chance: p => next() < p, pick: a => a[Math.floor(next() * a.length)] };
}

// ---- synthetic people -----------------------------------------------------------------------------------------------------
const FIRST = ['Zephyra', 'Anne-Marie', 'Daithi', 'José', 'Li', 'Mark', 'Will', 'Grace', 'Rose', 'Hope', 'Pat', 'Dawn', 'Sue', 'Amber', 'Hunter', 'Cash', 'Bill', 'Jack', 'Max', 'Noor', 'Ana', 'Ty', 'Bo', 'Ottoline', 'Perpetua', 'Rosalind', 'Cornelius', 'Philippa', 'Margaret (Peggy)'];
const LAST = ['Quillfeather', 'Wolfeschlegel-Stein', "O'Brannigan", 'Peña', 'Xu', 'Page', 'Stone', 'Fields', 'Bell', 'Young', 'Hill', 'King', 'Cook', 'Love', 'Sharp', 'Drummond', 'Ng', 'Yu', 'Mann', 'Tuckerbottom', 'Applewhite', 'Gooseberry'];
let seq = 0, idSeq = 0;
const cat = (...p) => p.join('');
const slug = s => s.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
function person(R, taken) {                                                  // `taken`: full names already used on this page, so two people never share one
  seq++;
  let first, last;
  do { first = R.pick(FIRST); last = R.pick(LAST); } while (taken.has((first + ' ' + last).toLowerCase()));
  taken.add((first + ' ' + last).toLowerCase());
  const tail = String(100 + (seq % 900)).padStart(4, '0');
  const d = cat('555', '010', tail);                                         // made-up digit groups, not a dialable number; assembled
  return {
    first, last, full: first + ' ' + last, id: cat('usr', '_', '9f3c', String(seq).padStart(8, '0')),
    email: cat('p', seq, '.fixture', '@', 'example', '.invalid'), digits: d,
    phones: [`(${d.slice(0, 3)}) ${d.slice(3, 6)}-${d.slice(6)}`, `${d.slice(0, 3)}-${d.slice(3, 6)}-${d.slice(6)}`, `${d.slice(0, 3)}.${d.slice(3, 6)}.${d.slice(6)}`, `+1 ${d.slice(0, 3)} ${d.slice(3, 6)} ${d.slice(6)}`, d],
    dob: cat('20', '12-', '04-', String(10 + (seq % 18))),
    gapDigits: cat('555', '011', tail), gapText: cat('(555)', '011-', tail),   // typed without a separator after the closing parenthesis: not matched by the text mask (a known gap)
  };
}

// ---- structural vocabulary (none of it may match the masks: see the check below) -------------------------------------------
const VOCAB = {
  h: ['Details', 'Family', 'Billing', 'Attendance', 'Memberships', 'Documents', 'Notes', 'Payments', 'Overview', 'Class types', 'Plans', 'Reports', 'Upcoming payments', 'Check-ins'],
  tabs: ['Overview', 'Billing', 'Attendance', 'Notes', 'Members', 'Leads', 'Staff', 'Active', 'Paused'],
  btn: ['Save', 'Cancel', 'Add member', 'Download CSV', 'Add Plan', 'Mark attendance', 'Request Payment Method', 'Next', 'Previous', 'Filters', 'Export', 'Setup pay rates', '+ Class type', 'Back'],
  th: ['Name', 'Email', 'Phone', 'Plan', 'Date', 'Class', 'Status', 'Amount', 'Visibility', 'Pay rate'],
  lbl: ['First name', 'Last name', 'Email', 'Phone', 'Date of birth', 'Emergency contact', 'Gender', 'Role', 'Start date'],
  inp: ['Search members', 'Filter by plan', 'Start date', 'End date'],
  sw: ['Send receipts', 'Auto-renew', 'Show inactive'],
};
const CAPS = { h: 25, tabs: 20, btn: 45, th: 40, inp: 30, lbl: 50, sw: 40, a: 30 };
const MASKED_VERB = /^(Select|Edit|View|Delete|Remove|Open) (?!all$|row$).{2,}$/i, MASKED_FOR = /\b(for|of) .{2,}$/i;
// maskLabel and the "@ or 3+ digits" drop apply to button labels only; the other fields pass text through safe() (emails and phone numbers)
for (const [f, arr] of Object.entries(VOCAB)) for (const l of arr) {
  assert(!/@|\d{3,}/.test(l), `vocabulary label would be dropped or masked: ${f}`);
  if (f === 'btn') assert(!MASKED_VERB.test(l) && !MASKED_FOR.test(l), 'vocabulary button label would be masked');
}

const SELECTORS = { h: ['h2'], tabs: ['[role=tab]'], btn: ['button', '[role=button]'], th: ['th'], lbl: ['label'], inp: ['input'], sw: ['input[type=checkbox]'], a: ['a[href]'], region: ['aside'], row: ['tbody tr'] };

function wordRe(w) { return new RegExp('(^|[^A-Za-z0-9])' + w.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + '(?![A-Za-z0-9])', 'i'); }

// ---- the generator --------------------------------------------------------------------------------------------------------
function generate(R) {
  const onPersonRoute = R.chance(0.6);
  const taken = new Set();
  const owner = person(R, taken), ga = person(R, taken), gb = person(R, taken), others = [person(R, taken), person(R, taken), person(R, taken)];
  const staff = person(R, taken);
  const pathIds = [];                                                        // record ids that the page's own path holds (P5)
  const idTail = () => '9f3c' + String(++idSeq).padStart(6 + R.int(5), '0');  // a record id's tail of 10 to 14 hex characters, so the id pattern's lower bound is exercised
  const sep = () => R.pick(['_', '-']);
  const els = [], contract = [], structural = [], hidden = [];
  const sideW = R.pick([255, 240, 281, 300]), haveNav = R.chance(0.7);
  const edge = haveNav ? sideW : 290;
  if (haveNav) {
    const nav = el({ tag: 'NAV', left: 0, width: sideW, sel: [] });
    els.push(nav, el({ tag: 'A', left: 10, width: 100, sel: ['a[href="/people"]', 'a[href]'], attrs: { href: '/people' }, text: 'People', parent: nav }));
  }
  // the left menu (P6): group buttons, ordinary links, the user menu (a person's name), person-shaped and contact-shaped links
  const side = { contract: [['sub', staff.full], ['word', staff.first], ['word', staff.last]], links: [], groups: [] };
  const menu = (text, open) => els.push(el({ tag: 'BUTTON', text, sel: ['button[aria-expanded]'], attrs: { 'aria-expanded': open ? 'true' : 'false' }, left: 12, width: 200 }));
  menu(staff.full, false);
  for (const g of ['Communicate', 'Plans', 'Payments', 'Reports']) if (R.chance(0.5)) { menu(g, R.chance(0.5)); side.groups.push(g); }
  for (const label of ['Dashboard', 'Calendar', 'Check-ins', 'Settings']) if (R.chance(0.6)) {
    const href = '/' + label.toLowerCase(); els.push(el({ tag: 'A', text: label, sel: ['a[href]'], attrs: { href }, left: 20, width: 150 })); side.links.push([label, href]);
  }
  for (const o of others) {
    if (R.chance(0.4)) { els.push(el({ tag: 'A', text: o.full, sel: ['a[href]'], attrs: { href: '/user/' + o.id }, left: 20, width: 150 })); side.contract.push(['sub', o.full]); }
    if (R.chance(0.3) && slug(o.full).length >= 8) { els.push(el({ tag: 'A', text: o.full, sel: ['a[href]'], attrs: { href: '/people/' + slug(o.full) }, left: 20, width: 150 })); side.contract.push(['sub', o.full], ['sub', slug(o.full)]); }
    if (R.chance(0.3)) { els.push(el({ tag: 'A', text: o.email, sel: ['a[href]'], attrs: { href: 'mailto:' + o.email }, left: 20, width: 150 })); side.contract.push(['sub', o.email]); }
    if (R.chance(0.3)) { els.push(el({ tag: 'A', text: R.pick(o.phones), sel: ['a[href]'], attrs: { href: 'tel:' + o.digits }, left: 20, width: 150 })); side.contract.push(['digits', o.digits]); }
    if (R.chance(0.3)) { els.push(el({ tag: 'A', text: 'Reach ' + o.email, sel: ['a[href]'], attrs: { href: '/reports/contacts' }, left: 20, width: 150 })); side.contract.push(['sub', o.email]); }
  }
  // the staff member's contact links (the text is a name) and a link whose path holds a record id: the sidebar must mask both
  const planId = 'plan' + sep() + idTail();
  els.push(el({ tag: 'A', text: staff.full, sel: ['a[href]'], attrs: { href: 'mailto:' + staff.email }, left: 20, width: 150 }));
  els.push(el({ tag: 'A', text: staff.full, sel: ['a[href]'], attrs: { href: 'tel:' + staff.digits }, left: 20, width: 150 }));
  els.push(el({ tag: 'A', text: 'Pinned plan', sel: ['a[href]'], attrs: { href: '/plans/' + planId }, left: 20, width: 150 }));
  side.contract.push(['sub', planId]); side.masked = ['LINK  <item>  ->  <contact>', 'LINK  <item>  ->  /plans/<id>'];
  const at = () => edge + R.int(400);                                        // a position inside the content
  const add = (field, p) => els.push(el(Object.assign({ sel: SELECTORS[field], left: at() }, p)));

  // structural labels: visible ones must survive, those left of the edge must not appear
  for (const [field, vocab] of Object.entries(VOCAB)) {
    const n = R.int(Math.min(7, vocab.length)) + 1;
    const used = new Set();
    for (let i = 0; i < n; i++) {
      const label = R.pick(vocab); if (used.has(label)) continue; used.add(label);
      const p = field === 'inp' ? { attrs: { 'aria-label': label }, type: 'text' } : field === 'sw' ? { attrs: { 'aria-label': label }, type: 'checkbox' } : { text: label };
      if (field === 'inp') p.sel = ['input'];
      if (field === 'sw') p.sel = ['input', 'input[type=checkbox]'];
      const left = R.chance(0.1) ? edge : at();                              // exactly at the edge counts as inside
      add(field, Object.assign(p, { left }));
      structural.push({ field, label });
    }
    if (R.chance(0.4)) {
      const label = 'Nav item ' + R.int(1000), p = field === 'inp' || field === 'sw' ? { attrs: { 'aria-label': label }, type: field === 'sw' ? 'checkbox' : 'text' } : { text: label };
      add(field, Object.assign(p, { left: edge - 1 - R.int(60) })); hidden.push({ field, label });
      if (field === 'inp') els[els.length - 1]._sel = ['input']; if (field === 'sw') els[els.length - 1]._sel = ['input', 'input[type=checkbox]'];
    }
  }
  const rowCount = R.int(6); for (let i = 0; i < rowCount; i++) add('row', {});
  const iconCount = R.int(4); for (let i = 0; i < iconCount; i++) add('btn', { text: '' });
  // icon-only buttons that ARE named (by aria-label or title): listed by that name and not counted as unnamed icons
  for (const label of ['Close', 'Help', 'Menu']) if (R.chance(0.3)) {
    add('btn', R.chance(0.5) ? { text: '', title: label } : { text: '', attrs: { 'aria-label': label } });
    structural.push({ field: 'btn', label });
  }
  if (R.chance(0.2)) add('btn', { text: 'Collapse sidebar' });                // top-bar chrome
  if (R.chance(0.2)) add('btn', { text: 'Search' });

  // values that must never come back, on any page: other people in masked shapes, emails and phones
  for (const o of others) {
    if (R.chance(0.7)) { add('sw', { attrs: { 'aria-label': 'Select ' + o.full }, type: 'checkbox', sel: ['input', 'input[type=checkbox]'] }); contract.push(['sub', o.full]); }
    if (R.chance(0.6)) { add('btn', { text: R.pick(['Edit', 'View', 'Delete', 'Remove', 'Open']) + ' ' + o.full }); contract.push(['sub', o.full]); }
    if (R.chance(0.5)) { add('btn', { text: 'Add sub-account for ' + o.full }); contract.push(['sub', o.full]); }
    if (R.chance(0.6)) { add('a', { attrs: { href: '/user/' + o.id }, text: o.full }); contract.push(['sub', o.full]); }
    if (R.chance(0.5)) { add('a', { attrs: { href: 'mailto:' + o.email }, text: o.email }); contract.push(['sub', o.email]); }
    if (R.chance(0.5)) { add('a', { attrs: { href: 'tel:' + o.digits }, text: R.pick(o.phones) }); contract.push(['digits', o.digits]); }
    if (R.chance(0.5)) { add('h', { text: 'Contact: ' + o.email }); contract.push(['sub', o.email]); }
    if (R.chance(0.5)) { add('lbl', { text: 'Phone ' + R.pick(o.phones) }); contract.push(['digits', o.digits]); }
    if (R.chance(0.4)) { add('btn', { text: o.email }); contract.push(['sub', o.email]); }
    if (R.chance(0.3)) { add('region', { text: 'Reach ' + o.email + ' or ' + R.pick(o.phones) }); contract.push(['sub', o.email], ['digits', o.digits]); }
    // link shapes off the person routes: an invoice id, a person path that is a name slug, a person id that is not hex, contact links whose text is a name, a query that holds an address
    if (R.chance(0.4)) { const inv = 'inv' + sep() + idTail(); add('a', { attrs: { href: '/payments/invoices/' + inv }, text: o.full }); contract.push(['sub', o.full], ['sub', inv]); }
    if (R.chance(0.3) && slug(o.full).length >= 8) { add('a', { attrs: { href: '/people/' + slug(o.full) }, text: o.full }); contract.push(['sub', o.full], ['sub', slug(o.full)]); }
    if (R.chance(0.3)) { const ext = 'cus_Nffr' + String(++idSeq) + 'Hib'; add('a', { attrs: { href: 'https://dashboard.example.invalid/customers/' + ext }, text: 'Open in the payment dashboard' }); contract.push(['sub', ext]); }   // an id in the path of a link to another site (not hex)
    if (R.chance(0.3)) { add('a', { attrs: { href: 'sms:' + o.digits }, text: o.full }); contract.push(['sub', o.full]); }
    // an input label or a toggle label that carries a number or an address: only the row mask's text part protects it
    if (R.chance(0.3)) { add('inp', { attrs: { 'aria-label': 'Call ' + R.pick(o.phones) }, type: 'text', sel: ['input'] }); contract.push(['digits', o.digits]); }
    if (R.chance(0.3)) { add('sw', { attrs: { 'aria-label': 'Email ' + o.email }, type: 'checkbox', sel: ['input', 'input[type=checkbox]'] }); contract.push(['sub', o.email]); }
    if (R.chance(0.2)) { const lead = 'lead-' + o.last.toLowerCase().replace(/[^a-z]/g, '') + 'x'; add('a', { attrs: { href: '/user/' + lead }, text: o.full }); contract.push(['sub', o.full], ['sub', lead]); }
    if (R.chance(0.3)) { add('a', { attrs: { href: 'mailto:' + o.email }, text: o.full }); contract.push(['sub', o.full]); }
    if (R.chance(0.3)) { add('a', { attrs: { href: 'tel:' + o.digits }, text: o.full }); contract.push(['sub', o.full]); }
    if (R.chance(0.3)) { add('a', { attrs: { href: '/payments/payments?email=' + o.email + '&q=' + o.last }, text: 'Filter' }); contract.push(['sub', o.email]); }
    // text that carries an address or a number in fields that only the text mask (safe) protects: a column header, a tab, the text of a plain link
    if (R.chance(0.3)) { add('th', { text: 'Contact ' + o.email }); contract.push(['sub', o.email]); }
    if (R.chance(0.3)) { add('tabs', { text: R.pick(o.phones) }); contract.push(['digits', o.digits]); }
    if (R.chance(0.3)) { add('a', { attrs: { href: '/reports/contacts' }, text: o.email }); contract.push(['sub', o.email]); }
  }

  let title = 'People | PushPress', pathname = R.pick(['/people/members', '/schedule/class-types', '/payments', '/main', '/plans/list']);
  let gapName = null, gapExposable = false, gapPhone = null;                    // exposable: no word of it is also a scrubbed word
  const secretWords = [];
  if (!onPersonRoute && R.chance(0.25)) { const pid = idTail(); pathname = R.pick(['/plans/plan' + sep() + pid, '/payments/invoices/inv' + sep() + pid]); pathIds.push(pid); }
  if (onPersonRoute) {
    const noInputs = R.chance(0.3);
    pathname = R.pick(['/user/' + owner.id, '/people/' + cat('lead', '_', owner.id.slice(4)), '/user/' + owner.id, '/people/' + slug(owner.full)]);
    if (pathname === '/people/' + slug(owner.full)) { if (slug(owner.full).length >= 8) pathIds.push(slug(owner.full)); else pathname = '/user/' + owner.id; }   // a name slug is only masked from 8 characters on, as ids are never shorter
    const suffix = R.pick([' | PushPress', ' - PushPress', '']);
    title = noInputs || R.chance(0.7) ? owner.full + suffix : owner.last + ', ' + owner.first;
    if (noInputs) {
      // a billing tab: the name is in the page title and the heading, and no input holds it, so only the title can scrub it
      add('h', { text: owner.full }); add('btn', { text: 'Edit ' + owner.full }); add('region', { text: owner.full });
      contract.push(['sub', owner.full]);
    } else {
      let sharedLast = null;
      if (R.chance(0.3)) {                                                     // the guardian shares the owner's first name: the longer name has to be scrubbed first
        const lasts = LAST.filter(l => l.length >= 6 && l !== owner.last && !gb.full.split(' ').includes(l));
        ga.first = owner.first; ga.last = R.pick(lasts); ga.full = ga.first + ' ' + ga.last; sharedLast = ga.last;
      }
      const field = (value, label) => els.push(el({ tag: 'INPUT', sel: ['input', 'input[type=text]'], type: 'text', value, attrs: { 'aria-label': label }, left: at() }));
      field(owner.first, 'First name'); field(owner.last, 'Last name'); field(owner.email, 'Email'); field(R.pick(owner.phones), 'Phone'); field(owner.dob, 'Date of birth');
      if (R.chance(0.5)) els.push(el({ tag: 'TEXTAREA', sel: ['textarea'], type: 'textarea', value: ga.full, attrs: { 'aria-label': 'Guardian name' }, left: at() })); else field(ga.full, 'Guardian name');
      field(ga.email, 'Guardian email');
      add('h', { text: owner.full }); add('h', { text: ga.full });
      if (R.chance(0.4)) add('h', { text: 'Family (' + ga.full + ')' });             // the scrub's left boundary is any non-alphanumeric, not only a space
      if (R.chance(0.4)) add('h', { text: 'Guardian:' + owner.first });
      if (R.chance(0.4)) add('h', { text: owner.full.toUpperCase() });          // innerText follows CSS text-transform: the scrub has to be case-insensitive
      add('btn', { text: 'Guardian', attrs: { role: 'combobox', 'aria-label': 'Relationship' }, sel: ['button', '[role=button]'] }); add('btn', { text: 'Wombat', attrs: { role: 'combobox' }, sel: ['button', '[role=button]'] });
      contract.push(['sub', 'Wombat']);
      // a second person who appears as plain text only: the recorded gap
      add('h', { text: gb.full }); add('btn', { text: 'Message ' + gb.first }); gapName = gb.full;
      add('a', { attrs: { href: 'mailto:' + gb.email }, text: gb.email }); contract.push(['sub', gb.email], ['digits', gb.digits]);
      add('lbl', { text: 'Phone ' + R.pick(gb.phones) });
      add('lbl', { text: 'Alt phone ' + gb.gapText }); gapPhone = gb.gapDigits;
      add('region', { text: owner.full + ' ' + gb.full });                    // must be skipped on a person route
      for (const w of [owner.first, owner.last]) secretWords.push(w);
      gapExposable = ![owner.first, owner.last, ...ga.full.split(' ')].some(w => wordRe(w).test(gb.full));
      contract.push(['word', owner.first], ['word', owner.last], ['sub', owner.full], ['sub', owner.email], ['digits', owner.digits], ['sub', owner.dob], ['sub', ga.full], ['sub', ga.email], ['digits', ga.digits]);
      if (sharedLast) contract.push(['word', sharedLast]);
      secretWords.push(...ga.full.split(' '));
    }
  }
  const loc = { origin: 'https://tenant.example.invalid', pathname, search: R.chance(0.4) ? '?' + R.pick(['page', 'status', 'q']) + '=' + R.pick(['2', 'active', QUERY_VALUE]) : '', hash: R.chance(0.3) ? '#' + R.pick(['billing', 'notes']) : '' };
  // overflow: on some pages a field gets more distinct visible entries than its cap (added last, so every earlier expectation is unaffected)
  const overflow = [];
  if (R.chance(0.04)) for (const f of ['h', 'btn']) {
    const extra = CAPS[f] + 1 + R.int(5);
    for (let i = 0; i < extra; i++) add(f, { text: `Overflow ${f} ${i + 1}` });
    overflow.push(f);
  }
  return { els, loc, title, contract, structural, hidden, onPersonRoute, gapName, gapExposable, edge, owner, others, ga, secretWords, rowCount, iconCount, side, overflow, pathIds, gapPhone };
}

// ---- running and checking -------------------------------------------------------------------------------------------------
// `p` (the path field) is not scrubbed by design, only masked, so it is checked on its own (P5) and left out of the text checks
function strings(out, dumpText) {
  const leaves = [];
  for (const [k, v] of Object.entries(out)) {
    if (k === 'p') continue;
    if (typeof v === 'string') leaves.push([k, v]); else if (Array.isArray(v)) for (const x of v) leaves.push([k, String(x)]);
  }
  let dump = dumpText;
  try { const obj = JSON.parse(dumpText.split('\n')[1]); delete obj.p; dump = JSON.stringify(obj); } catch (e) { /* keep the whole text */ }
  return { leaves, dump };
}
const QUERY_VALUE = 'x7Kq9ZPaLmN2vBt4Rw8Yc1Dg5Hs3Jf6';
const DEBUG = process.env.PP_PROPERTY_DEBUG === '1';                          // prints the (synthetic) value and the fields it reached
function found(tokens, s) {
  const hits = new Set();
  for (const [mode, value] of tokens) {
    // a phone number is its ten digits with the separators the page may use between the groups: "(nnn) nnn-nnnn", "nnn.nnn.nnnn", "+1 nnn nnn nnnn", "nnnnnnnnnn"
    const digitRe = new RegExp(String(value).slice(0, 3) + '\\)?[\\s.-]?' + String(value).slice(3, 6) + '[\\s.-]?' + String(value).slice(6));
    const has = mode === 'digits' ? t => digitRe.test(t) : mode === 'sub' ? t => t.toLowerCase().includes(value.toLowerCase()) : t => wordRe(value).test(t);
    const where = [...new Set(s.leaves.filter(([, t]) => has(t)).map(([f]) => f))];
    if (has(s.dump)) where.push('dump');
    if (where.length) hits.add(mode + ':' + (mode === 'digits' ? 'phone' : mode === 'sub' && value.includes('@') ? 'email' : 'name') + (DEBUG ? `=${value}@${where.join('+')}` : ''));
  }
  return [...hits];
}

const failures = [];
const kinds = {};                                                            // violations by property, over ALL pages: the controls read their tags from this
const record = (i, kind, detail) => { if (failures.length < 10) failures.push({ page: i, kind, detail }); failures.count = (failures.count || 0) + 1; kinds[kind] = (kinds[kind] || 0) + 1; };

(async () => {
const R = rng(SEED);
let stats = { pages: 0, personPages: 0, tokens: 0, structural: 0, hidden: 0, gapShown: 0, gapExposed: 0, phoneGapShown: 0, phoneGapExposed: 0, sidebarTokens: 0, sidebarLinks: 0, overflow: 0 };
for (let i = 0; i < PAGES; i++) {
  const g = generate(R);
  const { pp, dumpNodes } = install(g.els, g.loc, g.title);
  const out = plain(pp.extract());
  pp.store('p'); pp.dump();
  const s = strings(out, dumpNodes[0].textContent);
  stats.pages++; if (g.onPersonRoute) stats.personPages++;
  // P1
  stats.tokens += g.contract.length;
  const leaked = found(g.contract, s);
  if (leaked.length) record(i, 'P1 contract', leaked.join(','));
  // P2 / P3 / P4
  const secret = g.onPersonRoute ? g.secretWords.concat([g.owner.full, g.ga.full]) : [];
  for (const { field, label } of g.structural) {
    if (secret.some(w => wordRe(w).test(label))) continue;                    // legitimately scrubbed: counted by the audit, not a failure
    stats.structural++;
    if (!(out[field] || []).includes(label)) record(i, 'P2 structure', `${field} lost a visible label`);
  }
  for (const { field, label } of g.hidden) { stats.hidden++; if ((out[field] || []).includes(label)) record(i, 'P3 edge', `${field} kept a label left of the edge`); }
  for (const [f, cap] of Object.entries(CAPS)) if ((out[f] || []).length > cap) record(i, 'P4 caps', `${f} exceeds ${cap}`);
  // a field with more distinct entries than its cap holds exactly the cap; on a person route the scrub can merge two entries into one <value> after the cap
  // is applied, so there only "not more than the cap" is required (which is what removing a cap breaks)
  for (const f of g.overflow) {
    stats.overflow++; const n = (out[f] || []).length;
    if (g.onPersonRoute ? n > CAPS[f] : n !== CAPS[f]) record(i, 'P4 caps', `${f} holds ${n}, cap ${CAPS[f]}${g.onPersonRoute ? '' : ' (exactly the cap expected)'}`);
  }
  if ((out.rows || 0) !== g.rowCount) record(i, 'P4 rows', `rows ${out.rows || 0} vs ${g.rowCount}`);
  if ((out.icons || 0) !== g.iconCount) record(i, 'P4 icons', `icons ${out.icons || 0} vs ${g.iconCount}`);
  if (g.onPersonRoute && 'region' in out) record(i, 'P1 region', 'region text recorded on a person route');
  // P5: the path field holds no record id and no query value
  if ([g.owner.id.slice(4), ...g.others.map(o => o.id.slice(4)), ...g.pathIds].some(id => (out.p || '').includes(id))) record(i, 'P5 path', 'p holds a record id');
  if ((out.p || '').includes(QUERY_VALUE)) record(i, 'P5 path', 'p holds a query value');
  // the recorded gap: deterministic wherever no word of the name is also scrubbed
  if (g.gapName && g.gapExposable) { stats.gapShown++; if (found([['sub', g.gapName]], s).length) stats.gapExposed++; }
  if (g.gapPhone) { stats.phoneGapShown++; if (found([['digits', g.gapPhone]], s).length) stats.phoneGapExposed++; }   // a phone typed as "(nnn)nnn-nnnn": recorded gap
  // P6: the sidebar reader parks its lines, prints each group and ordinary link, and prints no person (the user menu is skipped)
  const ret = await pp.sidebar();
  const parked = dumpNodes[0] ? dumpNodes[0].textContent : '';
  const text = Array.isArray(ret) ? ret.join('\n') : parked;
  stats.sidebarTokens += g.side.contract.length;
  if (!parked.startsWith('### sidebar')) record(i, 'P6 sidebar', 'sidebar() did not park its lines');
  const sideHits = found(g.side.contract, { leaves: [['sidebar', parked.split('\n').slice(1).join('\n')]], dump: '' });
  if (sideHits.length) record(i, 'P6 sidebar', 'a person reached the sidebar lines: ' + sideHits.join(','));
  for (const grp of g.side.groups) if (!text.includes('GROUP ' + grp) || !parked.includes('GROUP ' + grp)) record(i, 'P6 sidebar', 'a group button is missing from the lines');
  for (const line of g.side.masked) if (!parked.includes(line)) record(i, 'P6 sidebar', 'a contact or id link was not masked to its <item> line');
  for (const [label, href] of g.side.links) { stats.sidebarLinks++; if (!parked.includes(`LINK  ${label}  ->  ${href}`)) record(i, 'P6 sidebar', 'an ordinary link is missing from the lines'); }
}

// ---- over-masking audit: which words of the references' own vocabulary does a common name mask? ------------------------------
function referenceLabels() {
  const dir = path.join(ROOT, 'skills', 'pushpress'); const files = [path.join(dir, 'SKILL.md'), ...fs.readdirSync(path.join(dir, 'references')).map(f => path.join(dir, 'references', f))];
  const seen = new Set();
  for (const f of files) for (const m of fs.readFileSync(f, 'utf8').matchAll(/`([A-Za-z+][A-Za-z0-9 +'’-]{2,38})`/g)) {
    const t = m[1].trim();
    if (/^[A-Z+]/.test(t) && !/[_/.:()=<>]/.test(t) && /[a-z]/.test(t) && !/^(true|false|null)$/i.test(t)) seen.add(t);
  }
  return [...seen];
}
const NAME_WORDS = ['Mark', 'Will', 'Grace', 'Rose', 'Hope', 'Pat', 'Dawn', 'Sue', 'Amber', 'Hunter', 'Cash', 'Bill', 'Jack', 'Max', 'Page', 'Stone', 'Fields', 'Bell', 'Young', 'Hill', 'King', 'Cook', 'Love', 'Sharp', 'Mann', 'Wood', 'Rice', 'Long', 'Gold', 'Brown', 'White', 'Black', 'Green', 'Lane', 'Park', 'Church', 'Bank', 'Cross', 'Ford', 'Day', 'Frost', 'Rain', 'Summer', 'Winter', 'Joy', 'Faith', 'Chase', 'Dash', 'Drew', 'Grant', 'Reed', 'Roy', 'Sky', 'Star', 'Wolf', 'Li', 'Xu', 'Ng', 'Yu', 'Bo', 'Ty', 'Jo', 'Al', 'Ed', 'Lee'];
const labels = referenceLabels();
const audit = NAME_WORDS.map(w => ({ w, n: labels.filter(l => wordRe(w).test(l)).length })).sort((a, b) => b.n - a.n || a.w.localeCompare(b.w));
const masked = audit.filter(a => a.n > 0);

// ---- report ---------------------------------------------------------------------------------------------------------------
console.log(`pushpress extractor property test: ${stats.pages} pages (${stats.personPages} on person routes), seed ${SEED}`);
console.log(`  checked ${stats.tokens} planted values (P1), ${stats.structural} visible labels (P2), ${stats.hidden} labels left of the edge (P3), caps (${stats.overflow} overflow fields), rows and icons and the path field (P4, P5)`);
console.log(`  sidebar reader (P6): ${stats.sidebarTokens} planted values and ${stats.sidebarLinks} ordinary links checked`);
console.log(`  known gap, second person shown as plain text: reached the output on ${stats.gapExposed} of ${stats.gapShown} person pages where no word of the name is also scrubbed`);
console.log(`  known gap, a phone number typed without a separator after the closing parenthesis: reached the output on ${stats.phoneGapExposed} of ${stats.phoneGapShown} pages that show one`);
console.log(`  over-masking audit: ${labels.length} labels quoted in the skill's references; of ${NAME_WORDS.length} words used as names, ${masked.length} would mask at least one`);
console.log('  worst: ' + masked.slice(0, 8).map(a => `${a.w}=${a.n}`).join(' ') + (masked.length > 8 ? ' ...' : ''));
let bad = 0;
if (failures.count) { bad++; console.log(`FAIL: ${failures.count} violations (${Object.entries(kinds).map(([k, n]) => k + ' ' + n).join(', ')}); first ${failures.length}:`); for (const f of failures) console.log('  page ' + f.page + ' ' + f.kind + ': ' + f.detail); }
// the recorded gaps are deterministic: reaching the output on every page that shows them. None (XPASS) or only some means the behaviour changed.
const gapVerdict = (shown, exposed, what) => {
  if (!shown || exposed === shown) return;
  bad++;
  console.log(exposed === 0 ? `XPASS: ${what} no longer reaches the output on any page: promote it to a property and update the journal`
    : `FAIL: ${what} is no longer deterministic (it reaches the output on some pages and not others): the behaviour changed`);
};
gapVerdict(stats.gapShown, stats.gapExposed, 'the second person shown as plain text');
gapVerdict(stats.phoneGapShown, stats.phoneGapExposed, 'the phone number typed without a separator after the closing parenthesis');
// counts of 100 thousand or more are written with commas, as strings, so the repository's long-number lint stays quiet about evidence files
const big = n => (n >= 100000 ? n.toLocaleString('en-US') : n);
if (JSON_OUT) fs.writeFileSync(JSON_OUT, JSON.stringify({
  seed: SEED, pages: stats.pages, person_route_pages: stats.personPages, planted_values_checked: big(stats.tokens), visible_labels_checked: big(stats.structural),
  labels_left_of_edge_checked: big(stats.hidden), sidebar_values_checked: big(stats.sidebarTokens), sidebar_links_checked: big(stats.sidebarLinks),
  known_gap: { exposable_person_pages: stats.gapShown, exposed: stats.gapExposed },
  known_gap_phone_shape: { pages_showing_one: stats.phoneGapShown, exposed: stats.phoneGapExposed },
  over_masking_audit: { labels_quoted_in_references: labels.length, name_words_tried: NAME_WORDS.length, words_masking_at_least_one_label: masked.map(a => ({ word: a.w, labels: a.n })) },
  violations: failures.count || 0, first_violations: failures,
}, null, 2) + '\n');
console.log(`pushpress-extractor-property.js: ${bad ? 'FAIL' : 'PASS'}`);
process.exit(bad ? 1 : 0);
})();
