# Money, billing and reports

Verified read-only on **2026-11-08**. `[observed]` is the default; `[documented]` = PushPress help center
or pricing page only;
`[not exercised]` = the control exists but charges, sends, downloads or writes, so it was not run.

**The API has no money surface at all** — no revenue, price, invoice, payment or transaction field in any
of the 44 tools ([api-and-mcp-tools.md §4](api-and-mcp-tools.md#4-what-the-api-cannot-do)). Every money
question is answered in
the web UI described here. Prefer reading figures **on screen** (tiles, tables) over `Download`, which
writes a file and needs the user's yes.

## Contents
1. [Dashboard](#dashboard)
2. [Payments group](#2-payments-group)
3. [Reports group](#3-reports-group)
4. [Embedded analytics](#4-embedded-analytics-financial-engagement-pro-metrics)
5. [Billing settings](#5-billing-settings)
6. [Products, pre-orders, guest charges](#6-products-pre-orders-guest-charges)
7. [How billing behaves](#7-how-billing-behaves-documented)
8. [Recipes for reconciliation](#8-recipes-for-reconciliation)

## Dashboard

`/main`. Date-range button; a "Try the new landing pages" banner
(`Go to Plans`, `Dismiss`); an **AI Assistant** card (beta; canned prompts such as "What's the health of
my gym?", "No-shows & late cancels", "Which classes are crushing it?", `Ask Assistant`); KPI tiles
**Leads**, **New Memberships**, **Check-ins** with % change; report shortcuts **Members · Payments
forecast · Financial · No show · Engagement**; an **Important** panel (*At Risk* last 7 days, *Expiring
plans* next 30 days, *Cancellation requests*, *New Leads* last 7 days, *New memberships* last 30 days,
*Celebrations* next 7 days); a schedule panel with tabs *Full schedule / My day*.

## 2. Payments group

| Page | Path | What it shows | Controls |
|---|---|---|---|
| **Invoices** | `/payments` | tabs *All · Open · Overdue · Paid · Pending · Forgiven*; table Customer · Date Opened · Description · Amount · Status · Payment Method; 25 per page | `Create` → dialog **Create invoice** (*Recipient* Member / Guest, *Member Name*, *Product*…) `[not exercised]`; *Search invoices*; rows are clickable but are not links (the extractor lists none), and the detail route `/payments/<id>` was not re-checked |
| **Transactions** | `/reports/transactions/<from>/<to>` | "Transaction Report" with sections *Transactions · Income · Expense · Payment Types · History*; summary table Category · Amount | `Download`, date-range button, `Add filter`, search "by name or email" |
| **Payments Forecast** | `/reports/payments` | tabs *This month · Last month · Next month · Overdue · Open invoices* (each with a count); table Date · Name · Receipt · Amount · Method · Item · Payment | `Download CSV`, `Generate Invoice` (per row, **MONEY** `[not exercised]`), an *Overdue $…* total, search by name |
| **Daily Deposits** | `/reports/deposits/<from>/<to>` | "Deposit Report" — what Stripe paid out | `Download CSV`, date-range button |
| **ACH Report** | `/reports/ach` (also Apps ▸ ACH) | tabs *Credit Card Memberships (N) · In Verification Process (N) · ACH Memberships (N)*; table Name · Last Requested | `ACH app configuration` → `/app-store/pushpress-ach`; `Request Payment Method` (**OUTBOUND** — emails members `[not exercised]`); `Actions`; search; 50 per page |

## 3. Reports group

| Page | Path | Key content | Export |
|---|---|---|---|
| Product Sales Report | `/reports/retail/<from>/<to>` | *Product Sales · Sales Breakdown · History*; table Item · Quantity · Amount | `Download` |
| No Show / Late Cancel | `/no-show` | date range + `Filter` | `Download` |
| Celebrations | `/reports/celebrations` | tabs *All · Birthdays · Anniversaries*; table Type · Date; previous/next range | — |
| Expiring Members | `/members/expiring` | table Name · Plan · Expiration date; row actions | `Download CSV` |
| Membership Change Report | `/reports/subscription_change/<from>/<to>` | "Showing results for: <range>"; tabs *All · New · Plan change · Canceled · Paused · Unpaused* (counts; an empty tab says "No … events / Try a different period or filter"); table Date · Event · Name · Plan (*A → B* on a plan change) · **Recurring revenue impact**; and a **KPI summary panel** beside the table: *Active memberships* (± net memberships), *Recurring revenue* (± this period), *Membership churn rate*, *Revenue churn rate* — values follow the date range | `Download CSV` |
| At Risk Report | `/members/risk` | filters *Inactive 7+ days*, `Plans`, `Assigned to`; table Name · Plans · Assigned to · Last check-in; `Bulk actions` `[not exercised]` | `Download CSV` |
| Payroll | `/reporting/export-payroll` | embedded; see [schedule-and-checkins.md](schedule-and-checkins.md) | — |
| Financial / Engagement / Pro Metrics | `/reporting/<name>?tab=…` | embedded; [§4](#4-embedded-analytics-financial-engagement-pro-metrics) | per-report menu |

At Risk, Expiring and Celebrations list **people** — their names are on screen; keep them out of notes.

## 4. Embedded analytics (Financial, Engagement, Pro Metrics)

These render inside an iframe from `analytics.pushpress.com` (dashboards named like
`snowflake-upcoming-payments`). The parent page's DOM and page-text tools (`read_page` and `get_page_text` on Claude in Chrome) see only the tab
bar — read the content with a (small-scale) screenshot or `zoom`, and expect **client names** in the
tables.

- **Financial** `/reporting/financial?tab=…` — tabs **Overview · Details · Membership Sales · Retail
  Sales · Upcoming Payments · Open Invoices**. *Upcoming Payments* has a month selector (*Last Month /
  This Month / Next Month*), KPI tiles (Last Month, Paid This Month, Upcoming This Month, This Month,
  Next Month) and a table Date · Client · Item · Invoice · Payment method · Payment status · Net Total ·
  Total Amount. Toolbar icons: refresh, filter, AI, ⋮ (not opened).
- **Engagement** `/reporting/engagement?tab=…` — **Overview · Class Attendance · Member Attendance ·
  All Time Attendance.**
- **Pro Metrics** `/reporting/pro-metrics?tab=…` — **Revenue · Members · Leaderboard · Export.**
  `[documented]` a 2024 changelog said Pro Metrics moved into Financial; here it is still its own page.
- Only `?tab=Upcoming%20Payments` was confirmed to select its tab by URL; click the others.

## 5. Billing settings

Settings ▸ **Billing & Payment** (`/settings/billing-and-payment`). Sections and labels:

| Section | Contents |
|---|---|
| **Bank Settings** | Stripe *Connection status*, *Account ID* (do not record), *Statement descriptor*, *Account*; a link to Stripe's transfers docs |
| **Disputes** | dispute handling |
| **Flex Fee** | `Enable flex fees`, *Currency* |
| **Tax** | table *Tax rate name · Tax rate · Status*; `Add tax rate` |
| **Billing** | `Retry failed invoices` (a number of times), `Stripe Setup` |
| **Autoclose** | `Autoclose invoices on first of the month` |

Edits are `[not exercised]`. The payout bank account itself is managed in Stripe's dashboard, not here
(`[documented]`).

## 6. Products, pre-orders, guest charges

- **Products** `/products` — tabs *All · Active · Inactive*; `Manage products`,
  `Create product`, `Add filter`, `Bulk actions`; table Product · Status · Category · Price · Options;
  20 per page; *Search products*; detail `/products/view/prd_<id>`.
- **Product Categories** — sidebar link `/products?manage_categories=…` `[not exercised]`.
- **Pre-Orders** `/preorders` — tabs *Active · Inactive*; `Create pre-order`; table Name · Status ·
  Start Date · Orders · Sales; detail `/preorders/preorder_<id>`.
- **Charge A Guest** — sidebar link `/payments?create=…`; presumably the *Create invoice* dialog set to
  *Guest* `[not exercised]`. **MONEY.**
- Store/POS: `[documented]` a separate Store App and Staff-App product purchases exist; which one the
  gym uses was not checked.

## 7. How billing behaves (`[documented]`)

- **Processor:** Stripe. Charges, payouts and disputes settle through the gym's Stripe account.
- **Invoice actions:** `Create Next Invoice`, `Change Billing Date`, `Change Amount/Discount`, and
  `Unlock` for an invoice stuck as "currently charging" — a locked ACH invoice needs *Unlock* before a
  retry, so do not blind-retry.
- **Retries:** members with a valid card get an automatic nightly retry on overdue balances.
  "Billing on the 1st" is per plan, not global; there is no built-in split payment.
- **Money facts:** refunds do not return the original processing fee; Stripe's failed-payment ($4) and
  dispute ($15) fees come out of the Stripe balance; payouts land in about 2 business days.
- **Fees by tier** (pushpress.com/pricing, fetched 2026-11-08): the *Pro* tier listed card 2.89% + $0.30
  and ACH 0.79% + $0.30. A separate ACH article quotes "0.8% + $0.30, capped at $5". The sources
  disagree and PushPress changes its pricing; confirm against a real deposit before quoting.

## 8. Recipes for reconciliation

Membership income flows PushPress → Stripe → the bank. These are read-only routes for checking one stage
against the next (a budget, a ledger or a bookkeeping tool):

| Question | Route |
|---|---|
| What was collected in month M, by payment type | Payments ▸ Transactions with range `M-01…M-end`; read *Income* and *Payment Types* on screen |
| What did Stripe actually pay out | Payments ▸ Daily Deposits for the same range — payouts are **net of fees, refunds and disputes**, so they will not equal gross revenue; reconcile against the bank line in your bookkeeping tool |
| What should come in next | Payments ▸ Payments Forecast (*Next month*), or Financial ▸ Upcoming Payments — compare with your own forecast |
| Who left, paused or changed plan, and the revenue effect | Reports ▸ Membership Change Report (*Recurring revenue impact* per row; the KPI panel gives *Recurring revenue* and churn for the range) |
| What is overdue | Invoices ▸ *Overdue*; Payments Forecast ▸ *Overdue* |
| Do advertised prices match billed prices | Plans ▸ Plans for prices; `/landing/plans/<id>` JSON for the public price; discounts are **only** visible in the UI |

Figures read from a PushPress screen are a cross-check, not a source of record: re-read them on the day
you quote them, and do not change a figure in another system from a screen alone.
