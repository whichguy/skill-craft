# Test changes after first write: census from records (read-only)

Two instruments, because ShipLoop commits a whole step (implement, test, document) at once, so git cannot see a test edited inside the `test` stage:

- **Table A, git-visible later modifications.** A test file's first-adding commit, then every later commit touching it, on the delivery branch (`git -C <work> log --follow`, `git show`). Diffs saved in `diffs/NN.txt` (same folder; numbers in the "diff" column).
- **Table B, recorded in-stage test changes.** The `test` stage's own notes, `<delivery>/.shiploop-runs/*/run/notes/<action>.md`, which `shiploop_loops.py` tells the run to write ("write each test change's independent reason"). Self-reported by the run; I did not check them against the transcript. Only deliveries with the post-Oct-26 stage structure (test-spec, implement, test) have this record (trace.jsonl). The 22 older deliveries (Oct 3 to Oct 18, Oct 6-16 runs) have no trace and no stage notes: their tests were written in the same work item as the code (first test commit == the code commit "feat: W1 ..."), so they do NOT follow the spec-then-code-then-test order and say nothing about the owner's question; they are in Table A only.

Labels: additive / execution / assertion / mixed. `?` = I am unsure of the label. "cosmetic" = a rename of a test title only; counted under execution (neither assertion nor additive) and flagged.

Case kinds: NEW APP = Battleship/Checkers (a page, a server, rules). SMALL = ticket-* (existing 1.4.0 service, base tests untouched in all 11 deliveries: no base test file was modified in any ticket delivery).

## Deliveries taken

New apps (31 delivery branches; the scoring-probe `run-d7a01...` is a follow-up "add scoring" change to the probe app, so a change to an existing app; its sibling `run-1f24...` is the same branch as battleship-probe, counted once). Paths under /Users/dadleet/e2e-runs/. Structure: OLD = no stage record; NEW = test-spec/implement/test stages.

| # | path | model | structure | commits |
|---|---|---|---|---|
| 1 | 2026-10-18/battleship-1 | grok-4.7 | OLD | 23 |
| 2 | 2026-11-03/narrative-battleship | gpt-6.1-terra | NEW | 13 |
| 3 | 2026-11-04/m2-checkers | gpt-6.1-terra | NEW | 14 |
| 4 | 20261003/v1161-battleship-luna | gpt-6-luna | OLD | 39 |
| 5 | 20261006/v1220-battleship-grok-medium-none | grok-4.7 | OLD | 23 |
| 6 | 20261006/v1220-battleship-sonnet | sonnet-5.5 | OLD | 18 |
| 7 | 20261007/v1230-battleship-grok-none | grok-4.7 | OLD | 25 |
| 8 | 20261007/v1230-battleship-sonnet | sonnet-5.5 | OLD | 17 |
| 9 | 20261008/r1-battleship-grok-none | grok-4.7 | OLD | 14 |
| 10 | 20261008/r1-battleship-sonnet | sonnet-5.5 | OLD | 15 |
| 11 | 20261008/r1-checkers-sonnet | sonnet-5.5 | OLD | 13 |
| 12 | 20261008/r2-battleship-grok-none | grok-4.7 | OLD | 30 |
| 13 | 20261008/r2-battleship-sonnet | sonnet-5.5 | OLD | 13 |
| 14 | 20261008/r2-checkers-sonnet | sonnet-5.5 | OLD | 18 |
| 15 | 20261008/r3-battleship-sonnet | sonnet-5.5 | OLD | 15 |
| 16 | 20261008/r3-checkers-sonnet | sonnet-5.5 | OLD | 15 |
| 17 | 20261010/battleship-1 | sonnet-5.5 | OLD | 16 |
| 18 | 20261010/checkers-1 | sonnet-5.5 | OLD | 13 |
| 19 | 20261010/checkers-1270-sonnet | sonnet-5.5 | OLD | 10 |
| 20 | 20261010/checkers-8stage-88d412e9 | sonnet-5.5 | OLD | 20 |
| 21 | 20261010/checkers-sections-1ac83089 | sonnet-5.5 | OLD | 19 |
| 22 | 20261010/pc1i-checkers-sonnet | sonnet-5.5 | OLD | 14 |
| 23 | 20261011/battleship-probe-28191c5b | sonnet-5.5 | OLD | 14 |
| 24 | 20261011/battleship-scoring-probe-28191c5b (run-d7a0, follow-up scoring change) | sonnet-5.5 | OLD | 27 |
| 25 | 20261016/battleship-e2eaudit-4dd3b4b4 | sonnet-5.5 | OLD | 16 |
| 26 | 20261026/ds-flash-978478-battleship | deepseek-v4.1-flash | NEW | 57 |
| 27 | 20261026/live-sonnet-battleship-01b9b3 | sonnet-5.5 | NEW | 21 |
| 28 | 20261027/v2170-ds-battleship-759a03 | deepseek-v4.1-flash | NEW | 63 |
| 29 | 20261027/v2170-sonnet-battleship-491d9a | sonnet-5.5 | NEW | 18 |
| 30 | 20261027/v2180-sonnet-battleship-36036c | sonnet-5.5 | NEW | 23 |
| 31 | 20261028/pa-ds-battleship-4ed4e3 | deepseek-v4.1-flash | NEW | 55 |

Left out: delivery branches without server.js or without a test file (battleship-luna, v1200, v1210 x2, r3-battleship-grok-none, battleship-1270-sonnet, haiku55, live-2160, ...), Salesforce variants, and `ratchet-*`.

Small changes (ticket-*; /Users/dadleet/e2e-runs-sdlc*/; "pass" is the E2E scorer's flag, not completion; all 11 ran the full stage sequence):

| # | path | model/effort | commits | new test files |
|---|---|---|---|---|
| T1 | sdlc12/20261121/sonnet-medium-due | sonnet-5.5 medium | 13 | 7 |
| T2 | sdlc11/20261121/ticket-assignment-sol-high | sol high | 12 | 2 |
| T3 | sdlc10/20261120/grok-46-xhigh-due-1 | grok-4.6 xhigh | 16 | 5 |
| T4 | sdlc10/20261121-paired/sol-high-due-p2 | sol high | 15 | 2 |
| T5 | sdlc10/20261121-paired/sol-high-due-p1 | sol high | 13 | 2 |
| T6 | sdlc10/20261121-paired/sol-medium-due-p1 | sol medium | 11 | 1 |
| T7 | sdlc10/20261121-paired/sol-medium-due-p2 | sol medium | 9 | 1 |
| T8 | sdlc9/20261120/sonnet-high-due-S-1 | sonnet-5.5 high | 24 | 7 |
| T9 | sdlc9/20261120/sonnet-high-due-L-1 | sonnet-5.5 high | 20 | 12 |
| T10 | sdlc8/20261120/ticket-assignment-sol-medium | sol medium | 11 | 2 |
| T11 | sdlc10/20261120/sol-high-due-4 | sol high | 13 | 2 |

(sdlc12 sonnet-high-due has no result yet: left out. Remaining ~50 ticket deliveries from sdlc4-7, 9-10 and e1/e2 stopped after planning or are rehearsals: left out.)

## Table A: git-visible later modifications of a test file (first-add commit given)

Columns: delivery, case kind, mod commit, test file (first-add commit), label, evidence, recorded reason, diff file. "Product code existed at first add": for every OLD new-app row the first-add commit is the code's own commit (test written together with, not after, the code); for NEW rows the first-add is the step commit after the implement and test stages.

| delivery | kind | commit | file (first add) | label | evidence | recorded reason | diff |
|---|---|---|---|---|---|---|---|
| #4 v1161-luna | NEW APP | 0960166 | test/http.test.js (1c58c85) | execution (cosmetic) ? | one test title renamed to `FIXTURE-VALIDATION-16: ...`; no assertion touched | none found | 01 |
| #4 | NEW APP | 0960166 | test/rules.test.js | additive | new cases inside existing tests: `random: () => 0`, `1-EPSILON`, NaN, corner shots, shot after victory; no old expected value changed | none found | 02 |
| #4 | NEW APP | 0960166 | test/server-startup.test.js | additive | PORT=1 and 65535 loop appended to SYS-PORT-09 | none found | 03 |
| #5 v1220-grok-medium | NEW APP | 1dde1a6 | scripts/system-browser.test.js (e3efb49) | execution (cosmetic) ? | TC-15 title "pending" -> "in-flight mark"; body unchanged | none found | 04 |
| #6 v1220-sonnet | NEW APP | d6910c8 | test/server.test.js (d7b380f) | additive | TC-16 appended (malformed request target gets 400); same commit fixes server crash | none found | 05 |
| #12 r2-grok | NEW APP | 953c694 | system/browser-check.js (0272a6d) | execution | `fs.existsSync(chromePath)` guard added to main() | none found | 06 |
| #12 | NEW APP | f367a66 | system/browser-check.js | execution | wait for Chrome exit before rmSync of its profile; retry options | none found | 07 |
| #12 | NEW APP | a0a5b5c | system/browser-check.js | execution | loop variable `last` removed, `answer` const | none found | 08 |
| #12 | NEW APP | 926cb83 | test/http.test.js (57ff874) | additive | two asserts added to the page test (`The fleet is sunk.`, `aria-label`); commit also fixes product | none found | 09 |
| #17 battleship-1 | NEW APP | 6bbe02f | test/system.test.js (41b6d66) | additive | ST-1 appended | none found | 10 |
| #21 checkers-sections | NEW APP | bd3648e | test/server.test.js (0253ece) | additive | one assert `a.id === a.game` added to TC-3; commit "Expose the game id as both game and id" changes product | none found | 11 |
| #22 pc1i-checkers | NEW APP | aaafcc8 | test/server.test.js (62029ae) | additive | TC-13 appended (malformed URL gets 400); same commit fixes crash | none found | 12 |
| #24 scoring-probe (follow-up feature) | NEW APP follow-up | 9f461f8 | test/game.test.js (b8fbbb7) | assertion | TC-2/TC-3 expected `{result,gameOver}` -> `{result,gameOver,shots,hits}`; plus TC-13, TC-15 appended. Cause: the new scoring request, not a first-draft error | none found (commit subject only) | 13 |
| #24 | NEW APP follow-up | 9f461f8 | test/server.test.js | assertion | TC-11 allowed key list `['result','gameOver','ship']` -> adds `'shots','hits'`; TC-14, TC-16 appended | none found | 14 |
| #24 | NEW APP follow-up | 1f04563 | test/system.test.js (5f50199) | additive | ST-3 appended | none found | 15 |
| #26 ds-flash | NEW APP | 6c0bda3 | test/api.test.js (7accb97) | additive | W3 page cases C-R2-1, C-R2-3 appended + helpers (planned by the W3 test spec) | W3 note: see Table B | 16 |
| #26 | NEW APP | e65e401 | test/system.test.js (503deba) | execution | `exitWithin()` timeout wrapper around child exit wait | none found | 17 |
| #31 pa-ds | NEW APP | 5c7838c | test/rules.test.js (2925e93) | additive | new test T-1 (a) (refused random source names the value); commit is an Improve fix of product | none found | 18 |
| #31 | NEW APP | a2e0713 | test/system.test.js (6b9f992) | additive | ST-4 README needles added (`Battleship listening on port`, `falls back to 3000`), two new asserts, header comment | none found | 19 |
| T6 sol-medium-p1 | SMALL | 19defd5 | test/due-times.test.js (d25c3bd) | additive | S2 appends +71 lines (overdue/CLI) to the S1 file | none (notes: "Strengthened TC-2 assertions") | 20 |
| T3 grok-46 | SMALL | 81b43b7 | test/due-config.test.js (4e796ba) | additive ? | TC-5 (a) retitled and also checks 0 (8761 kept); assertion message only changed | note nav-c08d..: "TC-5 (a): ... 8761" (Table B) | 21 |
| T3 | SMALL | 81b43b7 | test/due-persistence.test.js | additive | +36 lines | see Table B | 22 |
| T3 | SMALL | 81b43b7 | test/due-store.test.js | additive | +9 lines (list default page of 20) | see Table B | 23 |
| T3 | SMALL | 81b43b7 | test/due.test.js | additive | +18 lines | see Table B | 24 |
| T3 | SMALL | 6cd7c1d | test/due-system.test.js (8f79298) | additive ? | SYS-5 appended; SYS-4 title "open tickets" -> "open and in_progress tickets"; header comment | none found | 25 |
| T8 sonnet-S-1 | SMALL | f645d47 | test/due-api.test.js (8b18f9d) | additive | S1 left the file as a header stub; S2 adds C8/C9 (+190), 2 comment/import lines replaced | S1 note: "header only" | 26 |
| T8 | SMALL | 53a3347 | test/due-api.test.js | additive | +132 overdue cases | none | 27 |
| T8 | SMALL | f645d47 | test/due-file.test.js | additive | +93, import and header comment lines replaced | none | 28 |
| T8 | SMALL | 53a3347 | test/due-store.test.js | additive | +45 | none | 29 |
| T8 | SMALL | 53a3347 | test/due.test.js | additive | +26 | none | 30 |
| T9 sonnet-L-1 | SMALL | fe67e1e | test/due-api.test.js (d8d20e8) | additive | +167 | none | 31 |
| T9 | SMALL | fe67e1e | test/due-cli.test.js | additive | +46 | none | 32 |
| T9 | SMALL | fe67e1e | test/due-store.test.js | additive | +30 | none | 33 |
| T9 | SMALL | fe67e1e | test/due.test.js | additive | +18, one import line extended with `isOverdue` | none | 34 |
| T9 | SMALL | e700cd0 | test/due-rollback.test.js (4f01b6e) | execution | snapshot loader and `folder`/`release140` helpers moved out to `test/release-140.js` (-18 +1) | none | 35 |

Table A totals (a "modification" = one commit touching one test file after its first add; OLD runs have almost no stage record, so reasons are "none found"):

| kind | deliveries | test files | later modifications | additive | execution | assertion | mixed |
|---|---|---|---|---|---|---|---|
| NEW APP, all 31 | 31 | ~100 | 19 | 11 | 6 (2 cosmetic?) | 2 (both in the scoring follow-up, a new request) | 0 |
| NEW APP, 8 NEW-structure only (rows 16, 17, 18, 19) | 8 | ~27 | 4 | 3 | 1 | 0 | 0 |
| SMALL (11) | 11 | 45 (base tests: 18 per delivery, none modified) | 16 | 15 | 1 | 0 | 0 |


## Table B: test changes recorded in the `test` stage notes (after the first write, before the step commit)

One row per recorded item. Source: `<delivery>/.shiploop-runs/<run>/run/notes/<action>.md`. "Reason" is the run's own sentence.

| delivery | kind | note file (action id prefix) | item | label | recorded reason (quoted or close paraphrase) |
|---|---|---|---|---|---|
| #2 narrative-battleship | NEW APP | nav-f34bb3ec | port and client behaviour tests added | additive | "No tests changed to pass ... Added port and client behavior tests independently to cover validation" |
| #2 | NEW APP | nav-f34bb3ec | TC_3 (c) added (PORT=0 starts) | additive | "an invalid-port-only check cannot distinguish Node rejection from app rejection" |
| #2 | NEW APP | nav-32f2a9d2 | status-feedback assertion added to existing client fixture | additive | "no product mutation or test weakening" |
| #3 m2-checkers | NEW APP | nav-808fcced | DOM fixture added after mutation testing | additive | "client selection and turn handling were unobserved" |
| #26 ds-flash | NEW APP | nav-915d60a6 (W2) | test-support/server.js returns `child` | execution | reason 2: C-R6-2 oracle needs exitCode on the child handle |
| #26 | NEW APP | nav-915d60a6 | test-support/server.js removes env entries set to undefined | execution | reason 3: the unset-PORT case must not inherit a PORT |
| #26 | NEW APP | nav-915d60a6 | C-R4-1, C-R4-8 redraw a fresh game until the sweep can observe what the oracle names | execution ? | reason 4: "Not a weakening: both oracles require a state a single random fleet may not have" |
| #26 | NEW APP | nav-262f6444 (W3) | statusText capture bound and asserted to be a string before the error scan | additive | "the case must not be able to pass without the status text it inspects ... does not change the required behaviour" |
| #28 v2170-ds | NEW APP | nav-97e8dc9f (W2) | TC_WALK ladder: compared ships-remaining on every cell to [5,4,3,2,1,0] -> three checks (first reports 5; distinct values 5..0; sunk shots 4..0) | assertion | "R-5 makes shipsRemaining fall only on a sunk shot ... the expected sequence was the test's error, not the product's" |
| #28 | NEW APP | nav-97e8dc9f | TC_ERROR_TABLE (b) added `messageBody()` to undo chunked framing | execution | "JSON.parse read the chunk-size line as the body" |
| #28 | NEW APP | nav-92bb1ecb (W3) | `idle()` wait before each sweep click removed (page keeps aria-busy on a finished board) | execution | "timed out after 8000 ms waiting for the board to be ready" |
| #28 | NEW APP | nav-92bb1ecb | suite `before` hook: skip on any launch error -> skip only when Chrome is not installed, rethrow else | assertion ? | "skipping it hid a dead client" (mutation survivor `waitFor >` -> `<=`) |
| #28 | NEW APP | nav-92bb1ecb | TC_BROWSER_FIRE asserts click `detail === 1` | additive | mutation `clickCount 1 -> 2` survived |
| #28 | NEW APP | nav-92bb1ecb | TC_BROWSER_WIN sweep also stops when the count reaches 0; post-win refusal observed by clicking an unfired square, not the winning square | assertion ? | "the stop condition was incomplete, not strict; the case now proves strictly more" |
| #29 v2170-sonnet | NEW APP | nav-bb3c5100 | TC_2 shot count 17 -> 18 | assertion | "spec R-4 sequence is 1 opening miss plus 17 ship cells = 18 shots ... the test-spec text '17 times' was a counting slip" |
| #29 | NEW APP | nav-bb3c5100 | TC_10 require scan: no longer demands at least one require() in game.js (guard kept for server.js) | assertion | "spec R-1 forbids external dependencies, it does not demand imports" |
| #29 | NEW APP | nav-bb3c5100 | TC_1 (b), TC_3 TypeError asserts added (mutation survivors) | additive | "add assertions from spec R-5, none weakened" |
| #31 pa-ds | NEW APP | nav-bf7b8132 (W1) | T-3 (a) fifth ship moved from column 4 to column 5 (spec fixture overlapped ship one) | assertion (fixture value) | "the fixture must be a legal fleet for the rule being observed" |
| #31 | NEW APP | nav-bf7b8132 | T-1, T-5: "the remaining 83 cells refuse after game over" -> all 100 cells refuse | assertion | "Asserting 83 would assert the walk's stop position instead of the rule" |
| #31 | NEW APP | nav-bf7b8132 | T-4: first row-major cell "returns miss" -> re-fire the first cell that is a miss, (0,5) | assertion | "(0,0) is a ship cell of KNOWN_LAYOUT ... the parenthetical in the spec contradicts the spec's own fixture" |
| #31 | NEW APP | nav-64e862c6 (W2) | T-19 `playToGameOver` skips cells the case already fired | execution | "The walk's precondition is a fresh game, which T-19 does not have" |
| #27, #30 | NEW APP | nav-d66e483b, nav-b54b16d7 | none recorded (live-sonnet says "Test changes made to pass a run: none"; v2180 note is a command list only) | - | - |
| T1 sonnet-medium | SMALL | nav-a7a2e054 | DUE-6 (c) hung racing server shutdown -> uses `withService` | execution | "two first-draft tests failed for their own reasons" |
| T1 | SMALL | nav-a7a2e054 | DUE-6 (d) asserted no file after `stop()`; `stop()` always saves -> inspects directory while service runs | assertion | same sentence: expectation was wrong |
| T3 grok-46 | SMALL | nav-c08d68b3 | TC-21 also asserts `store.get('T-0001').due` | additive | "red-check showed TC-21 passing on 1.4.0 ... a file-only read is not RED" |
| T3 | SMALL | nav-c08d68b3 | TC-5 (a) 8760 accepted / 8761 refused for every DUE_HOURS_* | additive | mutation `config.js:49` survived |
| T3 | SMALL | nav-c08d68b3 | TC-29 (a) default page of 20 of 21 | additive | mutation `store.js:92` 20->21 survived |
| T3 | SMALL | nav-c08d68b3 | ECONNRESET in TC-7 once: re-ran, edited nothing | (none) | "Not recorded as a change-to-pass" |
| T4 sol-high-p2 | SMALL | nav-25ce4bac | assert status 200 and malformed-due fixture added | additive | mutation review |
| T4 | SMALL | nav-494742fc | TC-4 asserts the full CLI header with DUE added | additive | "No original tests were changed" |
| T5 sol-high-p1 | SMALL | nav-56d04da9 | TC-4 also checks the direct parser call ignores overdue | additive | first mutation pass |
| T6 sol-medium-p1 | SMALL | nav-5e2f7152 | TC-2 strengthened: HTTP 200, store default, updated/title columns | additive | "independent compatibility contracts" |
| T7 sol-medium-p2 | SMALL | nav-1a26c81f | assertions for omitted app flag and migration exit status; logging default via real HTTP request | additive (2 items) | "Existing tests unchanged" |
| T8 sonnet-S-1 | SMALL | nav-9fe3e01b (W2) | store-level C15 A5.3: expected `['T-0001','T-0002']` -> `[]` for filters {priority:'low'} + overdue | assertion | "the spec's rule (overdue narrows what the filters find ...) gives [], which is the oracle now" |
| T8 | SMALL | nav-bf49e975 (S2) | C11 (a) title corrected | execution (cosmetic) | "title was corrected to say what the test checks" |
| T8 | SMALL | nav-bf49e975, nav-9fe3e01b | C8 A4.1 status 200, C9 (b)(c), C15 (a) added | additive (2 items) | mutation survivors; "the oracles are the request's own 'answers exactly as today'" |
| T9 sonnet-L-1 | SMALL | nav-9c4279d7 (S1) | DUE-38 expected table padding widths re-derived from src/format.js | assertion | "the failure was in the test ... The product was not changed for it" |
| T9 | SMALL | nav-ec425c87 (S2) | DUE-32 `overdue=true&overdue=x` (expected refused) -> `overdue=TRUE` | assertion | "The expectation was an invention of the draft, not a requirement" |
| T9 | SMALL | nav-5daa83d4 (W2) | DUE-44 call count 16 -> 15 and the indexes of the 404/400 answers | assertion | "my arithmetic error, not a product defect" |
| T9 | SMALL | nav-9c4279d7, nav-ec425c87 | DUE-32 (a)(b), DUE-27/33 status asserts, DUE-39 (a)(b) added | additive (2 items) | mutation survivors / not_covered |
| T11 sol-high-4 | SMALL | nav-8cbe31dc | HTTP suite hung once: connections now close per request via the existing client | execution | "hung once in a temporary unmutated copy" |
| T11 | SMALL | nav-3b981638, nav-8cbe31dc | explicit boundary/default/header assertions added | additive (2 items) | "specified behaviors that previously lacked focused assertions" |
| T2, T10 | SMALL | none readable | T2 has no per-action notes file for its test actions; T10's notes are command logs only | not determinable / none recorded | - |

Table B totals (items, by label):

| kind | deliveries with a readable note | items | additive | execution | assertion | mixed | deliveries with >= 1 assertion change |
|---|---|---|---|---|---|---|---|
| NEW APP (8 NEW-structure) | 6 of 8 (live-sonnet and v2180 record none) | 21 (rows 1-21) | 7 | 6 | 8 | 0 | 3 of 8 (v2170-ds, v2170-sonnet, pa-ds) |
| SMALL (11) | 9 of 11 | 23 | 15 | 3 (1 cosmetic) | 5 | 0 | 3 of 11 (all Claude Sonnet: T1, T8, T9) |

Models behind the 13 assertion changes: DeepSeek-flash 6 (v2170-ds 3, pa-ds 3), Sonnet 5.5 7 (v2170-sonnet 2, T1 1, T8 1, T9 3); none from Sol (5 ticket deliveries with notes), Grok-4.6 (1) or Terra (2).

## Unsure labels / caveats
- Titles-only renames (Table A rows 1, 4; Table B T8 C11(a)) are neither execution nor assertion; counted under execution, flagged cosmetic.
- Table B rows marked `?`: #26 C-R4-1/C-R4-8 redraw (could be assertion-neutral fixture), #28 skip-vs-rethrow (tightening; could be called additive) and #28 sweep stop condition (mixed timing + what is checked).
- Table B is self-reported by the run; not checked against the transcript or against the final test file. Changes made inside the `test` stage after a test was first written but before the step commit appear only in Table B. A run may also have left out a change.
- In the OLD (Oct) runs the test was written in the same commit as the code; there is no `test` stage and no notes, so the "after code" order cannot be checked there.
- The ticket delivery `ticket-assignment-sol-high` (T2): git shows zero later modifications; its stage notes were not found.
