// sport80 runtime v2. Inject once per tab on the portal origin, then: await S80.exec(entry, options).
// Credentials stay in this page: tokens live in function scope only and never reach a global, a log, an error or a result.
(() => {
  const g = globalThis;
  if (g.S80 && g.S80.version === 2) return 'S80 runtime already loaded (v2)';
  const SPA = {'X-Requested-With': 'XMLHttpRequest', 'X-Keep-Session': 'keepsession'};
  const UUID = /[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/gi;
  const PUBLIC = {type: 'Public', name: null, cid: null, body_cid: null, public: true};
  const OPTION_TYPES = ['select', 'autocomplete', 'radio']; const OPTION_CAP = 50;
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const err = (code, message, extra) => Object.assign(new Error(message), {code}, extra || {});
  const origin = () => g.location.origin;
  // URLs that are not usable fail with a fixed message: the offending string is never echoed.
  const toUrl = (u, base) => { try { return new URL(String(u), base || origin() + '/'); } catch (e) { throw err('UNEXPECTED_ORIGIN', 'Not a usable URL; nothing was sent'); } };
  const absolute = (u) => toUrl(u).href;
  const qnames = (u) => { try { const x = new URL(String(u), origin() + '/'); const k = [...x.searchParams.keys()]; return (x.origin === origin() ? '' : x.origin) + x.pathname + (k.length ? '?' + k.join(',') : ''); } catch (e) { return '<unparsed url>'; } };
  const rankOrigin = () => { try { return new URL(g.env && g.env.RANKINGS_DOMAIN_URL).origin; } catch (e) { return null; } };
  const xsrf = () => { const m = /(?:^|;\s*)XSRF-TOKEN=([^;]*)/.exec(g.document.cookie || ''); return m ? decodeURIComponent(m[1]) : ''; };
  const parse = (text, path) => { try { return JSON.parse(text); } catch (e) { throw err('UNEXPECTED_RESPONSE', 'Expected JSON', {path}); } };
  const withQuery = (path, q) => { const e = Object.entries(q || {}).filter(([, v]) => v !== undefined && v !== null && v !== ''); return e.length ? path + (path.includes('?') ? '&' : '?') + e.map(([k, v]) => k + '=' + encodeURIComponent(v)).join('&') : path; };
  const today = () => new Date().toISOString().slice(0, 10);
  // A value counts as given unless it is missing, blank, an empty list or an empty object (zero and false are values).
  const present = (v) => v !== undefined && v !== null && !(typeof v === 'string' && v.trim() === '') && !(Array.isArray(v) && v.length === 0) && !(typeof v === 'object' && !Array.isArray(v) && Object.keys(v).length === 0);

  async function http(url, o = {}) {
    const method = o.method || 'GET';
    const target = toUrl(url); const abs = target.href;
    // Exact origins only: a lookalike host must never receive the SPA headers, the XSRF token or the rankings tokens.
    const same = target.origin === origin();
    if (!same && target.origin !== rankOrigin()) throw err('UNEXPECTED_ORIGIN', 'The target is neither the portal nor the rankings host; nothing was sent', {path: qnames(abs)});
    const headers = Object.assign({Accept: 'application/json, text/plain, */*'}, same ? SPA : {}, o.headers || {});
    let body;
    if (method !== 'GET') { headers['Content-Type'] = 'application/json'; body = JSON.stringify(o.json === undefined ? {} : o.json); if (same) headers['X-XSRF-TOKEN'] = xsrf(); }
    const host = same ? 'portal' : 'rankings';
    let res;
    try { res = await g.fetch(abs, {method, headers, body, credentials: same ? 'same-origin' : 'omit', redirect: same && o.follow ? 'follow' : 'manual'}); }
    catch (e) { throw err('NETWORK', 'No response: offline, blocked by CORS, or the session ended', {path: qnames(abs), host}); }
    if (res.type === 'opaqueredirect') throw err('REDIRECTED', 'The portal redirected the request instead of answering', {path: qnames(abs), host});
    const text = await res.text();
    const ctype = (res.headers.get('content-type') || '').split(';')[0];
    if (res.status >= 200 && res.status < 300) return {status: res.status, ctype, text};
    const code = {401: 'UNAUTHORIZED', 403: 'FORBIDDEN', 404: 'NOT_FOUND', 419: 'CSRF', 429: 'THROTTLED'}[res.status] || (res.status >= 500 ? 'SERVER' : 'HTTP');
    throw err(code, 'HTTP ' + res.status, {status: res.status, path: qnames(abs), host});
  }
  const challenge = (r) => r.ctype.includes('html') && /captcha|are you a robot|challenge-platform/i.test(r.text);
  const stopOnChallenge = (r, url) => { if (challenge(r)) throw err('CHALLENGE', 'The portal answered with a bot challenge: stop and ask the owner', {path: qnames(url)}); return r; };
  const getJson = async (url, o) => parse(stopOnChallenge(await http(url, o), url).text, qnames(url));

  async function ping() { try { await http('/api/account/roles'); return true; } catch (e) { return false; } }
  async function guard(fn) {
    try { return await fn(); }
    catch (e) {
      if (e && ['REDIRECTED', 'NETWORK', 'UNAUTHORIZED'].includes(e.code)) {
        if (!(await ping())) throw err('AUTH_REQUIRED', 'Not signed in: the session ended. Ask the owner to sign in, then retry.');
        if (e.code === 'UNAUTHORIZED') throw err(e.host === 'rankings' ? 'RANKINGS_REFUSED' : 'PERMISSION_DENIED', e.host === 'rankings' ? 'The rankings module refused the credentials for this scope' : 'The session is alive but this role may not read this (HTTP 401)', {status: 401, path: e.path});
        throw err(e.code === 'REDIRECTED' ? 'UNEXPECTED_REDIRECT' : 'NETWORK', e.message, {path: e.path});
      }
      throw e;
    }
  }

  async function roles() {
    const j = await getJson('/api/account/roles');
    return ((j.accounts && j.accounts.accounts) || []).map((a) => ({type: a.type, name: a.name, cid: a.cid, body_cid: a.body_cid || null}));
  }
  async function pickRole(sel) {
    if (sel === 'public') return PUBLIC;
    const all = await roles();
    const have = all.map((r) => ({type: r.type, name: r.name, body_cid: r.body_cid}));
    if (sel === undefined || sel === null || sel === 'personal') { const p = all.find((r) => !r.body_cid); if (p) return p; throw err('ROLE_NOT_FOUND', 'No personal role for this login', {have}); }
    const bodies = all.filter((r) => r.body_cid);
    const hit = sel === 'club' ? bodies.filter((r) => /club/i.test(r.type || '')) : bodies.filter((r) => String(r.body_cid) === String(sel) || (r.name || '').toLowerCase().includes(String(sel).toLowerCase()));
    if (hit.length === 1) return hit[0];
    throw err('ROLE_NOT_FOUND', hit.length ? 'More than one role matches; pass its body_cid' : 'No such role for this login', {have});
  }
  const scoped = (path, role) => (role && role.body_cid ? withQuery(path, {body_cid: role.body_cid}) : path);

  async function rankHeaders(role) {
    if (role.public) { const k = g.env && g.env.SERVICES_API_PUBLIC_KEY; if (!k) throw err('NO_PUBLIC_KEY', 'Open any portal page that defines window.env, then retry'); return {'X-API-Token': k}; }
    const t = await getJson(scoped('/ranking_module/access_token', role));
    return Object.fromEntries(['X-API-Token', 'X-Ranking-Access-Token'].filter((k) => t[k]).map((k) => [k, t[k]]));
  }

  // Route-specific references: a catalogue entry names which id may be read from which link, and nothing else of the URL is returned.
  const DIGITS = /^\d{1,12}$/;
  const refFrom = (specs, kind, link) => {
    const out = {};
    let u; try { u = new URL(String(link), origin() + '/'); } catch (e) { return out; }
    if (u.origin !== origin()) return out;
    for (const s of specs || []) {
      if (s.from !== kind) continue;
      if (kind === 'action' && s.match) { const m = new RegExp(s.match).exec(u.pathname); if (m && DIGITS.test(m[1] || '')) out[s.name] = m[1]; }
      if (kind === 'tab' && s.query) { const all = u.searchParams.getAll(s.query); if (all.length === 1 && DIGITS.test(all[0])) out[s.name] = all[0]; }
    }
    return out;
  };
  const cells = (row, specs) => {
    const o = {};
    for (const [k, v] of Object.entries(row)) if (k !== 'action' && k !== 'actions_description') o[k] = v;
    if (Array.isArray(row.action)) {
      o.actions = row.action.map((a) => a.text || a.type).filter(Boolean);
      const refs = Object.assign({}, ...row.action.map((a) => (a && typeof a.url === 'string' ? refFrom(specs, 'action', a.url) : {})));
      if (Object.keys(refs).length) o.refs = refs;
    }
    return o;
  };
  const isTable = (d) => d && Array.isArray(d.columns) && 'data_url' in d;
  async function table(url, o, hdr) {
    const d = await getJson(url, {headers: hdr});
    if (!isTable(d)) throw err('NOT_A_TABLE', 'The endpoint is not a datatable descriptor', {path: qnames(url), keys: Object.keys(d).slice(0, 12)});
    // The rows come from the host that served the descriptor, never from another origin.
    const dataUrl = toUrl(d.data_url, absolute(url)).href;
    if (new URL(dataUrl).origin !== new URL(absolute(url)).origin) throw err('UNEXPECTED_ORIGIN', 'The table points its rows at another host; nothing was sent', {path: qnames(dataUrl)});
    const known = (d.filters || []).map((f) => f.name);
    const filters = o.filters || {};
    if (!d.has_advanced_filter) { const bad = Object.keys(filters).filter((k) => !known.includes(k)); if (bad.length) throw err('UNKNOWN_FILTER', 'Unknown filter: ' + bad.join(', '), {have: known}); }
    // A select or autocomplete filter whose items carry numeric values takes the number, not its string form.
    const ftype = Object.fromEntries((d.filters || []).map((f) => [f.name, f]));
    const numeric = (f) => !!f && OPTION_TYPES.includes(f.type) && Array.isArray(f.items) && f.items.length > 0 && typeof f.items[0].value === 'number';
    const typed = Object.fromEntries(Object.entries(filters).map(([k, v]) => [k, numeric(ftype[k]) && typeof v === 'string' && /^-?\d+$/.test(v) ? Number(v) : v]));
    const body = {columns: [], filters: d.has_advanced_filter ? (Array.isArray(o.filters) ? o.filters : []) : typed};
    const maxRows = o.maxRows === undefined ? 50 : o.maxRows;
    const l = Math.max(1, Math.min(o.perPage || d.items_per_page || 20, maxRows || 1));
    const start = (o.page || 1) - 1;
    const call = (p) => getJson(dataUrl + (dataUrl.includes('?') ? '&' : '?') + Object.entries({p, l, sort: o.sort || '', d: o.sort ? (o.desc ? 'des' : 'asc') : '', s: o.search || '', st: o.searchType || ''}).map(([k, v]) => k + '=' + encodeURIComponent(v)).join('&'), {method: 'POST', json: body, headers: hdr});
    const rows = []; let total = null; let fetched = 0; let more = false;
    for (let n = 0; n < Math.max(1, Math.ceil(maxRows / l)); n++) {
      const r = await call(start + n); total = r.total; fetched += 1;
      if (maxRows > 0) rows.push(...(r.data || []).map((x) => cells(x, o.refSpecs)));
      more = maxRows > 0 && (r.data || []).length > 0 && rows.length < total;
      if (!more) break;
      await sleep(150);
    }
    const keep = o.fields && o.fields.length ? o.fields : null;
    const out = rows.map((r) => (keep ? Object.fromEntries(keep.filter((k) => k in r).map((k) => [k, r[k]])) : r));
    return {title: d.title, total, returned: out.length, complete: total !== null && out.length >= total, next: more ? {page: start + fetched + 1, perPage: l} : null,
      hint: total === 0 && typeof o.emptyHint === 'string' ? o.emptyHint : undefined,
      columns: d.columns.map((c) => ({key: c.value, label: c.text, sortable: !!c.sortable})), filters: (d.filters || []).map((f) => ({name: f.name, type: f.type, label: f.label})), buttons: (d.top_buttons || []).map((b) => b.label || b.text || b.type), rows: out};
  }
  // The values a reviewed select or autocomplete filter accepts, from the descriptor only (no rows are requested), at most 50 per call.
  const scalar = (v) => (typeof v === 'string' || typeof v === 'number') && String(v).length <= 120;
  async function tableOptions(url, o, hdr) {
    const d = await getJson(url, {headers: hdr});
    if (!isTable(d)) throw err('NOT_A_TABLE', 'The endpoint is not a datatable descriptor', {path: qnames(url), keys: Object.keys(d).slice(0, 12)});
    const all = d.filters || [];
    const f = all.find((x) => x.name === o.options);
    if (!f) throw err('UNKNOWN_FILTER', 'Unknown filter: ' + o.options, {have: all.map((x) => x.name)});
    if (!OPTION_TYPES.includes(f.type)) throw err('BAD_PARAM', 'Filter ' + f.name + ' has no options (type ' + f.type + ')', {have: all.filter((x) => OPTION_TYPES.includes(x.type)).map((x) => x.name)});
    if (!Array.isArray(f.items)) return {title: d.title, options: {filter: f.name, type: f.type, available: false, note: 'The descriptor carries no inline items for this filter'}};
    const uuid1 = new RegExp(UUID.source, 'i');
    let skipped = 0; const items = [];
    for (const i of f.items) {
      const text = i && typeof i === 'object' ? (i.text !== undefined ? i.text : i.label) : i;
      const value = i && typeof i === 'object' ? (i.value !== undefined ? i.value : i.id) : i;
      if (!scalar(text) || !scalar(value) || uuid1.test(String(text) + ' ' + String(value))) { skipped += 1; continue; }
      items.push({text: String(text), value});
    }
    const q = String(o.optionSearch || '').toLowerCase();
    const hit = q ? items.filter((i) => i.text.toLowerCase().includes(q)) : items;
    const cap = Math.min(OPTION_CAP, o.maxRows > 0 ? o.maxRows : OPTION_CAP);
    return {title: d.title, options: {filter: f.name, type: f.type, available: true, matching: hit.length, of: items.length, skipped, returned: Math.min(hit.length, cap), complete: hit.length <= cap, items: hit.slice(0, cap)}};
  }

  const flatTabs = (tabs, trail) => (tabs || []).flatMap((t) => { const here = (trail || []).concat(t.title); return [{path: here, tab: t}].concat(flatTabs(t.subtypes, here)); });
  const tabUrl = (t) => (t.vue_component_data && t.vue_component_data.url) || t.url || null;
  async function tabs(url, hdr, specs) {
    const j = await getJson(url, {headers: hdr});
    return {name: j.name || null, buttons: (j.buttons || []).map((b) => b.label || b.text || b.type), tabs: flatTabs(j.tabs).map((x) => {
      const raw = tabUrl(x.tab); const refs = raw ? refFrom(specs, 'tab', raw) : {};
      return Object.assign({title: x.path.join(' > '), kind: x.tab.vue_component || x.tab.type, url: raw ? qnames(raw) : null}, Object.keys(refs).length ? {refs} : {});
    })};
  }

  const shape = (v, d) => (v === null ? 'null' : Array.isArray(v) ? 'array[' + v.length + ']' + (v.length && d < 2 ? '<' + JSON.stringify(shape(v[0], d + 1)) + '>' : '') : typeof v === 'object' ? (d >= 2 ? '{' + Object.keys(v).slice(0, 12).join(',') + '}' : Object.fromEntries(Object.entries(v).slice(0, 24).map(([k, x]) => [k, shape(x, d + 1)]))) : typeof v);
  const unesc = (s) => s.replace(/&quot;/g, '"').replace(/&#0?39;/g, "'").replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&amp;/g, '&');
  const strip = (s) => s.replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ').trim();
  const fieldsOf = (form) => { const f = form && form.fields; const list = Array.isArray(f) ? f : f && typeof f === 'object' ? Object.entries(f).map(([k, v]) => Object.assign({name: k}, typeof v === 'object' ? v : {})) : []; const seen = new Set(); return list.map((x) => ({name: String(x.name || x.id || '').replace(/\d{3,}/g, '#'), type: x.type || null})).filter((x) => x.name && !/(^|\[)_?(csrf_)?token\]?$/i.test(x.name) && !seen.has(x.name) && seen.add(x.name)); };
  const trim = (v, fields) => (Array.isArray(v) ? v.map((x) => trim(x, fields)) : v && typeof v === 'object' && fields ? Object.fromEntries(Object.entries(v).filter(([k]) => fields.includes(k))) : v);
  function outline(r, o) {
    const pick = (o && o.pick) || []; const fields = o && o.fields && o.fields.length ? o.fields : null;
    if (r.ctype.includes('json')) {
      const j = parse(r.text, 'json');
      const data = pick.length ? Object.fromEntries(pick.filter((k) => k in j).map((k) => [k, trim(j[k], fields)])) : trim(j, fields);
      return JSON.stringify(data).length > ((o && o.maxChars) || 12000) ? {protocol: 'json', truncated: true, shape: shape(j, 0), note: 'Too large to return: pick keys (pick) or name fields (fields)'} : {protocol: 'json', data};
    }
    const m = /data-page="([^"]*)"/.exec(r.text);
    if (m) {
      const p = parse(unesc(m[1]), 'page'); const props = p.props || {}; const keys = Object.keys(props).filter((k) => k !== '_shared');
      return {protocol: 'inertia', component: p.component, propKeys: keys, formFields: fieldsOf(props.form), datatableUrl: props.datatable_url ? qnames(props.datatable_url) : null,
        shape: pick.length ? undefined : Object.fromEntries(keys.map((k) => [k, shape(props[k], 1)])), props: pick.length ? Object.fromEntries(pick.filter((k) => k in props).map((k) => [k, trim(props[k], fields)])) : undefined};
    }
    const all = (re) => [...r.text.matchAll(re)].map((x) => strip(x[1]).slice(0, 40)).filter(Boolean);
    return {protocol: 'html', headings: all(/<h[1-4][^>]*>([\s\S]*?)<\/h[1-4]>/gi).slice(0, 8), tableHeaders: all(/<th[^>]*>([\s\S]*?)<\/th>/gi).slice(0, 16), buttons: all(/<button[^>]*>([\s\S]*?)<\/button>/gi).slice(0, 12), forms: (r.text.match(/<form[\s>]/gi) || []).length};
  }
  async function inspect(url, o) {
    const raw = !!(o && o.raw);
    let r;
    try { r = await http(url, {follow: !!(o && o.follow), headers: {Accept: 'application/json, text/html;q=0.8'}}); } catch (e) { if (['REDIRECTED', 'NETWORK'].includes(e.code)) throw e; return {path: qnames(url), protocol: 'error', error: e.code, status: e.status}; }
    stopOnChallenge(r, url);
    const here = {path: qnames(url)};
    if (r.ctype.includes('json')) {
      const j = parse(r.text, here.path);
      if (isTable(j)) return Object.assign(here, {protocol: 'datatable', title: j.title || null, columns: j.columns.map((c) => c.value), filters: (j.filters || []).map((f) => f.name + ':' + f.type), buttons: (j.top_buttons || []).map((b) => b.label || b.text || b.type), dataUrl: raw ? j.data_url : qnames(j.data_url)});
      if (Array.isArray(j.tabs)) return Object.assign(here, {protocol: 'tabs', tabs: flatTabs(j.tabs).map((x) => ({title: x.path.join(' > '), kind: x.tab.vue_component || x.tab.type, url: tabUrl(x.tab) ? (raw ? tabUrl(x.tab) : qnames(tabUrl(x.tab))) : null}))});
      if (j.type && j.url && Object.keys(j).length <= 4) return Object.assign(here, {protocol: 'redirect', to: raw ? j.url : qnames(j.url)});
      return Object.assign(here, {protocol: 'json', keys: Object.keys(j).slice(0, 30)});
    }
    return Object.assign(here, outline(r, {}));
  }

  const flatMenu = (items, section, trail, raw) => (items || []).flatMap((it) => {
    const t = (trail || []).concat(it.title); const d = it.vue_component_data || {};
    const u = (x) => (x ? (raw ? x : qnames(x)) : null);
    const node = {section, trail: t, type: it.type, vue: it.vue_component || null, url: u(it.url), dataUrl: u(d.url), profileUrl: u(d.profile_url), tokenUrl: u(d.access_token_url), route: it.route || null, hidden: !!it.hidden, external: it.type === 'external'};
    const subs = (it.sub_routes || []).map((s) => ({section, trail: t.concat('<' + s.title + ' params:' + Object.values(s.url_params || {}).join('+') + '>'), type: 'sub-route', vue: s.vue_component || null, dataUrl: u(s.vue_component_data && s.vue_component_data.url), needs: Object.values(s.url_params || {})}));
    return [node].concat(subs, flatMenu(it.subtypes, section, t, raw));
  });
  async function menu(sel, o) {
    const role = await pickRole(sel); const raw = !!(o && o.raw);
    const m = await getJson(scoped('/api/menu/main', role)); const a = await getJson(scoped('/api/menu/top', role));
    return {role: {type: role.type, name: role.name, cid: raw ? role.cid : undefined, body_cid: raw ? role.body_cid : undefined}, nodes: flatMenu(m.topMenu, 'top', [], raw).concat(flatMenu(m.bottomMenu, 'bottom', [], raw), flatMenu(a.data, 'account', [], raw))};
  }

  const fill = (entry, params) => {
    const miss = [];
    const path = (entry.path || '').replace(/\{(\w+)\}/g, (_, k) => { const v = params[k]; if (v === undefined || v === '') { miss.push(k); return ''; } return encodeURIComponent(v); });
    const q = Object.assign({}, entry.query || {});
    for (const p of entry.params || []) {
      if (p.in === 'filter' || p.in === 'option') continue;
      const v = params[p.name];
      if (v !== undefined && v !== '' && p.values && !p.values.includes(String(v))) throw err('BAD_PARAM', p.name + ' must be one of ' + p.values.join(', '), {have: p.values});
      if (p.in === 'query') { if (v !== undefined && v !== '') q[p.as || p.name] = v; else if (p.required) miss.push(p.name); }
      else if (p.in === 'path' && p.required && (v === undefined || v === '')) miss.push(p.name);
    }
    if (miss.length) throw err('MISSING_PARAM', 'Missing required parameter: ' + [...new Set(miss)].join(', '), {have: [...new Set(miss)]});
    return {path, q};
  };
  const withDefaults = (entry, role, params) => {
    const out = Object.assign({}, params || {});
    for (const p of entry.params || []) {
      if (out[p.name] !== undefined && out[p.name] !== '') continue;
      if (p.default === 'role.cid' && role.cid) out[p.name] = role.cid;
      else if (p.default === 'role.body_cid' && role.body_cid) out[p.name] = role.body_cid;
      else if (p.default === 'today') out[p.name] = today();
    }
    return out;
  };

  async function run(entry, o) {
    if (entry.mode && entry.mode !== 'read') throw err('NOT_RUNNABLE', 'This capability is ' + entry.mode + ': follow its confirm text instead of running it');
    if (!['datatable', 'tabs', 'page', 'html', 'json'].includes(entry.kind)) throw err('NOT_RUNNABLE', 'Kind ' + entry.kind + ' is not a read');
    const given = o.params || {};
    const early = (entry.params || []).filter((p) => p.in !== 'filter' && p.in !== 'option');
    const need = early.filter((p) => p.required && !p.default && (given[p.name] === undefined || given[p.name] === ''));
    if (need.length) throw err('MISSING_PARAM', 'Missing required parameter: ' + need.map((p) => p.name).join(', '), {have: need.map((p) => p.name)});
    for (const p of early) if (given[p.name] !== undefined && given[p.name] !== '' && p.values && !p.values.includes(String(given[p.name]))) throw err('BAD_PARAM', p.name + ' must be one of ' + p.values.join(', '), {have: p.values});
    const wantOptions = o.options !== undefined && o.options !== null && o.options !== '';
    if (wantOptions && entry.kind !== 'datatable') throw err('BAD_PARAM', 'options applies to datatable entries');
    if (wantOptions && entry.data === 'sensitive') throw err('BAD_PARAM', 'Sensitive data: filter options are not offered');
    if (wantOptions && !(entry.option_filters || []).includes(o.options)) throw err('BAD_PARAM', 'Options for filter ' + o.options + ' are not offered for this capability', {have: entry.option_filters || []});
    const filters = o.filters || {};
    if (!wantOptions && entry.requires_filter && entry.requires_filter.length && !entry.requires_filter.some((k) => present(filters[k]))) throw err('FILTER_REQUIRED', 'Give at least one filter: ' + entry.requires_filter.join(', '), {have: entry.requires_filter});
    const sensitive = entry.data === 'sensitive';
    const rows = o.maxRows === undefined ? (sensitive ? 0 : 50) : o.maxRows;
    if (sensitive && rows > 0 && !(o.fields && o.fields.length) && entry.kind === 'datatable') throw err('FIELDS_REQUIRED', 'Sensitive data: name the fields to return (fields) or ask for counts only (maxRows 0)');
    if (sensitive && entry.kind !== 'datatable' && ((o.pick && o.pick.length) || entry.kind === 'json') && !(o.fields && o.fields.length)) throw err('FIELDS_REQUIRED', 'Sensitive data: name the exact fields to return (fields)');
    const rank = entry.host === 'rankings';
    const needsLogin = !(rank && entry.auth === 'public' && !entry.via);
    const sel = o.role || entry.defaultRole || 'personal';
    const publicRead = !needsLogin || (sel === 'public' && !entry.via);
    const role = publicRead ? PUBLIC : await pickRole(sel === 'public' ? 'personal' : sel);
    const params = withDefaults(entry, role, o.params);
    const base = g.env && g.env.RANKINGS_DOMAIN_URL;
    if (rank && !base) throw err('NO_RANKINGS_HOST', 'Open any portal page that defines window.env, then retry');
    let url; let hdr = {};
    if (entry.via) {
      const cid = entry.via.param ? params[entry.via.param] : undefined;
      if (entry.via.param && (cid === undefined || cid === '')) throw err('MISSING_PARAM', 'Missing required parameter: ' + entry.via.param, {have: [entry.via.param]});
      const tj = await getJson(scoped(withQuery(entry.via.tabs, Object.assign({}, entry.via.query || {}, entry.via.param ? {[entry.via.param]: cid} : {})), role));
      const want = entry.via.match.join(' > ');
      const hit = flatTabs(tj.tabs).find((x) => x.path.join(' > ') === want);
      if (!hit || !tabUrl(hit.tab)) throw err('TAB_NOT_FOUND', 'Tab not present for this role and record: ' + want, {have: flatTabs(tj.tabs).map((x) => x.path.join(' > '))});
      url = absolute(tabUrl(hit.tab));
    } else {
      const f = fill(entry, params);
      url = (rank ? base : '') + (rank ? withQuery(f.path, f.q) : scoped(withQuery(f.path, f.q), entry.scope === 'body' ? role : null));
    }
    if (rank) hdr = await rankHeaders(entry.auth === 'public' ? PUBLIC : role);
    if (wantOptions) return {role, result: await tableOptions(url, o, hdr)};
    if (entry.kind === 'datatable') {
      const t = await table(url, Object.assign({}, o, {maxRows: rows, refSpecs: entry.refs, emptyHint: entry.empty_hint}), hdr);
      return {role, result: t, note: sensitive && rows === 0 ? 'Sensitive data: rows withheld; total and columns only. Pass maxRows and fields to read rows.' : undefined};
    }
    if (entry.kind === 'tabs') return {role, result: await tabs(url, hdr, entry.refs)};
    const r = stopOnChallenge(await http(url, {headers: Object.assign({Accept: 'application/json, text/html;q=0.8'}, hdr)}), url);
    return {role, result: outline(r, o)};
  }

  const plain = (s) => s.replace(/\?/g, '[?]').replace(/&/g, '[&]').replace(/=/g, '[=]');
  // Defence in depth for any string in a result: UUIDs and the values of secret-looking query parameters never leave the page.
  const SECRET_Q = /([?&](?:token|access_token|auth|authorization|api_?key|key|secret|password|passwd|signature|sig|session|session_?id|jwt|code|x-amz-[a-z0-9-]+|expires)=)[^&\s"'<>]*/gi;
  const finish = (v, o) => JSON.parse(JSON.stringify(v, (k, x) => { if (typeof x !== 'string') return x; const s = x.replace(UUID, '<uuid>').replace(SECRET_Q, '$1<redacted>'); return o.plain ? plain(s) : s; }));
  function bound(res, max) {
    let s = JSON.stringify(res); const r = res.result;
    while (s.length > max && r && Array.isArray(r.rows) && r.rows.length > 1) { r.rows = r.rows.slice(0, Math.ceil(r.rows.length / 2)); r.returned = r.rows.length; r.complete = false; r.next = null; res.note = 'Rows cut to fit the output limit; narrow with filters or fields'; s = JSON.stringify(res); }
    while (s.length > max && r && r.options && Array.isArray(r.options.items) && r.options.items.length > 1) { r.options.items = r.options.items.slice(0, Math.ceil(r.options.items.length / 2)); r.options.returned = r.options.items.length; r.options.complete = false; res.note = 'Options cut to fit the output limit; narrow with optionSearch'; s = JSON.stringify(res); }
    // A single row or option that alone exceeds the limit is dropped rather than returned over it.
    if (s.length > max && r && Array.isArray(r.rows) && r.rows.length === 1) { r.rows = []; r.returned = 0; r.complete = false; r.next = null; res.note = 'One row alone exceeds the output limit; name fewer fields'; s = JSON.stringify(res); }
    if (s.length > max && r && r.options && Array.isArray(r.options.items) && r.options.items.length === 1) { r.options.items = []; r.options.returned = 0; r.options.complete = false; res.note = 'One option alone exceeds the output limit'; }
    return res;
  }
  async function exec(entry, opts) {
    const o = opts || {};
    try {
      const out = await guard(() => run(entry, o));
      return bound(finish({ok: true, id: entry.id, role: {type: out.role.type, name: out.role.name}, verified: entry.verified || null, result: out.result, note: out.note}, o), o.maxChars || 12000);
    } catch (e) {
      return finish({ok: false, id: entry && entry.id, error: e.code || 'ERROR', message: e.message, status: e.status, path: e.path, have: e.have}, o);
    }
  }
  const show = (v) => { const s = JSON.stringify(v, null, 1); g.document.body.innerText = s; return s.length; };
  g.S80 = {version: 2, roles, exec, ping, show, inspect: async (u, o) => finish(await guard(() => inspect(u, o)), o || {}), menu: async (s, o) => finish(await guard(() => menu(s, o)), o || {})};
  return 'S80 runtime loaded (v2)';
})()
