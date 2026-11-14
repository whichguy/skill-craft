'use strict';

// Real-browser privacy regression test for skills/pushpress/scripts/pp-extract.js.
//
// The stub-DOM harness (test/pushpress-extractor-harness.js) pins the extractor's logic, but a live pass once found a name leak
// that tests, reviews and scans had all passed, because layout, innerText and CSS only exist in a browser. This runs the real
// extractor in real Chrome against synthetic admin pages (synthetic-page.cjs) with planted names, emails, phone numbers and URL
// parts, at four viewport configurations, and checks EVERY value it returns, plus what dump() writes and what sidebar() prints.
//
//   node test/fixtures/pushpress-extractor/privacy-fixture.cjs [--quick] [--no-controls] [--json <file>]
//   node test/fixtures/pushpress-extractor/privacy-fixture.cjs --serve [port]    only serve the pages, to try another host's browser tool
//
// Statuses: PASS (a contract holds); FAIL (a contract is broken: exit 1); XFAIL (a KNOWN GAP leaks, as recorded; exit 0);
// XPASS (a known gap no longer leaks: exit 1 so the case is promoted to a contract and the journal updated).
// Controls run the same cases against deliberately broken copies of the extractor; each must produce a failure of the kind that break is
// expected to cause (mutations.cjs `expect`), and a run error is an ERROR, never a catch, or the fixture is blind. Caps are tested only by
// the property test.
// Nothing here prints a planted value: only its kind, the field it reached and a count. A run error prints its name and the step that
// failed; its message can quote page text, so it is shown only with PP_FIXTURE_DEBUG=1.
//
// PP_EXTRACT=<file> tests another copy of the extractor. Playwright and Chrome are found the way the other browser fixtures
// find them (PLAYWRIGHT_MODULE_PATH, BROWSER_EXECUTABLE_PATH, the installed fallbacks).

const crypto = require('node:crypto');
const fs = require('node:fs');
const http = require('node:http');
const path = require('node:path');
const browserTools = require('../../shiploop_e2e/checks/battleship_ui_browser.cjs');
const site = require('./synthetic-page.cjs');

const ROOT = path.resolve(__dirname, '..', '..', '..');
const EXTRACTOR = process.env.PP_EXTRACT || path.join(ROOT, 'skills', 'pushpress', 'scripts', 'pp-extract.js');
const args = process.argv.slice(2);
const QUICK = args.includes('--quick');
const CONTROLS = !args.includes('--no-controls') && !QUICK;
const JSON_OUT = args.includes('--json') ? args[args.indexOf('--json') + 1] : '';
const SERVE = args.includes('--serve');
const SERVE_PORT = SERVE && /^\d+$/.test(args[args.indexOf('--serve') + 1] || '') ? Number(args[args.indexOf('--serve') + 1]) : 0;

// The page's own responsive rule is modelled, not measured on the real app: the sidebar is 255 px wide at 1703, 240 px at 1280, 200 px at
// 900 and a 64 px icon rail when collapsed, so the content starts at 281, 266, 218 and 90 px and the extractor's measured edge has to follow.
const VIEWPORTS = [
  { name: '1703', width: 1703, height: 900, collapsed: false },
  { name: '1280', width: 1280, height: 800, collapsed: false },
  { name: '900', width: 900, height: 800, collapsed: false },
  { name: '1703-collapsed', width: 1703, height: 900, collapsed: true },
];

// ---------------------------------------------------------------------------------------------------------------- cases
const first = site.SCENARIOS[0];
const U = site.TOKENS_URL;
const CASES = [
  ...site.SCENARIOS.map(s => ({ id: 'person/' + s.key, kind: 'person', s, path: '/user/' + s.owner.id })),
  { id: 'url/lead-slug', kind: 'person', s: first, path: '/people/' + site.slug(first.owner.full), only: ['1703'], extra: { 'url.path-slug': site.slug(first.owner.full) } },
  { id: 'url/query', kind: 'person', s: first, path: '/user/' + first.owner.id + '?' + U.key + '=' + U.value, only: ['1703'],
    extra: { 'url.query-value': U.value }, gap: { 'url.query-key': U.key } },
  { id: 'url/fragment', kind: 'person', s: first, path: '/user/' + first.owner.id + '#' + U.hash, only: ['1703'], gap: { 'url.fragment': U.hash } },
  { id: 'list/members', kind: 'list', path: '/people/members' },
  { id: 'table/class-types', kind: 'table', path: '/schedule/class-types' },
  { id: 'list/payments', kind: 'payments', path: '/payments/payments', only: ['1703', '1703-collapsed'] },
  { id: 'page/plan', kind: 'plan', path: '/plans/' + site.PLAN_ID, only: ['1703', '1703-collapsed'] },
];

// Known gaps: asserted as XFAIL until fixed. gapNote says why, in one line, for the journal.
const GAP_NOTE = {
  'guardianB.name': 'a second person shown only as plain text (a heading, a button label) is not scrubbed: scrub takes input values and a multi-word page title only',
  'guardianB.first': 'same gap: a first name inside a button label the masks do not match',
  'guardianB.phone-shape': 'a phone number typed without a separator after the closing parenthesis, "(nnn)nnn-nnnn", is not matched by the text mask (also "nnn nnnnnnn", "nnn/nnn/nnnn" and "+nn nn nnnn nnnn"; fixture/phone-shape-probe.json)',
  'url.query-key': 'p records query KEYS verbatim and scrub skips p, so a name used as a query key reaches the output',
  'url.fragment': 'p appends location.hash verbatim and scrub skips p, so a name in a fragment reaches the output',
};

const tok = (label, value, mode) => ({ label, value, mode: mode || (value.length >= 5 ? 'sub' : 'word') });
const phoneToks = (label, p) => [tok(label, p, 'sub'), tok(label + '.digits', site.digits(p), 'digits')];

function tokensFor(c) {
  const contract = [], gap = [];
  const staff = site.STAFF;
  contract.push(tok('staff.name', staff.full), tok('staff.first', staff.first), tok('staff.last', staff.last), tok('staff.email', staff.email, 'sub'), tok('nav.plan', site.PLAN_ID, 'sub'),
    tok('nav.person', site.SCENARIOS[1].owner.full), tok('nav.person.slug', site.slug(site.SCENARIOS[1].owner.full), 'sub'));
  if (c.kind === 'person') {
    const o = c.s.owner, a = c.s.guardianA, b = c.s.guardianB;
    contract.push(tok('owner.full', o.full), tok('owner.first', o.first), tok('owner.last', o.last), tok('owner.email', o.email, 'sub'),
      ...phoneToks('owner.phone', o.phone), tok('owner.dob', o.dob, 'sub'),
      tok('combo.gender', site.COMBO.gender), tok('combo.role', site.COMBO.role),
      tok('guardianA.name', a.full), tok('guardianA.last', a.last), tok('guardianA.email', a.email, 'sub'), ...phoneToks('guardianA.phone', a.phone),
      tok('guardianB.email', b.email, 'sub'), ...phoneToks('guardianB.phone', b.phone),
      tok('injection', site.INJECTION_MARKER, 'sub'));
    if (c.s.style !== 'noinputs') gap.push(tok('guardianB.name', b.full), tok('guardianB.first', b.first), tok('guardianB.phone-shape', b.gapDigits, 'digits'));      // a billing tab has no family section
    for (const [k, v] of Object.entries(c.extra || {})) contract.push(tok(k, v, 'sub'));
    for (const [k, v] of Object.entries(c.gap || {})) gap.push(tok(k, v, 'sub'));
    // the heading itself belongs to this person only when the extractor is asked about the guardian's own page; not used here
  } else if (c.kind === 'list') {
    for (const s of site.SCENARIOS.slice(0, 5)) {
      const o = s.owner, k = 'row.' + s.key;
      contract.push(tok(k + '.full', o.full), tok(k + '.first', o.first), tok(k + '.last', o.last), tok(k + '.email', o.email, 'sub'), ...phoneToks(k + '.phone', o.phone));
    }
  } else if (c.kind === 'payments') {
    // links off the person routes: an invoice id, a person path that is a name slug, a person id that is not hex, contact links whose text is a name, a query that holds an address
    for (const s of site.SCENARIOS.slice(0, 3)) {
      const o = s.owner, k = 'pay.' + s.key;
      contract.push(tok(k + '.full', o.full), tok(k + '.first', o.first), tok(k + '.last', o.last), tok(k + '.email', o.email, 'sub'), ...phoneToks(k + '.phone', o.phone),
        tok(k + '.invoice', o.inv, 'sub'), tok(k + '.slug', site.slug(o.full), 'sub'), tok(k + '.lead', o.lead, 'sub'));
    }
    contract.push(tok('pay.ext', site.EXT_ID, 'sub'));
  } else if (c.kind === 'plan') {
    contract.push(tok('plan.id', site.PLAN_ID, 'sub'));
  }
  return { contract, gap };
}

// ------------------------------------------------------------------------------------------------------------ expectations
const hasAll = (arr, want) => want.filter(w => !(arr || []).includes(w));
const count = (arr, re) => (arr || []).filter(x => re.test(x)).length;

function structureProblems(c, r) {
  const p = [];
  const miss = (field, want) => { const m = hasAll(r[field], want); if (m.length) p.push(`${field} lacks ${m.length} of ${want.length} expected entries`); };
  if (c.kind === 'person' && c.s.style === 'noinputs') {
    miss('tabs', ['Overview', 'Billing', 'Attendance', 'Notes']);
    miss('th', ['Date', 'Amount']);
    miss('btn', ['Save']);
    miss('h', ['Billing']);
    if (!(r.rows >= 1)) p.push('table row count is 0');
    if ('region' in r) p.push('region text was recorded on a person route');
    if (!r.h || !r.h.some(h => h.includes('<value>'))) p.push('no heading was replaced by <value>: the name heading is not being scrubbed');
  } else if (c.kind === 'person') {
    miss('tabs', ['Overview', 'Billing', 'Attendance', 'Notes']);
    miss('th', ['Date', 'Class']);
    miss('btn', ['Save', 'Gender', '<combobox>']);
    miss('lbl', ['First name', 'Last name', 'Email', 'Phone', 'Date of birth']);
    miss('h', ['Details', 'Family']);
    if (!(r.rows >= 1)) p.push('table row count is 0');
    if ('region' in r) p.push('region text was recorded on a person route');
    if (!r.h || !r.h.some(h => h.includes('<value>'))) p.push('no heading was replaced by <value>: the name heading is not being scrubbed');
  } else if (c.kind === 'list') {
    miss('tabs', ['Members', 'Leads', 'Staff']);
    miss('th', ['Name', 'Email', 'Phone', 'Plan']);
    miss('btn', ['Add member', 'Download CSV']);
    if (!/Page 1 of 3/.test(r.pg || '')) p.push('pagination text missing');
    if (!(r.rows >= 5)) p.push('fewer than 5 table rows counted');
    if (count(r.a, /^<item> -> \/user\/<id>$/) < 1) p.push('person links were not masked to the <item> form');
    if (count(r.a, /^<item> -> <contact>$/) < 1) p.push('contact links were not masked');
  } else if (c.kind === 'table') {
    miss('th', ['Class type', 'Pay rate', 'Visibility']);
    miss('btn', ['Back', 'Setup pay rates', '+ Class type']);
    miss('h', ['Class types']);
  } else if (c.kind === 'payments') {
    miss('th', ['Customer', 'Amount', 'Status']);
    miss('btn', ['View <item>', 'Delete <item>', 'Remove <item>', 'Open <item>']);
    for (const want of ['<item> -> /payments/invoices/<id>', '<item> -> <contact>', '<item> -> /people/<id>', '<item> -> /user/<id>', 'Filter -> /payments/payments [q:email,q]', 'Open in the payment dashboard -> EXT dashboard.example.invalid']) {
      if (!(r.a || []).includes(want)) p.push(`a lacks the entry ${want}`);
    }
  } else if (c.kind === 'plan') {
    miss('h', ['Starter plan']);
    if (r.p !== '/plans/<id>') p.push('the path field is not masked to /plans/<id>');
  }
  // every page has exactly one unnamed icon-only button (an empty one in the top bar); the sidebar toggle is named by its aria-label
  if ((r.icons || 0) !== 1) p.push(`icon-only button count is ${r.icons || 0}, expected 1`);
  if (r.btn && r.btn.some(b => b === site.COMPANY)) p.push('the company switcher button was not filtered after __pp.company()');
  if (r.btn && r.btn.some(b => ['Search', 'Toggle Assistant', 'Product updates', 'Support and updates'].includes(b))) p.push('a top-bar button was listed as page content');
  if (r.btn && r.btn.some(b => /^(collapse|expand|toggle) sidebar$/i.test(b))) p.push('a sidebar toggle button was listed as page content');
  return p;
}

function sidebarProblems(vp, side) {
  const p = [];
  const want = vp.collapsed ? site.SIDEBAR.collapsed : site.SIDEBAR.expanded;
  const dump = side.dump || '';
  if (!dump.startsWith('### sidebar')) p.push('sidebar() did not park its lines in #pp-dump');
  const lines = dump.split('\n').slice(1);
  const groups = lines.filter(l => l.startsWith('GROUP ')).length, links = lines.filter(l => l.startsWith('LINK')).length;
  if (groups !== want.groups) p.push(`GROUP lines ${groups}, expected ${want.groups}`);
  if (links !== want.links) p.push(`LINK lines ${links}, expected ${want.links}`);
  const contactLines = lines.filter(l => l === 'LINK  <item>  ->  <contact>').length;
  if (contactLines !== 2) p.push(`contact links were not masked in the sidebar (${contactLines} of 2)`);
  if (!lines.includes('LINK  <item>  ->  /plans/<id>')) p.push('the sidebar link whose path holds a record id was not masked');
  if (!lines.includes('LINK  <item>  ->  /people/<id>')) p.push('the sidebar link to a person by name slug was not masked');
  // the result comes back inline only while it is short enough (2000 characters) to survive the tool's output cap
  const isLong = lines.join('\n').length > 2000;
  if (!vp.collapsed && !isLong) p.push('the fixture sidebar is too short to exercise the long-result path');
  if (isLong && typeof side.ret !== 'string') p.push('a long sidebar result came back inline instead of as a message');
  if (!isLong && !Array.isArray(side.ret)) p.push('a short sidebar result did not come back as a list');
  return p;
}

// ---------------------------------------------------------------------------------------------------------------- scanning
function fieldsOf(extracted, dumped, side) {
  const out = [];
  for (const [k, v] of Object.entries(extracted)) {
    if (typeof v === 'string') out.push([k, v]);
    else if (Array.isArray(v)) for (const x of v) out.push([k, String(x)]);
  }
  out.push(['dump', dumped || '']);
  out.push(['sidebar', (typeof side.ret === 'string' ? side.ret : (side.ret || []).join('\n')) + '\n' + (side.dump || '')]);
  return out;
}
const reEsc = s => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
function matcher(t) {
  if (t.mode === 'digits') {                                                 // ten digits with the separators a page may put between the groups
    const re = new RegExp(t.value.slice(0, 3) + '\\)?[\\s.-]?' + t.value.slice(3, 6) + '[\\s.-]?' + t.value.slice(6));
    return s => re.test(s);
  }
  if (t.mode === 'sub') { const v = t.value.toLowerCase(); return s => s.toLowerCase().includes(v); }
  const re = new RegExp('(^|[^A-Za-z0-9])' + reEsc(t.value) + '(?![A-Za-z0-9])', 'i');
  return s => re.test(s);
}
function scan(fields, toks) {
  const found = {};
  for (const t of toks) {
    const m = matcher(t);
    for (const [field, text] of fields) {
      // A short name is also an ordinary word ("Page"), and sidebar() prints its own message ("... as page text"), so a
      // short word is checked in the page's fields only. Nothing in the fixture's sidebar can hold a person but the staff
      // menu, whose name is long.
      if (field === 'sidebar' && t.mode === 'word') continue;
      if (m(text)) { found[t.label] = found[t.label] || {}; found[t.label][field] = (found[t.label][field] || 0) + 1; }
    }
  }
  return found;
}
const fmt = found => Object.entries(found).map(([label, f]) => `${label}[${Object.entries(f).map(([k, n]) => k + ':' + n).join(',')}]`).join(' ');

// ---------------------------------------------------------------------------------------------------------------- browser
async function open(browser, base, c, vp, source) {
  let stage = 'open';                                                         // the step that was running, for a run error (its message is not printed)
  const ctx = await browser.newContext({ viewport: { width: vp.width, height: vp.height } });
  try {
    const pg = await ctx.newPage();
    stage = 'goto'; await pg.goto(base + c.path, { waitUntil: 'load' });
    stage = 'install'; await pg.addScriptTag({ content: source });
    stage = 'company'; await pg.evaluate(name => window.__pp.company(name), site.COMPANY);
    if (vp.collapsed) { stage = 'collapse'; await pg.evaluate(() => document.getElementById('tog').click()); }
    stage = 'wait'; await pg.evaluate(() => window.__pp.wait(3000));
    stage = 'extract'; const extracted = await pg.evaluate(() => window.__pp.extract());
    stage = 'dump'; const dumped = await pg.evaluate(() => { window.__pp.store('case'); window.__pp.dump(); return document.getElementById('pp-dump').textContent; });
    stage = 'sidebar'; const side = await pg.evaluate(async () => { const ret = await window.__pp.sidebar(); const d = document.getElementById('pp-dump'); return { ret, dump: d ? d.textContent : null }; });
    return { extracted, dumped, side };
  } catch (e) { e.ppStage = stage; throw e; } finally { await ctx.close(); }
}

function judge(c, vp, got) {
  const { contract, gap } = tokensFor(c);
  const fields = fieldsOf(got.extracted, got.dumped, got.side);
  const leaks = scan(fields, contract);
  const gaps = scan(fields, gap);
  const problems = [...structureProblems(c, got.extracted), ...sidebarProblems(vp, got.side)];
  const info = {};
  if (c.kind === 'list') info.injection_reaches_region = (got.extracted.region || []).some(x => x.toLowerCase().includes(site.INJECTION_MARKER));
  // collateral masking: how many returned strings were rewritten to <value> (a short or common name masks structure words too)
  if (c.kind === 'person') info.value_strings = fields.filter(([k, s]) => k !== 'dump' && k !== 'sidebar' && s.includes('<value>')).length;
  const status = Object.keys(leaks).length > 0 || problems.length > 0 ? 'FAIL' : 'PASS';
  const gapStatus = {};
  for (const g of gap) gapStatus[g.label] = gaps[g.label] ? 'XFAIL' : 'XPASS';
  return { case: c.id, viewport: vp.name, status, leaks, problems, gaps, gapStatus, info, contractTokens: contract.length, fieldsChecked: fields.length };
}

function line(r) {
  const parts = [r.status.padEnd(4), r.case.padEnd(18), '[' + r.viewport + ']'];
  parts.push(`contract ${r.contractTokens} tokens over ${r.fieldsChecked} strings`);
  if (Object.keys(r.leaks).length) parts.push('LEAK ' + fmt(r.leaks));
  if (r.problems.length) parts.push('STRUCTURE ' + r.problems.join('; '));
  const gs = Object.entries(r.gapStatus || {});
  if (gs.length) parts.push('gaps ' + gs.map(([k, v]) => `${k}=${v}`).join(' '));
  return parts.join('  ');
}

async function runAll(browser, base, source, viewports, cases) {
  const results = [];
  await Promise.all(viewports.map(async vp => {
    for (const c of cases) {
      if (c.only && !c.only.includes(vp.name)) continue;
      try { results.push(judge(c, vp, await open(browser, base, c, vp, source))); }
      catch (e) {
        // A run error is a failure of the run, never a verdict. Its message can quote page text (planted values), so only the error's name and
        // the step that failed are kept; PP_FIXTURE_DEBUG=1 adds a URL-free first line of the message.
        const detail = process.env.PP_FIXTURE_DEBUG === '1' ? ': ' + String(e && e.message).split('\n')[0].replace(/https?:\/\/\S+/g, '<url>').slice(0, 120) : '';
        results.push({ case: c.id, viewport: vp.name, status: 'FAIL', leaks: {}, problems: [`run error: ${(e && e.name) || 'Error'} during ${(e && e.ppStage) || 'the run'}${detail}`], gaps: {}, gapStatus: {}, info: {}, contractTokens: 0, fieldsChecked: 0 });
      }
    }
  }));
  const order = new Map(CASES.map((c, i) => [c.id, i]));
  return results.sort((a, b) => order.get(a.case) - order.get(b.case) || VIEWPORTS.findIndex(v => v.name === a.viewport) - VIEWPORTS.findIndex(v => v.name === b.viewport));
}

const { MUTATIONS, apply } = require('./mutations.cjs');

// ---------------------------------------------------------------------------------------------------------------- main
(async () => {
  const source = fs.readFileSync(EXTRACTOR, 'utf8');
  const blob = crypto.createHash('sha1').update('blob ' + Buffer.byteLength(source) + '\0').update(source).digest('hex');
  const server = http.createServer((req, res) => {
    const pathname = new URL(req.url, 'http://x').pathname;
    if (SERVE && pathname === '/pp-extract.js') {                             // so a host's page-script tool can fetch and evaluate the extractor in the page
      res.writeHead(200, { 'content-type': 'text/plain; charset=utf-8' }); res.end(source); return;
    }
    const html = site.render(pathname);
    res.writeHead(html ? 200 : 404, { 'content-type': 'text/html; charset=utf-8' });
    res.end(html || '<!doctype html><title>Not found</title><p>Not found');
  });
  await new Promise(r => server.listen(SERVE_PORT, '127.0.0.1', r));
  const base = 'http://127.0.0.1:' + server.address().port;
  if (SERVE) {
    // --serve [port]: only serve the synthetic pages, for trying the extractor from another host's browser tool (nothing is checked)
    const s = site.SCENARIOS[0];
    console.log(`serving synthetic pages at ${base} (Ctrl-C to stop)`);
    console.log(`  person page   ${base}/user/${s.owner.id}`);
    console.log(`  list page     ${base}/people/members`);
    console.log(`  table page    ${base}/schedule/class-types`);
    return;
  }
  const { chromium } = browserTools.playwrightModule();
  const exe = browserTools.browserExecutable();
  const browser = await chromium.launch({ headless: true, ...(exe ? { executablePath: exe } : {}) });
  const t0 = Date.now();
  const report = { extractor_blob: blob, browser: browser.version(), viewports: VIEWPORTS.map(v => v.name), results: [], controls: [] };
  let bad = 0;
  try {
    console.log(`pushpress extractor privacy fixture: extractor blob ${blob.slice(0, 8)}, Chrome ${browser.version()}, ${QUICK ? 'quick (1 viewport)' : VIEWPORTS.length + ' viewports'}`);
    const results = await runAll(browser, base, source, QUICK ? VIEWPORTS.slice(0, 1) : VIEWPORTS, CASES);
    report.results = results;
    for (const r of results) console.log(line(r));
    const tally = {}; for (const r of results) tally[r.status] = (tally[r.status] || 0) + 1;
    const gapTally = { XFAIL: 0, XPASS: 0 };
    const gaps = {}, gapFields = {};
    for (const r of results) for (const [k, v] of Object.entries(r.gapStatus || {})) {
      gapTally[v]++;
      if (v === 'XFAIL') { gaps[k] = (gaps[k] || 0) + 1; for (const f of Object.keys(r.gaps[k] || {})) (gapFields[k] = gapFields[k] || new Set()).add(f); }
    }
    report.gap_fields = Object.fromEntries(Object.entries(gapFields).map(([k, s]) => [k, [...s].sort()]));
    const byCase = {}; for (const r of results) if (r.info && 'value_strings' in r.info) byCase[r.case] = (byCase[r.case] || []).concat(r.info.value_strings);
    report.value_strings_by_case = byCase;
    bad += (tally.FAIL || 0) + gapTally.XPASS;
    if (gapTally.XPASS) console.log(`XPASS: ${gapTally.XPASS} known-gap checks no longer leak: promote them to contract checks and update the journal`);
    for (const [k, n] of Object.entries(gaps)) console.log(`known gap ${k} (${n} runs, fields ${[...gapFields[k]].sort().join(',')}): ${GAP_NOTE[k] || ''}`);
    console.log('collateral <value> masking, strings per person-route run: ' + Object.entries(byCase).map(([k, v]) => `${k.replace('person/', '')}=${[...new Set(v)].join('/')}`).join(' '));
    report.gap_tally = gapTally;
    for (const r of results) if (r.info && 'injection_reaches_region' in r.info) { console.log(`info [${r.viewport}] the planted instruction text ${r.info.injection_reaches_region ? 'DOES' : 'does not'} reach the output through region text on a list page`); break; }
    console.log('tally: ' + Object.entries(tally).map(([k, n]) => k + ' ' + n).join(', '));

    // A control is caught only when a case fails for the reason that mutation is expected to cause (mutations.cjs `expect`). A run error
    // is never a catch, and nothing is proved when the unbroken run itself failed.
    if (CONTROLS && bad > 0) {
      console.log('controls skipped: the unbroken run did not pass, so a failure on a broken copy would prove nothing');
    } else if (CONTROLS) {
      const isRunError = r => r.problems.some(p => p.startsWith('run error'));
      const matches = (spec, r) => spec.startsWith('leak:') ? Object.keys(r.leaks).some(k => k.startsWith(spec.slice(5))) : r.problems.some(p => p.includes(spec.slice(8)));
      for (const m of MUTATIONS.filter(x => x.tests.includes('fixture'))) {
        const broken = apply(source, m);
        if (broken === null) { console.log(`CONTROL ${m.name}: STALE (the text it breaks is gone or no longer unique; update the control)`); report.controls.push({ name: m.name, status: 'STALE' }); bad++; continue; }
        const subset = m.cases ? CASES.filter(c => m.cases.includes(c.id)) : CASES;      // the cases that exercise this protection (mutations.cjs `cases`)
        const rs = await runAll(browser, base, broken, VIEWPORTS.slice(0, 1), subset);
        const errors = rs.filter(isRunError);
        const fails = rs.filter(r => r.status === 'FAIL' && !isRunError(r));
        const expected = (m.expect && m.expect.fixture) || [];
        const hit = fails.some(r => expected.some(spec => matches(spec, r)));
        const status = errors.length ? 'ERROR' : hit ? 'caught' : fails.length ? 'caught the wrong thing' : 'MISSED';
        const kinds = [...new Set(fails.flatMap(r => [...Object.keys(r.leaks).map(k => 'leak:' + k.split('.')[0]), ...r.problems.map(p => 'problem:' + p.split(/[0-9]| of /)[0].trim())]))];
        console.log(`CONTROL ${m.name}: ${status} (${fails.length} failing cases${errors.length ? ', ' + errors.length + ' run errors' : ''}${kinds.length ? '; ' + kinds.slice(0, 4).join(', ') : ''})`);
        report.controls.push({ name: m.name, status, failing_cases: fails.length, run_errors: errors.length, kinds });
        if (status !== 'caught') bad++;
      }
    }
  } finally { await browser.close(); server.close(); }
  report.seconds = Math.round((Date.now() - t0) / 100) / 10;
  if (JSON_OUT) fs.writeFileSync(JSON_OUT, JSON.stringify(report, null, 2) + '\n');
  console.log(`privacy-fixture.cjs: ${bad ? 'FAIL' : 'PASS'} (${report.seconds}s)`);
  process.exit(bad ? 1 : 0);
})().catch(e => { console.error(e); process.exit(2); });
