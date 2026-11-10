---
name: pushpress
description: >-
  Sign in to and navigate PushPress Core, the gym-management system, through the owner's signed-in browser: members and
  leads, memberships and plans with recurring billing, invoices and payments, class schedule and check-ins, digital
  waivers, reports, settings, and the PushPress API/MCP tools. Use whenever the user mentions PushPress, or works in a
  project whose notes say the gym runs on it and asks about member or lead records, plans or pricing, discounts, failed
  or upcoming payments, deposits, payouts or membership revenue, class types, check-ins or attendance, coach payroll,
  waivers, lead capture or API keys, or asks to "log in to" or "find X in" PushPress. Covers a verified map of the admin
  app, which questions need the web UI versus the API, sign-in through the host's approved credential flow (never a
  typed password), and safety rules for member data, money and outbound messages.
version: 0.1.0
license: MIT
platforms:
  - linux
  - macos
metadata:
  skill_craft:
    kind: mixed
---

# pushpress

PushPress **Core** is where a gym keeps its roster (members, leads, staff), sells and bills memberships (Stripe
underneath), runs the class calendar and check-ins, and stores signed waivers. Each gym's admin lives at its own tenant
host, `https://<tenant>.pushpress.com`. This skill navigates it through the owner's signed-in browser and routes what the
API can answer to the `pushpress` MCP server's tools. Its UI claims were checked read-only on **2026-11-08**, on one
tenant (the *Core Pro Monthly* tier), unless a claim is tagged otherwise or says it was reported (legend below). Execution needs a browser tool for the
UI and, optionally, the MCP server for the API: [hosts.md](references/hosts.md) lists what each needs and what is tested.
If one is missing, say so instead of improvising.

## Binding

`SKILL_ROOT` is the directory of this loaded `SKILL.md`, not the working directory. The one script,
`scripts/pp-extract.js`, runs inside a browser page and never in a shell: read it from `SKILL_ROOT` and hand its text to the
host's page-script tool.

```sh
SKILL_ROOT="/absolute/directory-containing-the-loaded-SKILL.md"
EXTRACT="$SKILL_ROOT/scripts/pp-extract.js"    # page-side only, see Operating notes
```

## Know the tenant first

Apart from the one tier named under *Honest limits*, this skill carries **no tenant facts**: no host, company ID, plan
names or prices, class names or revenue figures. Before acting, get the tenant host (`<tenant>` in `https://<tenant>.pushpress.com`) and the company name from the user or the
project's notes (`AGENTS.md`, `CLAUDE.md` or the host's equivalent); never guess them.

A project can supply its own overlay, `references/<tenant>.md`, for what is particular to its gym: host, company ID, plan
categories, known issues, ties to its other systems. Vendored into a project's skills directory, it sits beside the other
references; installed from a marketplace, keep it in the project and name it in the project's notes. Read it first: for its
own tenant it wins over this skill's maps, and the live page wins over both. An overlay never loosens the rules below.

## Pick the right door first

| You need | Use | Why |
|---|---|---|
| One member / plan / class / check-in record, check-in counts, enrollment status, the webhook list (URLs and event types only: the response carries signing secrets, which you never print) | **API**: the `pushpress` MCP server's tools (`mcp__pushpress__*` on Claude hosts). See [api-and-mcp-tools.md](references/api-and-mcp-tools.md) | Structured, no clicking; the read tools are safe to repeat. |
| Anything about **money** (charges, invoices, deposits, forecasts, revenue), plan **prices**, discounts, the **list of plans or leads**, reports, settings, class types | **Admin web UI** in a signed-in browser tab (this skill's maps) | The API has no revenue, price, discount, plan-list or headcount surface ([api-and-mcp-tools.md §4](references/api-and-mcp-tools.md#4-what-the-api-cannot-do)). |
| A plan's advertised price and quantity **when you already hold its `plan_…` ID**; the public policy page; public sign-up | **Public tenant pages**, no login | `GET /landing/plans/<plan_id>` returns JSON. You cannot start from a plan *name*: get the ID from the Plans page (*View landing page*) or an enrollment's `planId`. Signed in, the Plans page already shows the price: prefer it. See [app-map.md §6](references/app-map.md#6-public-tenant-pages-no-login). |

## Rules that matter, and why

1. **Read-only unless the user says otherwise.** Opening pages, menus, drawers, tabs, filters and the search box changes
   nothing. Anything that saves, sends, charges, deletes or downloads needs the user's explicit yes naming the target (see
   *Action classes*). This system bills real people and emails real people: members and, in many gyms, the parents of
   minors.
2. **Member data is sensitive.** Many gyms serve minors, and a child's profile often carries a parent's email. Never write
   names, emails, phones, birthdays, addresses, `usr_…` IDs or screenshots of person pages and reports into repo files,
   journals or messages: structure only (labels, paths, column headers, ID *prefixes*). Asked for a project file, a project
   note or an outbound message that lists members' names, emails, phones or birthdays, do not write it and do not offer to
   build one from the live report, pasted rows or an exported report: say member data stays out of project files and
   outbound messages, and offer counts, column names, or the PushPress screen, where the user can read the list. On the
   surveyed tenant a "structure-only" crawl still leaked a name and an email through a button label and a page title until
   the extractor was tightened ([browser-technique.md](references/browser-technique.md)).
3. **Re-verify before asserting.** The UI ships fixes constantly (the top-bar *Product updates* panel is the changelog) and
   help-center articles are older still. Quote labels and paths from the live page, and say plainly when a claim comes from
   documentation only.
4. **Close, don't Save.** Editors are drawers and dialogs. Leave with `Close` or `Escape`, then confirm no dialog remains
   open.
5. **Never type, read back or ask for a password.** See *Sign in*.
6. **An API key never goes through chat.** Never ask for, print, copy into chat or write a PushPress API key or webhook
   secret anywhere. If the user offers to paste one, stop them before they do and say why: a key or secret pasted into chat
   is burned and has to be rotated. Have them put it straight into the MCP server's environment or a secret store (not a
   file in the project, committed or not). If one is pasted anyway, do not save or reuse it, and tell the user to rotate it
   themselves: a rotation done by you, through a tool or the page, would put the new secret in this transcript too. Once
   `Add API Key` has been pressed, by you or by the user, read nothing from the page and do nothing more in it (no
   screenshot, page text, accessibility tree or page script) until the user says the value is stored and the dialog is
   closed; rule 4's check waits for that.

## Sign in

Sign-in is the owner's browser and password manager. You never handle a password: the host's approved credential flow (a
fill the owner is prompted to approve) does it, and a code or CAPTCHA is the owner's alone. The recipe for the one verified
host is in [hosts.md](references/hosts.md#recipe-claude-in-chrome).

1. **Check first.** Open your own tab on `https://<tenant>.pushpress.com/main`. The sidebar and *Dashboard* mean you are in;
   a redirect to `/login` means continue.
2. **Ask for the credential before navigating**, through the host's approved flow, naming PushPress and the company name.
   The owner approves in the password manager. If the saved item is bound to the tenant host, sign in there.
   If the host has no approved fill, ask the owner to sign in in the open tab, then re-check `/main`.
3. **Sign in on the tenant origin:** `https://<tenant>.pushpress.com/login` (branded "to continue to <company name>"). The
   bare `https://app.pushpress.com/` is a 404; `app.pushpress.com/login` works, but an item saved for the tenant host is not
   matched there, so prefer the tenant.
4. **It is a two-step form:** email, *Next*, password, *Login* (the URL carries `?step=accountCheck`, then
   `?step=passwordCheck`). The fill enters the email and advances.
5. **The password step is flaky.** On 2026-11-08 an automatic fill reported failure five times and an emptiness probe (whether `value.length` is above zero,
   never the value or its length) showed it empty, yet the session was authenticated within about a minute (cause
   unconfirmed: a delayed fill, or the owner finished it). So try once, **wait about 30 s and re-check the URL**, and do not
   loop. If it is still on `?step=passwordCheck`, tell the owner and ask them to finish the password in the open tab. Seen
   in one session and not re-tested.
6. If the fill leaves the password revealed (an eye icon on), mask it before a person types, and take no screenshot and no
   page-text read until it is masked.
7. A one-time code goes through the host's code-entry feature, never through you (none was seen). When the work is done,
   release any granted credentials and close the tabs you opened.

## Where things live

Sidebar groups are **collapsed in the DOM until opened and re-collapse after every navigation**: go by URL where you can.
Full route index: [app-map.md](references/app-map.md).

| Area | Sidebar → path | Read |
|---|---|---|
| Home | Dashboard → `/main` | [app-map.md](references/app-map.md) |
| People | People → `/people/members` · `/leads` · `/non-members` · `/staff`; profile `/user/<id>` | [people-and-plans.md](references/people-and-plans.md) |
| Plans, discounts, documents | Plans → `/plans/list`, `/discounts`; Apps → `/documents` | [people-and-plans.md](references/people-and-plans.md) |
| Schedule | Schedule → `/schedule`, `/schedule/classes`, `/schedule/events`, `/calendar/checkins`; Appointments `/appointments` | [schedule-and-checkins.md](references/schedule-and-checkins.md) |
| Money and reports | Payments → `/payments`, `/reports/transactions`, `/reports/payments`, `/reports/deposits`, `/reports/ach`; Reports → 10 pages; Products → `/products` | [money-and-reports.md](references/money-and-reports.md) |
| Settings and admin | Settings → `/settings/*`, `/account`; Apps → App Store; Marketplace; Communicate → Automatic Emails | [settings-and-admin.md](references/settings-and-admin.md) |
| Not in the sidebar | Class types `/schedule/class-types`, Locations `/locations`, Appointment setup `/appointments/settings`: reached from each Schedule page's `Setup`/gear | [schedule-and-checkins.md](references/schedule-and-checkins.md) |

## Task router

| I want to… | Go to | API instead? |
|---|---|---|
| Find a person fast | Top-bar **Search** (palette: "Search for a person or a page"), or People → tab → *Search members* | `customers-list email=…` (**READ**, returns personal data) |
| See a member's plans, next charge, billing history | `/user/<id>` → *Plans & Appointment Credits*, *Billing* | `enrollment-list customerId=…` (no amounts) |
| List plans, prices, who is on a plan | Plans → Plans (`/plans/list`); "N active" → `/members/by_plan/<id>` | `plans-get` by ID only, **no price** |
| See discounts | Plans → Discounts (`/discounts`) | none |
| Find failed, overdue or open invoices | Payments → Invoices tabs *Overdue* / *Open*; Payments Forecast tab *Overdue* | none |
| Income for a period, by payment type | Payments → Transactions `/reports/transactions/<from>/<to>` | none |
| Stripe payouts / bank deposits (to reconcile against the bank) | Payments → Daily Deposits `/reports/deposits/<from>/<to>` | none |
| Upcoming billing and forecast | Payments → Payments Forecast; Reports → Financial → *Upcoming Payments* | `enrollment-list` has next-charge dates, not amounts |
| Who cancelled, paused or changed plan | Reports → Membership Change Report | `enrollment-list status=…` |
| Who is at risk / expiring / has a birthday | Reports → At Risk · Expiring Members · Celebrations | `checkins-*` for last check-in |
| Who attended a class; check someone in | Schedule → Check-Ins (date in path) or `/schedule/cal-<id>` | `classes-get expand=reservations`, `checkins-class-list` |
| Edit class types, coach pay rates, locations | Schedule → Classes → **Setup** → `/schedule/class-types` | `classes-type-list` (read only) |
| Edit or reschedule one class | Check-Ins ▸ class card ▸ **pencil** → *Edit class* (`/schedule/cal-<id>/edit/class/…`); `Save` needs a yes | none: class tools are read-only |
| Coach payroll | Reports → Payroll (needs coach check-ins and pay rates set) | none |
| Waivers, photo release, signed documents | Apps → Digital Documents `/documents`; profile → *Documents* | none |
| Lead pipeline; the website lead form | People → Leads `/people/leads`; Settings → Lead Capture | `customers-create` creates a lead (**WRITE-DATA**) |
| Staff list and roles | People → Staff `/people/staff`; profile → *Settings → User Role* | `customers-list role=coach` |
| See or add an API key | Settings → Security & Access → *API Keys* | none |
| Stripe, ACH, tax, retry settings | Settings → Billing & Payment; ACH Report → *ACH app configuration* | none |
| The gym's own PushPress tier and bill | Settings → Your PushPress Plan `/account` | none |
| Alerts staff get (payment failed, new lead…) | Communicate → Automatic Emails | none |
| Check whether the UI changed | `scripts/pp-extract.js` → `__pp.sidebar()`; see [drift-and-open-questions.md](references/drift-and-open-questions.md) | none |

## Action classes: what needs a yes first

| Class | Seen in the UI | Rule |
|---|---|---|
| **READ** | open a page, menu, drawer or tab; filter; search; date range | free |
| **DOWNLOAD** | `Download`, `Download CSV`, `Export Class registrations`, `Export appointments schedule (CSV)`, a download button inside Pro Metrics ▸ Export (opening that tab is READ) | writes a file to the user's machine: ask, naming the report |
| **WRITE-DATA** | `Save`, `Save changes`, `Add Note`, `Change Role`, `Add Sub-account`, `Check in`, Automatic Emails toggles | confirm the exact change |
| **MONEY** | `Create a Charge`, invoice `Create`, `Generate Invoice`, Charge A Guest, `Add Plan` and `Add Credit` on a profile, plan price / billing-date / discount edits | confirm person, amount and method; never retry a failed charge blindly |
| **OUTBOUND** | `Send Profile Setup Link`, `Send Reset Password Link`, `Request Payment Method`, text/email attendees, `Add Document` (attaching may email the person: see [people-and-plans.md §8](references/people-and-plans.md#8-digital-documents)); API `messages-*-send` | real people receive it: confirm recipients and wording |
| **DESTRUCTIVE** | `Delete` (profile, plan, class, class type, document, policy), `Merge`, cancel or downgrade a plan | confirm; prefer a reversible option |
| **CONFIG / SECURITY** | `Add API Key`, Stripe / bank settings, roles, `Staff app & Core access`, `Connect` on an integration | ask first; never print a key or secret |

A control can fall in more than one class: apply the strictest.

## Operating notes

- Work in **your own tab**. Use real pointer clicks for tabs and menus: a synthetic script `.click()` does not switch the
  People tabs. Element references go stale after a re-render, so look the element up again just before you click.
- Financial, Engagement, Pro Metrics and Payroll are **embedded analytics iframes** (`analytics.pushpress.com`); the
  parent page's DOM cannot see inside them.
- Many controls are **icon-only** (a class page's pencil and ⋮, the Attendance icons, row ⋮ menus), so text extraction
  cannot name them: find them by role or position, or take a small screenshot of a page with no people on it.
- A page-script tool's output is usually capped (about 2.5 K characters on the verified host): write results into a page
  element and read that page's text instead, but only after the element exists (without it a page-text read returns the
  whole page), and keep person pages out of any page-text read, because its header carries the page title, which is a
  person's name there.
- `scripts/pp-extract.js` is the structure-only extractor and sidebar reader (see *Binding*). Run
  `__pp.company('<company name>')` once per tab so the company-switcher button is left out of button lists.
- Details, snippets and the pitfalls list: [browser-technique.md](references/browser-technique.md). Host recipes:
  [hosts.md](references/hosts.md).

## Honest limits

Verified read-only on 2026-11-08 on one PushPress Core tenant (the *Core Pro Monthly* tier), through Claude in Chrome only;
other hosts are untested. No write flow was exercised (no save, create, charge, send, delete, merge or download): controls
that would are tagged `[not exercised]`. The sign-in procedure was observed in one session and not re-tested. The project
version this card was generalized from was checked by three fresh agents with that version only, never against a no-skill
baseline. This generalized copy had its own live read-only pass the same day: its extractor on about twenty admin pages,
the sidebar against the route map, and one staff profile (no member profile, no sign-in, no write flow). That pass found
and fixed defects, among them the extractor leaking a person's name through a profile heading, and the fixes were
re-checked on the pages they touch. Other tiers may differ; Grow, Train and the Staff and Members apps were never surveyed. PushPress changes its UI often: treat every path and label as a
strong hint to confirm, and use the drift procedure in
[drift-and-open-questions.md](references/drift-and-open-questions.md).

## Reference

`[observed]` seen in the live UI on 2026-11-08 · `[documented]` from PushPress's public help center or pricing page, not
seen live · `[not exercised]` the control exists but writes, sends or deletes, so it was not run. A statement that says it was
*reported* comes from an earlier note, was not re-verified here, and is hedged where it appears.

| File | Contents |
|---|---|
| [app-map.md](references/app-map.md) | Every route: sidebar label, path, reach-via, notes |
| [people-and-plans.md](references/people-and-plans.md) | People tabs, member profile, leads, plans and editor, discounts, documents |
| [schedule-and-checkins.md](references/schedule-and-checkins.md) | Calendar, classes, events, check-ins, class types, locations, appointments, payroll |
| [money-and-reports.md](references/money-and-reports.md) | Invoices, transactions, deposits, forecasts, ACH, reports, billing settings, products |
| [settings-and-admin.md](references/settings-and-admin.md) | Settings pages, security, staff and roles, apps, top bar, automatic emails |
| [browser-technique.md](references/browser-technique.md) | Driving a browser tab on this app; PII hygiene (tool names are the verified host's) |
| [hosts.md](references/hosts.md) | What a host needs, the tested matrix, recipes per host |
| [api-and-mcp-tools.md](references/api-and-mcp-tools.md) | The 44 API tools, conventions, recipes, what the API cannot do |
| [drift-and-open-questions.md](references/drift-and-open-questions.md) | What is verified vs documented, re-verification procedure, open questions |
| `references/<tenant>.md` | Optional, supplied by the project, not shipped: tenant facts (see *Know the tenant first*) |
| `scripts/pp-extract.js` | Structure-only page extractor and sidebar reader, run inside the browser page |
