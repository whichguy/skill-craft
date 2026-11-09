#!/usr/bin/env node
// Register of inputs that skills/pushpress/scripts/pp-extract.js does NOT protect today, run through the real extractor on a stub DOM.
// Each gap plants one synthetic value and asserts that it still reaches the output (XFAIL: a recorded, expected failure). When the extractor
// is fixed the gap stops leaking (XPASS), which fails the run so the entry is promoted to a contract and docs/pushpress-journal.md updated.
// Two kinds of control keep the checker honest. Masked shapes (the extractor handles them today) must not leak; positive controls (a plain word
// and a short number the extractor passes through) must be found, so a leak check that reads nothing fails here instead of passing quietly.
// Every name, number and address is made up and assembled at run time; the report prints ids, fields and counts, never a planted value.
//
//   node test/pushpress-extractor-known-gaps.js [--flip-check] [--json <file>]     PP_EXTRACT=<file> tests another copy of the extractor
//
// Found by a black-box audit (a fifth independent review round) and by the phone-shape probe; docs/pushpress-journal.md (Round 9) lists
// them as H3 and H16 to H21 and proposes the fixes as P12 to P16. Not wired into any automatic run yet (P7).
'use strict';

const fs = require('fs');
const path = require('path');
const vm = require('vm');

const SRC = fs.readFileSync(process.env.PP_EXTRACT || path.join(__dirname, '..', 'skills', 'pushpress', 'scripts', 'pp-extract.js'), 'utf8');
const JSON_OUT = process.argv.includes('--json') ? process.argv[process.argv.indexOf('--json') + 1] : '';

// ---- the stub DOM (as in test/pushpress-extractor-property.js) ----------------------------------------------------------------
function el(p) {
  const e = Object.assign({ tag: 'DIV', text: '', sel: [], attrs: {}, left: 300, top: 100, width: 100, height: 20, title: '', placeholder: '', name: '', type: '', value: '', parent: null }, p);
  return { tagName: e.tag, innerText: e.text, title: e.title, placeholder: e.placeholder, name: e.name, type: e.type, value: e.value, parentElement: e.parent, _sel: e.sel,
    getAttribute: k => (k in e.attrs ? e.attrs[k] : null), getBoundingClientRect: () => ({ left: e.left, top: e.top, width: e.width, height: e.height, right: e.left + e.width }),
    closest: () => null, click() {} };
}
function extract(elements, pathname, title, src) {
  const store = new Map(); const dump = [];
  const document = { title: title || '', body: { innerText: 'x', appendChild() {} },
    querySelectorAll(s) { const w = s.split(',').map(x => x.trim()); return elements.filter(e => e._sel.some(x => w.includes(x))); },
    getElementById: () => dump[0] || null, createElement() { const n = { id: '', textContent: '', remove() {} }; dump[0] = n; return n; } };
  const sessionStorage = { getItem: k => (store.has(k) ? store.get(k) : null), setItem: (k, v) => store.set(k, String(v)), removeItem: k => store.delete(k) };
  const window = {};
  vm.runInNewContext(src || SRC, { window, document, sessionStorage, URL, URLSearchParams, console, setTimeout: f => setTimeout(f, 0),
    location: { origin: 'https://tenant.example.invalid', pathname, search: '', hash: '' } });
  return JSON.parse(JSON.stringify(window.__pp.extract()));
}
const SEL = { h: ['h2'], tabs: ['[role=tab]'], btn: ['button', '[role=button]'], th: ['th'], lbl: ['label'], a: ['a[href]'], region: ['aside'] };
const put = (field, text, extra) => el(Object.assign({ sel: SEL[field], text }, extra));
const link = (text, href, extra) => el(Object.assign({ tag: 'A', sel: ['a[href]'], text, attrs: { href } }, extra));
const input = (value, label) => el({ tag: 'INPUT', sel: ['input', 'input[type=text]'], type: 'text', value, attrs: { 'aria-label': label || 'Field' } });

// ---- planted values, assembled so no file holds a complete number or address -----------------------------------------------------
const cat = (...p) => p.join('');
const NAME = { first: 'Zephyra', last: 'Quillfeather' };
const CYR = { first: cat('Зеф', 'ира'), last: cat('Квил', 'фезер') };              // the same made-up name in Cyrillic letters
const EMAIL = cat('jane.fixture', '@', 'example', '.invalid');
const N = { a: '555', b: '010', c: '0123' };                                          // the fictional 555-01xx range
const UID = cat('usr', '_', '9f3c', '00001234');
const LIST = '/people/members', PERSON = '/user/' + UID;
const digitsOf = s => s.normalize('NFKC').replace(/\D/g, '');         // NFKC folds full-width digits to ASCII, so they count as digits
const fullWidth = s => s.replace(/\d/g, c => String.fromCharCode(c.charCodeAt(0) + 0xFEE0));   // built at run time: no full-width number sits in this file

// ---- the register ----------------------------------------------------------------------------------------------------------------
// planted: strings looked for in every returned string (case-insensitive); digits: a digit run looked for after stripping non-digits.
const GAPS = [
  // a person's name or contact detail
  { id: 'non-latin-name', sev: 'material', why: 'the scrub keeps only values that contain a Latin letter (A-Z)', path: PERSON, title: CYR.first + ' ' + CYR.last,
    els: [input(CYR.first, 'First name'), input(CYR.last, 'Last name'), put('h', CYR.first + ' ' + CYR.last), put('btn', 'Message ' + CYR.first)], planted: [CYR.last, CYR.first] },
  { id: 'letterless-field-values', sev: 'material', why: 'a field value with no letter (a date, a short number, a postal code) is not a secret', path: PERSON, title: NAME.first + ' ' + NAME.last,
    els: [input('04/10/2012', 'Date of birth'), input(cat('010', '-', '0123'), 'Phone'), input('12345', 'ZIP'), put('lbl', 'Born 04/10/2012'), put('lbl', cat('Phone 010', '-', '0123')), put('h', 'ZIP 12345')],
    planted: ['04/10/2012', cat('010', '-', '0123'), '12345'] },
  { id: 'owner-first-name-alone-with-no-fields', sev: 'material', why: 'with no text fields only the whole page title is a secret, so a first name on its own is not scrubbed', path: PERSON, title: NAME.first + ' ' + NAME.last + ' | PushPress',
    els: [put('h', NAME.first + ' ' + NAME.last), put('btn', 'Charge ' + NAME.first)], planted: [NAME.first], onlyIn: 'btn' },
  { id: 'title-with-an-em-dash-separator', sev: 'material', why: 'the title is split only on a pipe, an en dash or a hyphen with a space each side, so with an em dash the whole title is the secret and it never equals the heading', path: PERSON, title: NAME.first + ' ' + NAME.last + ' — PushPress',
    els: [put('h', NAME.first + ' ' + NAME.last)], planted: [NAME.last] },
  { id: 'title-with-the-name-second', sev: 'material', why: 'only the part before the first separator is used, so with "Product | Name" the secret is the product name and the person scrubs nothing', path: PERSON, title: 'PushPress | ' + NAME.first + ' ' + NAME.last,
    els: [put('h', NAME.first + ' ' + NAME.last)], planted: [NAME.last] },
  { id: 'title-written-last-comma-first', sev: 'material', why: 'a comma is not a separator and "Last, First" never equals the heading "First Last"', path: PERSON, title: NAME.last + ', ' + NAME.first,
    els: [put('h', NAME.first + ' ' + NAME.last)], planted: [NAME.last] },
  { id: 'second-person-plain-text', sev: 'material', why: 'recorded as H3: a second person shown only as text on a person page is not a secret', path: PERSON, title: NAME.first + ' ' + NAME.last,
    els: [input(NAME.first, 'First name'), input(NAME.last, 'Last name'), put('h', 'Guardian Rosalind Tuckerbottom')], planted: ['Tuckerbottom'] },
  // phone numbers (H16 and beyond), each in a label off a person route
  ...[
    ['phone-no-space-after-parenthesis', cat('(', N.a, ')', N.b, '-', N.c)], ['phone-seven-digits-with-space', cat(N.a, ' ', N.b, N.c)], ['phone-slashes', [N.a, N.b, N.c].join('/')],
    ['phone-international-spacing', cat('+44 20 ', '7946 ', '0958')], ['phone-glued-extension', cat(N.a, '-', N.b, '-', N.c, 'x45')], ['phone-glued-ext-word', cat(N.a, '-', N.b, '-', N.c, 'ext45')],
    ['phone-seven-digit-local', cat(N.b, '-', N.c)], ['phone-en-dash', [N.a, N.b, N.c].join('–')], ['phone-spaces-around-dash', cat('(', N.a, ') ', N.b, ' - ', N.c)],
    ['phone-underscores', [N.a, N.b, N.c].join('_')], ['phone-uk-national', cat('07700 ', '900123')], ['phone-french', cat('06 39 ', '98 12 34')], ['phone-full-width-digits', fullWidth(cat(N.a, '-', N.b, '-', N.c))],
  ].map(([id, num]) => ({ id, sev: 'material', why: 'the text mask does not match this way of writing a number', path: LIST, els: [put('lbl', 'Phone ' + num)], digits: digitsOf(num).slice(-7) })),
  // links and paths
  ...[cat('whatsapp://send?phone=1', N.a, N.b, N.c), cat('callto:', N.a, N.b, N.c), cat('facetime:', N.a, N.b, N.c), 'skype:jane.fixture?call', cat('https://wa.me/1', N.a, N.b, N.c)].map(h => (
    { id: 'contact-link-' + h.split(/[:/]/)[0] + (h.includes('wa.me') ? '-wa-me' : ''), sev: 'material', why: 'only mailto, tel and sms links are treated as contact links, so the text (a name) is kept', path: LIST, els: [link(NAME.first + ' ' + NAME.last, h)], planted: [NAME.last] })),
  { id: 'email-in-a-same-origin-path', sev: 'material', why: 'an email in a path segment is not masked (the text mask runs on text, not on paths)', path: LIST, els: [link('History', cat('/members/by-email/', EMAIL))], planted: ['jane.fixture'] },
  { id: 'person-link-with-numeric-id', sev: 'material', why: 'the person-route test needs 8 or more characters after /user/ or /people/', path: LIST, els: [link(NAME.first + ' ' + NAME.last, '/user/48213')], planted: [NAME.last] },
  { id: 'person-id-in-a-query', sev: 'material', why: 'only the path is tested for a person id', path: LIST, els: [link(NAME.first + ' ' + NAME.last, '/checkins?user=' + UID)], planted: [NAME.last] },
  { id: 'person-link-that-is-a-role-button', sev: 'material', why: 'the link is masked in the link list but its text is also a button label, which the person-link mask does not see', path: LIST,
    els: [el({ tag: 'A', sel: ['a[href]', '[role=button]'], text: NAME.first + ' ' + NAME.last, attrs: { href: '/user/' + UID, role: 'button' } })], planted: [NAME.last], onlyIn: 'btn' },
  // ids and address-like strings (lower severity)
  { id: 'uuid-in-text', sev: 'low', why: 'ids that are not hex-with-prefix are not masked in text', path: LIST, els: [put('lbl', 'Customer 3f2b8c1e-4a5b-4c6d-8e9f-0a1b2c3d4e5f')], planted: ['3f2b8c1e-4a5b-4c6d-8e9f-0a1b2c3d4e5f'] },
  { id: 'payment-processor-id-in-text', sev: 'low', why: 'a processor customer id in text is not masked', path: LIST, els: [put('lbl', 'Processor ' + cat('cus', '_', 'NffrFeUfNV2Hib'))], planted: [cat('cus', '_', 'NffrFeUfNV2Hib')] },
  { id: 'invoice-number-in-text', sev: 'low', why: 'invoice and order numbers in text are not masked', path: LIST, els: [put('lbl', 'Invoice INV-004213 Order #100245')], planted: ['INV-004213', '#100245'] },
  { id: 'card-last-four-in-text', sev: 'low', why: 'the last four digits of a card are not masked', path: LIST, els: [put('lbl', 'Card •••• 4242')], planted: ['4242'] },
  { id: 'street-address-in-text', sev: 'low', why: 'a street address is not masked', path: LIST, els: [put('lbl', '221 Fixture Street, 12345')], planted: ['221 Fixture Street'] },
];

// ---- controls: shapes the extractor masks today; a leak here means the extractor regressed or this harness stopped reading ----------
const CONTROLS = [
  // positive controls: a plain word and a short number the extractor passes through, so this checker is shown to read the fields it claims to read
  { id: 'checker-finds-a-word-in-a-heading', reads: true, path: LIST, els: [put('h', 'Sentinelword')], planted: ['Sentinelword'] },
  { id: 'checker-finds-a-short-number-in-a-label', reads: true, path: LIST, els: [put('lbl', 'Seats 42')], digits: '42' },
  { id: 'phone-parenthesis-and-space', path: LIST, els: [put('lbl', cat('Phone (', N.a, ') ', N.b, '-', N.c))], digits: N.b + N.c },
  { id: 'phone-international-plus-one', path: LIST, els: [put('lbl', cat('Phone +1 ', N.a, ' ', N.b, ' ', N.c))], digits: N.b + N.c },
  { id: 'email-in-text', path: LIST, els: [put('lbl', 'Email ' + EMAIL)], planted: ['jane.fixture'] },
  { id: 'button-edit-name', path: LIST, els: [put('btn', 'Edit ' + NAME.first + ' ' + NAME.last)], planted: [NAME.last] },
  { id: 'person-link-hex-id', path: LIST, els: [link(NAME.first + ' ' + NAME.last, '/user/' + UID)], planted: [NAME.last, UID] },
  { id: 'mailto-link-with-a-name', path: LIST, els: [link(NAME.first + ' ' + NAME.last, 'mailto:' + EMAIL)], planted: [NAME.last, 'jane.fixture'] },
  { id: 'title-pipe-separator-and-no-fields', path: PERSON, title: NAME.first + ' ' + NAME.last + ' | PushPress', els: [put('h', NAME.first + ' ' + NAME.last)], planted: [NAME.last, NAME.first] },
  { id: 'title-en-dash-separator-and-no-fields', path: PERSON, title: NAME.first + ' ' + NAME.last + ' – PushPress', els: [put('h', NAME.first + ' ' + NAME.last)], planted: [NAME.last, NAME.first] },
  { id: 'input-value-scrubbed-on-a-person-route', path: PERSON, title: NAME.first + ' ' + NAME.last, els: [input(NAME.first, 'First name'), input(NAME.last, 'Last name'), put('h', NAME.first + ' ' + NAME.last)], planted: [NAME.last, NAME.first] },
];

// ---- running ---------------------------------------------------------------------------------------------------------------------
const strings = v => (typeof v === 'string' ? [v] : Array.isArray(v) ? v.flatMap(strings) : v && typeof v === 'object' ? Object.values(v).flatMap(strings) : []);
function where(out, e) {
  const hits = {};
  for (const [field, v] of Object.entries(out)) {
    for (const s of strings(v)) {
      const low = s.toLowerCase();
      const found = (e.planted || []).some(p => low.includes(p.toLowerCase())) || (e.digits && digitsOf(s).includes(e.digits));
      if (found) hits[field] = (hits[field] || 0) + 1;
    }
  }
  return hits;
}
function run(src) {
  const rows = [];
  for (const e of [...GAPS.map(g => ({ ...g, kind: 'gap' })), ...CONTROLS.map(c => ({ ...c, kind: 'control' }))]) {
    let hits, error = '';
    try { hits = where(extract(e.els, e.path, e.title || '', src), e); } catch (err) { hits = {}; error = (err && err.name) || 'Error'; }
    const leaked = Object.keys(hits).length > 0 && (!e.onlyIn || e.onlyIn in hits);
    let status;
    if (error) status = 'ERROR';
    else if (e.kind === 'gap') status = leaked ? 'XFAIL' : 'XPASS';
    else if (e.reads) status = leaked ? 'PASS' : 'FAIL';           // a positive control passes only when the checker finds the planted value
    else status = leaked ? 'FAIL' : 'PASS';
    rows.push({ id: e.id, kind: e.kind, severity: e.sev || '', status, fields: Object.keys(hits), why: e.why || '', error });
  }
  return rows;
}
const isBad = r => r.status === 'ERROR' || r.status === 'XPASS' || r.status === 'FAIL';
const show = rows => { const t = {}; for (const r of rows) t[r.status] = (t[r.status] || 0) + 1; return Object.entries(t).map(([k, n]) => k + ' ' + n).join(', '); };

// ---- --flip-check: crude one-line fixes, applied to copies held in memory, must flip exactly the entries they target ---------------
// This is the control for the XPASS rule: it shows that a fix of each kind is noticed and that no masked-shape control breaks. The fixes are
// crude, so this proves the register notices a fix, not that the fix is safe (the other tests are not run on them). A fix whose original text is
// no longer in the extractor exactly once is skipped, which is what happens after the extractor has really been changed.
const ids = prefix => GAPS.filter(g => g.id.startsWith(prefix)).map(g => g.id);
const FIXES = [
  { name: 'phone pattern: any run of 7 or more digits with separators, an extension, full-width digits folded', flips: ids('phone-'),
    from: String.raw`const safe = t => clean(t).replace(/\S*@\S*/g, '<email>')`,
    to: String.raw`const safe = t => clean(t).normalize('NFKC').replace(/\S*@\S*/g, '<email>').replace(/\+?\d(?:[\s().\/_–-]*\d){6,}(?:\s?(?:x|ext\.?)\s?\d{1,5})?/g, '<phone>')` },
  { name: 'scrub: keep values with a letter in any script or 4 or more digits, with Unicode word boundaries', flips: ['non-latin-name', 'letterless-field-values'],
    from: String.raw`/[A-Za-z]/.test(v)`, to: String.raw`(/\p{L}/u.test(v) || /\d{4,}/.test(v))`,
    from2: String.raw`new RegExp('(^|[^A-Za-z0-9])' + esc(v) + '(?![A-Za-z0-9])', 'gi')`, to2: String.raw`new RegExp('(^|[^\\p{L}\\p{N}])' + esc(v) + '(?![\\p{L}\\p{N}])', 'giu')` },
  { name: 'contact links: whatsapp, callto, facetime, skype and wa.me count as contact links', flips: ids('contact-link-'),
    from: String.raw`const isContact = href => /^\s*(?:mailto|tel|sms):/i.test(href);`,
    to: String.raw`const isContact = href => /^\s*(?:mailto|tel|sms|whatsapp|callto|facetime|skype):|^\s*https?:\/\/(?:wa\.me|api\.whatsapp\.com)\//i.test(href);` },
  { name: 'title: an em dash, a middle dot and a colon also separate the name from the product', flips: ['title-with-an-em-dash-separator'],
    from: String.raw`.split(/\s[|–-]\s/)[0]`, to: String.raw`.split(/\s[|–—·:-]\s/)[0]` },
  { name: 'person link: any id after /user/ or /people/, not only 8 or more characters', flips: ['person-link-with-numeric-id'],
    from: '[^/?]{8,}/;\n  const onPerson', to: '[^/?]{1,}/;\n  const onPerson' },
];
function replaceOnce(s, a, b) { const i = s.indexOf(a); return i < 0 || s.indexOf(a, i + 1) >= 0 ? null : s.slice(0, i) + b + s.slice(i + a.length); }
function flipCheck() {
  const base = run(SRC), baseBad = base.filter(isBad);
  if (baseBad.length) { console.log('flip-check needs a clean baseline; not XFAIL or PASS: ' + baseBad.map(r => r.id).join(', ')); return { ok: false, results: [] }; }
  const results = [];
  for (const f of FIXES) {
    let patched = replaceOnce(SRC, f.from, f.to);
    if (patched && f.from2) patched = replaceOnce(patched, f.from2, f.to2);
    if (!patched) { results.push({ name: f.name, status: 'SKIP', note: 'the original text is not in the extractor exactly once' }); continue; }
    const rows = run(patched);
    const flipped = rows.filter(r => r.status === 'XPASS').map(r => r.id).sort();
    const broken = rows.filter(r => r.status === 'FAIL' || r.status === 'ERROR').map(r => r.id);
    const ok = JSON.stringify(flipped) === JSON.stringify([...f.flips].sort()) && broken.length === 0;
    results.push({ name: f.name, status: ok ? 'OK' : 'BAD', flipped: flipped.length, expected: f.flips.length, controls_broken: broken.length });
  }
  return { ok: results.every(r => r.status !== 'BAD'), results };
}

if (process.argv.includes('--flip-check')) {
  const { ok, results } = flipCheck();
  for (const r of results) console.log(`${r.status.padEnd(4)} flips ${r.flipped === undefined ? '-' : r.flipped + ' of ' + r.expected}  controls broken ${r.controls_broken === undefined ? '-' : r.controls_broken}  ${r.name}${r.note ? '  (' + r.note + ')' : ''}`);
  if (JSON_OUT) fs.writeFileSync(JSON_OUT, JSON.stringify({ recorded: '2026-11-09', mode: 'flip-check', results }, null, 2) + '\n');
  console.log(`pushpress-extractor-known-gaps.js --flip-check: ${ok ? 'PASS' : 'FAIL'}`);
  process.exit(ok ? 0 : 1);
}

const rows = run(SRC);
for (const r of rows) console.log(`${r.status.padEnd(5)} ${r.kind.padEnd(7)} ${r.id.padEnd(48)} ${r.fields.join(',')}${r.status === 'XPASS' ? '  (no longer leaks: promote it to a contract)' : ''}${r.error ? '  ' + r.error : ''}`);
console.log('tally: ' + show(rows));
if (JSON_OUT) {
  const tally = {}; for (const r of rows) tally[r.status] = (tally[r.status] || 0) + 1;
  fs.writeFileSync(JSON_OUT, JSON.stringify({ recorded: '2026-11-09', extractor: path.basename(process.env.PP_EXTRACT || 'pp-extract.js'), tally, entries: rows }, null, 2) + '\n');
}
const bad = rows.filter(isBad).length;
console.log(`pushpress-extractor-known-gaps.js: ${bad ? 'FAIL' : 'PASS'}`);
process.exit(bad ? 1 : 0);
