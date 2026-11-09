/* pp-extract.js — structure-only reader for the PushPress Core admin UI.
 *
 * USE (in a signed-in tab on https://<tenant>.pushpress.com, through the host's page-script tool):
 *   1. Pass this whole file as the script text (Claude in Chrome: `text` of mcp__claude-in-chrome__javascript_tool,
 *      action javascript_exec).
 *      It returns "pp-extract installed". A full page load wipes `window`; it also saved itself to
 *      sessionStorage, so restore with:  (0, eval)(sessionStorage.getItem('__pp_lib'))
 *   2. Then, in later page-script calls (on Claude in Chrome top-level `await` works and an async IIFE returns `{}`):
 *        await __pp.sidebar()                    // expand every sidebar group; one line per group/link; the lines are
 *                                                // also parked in #pp-dump, so a page-text read right after it returns
 *                                                // them and never the page (long results come back as a message)
 *        await __pp.wait(); __pp.store('Label')  // record this page's structure into sessionStorage
 *        __pp.dump(['Label', ...])               // render results into <article id="pp-dump">, then
 *                                                // read them as page text (no ~2.5 K output cap)
 *        __pp.company('<company name>')          // optional, once per tab: leave the company-switcher
 *                                                // button (it carries the company name) out of button lists
 *        __pp.clear()                            // remove everything stored or injected — do this last
 *
 * RECORDS: headings, tabs, buttons, column headers, input labels/placeholders, toggles, link PATTERNS,
 *          `icons` (a COUNT of unnamed icon-only buttons — find those with `find` or a screenshot) and
 *          `region` (text of side panels such as KPI summaries; skipped on person routes). Content is taken to start
 *          where the sidebar ends, measured from the sidebar itself (290px when there is none). Caps: 25 headings,
 *          45 buttons, 50 labels, 30 links: on a long page (a profile) the rest is cut, so look for it with `find`.
 * MASKS:   link text for any URL whose path has an ID segment (10 or more lower-case hex characters, optionally
 *          prefixed, as in plan_ or usr_) or is a person route (/user/<id>, /people/<id>), and every mailto:/tel:/sms:
 *          link; IDs in the page path and in sidebar links; buttons containing "@" or 3+ digits are dropped; emails and
 *          phone-like numbers in all other recorded text become <email> and <phone>;
 *          "Select/Edit/View/Delete/Remove/Open <name>" and "... for/of <name>" button labels, and "Select <name>"
 *          toggle and input labels. On a person route the values of the page's text fields and a two-word page title
 *          (the person's name, which is also the page heading) become <value> wherever they appear, and a combobox
 *          button's text (a selected value) is not recorded.
 * DOES NOT PROTECT: off a person route, a person's name that stands alone (a heading, label or link text with no "@",
 *          no phone-like number and no Select/Edit/... form), link text on a URL whose ID has another shape (a UUID, a
 *          number or a short id outside the person routes), the page <title> (a browser tool may echo it), text inside
 *          iframes, screenshots. Skip or mask those yourself, and never write what you read there into the repo.
 * READ-ONLY: the only clicks it makes are the sidebar group toggles in sidebar().
 */
(function install() {
  const LIB_KEY = '__pp_lib', RES_KEY = '__pp_res', CFG_KEY = '__pp_cfg';
  // Top-bar buttons that are on every page and so are not page content. The company switcher shows the
  // tenant's company name, which this file cannot know: declare it with __pp.company('<company name>').
  const CHROME = ['Search', 'Toggle Assistant', 'Product updates', 'Support and updates'];
  const cfg = () => { try { return JSON.parse(sessionStorage.getItem(CFG_KEY) || '{}'); } catch (e) { return {}; } };
  const isChrome = b => CHROME.includes(b) || /^(collapse|expand|toggle) sidebar$/i.test(b) || (!!cfg().company && b === cfg().company);
  const clean = s => (s || '').trim().replace(/\s+/g, ' ');
  const uniq = a => [...new Set(a.filter(Boolean))];
  // Where the page content starts: the right edge of the sidebar, measured on the ancestors of its People link (they start
  // at the left edge and are narrower than 400px); 290 when there is no such link. A fixed 290 dropped a table header that
  // starts at 281 on one tenant's layout.
  let edge = 290;
  const sideEdge = () => {
    let right = 0;
    for (let e = document.querySelectorAll('a[href="/people"]')[0]; e && e !== document.body; e = e.parentElement) {
      const r = e.getBoundingClientRect();
      if (r.left <= 1 && r.width > 40 && r.width < 400 && r.right > right) right = r.right;
    }
    return right ? Math.ceil(right) : 290;
  };
  const vis = el => { const r = el.getBoundingClientRect(); return (r.width || r.height) && r.left >= edge; };
  const q = sel => [...document.querySelectorAll(sel)].filter(vis);
  const ID_SEG = /\/([A-Za-z]*[_-])?[0-9a-f]{10,}/;
  const PERSON = /^\/(user|people)\/(?!(?:non-members|members|leads|staff)(?:[/?#]|$))[^/?]{8,}/;
  const onPerson = () => /^\/user\//.test(location.pathname) || PERSON.test(location.pathname);
  const maskLabel = t => t
    .replace(/^(Select|Edit|View|Delete|Remove|Open) (?!all$|row$).{2,}$/i, '$1 <item>')
    .replace(/\b(for|of) .{2,}$/i, '$1 <item>');
  // Text outside buttons can still carry contact details: emails and phone-like numbers are masked in all of it.
  const safe = t => clean(t).replace(/\S*@\S*/g, '<email>')
    .replace(/(?:\+?\d{1,3}[\s.-]?)?\(?\d{3}\)?[\s.-]\d{3}[\s.-]\d{4}\b|\+\d{8,15}\b|\b\d{10,15}\b/g, '<phone>');
  // Row checkboxes and their inputs are labelled "Select <name>"; other toggle labels survive.
  const safeRow = t => safe(t).replace(/^Select (?!all$|row$).{2,}$/i, 'Select <item>');
  // On a person's page the visible text repeats the person: the heading is their name and the form fields hold their details.
  const esc = s => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const secrets = () => {
    if (!onPerson()) return [];
    const vals = [...document.querySelectorAll('input,textarea')]
      .filter(e => !['password', 'checkbox', 'radio', 'hidden', 'submit', 'button'].includes((e.type || '').toLowerCase()))
      .map(e => clean(e.value));
    const title = clean(document.title).split(/\s[|–-]\s/)[0];
    return uniq([...vals, /\s/.test(title) ? title : '']).filter(v => v.length >= 2 && /[A-Za-z]/.test(v)).sort((a, b) => b.length - a.length);
  };
  const scrub = (s, ss) => typeof s !== 'string' ? s
    : ss.reduce((t, v) => t.replace(new RegExp('(^|[^A-Za-z0-9])' + esc(v) + '(?![A-Za-z0-9])', 'gi'), '$1<value>'), s);
  const maskPath = p => p.replace(/\/([A-Za-z]*[_-])?[0-9a-f]{10,}.*/, '/<id>')
    .replace(/^(\/(user|people))\/(?!(?:non-members|members|leads|staff)(?:[/?#]|$))[^/?]{8,}.*/, '$1/<id>');
  const isContact = href => /^\s*(?:mailto|tel|sms):/i.test(href);
  const pathOf = a => {
    try {
      const u = new URL(a.getAttribute('href') || '', location.origin);
      if (u.origin !== location.origin) return 'EXT ' + u.hostname;
      return u.pathname + (u.search ? ' [q:' + [...u.searchParams.keys()].join(',') + ']' : '') + u.hash;
    } catch (e) { return ''; }
  };
  const linkLine = a => {
    const p = pathOf(a);
    if (isContact(a.getAttribute('href') || '')) return '<item> -> <contact>';
    if (ID_SEG.test(p) || PERSON.test(p)) return '<item> -> ' + maskPath(p);
    return safe(a.innerText).slice(0, 40) + ' -> ' + p;
  };
  const load = () => { try { return JSON.parse(sessionStorage.getItem(RES_KEY) || '{}'); } catch (e) { return {}; } };

  const wait = async (max = 6000) => {
    let last = -1, same = 0; const t0 = Date.now();
    while (Date.now() - t0 < max) {
      await new Promise(r => setTimeout(r, 300));
      const n = document.body.innerText.length;
      if (n === last) { if (++same >= 2) break; } else { same = 0; last = n; }
    }
    return Date.now() - t0;
  };

  const extract = () => {
    edge = sideEdge();
    const person = onPerson();
    const txt = clean(document.body.innerText);
    const r = {
      p: maskPath(location.pathname) + (location.search ? ' [q:' + [...new URLSearchParams(location.search).keys()].join(',') + ']' : '') + location.hash,
      h: uniq(q('h1,h2,h3,h4,[role=heading]').map(e => safe(e.innerText))).slice(0, 25),
      tabs: uniq(q('[role=tab]').map(e => safe(e.innerText))).slice(0, 20),
      // on a person route a combobox button shows a selected value (gender, role, a date): only its label is recorded
      btn: uniq(q('button,[role=button]').map(e => person && e.getAttribute('role') === 'combobox' ? (e.getAttribute('aria-label') || '<combobox>')
        : clean(e.innerText) || e.getAttribute('aria-label') || e.title)
        .filter(t => t && !/@|\d{3,}/.test(t)).map(maskLabel)).filter(b => !isChrome(b)).slice(0, 45),
      th: uniq(q('th,[role=columnheader]').map(e => safe(e.innerText))).slice(0, 40),
      inp: uniq(q('input,select,textarea').map(e => safeRow(e.getAttribute('aria-label') || e.placeholder || e.name || e.type))).slice(0, 30),
      lbl: uniq(q('label,legend,h5,h6').map(e => safe(e.innerText).slice(0, 60))).slice(0, 50),
      sw: uniq(q('[role=switch],input[type=checkbox],input[type=radio]')
        .map(e => safeRow(e.getAttribute('aria-label') || (e.closest('label') || {}).innerText || e.name || ''))).slice(0, 40),
      rows: q('tbody tr,[role=row]').length,
      pg: (txt.match(/Page \d+ of \d+|rows per page/i) || [''])[0],
      a: uniq(q('a[href]').map(linkLine)).slice(0, 30),
      // icon-only buttons have no text or aria-label, so they cannot be named here: only counted
      icons: q('button,[role=button]').filter(b => !clean(b.innerText) && !b.getAttribute('aria-label') && !b.title).length,
      // side panels (e.g. a KPI summary) are plain text; skipped on person pages, where they could hold names
      region: person ? '' : uniq(q('[role=complementary],aside')
        .map(e => safe(e.innerText).slice(0, 200))).slice(0, 4),
    };
    const ss = secrets();
    if (ss.length) for (const k of Object.keys(r)) if (k !== 'p') r[k] = Array.isArray(r[k]) ? uniq(r[k].map(s => scrub(s, ss))) : scrub(r[k], ss);
    for (const k of Object.keys(r)) if (Array.isArray(r[k]) ? !r[k].length : !r[k]) delete r[k];
    return r;
  };

  const company = name => {
    try { sessionStorage.setItem(CFG_KEY, JSON.stringify({ company: clean(name) })); } catch (e) { return 'storage blocked: company label not saved'; }
    return 'company label set';
  };

  const store = label => { const all = load(); all[label] = extract(); sessionStorage.setItem(RES_KEY, JSON.stringify(all)); return label; };

  const dumpEl = () => {
    let el = document.getElementById('pp-dump');
    if (!el) { el = document.createElement('article'); el.id = 'pp-dump'; document.body.appendChild(el); }
    return el;
  };

  const dump = labels => {
    const all = load();
    const el = dumpEl();
    el.textContent = (labels || Object.keys(all)).map(l => '### ' + l + '\n' + JSON.stringify(all[l])).join('\n');
    return el.textContent.length;
  };

  const clear = () => {
    sessionStorage.removeItem(RES_KEY); sessionStorage.removeItem(LIB_KEY); sessionStorage.removeItem(CFG_KEY);
    const d = document.getElementById('pp-dump'); if (d) d.remove();
    return 'cleared';
  };

  // Sidebar groups are absent from the DOM until opened and re-collapse after each navigation.
  const sidebar = async () => {
    const names = ['Communicate', 'Plans', 'Products', 'Schedule', 'Payments', 'Reports', 'Apps', 'Settings'];
    [...document.querySelectorAll('button[aria-expanded]')].filter(b => names.includes(clean(b.innerText)))
      .forEach(b => { if (b.getAttribute('aria-expanded') === 'false') b.click(); });
    await new Promise(r => setTimeout(r, 1200));
    edge = sideEdge();
    const out = [];
    document.querySelectorAll('button[aria-expanded], a[href]').forEach(el => {
      const r = el.getBoundingClientRect();
      if (r.left >= edge || (!r.width && !r.height)) return;
      if (el.tagName === 'BUTTON' && !names.includes(clean(el.innerText))) return; // skips the user-menu button (a person's name)
      if (el.tagName === 'BUTTON') { out.push('GROUP ' + clean(el.innerText).slice(0, 40)); return; }
      const href = el.getAttribute('href') || '', p = pathOf(el);
      out.push(isContact(href) ? 'LINK  <item>  ->  <contact>'
        : (ID_SEG.test(p) || PERSON.test(p)) ? 'LINK  <item>  ->  ' + maskPath(p)
        : 'LINK  ' + safe(el.innerText || el.getAttribute('aria-label')).slice(0, 50) + '  ->  ' + p);
    });
    // The lines are always parked in the dump element, so a page-text read right after sidebar() returns them and never the
    // page itself. ~55 lines will not fit under the tool's output cap: then only a message comes back.
    dumpEl().textContent = '### sidebar\n' + out.join('\n');
    if (out.join('\n').length > 2000) return 'sidebar: ' + out.length + ' lines written to #pp-dump — read them as page text, then __pp.clear()';
    return out;
  };

  window.__pp = { wait, extract, store, dump, clear, sidebar, company };
  try { sessionStorage.setItem(LIB_KEY, '(' + install.toString() + ')()'); } catch (e) { /* storage blocked: re-paste after a reload */ }
  return 'pp-extract installed';
})()
