# Safety: classes, confirmation, personal data

These rules are the reason a catalogue entry has three separate fields. A single label cannot say that a financial report is
sensitive, exported and possibly emailed.

## The three fields

| Field | Values | Meaning |
|-------|--------|---------|
| `mode` | `read`, `guided`, `owner-only` | `read` runs through `sport80 js`; `guided` is walked through the portal's own form with the owner; `owner-only` the agent never drives |
| `effects` | `read`, `export`, `write`, `outbound`, `financial`, `security` | what running or completing it does; a list, because effects combine |
| `data` | `public`, `personal`, `sensitive` | what the result contains |

`sensitive` is: background screening, SafeSport and certifications, collegiate eligibility, addresses, notes, birth dates,
membership numbers in bulk, the roster search, transactions, merchants, disputes, access management and sessions. Identifiable
minors count as sensitive wherever they appear.

## What the runtime enforces

- A `guided` or `owner-only` entry never runs: `sport80 js` refuses it and the runtime returns `NOT_RUNNABLE`.
- A `sensitive` table returns the total and the column list and no rows. Rows need `--rows N` and `--fields a,b` together.
- A search that must be filtered (the roster quick search) refuses to run without a filter.
- Entries never exercised are listed but not offered as runnable unless `--unverified` is passed and reported as unverified.
- Required parameters, enumerated values and filter names are checked before any request.
- Results carry only chosen fields; header values never appear; UUID-shaped strings become `<uuid>`.

## Confirmation

Confirmation applies to the concrete target and effect, and an explicit instruction in the owner's request counts. A general
request ("sort out the club's renewals") does not authorise a specific purchase or message.

| Effect | Before you do it |
|--------|------------------|
| `write` | state the exact change and record; the owner says yes; use the portal's own form; stop before the final submit if unsure; read back afterwards |
| `export` | name the report, columns and filter; the owner downloads and keeps the file; its contents never go into a repository or note |
| `outbound` | draft only; show the audience as a count and the full text; send only after a yes for that audience and that message |
| `financial` | state item, person and total; stop before the payment step; never type card or bank details; the owner pays; never confirm an order without a yes naming item and total |
| `security` | never automate (2FA, password, sign-out, ending sessions, access management); tell the owner where the page is |

## Never

- Fetch or click Logout, Manage 2FA or Change Password, or probe Setup Club.
- Enter, request, store or echo a password, 2FA code, card, bank detail, token or cookie.
- Solve a CAPTCHA or work around a challenge or throttle.
- Create or change a person's record, buy, renew, register, sanction, email or export without the owner's yes for that act.
- Call a write or payment endpoint directly from a script.
- Read a member's record the owner did not ask about, or widen a lookup to scan a roster.
- Open the Archive Member tab, press Add Note, or press any other button inside a member's record without the owner's yes for that act.

## Personal data (including minors)

The club roster holds children. Use the smallest answer that serves the request: a count over a list, a list of names over
a record, one field over many. Counts for very small groups can identify a person, so say a group is small instead of
describing it. Do not infer ages, health, eligibility or family relationships. Never copy member data into a file, commit,
issue, note or journal; describe structure and counts only. When an owner asks to export, point to the portal's own export
(Queued Reports) rather than rebuilding the roster in chat.
