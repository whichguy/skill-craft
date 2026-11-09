# PushPress API, as exposed through the `pushpress` MCP server

Reference for the 44 `mcp__pushpress__*` tools (the count when this was written) backing the PushPress
Core skill. Covers what each tool does, what it returns, and the conventions (pagination, IDs,
dates, errors) that apply across all of them. Companion to the web-UI half of this skill.

**Provenance tags.** This file predates the skill-wide legend and uses finer tags: `[verified live]`
is the skill's `[observed]` (a real call on the surveyed tenant, 2026-11-08); `[from SDK source]` and `[from tool
schema]` are `[documented]` (read, not called); `[inferred]` is neither; a write tool listed here and
never called is `[not exercised]`.

**Safety column.** The tables label each tool `READ`, `READ-PII`, `WRITE-DATA`, `WRITE-OUTBOUND` or `WRITE-CONFIG`. They
map onto the card's seven action classes as READ, READ (the response is personal data: keep it out of notes),
WRITE-DATA, OUTBOUND and CONFIG / SECURITY. The two delete tools, `invitations-delete` and `manage-webhooks-delete`,
are also DESTRUCTIVE, and the strictest class applies.

**Setup** `[documented]`. This skill does not install or configure the MCP server. The tools come from
the official `@pushpress/pushpress` SDK's bundled MCP server (Node 20+), started as `mcp start
--api-key <key>` (plus `--company-id <id>` only for a multitenant key; a single-company key identifies
its own company). The key is issued under Settings ▸ Security & Access
([settings-and-admin.md](settings-and-admin.md#2-api-keys-settings--security--access)) and belongs in
the environment or a secret store, never in a committed file. The SDK declares no MCP scopes, so every
tool is mounted (`mcp start --tool <name>`, repeatable, narrows the set). Four tools message real
people (`messages-sms-send`, `messages-email-send`, `messages-push-send`, `messages-realtime-send`). The
other write tools are `customers-create`, `customers-attributions-create`, `invitations-create`,
`invitations-delete` and the six `manage-webhooks-` tools that create, update, delete, activate, deactivate
or rotate the secret of a webhook: **confirm with the user before calling any write tool.** The two webhook
reads (`manage-webhooks-list`, `manage-webhooks-get`) change nothing but return signing secrets: call them
only when the user asks about webhooks, and never print a `signingSecret`. Every other read is safe to
repeat; the `customers-*` reads return personal data, so keep their output out of notes.

## Table of contents

1. [API vs. web UI](#1-api-vs-web-ui)
2. [Tool inventory](#2-tool-inventory)
   - [Company](#company)
   - [Customers / roster](#customers--roster)
   - [Plans and enrollments](#plans-and-enrollments)
   - [Classes, class types, events](#classes-class-types-events)
   - [Appointments, reservations, invitations](#appointments-reservations-invitations)
   - [Checkins](#checkins)
   - [Messages (outbound)](#messages-outbound)
   - [Webhooks](#webhooks)
3. [Conventions](#3-conventions)
4. [What the API cannot do](#4-what-the-api-cannot-do)
5. [Recipes](#5-recipes)
6. [Webhooks (reference)](#6-webhooks-reference)
7. [UI ↔ API vocabulary](#7-ui--api-vocabulary)

---

## 1. API vs. web UI

Use the API (via these MCP tools) for anything **read-mostly and structured**: pulling a
single customer's roster record, looking up a plan whose ID you already hold, listing classes/events in a
date range, counting checkins, inspecting enrollment status, or listing webhooks (the webhook write
tools sit behind the Setup gate above). It is scriptable, auditable (no clicking through screens), and safe to run
read-only queries repeatedly. Use the **web UI** (PushPress admin, `<tenant>.pushpress.com`
back office) for anything the API cannot do at all — see
[§4](#4-what-the-api-cannot-do) — and for anything destructive or bulk on member data
(cancel a membership, edit billing, refund a charge, delete a customer, bulk-message the
roster) where a human should be looking at a confirmation screen rather than an agent
calling a write tool. The API also has **no revenue/payment/invoice surface at all**
(confirmed below) — any money question goes to the admin UI's Payments and Reports pages
([money-and-reports.md](money-and-reports.md)), or to your bookkeeping system for the bank side, never
to this API. [verified live] [from SDK source]

## 2. Tool inventory

All `company-id` / `customer` / `*Id` parameters below are omitted from the "params"
column when they are the obvious primary identifier already named by the tool (e.g. `id`
on `*-get`). `company-id` is optional on every tool (single-company key — see
[§3](#3-conventions)).

### Company

| Tool | Purpose | Params | Returns | Safety |
|---|---|---|---|---|
| `company-get` | Fetch the authenticated company's own profile | none required | `id`, `name`, `subdomain`, `address` (`line1/line2/city/state/postalCode/country{name,iso}`), `defaultTimezone`, `phone`, `email`, `url` | READ |

[verified live]: returns the company's `id` (a `client_…` value), `name`, `defaultTimezone` and
`subdomain` — the same identity the admin UI shows.

### Customers / roster

| Tool | Purpose | Params | Returns | Safety |
|---|---|---|---|---|
| `customers-list` | Paginated roster listing | optional `page`, `limit` (default 10), `role` (`admin`\|`frontdesk`\|`coach`\|`member`), `email` (exact-match filter) | array of full `Customer` records (see below) | **READ-PII** |
| `customers-get` | Single customer record by UUID | `uuid` (required) | same `Customer` shape | **READ-PII** |
| `customers-create` | Create a new **lead** (not a full member) | `RequestBody.email` (required); optional `name{first,last,nickname}`, `phone`, `dob`, `gender`, `address`, `emergencyContact`, `account{type:"primary"\|"linked",primaryCustomerId}`, `assignedToStaffId`, `source` | created `Customer` | **WRITE-DATA** |
| `customers-attributions-list` | List marketing-attribution records | optional `customer` (id filter), `attributionEvent` | array of attribution records (see below) | READ-PII *(carries IP address, user agent, referrer — not name/DOB, but still personal/browsing data)* |
| `customers-attributions-get` | Single attribution record by UUID | `uuid` | one attribution record | READ-PII *(same note)* |
| `customers-attributions-create` | Record a signup attribution event | `RequestBody.customerId`, `RequestBody.event` (`signup`\|`client_signup`) required; optional UTM/gclid/fbclid/msclkid/dclid, `ipAddress`, `userAgent`, `referer`, `url`, `rawUrl` | created record | **WRITE-DATA** |

`Customer` record fields [from SDK source, `src/models/components/customer.ts`]: `id`,
`companyId`, `name{first,last,nickname}`, `gender` (`male`\|`female`\|`null`), `dob`
(`YYYY-MM-DD` or `null`), `address{line1,line2,city,country,state,zip}` (empty strings if
unset, not `null`), `assignedToStaffId`, `account` (discriminated union:
`{type:"primary"}` or `{type:"linked",primaryCustomerId}`), `profileImage` (URL),
`emergencyContact{name,phone,relationship}`, `membershipDetails{initialMembershipStartDate}`
(object is `null` for leads/never-members), `email`, `phone`, `role`
(`superuser`\|`admin`\|`coach`\|`frontdesk`\|`member`\|`non-member`\|`ex-member`\|`lead`).

[verified live] `customers-list limit=1` returned one full record with every PII field
populated (name, DOB, home address, emergency-contact name/phone/relationship, email,
phone, profile image URL) — so treat every `customers-*` response as full PII. No field names or
values from that call are reproduced here beyond the schema above.

### Plans and enrollments

| Tool | Purpose | Params | Returns | Safety |
|---|---|---|---|---|
| `plans-get` | Plan details by ID | `id` (required) | `id`, `name`, `companyId`, `recurrenceDetails` (discriminated union, see below), `policies{allowClassCheckins,allowOpenGymCheckins,allow24HourAccess}`, `category{name}` | READ |
| `enrollment-list` | Paginated list of plan enrollments (subscriptions) | optional `customerId`, `status` (`active`\|`alert`\|`canceled`\|`completed`\|`paused`\|`pendactivation`\|`pendcancel`), `page`, `limit` | array of `Enrollment` records | READ |
| `enrollment-get` | Single enrollment by UUID | `uuid` | one `Enrollment` record | READ |

**There is no `plans-list` tool.** You can only fetch a plan if you already have its ID
(e.g. from an enrollment's `planId`, or from the public landing-page URL). [verified live — confirmed absent from the 44-tool list]

`recurrenceDetails` is one of: `{type:"recurring"}`, `{type:"session-pack",occurrences}`,
`{type:"limited-recurring",occurrences}`, `{type:"non-recurring"}`. **No price field
anywhere on `Plan`.** [verified live] `plans-get` on a real plan ID returned exactly
`id/name/companyId/recurrenceDetails/policies/category` — no `price`, `amount`, or `cost` field.
The v3 API exposes no revenue of any kind: checked against the full 44-tool list in this
file, no tool anywhere (plans, enrollments, checkins, customers) carries a price, amount,
invoice, payment, or transaction field.

`Enrollment` fields [from SDK source, `src/models/components/enrollment.ts`]: `id`
(prefix `sub_`), `customerId`, `companyId`, `planId`, `billingSchedule{period,interval}`
(`period` ∈ `day`\|`week`\|`month`\|`year`\|`once`), `status` (see enum above),
`startDate`/`endDate`/`lastCharge`/`nextCharge`/`paidUntil` (date strings, `YYYY-MM-DD`,
or empty string — see [§3](#3-conventions)), `checkinDetails{checkins,limit}` (`limit:-1`
= unlimited), `entitlements[]` (`{type,id,interval,quantity,metadata}`). No amount/price
field: an enrollment says *that* someone is billed and on what cadence,
never how much or whether a discount applied. [verified live]

### Classes, class types, events

| Tool | Purpose | Params | Returns | Safety |
|---|---|---|---|---|
| `classes-list` | Paginated list of scheduled classes | optional `access` (`invite_only`\|`open`), `startsAfter` (unix seconds), `order` (`ascending`\|`descending`, default ascending), `page`, `limit` | array of `Class` records | READ |
| `classes-get` | Single class by ID, optionally expanded | `id`; optional `expand[]` (`location`\|`reservations`) | one `Class` record | READ |
| `classes-type-list` | List class types for the gym | none | array of class types (`id`, `name`) | READ |
| `classes-type-get` | Single class type by ID | `id` | one class type record | READ |
| `events-list` | Paginated list of scheduled events (non-class calendar items) | same shape as `classes-list` plus `access` | array of `Event` records | READ |
| `events-get` | Single event by ID, optionally expanded | `id`; optional `expand` (string or array, `location`\|`reservations`) | one `Event` record | READ |

`Class`/`Event` fields [from SDK source]: `id` (prefix `cal_`), `coachUuid`,
`assistantCoachUuid`, `company`, `title`, `classTypeName` (Class only), `access` (Event
only: `invite_only`\|`open`), `locationUuid`, `location{name}`, `reservations[]` (only
present when `expand` includes `reservations`), `start`/`end` (unix seconds — see
[§3](#3-conventions)). [verified live] `classes-list limit=1` returned a `Class` with
exactly these fields; `page=2` returned a different `id` with the same shape, confirming
page-based pagination actually advances.

### Appointments, reservations, invitations

| Tool | Purpose | Params | Returns | Safety |
|---|---|---|---|---|
| `appointments-appointments-get` | Single appointment by ID | `id` | `id`, `type{name}`, `companyId`, `isLateCancel`, `customerId`, `startTimestamp`, `staffId` | READ |
| `reservations-list` | Paginated reservations for one calendar item (class or event) | `calendarItemId` (required), `page`, `limit` | array of `Reservation` records | READ |
| `reservations-get` | Single reservation by UUID | `id` | one `Reservation` record | READ |
| `invitations-list` | List invitations for an event | `eventId` (**required**), `page`, `limit` | array of `{id,eventId,customerId}` | READ |
| `invitations-get` | Single invitation by ID | `id` | one invitation record | READ |
| `invitations-create` | Invite customers to an event | `RequestBody.eventId`, `RequestBody.customerIds[]` | created invitation(s) | **WRITE-DATA** |
| `invitations-delete` | Remove an invitation | `id` | — | **WRITE-DATA**, DESTRUCTIVE |

`Reservation` fields [from SDK source]: `id`, `reservedId` (the class/event's calendar-item
ID), `customerId`, `companyId`, `registrationTimestamp` (unix seconds),
`status` (enum — exact values not enumerated in this pass, treat as a closed string enum),
`checkin` (embedded `Checkin` union, present only once the reservation has been checked
in — see below), `templateId` (set when the reservation came from a recurring-reservation
template). `invitations-list` requires `eventId`; there is **no way to list all
invitations across every event in one call**. [verified: param list, both from tool
schema]

### Checkins

| Tool | Purpose | Params | Returns | Safety |
|---|---|---|---|---|
| `checkins-count` | Count checkins matching filters | optional `customer`, `after`/`before` (unix seconds), `include` (`classes`\|`events`\|`appointments`\|`open`), `type`, `includeHistoricalCheckins` (`"true"`\|`"false"`, default `"true"`) | `{count: number}` | READ |
| `checkins-class-list` | Paginated class checkins | `customer`, `after`/`before`, `result` (`success`\|`failure`, default `success`), `page`, `limit` | array of `ClassCheckin` | READ |
| `checkins-class-get` | Single class checkin by UUID | `uuid` | one `ClassCheckin` | READ |
| `checkins-event-list` | Paginated event checkins | same as `checkins-class-list` | array of `EventCheckin` | READ |
| `checkins-event-get` | Single event checkin by UUID | `uuid` | one `EventCheckin` | READ |
| `checkins-appointment-list` | Cursor-paginated appointment checkins | `customer`, `after`/`before`, `next` (cursor) — **no `page`/`limit`** | array of `AppointmentCheckin`, plus optional `next` cursor | READ |
| `checkins-appointment-get` | Single appointment checkin by UUID | `uuid` | one `AppointmentCheckin` | READ |
| `checkins-open-list` | Paginated open-facility checkins | same as `checkins-class-list` | array of `OpenCheckin` | READ |
| `checkins-open-get` | Single open-facility checkin by UUID | `uuid` | one `OpenCheckin` | READ |

All four checkin record types share `id` (prefix `chk_`), `customer` (customer UUID —
**not** the customer's name/email: pair with `customers-get` if you need the person),
`company`, `timestamp` (unix seconds), `enrollmentId` (nullable). Discriminated by `kind`:
`"class"` (`ClassCheckin`: adds `name`, `typeId`, `role` ∈
`staff`\|`coach`\|`assistant`\|`attendee`), `"event"` (`EventCheckin`: adds `name`,
`typeId`, `role`), `"appointment"` (`AppointmentCheckin`: adds `appointmentId`, `typeId`,
`staffId`), `"open"` (`OpenCheckin`: no extra fields). [from SDK source,
`src/models/components/{classcheckin,eventcheckin,appointmentcheckin,opencheckin,checkin}.ts`]

[verified live] `checkins-class-list limit=1` returned a richer shape than the bare SDK
model above in practice — also carrying `classId`, `source` (e.g. `"member_app_iOS"`),
`result` (`"success"`\|`"failure"`), `failureReason`, and a nested `type{id,name}` object
in addition to the flat `typeId`/`name`. Treat the SDK's declared model as the floor, not
the ceiling — live responses carried more fields than the generated types declare.
**Anomaly noted**: the live `classId` value used a `cal-` (hyphen) separator rather than
the `cal_` (underscore) pattern seen on `classes-list` IDs — not explained by this pass;
don't assume the two are interchangeable string formats without checking.

`checkins-appointment-list` and `reservations-list`, called live with no matching data,
both returned `{"data":{"resultArray":[]}}` with no `next` key present — consistent with
the SDK typing `next` as optional (only appears when there are more pages/cursor
positions). [verified live]

### Messages (outbound)

| Tool | Purpose | Params | Returns | Safety |
|---|---|---|---|---|
| `messages-sms-send` | Send an SMS | `RequestBody.to`, `RequestBody.message` | send result | **WRITE-OUTBOUND** |
| `messages-email-send` | Send an email | `RequestBody.customer`, `subject`, `text`, `html`, `from`; optional `replyTo`, `type` | send result | **WRITE-OUTBOUND** |
| `messages-push-send` | Send a push notification | `RequestBody.customers[]`, `message`; optional `data`, `type` | send result | **WRITE-OUTBOUND** |
| `messages-realtime-send` | Publish an Ably realtime event | `RequestBody.channel`, `event`; optional `data` | send result | **WRITE-OUTBOUND** |

Tool descriptions explicitly note: *"only first party apps can send [emails / push /
realtime]"* — these may silently be no-ops or auth-reject for a third-party API key,
untested here per the hard rule against calling WRITE-* tools. [from tool schema]

### Webhooks

| Tool | Purpose | Params | Returns | Safety |
|---|---|---|---|---|
| `manage-webhooks-list` | List all webhooks | none | array `{id,url,eventTypes,signingSecret,...}` — **includes the signing secret** | READ *(but response is sensitive — see note)* |
| `manage-webhooks-get` | Single webhook by UUID | `uuid` | one webhook record, including signing secret | READ *(same note)* |
| `manage-webhooks-create` | Register a new webhook | `RequestBody.url`, `RequestBody.eventTypes[]` (app lifecycle events or the member/scheduling event list below) | created webhook | **WRITE-CONFIG** |
| `manage-webhooks-update` | Change a webhook's URL/events | `uuid`, `RequestBody.eventTypes[]`, optional `url` | updated webhook | **WRITE-CONFIG** |
| `manage-webhooks-delete` | Permanently delete a webhook | `uuid` | — | **WRITE-CONFIG**, DESTRUCTIVE |
| `manage-webhooks-activate` | Reactivate a deactivated webhook | `uuid` | — | **WRITE-CONFIG** |
| `manage-webhooks-deactivate` | Pause a webhook without deleting it | `uuid` | — | **WRITE-CONFIG** |
| `manage-webhooks-rotate-secret` | Rotate a webhook's signing secret | `uuid` | new secret | **WRITE-CONFIG** |

`manage-webhooks-list` returns `{"data":[]}` when no webhook is registered. While this reference was
written only `manage-webhooks-get`/`list` were called; create/update/delete/activate/deactivate/rotate
were not exercised.

---

## 3. Conventions

**Company scoping.** Every tool accepts an optional `company-id` parameter, but a
single-company API key identifies its own company, so it is not needed — every call above
succeeded with `company-id` omitted. The SDK documents it as required only for multitenant
keys. [verified live]

**Pagination — two different schemes, not one.** Most list tools
(`customers-list`, `classes-list`, `events-list`, `enrollment-list`, `invitations-list`,
`reservations-list`, `checkins-class-list`, `checkins-event-list`, `checkins-open-list`)
use **page-based** pagination: `page` (default `1`) and `limit` (default `10`), no
maximum documented. **`checkins-appointment-list`** is the odd one out: it uses
**cursor-based** pagination via a `next` string parameter instead of `page`/`limit` — pass
back the `next` value from the previous response to get the next page. [verified live:
page=2 on `classes-list` returned a different record than page=1; from SDK/tool schema
for the `next`-cursor behavior on `checkins-appointment-list`]

**No total-count metadata, anywhere.** Every list response observed is shaped
`{"data":{"resultArray":[...]}}` (or, for `manage-webhooks-list`, a bare array) — never a
total/count/hasMore field alongside the array. `checkins-count` is the **only** tool that
returns a count, and it counts checkins specifically (filterable by customer, type,
window), not customers, classes, or enrollments. So counting anything else means paging until a page
comes back shorter than `limit` (or empty). [verified live — every `data` shape inspected
in this pass matched `{resultArray:[...]}` except `manage-webhooks-list` (`{data:[...]}`)
and `checkins-count` (`{count:N}`)]

**ID prefixes** [verified live, except where marked inferred]:

| Prefix | Entity |
|---|---|
| `client_` | Company |
| `usr_` | Customer |
| `plan_` | Plan |
| `sub_` | Enrollment (subscription) |
| `cal_` | Class / event (calendar item) — **but** one live checkin's embedded `classId` field used `cal-` (hyphen) instead; treat as a possible second format, not confirmed interchangeable |
| `chk_` | Checkin |
| `calitemtype_` | Class/event type |

Hex-suffix length varies within the same prefix (seen 6, 14, and 32 hex characters on
different `usr_...` and `cal_...` IDs) — don't assume a fixed length. Appointment,
reservation, invitation, and webhook ID formats were not independently confirmed live in
this pass — treat as `[inferred]` UUID-like strings
until seen.

**Dates and times.** Unix-timestamp fields (`start`, `end`, `timestamp`,
`registrationTimestamp`, `startTimestamp`, `after`/`before` filters) are **seconds**, not
milliseconds — confirmed by the live `classes-list` result (a ten-digit `start` that decodes to a
plausible class date, not a far-future one as milliseconds would imply).
Date-only fields on `Enrollment` (`startDate`, `endDate`, `lastCharge`, `nextCharge`,
`paidUntil`) are either an **ISO date or date-time string** (seen both `"YYYY-MM-DD"` and
`"YYYY-MM-DDThh:mm:ss±hh:mm"` live, from the same record) or an **empty string** when not
applicable (`nextCharge:""` on a canceled enrollment) — never `null` on this field set.
`Customer.dob` is `YYYY-MM-DD` or `null`. The company's `defaultTimezone` is an IANA zone name;
timestamps returned are epoch seconds (UTC by construction) and date-time strings carry their
own UTC offset — no separate timezone conversion is needed on read.
[verified live]

**Errors.** Two distinct shapes observed for a deliberately invalid ID:

- Invalid **plan** ID (400, validated server-side): JSON body
  `{"message":"Plan not found"}`.
- Invalid **customer** UUID (404, not found): **empty body**, `Content-Type` empty string
  — no JSON at all.

Don't assume every error carries a parseable JSON `message` — some 404s are a bare empty
response, and callers must branch on HTTP status rather than relying on body content.
[verified live] The SDK additionally declares typed error classes for `BadRequest` (400),
`Unauthorized` (401), `NotFound` (404), `RateLimited` (429), `InternalServerError` (5xx),
each carrying `{message?, ...additionalProperties}` when a body is present [from SDK
source, `src/models/errors/*.ts`].

**Rate limits.** The underlying SDK documents `429 RateLimited` as applicable to "8 of 49
methods" and ships a default retry/backoff strategy (configurable, honors a `Retry-After`-
style interval from the response) [from SDK source, `README.md` + `src/lib/retries.ts`].
Which 8 of the 44 MCP-exposed tools those are was not enumerated in this pass — treat any
tool as potentially rate-limited and expect the MCP server's bundled retry logic to handle
transient 429s rather than building your own retry loop.

---

## 4. What the API cannot do

- **Revenue, payments, invoices, charges, transactions — `NOT IN API -> use UI`.** No tool
  in this inventory (or the SDK's full method list) exposes money. `plans-get` has no
  price field; `enrollment-get`/`list` says who is billed and on what schedule, never how
  much or whether it cleared. Confirmed live — read PushPress's own figures in the UI: Payments ▸
  Transactions, Daily Deposits and Payments Forecast ([money-and-reports.md](money-and-reports.md)),
  and reconcile the bank side in your bookkeeping tool.
- **Per-enrollment discounts — `NOT IN API -> use UI`.** `enrollment-list`/`-get` carries
  no discount or price field, so a discounted enrollment is indistinguishable from
  a full-price one through the API. The advertised base rate is
  visible unauthenticated at the public plan landing page
  (`GET https://<tenant>.pushpress.com/landing/plans/<plan_id>`) — that
  is a web fetch, not an MCP tool, and still isn't the billed/discounted amount.
- **Listing all plans — `NOT IN API -> use UI`.** No `plans-list` tool exists. A plan is
  only reachable by ID, obtained from an enrollment, a webhook payload, or the sign-up links
  on a website or landing page. The admin UI's Plans page is the only way to browse all plans.
- **Listing all invitations across every event — `NOT IN API -> use UI`.**
  `invitations-list` requires `eventId`; there's no cross-event invitation query.
- **Total headcount / any aggregate count besides checkins — `NOT IN API -> use UI`.**
  `checkins-count` is the only counting endpoint. Counting customers, active enrollments,
  or classes means paging the full list (see [§5](#5-recipes) recipe 1) or reading the
  number off an admin dashboard.
- **Editing a customer's profile, canceling/pausing an enrollment, refunding a charge,
  deleting a customer — `NOT IN API -> use UI`.** `customers-create` only creates leads;
  there is no `customers-update`, no enrollment-mutation tool, and no delete-customer
  tool anywhere in the 44. All of this is admin-UI-only.
- **Editing class/event schedules, creating classes, managing staff — `NOT IN API -> use
  UI`.** `classes-*`/`events-*` tools are read-only; there's no create/update/delete for
  calendar items.
- **Checking in a member or canceling a reservation — `NOT IN API -> use UI`.**
  `checkins-*` and `reservations-*` are all read-only; there's no `checkins-create` or
  `reservations-cancel`.

## 5. Recipes

1. **Count active members (no total-count metadata available).** Page
   `enrollment-list` with `status:"active"` and a large `limit`, incrementing `page` until
   a page returns fewer than `limit` rows (or empty); sum `resultArray.length` across
   pages. One enrollment per active member (barring multiple concurrent plans per
   customer, which this does not de-duplicate — cross-check `customerId` if that matters).
   Cheaper than paging `customers-list` with a `role` filter, since enrollment status is
   the actual "active member" signal, not the customer role flag.

2. **Find one customer by email without pulling the roster.** Call `customers-list` with
   `email:"<address>"` and `limit:1` — the tool supports an exact-email filter, so this
   avoids paging the whole PII-bearing roster for a single lookup. Only fall back to
   `customers-get uuid:<id>` if you already have the UUID from another record (e.g. an
   enrollment's `customerId`).

3. **Which plans exist and who is enrolled.** There's no `plans-list`. Instead: page
   `enrollment-list` and collect distinct `planId` values, then `plans-get id:<planId>`
   for each to resolve names/categories. To see who's on a given plan, filter
   `enrollment-list` results client-side by `planId` (the tool itself only filters by
   `customerId`/`status`, not `planId`).

4. **Upcoming classes and their reservations.** `classes-list startsAfter:<now_unix>
   order:"ascending"` for the schedule; for a specific class's roster,
   `classes-get id:<id> expand:["reservations"]` embeds the `Reservation[]` directly
   (avoids a separate `reservations-list calendarItemId:<id>` call). Each `Reservation`
   includes a `status` and, once attended, an embedded `checkin`.

5. **Who attended a class.** Either read the embedded `reservations[].checkin` from
   `classes-get ... expand:["reservations"]` (recipe 4), or call
   `checkins-class-list customer:<uuid> after:<ts> before:<ts>` filtered by a specific
   customer and window, or omit `customer` and page through all class checkins in a
   window. `checkins-count include:"classes" after:<ts> before:<ts>` gives just the
   number without the records.

6. **A customer's checkin history across all types.** `checkins-count customer:<uuid>`
   with no `include` filter counts everything (classes + events + appointments + open);
   add `include:"<type>"` to narrow. To get the actual records rather than a count, you
   must call the four `checkins-*-list` tools separately (`class`, `event`, `appointment`,
   `open`) with the same `customer` filter — there is no unified "list all checkins for
   this customer" tool.

7. **Resolve a plan's advertised price (API has none).** `plans-get` never returns a
   price. Fetch `https://<tenant>.pushpress.com/landing/plans/<plan_id>`
   (unauthenticated, outside the MCP server — a plain web fetch) for `amount`,
   `amountRecurring`, `quantityAvailable`, `limitQuantity`. This is
   the *advertised* rate, not necessarily what was billed (discount sign-up links append a
   base64 `discount_slug` param, seen on one tenant's public links, which the landing-page JSON
   and the API both miss).

8. **Check whether any webhooks are currently configured.** `manage-webhooks-list` with no
   params — returns `{"data":[]}` if none exist. It changes nothing, but its
   response carries every webhook's signing secret, which then sits in your context: call it only when
   the user asks about webhooks, never print or repeat a `signingSecret`, and report URLs and event
   types only.

9. **Distinguish a "no results" page from "query is wrong."** An empty `resultArray` with
   HTTP 200 means the filter matched nothing (confirmed live for `reservations-list` and
   `checkins-appointment-list` against a class with no bookings) — it is not an error.
   Only a malformed/nonexistent **ID** on a `-get` tool produces an error (400 with a JSON
   message, or 404 with an empty body — see [§3](#3-conventions)).

10. **Never page the roster just to get a headcount.** Combine recipe 1 (page
    `enrollment-list`, not `customers-list`) with the fact that `customers-list` returns
    full PII per record — paging it for a count pulls DOB/address/emergency-contact data
    for every member for no reason. Use `enrollment-list` (no PII beyond IDs) whenever the
    question is "how many," and reserve `customers-list`/`customers-get` for when you
    actually need a specific person's record.

## 6. Webhooks (reference)

Documentation only — no webhook was created, modified, or deleted while writing this
file; only `manage-webhooks-list`/`-get` (both READ) were called.

**Event types** a webhook can subscribe to [from tool schema,
`manage-webhooks-create`/`-update`]:

- App lifecycle: `app.installed`, `app.uninstalled`
- Appointments: `appointment.scheduled`, `appointment.rescheduled`,
  `appointment.noshowed`, `appointment.canceled`
- Checkins: `checkin.created`, `checkin.updated`, `checkin.failed`, `checkin.deleted`
- Classes: `class.canceled`
- Customers: `customer.created`, `customer.details.changed`, `customer.status.changed`,
  `customer.deleted`
- Enrollments: `enrollment.created`, `enrollment.status.changed`, `enrollment.deleted`
- Member app: `memberapp.updated`
- Reservations: `reservation.created`, `reservation.waitlisted`, `reservation.canceled`,
  `reservation.noshowed`

**Lifecycle tools**: `manage-webhooks-create` (register `url` + `eventTypes[]`),
`manage-webhooks-update` (change `url`/`eventTypes[]` by `uuid`), `manage-webhooks-delete`
(permanent), `manage-webhooks-deactivate` (pause, reversible — "If you want to fully
delete a webhook use the delete method" per the tool's own description),
`manage-webhooks-activate` (reverse a deactivation), `manage-webhooks-rotate-secret`
(issue a new signing secret for an existing webhook, presumably invalidating the old one —
not tested). All six are **WRITE-CONFIG** (`manage-webhooks-delete` is also DESTRUCTIVE) and were not called. `manage-webhooks-get`/
`-list` return the full record **including the signing secret in plaintext** — if this
skill ever lists or inspects a webhook, treat that output as a credential, not inert
metadata, for the same reason the PushPress API key itself is never printed. [from tool
schema; "including the signing secret" is the tool's own description text for both
`-get` and `-list`]

There is no tool to **receive** or replay a webhook delivery, inspect delivery history, or
verify a signature — this inventory covers configuring webhooks, not consuming them. That
would be implemented in whatever endpoint the `url` points at (outside this MCP server
entirely).

## 7. UI ↔ API vocabulary

The web UI and the API name the same things differently. Use this when a question is phrased in one
and the answer is in the other ([app-map.md](app-map.md) has the UI routes).

| In the admin UI | In the API |
|---|---|
| People ▸ **Staff** (roles *Admin*, *Coach*; *Asst. Coach* on rosters) | `customers-list role=` accepts only `admin`, `frontdesk`, `coach`, `member`; check-in records carry `role` ∈ `staff`/`coach`/`assistant`/`attendee` |
| People ▸ **Members** / **Non-members** / **Leads** | `Customer.role` ∈ `member`, `non-member`, `ex-member`, `lead` — but `customers-list` cannot filter by those; lead *pipeline status* (new lead, attempted, contacted, in discussion) is **not exposed** |
| Member status **Active**, **Pending cancel** | enrollment `status` `active`, `pendcancel` (others: `alert`, `canceled`, `completed`, `paused`, `pendactivation`) |
| Plans page — price, "N active", categories | `plans-get` (by ID only): name, recurrence, policies, category — **no price**; "N active" = count `enrollment-list status=active` filtered client-side by `planId` |
| Plans ▸ **Discounts** | not exposed |
| Class types list (`/schedule/class-types`) | `classes-type-list` / `classes-type-get` (read-only) |
| Class page `/schedule/cal-<id>` | `classes-get id=…` with `expand=["reservations"]`; the UI id is spelled `cal-…` where the API usually shows `cal_…` — check before assuming they match (§3) |
| Check-Ins card "checked-in / limit" | `checkins-class-list`, `checkins-count include=classes`; the API has no class capacity field |
| Invoices, Transactions, Deposits, Forecast | not exposed (§4) |
| Automatic Emails (staff alerts) | not exposed; webhooks (§6) are the programmatic equivalent for events |
