# Verification status, drift, and open questions

This skill's UI claims were observed once, on **2026-11-08**, read-only, on one tenant (the *Core Pro
Monthly* tier). PushPress changes its UI often
(the top-bar *Product updates* panel is the changelog), so treat every path and label here as a strong
hint to confirm, not a fact to assert.

## Contents
1. [What was and was not exercised](#1-what-was-and-was-not-exercised)
2. [Re-verifying after a change](#2-re-verifying-after-a-change)
3. [Help-center claims, checked against the live UI](#3-help-center-claims-checked-against-the-live-ui)
4. [Open questions](#4-open-questions)

## 1. What was and was not exercised

| Exercised (read-only) | Seen, never run (writes, sends, charges, deletes or downloads) |
|---|---|
| every sidebar page (all 7 Settings pages, 10 Reports, 5 Payments, 4 Schedule, Products, Plans, Apps) | every `Save`, `Create…`, `Add…`, `Delete`, `Merge`, `Change Role` |
| People: all four tabs and one member profile, the staff profile | `Send Profile Setup Link`, `Send Reset Password Link`, `Request Payment Method`, text/email attendees |
| menus: Calendar *Create*, gear, *Public Calendar*; class-type and plan row menus; *Person* menu; invoice *Create* dialog (opened, then closed) | `Create a Charge`, `Generate Invoice`, `Charge A Guest`, any refund, plan pause / cancel / switch |
| the plan editor drawer (opened, then **Close**) | every `Download` / `Export` button |
| top bar: Search palette, release-notes panel; user menu | toggles on Automatic Emails and Lead Capture; Marketplace `Connect`; `Add API Key` |
| the public tenant pages listed in `app-map.md` §6 | Migration Assistant imports; the Insurance and Referrals forms |

Nothing was saved, sent, charged or deleted. Dialogs and drawers opened for inspection were closed and
confirmed gone.

## 2. Re-verifying after a change

Do this when a path 404s, a label is missing, or *Product updates* mentions your area.

1. Install the extractor from `scripts/pp-extract.js` on a signed-in tab.
2. `await __pp.sidebar()` and compare the `LINK … -> path` lines with the table in
   [app-map.md](app-map.md). A missing, renamed or new path is drift. (Query strings and hashes print
   in brackets; compare paths only. The unlabeled `/` line is the logo, and labels carry their badges.)
3. Spot-check three or four **canary pages** — e.g. `/people/members`, `/plans/list`, `/payments`,
   `/schedule/class-types` — with `await __pp.wait(); __pp.store('Label')` and compare headings, tabs and
   column headers with the area file.
4. Open *Product updates* (top bar) and read the newest entries for your area.
5. Record what changed: fix the area file and `app-map.md` and change the **date at the top** if you
   maintain a copy, or put the correction in your tenant overlay and report it upstream. A stale map is
   worse than none.
6. `__pp.clear()`.

## 3. Help-center claims, checked against the live UI

From the help-center research done while building this skill (the research file is not shipped), its
"likely drift" list:

| Claim to check | Live result |
|---|---|
| "Events" has no end-user surface | **Wrong for this UI:** Schedule ▸ Events (`/schedule/events`) and Calendar ▸ Create ▸ Event exist |
| Pro Metrics moved into Financial (2024) | **Not here:** Pro Metrics is still its own Reports page |
| Dashboard 2.0 may be the only dashboard | **Yes:** the live dashboard has the AI Assistant card, KPI tiles and the *Important* panel |
| Click-to-Cancel request tracking "planned" | **Appears shipped:** the dashboard *Important* panel has a **Cancellation requests** list |
| Admin sits at `app.pushpress.com` | **Partly:** the root 404s; sign-in is at `/login`; the app itself runs on the tenant origin |
| 2FA is under the profile menu | **Not found** on My Profile or Security & Access — unresolved |
| Two ACH fee schedules | unresolved; confirm on a real deposit |
| Staff App product sales are beta | not checked |

## 4. Open questions

1. **Password step:** why does `autofill_credential` return `autosubmit_failed` and leave the field empty,
   when the session still ends up authenticated? Needs a controlled retry with the user watching.
2. **Where is two-factor security** in this UI?
3. **Financial tab URLs:** only `?tab=Upcoming%20Payments` was confirmed; the other tabs' parameter values
   were not.
4. **What do `Charge A Guest` and `Product Categories` open** (`?create=…`, `?manage_categories=…`)?
5. **Lead statuses** beyond the default four (and their names).
6. **Does the plan editor accept a quantity of 0?** (See the quantity trap in
   [people-and-plans.md](people-and-plans.md#6-plan-editor-drawer).) Testing needs a save on a real
   plan — only with the user's go-ahead and a plan they choose.
7. **Which of two ACH fee quotes is right**, and what a gym actually pays per deposit.
8. **Where is the member-facing messaging** (campaigns, texts)? Core's sidebar has none; documentation
   says it lives in Grow, which a gym may not license.
