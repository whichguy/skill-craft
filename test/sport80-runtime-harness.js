#!/usr/bin/env node
"use strict";

/**
 * Scenario harness for skills/sport80/scripts/runtime.js and the generated discover.js.
 * It runs them in a vm context against a fake portal and rankings host and prints one JSON array of
 * {name, ok, error} results. test/sport80.test.py turns each into a subtest.
 * A fake fetch pins request construction and result handling only: it cannot prove browser CORS, cookie
 * behaviour or portal compatibility, which the journal records from consented live smoke checks.
 */
const assert = require("assert");
const path = require("path");
const fs = require("fs");
const vm = require("vm");
const { execFileSync } = require("child_process");

const ROOT = path.join(__dirname, "..", "skills", "sport80");
const CLI = path.join(ROOT, "scripts", "sport80");
const RUNTIME = fs.readFileSync(path.join(ROOT, "scripts", "runtime.js"), "utf8");
const SECRET = { xsrf: "XSRF-SENTINEL-AAA", pub: "PUBKEY-SENTINEL-BBB", tokA: "TOKEN-SENTINEL-CCC", tokB: "TOKEN-SENTINEL-DDD" };
const ORIGIN = "https://portal.test";
const RANK = "https://rank.test";
const everything = [];
// Objects built inside the vm context carry another realm's prototypes, so compare plain data through JSON.
const J = (x) => JSON.parse(JSON.stringify(x === undefined ? null : x));
const eq = (a, b, m) => assert.deepStrictEqual(J(a), J(b), m);

const roleBody = { accounts: { accounts: [
  { type: "Personal", name: "Pat Example", cid: 101, body_cid: null },
  { type: "Club", name: "Example Barbell Club", cid: 202, body_cid: 202 }] } };
const descriptor = (title, cols, dataUrl, extra) => Object.assign({
  title, paginated: true, items_per_page: 2, has_search: true, has_filters: true,
  columns: cols.map((c) => ({ value: c, text: c.toUpperCase(), sortable: c === "name" })),
  filters: [{ name: "first_name", type: "text", label: "First" }], top_buttons: [{ label: "Add Thing" }], data_url: dataUrl }, extra || {});
const pageRows = (all) => (u) => {
  const p = Number(u.searchParams.get("p")); const l = Number(u.searchParams.get("l"));
  return { json: { total: all.length, page: p, items_per_page: l, data: all.slice(p * l, p * l + l) } };
};

function world(routes) {
  const calls = []; const logs = [];
  const fakeFetch = async (url, init) => {
    init = init || {};
    const u = new URL(url, ORIGIN);
    calls.push({ url, path: u.pathname, search: u.search, host: u.origin, method: init.method || "GET", headers: init.headers || {}, body: init.body, credentials: init.credentials, redirect: init.redirect });
    const r = await routes(u, init, calls);
    if (r === "throw") throw new TypeError("Failed to fetch");
    return {
      type: r.type || "basic", status: r.status === undefined ? 200 : r.status,
      headers: { get: (h) => (h.toLowerCase() === "content-type" ? r.ctype || (r.json !== undefined ? "application/json" : "text/html") : null) },
      text: async () => (r.json !== undefined ? JSON.stringify(r.json) : r.text || ""),
      json: async () => JSON.parse(r.json !== undefined ? JSON.stringify(r.json) : r.text || ""),
    };
  };
  const sandbox = {
    fetch: fakeFetch, location: { origin: ORIGIN, host: "portal.test" }, URL, setTimeout: (f) => setImmediate(f),
    document: { cookie: "a=1; XSRF-TOKEN=" + encodeURIComponent(SECRET.xsrf) + "; b=2", body: {} },
    env: { RANKINGS_DOMAIN_URL: RANK, SERVICES_API_PUBLIC_KEY: SECRET.pub },
    console: { log: (...a) => { logs.push(a.join(" ")); everything.push(a.join(" ")); }, error: (...a) => { logs.push(a.join(" ")); everything.push(a.join(" ")); }, warn: (...a) => { logs.push(a.join(" ")); everything.push(a.join(" ")); } },
  };
  vm.createContext(sandbox);
  vm.runInContext(RUNTIME, sandbox);
  const run = async (entry, opts) => { const r = await sandbox.S80.exec(entry, opts); everything.push(JSON.stringify(r)); return r; };
  return { S80: sandbox.S80, calls, logs, sandbox, run };
}
const std = (extra) => (u, init, calls) => {
  if (u.pathname === "/api/account/roles") return { json: roleBody };
  if (u.pathname === "/ranking_module/access_token") return { json: { "X-API-Token": SECRET.tokA, "X-Ranking-Access-Token": SECRET.tokB } };
  return extra ? extra(u, init, calls) : { status: 404, json: {} };
};
const tableEntry = (over) => Object.assign({ id: "t.table", kind: "datatable", mode: "read", data: "personal", path: "/api/things/datatable", scope: "body", verified: "live" }, over || {});
const people = [{ id: 1, name: "a", action: [{ text: "View" }] }, { id: 2, name: "b" }, { id: 3, name: "c" }, { id: 4, name: "d" }, { id: 5, name: "e" }];

const results = [];
async function test(name, fn) {
  try { await fn(); results.push({ name, ok: true }); }
  catch (e) { results.push({ name, ok: false, error: String((e && e.stack) || e).split("\n").slice(0, 4).join(" | ") }); }
}

(async () => {
  await test("roles lists the personal and club roles", async () => {
    const w = world(std());
    const r = await w.S80.roles();
    eq(r.map((x) => x.type), ["Personal", "Club"]);
    assert.strictEqual(r[1].body_cid, 202);
  });

  await test("datatable: descriptor GET, then row POST with the SPA's headers, zero-based p and the JSON body", async () => {
    const w = world(std((u) => (u.pathname === "/api/things/datatable" ? { json: descriptor("Things", ["name"], ORIGIN + "/api/things/data?data=1") } : u.pathname === "/api/things/data" ? pageRows(people)(u) : { status: 404, json: {} })));
    const r = await w.run(tableEntry(), { role: "personal", maxRows: 2, filters: { first_name: "Al" }, search: "x y", sort: "name", desc: true });
    assert.strictEqual(r.ok, true);
    const get = w.calls.find((c) => c.path === "/api/things/datatable");
    assert.strictEqual(get.method, "GET"); assert.strictEqual(get.redirect, "manual"); assert.strictEqual(get.credentials, "same-origin");
    assert.strictEqual(get.headers["X-Requested-With"], "XMLHttpRequest"); assert.strictEqual(get.headers["X-Keep-Session"], "keepsession");
    const post = w.calls.find((c) => c.path === "/api/things/data");
    assert.strictEqual(post.method, "POST");
    const q = new URL(post.url).searchParams;
    eq([q.get("data"), q.get("p"), q.get("l"), q.get("sort"), q.get("d"), q.get("s"), q.get("st")], ["1", "0", "2", "name", "des", "x y", ""]);
    eq(JSON.parse(post.body), { columns: [], filters: { first_name: "Al" } });
    assert.strictEqual(post.headers["X-XSRF-TOKEN"], SECRET.xsrf);
    assert.strictEqual(post.headers["Content-Type"], "application/json");
    assert.strictEqual(r.result.rows[0].actions[0], "View");
    assert.ok(!("action" in r.result.rows[0]));
  });

  await test("paging is zero-based, whole pages, and says when it is partial", async () => {
    const w = world(std((u) => (u.pathname === "/api/things/datatable" ? { json: descriptor("Things", ["name"], ORIGIN + "/api/things/data") } : pageRows(people)(u))));
    const part = await w.run(tableEntry(), { maxRows: 4 });
    eq(w.calls.filter((c) => c.method === "POST").map((c) => new URL(c.url).searchParams.get("p")), ["0", "1"]);
    assert.strictEqual(part.result.returned, 4); assert.strictEqual(part.result.total, 5);
    assert.strictEqual(part.result.complete, false); eq(part.result.next, { page: 3, perPage: 2 });
    const rest = await w.run(tableEntry(), { maxRows: 4, page: 3 });
    assert.strictEqual(rest.result.returned, 1); assert.strictEqual(rest.result.complete, false); assert.strictEqual(rest.result.next, null);
    const all = await w.run(tableEntry(), { maxRows: 10 });
    assert.strictEqual(all.result.returned, 5); assert.strictEqual(all.result.complete, true); assert.strictEqual(all.result.next, null);
    const small = await w.run(tableEntry(), { maxRows: 1 });
    assert.strictEqual(small.result.returned, 1); eq(small.result.next, { page: 2, perPage: 1 });
  });

  await test("club scope adds body_cid to the descriptor only; the server's data_url is used as given", async () => {
    const w = world(std((u) => (u.pathname === "/api/things/datatable" ? { json: descriptor("Things", ["name"], ORIGIN + "/api/things/data?body_cid=202&data=1") } : pageRows(people)(u))));
    await w.run(tableEntry(), { role: "club", maxRows: 1 });
    assert.strictEqual(new URL(w.calls.find((c) => c.path === "/api/things/datatable").url).searchParams.get("body_cid"), "202");
    const post = w.calls.find((c) => c.path === "/api/things/data");
    assert.strictEqual(new URL(post.url).searchParams.getAll("body_cid").length, 1);
    await w.run(tableEntry(), { role: "personal", maxRows: 1 });
    assert.ok(!new URL(w.calls.filter((c) => c.path === "/api/things/datatable").pop().url).searchParams.has("body_cid"));
  });

  await test("sensitive data: counts only by default, fields required for rows, only those fields returned", async () => {
    const w = world(std((u) => (u.pathname === "/api/things/datatable" ? { json: descriptor("Things", ["name", "email"], ORIGIN + "/api/things/data") } : pageRows(people.map((p) => Object.assign({ email: p.name + "@x.test" }, p)))(u))));
    const e = tableEntry({ data: "sensitive" });
    const counts = await w.run(e, {});
    assert.strictEqual(counts.ok, true); assert.strictEqual(counts.result.total, 5); assert.strictEqual(counts.result.returned, 0);
    eq(counts.result.rows, []); assert.match(counts.note, /withheld/);
    assert.strictEqual(w.calls.filter((c) => c.method === "POST").length, 1);
    assert.strictEqual(new URL(w.calls.filter((c) => c.method === "POST")[0].url).searchParams.get("l"), "1");
    const before = w.calls.length;
    const refused = await w.run(e, { maxRows: 3 });
    assert.strictEqual(refused.error, "FIELDS_REQUIRED"); assert.strictEqual(w.calls.length, before);
    const some = await w.run(e, { maxRows: 3, fields: ["name"] });
    eq(Object.keys(some.result.rows[0]), ["name"]);
    assert.ok(!JSON.stringify(some).includes("@x.test"));
  });

  await test("refusals happen before any request: missing filter, missing and bad parameters", async () => {
    const w = world(std());
    const search = tableEntry({ id: "t.search", params: [{ name: "first_name", in: "filter", type: "text" }], requires_filter: ["first_name"] });
    assert.strictEqual((await w.run(search, { role: "club" })).error, "FILTER_REQUIRED");
    const typed = tableEntry({ id: "t.typed", path: "/x/{type}/y", params: [{ name: "type", in: "path", required: true, values: ["a", "b"] }, { name: "eid", in: "query", required: true }] });
    assert.strictEqual((await w.run(typed, {})).error, "MISSING_PARAM");
    assert.strictEqual((await w.run(typed, { params: { type: "zzz", eid: "1" } })).error, "BAD_PARAM");
    assert.strictEqual(w.calls.length, 0);
  });

  await test("an unknown filter is refused before any row is requested", async () => {
    const w = world(std((u) => (u.pathname === "/api/things/datatable" ? { json: descriptor("Things", ["name"], ORIGIN + "/api/things/data") } : pageRows(people)(u))));
    const r = await w.run(tableEntry(), { filters: { bogus: "1" } });
    assert.strictEqual(r.error, "UNKNOWN_FILTER"); eq(r.have, ["first_name"]);
    assert.strictEqual(w.calls.filter((c) => c.method === "POST").length, 0);
  });

  await test("rankings token flow: club token, per-origin headers, no secret in any result", async () => {
    const w = world(std((u) => (u.origin === RANK && u.pathname === "/api/events/table" ? { json: descriptor("Events", ["meet", "results"], RANK + "/api/events/table/data?platform=1", { filters: [{ name: "date_range_start", type: "datepicker" }] }) } : u.origin === RANK ? pageRows([{ meet: "m1", results: 3 }, { meet: "m2", results: 4 }])(u) : { status: 404, json: {} })));
    const e = { id: "r.events", kind: "datatable", mode: "read", data: "public", path: "/api/events/table", query: { platform: "1" }, scope: "none", host: "rankings", auth: "role", defaultRole: "public" };
    const r = await w.run(e, { role: "club", maxRows: 10, filters: { date_range_start: "2026-01-01" } });
    assert.strictEqual(r.ok, true); assert.strictEqual(r.result.total, 2);
    const tok = w.calls.find((c) => c.path === "/ranking_module/access_token");
    assert.strictEqual(new URL(tok.url).searchParams.get("body_cid"), "202");
    const rank = w.calls.filter((c) => c.host === RANK);
    assert.ok(rank.length >= 2);
    for (const c of rank) {
      assert.strictEqual(c.headers["X-API-Token"], SECRET.tokA); assert.strictEqual(c.headers["X-Ranking-Access-Token"], SECRET.tokB);
      assert.ok(!("X-XSRF-TOKEN" in c.headers) && !("X-Requested-With" in c.headers)); assert.strictEqual(c.credentials, "omit");
    }
    for (const c of w.calls.filter((x) => x.host === ORIGIN)) assert.ok(!("X-API-Token" in c.headers));
    assert.ok(!JSON.stringify(r).includes("SENTINEL"));
  });

  await test("a public rankings read needs no login: no roles call, only the public key header", async () => {
    const w = world(std((u) => (u.pathname === "/api/events/9/table" ? { json: descriptor("Results", ["lifter"], RANK + "/api/events/9/table/data") } : pageRows([{ lifter: "x" }])(u))));
    const e = { id: "r.event", kind: "datatable", mode: "read", data: "personal", path: "/api/events/{event_id}/table", scope: "none", host: "rankings", auth: "public", params: [{ name: "event_id", in: "path", required: true }], defaultRole: "public" };
    const r = await w.run(e, { params: { event_id: "9" }, maxRows: 5 });
    assert.strictEqual(r.ok, true); assert.strictEqual(r.role.type, "Public");
    assert.ok(!w.calls.some((c) => c.host === ORIGIN));
    assert.ok(w.calls.every((c) => c.headers["X-API-Token"] === SECRET.pub));
    assert.ok(!JSON.stringify(r).includes("SENTINEL"));
  });

  await test("failure taxonomy: permission, forbidden, server, network, auth, redirect", async () => {
    const entry = tableEntry();
    // 401 with a live session is a permission problem, not a login problem
    let w = world((u) => (u.pathname === "/api/account/roles" ? { json: roleBody } : { status: 401, json: {} }));
    assert.strictEqual((await w.run(entry, {})).error, "PERMISSION_DENIED");
    // 403 and 500 are reported as they are, with no login guess
    w = world((u) => (u.pathname === "/api/account/roles" ? { json: roleBody } : { status: 403, json: {} }));
    assert.strictEqual((await w.run(entry, {})).error, "FORBIDDEN");
    assert.strictEqual(w.calls.filter((c) => c.path === "/api/account/roles").length, 1);
    w = world((u) => (u.pathname === "/api/account/roles" ? { json: roleBody } : { status: 500, json: {} }));
    assert.strictEqual((await w.run(entry, {})).error, "SERVER");
    // a redirect while the roles ping also redirects means the session ended
    w = world(() => ({ type: "opaqueredirect", status: 0 }));
    const lost = await w.run(entry, {});
    assert.strictEqual(lost.error, "AUTH_REQUIRED");
    // a redirect while the session is alive is unexpected, not a login problem
    w = world((u) => (u.pathname === "/api/account/roles" ? { json: roleBody } : { type: "opaqueredirect", status: 0 }));
    assert.strictEqual((await w.run(entry, {})).error, "UNEXPECTED_REDIRECT");
    // a bare network error with a live session stays a network error
    w = world((u) => (u.pathname === "/api/account/roles" ? { json: roleBody } : "throw"));
    assert.strictEqual((await w.run(entry, {})).error, "NETWORK");
    // a network error with no session is AUTH_REQUIRED
    w = world(() => "throw");
    assert.strictEqual((await w.run(entry, {})).error, "AUTH_REQUIRED");
  });

  await test("a rankings 401 with a live session is RANKINGS_REFUSED, and no token leaks into the error", async () => {
    const w = world(std((u) => (u.origin === RANK ? { status: 401, json: { detail: "bad " + SECRET.tokA } } : { status: 404, json: {} })));
    const e = { id: "r.events", kind: "datatable", mode: "read", data: "public", path: "/api/events/table", scope: "none", host: "rankings", auth: "role", defaultRole: "public" };
    const r = await w.run(e, { role: "club" });
    assert.strictEqual(r.error, "RANKINGS_REFUSED");
    assert.ok(!JSON.stringify(r).includes("SENTINEL"));
  });

  await test("a bot challenge and a throttle stop the run with no retry", async () => {
    let w = world(std(() => ({ text: "<html>please solve this captcha</html>" })));
    assert.strictEqual((await w.run(tableEntry(), {})).error, "CHALLENGE");
    w = world(std(() => ({ status: 429, json: {} })));
    assert.strictEqual((await w.run(tableEntry(), {})).error, "THROTTLED");
    assert.strictEqual(w.calls.filter((c) => c.path === "/api/things/datatable").length, 1);
  });

  await test("tab-resolved entries: nested tab path, default record id from the role, missing tab named", async () => {
    const tabsBody = { tabs: [
      { title: "Profile", vue_component: "x", vue_component_data: { url: ORIGIN + "/p?cid=101" } },
      { title: "Results & Rankings", type: "parent", subtypes: [{ title: "Results", vue_component: "s80-datatable", vue_component_data: { url: RANK + "/api/athletes/55/table?platform=1" } }] },
      { title: "Memberships", vue_component: "s80-datatable", vue_component_data: { url: ORIGIN + "/add_on_portal/t?cid=101&id_cat=5" } }] };
    const w = world(std((u) => {
      if (u.pathname === "/competitor_dashboard/profile_tabs") return { json: tabsBody };
      if (u.pathname === "/add_on_portal/t") return { json: descriptor("Memberships", ["add_on"], ORIGIN + "/add_on_portal/t/data?data=1") };
      if (u.pathname === "/add_on_portal/t/data") return pageRows([{ add_on: "m" }])(u);
      if (u.pathname === "/api/athletes/55/table") return { json: descriptor("Results", ["lifter"], RANK + "/api/athletes/55/table/data") };
      if (u.pathname === "/api/athletes/55/table/data") return pageRows([{ lifter: "z" }, { lifter: "y" }])(u);
      return { status: 404, json: {} };
    }));
    const cid = { name: "cid", in: "query", required: true, default: "role.cid" };
    const via = (match, extra) => Object.assign({ id: "m.x", kind: "datatable", mode: "read", data: "personal", scope: "body", via: { tabs: "/competitor_dashboard/profile_tabs", param: "cid", match }, params: [cid] }, extra || {});
    const mem = await w.run(via(["Memberships"]), { role: "personal", maxRows: 5 });
    assert.strictEqual(mem.result.total, 1);
    assert.strictEqual(new URL(w.calls.find((c) => c.path === "/competitor_dashboard/profile_tabs").url).searchParams.get("cid"), "101");
    const res = await w.run(via(["Results & Rankings", "Results"], { host: "rankings", auth: "public" }), { role: "personal", maxRows: 5 });
    assert.strictEqual(res.result.total, 2);
    assert.strictEqual(w.calls.filter((c) => c.path === "/api/athletes/55/table").pop().headers["X-API-Token"], SECRET.pub);
    const none = await w.run(via(["Nope"]), { role: "personal" });
    assert.strictEqual(none.error, "TAB_NOT_FOUND"); assert.ok(none.have.includes("Memberships"));
  });

  await test("pages: Inertia component and prop keys, form fields without the csrf token, sensitive pick needs fields", async () => {
    const page = { component: "Fin/Report", props: { _shared: { x: 1 }, title: "T", form: { fields: [{ name: "from", type: "date" }, { name: "csrf_token", type: "hidden" }] }, secretish: { name: "n", email: "e" } } };
    const html = '<div id="app" data-page="' + JSON.stringify(page).replace(/"/g, "&quot;") + '"></div>';
    const w = world(std(() => ({ text: html })));
    const e = { id: "p.page", kind: "page", mode: "read", data: "personal", path: "/fin/report", scope: "none" };
    const shape = await w.run(e, {});
    assert.strictEqual(shape.result.component, "Fin/Report"); eq(shape.result.propKeys, ["title", "form", "secretish"]);
    eq(shape.result.formFields.map((f) => f.name), ["from"]); assert.ok(!JSON.stringify(shape).includes("csrf_token"));
    assert.ok(!JSON.stringify(shape).includes('"e"'));
    const picked = await w.run(e, { pick: ["secretish"], fields: ["name"] });
    eq(picked.result.props, { secretish: { name: "n" } });
    const sens = await w.run(Object.assign({}, e, { data: "sensitive" }), { pick: ["secretish"] });
    assert.strictEqual(sens.error, "FIELDS_REQUIRED");
  });

  await test("html fragments: headings, table headers, buttons, form count", async () => {
    const w = world(std(() => ({ text: "<h2>Validation</h2><table><tr><th>Membership Number</th><th>DOB</th></tr><tr><td>row value</td></tr></table><button>Go</button><form></form>" })));
    const r = await w.run({ id: "h.html", kind: "html", mode: "read", data: "sensitive", path: "/frag", scope: "none" }, {});
    eq(r.result.headings, ["Validation"]); eq(r.result.tableHeaders, ["Membership Number", "DOB"]);
    eq(r.result.buttons, ["Go"]); assert.strictEqual(r.result.forms, 1);
    assert.ok(!JSON.stringify(r).includes("row value"));
  });

  await test("json kind returns data, trims to picked keys and fields, and shapes instead of dumping a huge body", async () => {
    const body = { events: [{ id: 1, name: "n1", secret: "s" }, { id: 2, name: "n2", secret: "s" }], page: 1, total_pages: 9 };
    let w = world(std(() => ({ json: body })));
    const e = { id: "j.json", kind: "json", mode: "read", data: "public", path: "/j", scope: "none" };
    assert.strictEqual((await w.run(e, {})).result.data.page, 1);
    const trimmed = await w.run(e, { pick: ["events"], fields: ["id", "name"] });
    eq(trimmed.result.data, { events: [{ id: 1, name: "n1" }, { id: 2, name: "n2" }] });
    w = world(std(() => ({ json: { big: "x".repeat(20000) } })));
    const huge = await w.run(e, {});
    assert.strictEqual(huge.result.truncated, true); assert.ok(huge.result.shape);
    const sens = await w.run(Object.assign({}, e, { data: "sensitive" }), {});
    assert.strictEqual(sens.error, "FIELDS_REQUIRED");
  });

  await test("host-safe output (plain) rewrites query punctuation in strings", async () => {
    const w = world(std(() => ({ json: { link: "/a?b=1&c=2" } })));
    const r = await w.run({ id: "j.json", kind: "json", mode: "read", data: "public", path: "/j", scope: "none" }, { plain: true });
    assert.strictEqual(r.result.data.link, "/a[?]b[=]1[&]c[=]2");
  });

  await test("an oversized result is cut and says so", async () => {
    const rows = Array.from({ length: 400 }, (_, i) => ({ id: i, name: "n".repeat(60) }));
    const w = world(std((u) => (u.pathname === "/api/things/datatable" ? { json: descriptor("Things", ["name"], ORIGIN + "/api/things/data", { items_per_page: 400 }) } : pageRows(rows)(u))));
    const r = await w.run(tableEntry(), { maxRows: 400, maxChars: 3000 });
    assert.strictEqual(r.result.complete, false); assert.strictEqual(r.result.next, null); assert.match(r.note, /cut/);
    assert.ok(JSON.stringify(r).length <= 3500); assert.strictEqual(r.result.total, 400);
  });

  await test("UUID-shaped strings never reach a result", async () => {
    const id = "123e4567-e89b-12d3-a456-426614174000";
    const w = world(std(() => ({ json: { v: "x " + id + " y" } })));
    const r = await w.run({ id: "j.json", kind: "json", mode: "read", data: "public", path: "/j", scope: "none" }, {});
    assert.strictEqual(r.result.data.v, "x <uuid> y");
  });

  await test("guided, owner-only and flow entries are not runnable and make no request", async () => {
    const w = world(std());
    assert.strictEqual((await w.run({ id: "a.logout", kind: "flow", mode: "owner-only", path: "/logout" }, {})).error, "NOT_RUNNABLE");
    assert.strictEqual((await w.run({ id: "a.add", kind: "page", mode: "guided", path: "/add" }, {})).error, "NOT_RUNNABLE");
    assert.strictEqual((await w.run({ id: "a.f", kind: "flow", path: "/f" }, {})).error, "NOT_RUNNABLE");
    assert.strictEqual(w.calls.length, 0);
  });

  await test("menu flattening gives the trails the coverage ledger uses", async () => {
    const menuMain = { topMenu: [{ title: "Members", type: "parent", subtypes: [{ title: "Quick Search", type: "vue", vue_component: "s80-datatable", vue_component_data: { url: ORIGIN + "/api/q?contact_type=c&body_cid=202" } }] }],
      bottomMenu: [{ title: "Admin", type: "parent", subtypes: [{ title: "Bulk Renewal", type: "vue", vue_component: "s80-datatable", vue_component_data: { url: ORIGIN + "/api/b" }, sub_routes: [{ title: "Bulk Renewal", url_params: { "{{p}}": "bulk_renew_add_on_id" }, vue_component_data: { url: ORIGIN + "/api/b2" } }] }] }] };
    const w = world(std((u) => (u.pathname === "/api/menu/main" ? { json: menuMain } : u.pathname === "/api/menu/top" ? { json: { data: [{ title: "Logout", type: "internal", url: "/logout" }] } } : { status: 404, json: {} })));
    const m = await w.S80.menu("club");
    eq(m.nodes.map((n) => n.section + " > " + n.trail.join(" > ")), ["top > Members", "top > Members > Quick Search", "bottom > Admin", "bottom > Admin > Bulk Renewal", "bottom > Admin > Bulk Renewal > <Bulk Renewal params:bulk_renew_add_on_id>", "account > Logout"]);
    assert.strictEqual(m.role.cid, undefined);
    const raw = await w.S80.menu("club", { raw: true });
    assert.strictEqual(raw.role.body_cid, 202); assert.ok(raw.nodes[1].dataUrl.includes("body_cid=202"));
    assert.ok(m.nodes[1].dataUrl.includes("?contact_type,body_cid") && !m.nodes[1].dataUrl.includes("=202"));
  });

  await test("inspect classifies datatable, tabs, redirect, page, html, json and error without dumping values", async () => {
    const w = world(std((u) => ({
      "/d": { json: descriptor("D", ["a"], ORIGIN + "/d/data") }, "/t": { json: { tabs: [{ title: "T1", vue_component: "x", vue_component_data: { url: ORIGIN + "/t1?id=9" } }] } },
      "/r": { json: { type: "list", url: ORIGIN + "/r2?x=1" } }, "/j": { json: { a: 1, b: 2 } }, "/h": { text: "<h1>Hi</h1>" }, "/e": { status: 500, json: {} },
      "/i": { text: '<div data-page="' + JSON.stringify({ component: "C/P", props: { _shared: {}, k: 1 } }).replace(/"/g, "&quot;") + '"></div>' } }[u.pathname] || { status: 404, json: {} })));
    const k = async (p, o) => w.S80.inspect(ORIGIN + p, o);
    assert.strictEqual((await k("/d")).protocol, "datatable");
    const t = await k("/t"); assert.strictEqual(t.protocol, "tabs"); assert.strictEqual(t.tabs[0].url, "/t1?id");
    assert.strictEqual((await k("/t", { raw: true })).tabs[0].url, ORIGIN + "/t1?id=9");
    const r = await k("/r"); assert.strictEqual(r.protocol, "redirect"); assert.strictEqual(r.to, "/r2?x");
    eq((await k("/j")).keys, ["a", "b"]); assert.strictEqual((await k("/h")).protocol, "html");
    const e = await k("/e"); assert.strictEqual(e.protocol, "error"); assert.strictEqual(e.error, "SERVER");
    const i = await k("/i"); assert.strictEqual(i.component, "C/P"); eq(i.propKeys, ["k"]);
  });

  await test("discover.js: follows classified reads, never fetches Logout, Setup Club, unclassified pages or rankings tables", async () => {
    const menuMain = {
      topMenu: [
        { title: "Home", type: "internal", url: ORIGIN + "/home" },
        { title: "Members", type: "vue", vue_component: "ContactsView", vue_component_data: { url: ORIGIN + "/api/contact/list/view_format?contact_type=c", profile_url: ORIGIN + "/competitor_dashboard/profile_tabs" } },
        { title: "Results", type: "vue", vue_component: "s80-datatable", vue_component_data: { url: RANK + "/api/events/table?platform=1", access_token_url: ORIGIN + "/ranking_module/access_token" } },
        { title: "Store", type: "external", url: "https://shop.example/x" }],
      bottomMenu: [{ title: "Admin", type: "parent", subtypes: [
        { title: "Bulk Renewal", type: "vue", vue_component: "s80-datatable", vue_component_data: { url: ORIGIN + "/api/b/datatable" }, sub_routes: [{ title: "Bulk Renewal", url_params: { "{{p}}": "bulk_renew_add_on_id" }, vue_component_data: { url: ORIGIN + "/api/b/detail" } }] },
        { title: "Brand New", type: "internal", url: ORIGIN + "/brand/new/page" }] }] };
    const tabsBody = { tabs: [{ title: "Profile", vue_component: "x", vue_component_data: { url: ORIGIN + "/profile/competitor?cid=101" } }, { title: "Memberships", vue_component: "s80-datatable", vue_component_data: { url: ORIGIN + "/add_on_portal/t?cid=101" } }] };
    const inertia = '<div data-page="' + JSON.stringify({ component: "Dashboard/UserDashboardPage", props: { _shared: {}, dashboard: {} } }).replace(/"/g, "&quot;") + '"></div>';
    const w = world(std((u) => ({
      "/api/menu/main": { json: menuMain }, "/api/menu/top": { json: { data: [{ title: "Logout", type: "internal", url: "/logout" }, { title: "Setup Club", type: "internal", url: "/body/setup?bt=5" }] } },
      "/home": { text: inertia }, "/profile/competitor": { text: inertia },
      "/api/contact/list/view_format": { json: { type: "cards", url: ORIGIN + "/competitor_dashboard/card_data?contact_type=c" } }, "/competitor_dashboard/card_data": { json: { card_data: [], success: true } },
      "/competitor_dashboard/profile_tabs": { json: tabsBody }, "/add_on_portal/t": { json: descriptor("Memberships", ["add_on"], ORIGIN + "/add_on_portal/t/data") },
      "/api/b/datatable": { json: descriptor("Bulk", ["name"], ORIGIN + "/api/b/data") },
      "/build/manifest.json": { json: { "assets/js/Pages/Dashboard/UserDashboardPage.vue": {}, "assets/js/Pages/Foo/BarPage.vue": {}, "assets/app.css": {} } } }[u.pathname] || { status: 404, json: {} })));
    const js = execFileSync("python3", [CLI, "discover"], { encoding: "utf8" });
    assert.ok(!js.includes("/*ALLOW*/"));
    vm.runInContext(js, w.sandbox);
    for (let i = 0; i < 400 && !w.sandbox.S80D.done; i++) await new Promise((r) => setImmediate(r));
    const D = w.sandbox.S80D;
    assert.strictEqual(D.done, true); assert.strictEqual(D.error, null);
    const paths = w.calls.map((c) => c.path);
    for (const never of ["/logout", "/body/setup", "/brand/new/page", "/api/b/detail", "/api/events/table", "/x"]) assert.ok(!paths.includes(never), never + " must not be fetched");
    assert.ok(!w.calls.some((c) => c.host === RANK) && !w.calls.some((c) => c.host === "https://shop.example"));
    const by = Object.fromEntries(D.nodes.filter((n) => n.role === "personal").map((n) => [n.trail, n]));
    assert.strictEqual(by["top > Home"].protocol, "inertia");
    assert.strictEqual(by["top > Members"].protocol, "redirect"); assert.strictEqual(by["top > Members (list)"].protocol, "json");
    assert.strictEqual(by["top > Members [profile tabs]"].protocol, "tabs");
    assert.strictEqual(by["top > Members [profile tabs] > Memberships"].protocol, "datatable");
    assert.strictEqual(by["top > Results"].protocol, "rankings-table"); assert.strictEqual(by["top > Store"].protocol, "skipped");
    assert.strictEqual(by["bottom > Admin > Bulk Renewal"].protocol, "datatable");
    assert.strictEqual(by["bottom > Admin > Bulk Renewal > <Bulk Renewal params:bulk_renew_add_on_id>"].protocol, "needs-params");
    assert.strictEqual(by["bottom > Admin > Brand New"].protocol, "unvisited");
    assert.strictEqual(by["account > Logout"].protocol, "skipped"); assert.strictEqual(by["account > Setup Club"].protocol, "skipped");
    eq(D.pages, ["Dashboard/UserDashboardPage", "Foo/BarPage"]);
    const text = D.text(); assert.ok(!text.includes("null") && !text.includes("[]"));
    everything.push(text);
  });

  await test("a session lost mid-discovery stops the crawl with AUTH_REQUIRED instead of recording noise", async () => {
    let alive = true;
    const w = world((u) => {
      if (u.pathname === "/api/account/roles") return alive ? { json: roleBody } : { type: "opaqueredirect", status: 0 };
      if (u.pathname === "/api/menu/main") return { json: { topMenu: [{ title: "Home", type: "internal", url: ORIGIN + "/home" }, { title: "T", type: "vue", vue_component: "s80-datatable", vue_component_data: { url: ORIGIN + "/api/t" } }], bottomMenu: [] } };
      if (u.pathname === "/api/menu/top") return { json: { data: [] } };
      if (u.pathname === "/home") { alive = false; return { type: "opaqueredirect", status: 0 }; }
      return { type: "opaqueredirect", status: 0 };
    });
    vm.runInContext(execFileSync("python3", [CLI, "discover"], { encoding: "utf8" }), w.sandbox);
    for (let i = 0; i < 400 && !w.sandbox.S80D.done; i++) await new Promise((r) => setImmediate(r));
    assert.strictEqual(w.sandbox.S80D.error, "AUTH_REQUIRED");
  });

  const rankDescriptor = (extra) => descriptor("Rankings", ["name"], ORIGIN + "/api/r/data", Object.assign({ filters: [
    { name: "weight_class", type: "autocomplete", label: "Weight", items: [{ text: "Open Men's 89kg", value: 1089 }, { text: "Open Women's 59kg", value: 2059 }, { text: "Masters Men's 89kg", value: 3089 }]
      .concat(Array.from({ length: 100 }, (_, i) => ({ text: "Filler " + i, value: 5000 + i }))) },
    { name: "level", type: "select", label: "Level", items: [{ text: "Local", value: 1 }, { text: "National", value: 3 }] },
    { name: "club", type: "autocomplete", label: "Club" },
    { name: "first_name", type: "text", label: "First" },
    { name: "date_range_start", type: "datepicker", label: "From" }] }, extra || {}));
  const rankEntry = (over) => tableEntry(Object.assign({ id: "t.rank", path: "/api/r/table", requires_filter: ["weight_class"], option_filters: ["weight_class", "level", "club", "first_name", "ghost"] }, over || {}));
  const rankRoutes = (extra) => std((u) => (u.pathname === "/api/r/table" ? { json: rankDescriptor(extra) } : u.pathname === "/api/r/data" ? pageRows(people)(u) : { status: 404, json: {} }));

  await test("filter options: reviewed filters only, from the descriptor, searched before the cap; refusals make no row request", async () => {
    const w = world(rankRoutes());
    const e = rankEntry();
    const all = await w.run(e, { role: "personal", options: "weight_class" });
    assert.strictEqual(all.ok, true, JSON.stringify(all));
    assert.strictEqual(all.result.options.of, 103); assert.strictEqual(all.result.options.matching, 103); assert.strictEqual(all.result.options.returned, 50);
    assert.strictEqual(all.result.options.complete, false); assert.strictEqual(all.result.options.items.length, 50); assert.strictEqual(all.result.options.available, true);
    eq(all.result.options.items[0], { text: "Open Men's 89kg", value: 1089 });
    const found = await w.run(e, { role: "personal", options: "weight_class", optionSearch: "men's 89" });
    eq(found.result.options.items, [{ text: "Open Men's 89kg", value: 1089 }, { text: "Masters Men's 89kg", value: 3089 }]);
    assert.strictEqual(found.result.options.complete, true);
    const filler = await w.run(e, { options: "weight_class", optionSearch: "filler" });
    assert.strictEqual(filler.result.options.matching, 100); assert.strictEqual(filler.result.options.returned, 50);
    eq((await w.run(e, { options: "level" })).result.options.items, [{ text: "Local", value: 1 }, { text: "National", value: 3 }]);
    const none = await w.run(e, { options: "club" });
    assert.strictEqual(none.result.options.available, false); assert.ok(!("items" in none.result.options));
    assert.ok(!w.calls.some((c) => c.method === "POST"), "options never request rows");
    const before = w.calls.length;
    assert.strictEqual((await w.run(e, { options: "ghost" })).error, "UNKNOWN_FILTER");
    assert.strictEqual((await w.run(e, { options: "first_name" })).error, "BAD_PARAM");
    const notOffered = await w.run(e, { options: "date_range_start" });
    assert.strictEqual(notOffered.error, "BAD_PARAM"); assert.match(notOffered.message, /not offered/); eq(notOffered.have, ["weight_class", "level", "club", "first_name", "ghost"]);
    const sens = await w.run(Object.assign({}, e, { data: "sensitive" }), { options: "weight_class" });
    assert.strictEqual(sens.error, "BAD_PARAM"); assert.match(sens.message, /not offered/);
    assert.strictEqual((await w.run({ id: "j.json", kind: "json", mode: "read", data: "public", path: "/j", scope: "none" }, { options: "x" })).error, "BAD_PARAM");
    assert.strictEqual(w.calls.length - before, 4, "two descriptor-level refusals fetched the roles and the descriptor; the other three fetched nothing");
  });

  await test("filter options: unusable items are skipped and counted, and the envelope is bounded without cutting a value", async () => {
    const odd = [{ text: "ok one", value: 1 }, { text: "nested", value: { a: 1 } }, { text: "x".repeat(200), value: 2 }, { text: "id 123e4567-e89b-12d3-a456-426614174000", value: 3 }, { text: "ok two", value: "v2" }, null, 7];
    const w = world(rankRoutes({ filters: [{ name: "weight_class", type: "select", label: "W", items: odd.concat(Array.from({ length: 40 }, (_, i) => ({ text: "bulk item number " + i, value: 9000 + i }))) }] }));
    const r = await w.run(rankEntry(), { options: "weight_class" });
    eq(r.result.options.items.slice(0, 3), [{ text: "ok one", value: 1 }, { text: "ok two", value: "v2" }, { text: "7", value: 7 }]);
    assert.strictEqual(r.result.options.skipped, 4);
    const small = await w.run(rankEntry(), { options: "weight_class", maxChars: 700 });
    assert.ok(JSON.stringify(small).length <= 700, "bounded: " + JSON.stringify(small).length);
    assert.strictEqual(small.result.options.complete, false); assert.strictEqual(small.result.options.returned, small.result.options.items.length);
    for (const it of small.result.options.items) assert.ok(!String(it.value).includes("<") && String(it.text).length <= 120);
  });

  await test("a filter whose items carry numeric values is sent the number; text filters and other values pass through", async () => {
    const w = world(rankRoutes());
    const r = await w.run(rankEntry(), { filters: { weight_class: "1089", level: "3", first_name: "42", date_range_start: "2026-01-01", club: "7" }, maxRows: 1 });
    assert.strictEqual(r.ok, true, JSON.stringify(r));
    const sent = JSON.parse(w.calls.find((c) => c.method === "POST").body).filters;
    eq(sent, { weight_class: 1089, level: 3, first_name: "42", date_range_start: "2026-01-01", club: "7" });
    assert.strictEqual(typeof sent.weight_class, "number"); assert.strictEqual(typeof sent.first_name, "string"); assert.strictEqual(typeof sent.club, "string");
  });

  await test("an empty table says why with the catalogue's own hint, never with the descriptor's text", async () => {
    const msg = "descriptor text <script>alert(1)</script> that must not be echoed";
    let w = world(std((u) => (u.pathname === "/api/r/table" ? { json: rankDescriptor({ no_data_message: msg }) } : { json: { total: 0, page: 0, items_per_page: 1, data: [] } })));
    const e = rankEntry({ empty_hint: "Give a body weight category and a date range." });
    const empty = await w.run(e, { filters: { weight_class: "1089" }, maxRows: 1 });
    assert.strictEqual(empty.result.total, 0); assert.strictEqual(empty.result.hint, "Give a body weight category and a date range.");
    assert.ok(!JSON.stringify(empty).includes("alert(1)"));
    const nohint = await w.run(rankEntry(), { filters: { weight_class: "1089" }, maxRows: 1 });
    assert.ok(!("hint" in nohint.result));
    w = world(rankRoutes());
    const full = await w.run(e, { filters: { weight_class: "1089" }, maxRows: 1 });
    assert.ok(!("hint" in full.result));
  });

  await test("a required filter counts only when it holds a value: blank, null, empty list and empty object are refused, zero is accepted", async () => {
    const w = world(rankRoutes());
    const e = rankEntry({ requires_filter: ["first_name"] });
    for (const v of [undefined, null, "", "   ", [], {}]) assert.strictEqual((await w.run(e, { filters: { first_name: v } })).error, "FILTER_REQUIRED", JSON.stringify(v));
    assert.ok(!w.calls.some((c) => c.path === "/api/r/table"), "nothing was fetched for a refused request");
    assert.strictEqual((await w.run(e, { filters: { first_name: 0 }, maxRows: 1 })).ok, true);
  });

  const viewRows = (urls) => urls.map((url, i) => ({ meet: "m" + i, action: [{ type: "external", text: "View", url }] }));
  const refEntry = (over) => tableEntry(Object.assign({ id: "t.events", path: "/api/e/table", refs: [{ name: "event_id", from: "action", match: "^/public/rankings/results/(\\d{1,12})$" }] }, over || {}));
  const refRoutes = (urls) => std((u) => (u.pathname === "/api/e/table" ? { json: descriptor("Events", ["meet"], ORIGIN + "/api/e/data") } : u.pathname === "/api/e/data" ? pageRows(viewRows(urls))(u) : { status: 404, json: {} }));

  await test("row references come only from approved routes: a digit id from a matching portal link, and nothing else of the URL", async () => {
    const urls = ["/public/rankings/results/123", "public/rankings/results/456", ORIGIN + "/public/rankings/results/789?token=SECRETQUERY&x=1",
      "https://evil.test/public/rankings/results/1", "/public/rankings/results/abc", "/public/rankings/results/1234567890123", "/public/rankings/results/5/edit",
      "/public/rankings/results/%31", "/contact/delete/5", "/public/rankings/results/77#frag"];
    const w = world(refRoutes(urls));
    const r = await w.run(refEntry(), { maxRows: 10, perPage: 10 });
    assert.strictEqual(r.ok, true, JSON.stringify(r));
    const refs = r.result.rows.map((x) => x.refs && x.refs.event_id);
    eq(refs, ["123", "456", "789", undefined, undefined, undefined, undefined, undefined, undefined, "77"]);
    assert.ok(r.result.rows.every((x) => x.actions[0] === "View" && !("action" in x) && !("links" in x)));
    const blob = JSON.stringify(r);
    for (const leak of ["SECRETQUERY", "token=", "/contact/delete", "evil.test", "%31"]) assert.ok(!blob.includes(leak), "leaked " + leak);
    const none = await world(refRoutes(urls)).run(refEntry({ refs: undefined }), { maxRows: 10, perPage: 10 });
    assert.ok(none.result.rows.every((x) => !("refs" in x)), "an entry without refs returns none");
    const picked = await world(refRoutes(urls)).run(refEntry(), { maxRows: 2, perPage: 2, fields: ["meet"] });
    assert.ok(picked.result.rows.every((x) => !("refs" in x)), "refs follow the fields rule");
    const named = await world(refRoutes(urls)).run(refEntry(), { maxRows: 2, perPage: 2, fields: ["meet", "refs"] });
    eq(named.result.rows.map((x) => x.refs.event_id), ["123", "456"]);
    // Defence in depth: even a loose spec (the validator forbids it) can only ever yield digits.
    const loose = await world(refRoutes(["/public/rankings/results/abc", "/public/rankings/results/42"])).run(refEntry({ refs: [{ name: "event_id", from: "action", match: "^/public/rankings/results/(.+)$" }] }), { maxRows: 2, perPage: 2 });
    eq(loose.result.rows.map((x) => x.refs && x.refs.event_id), [undefined, "42"]);
  });

  await test("tab references: one numeric query value of an approved name; URLs still print names only; no raw URL on a parse failure", async () => {
    const tabs = [{ title: "A", vue_component_data: { url: "/api/stat/draw?addon_id=830&contact_type=competitor&body_cid=202&token=SECRETTAB" } },
      { title: "B", vue_component_data: { url: "/api/stat/draw?addon_id=1&addon_id=2" } }, { title: "C", vue_component_data: { url: "/api/stat/draw?addon_id=abc" } },
      { title: "D", vue_component_data: { url: "http://[::1/leak?token=SECRETPARSE" } }, { title: "E", vue_component_data: { url: "/api/stat/draw?other_id=9" } }];
    const w = world(std((u) => (u.pathname === "/api/stat" ? { json: { name: "Stats", tabs } } : { status: 404, json: {} })));
    const e = { id: "t.tabs", kind: "tabs", mode: "read", data: "personal", path: "/api/stat", scope: "body", refs: [{ name: "addon_id", from: "tab", query: "addon_id" }] };
    const r = await w.run(e, { role: "club" });
    assert.strictEqual(r.ok, true, JSON.stringify(r));
    eq(r.result.tabs.map((t) => t.refs && t.refs.addon_id), ["830", undefined, undefined, undefined, undefined]);
    assert.strictEqual(r.result.tabs[0].url, "/api/stat/draw?addon_id,contact_type,body_cid,token");
    assert.strictEqual(r.result.tabs[3].url, "<unparsed url>");
    assert.ok(!JSON.stringify(r).includes("SECRETTAB") && !JSON.stringify(r).includes("SECRETPARSE"));
  });

  await test("exact origins: a lookalike host, a table pointing elsewhere and a rankings redirect receive nothing", async () => {
    const lookalike = "https://portal.test.other.test";
    let w = world(std((u) => (u.pathname === "/api/things/datatable" ? { json: descriptor("Things", ["name"], lookalike + "/steal") } : { status: 404, json: {} })));
    let r = await w.run(tableEntry(), { maxRows: 1 });
    assert.strictEqual(r.error, "UNEXPECTED_ORIGIN");
    assert.ok(!w.calls.some((c) => c.url.startsWith(lookalike)), "nothing was sent to the lookalike");
    w = world(std((u) => (u.pathname === "/api/things/datatable" ? { json: { tabs: [{ title: "Memberships", vue_component_data: { url: lookalike + "/tabs/x" } }] } } : { status: 404, json: {} })));
    r = await w.run(tableEntry({ via: { tabs: "/api/things/datatable", match: ["Memberships"] } }), { maxRows: 1 });
    assert.strictEqual(r.error, "UNEXPECTED_ORIGIN");
    assert.ok(!w.calls.some((c) => c.url.startsWith(lookalike)));
    const rank = { id: "r.rank", kind: "datatable", mode: "read", data: "public", path: "/api/events/table", scope: "none", host: "rankings", auth: "role", verified: "live" };
    w = world(std((u) => (u.origin === RANK && u.pathname === "/api/events/table" ? { json: descriptor("Events", ["meet"], ORIGIN + "/api/portal/rows") } : { status: 404, json: {} })));
    r = await w.run(rank, { role: "club", maxRows: 1 });
    assert.strictEqual(r.error, "UNEXPECTED_ORIGIN");
    assert.ok(!w.calls.some((c) => c.path === "/api/portal/rows"), "rankings tokens never go to a descriptor-chosen host");
    w = world(std((u) => (u.origin === RANK && u.pathname === "/api/events/table" ? { type: "opaqueredirect", status: 0 } : { status: 404, json: {} })));
    r = await w.run(rank, { role: "club", maxRows: 1 });
    assert.strictEqual(r.error, "UNEXPECTED_REDIRECT");
    for (const c of w.calls.filter((x) => x.host === RANK)) { assert.strictEqual(c.redirect, "manual"); assert.strictEqual(c.credentials, "omit"); }
    for (const c of w.calls) if (c.host !== ORIGIN) assert.ok(!("X-XSRF-TOKEN" in c.headers) && !("X-Requested-With" in c.headers), "no portal headers off the portal origin");
  });

  await test("a stale runtime is replaced, and a snippet refuses to run against version 1", async () => {
    const w = world(std());
    w.sandbox.S80 = { version: 1 };
    assert.match(vm.runInContext(RUNTIME, w.sandbox), /loaded \(v2\)/);
    assert.strictEqual(w.sandbox.S80.version, 2);
    assert.match(vm.runInContext(RUNTIME, w.sandbox), /already loaded \(v2\)/);
    const snippet = execFileSync("python3", [CLI, "js", "account.roles"], { encoding: "utf8" });
    const body = snippet.split("\n").filter((l) => !l.startsWith("//")).join("\n").replace(/^await /m, "return await ");
    const old = world(std());
    old.sandbox.S80 = { version: 1 };
    await assert.rejects(async () => vm.runInContext("(async () => {" + body + "})()", old.sandbox), /Load the runtime first/);
    const ok = await vm.runInContext("(async () => {" + body + "})()", w.sandbox);
    assert.strictEqual(ok.ok, true);
  });

  await test("strings in a result never carry secret-looking query values, even from ordinary columns", async () => {
    const w = world(std((u) => (u.pathname === "/j" ? { json: { link: "https://files.test/x?token=SECRETCELL&id=5&sig=ABCDEF&expires=99", benign: "a?b=1&c=2", n: 7 } } : { status: 404, json: {} })));
    const r = await w.run({ id: "j.json", kind: "json", mode: "read", data: "public", path: "/j", scope: "none" }, {});
    assert.strictEqual(r.result.data.link, "https://files.test/x?token=<redacted>&id=5&sig=<redacted>&expires=<redacted>");
    assert.strictEqual(r.result.data.benign, "a?b=1&c=2");
    assert.ok(!JSON.stringify(r).includes("SECRETCELL"));
  });

  await test("the output bound holds after plain-text expansion", async () => {
    const rows = Array.from({ length: 60 }, (_, i) => ({ id: i, note: "a=b&c=d?e=f ".repeat(6) }));
    const w = world(std((u) => (u.pathname === "/api/things/datatable" ? { json: descriptor("Things", ["note"], ORIGIN + "/api/things/data") } : pageRows(rows)(u))));
    const r = await w.run(tableEntry(), { maxRows: 60, perPage: 60, plain: true, maxChars: 1500 });
    assert.ok(JSON.stringify(r).length <= 1500, "bounded after expansion: " + JSON.stringify(r).length);
    assert.strictEqual(r.result.complete, false); assert.match(r.note, /cut/);
  });

  await test("one row that alone exceeds the output limit is dropped, not returned over it", async () => {
    const rows = [{ id: 1, note: "x".repeat(3000) }];
    const w = world(std((u) => (u.pathname === "/api/things/datatable" ? { json: descriptor("Things", ["note"], ORIGIN + "/api/things/data") } : pageRows(rows)(u))));
    const r = await w.run(tableEntry(), { maxRows: 5, maxChars: 1000 });
    assert.ok(JSON.stringify(r).length <= 1000, "bounded: " + JSON.stringify(r).length);
    eq(r.result.rows, []); assert.strictEqual(r.result.total, 1); assert.strictEqual(r.result.complete, false); assert.match(r.note, /One row alone/);
  });

  await test("no secret sentinel appears in any result, error or log produced by the scenarios", async () => {
    const blob = everything.join("\n");
    for (const v of Object.values(SECRET)) assert.ok(!blob.includes(v), "leaked " + v);
    assert.ok(everything.length > 15);
  });

  process.stdout.write(JSON.stringify(results) + "\n");
})();
