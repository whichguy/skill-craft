---
Status: measured 2026-10-31; exploratory. One reader (Claude Sonnet 5.5) classified the 25 texts; a second and a third reader replayed them on 2026-11-01 (superseding "no second reader has": [the replay](../follow-on-replay-20261101/README.md)); E2E cases only; no model was run for the peek itself and nothing in ShipLoop changed.
Consumer: the owner, deciding whether ShipLoop should surface a post-delivery follow-on run (docs/shiploop-follow-on-run-design-2026-10-31.md, sections 4, 5 and 10). Later: whoever runs the replay (design section 7, M1) and needs this base rate and this classification to compare a second reader against.
Journal: docs/shiploop-follow-on-run-journal.md (Round 0).
---

# What archived runs leave open at handoff — 2026-10-31

Owner, 2026-10-31 (dictated; the full text is in the design note, section 0): after a feature is built and deployed,
ShipLoop might reconsider what it learned, decide whether the feature or spec could improve, and re-enter the loop from
the top with an improvement prompt. Before designing a gate for that, this measurement reads what finished runs actually
leave open. Nothing in ShipLoop changes.

## 1. The answer

**No leftover in 122 finished runs was a gap the system could close without a person.** Of 125 archived runs, 122 reached
handoff. 45 of those (37%) have some text under `Open for the next run` in their release-verify lessons, and 25 (20%) have
real content once phrasings such as "None for this request" are dropped. Read in full, the 25 are:

| Class (one reader) | Rows | What it is |
|---|---:|---|
| person | 6 | a person must do or confirm something (a click-through, playing a game) |
| capability | 4 | a later run with a capability this run lacked (headed Chrome, a Lightning UI, a Windows host) could close it |
| extension | 4 | optional or conditional scope beyond what the request asks |
| debt | 1 | a small hygiene item inside the request's scope |
| note | 7 | knowledge for a later change; nothing is open |
| decision | 3 | a choice or an answer a person must give about the spec or scope before anything is built |
| gap | 0 | a request outcome or refuted assumption the system could close alone |

So a gate on "something is open" would fire on 20% to 37% of runs and find nothing the system can act on, while a gate on
classified leftovers would fire on 3 runs (2.5%; 2 to 4 if the four arguable rows of section 2 move) and route each to a
person. The outcome that closes a gap the run itself
notices already exists: `add-work`, accepted by every outer stage including handoff. It was used in 3 of 125 runs.

## 2. Method

`peek.py` finds the runs with `ledger.find_runs()` of `docs/experiments/coverage-ledger-20261031` (archived runs that
reached product-acceptance; test-fixture copies and seeded slices skipped) and reads each with ShipLoop's own readers:
`shiploop_store.read_record`, `shiploop_planning_revision.current_actions`, `shiploop_assumptions.open_items` and
`shiploop_unverified.current_list`. Per run it keeps whether handoff was accepted, the release-verify result's
`lessons.open_next` text, the open assumption rows, the unverified rows, and the counts of add-work and send-back outcomes in
the history. Two filters on the text, both reported: loose (not exactly "none") and strict (also not opening with a "none"
phrase: none, no known, no open, no other, no unfinished, nothing, n/a, no further, no remaining).

The strict rows were read in full and classified by hand into the seven classes of `classification.json`. Four rows are
marked arguable because a second reader could reasonably move them: row 3 (an audit that was not performed: extension, or
capability because it needs a browser), row 11 (a recorded default the owner may change: note, or decision), row 16 (a manual
screen-reader pass that also names a one-line README fix: person, or debt), row 22 (a delivery route the build revealed was
missing: decision, or extension). `summarize.py` refuses to print counts when `classification.json` no longer describes the
rows in `peek.json`, so a rerun on a grown run set cannot be counted against a stale classification.

## 3. Results

| Measure | Value |
|---|---|
| archived runs found (reached product-acceptance) / readable | 125 / 125 |
| reached handoff done | 122 |
| `Open for the next run` has text other than "none" (loose) | 45 (37% of 122) |
| ... and does not open with a "none" phrase (strict) | 25 (20%) |
| runs with an add-work in their history | 3 of 125 |
| runs with a send-back in their history | 30 of 125 |
| runs whose unverified list is non-empty at the end | 38 (47 rows; all 47 carry an owner, which the stage requires); 17 runs never listed it |
| runs ending with at least one open assumption row | 59 (121 rows, 44 with a person owner); not a signal, see section 5 |

The 25 strict rows (`*` marks an arguable row; the full text of each is in `peek.json`, the reader's note in `summary.txt`):

| # | Case (run folder) | Class | Text starts |
|---:|---|---|---|
| 1 | shiploop-salesforce-battleship-zbcb4i5d | person | Confirm rendering and click-through in an authenticated browser.… |
| 2 | battleship-candidate | extension | If promoting beyond this Developer Edition, add coverage for add… |
| 3 | development-01 | extension* | A full visual theme and viewport audit was not performed.… |
| 4 | gym-published-baseline-03 | extension | If responsive dark-theme support is required, validate those vie… |
| 5 | bs-sf-int-b7c77f | capability | A later run should open app SLBattle on tab SLBattle Board in he… |
| 6 | bs-release-update-436528 | person | A person still has to open App Launcher entry SL Battleship and … |
| 7 | chess-sf-full-12a23d | capability | A later run that can open Lightning app SLChess at path /lightni… |
| 8 | gate-290-b60ed7-claude-csv-report | decision | Ask the requester whether exponent notation and a leading '+' sh… |
| 9 | gate-290-b60ed7-codex-hello | note | No product follow-up is open. If a later change touches this scr… |
| 10 | battleship | debt | Retain the browser click-through as a BROWSER=1 test (currently … |
| 11 | battleship-scoring | note* | Ship names are a recorded default (the request named none); chan… |
| 12 | gate-2132-f7ba78-grok-hello | note | A later run inherits the two Commands and the three rollback rec… |
| 13 | battleship | capability | A later run with a runner that can activate a control and hold a… |
| 14 | battleship-scoring | person | SYS-CLICK stays with the local player at handoff: click one cell… |
| 15 | pilot-ollama-dsflash-993a9d-hello | note | If a later run changes the delivered files, it must start from `… |
| 16 | v2170-ds-battleship-759a03 | person* | Carry the manual consumer pass to the user: play the returned ga… |
| 17 | v2170-sonnet-battleship-491d9a | person | A5: a person opens http://localhost:3000/ after node server.js a… |
| 18 | v2180-sonnet-battleship-36036c | extension | Optional: a test for the page's fetch-failure message and dark c… |
| 19 | pa-ds-battleship-4ed4e3 | person | A person still has to play one game in a real browser from the r… |
| 20 | control-hello | note | The six kept files are uncommitted on main. A later run should t… |
| 21 | control-hello | note | If a later run wants a fast-forward, do not let plan-return comm… |
| 22 | bf-ds-ticket-assignment-09c33b | decision* | Whoever picks this up next should decide whether the ticket.assi… |
| 23 | bf-ds-ticket-escalation-09c33b | decision | At handoff: record the requesting user's answer to A1 (person-le… |
| 24 | hooks-after-ticket-escalation | note | No feature work remains; future service or fixture changes shoul… |
| 25 | pc-ds-hello-note-b45e87 | capability | Only A1 travels onward: a Windows host should confirm hello.py's… |

The three decisions are the closest thing in 122 runs to the owner's scenario, a missing enhancement or an open question the
build made visible:

- Row 8, csv-report: ask the requester whether exponent notation and a leading "+" count as numeric, and whether zero
  arguments should exit 1. A spec ambiguity.
- Row 22, ticket-assignment: decide whether the `ticket.assigned` line gets a real delivery route, and if so add it as a
  work item. An enhancement the build revealed.
- Row 23, ticket-escalation: record the requesting user's answer to assumption A1 (person-level delivery). An unresolved
  assumption.

All three wait for a person before anything is built. The four `capability` rows (5, 7, 13, 25) are also follow-on shaped,
but only a host that has the missing capability can close them, and a follow-on run started on the same host would stall in
the same place.

## 4. What this does and does not show

- It shows the base rate of a candidate gate on the archive: a raw "something is open" gate is noise, a classified one is rare.
- It does not show that the idea has no value. The E2E cases are small and mostly saturated: every completed brownfield run
  of the node-tickets and user-listing cases passes its held-out checks, the acceptance checks the run never sees (26 of 26,
  593b4b44cfc0a166e01fe3a61e301ba85833c8a8). So there is no room left to show a gain, and a completed run that is wrong, which
  is what a follow-on run exists to repair, is not in this corpus. The scenario in the owner's note (a substantial,
  exploratory feature that has not concluded) is under-represented here.
- `Open for the next run` is what the run chose to write. It cannot hold what the run did not know it missed, and the gaps a
  run does notice can be built in the same run through `add-work`. What is left is, by construction, what the run chose not
  to or could not close.

## 5. Limits and unknowns

- One reader, Claude Sonnet 5.5, who also wrote the design note that cites these numbers. A second, distinct reader, blind to
  these labels, was the first step of the design's replay (section 7, M1), done 2026-11-01 ([the replay](../follow-on-replay-20261101/README.md)):
  Sol twice and Grok kept the class of all four arguable rows and moved three others (F01, F18, F23); `gap` stayed 0 for every reader but one Sol run, on two rows that are not gaps. Moving the four arguable rows, each to the other
  class named in section 2, would give at most decision 2 to 4, extension 3 to 5, person 5 to 6, capability 4 to 5, debt 1 to 2
  and note 6 to 7; `gap` stays 0 unless a reader finds a system-closable row that this reader did not.
- The run set is `ledger.find_runs()`'s five roots (`~/e2e-runs`, `-brownfield`, `-qr`, `-x4`, `-owner-note`). The output roots
  of the experiments `-xr`, `-s7`, `-pf`, `-multipass` and `-brownfield-interrupted` are not read. The set grows as sessions finish runs, so
  a rerun can differ; this snapshot is 125 runs.
- The open-assumption count is not a signal: `shiploop_assumptions.open_items` never closes a plan row ("the ledger never
  updates a disposition"), so 59 runs end with an open row whether or not anything is left. The unverified count is not an
  autonomous signal either: product-acceptance requires an owner on every entry, and all 47 have one.
- Not joined to the held-out E2E checks, and not joined to the cost of the runs.
- The only two runs outside the E2E roots on this machine, under `~/src/.shiploop-runs`, were unfinished when listed (one at
  system-test, one at intake), so no finished run of the owner's own features was available. This was a one-time listing and
  is not reproducible from this directory.

## 6. Reproduce

```sh
python3 -B docs/experiments/follow-on-peek-20261031/peek.py --json docs/experiments/follow-on-peek-20261031/peek.json
python3 -B docs/experiments/follow-on-peek-20261031/summarize.py
```

The archives live outside the repository (`~/e2e-runs*` on the owner's machine), so the commands reproduce only there.
Files: `peek.py` (reads the archive), `peek.json` (rows, summary and the 25 strict texts), `output.txt` (peek.py's output),
`classification.json` (the hand classification, its class definitions and one note per row), `summarize.py` and
`summary.txt` (the counts, refused when the classification is stale).
