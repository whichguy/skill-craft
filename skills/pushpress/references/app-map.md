# PushPress Core — route index

Verified read-only on **2026-11-08** against one tenant, `https://<tenant>.pushpress.com` (product label
"PushPress CORE"). Row = one page. **Reach via** is how a person gets there; paths are what to
`navigate` to. Re-check with `scripts/pp-extract.js` → `__pp.sidebar()` before relying on this after
any hint the UI changed ([drift-and-open-questions.md](drift-and-open-questions.md)).

## Contents
1. [Sidebar](#1-sidebar-as-observed-top-to-bottom)
2. [Pages not in the sidebar](#2-pages-not-in-the-sidebar)
3. [URL shapes](#3-url-shapes)
4. [Detail routes and ID prefixes](#4-detail-routes-and-id-prefixes)
5. [Top bar and shell](#5-top-bar-and-shell)
6. [Public tenant pages (no login)](#6-public-tenant-pages-no-login)

## 1. Sidebar, as observed (top to bottom)

Groups (▸) are collapsed in the DOM until opened and re-collapse after each navigation; the group that
holds the current page stays open.

| Sidebar label | Path | Notes | Detail in |
|---|---|---|---|
| Dashboard (*New* badge) | `/` → `/main` | widgets, report shortcuts, AI assistant | [§ Dashboard](money-and-reports.md#dashboard) |
| People | `/people` → `/people/members?membershipRole=member` | four tab routes | [people-and-plans](people-and-plans.md) |
| Communicate ▸ Automatic Emails | `/communications/automatic` | only child; 17 staff-alert toggles | [settings-and-admin](settings-and-admin.md) |
| Appointments | `/appointments` | top-level link, not a group | [schedule-and-checkins](schedule-and-checkins.md) |
| Plans ▸ Plans | `/plans/list` | plan list; editor is a drawer on this URL | [people-and-plans](people-and-plans.md) |
| Plans ▸ Discounts | `/discounts?type=…` | tabs Membership / Product / Event | [people-and-plans](people-and-plans.md) |
| Products ▸ Products | `/products` | | [money-and-reports](money-and-reports.md) |
| Products ▸ Charge A Guest | `/payments?create=…` | `[not exercised]` presumably opens the *Create invoice* dialog for a guest | [money-and-reports](money-and-reports.md) |
| Products ▸ Product Categories | `/products?manage_categories=…` | `[not exercised]` | [money-and-reports](money-and-reports.md) |
| Products ▸ Pre-Orders | `/preorders` | | [money-and-reports](money-and-reports.md) |
| Products ▸ Discounts | `/discounts?type=…` | same page as Plans ▸ Discounts | [people-and-plans](people-and-plans.md) |
| Schedule ▸ Calendar | `/schedule` | week view | [schedule-and-checkins](schedule-and-checkins.md) |
| Schedule ▸ Classes | `/schedule/classes` | list view; has **Setup** → class types | [schedule-and-checkins](schedule-and-checkins.md) |
| Schedule ▸ Events | `/schedule/events` | | [schedule-and-checkins](schedule-and-checkins.md) |
| Schedule ▸ Check-Ins | `/calendar/checkins` → `/calendar/checkins/MM/DD/YYYY` | opens on today | [schedule-and-checkins](schedule-and-checkins.md) |
| Payments ▸ Invoices | `/payments` | | [money-and-reports](money-and-reports.md) |
| Payments ▸ Transactions | `/reports/transactions` → `…/<from>/<to>` | defaults to the current month | [money-and-reports](money-and-reports.md) |
| Payments ▸ Payments Forecast | `/reports/payments` | | [money-and-reports](money-and-reports.md) |
| Payments ▸ Daily Deposits | `/reports/deposits` → `…/<from>/<to>` | | [money-and-reports](money-and-reports.md) |
| Payments ▸ ACH Report | `/reports/ach` | same page as Apps ▸ ACH | [money-and-reports](money-and-reports.md) |
| Reports ▸ Product Sales Report | `/reports/retail` → `…/<from>/<to>` | | [money-and-reports](money-and-reports.md) |
| Reports ▸ Payroll | `/reporting/export-payroll` | embedded analytics; **full page load** | [schedule-and-checkins](schedule-and-checkins.md) |
| Reports ▸ No Show / Late Cancel | `/no-show` | | [money-and-reports](money-and-reports.md) |
| Reports ▸ Celebrations | `/reports/celebrations` | | [money-and-reports](money-and-reports.md) |
| Reports ▸ Expiring Members | `/members/expiring` | | [money-and-reports](money-and-reports.md) |
| Reports ▸ Membership Change Report | `/reports/subscription_change` → `…/<from>/<to>` | | [money-and-reports](money-and-reports.md) |
| Reports ▸ At Risk Report | `/members/risk` | | [money-and-reports](money-and-reports.md) |
| Reports ▸ Financial | `/reporting/financial?tab=…` | embedded analytics | [money-and-reports](money-and-reports.md) |
| Reports ▸ Engagement | `/reporting/engagement?tab=…` | embedded analytics | [money-and-reports](money-and-reports.md) |
| Reports ▸ Pro Metrics | `/reporting/pro-metrics?tab=…` | embedded analytics | [money-and-reports](money-and-reports.md) |
| Insurance | `/insurance` | third-party quote form (Authentic); not gym data | [settings-and-admin](settings-and-admin.md) |
| Apps ▸ App Store | `/app-store` | tabs Discover Apps / My Apps | [settings-and-admin](settings-and-admin.md) |
| Apps ▸ ACH | `/reports/ach` | duplicate of Payments ▸ ACH Report | [money-and-reports](money-and-reports.md) |
| Apps ▸ Digital Documents | `/documents` | waivers and policies to sign | [people-and-plans](people-and-plans.md) |
| Marketplace | `/marketplace` | partners and integrations | [settings-and-admin](settings-and-admin.md) |
| Updates (*New* badge) | external `hub.pushpress.com/whiteboard/index.html#top` | PushPress changelog; leaves the app | — |
| Settings ▸ Your PushPress Plan | `/account` | the gym's own PushPress tier | [settings-and-admin](settings-and-admin.md) |
| Settings ▸ Settings | `/settings/client` | brand, contact, business info; read-only until *Edit* | [settings-and-admin](settings-and-admin.md) |
| Settings ▸ Billing & Payment | `/settings/billing-and-payment` | Stripe, tax, retries | [money-and-reports](money-and-reports.md) |
| Settings ▸ Lead Capture | `/settings/leads` | lead-form builder | [settings-and-admin](settings-and-admin.md) |
| Settings ▸ Migration Assistant | `/migration-assistant/` | bulk member import | [settings-and-admin](settings-and-admin.md) |
| Settings ▸ Policies | `/settings/policies` | | [settings-and-admin](settings-and-admin.md) |
| Settings ▸ Security & Access | `/settings/security` | API keys | [settings-and-admin](settings-and-admin.md) |
| Refer and earn $250 | `/referrals` | referral form; do not submit | [settings-and-admin](settings-and-admin.md) |

Labels print with their badges (`Dashboard New`, `Updates New`), and `__pp.sidebar()` also prints one unlabeled link to `/`
(the logo) ahead of Dashboard; neither is drift. A live pass on 2026-11-08 compared the extractor's output with this table:
the same 44 labelled links and 8 groups, and no other difference.

## 2. Pages not in the sidebar

| Path | What | Reach via |
|---|---|---|
| `/schedule/class-types` | **Class types** list | Schedule ▸ Classes ▸ **Setup**; or Calendar ▸ gear ▸ *Class types* |
| `/locations` | **Locations** list (`+ Location`) | Calendar ▸ gear ▸ *Locations* |
| `/appointments/settings` | Appointment types, packages, discounts, pay rates | Appointments ▸ **Setup** |
| `/people/leads`, `/people/non-members`, `/people/staff` | the other People tabs | People ▸ tab (real click) or by URL |
| `/user/<id>` | person profile (`#staff-details` for a staff view) | any name link; user menu ▸ *My Profile* |
| `/members/by_plan/<id>` | members on one plan | Plans ▸ "N active" link |
| `/landing/plans` | plan landing-page settings (beta) | banner on `/plans/list` |
| `/app-store/<slug>`, `/integrations/app/<slug>` | one app's page / configuration | App Store ▸ *Learn more* / *Configure* |

## 3. URL shapes

- **Date-ranged reports** — `/reports/<name>/<YYYY-MM-DD>/<YYYY-MM-DD>` for `transactions`, `deposits`,
  `retail`, `subscription_change`. The bare path opens the current calendar month
  (observed `2026-11-01/2026-11-30`). Changing the range in the URL is the dependable way to set it.
- **Check-ins by day** — `/calendar/checkins/MM/DD/YYYY`.
- **Embedded analytics** — `/reporting/<name>?tab=<Tab label>`; `?tab=Overview` is the default and
  `?tab=Upcoming%20Payments` was confirmed to select that tab.
- **Sidebar links with parameters** — `?type=` (discounts), `?create=` (payments), `?manage_categories=`
  (products). Parameter *values* were not captured; click the sidebar link rather than guessing them.
- **People tabs** carry their own filter keys: `membershipRole` on members and non-members, `leadStatus`
  on leads (default `new lead,attempted,contacted,in discussion`).

## 4. Detail routes and ID prefixes

| Route | Entity | ID shape |
|---|---|---|
| `/user/<id>` | person (member, lead, staff) | `usr_` + hex (6–32 chars seen) |
| `/discounts/<id>` | discount | `dis_` + hex |
| `/products/view/<id>` | product | `prd_` + hex |
| `/preorders/<id>` | pre-order | `preorder_` + hex |
| `/documents/view/<id>` | digital document | not captured |
| `/payments/<id>` | invoice / payment | not captured |
| `/schedule/<id>` | class or event instance | `cal-` + hex (hyphen). Links on the Check-Ins page use `/calendar/view/<id>` and land here |
| `/schedule/<id>/edit/class/<id>` | the **Edit class** form (`Cancel` / `Save`), opened by the class page's pencil icon | `cal-` + hex, twice |
| `/members/by_plan/<id>` | plan's member list | `plan_` + hex |

The API uses `cal_` (underscore) for calendar items but one live check-in carried `cal-`; do not assume
the two spellings are interchangeable ([api-and-mcp-tools.md](api-and-mcp-tools.md) §3).

## 5. Top bar and shell

Top bar on every page: sidebar collapse toggle · company switcher "<company name> ⌄" ·
**Search** (command palette) · **Toggle Assistant** (AI assistant, beta) · **Product updates** ("What's
new on PushPress" release notes, opens a right-hand panel) · **Support and updates** (help). Bottom-left:
user menu → **My Profile** (`/user/<id>#staff-details`) and **Logout**. A small red chip at the top
right during automation is the Claude in Chrome overlay, not part of PushPress.

## 6. Public tenant pages (no login)

| Path | What |
|---|---|
| `/landing/plans/<plan_id>` | public plan page; returns plan JSON (`amount`, `amountRecurring`, `quantityAvailable`, `limitQuantity`) |
| `/open/subscribe/<code>` | older-style public sign-up link |
| `/open/policy/` | public policy page, linked from the lead form |
| Calendar ▸ *Public Calendar* icon | "Public / Embeddable Calendar" option for the website schedule embed |

A gym's website sign-up links usually point at these pages; a project's tenant overlay is the place to
record which ones it uses.
