// sport80 discovery v1: maintenance only, never part of an ordinary request. Needs the runtime in the same tab.
// Records structure (names, counts, status), never row values. Follows protocol-classified reads and ALLOW paths only.
(() => {
  const S = globalThis.S80;
  if (!S || S.version !== 1) throw new Error('Load the runtime first: sport80 runtime');
  const ALLOW = /*ALLOW*/[];
  const DENY = /logout|auth\.sport80\.com|\/body\/setup|\.(xlsx|pdf|csv)(\?|$)|\/uploads\//i;
  const FOLLOW = ['s80-datatable', 's80-tab-menu', 'ContactsView'];
  const bare = (u) => String(u || '').replace(/^https?:\/\/[^/]+/, '').split('?')[0];
  const portal = (u) => !/^https?:/i.test(u) || u.startsWith(location.origin);
  const allowed = (u) => ALLOW.some((p) => new RegExp('^' + p + '$').test(bare(u)));
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const D = globalThis.S80D = {done: false, error: null, requests: 0, observed_on: new Date().toISOString().slice(0, 10), roles: [], nodes: [], pages: []};
  const rec = (role, trail, rest) => D.nodes.push(Object.assign({role, trail}, rest));
  const seen = new Set();
  const keep = (r) => ({protocol: r.protocol, path: r.path, title: r.title, columns: r.columns, filters: r.filters, buttons: r.buttons, tabs: r.tabs && r.tabs.map((t) => t.title), component: r.component, propKeys: r.propKeys, formFields: r.formFields && r.formFields.map((f) => f.name), headings: r.headings, tableHeaders: r.tableHeaders, keys: r.keys, error: r.error});

  async function follow(role, trail, url, depth, redirects) {
    const key = role + '|' + url; if (seen.has(key)) return; seen.add(key);
    if (DENY.test(url)) return rec(role, trail, {protocol: 'skipped', reason: 'never fetched', path: bare(url)});
    if (!portal(url)) return rec(role, trail, {protocol: 'rankings-table', path: bare(url)});
    let r; D.requests += 1;
    try { r = await S.inspect(url, {raw: true, follow: !!redirects}); } catch (e) { if (['AUTH_REQUIRED', 'CHALLENGE', 'THROTTLED'].includes(e.code)) throw e; return rec(role, trail, {protocol: 'error', error: e.code || 'ERROR', path: bare(url)}); }
    rec(role, trail, keep(r));
    await sleep(120);
    if (r.protocol === 'tabs' && depth < 3) for (const t of r.tabs) if (t.url) await follow(role, trail + ' > ' + t.title, t.url, depth + 1);
    if (r.protocol === 'redirect' && depth < 3) await follow(role, trail + ' (list)', r.to, depth + 1);
  }

  async function crawl(sel, label) {
    const m = await S.menu(sel, {raw: true});
    D.roles.push({role: label, type: m.role.type});
    for (const n of m.nodes) {
      const trail = n.section + ' > ' + n.trail.join(' > ');
      if (n.type === 'parent') continue;
      if (n.type === 'sub-route') { rec(label, trail, {protocol: 'needs-params', params: n.needs, path: bare(n.dataUrl)}); continue; }
      if (n.external) { rec(label, trail, {protocol: 'skipped', reason: 'external', path: bare(n.url)}); continue; }
      if (n.tokenUrl) { rec(label, trail, {protocol: 'rankings-table', path: bare(n.dataUrl)}); continue; }
      if (n.vue && FOLLOW.includes(n.vue)) {
        if (n.dataUrl) await follow(label, trail, n.dataUrl, 0);
        if (n.profileUrl) await follow(label, trail + ' [profile tabs]', n.profileUrl + (m.role.body_cid ? '' : (n.profileUrl.includes('?') ? '&' : '?') + 'cid=' + m.role.cid), 0);
        continue;
      }
      const u = n.vue === 'AjaxContainer' ? n.dataUrl : n.url;
      if (!u) { rec(label, trail, {protocol: 'unvisited', reason: 'no url'}); continue; }
      if (DENY.test(u)) { rec(label, trail, {protocol: 'skipped', reason: 'never fetched', path: bare(u)}); continue; }
      if (allowed(u)) await follow(label, trail, u, 0, true); else rec(label, trail, {protocol: 'unvisited', reason: 'not classified as a read in the catalogue', path: bare(u)});
    }
  }

  (async () => {
    try {
      await crawl('personal', 'personal');
      const all = await S.roles();
      for (const r of all.filter((x) => x.body_cid)) await crawl(r.body_cid, /club/i.test(r.type || '') ? 'club' : String(r.type || 'body').toLowerCase());
      const man = await (await fetch('/build/manifest.json', {credentials: 'same-origin'})).json();
      D.pages = [...new Set(Object.keys(man).map((k) => (/assets\/js\/Pages\/(.+)\.vue$/.exec(k) || [])[1]).filter(Boolean))].sort();
    } catch (e) { D.error = e.code || e.message; }
    D.done = true;
  })();
  D.text = () => JSON.stringify({observed_on: D.observed_on, roles: D.roles, requests: D.requests, error: D.error, nodes: D.nodes, pages: D.pages}, (k, v) => (v === null || (Array.isArray(v) && !v.length) ? undefined : v));
  return 'discovery started: poll S80D.done, then read S80D.text()';
})()
