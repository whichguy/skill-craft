"""sport80 CLI: catalogue, snippet generator, coverage and drift tools for the USA Weightlifting Sport80 portal.

Local and offline: it makes no network calls and never holds credentials. `js`, `runtime` and `discover` print browser
code for the host's JavaScript tool, which runs it in the owner's already signed-in tab.

  sport80 catalog [--area A] [--role R] [--mode M] [--data D] [--verified V] [--runnable] [--json]
  sport80 show ID
  sport80 js ID [--role personal|club|public|<body_cid>] [--param k=v] [--filter k=v] [--rows N] [--fields a,b] [--search S] [--sort C] [--desc]
                [--page N] [--per-page N] [--pick k,k] [--plain] [--max-chars N] [--unverified] [--with-runtime] [--wrap expr|function]
                [--options FILTER [--option-search TEXT]]
  sport80 runtime
  sport80 discover
  sport80 diff LIVE.json [--json] [--write-descriptors]
  sport80 coverage [--json]
  sport80 check [--require-node]

Exit: 0 ok, 1 a check or diff found problems, 2 usage or a refused request.
"""
import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "references" / "capabilities.json"
RUNTIME = ROOT / "scripts" / "runtime.js"
DISCOVER = ROOT / "scripts" / "discover.js"

KINDS = {"datatable", "tabs", "page", "html", "json", "flow", "file"}
RUNNABLE = {"datatable", "tabs", "page", "html", "json"}
MODES = {"read", "guided", "owner-only"}
EFFECTS = {"read", "export", "write", "outbound", "financial", "security"}
DATA = {"public", "personal", "sensitive"}
ROLE_KEYS = {"personal", "club", "public"}
SEEN = {"menu", "props", "page", "bundle", "tab"}
VERIFIED = {"live", "descriptor", "page", "none", "denied"}
USABLE = {"live", "descriptor", "page"}
SCOPES = {"body", "none"}
HOSTS = {"portal", "rankings"}
AUTHS = {"public", "role"}
PARAM_IN = {"path", "query", "filter", "option"}
OPTION_TYPES = {"select", "autocomplete", "radio"}
REF_NAME = re.compile(r"^[a-z][a-z0-9_]{0,31}$")
SURFACES = {"reachable", "flow", "renderer", "out-of-scope", "unmapped", "inaccessible"}
DENY = re.compile(r"logout|auth\.sport80\.com|/body/setup|\.(xlsx|pdf|csv)(\?|$)|/uploads/", re.IGNORECASE)
LINT = [("email address", re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")), ("uuid", re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.IGNORECASE)),
        ("long number (an id?)", re.compile(r"\b\d{6,}\b"))]
ID_RE = re.compile(r"^[a-z0-9_]+(\.[a-z0-9_]+)+$")
DESCRIPTOR_KEYS = {"datatable": ("columns", "filters", "buttons"), "tabs": ("tabs",), "inertia": ("component", "propKeys", "formFields"), "html": ("tableHeaders",), "json": ("keys",)}


def load(path=CATALOG):
    return json.loads(Path(path).read_text())


def by_id(doc):
    return {e["id"]: e for e in doc["entries"]}


# ---- validation ------------------------------------------------------------------------------------------------------
def validate(doc):
    errs = []
    add = errs.append
    if doc.get("schema") != 1:
        add("schema must be 1")
    for k in ("portal", "observed_on", "entries", "coverage", "legend"):
        if k not in doc:
            add("missing top-level key " + k)
    entries = doc.get("entries", [])
    ids = [e.get("id") for e in entries]
    for i in sorted({x for x in ids if ids.count(x) > 1}):
        add("duplicate id " + str(i))
    known = set(ids)
    for e in entries:
        i = e.get("id", "?")
        e_ = lambda m, i=i: add(f"{i}: {m}")
        if not ID_RE.match(str(i)):
            e_("id must look like area.name")
        for k in ("title", "area", "kind", "mode", "effects", "data", "roles", "source"):
            if k not in e:
                e_("missing " + k)
        if e.get("kind") not in KINDS:
            e_("bad kind")
        if e.get("mode") not in MODES:
            e_("bad mode")
        if e.get("data") not in DATA:
            e_("bad data")
        if not e.get("effects") or not set(e["effects"]) <= EFFECTS:
            e_("effects must be a non-empty list drawn from " + ",".join(sorted(EFFECTS)))
        if not e.get("source"):
            e_("source must be a non-empty list")
        roles = e.get("roles") or {}
        if not roles:
            e_("roles must not be empty")
        for r, v in roles.items():
            if r not in ROLE_KEYS:
                e_("bad role " + r)
            if v.get("seen") not in SEEN:
                e_(f"role {r}: bad seen")
            if v.get("verified") not in VERIFIED:
                e_(f"role {r}: bad verified")
        mode = e.get("mode")
        if mode in ("guided", "owner-only") and not e.get("confirm"):
            e_(mode + " entries need confirm text")
        if mode != "read" and "financial" in e.get("effects", []) and not re.search(r"card", e.get("confirm", ""), re.IGNORECASE):
            e_("a financial entry's confirm text must say never to enter card details")
        if "security" in e.get("effects", []) and mode != "owner-only":
            e_("security effects are owner-only: the agent never drives them")
        if mode == "read":
            if e.get("kind") not in RUNNABLE:
                e_("a read entry must have a runnable kind")
            if e.get("effects") != ["read"]:
                e_("a read entry has effects [read] only; move other effects to a guided entry")
            if not (e.get("path") or e.get("via")):
                e_("a read entry needs a path or via")
        if e.get("scope", "none") not in SCOPES:
            e_("bad scope")
        host = e.get("host", "portal")
        if host not in HOSTS:
            e_("bad host")
        if host == "rankings":
            if e.get("auth") not in AUTHS:
                e_("a rankings entry needs auth public|role")
            if e.get("path") and not str(e["path"]).startswith("/"):
                e_("a rankings path is host-relative")
        path = e.get("path")
        params = e.get("params", [])
        pnames = {p.get("name") for p in params}
        if path is not None and not (str(path).startswith("/") or str(path).startswith("https://")):
            e_("path must start with / or https://")
        for pg in e.get("pages", []):
            if not str(pg).startswith("/"):
                e_("pages entries must be portal paths starting with /")
        for ph in re.findall(r"\{(\w+)\}", path or ""):
            if not any(p.get("name") == ph and p.get("in") == "path" for p in params):
                e_(f"path placeholder {{{ph}}} has no path parameter")
        for p in params:
            if p.get("in") not in PARAM_IN:
                e_(f"param {p.get('name')}: bad in")
            if p.get("in") == "filter" and not p.get("type"):
                e_(f"filter {p.get('name')}: needs a type")
            if "values" in p and not all(isinstance(x, str) for x in p["values"]):
                e_(f"param {p.get('name')}: values must be strings")
        via = e.get("via")
        if via:
            if not (via.get("tabs") and via.get("match")):
                e_("via needs tabs and match")
            elif via.get("param") and via["param"] not in pnames:
                e_("via param is not declared in params")
        for f in e.get("requires_filter", []):
            if not any(p.get("name") == f and p.get("in") == "filter" for p in params):
                e_("requires_filter names an undeclared filter: " + f)
        for op in e.get("operations", []):
            if not (op.get("label") and op.get("source")) or not set(op.get("effects", [])) <= EFFECTS or not op.get("effects"):
                e_("operation needs label, source and effects")
        # Route-specific references: the only way an id leaves a link (journal Round 9 and its design review). Anchored, digits only.
        for r in e.get("refs", []):
            if not (isinstance(r, dict) and REF_NAME.match(str(r.get("name", ""))) and r.get("from") in ("action", "tab")):
                e_("a ref needs a name like event_id and from action|tab")
                continue
            if e.get("data") == "sensitive":
                e_("a sensitive entry has no refs")
            if r["from"] == "action":
                m = str(r.get("match", ""))
                if e.get("kind") != "datatable":
                    e_("an action ref belongs to a datatable entry")
                if not (m.startswith("^/") and m.endswith("$") and m.count("(") == 1 and "(\\d{1,12})" in m):
                    e_("an action ref's match is anchored (^/...$) and captures exactly one (\\d{1,12})")
                try:
                    re.compile(m)
                except re.error:
                    e_("a ref's match does not compile")
            else:
                if e.get("kind") != "tabs":
                    e_("a tab ref belongs to a tabs entry")
                if not re.fullmatch(r"[a-z_]{1,32}", str(r.get("query", ""))):
                    e_("a tab ref names one query parameter")
        offered = e.get("option_filters", [])
        if offered and (e.get("kind") != "datatable" or e.get("data") == "sensitive"):
            e_("option_filters belong to a non-sensitive datatable entry")
        for f in offered:
            if not any(p.get("name") == f and p.get("in") == "filter" and p.get("type") in OPTION_TYPES for p in params):
                e_("option_filters names a filter without options: " + str(f))
        hint = e.get("empty_hint")
        if hint is not None and (not isinstance(hint, str) or len(hint) > 160 or re.search(r"https?://|\?\w+=", hint)):
            e_("empty_hint is plain text up to 160 characters with no URL")
        ra = e.get("row_actions", "unobserved")
        if ra != "unobserved" and not (isinstance(ra, list) and all(isinstance(x, str) for x in ra)):
            e_("row_actions is 'unobserved' or a list of observed labels")
    cov = doc.get("coverage", {})
    seen_nodes = set()
    for n in cov.get("menu_nodes", []):
        k = (n.get("role"), n.get("trail"))
        if k in seen_nodes:
            add("coverage: duplicate menu node " + str(k))
        seen_nodes.add(k)
        if n.get("role") not in ROLE_KEYS:
            add("coverage: bad role on " + str(k))
        if n.get("entry") is not None and n["entry"] not in known:
            add(f"coverage: menu node {k} names unknown entry {n['entry']}")
        if not n.get("entry") and not n.get("skip"):
            add(f"coverage: menu node {k} needs an entry or a skip reason")
    comps = set()
    for p in cov.get("pages", []):
        if p.get("component") in comps:
            add("coverage: duplicate page " + str(p.get("component")))
        comps.add(p.get("component"))
        if p.get("surface") not in SURFACES:
            add("coverage: bad surface on " + str(p.get("component")))
        for x in p.get("entries", []):
            if x not in known:
                add(f"coverage: page {p.get('component')} names unknown entry {x}")
        if p.get("surface") in ("reachable", "flow") and not p.get("entries"):
            add(f"coverage: page {p.get('component')} is {p.get('surface')} but names no entry")
        if p.get("surface") in ("unmapped", "out-of-scope", "inaccessible") and not p.get("reason"):
            add(f"coverage: page {p.get('component')} needs a reason")
    gids = [g.get("id") for g in cov.get("gaps", [])]
    for x in sorted({y for y in gids if gids.count(y) > 1}):
        add("coverage: duplicate gap " + str(x))
    for g in cov.get("gaps", []):
        for x in g.get("entries", []):
            if x not in known:
                add(f"coverage: gap {g.get('id')} names unknown entry {x}")
    if not isinstance(cov.get("unknowns"), list):
        add("coverage: unknowns must be a list")
    text = json.dumps(doc)
    for label, rx in LINT:
        m = rx.search(text)
        if m:
            add(f"lint: a {label} appears in the catalogue ({m.group(0)[:12]}...); the catalogue must not carry identifiers or addresses")
    return errs


# ---- helpers ---------------------------------------------------------------------------------------------------------
def default_role(e):
    roles = e["roles"]
    if e.get("via"):
        return "personal" if "personal" in roles else "club"
    if "public" in roles:
        return "public"
    return "personal" if "personal" in roles else "club"


def verified_for(e, role):
    return e["roles"].get(role, {}).get("verified")


def runtime_entry(e, role):
    keep = ("id", "kind", "mode", "data", "path", "query", "scope", "host", "auth", "via", "params", "requires_filter", "refs", "option_filters", "empty_hint")
    out = {k: e[k] for k in keep if k in e}
    out["defaultRole"] = default_role(e)
    out["verified"] = verified_for(e, role)
    return out


def endpoint(e):
    if e.get("via"):
        return "resolved from the tab " + " > ".join(e["via"]["match"]) + " of " + e["via"]["tabs"]
    q = e.get("query") or {}
    return (e.get("path") or "-") + (("?" + "&".join(f"{k}={v}" for k, v in q.items())) if q else "")


def split_kv(items, what):
    out = {}
    for it in items or []:
        if "=" not in it:
            raise SystemExit(f"sport80: {what} needs k=v, got {it!r}")
        k, v = it.split("=", 1)
        out[k] = v
    return out


def say(msg):
    print(msg)


# ---- commands --------------------------------------------------------------------------------------------------------
def cmd_catalog(a):
    doc = load()
    rows = []
    for e in doc["entries"]:
        if a.area and e["area"] != a.area:
            continue
        if a.role and a.role not in e["roles"]:
            continue
        if a.mode and e["mode"] != a.mode:
            continue
        if a.data and e["data"] != a.data:
            continue
        vs = {v["verified"] for r, v in e["roles"].items() if not a.role or r == a.role}
        if a.verified and a.verified not in vs:
            continue
        if a.runnable and not (e["mode"] == "read" and vs & USABLE):
            continue
        rows.append(e)
    if a.json:
        say(json.dumps(rows, indent=1))
        return 0
    w = max([len(e["id"]) for e in rows] or [10])
    for e in rows:
        rv = ",".join(f"{r}:{v['verified']}" for r, v in e["roles"].items())
        say(f"{e['id']:<{w}}  {e['mode']:<10} {e['data']:<9} {rv:<38} {e['title']}")
    say(f"{len(rows)} of {len(doc['entries'])} entries")
    return 0


def cmd_show(a):
    e = by_id(load()).get(a.id)
    if not e:
        say(f"sport80: no capability {a.id!r}; run `sport80 catalog`")
        return 2
    say(f"{e['id']}  {e['title']}")
    say(f"area: {e['area']}   kind: {e['kind']}   mode: {e['mode']}   data: {e['data']}   effects: {','.join(e['effects'])}")
    say("roles: " + "; ".join(f"{r} ({v['seen']}, {v['verified']}{', ' + v['scope'] if v.get('scope') else ''})" for r, v in e["roles"].items()))
    say(f"endpoint: {endpoint(e)}   scope: {e.get('scope', 'none')}   host: {e.get('host', 'portal')}" + (f"   auth: {e['auth']}" if e.get("auth") else ""))
    for p in e.get("params", []):
        extra = ", ".join(f"{k}={p[k]}" for k in ("type", "values", "default", "identity") if k in p)
        say(f"  param {p['name']} [{p['in']}{', required' if p.get('required') else ''}] {extra}")
    if e.get("requires_filter"):
        say("requires at least one filter of: " + ", ".join(e["requires_filter"]))
    ops = e.get("operations", [])
    say("operations: " + ("; ".join(f"{o['label']} ({','.join(o['effects'])}; {o['source']})" for o in ops) if ops else "none observed"))
    ra = e.get("row_actions", "unobserved")
    say("row actions: " + (ra if isinstance(ra, str) else ", ".join(ra)))
    if e.get("confirm"):
        say("confirm: " + e["confirm"])
    if e.get("descriptor"):
        say("descriptor: " + json.dumps(e["descriptor"]))
    say("source: " + "; ".join(e["source"]))
    if e.get("notes"):
        say("notes: " + e["notes"])
    if e["mode"] == "read":
        r = default_role(e)
        say(f"run: sport80 js {e['id']} --role {r}" + (" --rows 5 --fields <names>" if e["data"] == "sensitive" else ""))
    else:
        say(f"procedure: this is {e['mode']}; open {e.get('path') or 'the page named above'} in the signed-in tab only as the confirm text allows. `sport80 js` refuses it.")
    return 0


def cmd_js(a):
    doc = load()
    e = by_id(doc).get(a.id)
    if not e:
        say(f"sport80: no capability {a.id!r}; run `sport80 catalog`")
        return 2
    if e["mode"] != "read":
        say(f"sport80: {a.id} is {e['mode']}, not a read. Run `sport80 show {a.id}` and follow its confirm text; no snippet is generated.")
        return 2
    selector = a.role or default_role(e)
    role = selector if selector in ROLE_KEYS else "club"
    if role not in e["roles"]:
        say(f"sport80: {a.id} is not offered for role {selector}; it has: {', '.join(e['roles'])}")
        return 2
    ver = verified_for(e, role)
    if ver not in USABLE and not a.unverified:
        say(f"sport80: {a.id} for role {role} is '{ver}' (never exercised or denied), so it is not offered as runnable. Pass --unverified to generate it anyway and report the result as unverified.")
        return 2
    allowed = {p["name"] for p in e.get("params", []) if p["in"] in ("path", "query", "option")}
    params = split_kv(a.param, "--param")
    for k in params:
        if k not in allowed:
            say(f"sport80: {a.id} has no parameter {k!r}; it takes: {', '.join(sorted(allowed)) or 'none'}")
            return 2
    if role == "club":
        for p in e.get("params", []):
            if p.get("default") == "role.cid" and p["name"] not in params:
                say(f"sport80: {a.id} with a club role needs --param {p['name']}=<{p.get('identity', 'record id')}>: its default would be the club's own contact id, not a member's. "
                    "Find a member's id with members.quick_search, and read a record only after the owner names the member.")
                return 2
    filters = split_kv(a.filter, "--filter")
    fields = [x for x in (a.fields or "").split(",") if x]
    pick = [x for x in (a.pick or "").split(",") if x]
    if e["data"] == "sensitive" and ((a.rows and a.rows > 0 and e["kind"] == "datatable") or pick) and not fields:
        say(f"sport80: {a.id} is sensitive data. Name the fields to return with --fields (or use --rows 0 for counts only).")
        return 2
    if a.options:
        if e["kind"] != "datatable":
            say(f"sport80: --options applies to datatable entries; {a.id} is a {e['kind']}.")
            return 2
        if e["data"] == "sensitive":
            say(f"sport80: {a.id} is sensitive data; its filter options are not offered.")
            return 2
        offered = e.get("option_filters", [])
        if a.options not in offered:
            say(f"sport80: {a.id} does not offer options for filter {a.options!r}; it offers: {', '.join(offered) or 'none'}")
            return 2
    elif a.option_search:
        say("sport80: --option-search needs --options FILTER")
        return 2
    needs = e.get("requires_filter") or []
    if needs and not a.options and not any(filters.get(k) for k in needs):
        say(f"sport80: {a.id} needs at least one filter of: {', '.join(needs)}. " + (e.get("empty_hint") or "Pass --filter NAME=VALUE."))
        return 2
    opts = {"role": selector}
    for k, v in (("params", params), ("filters", filters), ("fields", fields), ("pick", pick)):
        if v:
            opts[k] = v
    for k, v in (("maxRows", a.rows), ("search", a.search), ("searchType", a.search_type), ("sort", a.sort), ("page", a.page), ("perPage", a.per_page), ("maxChars", a.max_chars)):
        if v is not None:
            opts[k] = v
    if a.desc:
        opts["desc"] = True
    if a.plain:
        opts["plain"] = True
    if a.options:
        opts["options"] = a.options
        if a.option_search:
            opts["optionSearch"] = a.option_search
    call = "await S80.exec(" + json.dumps(runtime_entry(e, role), separators=(",", ":")) + ", " + json.dumps(opts, separators=(",", ":")) + ")"
    guard = "if (!globalThis.S80 || globalThis.S80.version < 2) throw new Error('Load the runtime first: sport80 runtime');"
    head = f"// sport80 js {a.id} role={selector} ({e['mode']}; {e['data']}; verified {ver}); run in a signed-in tab on {doc['portal']}"
    body = f"async () => {{ {guard} return {call}; }}" if a.wrap == "function" else f"{guard}\n{call}"
    say((RUNTIME.read_text() + "\n" if a.with_runtime else "") + head + "\n" + body)
    return 0


def cmd_runtime(_a):
    sys.stdout.write(RUNTIME.read_text())
    return 0


def allow_patterns(doc):
    out = set()
    for e in doc["entries"]:
        if e["mode"] == "owner-only":
            continue
        cands = list(e.get("pages", []))
        if e["kind"] in ("page", "html", "json"):
            cands.append(e.get("path") or "")
        for p in cands:
            if p.startswith("/") and not DENY.search(p):
                out.add(re.sub(r"\\\{\w+\\\}", "[^/]+", re.escape(p)))
    return sorted(out)


def cmd_discover(_a):
    text = DISCOVER.read_text()
    if "/*ALLOW*/[]" not in text:
        say("sport80: discover.js lost its ALLOW placeholder")
        return 1
    sys.stdout.write(text.replace("/*ALLOW*/[]", json.dumps(allow_patterns(load()))))
    return 0


def descriptor_of(node):
    p = node.get("protocol")
    if p not in DESCRIPTOR_KEYS:
        return None
    d = {"protocol": p}
    for k in DESCRIPTOR_KEYS[p]:
        v = node.get(k)
        if v is not None:
            d[k] = v
    return d


def merged(nodes):
    out = {}
    for n in nodes:
        d = descriptor_of(n)
        if not d:
            continue
        cur = out.setdefault(d["protocol"], {"protocol": d["protocol"]})
        for k, v in d.items():
            if k == "protocol":
                continue
            if isinstance(v, list):
                cur[k] = sorted(set(cur.get(k, [])) | set(map(str, v)))
            else:
                cur[k] = v
    return out


def compute_diff(doc, live):
    ledger = {(n["role"], n["trail"]): n for n in doc["coverage"]["menu_nodes"]}
    entries = by_id(doc)
    nodes = live.get("nodes", [])
    roles_live = {n["role"] for n in nodes}
    seen, unclassified, gaps = set(), [], []
    mapped = defaultdict(list)
    for n in nodes:
        k = (n["role"], n["trail"])
        seen.add(k)
        item = ledger.get(k)
        if item is None:
            unclassified.append({"role": n["role"], "trail": n["trail"], "protocol": n.get("protocol"), "path": n.get("path")})
        elif item.get("entry"):
            mapped[item["entry"]].append(n)
        if n.get("protocol") in ("unvisited", "needs-params", "error"):
            gaps.append({"role": n["role"], "trail": n["trail"], "protocol": n["protocol"], "why": n.get("reason") or n.get("error") or ",".join(n.get("params", []))})
    missing = [{"role": r, "trail": t, "entry": ledger[(r, t)].get("entry")} for (r, t) in ledger if r in roles_live and (r, t) not in seen and ledger[(r, t)].get("entry")]
    changed = []
    for eid, ns in mapped.items():
        want = entries[eid].get("descriptor")
        if not want:
            continue
        got = merged(ns)
        for proto, wd in want.items() if all(isinstance(v, dict) for v in want.values()) else []:
            gd = got.get(proto)
            if gd is None:
                if any(descriptor_of(n) for n in ns):
                    changed.append({"entry": eid, "what": f"protocol changed: expected {proto}, saw {sorted(got)}"})
                continue
            for k, wv in wd.items():
                if k == "protocol" or not isinstance(wv, list):
                    continue
                gv = gd.get(k, [])
                add_, rem_ = sorted(set(gv) - set(wv)), sorted(set(wv) - set(gv))
                if add_ or rem_:
                    changed.append({"entry": eid, "what": k, "added": add_, "removed": rem_})
    pages = {"new": [], "gone": []}
    if live.get("pages"):
        have = {p["component"] for p in doc["coverage"]["pages"]}
        pages["new"] = sorted(set(live["pages"]) - have)
        pages["gone"] = sorted(have - set(live["pages"]))
    return {"unclassified": unclassified, "missing": missing, "changed": changed, "pages": pages, "gaps": gaps,
            "nodes_seen": len(nodes), "roles": sorted(roles_live), "ok": not (unclassified or missing or changed or pages["new"] or pages["gone"])}


def cmd_diff(a):
    doc = load()
    live = json.loads(Path(a.live).read_text())
    if live.get("error"):
        say(f"sport80: the live run stopped early with {live['error']}; nothing to compare. Sign in and rerun discovery.")
        return 2
    res = compute_diff(doc, live)
    if a.write_descriptors:
        entries = by_id(doc)
        groups = defaultdict(list)
        ledger = {(n["role"], n["trail"]): n for n in doc["coverage"]["menu_nodes"]}
        for n in live.get("nodes", []):
            item = ledger.get((n["role"], n["trail"]))
            if item and item.get("entry"):
                groups[item["entry"]].append(n)
        for eid, ns in groups.items():
            m = merged(ns)
            if m:
                entries[eid]["descriptor"] = m
        doc["observed_on"] = live.get("observed_on", doc["observed_on"])
        CATALOG.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n")
        say(f"wrote descriptors for {sum(1 for e in doc['entries'] if e.get('descriptor'))} entries")
    if a.json:
        say(json.dumps(res, indent=1))
    else:
        say(f"live nodes {res['nodes_seen']} across roles {', '.join(res['roles'])}")
        for k in ("unclassified", "missing", "changed"):
            say(f"{k}: {len(res[k])}")
            for x in res[k]:
                say("  " + json.dumps(x))
        say(f"pages new: {res['pages']['new']}  gone: {res['pages']['gone']}")
        say(f"gaps (not failures, record them): {len(res['gaps'])}")
        for x in res["gaps"]:
            say("  " + json.dumps(x))
        say("OK" if res["ok"] else "DIFFERENCES FOUND")
    return 0 if res["ok"] else 1


def cmd_coverage(a):
    doc = load()
    cov = doc["coverage"]
    surf = defaultdict(int)
    for p in cov["pages"]:
        surf[p["surface"]] += 1
    mn = defaultdict(int)
    for n in cov["menu_nodes"]:
        mn[(n["role"], "skipped" if n.get("skip") else "covered")] += 1
    if a.json:
        say(json.dumps({"entries": len(doc["entries"]), "menu_nodes": {f"{r}:{s}": c for (r, s), c in sorted(mn.items())}, "pages": dict(surf), "gaps": cov["gaps"], "unknowns": cov["unknowns"]}, indent=1))
        return 0
    say(f"entries: {len(doc['entries'])} (read {sum(e['mode'] == 'read' for e in doc['entries'])}, guided {sum(e['mode'] == 'guided' for e in doc['entries'])}, owner-only {sum(e['mode'] == 'owner-only' for e in doc['entries'])})")
    say("menu nodes: " + ", ".join(f"{r} {s} {c}" for (r, s), c in sorted(mn.items())))
    say("front-end pages: " + ", ".join(f"{s} {c}" for s, c in sorted(surf.items())))
    say("gaps:")
    for g in cov["gaps"]:
        say(f"  {g['id']}: {g['what']} - {g['why']}")
    say("scope unknowns:")
    for u in cov["unknowns"]:
        say("  " + u)
    return 0


def node_check(path):
    node = shutil.which("node")
    if not node:
        return None
    r = subprocess.run([node, "--check", str(path)], check=False, capture_output=True, text=True)
    return r.returncode == 0, (r.stderr or "").strip()


def cmd_check(a):
    doc = load()
    errs = validate(doc)
    for e in errs:
        say("FAIL " + e)
    with tempfile.TemporaryDirectory() as d:
        gen = Path(d) / "discover.generated.js"
        gen.write_text(DISCOVER.read_text().replace("/*ALLOW*/[]", json.dumps(allow_patterns(doc))))
        for label, p in (("runtime.js", RUNTIME), ("discover.js (generated)", gen)):
            r = node_check(p)
            if r is None:
                say(f"SKIPPED JavaScript syntax check of {label}: node not found")
                if a.require_node:
                    errs.append("node required")
            elif not r[0]:
                errs.append(f"{label} does not parse")
                say(f"FAIL {label}: {r[1]}")
    say(f"{len(doc['entries'])} entries, {len(errs)} problems")
    return 1 if errs else 0


def main(argv=None):
    ap = argparse.ArgumentParser(prog="sport80", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("catalog")
    c.add_argument("--area"); c.add_argument("--role", choices=sorted(ROLE_KEYS)); c.add_argument("--mode", choices=sorted(MODES)); c.add_argument("--data", choices=sorted(DATA))
    c.add_argument("--verified", choices=sorted(VERIFIED)); c.add_argument("--runnable", action="store_true"); c.add_argument("--json", action="store_true")
    s = sub.add_parser("show"); s.add_argument("id")
    j = sub.add_parser("js"); j.add_argument("id"); j.add_argument("--role", help="personal, club, public, or a club's body_cid or name when the login has several"); j.add_argument("--param", action="append"); j.add_argument("--filter", action="append")
    j.add_argument("--rows", type=int); j.add_argument("--fields"); j.add_argument("--pick"); j.add_argument("--search"); j.add_argument("--search-type"); j.add_argument("--sort"); j.add_argument("--desc", action="store_true")
    j.add_argument("--page", type=int); j.add_argument("--per-page", type=int); j.add_argument("--max-chars", type=int); j.add_argument("--plain", action="store_true"); j.add_argument("--unverified", action="store_true")
    j.add_argument("--with-runtime", action="store_true"); j.add_argument("--wrap", choices=["expr", "function"], default="expr")
    j.add_argument("--options", help="list the values a select or autocomplete filter accepts (descriptor only, no rows)"); j.add_argument("--option-search", help="substring to match in the option text")
    sub.add_parser("runtime"); sub.add_parser("discover")
    d = sub.add_parser("diff"); d.add_argument("live"); d.add_argument("--json", action="store_true"); d.add_argument("--write-descriptors", action="store_true")
    v = sub.add_parser("coverage"); v.add_argument("--json", action="store_true")
    k = sub.add_parser("check"); k.add_argument("--require-node", action="store_true")
    a = ap.parse_args(argv)
    return {"catalog": cmd_catalog, "show": cmd_show, "js": cmd_js, "runtime": cmd_runtime, "discover": cmd_discover, "diff": cmd_diff, "coverage": cmd_coverage, "check": cmd_check}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
