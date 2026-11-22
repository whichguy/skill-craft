# Part R: every finding of the 24 reviews, reproduced by two Sonnet subagents that ran the products

## The brief both were given

# Brief: check what twelve reviews claim, by running the products

You verify claims. Twelve short review files each judge a delivered change to a help-desk ticket service (a
Node.js service with no npm dependencies). Each review lists findings: a difference it says exists between what
was asked (or what the product did before) and what the delivered product does, with a probe. Your job is to say,
by running the products yourself, which of those claimed differences are real. You do not judge whether a
difference matters, and you do not review the products yourself beyond the claims made.

## Where things are

Everything is under
`<scratch>/lens/r-verify/`:

- `reviews/`: the review files for your set (named in your task message). A file's name starts with the product it
  reviews: `wa…` reviews product `ka`, `wb…` reviews `kb`, `wc…` reviews `kc`, `wd…` reviews `kd`.
- `products/ka`, `products/kb`, `products/kc`, `products/kd`: the delivered products. `products/starting`: the
  product before the change. **Never change anything under `products/`.** To run a product, first copy it into
  your own folder under `work/<your set>/` and run the copy there.
- Each product is started with `PORT=<port> node src/server.js` from its folder (`DATA_FILE=<path>` makes it keep
  its data in a file; `README.md` and `docs/` in the product say the rest), and has a command-line tool,
  `node bin/tickets.js`.

## Rules

- Use a free port for every server you start (ask the system for one; never a fixed default). Stop every process
  you started, by its process id. Never stop processes by name (no pkill, no killall).
- Temporary files go under your `work/<your set>/` folder. Install nothing. Do not use Git to commit anything.
- Do not read any file outside the folder above. Write only under `work/<your set>/`.

## What to do

1. Read every review in your set. Make one list of the **distinct findings** over all of them: two findings in
   different reviews that claim the same difference are one. For each, note which reviews make it.
   Only the entries under `## Findings` count; entries under `## Decisions made for the requester` and under
   `## What must be true` are not findings.
2. For each distinct finding, reproduce it: run the claimed probe (or the shortest equivalent) on
   `products/starting` and on each delivered product whose review makes the claim. Then sort it:
   - `real`: you saw the difference the finding claims (the delivered product does what the finding says, and the
     starting product, or the request's own words, differs as the finding says).
   - `not real`: you ran it and the claimed difference is not there.
   - `could not run`: say why.
   Give the commands you ran in short form and what each returned (status codes, the lines that matter).
   Where two delivered products are reviewed with the same claim, say for each product whether it is real there.
3. Two readings, by reading only:
   - For each review of product `ka`: does one of its findings say that the delivered product refuses an edit of
     a **resolved** ticket (a `PATCH` of its title or priority) that the starting product allowed? `yes`, with
     the finding's first words, or `no`.
   - For each review of product `kc` or `kd`: does the review say, under `## Findings` or under
     `## Decisions made for the requester`, **how the tickets already in the data file get their due times, or
     what the service does when it is started with `DUE_TIMES=on` while tickets lack due times** (for example: a
     separate preparation command and a refusal to start, or the service filling them in at start)? `yes`, with
     the heading it stands under and the entry's first words, or `no`.

## What to send back

- A table of the distinct findings: a short name, the reviews that make it, the products it is claimed for, and
  `real` / `not real` / `could not run` for each product, with the evidence in a line or two.
- The two readings of step 3, one line for each review in your set that the reading applies to.
- For each review: its `Verdict:` line, the number of its findings, and how many of them you found real.
- Anything that surprised you, stated as fact.

Keep the report to what is asked. It is read by another agent.

## Report on the twelve ticket-assignment reviews (products ka and kb), word for word

Set `assignment` (wax1-3, way1-3 review ka; wbx1-3, wby1-3 review kb). All distinct findings reproduced by running copies under work/assignment/ (starting, ka, kb). Every server I started was stopped by pid; nothing under products/ was touched. Nothing was "could not run".

## Distinct findings (only entries under `## Findings` counted)

| # | Finding | Reviews making it | Claimed for | ka | kb |
|---|---|---|---|---|---|
| F1 | PATCH of title/priority on a resolved ticket is refused with 409 `conflict`; starting allowed it | wax1, wax2, wax3, way1, way2, way3 | ka | REAL. Create, in_progress, resolved, then PATCH {title,priority}: starting 200 (title "Edited", priority high); ka 409 "ticket T-0001 is resolved and can no longer change", GET still shows old title/priority. | NOT REAL (not claimed; tried anyway). kb PATCH on resolved returns 200 and saves the edit. kb still returns 409 for a closed ticket, as the starting product does. |
| F2 | CLI `list --status S --priority P` now requires both to match; starting listed tickets matching either, so rows vanish (table prints `no tickets`, raw prints zero rows) | ka: wax1-3, way1-3. kb: wbx1-3, wby1-3 | ka, kb | REAL. File with T-0001 resolved/urgent, T-0002 in_progress/normal, T-0003 resolved/urgent->, T-0004 open/normal: `list --status open --priority urgent` gives starting T-0001,T-0003,T-0004; ka `no tickets`, exit 0; `--raw` zero rows. `--status open --priority normal` gives starting T-0001,T-0002,T-0004; ka T-0004 only. Single-filter listings unchanged. | REAL, identical output to ka. |
| F3 | CLI table shows `-` both for an unassigned ticket and for a ticket assigned to the valid name `-` | wax1, wax2, wax3, wbx1, wbx2, wby2 | ka, kb | REAL. `PUT /tickets/T-0002/assignee {"assignee":"-"}` returns 200 with assignee "-"; T-0001 unassigned (GET gives null); `list` shows `-` in the ASSIGNEE column for both rows. | REAL, identical. |
| F4 | `list --raw` gains a fifth tab field, even for unassigned tickets (trailing tab), breaking readers that expect four fields or the title last | wax2 (ka); wbx1, wbx2, wbx3 (kb) | ka, kb | REAL. Same file: starting rows have 4 fields, and `awk -F'\t' 'NF!=4{exit 1}'` exits 0. ka rows read `T-0001\tresolved\turgent\tResolved urgent\t` and the awk check exits 1; last field is "". After assigning dana the row ends `...One\tdana`. wbx3's shell check (`IFS=<tab> read -r id status priority title`) gives title `One<TAB>dana` for an assigned row, and the plain title for unassigned rows because read strips the trailing tab. `scripts/weekly-report.js --json` returns identical counts on starting and ka (total 4, open 3, resolved 1, low 1, normal 1, urgent 2), as the reviews also say. | REAL, identical to ka, weekly report also identical. |
| F5 | Loader accepts a hand-edited `assignee` of 65 chars at startup and GET exposes it, while PUT with the same name returns 400 | wax1 (ka); wby3 (kb) | ka, kb | REAL. File with `tickets[0].assignee='a'.repeat(65)`: server starts, `GET /tickets/T-0001` 200 with length 65; `PUT` same name 400 `invalid` "assignee must be at most 64 characters". Loader does refuse assignee 5 and assignee "" at start (startup error). | REAL, identical. |
| F6 | A pending assignment notice for ticket+agent suppresses the notice for a later assignment back to that agent (A, B, A; or A, null, A) | way2 (ka); wbx1, wby3 (kb) | ka, kb | REAL. WORKER_INTERVAL_MS=0, PUT dana, lee, dana: all three 200, audit has three `ticket.assigned` entries (null to dana, dana to lee, lee to dana); outbox holds only 2 assignment events (dana, lee); after restart with the worker and NOTIFY_FILE, delivered: requester created notice, "Assigned to you" to dana, to lee. None for the third. amina, null, amina: audit has 3 entries, outbox 1 assignment event, 1 delivered. | REAL, identical outputs. |
| F7 | `GET /tickets?assignee=dana&assignee=lee` ignores the second value, so returns a ticket failing the second filter (breaks "must match every filter given") | wbx2 | kb | REAL in behaviour. ka: `assignee=dana&assignee=lee` returns T-0001 (dana); `assignee=lee&assignee=dana` returns T-0002 (lee). First value wins. `assignee=dana&assignee=` returns dana's ticket. | REAL in behaviour as claimed (same results as ka). |

Context for F7 and F2: the starting product already uses the first value for a repeated `status` (`?status=open&status=in_progress` returns only the open ticket). Whether first-value-wins breaks the request's "match every filter given" wording is a judgement I did not make. For F2, the starting product's HTTP `GET /tickets?status=open&priority=urgent` also behaved as "either" (returned T-0001,T-0003,T-0004), contrary to its own docs/api.md line 76 ("matches every filter given"). Cause: `matchesFilters` in starting/src/tickets/query.js uses `.some`. Both delivered products' HTTP and CLI now return none for that query.

## Step 3 reading (ka reviews: does a finding say the delivery refuses an edit of a resolved ticket that the starting product allowed?)
- wax1: yes, "The starting API lets operators edit a resolved ticket's title or priority".
- wax2: yes, "The starting API lets operators edit a resolved ticket's title or priority with `PATCH /tickets/:id`".
- wax3: yes, "The starting API lets an operator edit the title or priority of a resolved ticket".
- way1: yes, "The starting product lets operators correct the title and priority of a resolved ticket with PATCH".
- way2: yes, "PATCH previously allowed ordinary edits to resolved tickets".
- way3: yes, "The starting API allowed title and priority edits on resolved tickets".

(The kc/kd reading does not apply to this set.)

## Per review: Verdict, findings, real
| Review | Verdict | Findings | Real | Which |
|---|---|---|---|---|
| wax1 | reject | 4 | 4 | F1, F2, F3, F5 |
| wax2 | reject | 4 | 4 | F1, F2, F4, F3 |
| wax3 | reject | 3 | 3 | F1, F2, F3 |
| way1 | reject | 2 | 2 | F1, F2 |
| way2 | reject | 3 | 3 | F1, F6, F2 |
| way3 | reject | 2 | 2 | F1, F2 |
| wbx1 | reject | 4 | 4 | F4, F2, F6, F3 |
| wbx2 | reject | 4 | 4 | F2, F4, F7, F3 |
| wbx3 | reject | 2 | 2 | F4, F2 |
| wby1 | reject | 1 | 1 | F2 (table and raw) |
| wby2 | reject | 2 | 2 | F2, F3 |
| wby3 | reject | 3 | 3 | F6, F2, F5 |

## Things that surprised me (facts)
- ka and kb differ in one line only (`src/store.js` line 90): ka checks `!isActive(status)` and kb checks `isFinal(status)` in the PATCH path. That is the whole of F1: real in ka, absent in kb. Every other finding behaved identically in the two products.
- Starting product's loader only checks that strings are non-empty. A 65-char requester and a 201-char title in a data file load and are served (GET 200, lengths 65 and 201). So F5 is consistent with the starting loader's existing looseness, but the reviews' premise that "the service validates saved records at startup" holds only for type/emptiness.
- `ratchet`/`acceptance` exist in ka and kb; I did not run them (not needed for any claim).
- F4 shell-based consumer break (wbx3) shows only for assigned tickets. With an unassigned row, `read` strips the trailing tab, so the title field looks unchanged.
- A finding present in four reviews of ka (F1) is absent from all six kb reviews, and kb reviews list nothing about PATCH at all. That matches the one-line code difference.

## Report on the twelve due-times reviews (products kc and kd), word for word

All findings in the `due-times` set were reproduced by running the products. Every finding in these twelve reviews is real for the product its review covers. Working copies and probe scripts are under `work/due-times/` (`starting`, `kc`, `kd`, `h.js`, `c1.js` to `c7.js`, `d1.js` to `d3.js`, data in `t/`). `kc` is 1.5.2 and uses `npm run prepare:due-times`; `kd` backfills at enabled startup and reads `DUE_HOURS_*`. Servers were started with `PORT=0`, and every process I started was stopped by its own process id. I did not run the `kc` acceptance suite.

## Distinct findings

| # | Finding | Reviews | Claimed for | Result |
|---|---|---|---|---|
| C1 | `GET /tickets?status=open&priority=urgent` matches either filter in 1.4.0. With `DUE_TIMES=on` it requires both, and `overdue=false` or no `overdue` makes no difference. | wcx1, wcx2, wcx3, wcy1, wcy2, wcy3 | kc | **real** |
| C2 | With the flag off, a create at the largest safe counter returns 201 in 1.4.0 and 500 in the delivery. This applies to both `nextNumber` and `outbox.nextId`. | wcx1 (nextNumber), wcx2 (both), wcx3 (nextNumber), wcy1 (nextNumber), wcy3 (both) | kc | **real** |
| C3 | Preparation, recovery and enabled startup accept a `due` earlier than `created` when `created` is in a legacy spelling with an explicit offset. | wcx1, wcx2, wcx3, wcy3 | kc | **real** |
| C4 | Preparing a symlinked `DATA_FILE` replaces the link with a regular file and leaves the backing file unprepared. | wcx1, wcx2, wcx3, wcy3 | kc | **real** |
| C5 | With the flag off, a failed save rolls back the in-memory change in the delivery. | wcx1 only | kc | **real** |
| C6 | Raw CLI list and the weekly report escape tabs and newlines in stored titles, with the flag unset. | wcy1 | kc | **real** |
| C7 | A literal CR and a literal backslash-r in two stored titles become identical in `list --raw`. | wcy2 | kc | **real** |
| D1 | A ticket created with the flag off gets no saved `due`. Enabling later computes it from the then-current priority and hours. | wdx2, wdy1, wdy2 | kd | **real** |
| D2 | An hours value too large to give any valid due is accepted at startup, and creating a ticket of that priority returns 500. | wdy2 (`DUE_HOURS_HIGH=4800000001`), wdy3 (`DUE_HOURS_URGENT=9007199254740991`) | kd | **real** |
| D3 | A save by 1.4.0 drops every `due`, and the later enabled start recomputes different deadlines. | wdy3 | kd | **real** |

Evidence for each:
- **C1.**
  - Setup: a prepared 3-ticket file with T-0001 open low, T-0002 in_progress urgent, T-0003 open urgent.
  - `starting`, and `kc` with the flag off, both returned 200 with `[T-0001, T-0002, T-0003]`.
  - `kc` with `DUE_TIMES=on` returned 200 with `[T-0003]`. Adding `&overdue=false` gave the same, and `&limit=1` gave `next: null`.
  - With status alone it returned T-0001 and T-0003, and with priority alone T-0002 and T-0003.
- **C2.**
  - `starting` returned 201 with `T-9007199254740991` and saved `nextNumber` 9007199254740992.
  - `kc` with `DUE_TIMES=off` returned 500 `internal` and left the counter unchanged.
  - Setting `outbox.nextId` to the maximum gave 201 in `starting` (outbox 9007199254740992) and 500 in `kc` (outbox unchanged).
  - For information, `kd` behaves like `starting` on both counters.
- **C3.**
  - Setup: `created` is `Mon, 01 Sep 2025 08:15:00 +0200` (06:15Z) with `due` `2025-09-01T06:14:59.999Z`.
  - `prepare:due-times` exited 0, enabled `GET /tickets/T-0001` returned 200 with that `due`, and `?overdue=true` listed it. `2025-09-01 08:15:00+02:00` did the same.
  - A recovery file holding the early `due` also exited 0 and copied it into the live file.
  - The ISO control `2025-09-01T08:15:00+02:00` exited 2.
  - Preparation with no `due` on the RFC spelling assigned `2025-09-01T10:15:00.000Z`, which is correct.
  - I used `.999Z`; wcx3's `.998Z` is the same case.
- **C4.**
  - `ln -s backing.json production.json`, then `DATA_FILE=production.json npm run prepare:due-times` exited 0. `production.json` was no longer a symlink and held `due`; `backing.json` had none.
  - Enabled start on `backing.json` exited 2 with a message about a missing `due`.
  - An enabled create through `production.json` returned 201 `T-0004`. Then 1.4.0 listed 4 tickets through `production.json` and 3 through `backing.json`.
  - Side fact: a 1.4.0 service on the symlink path, and `kc` and `kd` with the flag off, also replace the symlink on their first save. So the replacement is not new to preparation.
- **C5.**
  - After starting with a file-backed T-0001 titled `Before`, I moved the data directory aside and put a regular file in its place.
  - `PATCH` of the title returned 500 `internal` on both products.
  - The next `GET` returned title `Attempted change` on `starting` and `Before` on `kc`.
  - I ended each service by SIGKILL on its pid.
- **C6.**
  - Setup: titles with a literal tab (T-0001) and a literal newline (T-0002).
  - `starting` printed literal separators, so the newline broke a line.
  - `kc` printed `\t` and `\n` as visible escapes.
  - The weekly report `--json` total on a 4-ticket file with one newline title was 5 on `starting` and 4 on `kc`. Status and priority counts were identical in both.
  - `kd` matches `starting`.
- **C7.**
  - Titles `First<CR>part` and `First\rpart` (backslash, `r`) were distinct in `starting` and `kd`.
  - In `kc` both printed as `First\rpart`.
- **D1.**
  - I ran this with the real clock. I could not set a clock, but the probe does not need one.
  - Under `DUE_TIMES=on`, T-0001's `due` was assigned.
  - Then with `DUE_TIMES=off DUE_HOURS_URGENT=4` I created two urgent tickets. Both returned 201 with no `due` in the response, and neither had `due` on disk.
  - I patched T-0004 to low and restarted with `DUE_TIMES=on DUE_HOURS_URGENT=6`.
  - T-0004 got `created + 168h`.
  - T-0005 got `created + 6h` (`08:31:29.998Z`), where the creation-time schedule gives 4h.
- **D2.**
  - `kd` with `DUE_TIMES=on DUE_HOURS_HIGH=4800000001` started. `/health` returned 200, a high-priority create returned 500 `internal`, and a normal create returned 201.
  - `DUE_HOURS_URGENT=9007199254740991` behaved the same.
  - Controls: `0` and `9007199254740992` are refused at startup with exit 2 ("must be from 1 to 9007199254740991").
- **D3.**
  - On `kd` (on), I created urgent T-0004 and patched it to low; its `due` was `2026-11-22T06:31:44Z`.
  - 1.4.0 on the same file listed 4 tickets, and a create there succeeded. Afterwards 0 tickets on disk had `due`.
  - Re-enabling `kd` with `DUE_HOURS_LOW=192` gave T-0004 `2026-11-30T02:31:44Z`, which is 192h after creation and not the original 4h.

## Step 3: how tickets already in the data file get due times (all twelve reviews)

All twelve say yes, each under `## Decisions made for the requester`.
- wcx1: yes, "Assign deadlines to existing tickets through a separate offline `npm run prepare:due-times` step and require readiness before enabled startup".
- wcx2: yes, "Assign old tickets through an explicit offline command and refuse enabled startup on an existing incomplete snapshot".
- wcx3: yes, "Assign historical deadlines with a separate offline command and refuse enabled startup on an incomplete existing file".
- wcy1: yes, "Use an explicit offline npm run prepare:due-times command and refuse enabled startup on an incomplete existing file".
- wcy2: yes, "Prepare the version-1 file with the separate npm run prepare:due-times command while its writer is stopped".
- wcy3: yes, "Use a separate offline npm preparation command and refuse enabled startup when a populated file is missing deadlines".
- wdx1: yes, "Prepare and save missing deadlines during enabled startup before opening the listener".
- wdx2: yes, "Prepare missing deadlines on enabled startup before opening the listener".
- wdx3: yes, "Prepare missing deadlines during enabled startup and save them before listening".
- wdy1: yes, "Backfill synchronously on enabled startup before accepting traffic".
- wdy2: yes, "Prepare synchronously at enabled startup".
- wdy3: yes, "Prepare missing deadlines in one enabled startup before binding the port".

## Per review

| Review | Verdict | Findings | Real |
|---|---|---|---|
| wcx1 | reject | 5 (C3, C4, C1, C5, C2) | 5 |
| wcx2 | reject | 4 (C1, C2, C3, C4) | 4 |
| wcx3 | reject | 4 (C1, C4, C3, C2) | 4 |
| wcy1 | reject | 3 (C1, C2, C6) | 3 |
| wcy2 | reject | 2 (C1, C7) | 2 |
| wcy3 | reject | 4 (C1, C3, C4, C2) | 4 |
| wdx1 | accept | 0 ("none") | 0 |
| wdx2 | reject | 1 (D1) | 1 |
| wdx3 | accept | 0 ("none") | 0 |
| wdy1 | reject | 1 (D1) | 1 |
| wdy2 | reject | 2 (D1, D2) | 2 |
| wdy3 | reject | 2 (D3, D2) | 2 |

## Things that surprised me
- `starting` (1.4.0) itself replaces a symlinked `DATA_FILE` with a regular file on its first save. C4 is therefore only new in that preparation does it before activation.
- wcy2's and wdy2's "What must be true" sections mark some items `broken` that are not findings. I did not examine them, per the brief.
- In `kc`, a failed prepare or recovery (exit 2) leaves the file without `due` (checked on the ISO recovery case).
