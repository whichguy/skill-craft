# Help desk ticket service specification

## Requirements

### R-1 Configurable, fixed due times

Basis: 2026-11-21 response-time request, S1–S4. For newly created tickets with due times enabled, the API returns `due` in UTC ISO format. Add 4/24/72/168 hours for urgent/high/normal/low respectively to the stored creation instant. Each target is configurable independently at startup using `DUE_HOURS_<PRIORITY>`, a positive whole-hour value. Invalid overrides name the variable when used. Priority edits, status transitions and changed targets on restart leave stored deadlines alone. Verify with manual-clock HTTP mutations and a file-backed restart.

### R-2 Due display and overdue listing

Basis: S5 and S7. The exact setting `DUE_TIMES=on` exposes due on ticket responses and human-facing CLI output. Raw CLI output retains the four columns consumed by the report. Only the exact query value `overdue=true` requests overdue filtering. At one clock sample per request, include `open` and `in_progress` tickets whose deadlines are strictly earlier, intersected with the legacy filters before cursor pagination. Existing status and priority filters retain their OR behavior when combined. Verify using mixed statuses, future and exact-due cases, and a paged query.

### R-3 File preparation and rollback

Basis: S6–S8, decision 8. Historical records derive their first deadline from their own saved creation and priority. A repeat preparation preserves existing values, audit, notifications and counters. Persist atomically before enabled service starts answering, with a documented offline production preparation command for completing the file before setting the gate. Flag-off answers and CLI output stay identical even with prepared data, and flag-off writes preserve stored deadlines. The actual 1.4.0 process must open the candidate's file and list every ticket. Files rewritten by 1.4.0 lose fields its writer ignores. Verify with file-backed startup, repeat migration and original-release smoke checks.

### R-4 Existing behavior and additive tests

Basis: S1, S9–S10 and CONTRIBUTING.md. The existing entry points, error envelope, audit, notification delivery and report continue to operate without npm dependencies. Add node:test coverage under test/ and run the unchanged existing tests alongside it via npm test.

## Non-functional requirements

Keep the one-writer operational model. Local file updates publish as a single atomic replacement using the existing storage boundary. Preserve CLI layout and raw interchange. No new network, secrets, identity, retention, browser interaction or async worker work is needed.

## Retired

None.
