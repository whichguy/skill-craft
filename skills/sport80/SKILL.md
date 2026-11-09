---
name: sport80
description: >-
  Use for the USA Weightlifting Sport80 portal (usaweightlifting.sport80.com): the owner's personal member account
  (memberships, certifications, entries, results, orders) and club account (members, events, sanctioning, finance,
  affiliations, and the meets and results of the club's athletes), plus public results and rankings. Catalogues every
  capability the portal exposes per role, runs the reads through the owner's already signed-in browser, and gates
  writes, payments and email behind explicit confirmation. Triggers: "Sport80", "USAW club", "my USAW membership",
  "club roster", "meet results", "club results".
version: 0.1.0
license: MIT
platforms:
  - linux
  - macos
metadata:
  skill_craft:
    kind: mixed
---

# sport80

Read the owner's USA Weightlifting Sport80 accounts, personal and club, and run what the portal exposes there, without
ever handling a password. The portal is server-driven, so its menus are the capability list: this skill catalogues them
per role, generates the exact browser snippet for each read, and tells the agent how to walk the owner through the rest.

Not for other federations on Sport80 (same platform, untested), and not for anything that moves money or sends messages
without the owner's explicit yes.

## Binding

`SKILL_ROOT` is the directory of this loaded `SKILL.md`, not the working directory. Scripts are Python 3 standard
library and make no network calls.

```sh
SKILL_ROOT="/absolute/directory-containing-the-loaded-SKILL.md"
S80="$SKILL_ROOT/scripts/sport80"
```

## What it reaches

Three scopes, one login. `personal` is the login's own member role. `club` is a club role the login administers,
addressed by `body_cid`. `public` needs no login. List with `"$S80" catalog` (add `--role`, `--area`, `--mode`, `--data`,
`--runnable`); inspect with `"$S80" show ID`; coverage and the honest gaps with `"$S80" coverage`.

| Area | What it holds |
|------|---------------|
| `account`, `dashboard` | roles, menus, profile form, settings, sessions, support; the personal dashboard widgets |
| `member` | one person's profile tabs: memberships, roles, certifications, screening, SafeSport, eligibility, addresses, entries, results |
| `members` | the club roster tools: quick search, Smart List, charts, add, email, reports |
| `club` | the club's own profile, memberships, insurance, addresses, notes |
| `events`, `sanction` | event finder, public search, event administration, sanctioning requests |
| `results` | results and rankings: the club's athletes' meets with a club role, every event with the personal role, national when public |
| `orders`, `finance`, `admin`, `affiliation` | transactions, cart, bulk renewal, queued reports, Stripe, invoices, discount codes, transfers |

The same option reads differently per role. Results under `--role club` lists the meets the club's athletes entered and
how many results each produced (2026 meets, checked 2026-11-08: 18 meets and 142 results, against 387 events unscoped
under `personal`). Take a meet's `event_id` from a row's View link and `results.event` returns that meet's public results,
all lifters. A club member's own tabs (memberships, certifications, entries, results) are in the club role's menus but were
never read for a member, because that exposes a person's record and some are minors (gap G9). Find the member with
`members.quick_search`; read a tab only after the owner names the member and the tab, and expect `js` to ask for
`--unverified`.

## Trust boundary

- Local scripts never receive credentials and make no requests; they print catalogue text and browser code.
- Code running inside the owner's signed-in page may use session tokens transiently in function scope. No token reaches a
  global, a log, an error or a result; headers are set per origin; UUID-shaped strings are redacted.
- Passwords, 2FA codes and card or bank details are the owner's alone. Sign-in is the owner's browser and password manager.
  If a code or CAPTCHA appears, stop and ask.
- Rows are returned only as asked: sensitive tables give counts unless fields are named.

## Run loop

1. Classify the request against `"$S80" catalog`. If it is `guided` or `owner-only`, read `show ID`, follow its `confirm`
   text, and stop short of the final action until the owner says yes to that exact target and effect.
2. Have a tab on `https://usaweightlifting.sport80.com` that is signed in (not needed for public reads). Load the runtime
   once per tab: run `"$S80" runtime` and execute it in the tab. Reload clears it.
3. `"$S80" js ID --role personal|club|public|<body_cid> [--param k=v] [--filter k=v] [--rows N] [--fields a,b]`, then execute the
   printed snippet in the tab. Public results and rankings default to `public`; tab-resolved entries need a login.
4. Read the envelope: `ok`, `role`, `verified`, and for tables `total`, `returned`, `complete`, `next`. Never present a
   partial page as the whole; say which role and scope produced it.
5. On `ok: false` follow the map below. Report counts and answers, not raw personal data. Never write member data into
   files, commits or notes.

## Failure map

| `error` | Meaning and next step |
|---------|-----------------------|
| `AUTH_REQUIRED` | the session ended (a ping also failed): ask the owner to sign in, then retry |
| `PERMISSION_DENIED`, `FORBIDDEN`, `RANKINGS_REFUSED` | this role lacks the right or needs an id: report it, do not retry |
| `MISSING_PARAM`, `BAD_PARAM`, `FILTER_REQUIRED`, `UNKNOWN_FILTER`, `FIELDS_REQUIRED` | fix the request; nothing was fetched |
| `UNEXPECTED_REDIRECT`, `UNEXPECTED_RESPONSE`, `NOT_A_TABLE`, `TAB_NOT_FOUND`, `NETWORK`, `SERVER` | the portal behaved unexpectedly: report, do not loop |
| `CHALLENGE`, `THROTTLED` | stop at once and ask the owner |
| `NOT_RUNNABLE` | guided or owner-only: use `show ID` |

## Safety in one paragraph

Every entry has a `mode` (read, guided, owner-only), `effects` (read, export, write, outbound, financial, security) and
`data` (public, personal, sensitive). Writes, exports, email, subscriber groups, bulk renewals and anything involving money
are guided and need an explicit yes; 2FA, passwords, sign-out and session changes are owner-only; payment is always the
owner's. Minors' records are in scope of the roster tools: use the smallest answer. Details in `references/safety.md`.

## Reference

- `references/access.md`: sessions, roles and scope, tokens, sign-in, errors, politeness.
- `references/protocols.md`: the request shapes the runtime speaks.
- `references/safety.md`: classes, confirm rules, never-do list, personal-data rules.
- `references/hosts.md`: what a host needs, the tested matrix, recipes per host.
- `references/capabilities.json`: the catalogue, the single source of truth; `coverage` inside it is the ledger.

## Honest limits

Verified live on 2026-11-08 with the owner's personal and club roles through Claude in Chrome only; other hosts are
untested. Entries marked `none` were seen in a menu or the front-end code and never exercised, so they are listed but not
offered as runnable; `"$S80" coverage` lists what was never observed (event admin panels, row actions, every write and
payment flow). Maintenance: `"$S80" discover` prints a crawler to run in the tab, `"$S80" diff LIVE.json` compares its
output with the catalogue, `"$S80" check` validates the catalogue and the browser code.
