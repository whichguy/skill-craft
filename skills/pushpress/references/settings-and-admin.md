# Settings, security, apps and admin tools

Verified read-only on **2026-11-08**. `[observed]` is the default; `[documented]` = help center only;
`[not exercised]` = the control exists but writes, sends or deletes, so it was not run. Billing settings
are in [money-and-reports.md](money-and-reports.md#5-billing-settings).

## Contents
1. [Settings pages](#1-settings-pages)
2. [API keys](#2-api-keys-settings--security--access)
3. [Apps, Marketplace, Insurance](#3-apps-marketplace-insurance)
4. [Automatic emails](#4-automatic-emails-communicate)
5. [Top bar and user menu](#5-top-bar-and-user-menu)
6. [Not found / unresolved](#6-not-found--unresolved)

## 1. Settings pages

Sidebar ▸ **Settings** had exactly seven children.

| Page | Path | Contents |
|---|---|---|
| **Your PushPress Plan** | `/account` | the gym's own PushPress subscription: the current tier, an *Upgrade Core* option, *Add-Ons* (Grow, Train, Branded App, each a *Learn more* link to pushpress.com), buttons `Payment method & invoices`, `Cancel or downgrade plan` (**MONEY / DESTRUCTIVE**), `Upgrade`, `Book a demo` |
| **Settings** | `/settings/client` | read-only until `Edit` on a section. **Brand**: logos (PNG/JPEG, 52×52 suggested), colour, website, *Role names* (the words for coach and member). **Email Branding**: display information, social links. **Contact Information**: company name, email, phone, address, *Timezone*. **Business Information**: gym type, business license. A "Give support a chat" link |
| **Billing & Payment** | `/settings/billing-and-payment` | see [money-and-reports.md](money-and-reports.md#5-billing-settings) |
| **Lead Capture** | `/settings/leads` | builder for the public lead form; saves with `Save changes` (below) |
| **Migration Assistant** | `/migration-assistant/` | bulk member import: `Start an import`; steps *Upload members to migrate → Assign plan details*; counters *Assign plans (N)*, *Created members (N)*; `Create member(s)`; a wide table (name, email, status, plan, plan price, payment type, next billing date, discount, remaining sessions, expiration, plan start, member since, imported check-ins, DOB, gender, address, parent account). **WRITE-DATA** `[not exercised]` |
| **Policies** | `/settings/policies` | tabs *All · Active · Inactive*; `Create Policy`; table Title · Last Updated · Status · Actions; the public copy is at `/open/policy/` |
| **Security & Access** | `/settings/security` | **API Keys** only ([§2](#2-api-keys-settings--security--access)) |

**Lead Capture** sections: *General* (page title, description/upsell), *Collect additional data* (a
`Show…` and a `Make… required` toggle for each of Phone number, Date of birth, Postal code, Referral
source, Preferred communication, Message/note), *Client objectives* (up to four objective lines, `Add
objective`, `Show client objectives on lead form`), *Lead types* (`Show lead types on lead form`),
*Notifications & redirect* (`Notify coach`, `Notify front desk`, `Send confirmation to lead`,
*Post-submission redirect URL*), and a live **Lead form preview** (Desktop / Mobile; First Name\*, Last
Name\*, Email\*, Phone\*, Date of Birth, objectives, "How did you hear about us?"). The preview's
`Submit` is part of the preview — do not press it. Changes go live on `Save changes`.

## 2. API keys (Settings ▸ Security & Access)

`/settings/security` shows one heading, **API Keys**, an `Add API Key` button and a table **Name ·
Description · Create Date · Last Used Date · Actions** (`Edit`). This is where the key behind the
`pushpress` MCP server is issued, and where a leaked one is replaced.

- **Never print, copy into chat or write a key value anywhere.** Creating a key is **CONFIG / SECURITY**:
  ask first, and have the user place the value straight into the MCP server's environment or their secret
  store, never through chat. Treat a key that reaches a transcript as burned: the user rotates it, not you (you could
  not pass the new key on without reading it).
- **Routes that show a key without a print command.** Do not run these commands or read these files: ask the user to look
  and tell you what they find, never the key. They are: `ps`, `env`, `printenv` or `set` output that shows the server's
  arguments or any environment you know or suspect holds the key (the server is started as
  `mcp start --api-key <key>`, so the key is in its command line; `pgrep -a` shows it too), `claude mcp list` (each
  server's command line) or `claude mcp get` (its command line and environment), or the host's equivalent, shell
  history, a search or echo that prints the key's value (`grep -r` over files that may hold it, `git log -p -S`,
  `echo $VAR` of the key's variable), a file or profile you know or suspect holds the key (`.env`, a shell profile, the
  PushPress server's entry in an MCP config), and a verbose or traced run that sends the key (`curl -v`, `set -x`).
  Exempt: a check that prints no value (`ps -o pid,comm`, `env | cut -d= -f1`, `[ -n "$VAR" ]`), the API Keys table (it
  lists no value), the webhook tools of [api-and-mcp-tools.md](api-and-mcp-tools.md) (follow that file's rules for them,
  and never print a secret one returns), and another server's entry in an MCP config read on its own (for example
  `jq '.mcpServers.<name>'`, not the whole file). To add or change a server in a shared MCP config, the PushPress one
  included, write the edit with a filter whose output goes straight to a file and never to the screen (for example
  `jq '…' f > f.new && mv f.new f`; rewriting the file this way is not writing the key), or have the user do it. To test
  that the key works, call `company-get`.
- *Last Used Date* is the quick way to see which key is live before revoking one `[not exercised]`.

## 3. Apps, Marketplace, Insurance

- **App Store** `/app-store` — tabs *Discover Apps / My Apps*, filters *Type* and *Category*, and a note
  "Available with your PRO plan". The catalogue lists PushPress's own apps (the ACH and Digital Documents apps are the
  ones other pages here depend on) and third-party integrations; which of them a gym has installed is that gym's own
  business and is not recorded here. Each has *Learn more* (`/app-store/<slug>`) or *Configure* (`/app-store/<slug>`
  or `/integrations/app/<slug>`).
- **Marketplace** `/marketplace` — tabs *All · Integrations · Partners*, `Sort: Featured`, search,
  `Connect` on an integration (**CONFIG**, `[not exercised]`).
- **Insurance** `/insurance` — a third-party quote form ("Get a quote in minutes", provided by Authentic
  Services). It is marketing for a partner, not gym data. It pre-fills the gym's email; **do not submit**.
- **Referrals** `/referrals` — a form to refer another gym for $250. Do not submit.

## 4. Automatic emails (Communicate)

Communicate ▸ **Automatic Emails** (`/communications/automatic`) — "Keep your gym running smoothly with
automated updates about members, payments, and staff. Toggle any alert on or off as needed." Most are
**alerts to staff**, not member newsletters, but check a row's recipient before assuming (see *Document Ready to
Sign* in [people-and-plans.md §8](people-and-plans.md#8-digital-documents)): open the row's workflow, then
close it without saving. Table **Email Trigger · Category · Status**, with row
selection ("0 selected out of 17"). The 17 triggers:

| Category | Triggers |
|---|---|
| Billing | Billing Method Updated |
| Invoices | Payment Failed · Payment Succeeded · Refund Issued |
| Subscriptions | Plan Switch · Subscription Cancelled · Punchcard Completed · Recurring Subscription Due |
| Product | Low Inventory |
| People | New Person · Staff Assignment · New Lead · Document Ready to Sign · Migration Account Setup Request · Email Update |
| Schedule | Event Registration |
| Reports | Daily Summary |

Flipping a toggle changes who gets alerted (**WRITE-DATA**, `[not exercised]`). Member-facing marketing
(campaigns, workflows, texts) is **Grow**, a separate paid add-on `[documented]`; nothing in Core's sidebar
is a campaign tool.

## 5. Top bar and user menu

- **Search** — command palette, "Search for a person or a page", with quick actions (*Add Member*, *Add
  Lead*, *Create Invoice*, *See all members*, *Dashboard*, *Manage Staff*, *Manage Plans*, *Appointments*).
- **Toggle Assistant** — AI assistant panel (beta; it reads gym data, so treat what it returns as
  member data).
- **Product updates** — "What's new on PushPress": the in-app release notes (billing fixes, member
  portal, classes and appointments). Check here when a page does not match this skill.
- **Support and updates** — help and chat.
- **Company switcher** ("<company name> ⌄") — lists the gym entities.
- **User menu** (bottom-left) — **My Profile** (`/user/<id>#staff-details`) and **Logout**. Do not log out
  unless asked: a new sign-in needs the flaky password step ([`SKILL.md`](../SKILL.md)).

## 6. Not found / unresolved

- **Two-factor security** — not on *My Profile* and not on *Security & Access* (which holds only API
  keys). The help center places it under a profile menu, but that source is a third-party-hosted copy;
  its location in this UI is **unconfirmed**.
- **Staff roles beyond Admin / Coach** — *Front Desk* is documented but its UI was not observed.
- **Tags** — none seen on the profile or People filters; Tags may exist only in Grow. The places for
  recording something against a person that do exist are the profile's *Notes and reminders* and the
  signed documents under *Documents*.
