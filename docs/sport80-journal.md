# Sport80 skill journal

Living record for the `sport80` skill: what was asked, what was measured, what was decided and why. Newest round last.
Finding status: **firm** (reproduced or read from the portal's own code), **interim** (one observation), **exploratory**
(a lead), **superseded** (kept, marked, with the date and reason). Evidence lives under
`docs/evidence/sport80-discovery-20261108/`. No ids, names, emails, row values or token values are recorded anywhere in
this repository; role ids appear as `<cid>` (personal) and `<body_cid>` (club).

## Request and consumers

Owner, 2026-11-08: a brand-new skill that "knows how to access both my personal and club accounts through Sport80 with USA
Weightlifting", with "all of the logic and skill that's exposed in those areas ... exposed as Sport80 skills so that we can
access this information" (https://usaweightlifting.sport80.com/).

Reading: one skill leaf, `sport80`; each capability the portal exposes to the personal role and to the club role is a named,
parameterised catalogue entry that an agent can run (reads) or walk the owner through (writes). Consumers: an agent in any
host with a browser tool that can evaluate JavaScript in a signed-in tab (reads the card, the catalogue and the runtime), the
owner (reads results), CI (the hermetic suite), and a maintainer refreshing the catalogue after the portal changes.

## Round 0 - repository state (2026-11-08)

Canonical checkout clean on `main` at `44e9a60d`, equal to `origin/main`; a worktree branch `sport80/<suffix>` cut from it. Rules that
bind the work (AGENTS.md, owner notes): a new skill's first change note is `version: 0.1.0`; new suites are registered in
`test/suite_catalog.py` and counted in `test/test-groups.test.py`; release output is written only by `scripts/release.py`;
no `Co-Authored-By` trailer (owner, 2026-10-29); an Astra max review of the design precedes the build (owner, 2026-10-25 and
three later misses).

## Round 1 - live discovery of both roles (2026-11-08)

Question: what do the owner's personal role and club role expose, and how can an agent call it without handling a password,
a cookie or a token?

Conditions: the owner's own Chrome through Claude in Chrome, already signed in (the password manager was approved but not
needed until the session expired once, see F7). GET-only crawl, one request at a time. POST only to a datatable's `data_url`
(the call the UI itself makes to read rows); no write, payment, logout, 2FA or password endpoint was touched. Output was
reduced to structure (names, counts, status) before it reached the transcript; the two token values were measured by length
and never printed. Tool limits met: the page-script tool blocks output that resembles cookies or query strings, and caps
output near 1,000 characters, so larger results were rendered into a scratch tab and read as page text.

Cases and results:

| # | Case | Result |
|---|------|--------|
| C1 | Read the shared page props of the dashboard | `_shared.roles` lists a personal role and a club role; keys `menu`, `roles`, `accounts`, `user_account_menu`, `support` |
| C2 | Fetch `/build/manifest.json` | 200; 402 JS chunks, 127 page entries (about 83 Inertia components) |
| C3 | `GET /api/menu/main` and `/api/menu/top`, personal and club (`?body_cid=`) | 200; personal 20 crawlable nodes, club 58 |
| C4 | Read the datatable component in the front-end bundle | request shape for descriptors and rows (see F3) |
| C5 | Replay descriptors and rows for 5 club tables | 200; rows `{total,page,items_per_page,statistics,data[]}`; member quick search returns 0 rows without a filter |
| C6 | Rankings token exchange, club and personal scope | 200; two opaque 36-character header values; differ between scopes |
| C7 | Club-scoped results for 2026 | 18 events, `results` column sums to 142; equals the owner's earlier independent figures |
| C8 | Personal-scoped results for 2026 | 387 events (unscoped national list) |
| C9 | Public results: event table descriptor and rows, rankings and events descriptors | 200 without login; 131 rows for one national event |
| C10 | Full menu-graph crawl, both roles | 74 requests, 81 lines (`crawl.txt`); gated nodes 401, 403, 500 as listed in F8 |
| C11 | Member profile tabs for the owner's own member | 15 tabs, mostly one add-on table endpoint with different `id_cat` |
| C12 | Personal data counts: transactions, entries | personal transactions 71, club transactions 63, entries 19 (counts only) |

Findings:

- **F1 firm.** The UI is server-driven: each role's menu response names every page and the endpoint behind it, so the menu is
  the capability inventory and differs by role. Evidence: C3, C10, `crawl.txt`.
- **F2 firm.** Two roles on one login. The club role is addressed by `?body_cid=<id>` on API calls and `/v/<id>/...` on
  pages; the page banner reads "acting as" the club. `/api/account/roles` returns the list. Evidence: C1, C3.
- **F3 firm.** Datatable protocol: `GET <descriptor>` then `POST <data_url>?p=<page, 0-based>&l=<size>&sort=<col>&d=asc|des&s=<search>&st=<type>`
  with body `{"columns":[],"filters":{...}}` (`[]` when `has_advanced_filter`), headers `X-Requested-With: XMLHttpRequest`,
  `X-Keep-Session: keepsession`, `X-XSRF-TOKEN` from the `XSRF-TOKEN` cookie. Read from the app's own component code and
  replayed live. Evidence: C4, C5, C7.
- **F4 firm.** Tab menus nest endpoints; a sub-route's `url_params` become query parameters (`&eid=<id>`). Evidence: C10 and the
  router code that appends them.
- **F5 firm.** The Results and Rankings modules live on `window.env.RANKINGS_DOMAIN_URL`. A logged-in tab mints header values
  from `/ranking_module/access_token[?body_cid=]`; the club-scoped pair filters rows to the club. Evidence: C6, C7, C8, and the
  UI's own request (method, URL, header names, body keys) captured by an XHR hook and matching the replay.
- **F6 firm.** Public results need no login: `X-API-Token` set to the page's public key (`window.env.SERVICES_API_PUBLIC_KEY`).
  Evidence: C9.
- **F7 interim.** An idle session expired once: the next navigation redirected to the SAML sign-in page. Autofill from the
  owner's password manager signed back in. Cause not isolated (idle time is the leading hypothesis; the personal-scope token
  call did not end the session, checked afterwards; probes sent no `X-Keep-Session` header while the UI does).
- **F8 firm.** Gating: 401 Pre-Screening Approvals (role lacks it); 403 event admin panels, discount-code eligible
  organisations without their id; 500 Bulk Renewal detail without its add-on id; 404 a public athlete id that is not a
  rankings-module id. Evidence: C10, C9.
- **F9 exploratory.** The rankings-module athlete id is not the portal contact id or the membership number (both returned 404
  for a member with no recorded results); it appears in the member's Results & Rankings tab. One member only.
- **F10 firm.** Nothing was written, sent, paid or deleted during discovery.

Unknowns carried forward: per-event admin panels (the club hosts no events on the platform, so no `eid` exists to try); Smart
List rows and saved-view behaviour; Bulk Renewal detail with a real add-on id; sanctioning and add-membership forms; every
write, payment, email and report-generation flow; roles other than the owner's; the real idle timeout and whether
`X-Keep-Session` extends it; row actions beyond the single `View` link seen on results rows.

## Round 2 - design review by Astra at max effort

Reviewer: Astra (Codex, effort max, read-only sandbox; it read the repository and relevant history, did not browse the
portal, and says so). Input: the design brief written before any code. Verdict: the design is sound with one P0 and
several P1 changes; every consumer named in the brief was accepted as justified except the cut list below.

| Finding | Reviewer's point | Disposition |
|---------|------------------|-------------|
| P0 credential boundary | The brief said scripts never handle tokens while the runtime reads the XSRF cookie and rankings tokens. "Never returns a header value" is not enough: raw props, error bodies, URLs and hidden fields can hold secrets. | **Accepted.** Exact statement: local scripts (the CLI) never receive credentials and make no network calls; code running inside the signed-in page may use session tokens transiently inside function scope; passwords, 2FA codes and card data stay with the owner. No token in a global, a log, an error or a result; results carry only selected fields; headers are set per origin (portal headers and XSRF only to the portal, token headers only to the rankings host). |
| P1 completeness | Menu URLs prove coverage of discovered structure, not of capabilities; buttons, row actions, forms and wizard steps are operations. Zero unclassified endpoints must not hide an inaccessible subtree. | **Accepted.** Catalogue entries carry `operations` (observed buttons, config actions, form fields) and `row_actions` (`observed` list or `unobserved`; no invented handlers). A coverage ledger records menu nodes, manifest pages classified as reachable, inaccessible or out of scope, blocked branches as gaps, and scope unknowns (email-only and mobile-only flows). `diff` compares operations and descriptor columns, filters and buttons, and reports gaps separately from unclassified entries. |
| P1 sensitivity and effects | One exclusive enum cannot express a financial report that is sensitive, exported and emailed. "Summarise by default" is prompt policy; small groups identify people. | **Accepted.** Two fields: `data` (public, personal, sensitive) and `effects` (a list drawn from read, export, write, outbound, financial, security). Technical default: a sensitive table returns total and columns only; rows need an explicit `maxRows` and explicit `fields`. Subscriber-group creation is a write; report download is an export; sending email is outbound. Confirmation applies to the concrete target and effect, and an existing explicit instruction counts. |
| P1 roles and modes | Share entries, but record availability, verification and effective scope per role; personal scope is not "my records"; keep member, event and athlete ids distinct; add an execution mode. | **Accepted.** One entry per operation with `roles.{personal,club,public}` each carrying availability, verification and a scope note. `mode` is read, guided or owner-only. Entries seen only in a menu or never exercised are listed but `js` refuses them without `--unverified`. Parameter names are distinct (`member_cid`, `event_id`, `eid`, `athlete_id`). |
| P1 error handling | Not every 401 or HTML response means expired login; a SAML redirect can look like a network failure; validate parameters first; stop on throttling or a challenge; discovery must not follow every GET link (the account menu has Logout). | **Accepted, and measured.** With credentials omitted, portal calls return an opaque redirect (redirects not followed) or throw a network error (followed); the rankings host returns a readable 401. The runtime does not follow redirects, reports AUTH_REQUIRED only when a ping to the roles endpoint also fails, keeps permission, missing-parameter, unexpected-response, network, throttled and challenge outcomes distinct, validates required parameters and filters before fetching, and never loops a keepalive. Discovery follows only protocol-classified reads and an allowlist taken from the catalogue; everything else is recorded as unvisited. |
| P1 tests | Fake fetch cannot prove CORS, cookies or portal compatibility; test generated snippets end to end with secret sentinels; return `complete` and continuation. Require Node; `check` must say when it skipped JS validation. Live support needs a consented smoke check recorded with date, tool and sanitized observations. | **Accepted.** The suite requires Node. Live smoke checks are recorded below with the tool and filters; historical counts are labelled as evidence from a date. |
| P1 host contract | "Can evaluate JavaScript" is necessary but not sufficient. | **Accepted.** `references/hosts.md` lists prerequisites (existing authenticated tab, correct origin, awaited async evaluation, controlled result size, re-injection after navigation; form interaction and safe navigation for guided writes) and a tested matrix; only Claude in Chrome is tested. Public reads do not need login. |
| P2 | Drop the "about 200 lines" target; discovery is maintenance, never part of an ordinary request; `discover` prints browser code. Naming is fine; do not imply every Sport80 federation. Register the suite; new-skill note uses `version: 0.1.0`. | **Accepted.** |

Cut by the review and by me: persistent token or global state, automatic full crawls, code-size targets, speculative action
handlers, and a repository identity scan presented as proof of privacy (a narrow lint for emails and UUID literals stays, and
is labelled as a lint).

Unknowns the reviewer added: rate limits, automation detection, account flags and the portal's terms cannot be inferred from
successful requests; browser-tool logging behaviour needs checking; other owners' roles are discoverable candidates, not
supported capabilities.

Decision: build as reviewed. Order: catalogue and coverage data, runtime, discovery, CLI, tests, live smoke checks with the
shipped snippets, card and references, registration and note.

## Round 3 - build and verification

Built as reviewed, in this order: catalogue and coverage ledger, runtime, discovery, CLI, tests, live smoke checks with the
shipped snippets, card and references, registration and note. Reference commits that set the pattern for a new skill: the
change-note, shim-plus-module CLI and core-suite registration of `d8c159e91f1cbb0666beba05b3ca827fc7133eae` (rubric-eval and
adversarial-review) and the multi-reference layout and suite catalog entry of `9a76358dfa47cae1e2dee6bf1da9c355c4aca0b0`
(in-parallel). Source revision this round was built on: `44e9a60d8b6cd646c73412877097c4e872cbb6b1`.

### What shipped

`skills/sport80/` with a card, four references (access, protocols, safety, hosts), `capabilities.json` (114 entries: 89 read,
23 guided, 2 owner-only; 75 runnable now; coverage ledger of 112 menu nodes, 76 front-end pages, 9 gaps and 4 scope
unknowns), `scripts/runtime.js`, `scripts/discover.js`, and the `sport80` CLI (`catalog`, `show`, `js`, `runtime`, `discover`,
`diff`, `coverage`, `check`). `test/sport80.test.py` (24 tests) and `test/sport80-runtime-harness.js` (25 scenarios) are
registered as one core suite. `changes/sport80/initial.md` carries `version: 0.1.0`.

### Tests (hermetic; Node required)

- Catalogue: validates; 16 mutation cases each prove the validator reports the specific breakage (missing confirm, a financial
  entry without the card rule, security effects on a non-owner entry, a read entry with other effects, dangling coverage,
  duplicate ids, an email, a UUID, a long number, an undeclared via parameter, an unbound path placeholder, an undeclared
  required filter, a bad enum).
- CLI: filters, `show`, every refusal (guided, owner-only, unverified, unknown parameter, wrong role, sensitive rows without
  fields) exits 2, generated snippets parse under Node as expression, function and bundle, `check` reports a skipped syntax check
  when Node is absent and fails under `--require-node`.
- Drift: the recorded live run (`docs/evidence/sport80-discovery-20261108/live-discovery.json`) against the catalogue gives 0
  unclassified, 0 missing, 0 changed and equal page sets; mutated runs prove new items, removed items, column and button
  changes, new and gone pages, and a stopped run are each reported; `--write-descriptors` touches only descriptors.
- Runtime (25 scenarios, fake portal and rankings host, secret sentinels for the cookie, public key and both tokens): request
  construction (headers, zero-based `p`, body, XSRF only to the portal, token headers only to the rankings host with
  credentials omitted), paging and `complete` and `next`, scope, sensitive counts-only, refusals before any request, the failure
  taxonomy, challenge and throttle with no retry, tab resolution, page and fragment outlines, bounding, UUID scrub, menu trails,
  and discovery (never fetches Logout, Setup Club, unclassified pages or rankings tables; stops on a lost session). No sentinel
  appears in any result, error or log.

What a fake fetch cannot prove (browser CORS, cookie behaviour, portal compatibility) is covered only by the live checks
below, which are evidence from one day, not a standing assertion.

### Live smoke checks (2026-11-08, Claude in Chrome script tool, personal and club roles, signed in)

All through snippets generated by `sport80 js`:

| Case | Result |
|------|--------|
| club results 2026, club token | 18 events, `results` sums to 142 (the owner's earlier independent figures) |
| results 2026, public key, no login | role Public, total 387 |
| public event results | total 131 |
| quick search with no filter | `FILTER_REQUIRED`, 0 requests |
| quick search, one filter, counts only | total 0, rows withheld |
| member memberships, member results (tab-resolved, public key for the rankings call) | totals 1 and 2 |
| transactions, personal and club | 71 and 63, counts only |
| events.find meets | truncated at the 12 KB bound; `--pick events --fields` documented |
| missing event type; unknown filter | `MISSING_PARAM`; `UNKNOWN_FILTER` |
| club sanction requests pending; bulk renewal products with one field | total 0; one row with `name` |
| club profile tabs; roles | six tabs; two roles |
| session ended (requests sent without cookies) | `AUTH_REQUIRED` for portal and club-token reads; the public read still succeeds; a guided entry returns `NOT_RUNNABLE`; the session then resumes |
| secrets | no UUID-shaped string in any output; the runtime object exposes only `version, roles, exec, ping, show, inspect, menu` |

### Discovery with the shipped tool

The shipped `scripts/discover.js` (generated by `sport80 discover`, allowlist taken from the catalogue) was run in the signed-in
tab over both roles: 79 requests, 112 nodes, 76 front-end pages, no run error. Protocols seen: inertia 23, datatable 36, html 9,
tabs 4, json 4, redirect 2, rankings-table 6 (recorded, not fetched), needs-params 17 (recorded, not fetched), skipped 10
(three external links; Setup Club, Manage 2FA, Change Password and Logout for both roles, never fetched), unvisited 0, error 1
(Pre-Screening Approvals, HTTP 401, the role lacks it). The node and page counts equal the coverage ledger's, so the diff of this run
against the catalogue is clean.

The committed snapshot `docs/evidence/sport80-discovery-20261108/live-discovery.json` is the first live run, made with an earlier
build of the crawler (before the deny list was checked first and before redirects were followed for allowlisted pages). It
differs from the shipped build's run only in ten nodes: six event-finder pages recorded as `UNEXPECTED_REDIRECT` and four
Setup Club, 2FA, password and logout items recorded as `unvisited`; the ledger and descriptors were built from it. It is kept
as the test fixture and is evidence of that run, not of the final tool. Method and structure of the first manual crawl are in
`crawl.txt` beside it (role ids scrubbed).

### Findings added this round

- **F11 firm.** Without a session, portal calls with redirects not followed return an opaque redirect; with redirects followed
  they throw a network error (the cross-origin sign-in redirect fails CORS). The rankings host answers a missing or bad token
  with a readable 401 and CORS headers. Basis of the `AUTH_REQUIRED` rule (a ping must also fail).
- **F12 firm.** The event finder pages redirect to the same URL with a default `from_date`. With redirects not followed the
  crawl first recorded them as `UNEXPECTED_REDIRECT`. Fix: the page entry takes `from_date` (default today) and discovery follows
  redirects only for allowlisted same-origin pages.
- **F13 firm.** A page cannot load the runtime from a localhost server: the browser raises its local-network permission prompt
  and the script call hangs (45 s timeout). The runtime is pasted instead; the server was stopped and nothing was granted.
- **F14 interim.** The Claude in Chrome script tool returns about 1,000 characters and blocks output that looks like cookies or
  query strings. Recipe in `references/hosts.md`: small outputs, `--plain`, or a scratch same-origin tab read as page text.
- **F15 firm.** A member's Results & Rankings sub-tabs point at athlete tables on the rankings host and carry the public key;
  `member.results` resolves the tab and calls the host with the page's public key; the athlete id is never printed or stored.
- **F16 firm.** The Smart List descriptor lists only an action column; rows need the saved view's column model (not exercised).

### Decisions

One leaf named `sport80`, first version 0.1.0. Entries are shared across roles with per-role evidence. Unverified reads are
listed but refused by `js` without `--unverified`. Discovery follows protocol-classified reads and allowlisted pages only, checks
the deny list first, and records unclassified items as unvisited. The coverage ledger and the descriptors were corrected from
the observed trails and the live snapshot, not the other way round. Lint: ruff was run in isolation on the Python; findings were
fixed except the three that match the repository's own convention (a shebang on a non-executable test file and `noqa: E402`
on imports after a path insert).

### Still unknown

Event admin panels (no hosted event to try), Smart List rows, Bulk Renewal detail, every write, payment, email and
report-generation flow, other owners' roles, the portal's rate limits and terms, and the real idle timeout. They are the
catalogue's gaps G1 to G9 and its unknowns.
