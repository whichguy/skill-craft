/* pp-extract.js — structure-only reader for the PushPress Core admin UI.
 *
 * USE (in a signed-in tab on https://<tenant>.pushpress.com, through the host's page-script tool):
 *   1. Pass this whole file as the script text (Claude in Chrome: `text` of mcp__claude-in-chrome__javascript_tool,
 *      action javascript_exec).
 *      It returns "pp-extract installed". A full page load wipes `window`; it also saved itself to
 *      sessionStorage, so restore with:  (0, eval)(sessionStorage.getItem('__pp_lib'))
 *   2. Then, in later page-script calls (on Claude in Chrome top-level `await` works and an async IIFE returns `{}`):
 *        await __pp.sidebar()                    // expand every sidebar group; one line per group/link
 *                                                // (long results go to #pp-dump — then read the page text)
 *        await __pp.wait(); __pp.store('Label')  // record this page's structure into sessionStorage
 *        __pp.dump(['Label', ...])               // render results into <article id="pp-dump">, then
 *                                                // read them as page text (no ~2.5 K output cap)
 *        __pp.company('<company name>')          // optional, once per tab: leave the company-switcher
 *                                                // button (it carries the company name) out of button lists
 *        __pp.clear()                            // remove everything stored or injected — do this last
 *
 * RECORDS: headings, tabs, buttons, column headers, input labels/placeholders, toggles, link PATTERNS,
 *          `icons` (a COUNT of unnamed icon-only buttons — find those with `find` or a screenshot) and
 *          `region` (text of side panels such as KPI summaries; skipped on /user/ pages).
 * MASKS:   link text for any URL with an ID segment; buttons containing "@" or 3+ digits; "Select/Edit/
 *          View/Delete/Remove/Open <name>" and "... for/of <name>" labels.
 * DOES NOT PROTECT: the page <title>, headings on a person's profile, text inside iframes, screenshots.
 *          Skip or mask those yourself, and never write what you read there into the repo.
 * READ-ONLY: the only clicks it makes are the sidebar group toggles in sidebar().
 */
(function install() {
  const LIB_KEY = '__pp_lib', RES_KEY = '__pp_res', CFG_KEY = '__pp_cfg';
  // Top-bar buttons that are on every page and so are not page content. The company switcher shows the
  // tenant's company name, which this file cannot know: declare it with __pp.company('<company name>').
  const CHROME = ['Search', 'Toggle Assistant', 'Product updates', 'Support and updates'];
  const cfg = () => { try { return JSON.parse(sessionStorage.getItem(CFG_KEY) || '{}'); } catch (e) { return {}; } };
  const isChrome = b => CHROME.includes(b) || (!!cfg().company && b === cfg().company);
  const clean = s => (s || '').trim().replace(/\s+/g, ' ');
  const uniq = a => [...new Set(a.filter(Boolean))];
  const vis = el => { const r = el.getBoundingClientRect(); return (r.width || r.height) && r.left >= 290; };
  const q = sel => [...document.querySelectorAll(sel)].filter(vis);
  const ID_SEG = /\/([A-Za-z]*[_-])?[0-9a-f]{10,}/;
  const PERSON = /^\/(user|people)\/[^/?]{8,}/;
  const maskLabel = t => t
    .replace(/^(Select|Edit|View|Delete|Remove|Open) (?!all$|row$).{2,}$/i, '$1 <item>')
    .replace(/\b(for|of) .{2,}$/i, '$1 <item>');
  const pathOf = a => {
    try {
      const u = new URL(a.getAttribute('href') || '', location.origin);
      if (u.origin !== location.origin) return 'EXT ' + u.hostname;
      return u.pathname + (u.search ? ' [q:' + [...u.searchParams.keys()].join(',') + ']' : '') + u.hash;
    } catch (e) { return ''; }
  };
  const linkLine = a => {
    const p = pathOf(a);
    if (ID_SEG.test(p) || PERSON.test(p)) {
      return '<item> -> ' + p.replace(/\/([A-Za-z]*[_-])?[0-9a-f]{10,}.*/, '/<id>').replace(/^(\/(user|people))\/[^/?]{8,}.*/, '$1/<id>');
    }
    return clean(a.innerText).slice(0, 40) + ' -> ' + p;
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
    const txt = clean(document.body.innerText);
    const r = {
      p: location.pathname + (location.search ? ' [q:' + [...new URLSearchParams(location.search).keys()].join(',') + ']' : '') + location.hash,
      h: uniq(q('h1,h2,h3,h4,[role=heading]').map(e => clean(e.innerText))).slice(0, 25),
      tabs: uniq(q('[role=tab]').map(e => clean(e.innerText))).slice(0, 20),
      btn: uniq(q('button,[role=button]').map(e => clean(e.innerText) || e.getAttribute('aria-label') || e.title)
        .filter(t => t && !/@|\d{3,}/.test(t)).map(maskLabel)).filter(b => !isChrome(b)).slice(0, 45),
      th: uniq(q('th,[role=columnheader]').map(e => clean(e.innerText))).slice(0, 40),
      inp: uniq(q('input,select,textarea').map(e => e.getAttribute('aria-label') || e.placeholder || e.name || e.type)).slice(0, 30),
      lbl: uniq(q('label,legend,h5,h6').map(e => clean(e.innerText).slice(0, 60))).slice(0, 50),
      sw: uniq(q('[role=switch],input[type=checkbox],input[type=radio]')
        .map(e => clean(e.getAttribute('aria-label') || (e.closest('label') || {}).innerText || e.name || ''))).slice(0, 40),
      rows: q('tbody tr,[role=row]').length,
      pg: (txt.match(/Page \d+ of \d+|rows per page/i) || [''])[0],
      a: uniq(q('a[href]').map(linkLine)).slice(0, 30),
      // icon-only buttons have no text or aria-label, so they cannot be named here: only counted
      icons: q('button,[role=button]').filter(b => !clean(b.innerText) && !b.getAttribute('aria-label') && !b.title).length,
      // side panels (e.g. a KPI summary) are plain text; skipped on person pages, where they could hold names
      region: /^\/user\//.test(location.pathname) ? '' : uniq(q('[role=complementary],aside')
        .map(e => clean(e.innerText).replace(/\S*@\S*/g, '<email>').slice(0, 200))).slice(0, 4),
    };
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
    const out = [];
    document.querySelectorAll('button[aria-expanded], a[href]').forEach(el => {
      const r = el.getBoundingClientRect();
      if (r.left > 300 || (!r.width && !r.height)) return;
      if (el.tagName === 'BUTTON' && !names.includes(clean(el.innerText))) return; // skips the user-menu button (a person's name)
      out.push(el.tagName === 'BUTTON'
        ? 'GROUP ' + clean(el.innerText).slice(0, 40)
        : 'LINK  ' + clean(el.innerText || el.getAttribute('aria-label')).slice(0, 50) + '  ->  ' + pathOf(el));
    });
    // ~55 lines will not fit under the tool's output cap: park them in the dump element instead.
    if (out.join('\n').length > 2000) {
      dumpEl().textContent = '### sidebar\n' + out.join('\n');
      return 'sidebar: ' + out.length + ' lines written to #pp-dump — read them as page text, then __pp.clear()';
    }
    return out;
  };

  window.__pp = { wait, extract, store, dump, clear, sidebar, company };
  try { sessionStorage.setItem(LIB_KEY, '(' + install.toString() + ')()'); } catch (e) { /* storage blocked: re-paste after a reload */ }
  return 'pp-extract installed';
})()
