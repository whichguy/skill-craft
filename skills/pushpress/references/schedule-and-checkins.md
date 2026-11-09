# Schedule, check-ins, class types and payroll

Verified read-only on **2026-11-08**. `[observed]` is the default; `[documented]` = help-center only;
`[not exercised]` = the control exists but writes or sends, so it was not run.

## Contents
1. [How the pieces fit](#1-how-the-pieces-fit)
2. [Calendar](#2-calendar-schedule)
3. [Classes and Events lists](#3-classes-and-events-lists)
4. [Check-Ins by day](#4-check-ins-by-day)
5. [Class page](#5-class-page-schedulecal-id)
6. [Class types, pay rates and locations](#6-class-types-pay-rates-and-locations)
7. [Appointments](#7-appointments)
8. [Payroll and no-shows](#8-payroll-and-no-shows)
9. [Recipes](#9-recipes)

## 1. How the pieces fit

A **class type** (name, colour, free/paid, pay rates) is the template; a **class** is a scheduled
instance on the **calendar**, at a **location**, with staff; **check-ins** record who showed up.
**Events** and **Appointments** are separate calendar object types with their own lists and setup.
Coach **payroll** is computed from coach check-ins and pay rates, so an unchecked class earns nothing.

## 2. Calendar (`/schedule`)

Week view. Toolbar: **Public Calendar** icon (popup item *Public / Embeddable Calendar* — the
website-embed link), **gear = Setup** (menu: **Class types**, **Locations**), **Create** (menu:
**Class**, **Event**, **Appointment** — each opens a create form, `[not exercised]`), `Today`, previous
and next, the month label, a view selector (*Week*), `Filter`, `Save filters`.

## 3. Classes and Events lists

- **`/schedule/classes`** — list view. Buttons `Setup` (goes **straight to class types** — no menu, unlike the
  Calendar gear), `Class` (not opened —
  on Events the equivalent is `Event`), previous/next range, `Filter`, `Save filters`, `More options`.
  Columns Date · Staff · Attendance. This is a list of class *instances*, not class types.
- **`/schedule/events`** — same layout with an `Event` filter. Events are real in this UI (the
  help-center material did not describe them); an empty list reads "Nothing to show!".

## 4. Check-Ins by day

`/calendar/checkins/MM/DD/YYYY` (the sidebar link opens on today). Header "Check-ins: <date>";
`Previous day` / `Next day`; section **Classes (N)** or "No classes scheduled"; **open gym** section
("No open gym check-ins"); `Add check-in`; `Expand all classes` / `Collapse all classes`.

Each class is a card "`<time> <class name> Class a/b`" — **checked-in / limit** — that
expands to a table Name · Role · Plan · Status · Actions. Scheduled staff appear in that table with Plan
*Scheduled Staff* and Status *Scheduled*; attendees appear alongside. A card links to the class page.

**Reading zeros (interim):** a card reading `0/…`, or a dashboard *Check-ins* tile reading 0, means no
check-ins were *recorded* — not necessarily that nobody came (members may not be checking in, or marks
may not be saved). Cross-check with the API (`checkins-count`) before drawing conclusions about
attendance.

## 5. Class page (`/schedule/cal-<id>`)

Reached by clicking a class card (Check-Ins) or a calendar entry; the Check-Ins links use
`/calendar/view/<id>` and resolve here. Two panels:

- **Class info** (left): class name with a *Recurring class* marker, date and time, **Coach** and
  **Assistant coach** each with a `Check in` button (staff check-in — payroll depends on it),
  *Attendees* "n / limit" with a bar, *Location*, *Reservations open* (for example "Immediately") and
  *Reservations close* (for example "At class start time"). Two **icon-only** buttons sit at its top right, with no
  text label — find them by role or position (`find` on Claude in Chrome): a **pencil** (Edit class) and a **⋮** menu holding
  **Delete** and **Duplicate** (both `[not exercised]`).
- **Attendance** (right): table Name · Plan · Status, `+ Add` (add an attendee), and three icon buttons:
  download (`Export Class registrations`, **DOWNLOAD**), chat and mail (labelled `No attendees to text` /
  `No attendees to email` while the roster is empty — the labels *with* attendees were not observed). The
  chat and mail icons are bulk **OUTBOUND** actions.

**Edit class** (the pencil) opens a form at `/schedule/cal-<id>/edit/class/cal-<id>` with *Class name*,
*Type*, *Start date*, *Start time*, *End time*, *Coach*, *Assistant Coach*, *Reservations open*,
*Reservations close*, an `Attendance limit` toggle with *Attendance number*, *Minimum notice to keep
session*, *Location* and *Description*, and the buttons **Cancel** and **Save**. This is how one class is
rescheduled; leave it with `Cancel`. `[not exercised: Save]` — whether a change applies to this
occurrence only or to the whole recurring series was **not observed**, so ask before saving anything on
a *Recurring class*.

## 6. Class types, pay rates and locations

These pages are **not in the sidebar**.

| Page | Path | Reach via | Contents |
|---|---|---|---|
| **Class types** | `/schedule/class-types` | Schedule ▸ Classes ▸ **Setup**, or Calendar ▸ gear ▸ *Class types* | title "Class types"; `Back`; `Setup pay rates` and `+ Class type`; table Name (colour dot) · Free; per-row ⋮ menu: **Edit · Edit pay rates · Delete** |
| **Locations** | `/locations` | Calendar ▸ gear ▸ *Locations* | `Back to calendar`; `+ Location`; rows with ⋮ |
| **Appointment setup** | `/appointments/settings` | Appointments ▸ **Setup** | tabs *Types / Packages / Discounts / Payrates*; `+ Type` |

The API lists class types (`classes-type-list`, read-only) but cannot create or edit them. Pay rates
also appear per staff member on the staff profile (*Class type · Coach pay rate · Coach check-in pay ·
Asst. coaching pay rate*).

## 7. Appointments

`/appointments`: week view titled by month, `Previous`/`Next`, `Filter`, `Save filters`, view selector,
`Learn more`, `Setup`, `Add Credits`, `Book Appointment`, `Export appointments schedule (CSV)`
(**DOWNLOAD**). Types, packages and booking were not examined: treat this module as unverified.

## 8. Payroll and no-shows

- **Reports ▸ Payroll** (`/reporting/export-payroll`) — an embedded analytics report ("Payroll Report"),
  default date range *Previous Month*. A banner says coaches must check in to the class or appointment
  and pay rates must be set; the report updates hourly. Tables: **Summary** (Staff · Appointments count
  · Appointments earnings · Classes & event count · Classes & event earnings · Earnings) and
  **Appointments** (Staff · Client · Name · Date/Time · Status · Pay type · Pay rate · Earnings). Their
  contents were not seen live. This route does a **full page load** and the content is inside an iframe.
- **Reports ▸ No Show / Late Cancel** (`/no-show`) — date-range button (default 1st of month to today),
  `Filter`, `Download`; an empty result reads "Nothing to show!".

## 9. Recipes

| Goal | Steps |
|---|---|
| See a day's classes and attendance | `navigate` to `/calendar/checkins/MM/DD/YYYY`; read each class card's `a/b`; `Expand all classes` for names |
| Open one class's roster | Check-Ins ▸ click the class card ▸ `/schedule/cal-<id>` ▸ *Attendance* |
| Reschedule or edit one class | class page ▸ pencil ▸ *Edit class* ▸ change the times ▸ `Save` (**WRITE-DATA** — confirm first; recurring-series scope unverified) |
| Tell attendees about a change | class page ▸ chat / mail icons (**OUTBOUND**) — confirm recipients and wording first; do the schedule edit first |
| Get a class roster programmatically | API `classes-get id=<id> expand=["reservations"]` ([api-and-mcp-tools.md](api-and-mcp-tools.md) recipe 4) |
| Find where class types are edited | Schedule ▸ Classes ▸ `Setup` → `/schedule/class-types` ▸ row ⋮ ▸ *Edit* (editor `[not exercised]`) |
| Check whether coaches are being paid for a class | class types ▸ *Edit pay rates* (read only); Reports ▸ Payroll; remember payroll needs coach check-ins |
| Pull a date range of check-ins | API `checkins-class-list after=<unix> before=<unix>` (seconds), or `checkins-count include=classes` for the number |
