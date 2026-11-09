#!/usr/bin/env node
// Register of inputs that skills/pushpress/scripts/pp-extract.js does NOT protect today, run through the real extractor on a stub DOM.
// Each gap plants a made-up value or a few (the parts of a name, a name and the id a link prints, or two or three values of one kind) and
// asserts that they still reach the output (XFAIL: a recorded, expected failure). When the extractor is fixed the gap stops leaking (XPASS),
// which fails the run so the entry is promoted to a contract and docs/pushpress-journal.md updated. A fix that stops only some of an
// entry's values is PARTIAL, which also fails the run: split the entry.
// Controls keep the checker honest. Masked shapes (the extractor handles them today) must not leak. Positive controls (a plain word in a
// heading, a button and a link, a short number in a label, a short number written in full-width digits) must be found, so a leak check that
// reads nothing, or stops reading a field the gaps leak through, or stops folding full-width digits, fails a control instead of passing
// quietly or being read as an extractor fix; every field in which a gap leaks must have a positive control that is found in it (checked on
// every run). A malformed entry (an empty or too short value, one value inside another, a digits value that overlaps a planted value, digits
// that are not 2 or more ASCII digits, an unknown onlyIn field, an entry that plants nothing) is an ERROR.
// Two limits, stated so that nobody reads more into the checks than they do. The coverage rule is per field, not per kind of match (text or
// digits): a checker fault confined to one kind in one field is not caught. And a planted value must be a string the extractor does not
// print on its own (part of a mask token, a path or the entry's own text); problem() does not enforce that. A round-8 reviewer checked every
// planted value against the mask tokens, the paths and its own element text and found none that is.
// Phone numbers, email addresses and the prefixed ids are assembled at run time so that no file holds a complete one. The other planted
// values (names, a UUID, a date, a postal code, card digits, invoice and order numbers, short numeric ids, a street address) are made-up
// literals. The report prints ids, fields and counts, never a planted value.
//
//   node test/pushpress-extractor-known-gaps.js [--flip-check] [--json <file>]     PP_EXTRACT=<file> tests another copy of the extractor
//   require() of this file exposes the register and the stub DOM for probes and reviews and runs nothing.
//
// Found by a black-box audit (review round 5) and checked by independent reviewers in the rounds after it; docs/pushpress-journal.md (Round 9) lists them as
// H3 and H16 to H22 and proposes the fixes as P12 to P16. Not wired into any automatic run yet (P7).
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

// ---- planted values ----------------------------------------------------------------------------------------------------------------
const cat = (...p) => p.join('');
const NAME = { first: 'Zephyra', last: 'Quillfeather' };
const CYR = { first: cat('Зеф', 'ира'), last: cat('Квил', 'фезер') };              // the same made-up name in Cyrillic letters
const EMAIL = cat('jane.fixture', '@', 'example', '.invalid');
const N = { a: '555', b: '010', c: '0123' };                                          // made-up digit groups, not a dialable number
const UID = cat('usr', '_', '9f3c', '00001234');
const LIST = '/people/members', PERSON = '/user/' + UID;
const digitsOf = s => s.normalize('NFKC').replace(/\D/g, '');         // NFKC folds full-width digits to ASCII, so they count as digits
const fullWidth = s => s.replace(/\d/g, c => String.fromCharCode(c.charCodeAt(0) + 0xFEE0));   // built at run time: no full-width number sits in this file
const NAMETEXT = NAME.first + ' ' + NAME.last;

// ---- the register ----------------------------------------------------------------------------------------------------------------
// planted: strings looked for in every returned string (case-insensitive); digits: a digit run looked for after stripping non-digits;
// onlyIn: count a hit only in that output field. sev says what could reach the output, not how likely it is: none is observed on a tenant.
const GAPS = [
  // a person's name or detail on a person route
  { id: 'non-latin-name', sev: 'material', why: 'the scrub keeps only values that contain a Latin letter (A-Z)', path: PERSON, title: CYR.first + ' ' + CYR.last,
    els: [input(CYR.first, 'First name'), input(CYR.last, 'Last name'), put('h', CYR.first + ' ' + CYR.last), put('btn', 'Message ' + CYR.first)], planted: [CYR.last, CYR.first] },
  { id: 'letterless-field-values', sev: 'material', why: 'a field value with no letter (a date, a short number, a postal code) is not a secret', path: PERSON, title: NAMETEXT,
    els: [input('04/10/2012', 'Date of birth'), input(cat('010', '-', '0123'), 'Phone'), input('12345', 'ZIP'), put('lbl', 'Born 04/10/2012'), put('lbl', cat('Phone 010', '-', '0123')), put('h', 'ZIP 12345')],
    planted: ['04/10/2012', cat('010', '-', '0123'), '12345'] },
  { id: 'owner-first-name-alone-with-no-fields', sev: 'material', why: 'with no text field that holds the name, the only secret is the part of the title before its separator, taken as a whole string, so a first name on its own is not scrubbed (a secret for each word of the title would catch it)', path: PERSON, title: NAMETEXT + ' | PushPress',
    els: [put('h', NAMETEXT), put('btn', 'Charge ' + NAME.first)], planted: [NAME.first], onlyIn: 'btn' },
  { id: 'title-with-an-em-dash-separator', sev: 'material', why: 'the title is split only on a pipe, an en dash or a hyphen with a space each side, so with an em dash the whole title is the secret and it never equals the heading', path: PERSON, title: NAMETEXT + ' — PushPress',
    els: [put('h', NAMETEXT)], planted: [NAME.last] },
  { id: 'title-with-the-name-second', sev: 'material', why: 'only the part before the first separator is used, and only when it holds a space, so with "Product | Name" no title secret is taken', path: PERSON, title: 'PushPress | ' + NAMETEXT,
    els: [put('h', NAMETEXT)], planted: [NAME.last] },
  { id: 'title-written-last-comma-first', sev: 'material', why: 'a comma is not a separator, the part before it would be one word and a title part must hold a space to be a secret, and "Last, First" never equals the heading "First Last"; only a secret for each word of the title catches it (a comma split alone does not)', path: PERSON, title: NAME.last + ', ' + NAME.first,
    els: [put('h', NAMETEXT)], planted: [NAME.last] },
  { id: 'second-person-plain-text', sev: 'material', why: 'recorded as H3: a second person shown only as text on a person page is not a secret', path: PERSON, title: NAMETEXT,
    els: [input(NAME.first, 'First name'), input(NAME.last, 'Last name'), put('h', 'Guardian Rosalind Tuckerbottom')], planted: ['Tuckerbottom'] },
  // phone numbers (H16), each in a label off a person route
  ...[
    ['phone-no-space-after-parenthesis', cat('(', N.a, ')', N.b, '-', N.c)], ['phone-seven-digits-with-space', cat(N.a, ' ', N.b, N.c)], ['phone-slashes', [N.a, N.b, N.c].join('/')],
    ['phone-international-spacing', cat('+44 20 ', '7946 ', '0958')], ['phone-international-parenthesised-area-code', cat('+44 (20) ', '7946', '-', '0958')],
    ['phone-glued-extension', cat(N.a, '-', N.b, '-', N.c, 'x45')], ['phone-glued-ext-word', cat(N.a, '-', N.b, '-', N.c, 'ext45')],
    ['phone-seven-digit-local', cat(N.b, '-', N.c)], ['phone-en-dash', [N.a, N.b, N.c].join('–')], ['phone-spaces-around-dash', cat('(', N.a, ') ', N.b, ' - ', N.c)],
    ['phone-underscores', [N.a, N.b, N.c].join('_')], ['phone-uk-national', cat('07700 ', '900123')], ['phone-french', cat('06 39 ', '98 12 34')], ['phone-full-width-digits', fullWidth(cat(N.a, '-', N.b, '-', N.c))],
  ].map(([id, num]) => ({ id, sev: 'material', why: 'the text mask does not match this way of writing a number', path: LIST, els: [put('lbl', 'Phone ' + num)], digits: digitsOf(num).slice(-7) })),
  { id: 'button-label-with-a-phone-in-short-groups', sev: 'material', why: 'a button label is not passed through the text mask and is dropped only when it holds an @ or a run of 3 digits, so a number written in groups of two survives; today\'s text mask would not catch it either (phone-french leaks the same way through a label), so only a lower drop rule closes it on its own', path: LIST,
    els: [put('btn', 'Call ' + cat('06 39 ', '98 12 34'))], digits: '9981234' },
  { id: 'email-full-width-at-sign', sev: 'low', why: 'the email mask needs an ASCII at sign, so an address written with the full-width character passes', path: LIST,
    els: [put('lbl', 'Email ' + cat('jane.fixture', String.fromCharCode(0xFF20), 'example', '.invalid'))], planted: ['jane.fixture'] },
  // links and paths (H19, H20)
  ...[cat('whatsapp://send?phone=1', N.a, N.b, N.c), cat('callto:', N.a, N.b, N.c), cat('facetime:', N.a, N.b, N.c), 'skype:jane.fixture?call', cat('viber://chat?number=%2B1', N.a, N.b, N.c),
    cat('sgnl://signal.me/#p/+1', N.a, N.b, N.c), cat('https://wa.me/1', N.a, N.b, N.c)].map(h => (
    { id: 'contact-link-' + h.split(/[:/]/)[0] + (h.includes('wa.me') ? '-wa-me' : ''), sev: 'material', why: 'only mailto, tel and sms links are treated as contact links, so the text (a name) is kept', path: LIST, els: [link(NAMETEXT, h)], planted: [NAME.last] })),
  { id: 'email-in-a-same-origin-path', sev: 'material', why: 'an email in a path segment is not masked (the text mask runs on text, not on paths)', path: LIST, els: [link('History', cat('/members/by-email/', EMAIL))], planted: ['jane.fixture'] },
  { id: 'person-link-with-numeric-id', sev: 'material', why: 'a 5-digit id is caught by neither rule: the person-route test for a link, and the path mask that prints it, need 8 or more characters after /user/ or /people/, and the id rule needs 10 or more hex characters', path: LIST, els: [link(NAMETEXT, '/user/48213')], planted: [NAME.last, '48213'] },
  { id: 'person-link-under-people-members', sev: 'material', why: 'the person test looks only at the first segment after /people/ (8 or more characters, not a list name), and the id rule needs 10 or more hex characters, so an 8-digit id one segment below a list page is seen by neither (a 10-character hex id there is masked by the id rule)', path: LIST, els: [link(NAMETEXT, '/people/members/12345678')], planted: [NAME.last, '12345678'] },
  { id: 'person-id-in-a-query', sev: 'material', why: 'only the path is tested for a person id', path: LIST, els: [link(NAMETEXT, '/checkins?user=' + UID)], planted: [NAME.last] },
  { id: 'person-link-that-is-a-role-button', sev: 'material', why: 'the link is masked in the link list but its text is also a button label, which the person-link mask does not see', path: LIST,
    els: [el({ tag: 'A', sel: ['a[href]', '[role=button]'], text: NAMETEXT, attrs: { href: '/user/' + UID, role: 'button' } })], planted: [NAME.last], onlyIn: 'btn' },
  // identifiers and address-like strings in text (H21; lower severity)
  { id: 'uuid-in-text', sev: 'low', why: 'the text mask covers emails and phone-like numbers only, so an id in text is never masked', path: LIST, els: [put('lbl', 'Customer 3f2b8c1e-4a5b-4c6d-8e9f-0a1b2c3d4e5f')], planted: ['3f2b8c1e-4a5b-4c6d-8e9f-0a1b2c3d4e5f'] },
  { id: 'prefixed-hex-id-in-text', sev: 'low', why: 'the id shape that the path mask knows is not masked in text either', path: LIST, els: [put('lbl', 'Record ' + UID)], planted: [UID] },
  { id: 'payment-processor-id-in-text', sev: 'low', why: 'a processor customer id in text is not masked', path: LIST, els: [put('lbl', 'Processor ' + cat('cus', '_', 'FixtureSample01'))], planted: [cat('cus', '_', 'FixtureSample01')] },
  { id: 'invoice-number-in-text', sev: 'low', why: 'invoice and order numbers in text are not masked', path: LIST, els: [put('lbl', 'Invoice INV-004213 Order #100245')], planted: ['INV-004213', '#100245'] },
  { id: 'card-last-four-in-text', sev: 'low', why: 'the last four digits of a card are not masked', path: LIST, els: [put('lbl', 'Card •••• 4242')], planted: ['4242'] },
  { id: 'street-address-in-text', sev: 'low', why: 'a street address is not masked', path: LIST, els: [put('lbl', '221 Fixture Street, 12345')], planted: ['221 Fixture Street'] },
];

// ---- controls: a masked shape that leaks means the extractor regressed; a positive control that is not found means this checker stopped reading ----
const CONTROLS = [
  // positive controls: values the extractor passes through, so the checker is shown to read the fields it claims to read (and to fold full-width digits)
  { id: 'checker-finds-a-word-in-a-heading', reads: true, path: LIST, els: [put('h', 'Sentinelword')], planted: ['Sentinelword'] },
  { id: 'checker-finds-a-word-in-a-button', reads: true, path: LIST, els: [put('btn', 'Sentinelbutton')], planted: ['Sentinelbutton'] },
  { id: 'checker-finds-a-word-in-a-link', reads: true, path: LIST, els: [link('Sentinellink', '/reports')], planted: ['Sentinellink'] },
  { id: 'checker-finds-a-short-number-in-a-label', reads: true, path: LIST, els: [put('lbl', 'Seats 42')], digits: '42' },
  { id: 'checker-folds-a-full-width-number-in-a-label', reads: true, path: LIST, els: [put('lbl', 'Seats ' + fullWidth('42'))], digits: '42' },
  // masked shapes
  { id: 'phone-parenthesis-and-space', path: LIST, els: [put('lbl', cat('Phone (', N.a, ') ', N.b, '-', N.c))], digits: N.b + N.c },
  { id: 'phone-international-plus-one', path: LIST, els: [put('lbl', cat('Phone +1 ', N.a, ' ', N.b, ' ', N.c))], planted: ['+1'], digits: N.b + N.c },
  { id: 'email-in-text', path: LIST, els: [put('lbl', 'Email ' + EMAIL)], planted: ['jane.fixture'] },
  { id: 'button-edit-name', path: LIST, els: [put('btn', 'Edit ' + NAMETEXT)], planted: [NAME.last] },
  { id: 'person-link-hex-id', path: LIST, els: [link(NAMETEXT, '/user/' + UID)], planted: [NAME.last, UID] },
  { id: 'person-link-non-hex-slug', path: LIST, els: [link(NAMETEXT, cat('/user/slug', '-', 'zzzzzzzz'))], planted: [NAME.last, 'zzzzzzzz'] },
  { id: 'record-id-link-that-is-not-a-person', path: LIST, els: [link(NAMETEXT, cat('/invoices/inv', '_', '9f3c', '000012'))], planted: [NAME.last, '9f3c000012'] },
  { id: 'mailto-link-with-a-name', path: LIST, els: [link(NAMETEXT, 'mailto:' + EMAIL)], planted: [NAME.last] },
  { id: 'title-pipe-separator-and-no-fields', path: PERSON, title: NAMETEXT + ' | PushPress', els: [put('h', NAMETEXT)], planted: [NAME.last, NAME.first] },
  { id: 'title-en-dash-separator-and-no-fields', path: PERSON, title: NAMETEXT + ' – PushPress', els: [put('h', NAMETEXT)], planted: [NAME.last, NAME.first] },
  // no page title here, so only the field values can scrub the heading
  { id: 'input-value-scrubbed-on-a-person-route', path: PERSON, title: '', els: [input(NAME.first, 'First name'), input(NAME.last, 'Last name'), put('h', NAMETEXT)], planted: [NAME.last, NAME.first] },
];

// ---- running ---------------------------------------------------------------------------------------------------------------------
const strings = v => (typeof v === 'string' ? [v] : Array.isArray(v) ? v.flatMap(strings) : v && typeof v === 'object' ? Object.values(v).flatMap(strings) : []);
// which of an entry's planted values reach which output fields; fields counts a field once however many strings in it hit
function leaks(out, e) {
  const vals = [...(e.planted || []).map(v => ({ text: v })), ...(e.digits ? [{ digits: e.digits }] : [])];
  const fields = new Set(), leaked = new Set();
  for (const [field, v] of Object.entries(out)) {
    for (const s of strings(v)) {
      const low = s.toLowerCase(), dg = digitsOf(s);
      vals.forEach((x, i) => {
        const hit = x.text !== undefined ? low.includes(x.text.toLowerCase()) : dg.includes(x.digits);
        if (hit && (!e.onlyIn || e.onlyIn === field)) { fields.add(field); leaked.add(i); }
      });
    }
  }
  return { fields: [...fields], leaked: leaked.size, total: vals.length };
}
const FIELDS = ['p', 'h', 'tabs', 'btn', 'th', 'inp', 'lbl', 'sw', 'a', 'region', 'pg'];
// a malformed entry would read as a result about the extractor, so it is an ERROR; digit runs are matched after everything that is not a digit
// is stripped, so a short digits value can also match digits that sit in different words of one string (the positive controls use 42)
function problem(e) {
  const vals = (e.planted || []).map(v => String(v).toLowerCase());
  if (vals.some(v => v.trim().length < 2)) return 'a planted value is empty or too short';
  if (vals.some((v, i) => vals.some((w, j) => i !== j && w.includes(v)))) return 'a planted value is contained in another';
  if (e.digits !== undefined && !/^\d{2,}$/.test(e.digits)) return 'digits must be 2 or more ASCII digits';
  if (e.digits !== undefined && vals.some(v => { const d = digitsOf(v); return d.length >= 2 && (d.includes(e.digits) || e.digits.includes(d)); })) return 'digits overlap a planted value';
  if (e.onlyIn && !FIELDS.includes(e.onlyIn)) return 'onlyIn names no output field';
  return '';
}
// every field in which a gap leaks needs a positive control that is found in it; otherwise a checker that stopped reading the field would show
// the gaps there as fixed
function coverage(rows) {
  const read = new Set(rows.filter(r => r.kind === 'positive' && r.status === 'PASS').flatMap(r => r.fields));
  return [...new Set(rows.filter(r => r.kind === 'gap' && (r.status === 'XFAIL' || r.status === 'PARTIAL')).flatMap(r => r.fields))].filter(f => !read.has(f)).sort();
}
function run(src) {
  const rows = [];
  for (const e of [...GAPS.map(g => ({ ...g, kind: 'gap' })), ...CONTROLS.map(c => ({ ...c, kind: c.reads ? 'positive' : 'masked' }))]) {
    let r = { fields: [], leaked: 0, total: 0 }, error = problem(e) ? 'bad entry: ' + problem(e) : '';
    if (!error) { try { r = leaks(extract(e.els, e.path, e.title || '', src), e); } catch (err) { error = (err && err.name) || 'Error'; } }
    if (!error && r.total === 0) error = 'plants nothing';           // an entry with no value would read as XFAIL (0 of 0) whatever the extractor does
    let status;
    if (error) status = 'ERROR';
    else if (e.kind === 'gap') status = r.leaked === r.total ? 'XFAIL' : r.leaked === 0 ? 'XPASS' : 'PARTIAL';
    else if (e.kind === 'positive') status = r.leaked === r.total ? 'PASS' : 'FAIL';           // a positive control passes only when every planted value is found
    else status = r.leaked === 0 ? 'PASS' : 'FAIL';
    rows.push({ id: e.id, kind: e.kind, severity: e.sev || '', status, values: r.total, leaking: r.leaked, fields: r.fields, why: e.why || '', error });
  }
  return rows;
}
const isBad = r => r.status === 'ERROR' || r.status === 'XPASS' || r.status === 'PARTIAL' || r.status === 'FAIL';
const show = rows => { const t = {}; for (const r of rows) t[r.status] = (t[r.status] || 0) + 1; return Object.entries(t).map(([k, n]) => k + ' ' + n).join(', '); };

// ---- --flip-check: crude fixes (one or two small edits each), applied to copies held in memory, must flip exactly the entries they target ----
// This is the control for the XPASS rule: it shows that a fix of each kind is noticed and that no control breaks. The fixes are crude, so
// this proves the register notices a fix, not that the fix is safe (this check does not run the other tests on them; known-gaps-fix-trials.json
// records one run of each through them). A fix whose original text is no
// longer in the extractor exactly once is a SKIP and FAILS the check: the extractor was reformatted or really changed, that fix is no longer
// verified, and FIXES has to be updated (after a real fix, promote its entries and delete its fix).
const ids = prefix => GAPS.filter(g => g.id.startsWith(prefix)).map(g => g.id);
// A fix names the entries it targets (flips) and, separately, the side effects it is known to have (also): this first one is greedy, so it
// also masks the digits inside an id (that entry flips) and part of the letterless entry (PARTIAL), and it masks an ISO date, which the stub
// harness pins ("Report 2026-10-01" must survive). It is a demonstration that a phone fix is noticed, not a fix to use.
const FIXES = [
  { name: 'text mask: fold with NFKC, and any run of 7 or more digits with separators or an extension is a phone', flips: [...ids('phone-'), 'email-full-width-at-sign'],
    also: { xpass: ['prefixed-hex-id-in-text'], partial: ['letterless-field-values'] },
    from: String.raw`const safe = t => clean(t).replace(/\S*@\S*/g, '<email>')`,
    to: String.raw`const safe = t => clean(t).normalize('NFKC').replace(/\S*@\S*/g, '<email>').replace(/\+?\d(?:[\s().\/_–-]*\d){6,}(?:\s?(?:x|ext\.?)\s?\d{1,5})?/g, '<phone>')` },
  { name: 'scrub: keep values with a letter in any script or 4 or more digits (the word boundary is left as it is: a Unicode one would stop scrubbing a name that touches a non-ASCII letter)', flips: ['non-latin-name', 'letterless-field-values'],
    from: String.raw`/[A-Za-z]/.test(v)`, to: String.raw`(/\p{L}/u.test(v) || /\d{4,}/.test(v))` },
  { name: 'contact links: any scheme other than http and https, and the wa.me and api.whatsapp.com hosts, count as contact links', flips: ids('contact-link-'),
    from: String.raw`const isContact = href => /^\s*(?:mailto|tel|sms):/i.test(href);`,
    to: String.raw`const isContact = href => /^\s*(?!https?:)[a-z][a-z0-9+.-]*:|^\s*https?:\/\/(?:wa\.me|api\.whatsapp\.com)\//i.test(href);` },
  { name: 'title: an em dash, a middle dot and a colon also separate the name from the product', flips: ['title-with-an-em-dash-separator'],
    from: String.raw`.split(/\s[|–-]\s/)[0]`, to: String.raw`.split(/\s[|–—·:-]\s/)[0]` },
  { name: 'person link: any id after /user/ or /people/, not only 8 or more characters (in the person test and in the path mask)', flips: ['person-link-with-numeric-id'],
    from: '[^/?]{8,}/;', to: '[^/?]{1,}/;',
    from2: String.raw`[^/?]{8,}.*/, '$1/<id>')`, to2: String.raw`[^/?]{1,}.*/, '$1/<id>')` },
];
function replaceOnce(s, a, b) { const i = s.indexOf(a); return i < 0 || s.indexOf(a, i + 1) >= 0 ? null : s.slice(0, i) + b + s.slice(i + a.length); }
function flipCheck() {
  const baseRows = run(SRC), baseBad = baseRows.filter(isBad), uncovered = coverage(baseRows);
  if (baseBad.length || uncovered.length) {
    console.log('flip-check needs a clean baseline; not XFAIL or PASS: ' + [...baseBad.map(r => r.id), ...uncovered.map(f => 'field ' + f + ' has no positive control')].join(', '));
    return { ok: false, applied: 0, results: [] };
  }
  const results = [];
  for (const f of FIXES) {
    let patched = replaceOnce(SRC, f.from, f.to);
    if (patched && f.from2) patched = replaceOnce(patched, f.from2, f.to2);
    if (!patched) { results.push({ name: f.name, status: 'SKIP', note: 'the original text is not in the extractor exactly once' }); continue; }
    const rows = run(patched);
    const named = status => rows.filter(r => r.status === status).map(r => r.id).sort();
    const side = f.also || {};
    const wantFlipped = [...f.flips, ...(side.xpass || [])].sort(), wantPartial = [...(side.partial || [])].sort();
    const broken = [...named('FAIL'), ...named('ERROR')];
    const ok = JSON.stringify(named('XPASS')) === JSON.stringify(wantFlipped) && JSON.stringify(named('PARTIAL')) === JSON.stringify(wantPartial) && broken.length === 0;
    results.push({ name: f.name, status: ok ? 'OK' : 'BAD', flipped: named('XPASS').length, expected: wantFlipped.length, targeted: f.flips.length, partial: named('PARTIAL').length, controls_broken: broken.length });
  }
  return { ok: results.length > 0 && results.every(r => r.status === 'OK'), applied: results.filter(r => r.status === 'OK').length, results };
}

function main() {
  if (process.argv.includes('--flip-check')) {
    const { ok, applied, results } = flipCheck();
    for (const r of results) console.log(`${r.status.padEnd(4)} flips ${r.flipped === undefined ? '-' : r.flipped + ' of ' + r.expected + ' (' + r.targeted + ' targeted)'}  partial ${r.partial === undefined ? '-' : r.partial}  controls broken ${r.controls_broken === undefined ? '-' : r.controls_broken}  ${r.name}${r.note ? '  (' + r.note + ')' : ''}`);
    if (results.some(r => r.status === 'SKIP')) console.log('a fix was skipped: its original text is no longer in the extractor exactly once (reformatted or really changed), so it is no longer verified; update FIXES');
    if (JSON_OUT) fs.writeFileSync(JSON_OUT, JSON.stringify({ recorded: '2026-11-09', mode: 'flip-check', applied, results }, null, 2) + '\n');
    console.log(`pushpress-extractor-known-gaps.js --flip-check: ${ok ? 'PASS' : 'FAIL'}`);
    process.exit(ok ? 0 : 1);
  }
  const rows = run(SRC);
  for (const r of rows) console.log(`${r.status.padEnd(7)} ${r.kind.padEnd(8)} ${r.id.padEnd(48)} ${r.fields.join(',')}${r.status === 'XPASS' ? '  (no longer leaks: promote it to a contract)' : ''}${r.status === 'PARTIAL' ? `  (${r.leaking} of ${r.values} values still leak: split the entry or promote it)` : ''}${r.error ? '  ' + r.error : ''}`);
  console.log('tally: ' + show(rows));
  const brokenChecker = rows.filter(r => r.kind === 'positive' && r.status !== 'PASS'), uncovered = coverage(rows);
  if (brokenChecker.length) console.log('the checker failed a positive control (' + brokenChecker.map(r => r.id).join(', ') + '): XPASS lines above are not evidence of a fix');
  if (uncovered.length) console.log('no positive control is found in field ' + uncovered.join(', ') + ': a checker that stopped reading it would show the gaps there as fixed');
  if (JSON_OUT) {
    const tally = {}; for (const r of rows) tally[r.status] = (tally[r.status] || 0) + 1;
    fs.writeFileSync(JSON_OUT, JSON.stringify({ recorded: '2026-11-09', extractor: path.basename(process.env.PP_EXTRACT || 'pp-extract.js'), tally, entries: rows }, null, 2) + '\n');
  }
  const bad = rows.filter(isBad).length + uncovered.length;
  console.log(`pushpress-extractor-known-gaps.js: ${bad ? 'FAIL' : 'PASS'}`);
  process.exit(bad ? 1 : 0);
}

if (require.main === module) main();
else module.exports = { extract, el, put, link, input, cat, N, NAME, NAMETEXT, UID, LIST, PERSON, EMAIL, digitsOf, fullWidth, GAPS, CONTROLS, FIXES, FIELDS, SRC, run, leaks, flipCheck, problem, coverage };
