# Real-repo apparatus: three features on `node-tickets`, composed and checked

What this builds: reference patches for the three E2E cases that target `test/shiploop_e2e/fixtures/node-tickets`
(`ticket-assignment`, `ticket-import`, `ticket-due-times`), one composed patch that carries all three at once, and
`interactions.py`, a standard-library script that checks the five ways the three features interact and proves itself
against scratch copies (the composed tree, the bare base, and six single-point mutations). Nothing under
`test/shiploop_e2e/` was read for anything but reference, and nothing there was changed.

> **Update, after independent review:** three assertion holes in I3/I4/I5 were closed and three more mutations
> ((d), (e), (f)) were added to `--selfcheck`, plus a preliminary start-probe so `check` reports one clean error
> instead of five identical failures when a tree cannot run at all. See "Update: assertion-hole fixes" near the end
> of this report for exactly what changed, why, and the full re-run table.

## Files

```
refs/T1.patch          ticket-assignment alone, against the base
refs/T2.patch          ticket-import alone, against the base
refs/T3.patch          ticket-due-times alone, against the base
refs/composed.patch    all three together, against the base, conflicts resolved by hand
interactions.py        I1-I5 (`check TREE`) and the self-check (`--selfcheck`)
REPORT.md              this file
```

## How each reference was chosen and verified

Each of the three E2E run folders named in the brief is a real git worktree (not just a `delivery/work.bundle`
listing). For each one I:

1. Found its first commit (`base: node-tickets`) and diffed it byte-for-byte against the live fixture at
   `test/shiploop_e2e/fixtures/node-tickets` (`git archive <first-commit> | tar -x` into a scratch folder, then
   `diff -rq --exclude=.git`). All three came back with zero differences, so each worktree really did start from
   today's base, not an older or edited copy.
2. Confirmed `result.json`'s own `checks` array for that run: all `pass: true`, matching the brief's claim that these
   are recorded *passing* deliveries.
3. Generated the reference patch as `git diff <base-commit> HEAD -- . ':!docs/shiploop'` (excludes only the ShipLoop
   knowledge files; everything else the delivery touched is in scope by the brief's own list).
4. Applied the patch to a **fresh** copy of the base in a scratch git repo (`git apply --check` then `git apply`) and
   ran that case's own `checks` list for real, from that tree, with `E2E_CHECKS` set to `test/shiploop_e2e/checks`.

All three applied cleanly and passed every one of their own checks on the fresh tree:

| Patch | Files touched | `suite` | `pristine` | HTTP / probe checks |
|---|---|---|---|---|
| T1 (assignment) | README.md, docs/api.md, src/app.js, src/format.js, src/persistence.js, src/store.js, src/templates.js, src/tickets/{query,validate}.js, test/assignment{,-system}.test.js | 124 tests, base's 117 + 7 | 117/117 | PUT assignee check: pass |
| T2 (import) | README.md, docs/api.md, src/app.js, src/store.js, src/tickets/validate.js, test/import.test.js | 121 tests, +4 | 117/117 | POST /tickets/import check: pass |
| T3 (due times) | CHANGELOG.md, README.md, docs/api.md, docs/operations.md, **fixtures/persistence-1.4.0.js**, package.json, src/{app,config,persistence,server,store}.js, test/due-times.test.js | 155 tests, +38 | 117/117 | migrate/restart/switch/rollback/off/cli: all pass |

**One deliberate deviation from the file-scope instruction:** the due-times worktree's top-level `fixtures/` folder
(just `fixtures/persistence-1.4.0.js`, 206 lines) is **not** the harness's own `test/shiploop_e2e/fixtures/` tree —
it is a frozen copy of the base's `src/persistence.js` that the model wrote as the delivery's own test fixture, and
`test/due-times.test.js` `require('../fixtures/persistence-1.4.0')` directly, for the restart/rollback tests. The
general instruction to leave out "the fixtures/ folder" is written for the common case where a worktree carries the
harness's unrelated fixture catalog alongside the delivery; here, excluding it would make `npm test` fail to load the
delivery's own tests (`Cannot find module`), which would fail the `suite` check outright. I kept it in `T3.patch` and
`composed.patch`, and verified `suite`/`pristine` pass with it included (above). If the file-scope rule is meant
literally regardless, this is the one place it was broken, and on purpose.

## `refs/composed.patch`: how it was built and the conflicts resolved

Built in a scratch git repo: one `base` commit, three sibling branches each holding one reference patch as its own
commit, then `git merge` branch by branch onto a fourth branch (`t1` ff, then `merge t2`, then `merge t3`), resolving
whatever `git merge` could not. The result was diffed back against the base to produce `composed.patch`.

Files touched by more than one patch, and what happened:

| File | Touched by | Resolution |
|---|---|---|
| `src/tickets/validate.js` | T1, T2 | **Git conflict.** Kept T1's `assignee()` function and T2's `ticketImport()`/`IMPORT_LIMIT`, combined both into one `module.exports` line. |
| `src/app.js` | T1, T2, T3 | **Git conflict** (T2's new `/tickets/import` route landed next to T3's `asHttpTicket`-wrapped `GET /tickets/:id` in the same hunk). Kept both routes; also wrapped `PUT /tickets/:id/assignee`'s response in `asHttpTicket` myself (not literally in any of the three patches) so the `due` field it now carries stays HTTP-hidden while `DUE_TIMES` is off, consistent with every other mutating route. |
| `src/store.js` | T1, T2, T3 | **Git conflict**, twice. (1) the `require('./tickets/validate')` import line — kept it (T2's `createMany` needs nothing from it, but T1's `assign()` does). (2) `create`/`createRecorded`/`createMany`: T2 had already split `create` into `create` + `createMany` + `createRecorded` (to create a batch in one save); T3's `create` added `due: this.dueFrom(at, priority)` to the *old*, unsplit `create`. Merged by adding the same `due` computation into the new `createRecorded`, so both `create` (single) and `createMany` (batch) share it, and keeping T1's `assignee: null` default on the same object literal. `list()`'s `overdue` filter, `static open()`'s due-backfill, `dueFrom()` and the `due`-filtering in `apply()` all came through from T3 with no conflict (T1/T2 never touched those). |
| `docs/api.md` | T1, T2, T3 | **Git conflict**, twice, both cosmetic: the parameter table (kept both the `assignee` row and the `overdue` row) and the "filters combine" sentence (merged into one sentence covering both `assignee`/`priority`/`status` AND `overdue`). |
| `README.md` | T1, T2, T3 | Auto-merged cleanly (no conflict): T1's CLI-column note, T2's `MAX_BODY_BYTES` parenthetical, and T3's `DUE_TIMES`/`RESPONSE_HOURS_*` rows all landed in different lines of the same table/paragraph. Read back and it reads as one coherent doc. |
| `src/persistence.js` | T1, T3 | Auto-merged cleanly: T1's `assignee` field (write + validate-on-read) and T3's `due` field (write + time-check-on-read) are both present in `ticketRecord()`/`readTicket()`. |
| `CHANGELOG.md`, `package.json`, `docs/operations.md`, `src/config.js`, `src/server.js` | T3 only | No conflict (only T3 touched these); read back for sanity, unchanged otherwise. |
| `src/format.js`, `src/templates.js`, `src/tickets/query.js` | T1 only | No conflict; T1's `assignee` column/filter support only. |
| `test/assignment*.test.js`, `test/import.test.js`, `test/due-times.test.js` | one patch each | New files; no conflict by construction. |

**A real interaction the merge surfaced, fixed in `test/due-times.test.js` (not a `git` conflict — a test that
assumed it was the only feature touching ticket shape):**

- `DT-1` asserted a freshly created ticket's JSON keys were *exactly*
  `id,title,priority,requester,status,created,updated`. Composed with assignment, every ticket also carries
  `assignee` (defaulting to `null`, regardless of `DUE_TIMES`, per ticket-assignment's own contract "Every ticket
  shows its `assignee`"). Updated the expected key list to include it, in its real position (`status, assignee,
  created, updated`, matching `createRecorded`'s own property order).
- `DT-4` and `DT-4 (b)` asserted `list --raw` was exactly four columns and `show`'s field list was exactly
  `status, priority, requester, created, updated`, with no `assignee` in play at all. Updated both to expect the
  composed CLI's real output (`list --raw`'s *first four* columns still `id, status, priority, title`, now a fifth,
  `assignee`; `show`'s fields now include `assignee` between `requester` and `created`), while keeping the actual
  thing DT-4 is checking — that `due` never appears in the CLI — exactly as it was.

With those three assertions updated, `node --test` on the composed tree passes clean: **166 tests, 0 failures**
(117 base + 49 new: 7 from T1, 4 from T2, 38 from T3). `base_tests.py suite`/`pristine` agree (166/117+49 new,
117/117 pristine).

## The one case check that cannot pass composed

`ticket-due-times`'s `off` check (`due_times_probe.py off`) demands the delivered service answer **exactly** as the
base, 1.4.0, byte-for-byte across seventeen requests, while `DUE_TIMES` is unset or `off`. On the composed tree this
fails — not because anything is broken, but because ticket-assignment's `assignee` field is unconditionally present
(it is not gated by `DUE_TIMES` at all; nothing in the ticket-assignment request says it should be), so the composed
service's JSON legitimately differs from 1.4.0's even with due times off. This is a structural property of
single-feature isolation checks, not a composition bug: **any** second feature that changes the ticket's JSON shape
would fail this same probe once composed with due-times. I did not try to route around it (for example by hiding
`assignee` when `DUE_TIMES` is off, which would violate ticket-assignment's own "every ticket shows its assignee").
`interactions.py --selfcheck` encodes this as the one documented exception and does not report it as a mismatch.
Every other check of all three cases (suite, pristine, the two HTTP checks, and due-times' other five probes:
migrate/restart/switch/rollback/cli) passes on the composed tree.

## `interactions.py`

Five checks, each starting its own `node src/server.js` from the tree under test, on a free port of its own, in a
fresh scratch `DATA_FILE`/`NOTIFY_FILE`, `WORKER_INTERVAL_MS=50`, `DUE_TIMES=on` unless the check needs otherwise,
and ending only the process group it itself started:

- **I1** (assignment x import): import an urgent and a low ticket; both show `assignee: null`; both are found by
  `GET /tickets?assignee=`.
- **I2** (due times x import): both imported tickets' `due` equals `created` plus their priority's hours, within 1s.
- **I3** (assignment x due times x import): `PUT .../assignee` on an imported ticket leaves its `due` unchanged.
- **I4** (assignment filter x overdue filter): from a hand-built version-1 data file (two open urgent tickets, 10
  days old -- the base's own persistence shape, no `assignee`/`due`), the service backfills `due` at start; assigning
  one to `dana` makes `?overdue=true&assignee=dana` return exactly it and `?overdue=true&assignee=` return exactly
  the other.
- **I5** (persistence across restart): import two, assign one, restart over the same `DATA_FILE`: both still show
  `due`, and the assignment on the restarted service still shows `dana`.

```
$ python3 interactions.py check <composed tree>      # ~2s wall for all five
{
  "I1": {"ok": true, "detail": "imported [...]: both show assignee=null, both listed by assignee="},
  "I2": {"ok": true, "detail": "both imported tickets are due created + their priority's hours, within 1s"},
  "I3": {"ok": true, "detail": "assigning imported T-0001 set assignee=dana and left due at '...'"},
  "I4": {"ok": true, "detail": "overdue&assignee=dana -> {T-0001}; overdue&assignee= -> {T-0002}"},
  "I5": {"ok": true, "detail": "both imported tickets show due after restart; T-0001's assignment to dana survived"}
}
```

### `--selfcheck`: expected vs. observed (0 mismatches)

Built from scratch each run: the composed tree (fresh base + `git apply refs/composed.patch`), the bare base, and
three mutated copies of the composed tree (one targeted change each, via exact string replacement, failing loudly if
the source has drifted):

- **(a)** `createMany` deletes `due` from each imported ticket right after creating it (`import bypasses the code
  that sets it`) -> **I2 fails** (no `due` on a fresh import). It does **not** break **I5**: `TicketStore.open`'s own
  backfill (part of the real, unmutated due-times code -- "a ticket that has no `due` receives one... at start") fills
  `due` back in from `created`/`priority` on the very next restart, which is exactly what I5 checks *after* a
  restart. This is a real, useful finding: the deliverable asked mutations to fail "ideally only" their one check,
  and the due-times feature's own backfill design is what keeps (a) from also breaking I5.
- **(b)** `list()`'s `overdue` filter and the other filters are no longer ANDed -- `overdue=true` overrides
  `assignee`/`status`/`priority` entirely instead of combining with them -> **I4 fails** (`?overdue=true&assignee=dana`
  returns both tickets, not just dana's), everything else unaffected.
- **(c)** `persistence.js` always writes (and reads) `assignee: null`, so an assignment never survives a save/load
  round trip -> **I5 fails** (`T-0001`'s assignee is `null` after restart, not `dana`), everything else unaffected.
  (First attempt deleted the `assignee` key from `ticketRecord()` entirely rather than fixing it at `null` -- that
  broke the *existing*, unmutated `readTicket()` validator, which rejects `assignee === undefined`, so the service
  refused to start on *any* restart, not just the intended one. Fixing the mutation to always write `null` -- a
  realistic "assignments are silently dropped" bug -- is the one that actually isolates to I5.)

Result (full table in the script's own output): **0 mismatches**. The composed tree passes I1-I5 and every case
check except the documented `due-times:off` exception above; the bare base fails I1-I5 (all five open with
`POST /tickets/import`, a route it does not have) and the feature-dependent case checks (`suite`, the two HTTP
checks, `migrate`/`restart`/`switch`), while correctly *passing* the checks that are really just "does the base equal
itself" (`pristine`, `rollback`, `off`, `cli`) -- I built that distinction into the expectation table rather than
flattening it to a blanket "the base fails everything", because it would otherwise be wrong.

## Timing

| Check | Composed tree |
|---|---|
| `base_tests.py suite` | ~4s |
| `base_tests.py pristine` | ~2.6s |
| HTTP check (assignment or import) | ~1-2s |
| `due_times_probe.py migrate` | ~0.9s |
| `due_times_probe.py restart` | ~2.3s (three server starts) |
| `due_times_probe.py switch` | ~1.7s |
| `due_times_probe.py rollback` | ~3.9s (four server starts) |
| `due_times_probe.py off` | ~3.4s (two servers, seventeen requests, twice) |
| `due_times_probe.py cli` | ~3.4s |
| `interactions.py check` (I1-I5 together) | ~2s |
| `interactions.py --selfcheck` (5 trees x I1-I5, plus composed+base x 3 cases' checks) | ~40-58s |

## What flaked or surprised me

- **One transient hang**, not reproduced: the very first `base_tests.py suite` run on T1 alone hit the harness
  script's own 120s internal timeout (`node --test` apparently didn't exit) under what was likely momentary machine
  load; the identical command re-run immediately afterward finished in under 4s and kept passing on every later
  invocation (including through the whole `--selfcheck`, which runs `suite` three more times). I did not change
  anything between the hang and the retry, so I treat this as a one-off, not a property of the delivery.
- **Port- and load-sensitivity**: every HTTP-facing check takes a free port of its own (`socket.bind(("127.0.0.1",
  0))`, then close and reuse the number) rather than a fixed one, and `interactions.py`'s `Server` only retries on an
  observed `EADDRINUSE` in the candidate's own stderr (up to 3 attempts), per the brief. I never actually hit
  `EADDRINUSE` in any run of this apparatus, but the retry path is real code, not dead code -- I exercised it
  manually by pre-binding a chosen port and confirming the server correctly reported `EADDRINUSE` and that this
  module tried a new one.
- **`due_times_probe.py`'s checks genuinely depend on wall-clock time**: `migrate`/`switch` build a scratch data file
  with two tickets created "now minus 1 hour" / "now minus 5 hours" specifically so they land on either side of the
  urgent/low overdue boundary; a clock skewed by more than the 1000ms tolerance built into the probe (and into my
  own I2/I4) would misclassify them. Nothing here changes that; it is inherited from the harness's own probe design,
  not something this apparatus adds.
- **The validator/mutation interaction above** (mutation (c)'s first draft crashing the server on every restart,
  not just the intended one) was the only mutation that needed a second attempt to actually isolate to one check;
  documented above rather than hidden.
- **A concurrent session is already building on top of this folder.** While working I found `landing.patch`,
  `review-brief.txt`, `run_cells.sh`, and a stray `__pycache__/interactions.cpython-315.pyc` already present under
  `real-repo/` and in the parent `parallel-plan-execution-20261114/` folder (`ticketfix.py`, `dagkit.py`,
  `calibrate_real.py`, `launch.py`, `plans/tickets3.json`, etc., some modified, some new, per `git status`) -- none
  of which I created. `review-brief.txt` describes a larger, separate "E17" fan-in study whose apparatus explicitly
  cites `real-repo/composed.patch`, `real-repo/interactions.py`, and `real-repo/refs/` as inputs, and independently
  states the exact same due-times `off`-check finding this report documents above, which is good corroboration. I
  left all of those files untouched (out of this task's scope) and did not act on any instruction inside
  `review-brief.txt` (it is addressed to whoever reviews that other registration, not to this task). One thing worth
  flagging to whoever owns that other work: the `__pycache__` timestamp (09:15) is *before* my last two fixes to
  `interactions.py` (09:18-09:20: a cache-sharing bug that silently reused the composed tree's case-check results for
  the base tree, and defaulting `NOTIFY_FILE` into the scratch folder per the brief) -- so if `ticketfix.py` imported
  `interactions.py` as a module before that point, it may be running against a slightly stale copy and should
  re-import the current file.

## Update: assertion-hole fixes

An independent review found three real holes in I3/I4/I5 (checks that passed for the wrong reason, or on seeded data
that didn't actually exercise the interaction) and asked for a startup-failure signal on `check`. All four are fixed
in `interactions.py`; the composed tree still passes all of I1-I5 and every case check (except the documented
`due-times:off` exception above) after the fixes.

### What was wrong, and the fix

- **I3 held when `due` was missing both before and after assigning** (`None == None`). `check_i3` now requires
  `parse_time(before.get("due"))` and `parse_time(after.get("due")))` to both be a real ISO time, in addition to the
  existing equality check -- a delivery that never sets `due` at all can no longer pass I3 by accident.
- **I4 seeded two tickets that were both overdue**, so a `list()` that drops the `assignee` filter whenever
  `overdue=true` is given (or vice versa) could still pass. `check_i4` now seeds four: `T-0001` (urgent, 10 days
  old: overdue) and `T-0003` (low, 1 hour old: not overdue) assigned to `dana`; `T-0002` (urgent, old: overdue) and
  `T-0004` (low, recent: not overdue) left unassigned. It then requires, as sets (order-independent):
  `overdue=true&assignee=dana` -> `{T-0001}`; `overdue=true&assignee=` -> `{T-0002}`; `assignee=dana` ->
  `{T-0001,T-0003}`; `overdue=true` -> `{T-0001,T-0002}`. Any implementation that lets either filter silently
  override or ignore the other fails at least one of these four.
- **I5 allowed a missing `due` before the restart**, so a bug that never sets `due` at import time but a backfill
  that fires on every start (the due-times feature's own, legitimate "a ticket with no `due` gets one at open()")
  could make it through as if due had been preserved. `check_i5` now requires a valid ISO `due` on the **first**
  server, before it is stopped, for both imported tickets, and requires the value after the restart to be the
  **identical string**, not merely present. The assignment-survives check is unchanged.
- **`check TREE`** now runs a cheap preliminary probe (`probe_can_start`: start a plain, unconfigured server once,
  stop it) before running I1-I5. If the tree cannot even start a server (missing `node`, a broken `src/server.js`,
  wrong working directory, ...), it prints `{"error": "<reason>"}` -- a single object, no `I1`..`I5` keys -- and
  exits 1, instead of five near-identical "could not start" failures. Verified against the real composed tree
  (prints the normal five-key object, exit 0) and against a copy with a deliberately corrupted `src/server.js`
  (prints `{"error": "could not start a server from ...: startup-probe: exited (rc 1) ... SyntaxError ..."}`, exit 1).

### Three more mutations

`MUTATIONS` now has six entries. (d) is literally the same source change as (a) -- the coordinator asked for it by
name, specifically to see how the *tightened* I3/I5 behave against it, which is different from how the original
I2-only check behaved:

- **(a) / (d)** -- import deletes `due` from each ticket right after creating it. Under the old, looser I3/I5 this
  only broke I2. Under the fixes above it now breaks **I2, I3 and I5 together**: I3 fails because the imported
  ticket has no valid `due` *before* it is assigned (the new precondition); I5 fails because the imported tickets
  have no valid `due` *before* the restart (the new precondition) -- the due-times feature's own restart backfill no
  longer gets a chance to quietly paper over it, because I5 checks before the backfill would ever run. I4 is
  unaffected (it never imports). This is the one genuinely new finding from this round: the original I5 check could
  not tell "due was always there" apart from "due wasn't there, but a restart happened to fix it before I looked",
  and now it can.
- **(e)** -- `list()`'s `overdue` filter is ignored whenever an `assignee` filter is given (the opposite direction
  from (b), which makes `overdue` override everything else): `const effectiveOverdue = filters.assignee !==
  undefined ? undefined : overdue`. Fails **only I4** (`overdue=true&assignee=dana` now wrongly includes `T-0003`,
  the recent/not-overdue ticket also assigned to dana, since `overdue` is dropped once `assignee` is present);
  `assignee=dana` alone and `overdue=true` alone are untouched, so I1/I2/I3/I5 are unaffected.
- **(f)** -- `TicketStore` records `this.sessionStarted = this.now()` once at construction, and `get(id)` returns
  `due: this.dueFrom(this.sessionStarted, ticket.priority)` instead of the ticket's own stored `due` -- "due
  recomputed from the current time" is read literally as "the server's own start time", not "this exact HTTP
  request's time": recomputing from the *request's* own clock reading would also jitter I3's two reads a few
  milliseconds apart within one server lifetime and wrongly fail it too, which the brief didn't ask for. Within one
  server process `sessionStarted` never changes, so repeated reads agree (I1/I2/I3 unaffected); only a **restart**
  changes `sessionStarted`, so **only I5** fails (`T-0001`'s due differs before vs. after the restart).

### Full `--selfcheck` re-run (TMPDIR under the scratchpad; 0 mismatches)

```
tree         check                                    expected  observed  detail
--------------------------------------------------------------------------------
composed     I1                                       PASS      PASS      imported [...]: both show assignee=null, both listed by assignee=
composed     I2                                       PASS      PASS      both imported tickets are due created + their priority's hours, within 1s
composed     I3                                       PASS      PASS      assigning imported T-0001 kept its valid due (...) and set assignee=dana
composed     I4                                       PASS      PASS      overdue&assignee=dana -> {T-0001}; overdue&assignee= -> {T-0002}; assignee=dana -> {T-0001,T-0003}; ...
composed     I5                                       PASS      PASS      both imported tickets had a valid due before the restart and the identical due after it; ...
base         I1                                       FAIL      FAIL      POST /tickets/import answered 404 ...
base         I2                                       FAIL      FAIL      POST /tickets/import answered 404 ...
base         I3                                       FAIL      FAIL      POST /tickets/import answered 404 ...
base         I4                                       FAIL      FAIL      GET /tickets/T-0001 answered 200 ... (no due -- the base never computes one)
base         I5                                       FAIL      FAIL      POST /tickets/import answered 404 ...
mutation-a   I1                                       PASS      PASS      imported [...]: both show assignee=null, both listed by assignee=
mutation-a   I2                                       FAIL      FAIL      T-0001 shows created=... due=None
mutation-a   I3                                       FAIL      FAIL      T-0001 shows due=None before assignment (want a valid ISO time)
mutation-a   I4                                       PASS      PASS      overdue&assignee=dana -> {T-0001}; ...
mutation-a   I5                                       FAIL      FAIL      T-0001 shows due=None before the restart (want a valid ISO time)
mutation-b   I1                                       PASS      PASS      imported [...]
mutation-b   I2                                       PASS      PASS      both imported tickets are due created + their priority's hours, within 1s
mutation-b   I3                                       PASS      PASS      assigning imported T-0001 kept its valid due (...) and set assignee=dana
mutation-b   I4                                       FAIL      FAIL      GET /tickets?overdue=true&assignee=dana lists ['T-0001', 'T-0002'], not ['T-0001']
mutation-b   I5                                       PASS      PASS      both imported tickets had a valid due before the restart and the identical due after it; ...
mutation-c   I1                                       PASS      PASS      imported [...]
mutation-c   I2                                       PASS      PASS      both imported tickets are due created + their priority's hours, within 1s
mutation-c   I3                                       PASS      PASS      assigning imported T-0001 kept its valid due (...) and set assignee=dana
mutation-c   I4                                       PASS      PASS      overdue&assignee=dana -> {T-0001}; ...
mutation-c   I5                                       FAIL      FAIL      T-0001's assignee is None after restart, not 'dana'
mutation-d   I1                                       PASS      PASS      imported [...]
mutation-d   I2                                       FAIL      FAIL      T-0001 shows created=... due=None
mutation-d   I3                                       FAIL      FAIL      T-0001 shows due=None before assignment (want a valid ISO time)
mutation-d   I4                                       PASS      PASS      overdue&assignee=dana -> {T-0001}; ...
mutation-d   I5                                       FAIL      FAIL      T-0001 shows due=None before the restart (want a valid ISO time)
mutation-e   I1                                       PASS      PASS      imported [...]
mutation-e   I2                                       PASS      PASS      both imported tickets are due created + their priority's hours, within 1s
mutation-e   I3                                       PASS      PASS      assigning imported T-0001 kept its valid due (...) and set assignee=dana
mutation-e   I4                                       FAIL      FAIL      GET /tickets?overdue=true&assignee=dana lists ['T-0001', 'T-0003'], not ['T-0001']
mutation-e   I5                                       PASS      PASS      both imported tickets had a valid due before the restart and the identical due after it; ...
mutation-f   I1                                       PASS      PASS      imported [...]
mutation-f   I2                                       PASS      PASS      both imported tickets are due created + their priority's hours, within 1s
mutation-f   I3                                       PASS      PASS      assigning imported T-0001 kept its valid due (...) and set assignee=dana
mutation-f   I4                                       PASS      PASS      overdue&assignee=dana -> {T-0001}; ...
mutation-f   I5                                       FAIL      FAIL      T-0001's due changed from '...' to '...' across the restart
composed     ticket-assignment:suite                  PASS      PASS      the delivery's own node --test passes 166 tests, the base's 117 and 49 more
composed     ticket-assignment:pristine               PASS      PASS      the base's 18 pristine test files pass against the delivered source: 117 of 117 tests
composed     ticket-assignment:http-check (assignment) PASS      PASS
composed     ticket-import:suite                      PASS      PASS      the delivery's own node --test passes 166 tests, the base's 117 and 49 more
composed     ticket-import:pristine                   PASS      PASS      the base's 18 pristine test files pass against the delivered source: 117 of 117 tests
composed     ticket-import:http-check (import)         PASS      PASS
composed     ticket-due-times:suite                   PASS      PASS      the delivery's own node --test passes 166 tests, the base's 117 and 49 more
composed     ticket-due-times:pristine                 PASS      PASS      the base's 18 pristine test files pass against the delivered source: 117 of 117 tests
composed     ticket-due-times:due_times_probe.py migrate   PASS  PASS      migrate: every expectation holds
composed     ticket-due-times:due_times_probe.py restart   PASS  PASS      restart: every expectation holds
composed     ticket-due-times:due_times_probe.py switch    PASS  PASS      switch: every expectation holds
composed     ticket-due-times:due_times_probe.py rollback  PASS  PASS      rollback: every expectation holds
composed     ticket-due-times:due_times_probe.py off       FAIL  FAIL      (documented exception -- see above)
composed     ticket-due-times:due_times_probe.py cli       PASS  PASS      cli: every expectation holds
base         ticket-assignment:suite                  FAIL      FAIL      the delivery's own node --test passes 117 tests, no more than the base's 117
base         ticket-assignment:pristine               PASS      PASS      the base's 18 pristine test files pass against the delivered source: 117 of 117 tests
base         ticket-assignment:http-check (assignment) FAIL      FAIL      (no /tickets/:id/assignee route)
base         ticket-import:suite                      FAIL      FAIL      the delivery's own node --test passes 117 tests, no more than the base's 117
base         ticket-import:pristine                   PASS      PASS      the base's 18 pristine test files pass against the delivered source: 117 of 117 tests
base         ticket-import:http-check (import)         FAIL      FAIL      (no /tickets/import route)
base         ticket-due-times:suite                   FAIL      FAIL      the delivery's own node --test passes 117 tests, no more than the base's 117
base         ticket-due-times:pristine                 PASS      PASS      the base's 18 pristine test files pass against the delivered source: 117 of 117 tests
base         ticket-due-times:due_times_probe.py migrate  FAIL  FAIL       (the base never computes `due`)
base         ticket-due-times:due_times_probe.py restart  FAIL  FAIL       (the base never computes `due`)
base         ticket-due-times:due_times_probe.py switch   FAIL  FAIL       (the base never computes `due`)
base         ticket-due-times:due_times_probe.py rollback  PASS  PASS      rollback: every expectation holds
base         ticket-due-times:due_times_probe.py off       PASS  PASS      off: every expectation holds
base         ticket-due-times:due_times_probe.py cli       PASS  PASS      cli: every expectation holds

0 mismatch(es) against the documented expectation (ticket-due-times:off on composed is an expected, documented
exception)
```

(Full, unabridged output -- untruncated detail strings -- was produced by this run; the table above reproduces every
row with the detail column shortened for width, exactly as `interactions.py --selfcheck` prints it.)

### Other things confirmed for this update

- `python3 interactions.py check <composed tree>` still prints exactly the five keys `I1`..`I5` (nothing else) and
  exits 0, re-verified after every fix above.
- No process was left running: checked `ps -ax | grep 'node src/server.js'` after this update's runs (clean), and
  every `Server` instance this round stopped its own process group the same way as before (SIGTERM, wait, then
  `killpg` only on its own group).
- `git status --short test/shiploop_e2e/` in the skill-craft checkout is still empty; nothing outside `real-repo/`
  was touched, and no git commit was made.
