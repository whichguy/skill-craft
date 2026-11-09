# Driving a browser tab on the PushPress admin

How to work this app through a browser tool without breaking it or leaking member data. The tool names below are
Claude in Chrome's (`mcp__claude-in-chrome__*`), the one host this skill was verified on; [hosts.md](hosts.md) lists the
capabilities they stand for. Earned on 2026-11-08; each pitfall below happened.

## Contents
1. [Setup and tidy-up](#1-setup-and-tidy-up)
2. [How the app behaves](#2-how-the-app-behaves)
3. [Reading pages without leaking people](#3-reading-pages-without-leaking-people)
4. [Extraction toolkit](#4-extraction-toolkit)
5. [Safe interaction patterns](#5-safe-interaction-patterns)
6. [Pitfalls table](#6-pitfalls-table)

## 1. Setup and tidy-up

Setup, sign-in and tidy-up for the verified host are one recipe, kept in
[hosts.md](hosts.md#recipe-claude-in-chrome) so that there is a single copy. The two rules that matter most here: work
in **your own tab**, and at the end run `__pp.clear()` (it removes the page-side storage and dump element) before you
release credentials and close the tabs you opened.

## 2. How the app behaves

- **Single-page app.** Clicking a link routes client-side and keeps `window` state, so a script can
  crawl by clicking. **Some routes do a full page load** (`/reporting/export-payroll` killed a crawl
  mid-script, "Inspected target navigated or closed") — that wipes `window`. Keep results in
  `sessionStorage`, or `navigate` per page, which is slower but always safe.
- **Sidebar groups** are absent from the DOM until opened and re-collapse after every navigation; open
  the group (click its `button[aria-expanded]`) before looking for a child link, or navigate by URL.
- **Tabs and many menus need a real click.** A synthetic JS `.click()` on the People tabs did nothing;
  `find` → `computer left_click ref=…` worked. Sidebar `<a>` links *do* respond to `.click()`.
- **Refs go stale** after any re-render (switching a tab re-renders the tab bar). Call `find`
  immediately before the click. A `find` can also return the neighbouring control — one "Search" ref
  opened *Product updates* — so confirm with a small screenshot when the target matters.
- **Editors are drawers/dialogs.** The plan editor opens over `/plans/list` with no URL change; leave
  with `Close`, then check `document.querySelectorAll('[role=dialog],[aria-modal=true]')` is empty.
- **Unknown paths render the calendar** (e.g. `/schedule/locations`) instead of a 404 — confirm by
  title and URL that you reached the page you meant.
- **Report URLs carry the date range** (`/reports/<name>/<from>/<to>`); edit the URL to change it.
- **Embedded analytics** (Financial, Engagement, Pro Metrics, Payroll) are cross-origin iframes
  (`analytics.pushpress.com`). `read_page`, `get_page_text` and page JS see only the tab bar; read the
  content from a small screenshot or `zoom`, and expect member names in the tables.
- The red chip at the top right while automating is the Claude in Chrome overlay.

## 3. Reading pages without leaking people

Gyms often serve minors, and a parent's email sits on a child's profile. Three leaks happened in one
session even with a "structure-only" extractor:

| Leak | Where | Fix |
|---|---|---|
| A member's **name and a parent's email** inside a *button label* | profile page, `read` of buttons | drop any label containing `@`; mask `Select/Edit/View… <name>` and `… for <name>` |
| The person's **name and `usr_` ID** in the *page title and URL* | `get_page_text` header on `/user/<id>`, and the title-and-URL footer that Claude in Chrome adds to every tool result | never `get_page_text` a person page; open one only when you must, make one call, and navigate to a neutral page before anything else |
| The person's **name as the page heading**, and **selected values** shown as button text (gender, role) | a person page, in `h` and `btn`; found by a live pass on 2026-11-08 | on a person route the extractor removes the page's text-field values and a two-word page title, and records only a combobox's label; the rest is still yours to keep out of the repo |
| **Client names** in a report | a screenshot of Financial ▸ Upcoming Payments (iframe) | screenshot only when needed, small scale, and treat as member data |

Rules: record **structure only** — labels, paths, column headers, ID **prefixes** (`usr_`, `plan_`),
counts; never names, emails, phones, birthdays, addresses, IDs, or screenshots of person pages and
reports. Check only whether a password field is empty (`value.length > 0`); never read its `value` or its length. If
something personal reaches your
context, do not repeat it in any file, journal or message; purge it from `sessionStorage`.

## 4. Extraction toolkit

`scripts/pp-extract.js` installs `window.__pp` (see its header for exact calls):

- `await __pp.sidebar()` — the whole sidebar tree with paths (the drift check); its lines also go to `#pp-dump`.
- `await __pp.wait(); __pp.store('Label')` — one page's structure, saved to `sessionStorage`.
- `__pp.dump([...])` then `get_page_text` — read many pages at once. Read page text only when `#pp-dump` exists: without
  it the tool returns the whole page, and its first line says which element it read (`<article>` is the dump, `<main>`
  is the page).
- `__pp.clear()` — clean up.

Tool quirks it works around:

| Quirk | Workaround |
|---|---|
| `javascript_tool` results are cut at ~2.5 K characters | write results into `<article id="pp-dump">` and read with `get_page_text` |
| An `async` IIFE returns `{}` | use top-level `await` |
| `const` in one call is invisible to the next | attach helpers to `window` |
| Output containing a URL query string is blocked ("[BLOCKED: Cookie/query string data]") | print `searchParams.keys()`, not values |
| A full page load wipes `window` | persist in `sessionStorage`; restore with `(0, eval)(sessionStorage.getItem('__pp_lib'))` |
| `navigate` leaves the SPA still loading | `await __pp.wait()` before extracting |

## 5. Safe interaction patterns

1. **Open a menu to learn its items:** `find` the button → `left_click` → `find` "items in the open menu"
   (or `read_page`) → **`key Escape`** → confirm no dialog is open. Never pick an item.
2. **Open an editor to learn its fields:** open, read labels and toggles, click **Close**, never `Save`.
3. **Learn what a link does:** hover or read its `href`; follow only navigation links.
4. **Before any click, name its action class** ([`SKILL.md`](../SKILL.md)). A `Send…`, `Create a
   Charge`, `Delete`, `Merge`, `Download` or `Request…` is not exploration.
5. If a JavaScript `alert`/`confirm` could appear, warn the user first — a native dialog freezes the
   extension until a human dismisses it.

## 6. Pitfalls table

| Symptom | Cause | Fix |
|---|---|---|
| `app.pushpress.com/` shows "We couldn't find that page" | the root is a 404 on the marketing site | use `…/login` or the tenant login |
| `autofill_credential` → `autosubmit_failed`, password field empty | password step does not take the fill | try once, wait ~30 s, re-check; then ask the user |
| People tabs do not change | synthetic `.click()` | real click via `find` + `computer` |
| Script dies with "Inspected target navigated or closed" | a link did a full page load | store progress in `sessionStorage`; navigate per page |
| Sidebar link "not found" | its group collapsed again | open the group first, or navigate by URL |
| Result ends with "[TRUNCATED]" | ~2.5 K output cap | dump to `<article>` and `get_page_text` |
| Financial tab shows nothing to `read_page` | content is in a cross-origin iframe | screenshot / `zoom` |
| A different page opened than expected | stale or neighbouring ref | re-`find`, verify with a screenshot |
| A control you can see is missing from the extractor's output | **icon-only** button (no text, no `aria-label`): the class page's pencil and ⋮, Attendance icons, row ⋮ menus — the extractor reports only a count | `find` ("pencil edit icon…") or a small screenshot |
| A number on a report is missing from the extractor's output | KPI panels are plain text, not headings (e.g. the Membership Change Report's panel) | `find` the labelled values, or read the panel's `complementary` region |
| A heading or button is missing from the extractor's output on a long page | its caps: 25 headings, 45 buttons, 50 labels, 30 links (a person profile reaches them; its Account Management buttons fall after the 45th) | `find` it |
| `get_page_text` returned the whole page (on the Dashboard: people's initials and KPI figures) | `#pp-dump` did not exist, so the tool fell back to `<main>`; its first line says `Source element: <main>` | call `dump()` or `sidebar()` first and read page text only when it says `<article>`; stop reading and do not repeat what was shown |
