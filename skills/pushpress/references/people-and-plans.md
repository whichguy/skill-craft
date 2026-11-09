# People, plans, discounts and documents

Verified read-only on **2026-11-08**. Tags: `[observed]` is the default; `[documented]` = help-center only;
`[not exercised]` = control exists but writes, sends or deletes, so it was not run. Member data is
sensitive and many gyms serve minors — see the privacy rule in [`SKILL.md`](../SKILL.md).

## Contents
1. [People list and tabs](#1-people-list-and-tabs)
2. [Finding someone](#2-finding-someone)
3. [Person profile](#3-person-profile-userid)
4. [Leads](#4-leads)
5. [Plans](#5-plans)
6. [Plan editor (drawer)](#6-plan-editor-drawer)
7. [Discounts](#7-discounts)
8. [Digital Documents](#8-digital-documents)
9. [Roles and staff](#9-roles-and-staff)

## 1. People list and tabs

`/people` redirects to `/people/members?membershipRole=member`. Header **People**, a **Person** button
(menu: *Lead*, *Member*, *Staff* — each starts an add flow, `[not exercised]`), and four tabs that are
**separate routes**:

| Tab | Path | Columns | Filters / notes |
|---|---|---|---|
| Members | `/people/members?membershipRole=member` | Name, Type, Plan, Status, Last check-in | `Plan` filter, *Search members*, select-all and row checkboxes; 50 per page. Types seen: *Member*; statuses: *Active*, *Pending cancel* |
| Leads | `/people/leads?leadStatus=new+lead,attempted,contacted,in+discussion` | Name, Status, First contacted, Assigned to, Plan, Last check-in | the default filter is the open pipeline; status seen: *New* |
| Non-members | `/people/non-members` | Name, Plan, Status (`--`), Last check-in | people with no plan |
| Staff | `/people/staff` | Name, Role, Plan, Status, Last check-in | roles seen: *Admin*, *Coach*; the check-in roster also shows *Asst. Coach* |

Lists show 50 rows per page. **Switching tabs needs a real click** (on Claude in Chrome, `find` then `computer` `left_click`); a
synthetic JS `.click()` leaves the list unchanged. Or navigate by URL.

## 2. Finding someone

- **Top-bar Search** is a command palette: placeholder "Search for a person or a page", with quick
  actions *Add Member*, *Add Lead*, *Create Invoice*, *See all members*, *Dashboard*, *Manage Staff*,
  *Manage Plans*, *Appointments*. Fastest route to a profile.
- **People ▸ tab ▸ Search members.**
- **API:** `customers-list email=<address> limit=1` — an exact-email filter avoids paging the roster
  ([api-and-mcp-tools.md](api-and-mcp-tools.md) recipe 2).
- A tool's page-title and URL header on a profile contain the person's **name and `usr_` ID** — keep
  them out of notes ([browser-technique.md](browser-technique.md)).

## 3. Person profile (`/user/<id>`)

One long page with an in-page section nav. Sections, with what each contains:

| Section | Contents |
|---|---|
| **Plans & Appointment Credits** | sub-tabs *All / Current / Credits*; counts "Active N / Inactive N"; buttons `Add Credit`, `Add Plan`; table Plan · Start date · Next charge · Usage · Status. A profile linked to a family shows **Parent Account**; a primary account shows **Sub-accounts** with `Add Sub-account` |
| **Billing** | *Payment Methods* (`Add Payment Method`, `Request Payment Method`), `Create a Charge`, *Billing History* with tabs *Payments / Invoices N / Pending N*; table Date · Description · Type · Amount |
| **Schedule** | tabs *Upcoming / Classes / Events / Appointments* |
| **Communication** | message log: Date & Time · Channel · Subject (· Status) |
| **Personal Information** | *Basic Information* (First/Last Name, Nickname, Birthday, Email, Phone, Gender), *Address*, *Emergency Contact* (Name, Relationship, phone), *Gym Details* (Member Since, First Check-in, Custom ID, User Type, Username, Referred By, Assigned To); `Edit`; `Copy email to clipboard` |
| **Notes** | *Notes and reminders*: `Add Note`; table Created · Note · Remind on · Remind via · Created By |
| **Documents** | `Sign all unsigned documents`, `Add Document`; tabs *Active / Archived*; table Document · Version |
| **Settings** | *User Role* (`Change Role`), *Lead Profile* (toggle `Lead profile`), *At Risk Report* (toggle `Exclude from At Risk Report`), *Account Management*: `Merge` (Merge Account) and `Delete` (Delete Account) |

**OUTBOUND** buttons on the profile — they email the member: `Send Profile Setup Link`,
`Send Reset Password Link`, `Request Payment Method`, and `Add Document` ([§8](#8-digital-documents)).
**MONEY**: `Create a Charge`, `Add Plan`,
`Add Credit`. **DESTRUCTIVE**: `Merge`, `Delete`. All `[not exercised]`.

**Staff profile** (`/user/<id>#staff-details`, e.g. user menu ▸ *My Profile*) adds *Staff Details*: a
`Staff app & Core access` toggle, `Manage Class Types`, a per-class-type pay table (Class type · Coach
pay rate · Coach check-in pay · Asst. coaching pay rate), `Sync your Google calendar`,
`Set your working hours`, `My lead gen link`, `Slack Username`, plus *Staff Availability*.

**Family accounts:** profiles link through *Parent Account* (on the linked profile) and *Sub-accounts*
(on the primary account); which profile is billed was not checked. Family pricing can be set up as a **discount** on the same plan rather than as a separate
plan; see [§7](#7-discounts).

## 4. Leads

- Pipeline statuses in the default filter: **new lead, attempted, contacted, in discussion** (other
  statuses exist outside the default filter; names not captured).
- The website's lead form is configured under Settings ▸ Lead Capture
  ([settings-and-admin.md](settings-and-admin.md)). New leads trigger the *New Lead* automatic email to
  staff.
- API: `customers-create` creates a **lead** only (WRITE); there is no update tool.

## 5. Plans

`/plans/list`. Tabs **Active plans / Deleted plans**; toolbar: external-link icon (public plan page),
`+ Category`, `+ Plan`; a banner for "New landing pages (beta)" → `/landing/plans`.

- Plans are grouped under **category headers** (named by the gym), each with a ⋮ menu.
- Each plan row shows name, *Member* or *Non-member*, **price and period** (e.g. "$NN.00 / per month"),
  *Recurring* or *Non-Recurring*, and an **"N active"** link to `/members/by_plan/<id>`.
- Row ⋮ menu: **View landing page · Edit plan · Duplicate plan · Delete plan.**
- **The UI shows prices; the API does not** — this page is the way to list plans and prices
  ([api-and-mcp-tools.md](api-and-mcp-tools.md) §4).

## 6. Plan editor (drawer)

*Edit plan* opens a **drawer on `/plans/list`** (no URL change) with `Save` and `Close`. Leave with
**Close**. Sections: Advanced Purchase Settings · Appointments · Advanced Access Settings · Online
sales · Plan description · Post-purchase · Link to purchase page (`Generate`).

Fields and toggles: *Client status\** · *Category\** (`Add new category`) · *Bill every\** (Month(s)/Day…)
· *Price\** · *Bills on* (day the plan begins) · `Recurs forever` · `Setup fee (one-time)` ·
`Limit quantity` + *Quantity\** · `Limit per person` · `Force purchase start date` · `Open gym access` ·
`Priority booking` · `24-hour access` · `Publish page` · *Short description* · *Detailed description* ·
`Allow class booking after purchase` · *Purchase confirmation message* · `Website plan list` ·
`Kiosk mode (Staff App)` · `Members App`. A note in the drawer links to the Kisi / HybridAF access
integration in Marketplace.

**Quantity trap** `[not exercised]` — reported once, not re-tested here (it would need
a `Save`): *Quantity* appeared to be validated by truthiness, so a sold-out plan (`0`) could not be
saved until a non-zero number was entered, and unticking `Limit quantity` makes the plan unlimited.
Check a plan's quantity before editing anything on it.

## 7. Discounts

`/discounts?type=…`; reached from **Plans ▸ Discounts** or **Products ▸ Discounts** (same page). Tabs
**Membership / Product / Event** with counts, `Create Discount`, `Add filter`,
`Bulk actions`; columns Discount Name · Status · Type · Amount · Duration; 20 per page; row link
`/discounts/dis_<id>`. Discounts are fixed-amount or percentage, often for a set number of billing
cycles ("for 3 cycles", "for 6 months"), and are named by the gym. **The API cannot see them** — a
discounted enrollment looks full-price through `enrollment-list`.

## 8. Digital Documents

Apps ▸ **Digital Documents** → `/documents`. `Create document`; table Title · Current version · Last
updated · Status; 10 per page; row link `/documents/view/<id>`; a per-row actions menu; *Search
documents*. The documents are authored by the gym (membership policies, waivers, photo releases). On
a profile, **Documents** shows what that person signed, by version
(`Sign all unsigned documents`, `Add Document`).

`[documented]` Waivers are **plan-specific** — each plan has its own assigned waiver — so a lead or
non-member does not automatically receive one; PushPress supplies no legal template text, and the
builder adds date and signature fields itself (do not add them by hand). The *Document Ready to Sign*
automatic email is described as a staff notification, but a later look at one tenant's workflow found it
addressed to the member (reported, not re-verified here), so attaching a document may email the person:
treat `Add Document` as **OUTBOUND**.

## 9. Roles and staff

- People ▸ **Staff** lists staff with a **Role** column (*Admin*, *Coach*; *Asst. Coach* appears on
  class rosters). Role names can be relabelled in Settings ▸ Settings ▸ *Role names* (coach / member).
- Change a role on the person's profile ▸ *Settings* ▸ *User Role* ▸ `Change Role` (`[not exercised]`).
- `[documented]` Roles ascend Member → Front Desk → Coach → Admin; only Admins change roles; an Admin
  cannot demote another Admin (PushPress Support does it); demoting is two steps — set the role to
  Member, **then** switch off the `Staff app & Core access` toggle.
- Pay rates for payroll live on the staff profile and under Class types
  ([schedule-and-checkins.md](schedule-and-checkins.md)).
