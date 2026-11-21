# Battleship: blind vs with-build test-writing sessions (activity, execution side, tolerance, own reports)

Sources. RUN = /Users/dadleet/e2e-runs/ratchet-parallel-20261121-6f54fb.
- blind: RUN/bs-blind (session record `sessions/01-tests-1-1/events.jsonl`, work folder `work/`). Its `run.json` says `tests_blind_from` = RUN/bs-loop, so spec.md and plan.md are the ones the with-build run produced.
- with-build: RUN/bs-loop (`sessions/04-tests-1-1/events.jsonl`, `work/`).
- `ratchet/spec.md` and `ratchet/plan.md` are byte-identical in both work folders (checked with diff).
- The two stage prompts (`prompt.txt`) differ only where expected: blind adds "the product is not in this folder", the adapter rule, the "Assumed" section, and "run against the starting project; new behaviour must fail". Both carry the sentence "A test checks only what its clause states, and must pass whichever reasonable answer a build took." So tolerance at the `Open:` points is the packet's own rule for both sessions.
- Counting script: `bs-session-activity-count.py` beside this file (adapted from the morning's `blind-session-activity-count.py`; its output was checked by hand per command with `dump.py`, also here). Nothing was run except those read-only scripts.

## Part 1: what each session ran

| session | seconds | shell cmds | own acceptance-test runs | of those showing a failing test | first acceptance run | product's own tests (`node --test` / `npm test`) | distinct product source files read | `search_replace` edits | output tokens |
|---|---|---|---|---|---|---|---|---|---|
| blind (bs-blind) | 988.8 | 22 | 3 (#14, #21, #22, each runs all 28 mapped commands) | 3 of 3 by hand (every item exited 1 with "no HTTP game became reachable" / "zero cases"); 0 by the literal `not ok`/`✖`/`# fail N` test because its runner prints exit statuses | #14 of 22 | 2 (#7, #19), both in a folder with no tests: 0 tests, exit 0 | 0 (no product existed; it read only ratchet/spec.md and plan.md, command #2) | 17 (plus 4 file-writing heredocs: #9, #10, #11, #20) | 45,571 (reasoning 20,390) |
| with-build (bs-loop) | 903.3 | 19 | 5 against the real product (#10 one item C-5; #11, #14, #17 all 28; #12 one item C-14). A sixth, #15, ran six items against mutated copies | 1 real (#11: C-14 timed out, `not ok`, literal match). #15: 5 of 6 mutants detected, 1 survived (C-17) | #10 of 19 (single item); first full run #11 | 2 real (#8, 6 tests pass; #18) plus #7, `node --test -C`, exit 9, ran no tests | 4 source files, all in one command (#3): game.js, server.js, index.html, test/game.test.js; plus README.md | 0 (it wrote files by heredoc and python edits) | 38,836 (reasoning 17,655) |

Gate results in `run.json` for context: bs-loop `after-build-1` pass, `cycle-1-first` 28 of 28 passing, `final` pass. bs-blind `cycle-1-first` and `final`: all 28 items failing, as expected (the folder has no product). Nothing in the blind folder shows its suite ever running against a product.

Notes on the table
- Acceptance run = a command that executes `node acceptance/...` or a runner over `ratchet/acceptance.json`. Not counted: `node --check`, heredoc writes that only create files, probe scripts. Blind #12 writes acceptance.json and then only runs `node --check`; blind #13 and #18 are driver/reporter checks (below). With-build #16 is a probe script (prints 8192 -> 200, 8193 -> 413, PORT=0), not the tests.
- Blind #14, #21, #22 are three variants of one runner: #14 runs all 28 commands six at a time and prints "exit 1, N named failures"; #21 and #22 assert each item failed for the right reason ("no HTTP game became reachable", "must use node:test", "actual cases"). The `ratchet/tests-1.md` claim "all 28 mapped commands printed their item IDs and exited 1" is verified by #22's final line "All 28 commands produced their expected named baseline failures."
- With-build #11's one failure was a 42-second timeout in `C-14 does not apply malformed or interrupted requests to a game` (`testTimeoutFailure`, "test timed out after 42000ms"); the next run (#14) passed all 28, after #12 reworked the browser-compile caching in support.cjs and C-14.

### What did the blind session run its tests AGAINST?

Against nothing. Its work folder held only `ratchet/spec.md` and `ratchet/plan.md` (command #3: `rg --files` lists those two; command #4 `git ls-files` lists the same two). Every acceptance run (#14, #21, #22) failed at the first step, "no HTTP game became reachable" (the server entry `server.js` does not exist), so none of the suite's later code (coordinate probe, id selectors, board probes, browser driving of the real page, proxy) ever executed against a product.

Did it write or generate a stand-in product? No server, no fake game, no copy of a product, anywhere (checked every command and all 17 `search_replace` targets: they are only `acceptance/*`). It did build two small throwaway fixtures to check its own machinery, both created with `mkdtemp` under `TMPDIR` (= RUN/bs-blind/tmp) and removed in a `finally`:
1. #13, a driver check of the WebKit browser helper: compiles `acceptance/webkit.m` with clang into a temp dir, loads a data URL and reads its title. Quote: `'data:text/html,<title>Driver check</title>'` -> output `{"id":2,"value":"Driver check"}`. No product page.
2. #18, a check of the reporter/instrumentation preload: writes a 1-line fake rules module and a 1-line `node:test` file into a temp dir. Quotes: `writeFileSync(rule + '.js', 'exports.makeRecord = () => ({ value: 7 }); exports.readRecord = record => record.value;\n')` and `writeFileSync(test, "require('node:test')('reports a leaf case', () => { const record = require('./record'); record.readRecord(record.makeRecord()); });\n")`. Output showed the instrument recording `rules-import`, `makeRecord` (creation) and `readRecord` (inputStates [1]). That is the only moment the C-22/C-23 instrumentation ran, and only on this ~90-byte stand-in.
Size: two files of one line each (about 90 and 150 bytes) plus a compiled helper binary. Left in the work folder: none. `RUN/bs-blind/tmp` is empty (`ls -laR`: total 0) and `git status` in the work folder (#20, #22) lists only `acceptance/`, `ratchet/acceptance.json`, `ratchet/tests-1.md`.
Two test-side stand-ins live inside the suite, unrun: (a) `browser()` in adapter.cjs starts an `http.createServer` proxy in front of the product; (b) `fakeShot()` in checks.cjs (C-7 line 205, C-10 line 298, C-11 lines 313 and 331) makes the proxy answer every `POST /api/fire` itself with a forged `{result, gameOver}` instead of forwarding to the product. So C-7, C-10 and C-11 exercise the page against forged replies only (creation is still forwarded). The with-build proxy (`observedBrowser`, support.cjs) forwards every reply and only drops one (C-11 lost-win case).

## Part 2: the execution side of each suite

### Line counts

| suite | file | lines | what it holds |
|---|---|---|---|
| blind | adapter.cjs | 481 | start/stop (`spawn node server.js`, env, free port, port capture), HTTP helpers, id/coordinate discovery, placement probe, rule-test runner, browser proxy, WebKit client, page inspection script |
| blind | instrument.cjs | 114 | `--require` preload: wraps `net.Server.listen` (port capture) and the rules module's exports (`game`) to observe calls |
| blind | reporter.cjs | 16 | `node --test` reporter that prints one JSON line per leaf test |
| blind | webkit.m | 76 | Objective-C WebKit driver (load URL, evaluate JS) |
| blind | checks.cjs | 743 | the 28 items: `check('C-n', ...)` blocks (523 lines) plus helpers (sweep, held-square play, completion regex, leak heuristics) |
| blind | total | 1,430 | |
| with-build | support.cjs | 349 | launch/stop, free port, clean checkout, id/coordinate discovery, sweep, WebKit client, page inspection script, forwarding proxy |
| with-build | listener.cjs | 50 | `--require` preload: port capture/remap, V8 coverage hook, seeded `Math.random`/`crypto.randomInt` |
| with-build | browser.swift | 58 | Swift WebKit driver |
| with-build | api.cjs | 345 | API-level scenarios (fleet, fresh, isolation, boundaries, bodies, water, hit, sink, damage, repeats, gameOver) |
| with-build | page.cjs | 206 | browser-level scenarios (grid, chooseSquare, concealment, feedback, play, lost win) |
| with-build | structure.cjs | 92 | V8-coverage tracing for C-22/C-23/U-4 |
| with-build | checks.cjs | 123 | the 28 items (89 lines inside `check()` blocks), thin wrappers over the three files above |
| with-build | total | 1,223 | |

Execution side against expectation side (rough: a file split, because with-build mixes driving and asserting inside api.cjs and page.cjs).
- Blind: execution = adapter.cjs + instrument.cjs + reporter.cjs + webkit.m = 687 lines (48%). Expectations = checks.cjs 743 lines (52%), of which 523 inside the `check()` blocks and 220 helpers (about 130 of those helper lines are driving/heuristics, e.g. `sweep`, `playWithHeldSquare`, `finishedText`, `leakedPlacement`, `feedback`). adapter.cjs alone is 481 lines (33.6% of all). Roughly 140 of adapter.cjs's lines are discovery/tolerance (`idSelectors`, `matchesGameId`, `coordinates`, `placement`) rather than start-up.
- With-build: execution = support.cjs + listener.cjs + browser.swift + structure.cjs plumbing = 549 lines (45%); scenarios/expectations = api.cjs + page.cjs + checks.cjs = 674 lines (55%). Its support.cjs is 349 lines (28.5%) and also carries discovery (`idCandidates`, `discover`, `inferStart`).

### Does anything outside the adapter start or configure the product?

Blind: no. Grep of spawn/`process.env`/PORT/`server.js`/`/api/`/`game.js` outside adapter.cjs: checks.cjs mentions PORT and `/api/new` only in item-description strings (lines 156, 165, 169-170, 350, 363, 374, 663); instrument.cjs reads only the test's own variables (`RATCHET_TRACE_FILE`, `RATCHET_CAPTURE_PORT`, `RATCHET_RULES_FILE`, lines 9-32); reporter.cjs and webkit.m name nothing of the product. Routes, `server.js`, `game`, PORT, port 3000 and the JSON request keys sit in adapter.cjs lines 13-25 and `server()`. JSON response names `result` and `gameOver` are read directly in checks.cjs (`outcome`, `completed`, lines 20-26), and `row`/`col`/`game` in the adapter's proxy.
With-build: mostly, but less cleanly. `/api/new` and `/api/fire` are in support.cjs; but api.cjs line 161 writes a raw `POST /api/fire HTTP/1.1` request, structure.cjs line 52 excludes `server.js` by name, listener.cjs line 9 uses `ACCEPTANCE_REMAP_PORT`, and checks.cjs lines 13/29/38 name PORT and 3000.

### Product-facing names, blind suite

"plan" = in ratchet/plan.md; "spec" = in ratchet/spec.md; "neither" = an assumption.

| name | where used | in |
|---|---|---|
| `server.js` run as `node server.js`, cwd = folder root | adapter.cjs:14, 118 | spec and plan |
| env `PORT`; default 3000; PORT unset | adapter.cjs:17-18, 110-113 | spec and plan |
| PORT=0 (OS-assigned) and PORT=65535 | checks.cjs C-2 second case (160-167) | plan (Nuances: ports 0 to 65535); not spec |
| `127.0.0.1` as the host to connect to | adapter.cjs:24, 69-71 | neither (assumes the server accepts IPv4 loopback) |
| `GET /`, `GET /api/new`, `POST /api/fire` | adapter.cjs:21 | spec and plan |
| request JSON keys `game`, `row`, `col` | adapter.cjs:157, 166-168 | spec and plan |
| response keys `result`, `gameOver`; values `miss`, `hit`, `sunk` | adapter.cjs:25; checks.cjs:20-26 | spec and plan |
| creation id field: tries `game`, `id`, `gameId`, any key ending `id`, any other key, then a bare JSON value | adapter.cjs `idSelectors` 211-221 | `game` is in the plan (C-13 row); the other shapes are neither (hedges; spec C-13 is `Open:`) |
| coordinates 0..9 (first), 1..10 (second) | adapter.cjs `coordinates` 243-258 | zero-based: plan (C-15 row); one-based: neither (hedge; spec C-15 is `Open:`) |
| rules module file `game` (`game.js`), loaded by relative `require` | adapter.cjs:15, 115; instrument.cjs:84-85 | plan (Approach: `game.js`); spec says only "a game-rules module" (C-22) |
| `test/` directory, `node --test` at the root, `node:test` | adapter.cjs:16, 312; checks.cjs C-23/C-24/U-4 | spec and plan |
| rules module state shape: public creation result with `board`, `grid`, `shipAt`, `squareToShip`, or any 100-element array / 10x10 / Map; `ships` Map/array with `id`; `shots`; cell values null, 0, -1, false, '', 'water', 'empty', '.', '~', or `shipId`/`shipIndex`/`ship`/`id` | instrument.cjs:39-57; adapter.cjs `placement` 260-297 | plan names "the returned board", "square-to-ship mapping", "map of prior shot results"; `board` is the only field the plan names; `grid`, `shipAt`, `squareToShip`, the cell encodings and id fields are neither |
| body limit 8192 / 8193 bytes | checks.cjs C-15 (475) | plan (8 KiB); not spec |
| page `Content-Type` `text/html`, `document.contentType` | checks.cjs:179, 181, 658 | plan (`text/html; charset=utf-8`); spec says "as HTML" |
| document title `Battleship` | checks.cjs:188, 673 | spec and plan |
| board = 10 rows x 10 columns of targets, found by layout | checks.cjs `gridDimensions`, C-6 | spec and plan |
| target elements: `button, [role="button"], input[type="button"]`, then `[role="gridcell"], td`, `[data-row][data-col]` / `[data-row][data-column]`, `canvas`; groups of 90 or more preferred | adapter.cjs `findTargets` 427-455 | `button` in plan ("100 labeled buttons"); the rest neither (hedges) |
| attributes read from targets: `aria-label`, `title`, `disabled`, `aria-disabled`, computed colours, `::before`/`::after` content | adapter.cjs `pageInspection` 457-476 | neither (generic; "labeled" is in the plan but no attribute named) |
| completion wording (`game over`, `you won`, `victory`, `congratulations`, `play again`, `fleet sunk/destroyed`, `all ships sunk` ...) | checks.cjs `finishedText` 122-131 | neither (plan says "persistent completion message", no words) |
| ship-reveal wording (`ship here`, `occupied by`, `unhit ship`, `battleship at` ...) and creation-response field names `board`, `grid`, `fleet`, `ships`, `placements`, `occupied`, `positions`, `locations`, `cells`, `squares` | checks.cjs C-9 (234-259) | neither |
| test-side only: `RATCHET_CAPTURE_PORT`, `RATCHET_RULES_FILE`, `RATCHET_TRACE_FILE`, `NODE_PATH` cleared | adapter.cjs, instrument.cjs | n/a (machinery) |

Names in neither spec nor plan (blind): host 127.0.0.1; creation-id shapes other than `game`; one-based coordinates; rules-state field names other than `board` and the cell encodings; target selectors other than `button`; accessibility attributes read; completion wording; ship-reveal wording; creation-leak field names.

### Product-facing names, with-build suite (shorter)

| name | in | note |
|---|---|---|
| `server.js`, PORT, 3000, `/`, `/api/new`, `/api/fire`, `game`/`row`/`col`, `result`/`gameOver`, `miss`/`hit`/`sunk`, title `Battleship`, `test/`, `node --test` | spec and plan | |
| id keys `game`, `id`, `gameId`, `game_id`, bare value, any nested value (support.cjs:148-160) | `game` plan; the rest neither | hedges |
| coordinate bases: probes [1,1] then [0,0], and walks down up to 11 steps (support.cjs:177, 197) | neither | hedge; the page's top-left click also fixes the base (page.cjs `topLeftShot`) |
| 8192 / 8193 bytes | plan (8 KiB); also build-1.md | |
| completion wording `winLanguage` (page.cjs:3); `fire|shoot|attack|new game|restart|reset|play again` control names (support.cjs:267) | neither | the built page says "Fleet sunk. You win!", which the regex matches, but the regex is generic |
| DOM names | none used | no `#grid`, `#status`, `data-result`, `aria-label` text, `#targets` from index.html appears in any acceptance file (grep of acceptance/*.cjs: only generic `button`, `[role=...]`, `td`, `aria-label`/`title`). The only DOM name is its own `window.__battleshipTargets` |
| `crypto.randomInt` and `Math.random` patched by `ACCEPTANCE_SEED` (listener.cjs:29-49) | neither; `randomInt` appears only in game.js line 1 (`const { randomInt } = require('node:crypto')`) | the one place that could only have come from the built product (the session read game.js in command #3, before writing listener.cjs in #6). Not certain it was taken from there: the comment says "common placement randomness". Every seeded comparison is guarded by a `comparable` check (api.cjs:202, 218, 87, 150, 180, 190) so on a build that ignores the hooks the checks skip rather than fail |
| the module file names: not named; V8 coverage over any file other than `server.js` and `test/` (structure.cjs:52) | `server.js` spec | no `game.js` anywhere in with-build's tests |

## Part 3: tolerance

Reading rule. "Accepts more than one" = the suite has code that lets two or more distinct product behaviours pass. Each row: the blind place, what it accepts, the with-build place and quote, and the comparison ("equal" = both accept the same set; "with-build wider" = with-build tolerates more, so blind is stricter there; "blind wider" = blind is looser). Line numbers are of the files as left in the work folders.

| # | blind: file and check | blind accepts | with-build at the same point (quote) | comparison |
|---|---|---|---|---|
| 1 | adapter.cjs `coordinates` 246 (`for (const [origin, edge] of [[0, 0], [1, rows]])`) with `boardSquares(origin)`; used by C-7, C-8, C-12 to C-22, U-3 | origin 0 or origin 1 (two bases; first one whose corner shot returns a result) | support.cjs `discover` 177 `const pairs = [[1, 1], [0, 0]];` and `inferStart` 197 `for (let step = 1; step <= 11; step++)`; the page's own top-left click as a third source | with-build wider (any base within 11 steps; blind only 0 or 1) |
| 2 | adapter.cjs `idSelectors` 211-221 (`known = ['game','id','gameId', ...]`, then every other field, then `identity`); used by `coordinates`, `newGame`, C-13 | id as `game`, `id`, `gameId`, any `*id` key, any other key, or the whole JSON as a bare id | support.cjs `idCandidates` 148-160 `for (const key of ['game','id','gameId','game_id'])`, `add(value)`, `descend(value)` (every nested value) | with-build wider (nested values, `game_id`) |
| 3 | adapter.cjs `unknownId` 231-236 (C-14) | for a number id, a large number; for object/array/string ids, a forged one of the same type | api.cjs `unknownId` 70-75 same four types | equal |
| 4 | checks.cjs U-2 688 `assert.ok(matchesGameId(creation.response.json, shot.game))` with adapter.cjs `matchesGameId` 223 | the browser's submitted id may equal any selector shape of the creation JSON | none: page.cjs never compares the id the page sends with the one it received | blind stricter (with-build asserts nothing here) |
| 5 | adapter.cjs `isShot` 227; checks.cjs `outcome`/`completed` 20-26 | any HTTP status; only `json.result` in {miss, hit, sunk} (no status checked anywhere on /api/fire) | support.cjs:14 `const isShot = value => value && results.has(value.result);` | equal |
| 6 | checks.cjs C-20 570-595 (`sequential and overlapping repeats`) | any answer to a repeat shot (hit/miss/sunk replay, an error, a refusal); asserts only no added damage and no premature completion | api.cjs `repeated` 280-305: `assertFleetCanBeSunk(...)`, `assert.deepEqual(after.slice(1), shots.slice(1))` only for later distinct shots | equal |
| 7 | checks.cjs C-21 614-619 (shots after completion) | refusal (any status or body) or a result; if a result, `gameOver` must be true | api.cjs 321 `if (isShot(reply)) assert.equal(reply.gameOver, true, ...)` | equal |
| 8 | checks.cjs C-14 382-421 (`isDeepStrictEqual(other.id, target.id)`, `if (isShot(otherShot) ...)`) and restart case 406-421 | an earlier id may stay playable or be retired; an unknown id may get any answer; after restart an old id may be refused or reused | api.cjs `isolation` 77-127 (`if (JSON.stringify(first.game) !== JSON.stringify(second.game))`, `if (JSON.stringify(current.game) !== JSON.stringify(second.game))`) | equal |
| 9 | checks.cjs C-15 (third case) 475-488 (8192 and 8193 bytes: `if (reply.ok && isShot(reply)) {...} else {...}`) | accepted-and-counted, or refused-and-not-applied, at either length | api.cjs `invalidBodies` 182-194 `if (baseline.comparable && !isShot(reply.json))` | equal |
| 10 | checks.cjs C-16 491-514, C-17 516-531, C-18 533-546, C-19 548-568; instrument.cjs `snapshot` 39-57 and adapter.cjs `placement` 260-297 | two modes. If the module's creation result exposes a board (10x10 array, 100-element array, or Map with `r,c` or index keys, many cell encodings), exact assertions on ship squares. If not, HTTP sweeps with weak assertions: C-17 528 `if (completed(shots.at(-1)?.reply) && outcome(shots.at(-1).reply) !== 'sunk') { assert.ok(shots.some(... 'hit')) }`; C-19 567 `if (hadHit) assert.ok(shots.some(... 'sunk'))`; C-16 and C-18 similar. Also accepts fleets of 1-square ships (C-20 589-593, C-8 223) | with-build never reads module state: api.cjs `hit` 215-242 asserts `... ?.result, 'hit'` on a located multi-square-ship candidate, `water` asserts `'miss'` on a located water square, `sink` asserts `final.result === 'sunk'`; but each starts `if (!comparable) return;` (api.cjs 202, 218) or `if (!candidate) return;` (239) so on a build that ignores its seed hooks they skip | blind wider only in fallback mode (C-16 to C-19 become almost vacuous when the board is not recognised); strict and exact when it is recognised |
| 11 | checks.cjs C-22 622-635, C-23 637-645, U-4 724-738; instrument.cjs `wrapCall` 59-77 and `Module._load` 79-113 | rules module may export a function or an object of functions; creation = a call with no args or whose result has `board`/`grid`; resolution = any call taking an earlier creation result as an argument. Requires: module file `game(.js)`, loaded by CJS `require` with a relative path, a state object passed between calls | structure.cjs `rulesModules` 33-55 and `coverageMap` 10-31: any non-`server.js`, non-`test/` file whose functions ran on both /api/new and /api/fire (V8 coverage); `assertRuleCoverage` 69-81 needs a `node:test` file under `test/` covering the same function ranges. No file name, no export shape, works for ESM too | with-build wider (blind is tied to `game.js` from the plan and to CJS and an object-state API; a build that named the module differently, used `import`, or kept state in a closure would fail C-22/C-23/U-4 in blind) |
| 12 | adapter.cjs `findTargets` 427-455 (selector priority list; group of 90 or more preferred; falls back to the first non-empty group; trims to the 100-sibling group) | buttons, role=button, input[button]; gridcell/td; `[data-row][data-col]`; canvas. No separate Fire control | support.cjs `inspectPage` 264-293 (buttons, role=button/gridcell, td, input[button], `a`; excludes `fire|shoot|attack|new game|restart|reset|play again`; largest same-size group) and page.cjs `click` 54-59 (selects a target, then clicks a visible `Fire/Shoot/Attack` control if no request went out) | mixed: blind adds canvas and data-attributes; with-build adds `a` and the select-then-Fire flow, which blind cannot drive |
| 13 | checks.cjs `finishedText` 122-131 (eight alternatives); C-11 316-322 also asserts a new round and a mid-fleet sink do not already read as complete | any of about 25 completion phrases | page.cjs:3 `winLanguage` (one regex, about 15 phrases) | equal in kind (both unspecified wording); about the same breadth |
| 14 | checks.cjs C-11 second case 325-347 | completion visible right after the lost reply; or the same target re-enabled within 750 ms; or reload, fire again and see completion (forged reply `fakeShot('sunk', true)`) | page.cjs `play` 175-194: if no retry is offered, or the recovery reply is not `gameOver`, it reopens the page and `return`s with no assertion | blind stricter (blind still asserts completion after reload-and-fire; with-build passes with nothing asserted) |
| 15 | checks.cjs C-10 294-307 (`marks[0]` vs `marks[1]` via `feedback`) and `outcomeAppeared` 110-113 | any visible difference between a water and a ship shot (text, aria-label, tooltip, any of six computed styles, new text lines) | page.cjs `feedback` 138-144, `changed` 33-38 | equal; blind feeds forged `miss` then `hit` replies (checks.cjs:298), with-build real ones |
| 16 | adapter.cjs `server` 105-131 with instrument.cjs 14-30 (C-2 160-167, C-3 169-173); `preferredPort` | `listen(port)`, `listen('3000')`, or `listen({port})` forms (it normalises by `Number(requested)`); additionally requires PORT=65535 and PORT=0 to be passed through | listener.cjs 6-17 `const requested = Number(typeof first === 'object' && first !== null ? first.port : first)`; checks.cjs:13 `assert.equal(app.requested, 3000, ...)`; no 65535 or 0 test | equal for 3000; blind stricter overall (extra port cases) |
| 17 | checks.cjs C-9 234-275 `leakedPlacement` and the ship-reveal regex | many creation-leak field names and label wordings are detected | page.cjs 105-122 `concealment` (field list `board`, `fleet`, `ships`, `placements`, `shipPositions`; regex `unhit ship|unfired ship|enemy ship|occupied`) | equal in kind; blind's list is longer |

Count: 17 places where the blind suite accepts more than one answer or shape. Against with-build at the same point:
- equal acceptance: 3, 5, 6, 7, 8, 9, 13, 15, 17 (9 places; row 16 is equal for port 3000);
- with-build accepts more (blind stricter or narrower): 1, 2, 11 (3 places); with-build asserts less or nothing: 4, 14 (2 places; blind stricter); row 16 (blind has extra port cases) and row 12 (mixed) make 2 more with no clear direction;
- blind accepts more (looser): 10 only, and only in its fallback mode.
So the blind suite is not systematically looser than the with-build suite. Both suites are written to the same packet rule and tolerate the same open points (id shape, coordinate base, repeat, after-game-over, retired ids, body limit, fleet). The with-build suite is itself black-box and discovery-driven (it never pins a coordinate base, an id field, a status code or a repeat response); the one place it is strict where the blind suite could not be is the seeded differential check on this specific build, which silently skips when seeds are not honoured.

Five most consequential differences, in order
1. Row 10 (checks.cjs C-16/C-17/C-18/C-19): the only place blind is looser. If the build's creation result is not recognised as a board by `placement()`/`snapshot()`, C-17 and C-19 reduce to "if a hit happened some sunk happened", which a build that mislabels hits as sunk could pass; with-build's `hit()` asserts `'hit'` directly. (the built game.js `createGame()` returns `{board, remaining, afloat, shots}` with `board` a 10x10 array of null or ship index 0 to 4, which `snapshot` finds through `state.board`, so on this build blind should run in exact mode; not confirmed, I did not run it.)
2. Row 11 (C-22, C-23, U-4): blind is stricter and could false-fail a correct build: it needs module file `game`, CJS `require` with a relative path in both server.js and the tests, and the rules creation result passed back as an argument. With-build's V8 coverage has none of these couplings.
3. Rows 1 and 2 (coordinate base, id field): both suites tolerate; with-build tolerates more (any base within 11 steps, nested id values). Blind fails at a base other than 0 or 1, or an id that is not a top-level field or the bare JSON.
4. Row 14 (C-11 lost winning response): with-build passes without asserting anything if the page offers no retry; blind still requires completion to show after reload and a second shot.
5. Row 12 (page controls): blind cannot drive a page that needs a select-then-Fire flow, with-build can; blind can drive a canvas or `data-row` grid, with-build cannot. Also (note, not in the count) C-7, C-10 and C-11 in blind run the page against forged replies `{result, gameOver}`, so they pin the reply shape the page reads; with-build uses the real replies.

## Part 4: the sessions' own reports

### Blind: ratchet/tests-1.md, `## On the starting project`

```
## On the starting project

- Existing clauses whose tests fail: none. The specification has no clauses sourced from existing behavior.
- Other clauses whose tests pass: none. All 28 mapped commands printed their item IDs and exited 1. C-1 through C-22 and U-1 through U-3 reported the missing HTTP game. C-23 reported missing game-rule coverage. C-24 and U-4 reported zero discovered cases under `test/`.
```
Check: matches the run (blind #14, #21, #22). Note the starting project is empty, so every item fails for the reason "no product", not for a reason that says anything about the clause.

### Blind: `## Assumed`, each line labelled

```
## Assumed

- The browser driver uses the macOS host's WebKit and Clang. It locates the plan's board controls by their rendered positions and recognizes common completion cues in visible text.
- The rules module probes recognize public creation results that expose a board as a square array, flat array, or map using common empty-cell and ship identifiers. Other layouts use HTTP sweeps, which give less precise evidence about individual ships.
- The adapter tries the plan's zero-based API coordinates first and also recognizes conventional one-based integer coordinates. It probes the planned JSON id field, other named fields, and a bare JSON id.
```
1. "WebKit and Clang" part: execution (how tests drive a browser on this host). "Board controls by rendered positions" and "common completion cues in visible text": design gap, because the plan says "100 labeled buttons" and "a persistent completion message" but gives no selector, label text or completion wording.
2. Rules-module probes: design gap, because the plan names no export names and only the phrase "the returned board" for the state shape; the instrument has to guess function and field names. (Also execution: the instrumentation mechanism itself.)
3. Coordinates and id probes: execution (a hedge, not a gap). The plan does give both answers (`{ "game": "<opaque string>" }`, zero-based 0 through 9) and the spec marks both `Open:`, so the session tests for other reasonable answers by the packet's rule.

### Blind: `## Discoveries` (not asked, one line, for completeness)

`- An incomplete shot request leaves the round unchanged even if the bytes received so far form valid JSON | Observable: ... | Why: A server can parse a complete JSON value before the HTTP request has finished.` Label: design gap (the plan has the sentence in Nuances: "If the connection closes or errors before a complete body arrives, discard it"; the spec has no clause).

### With-build: ratchet/tests-1.md (the stage asks for `## Failing now` and `## Discoveries`; it has no `## Assumed` and no `## On the starting project`)

```
## Failing now

none
```
(Run #17 confirms: all 28 commands pass on the build; its own failing run #11 was a timeout of C-14 that it fixed in #12.)

```
## Discoveries

- A shot request body can be padded to 8,192 bytes. The server refuses the same request at 8,193 bytes without applying the shot. | Observable: Pad valid shot JSON with whitespace and compare the two responses, then fire legally at the same square. | Why: The plan mentioned a body limit, but the specification gives no size or boundary.
- A shot sent in a request that disconnects before its declared body ends does not advance play, even when the bytes already received form valid JSON. | Observable: Send valid shot JSON with a larger Content-Length, close the connection, then compare the round with a control. | Why: A server that acts on the first parseable JSON value could apply a shot before the HTTP request is complete.
- The HTTP interface exposes no independent evidence of which occupied squares belong to the same ship. | Observable: Every occupied square reported as sunk is consistent with a fleet of one-square ships. | Why: A temporary test build that mislabeled every non-final hit as sunk passed C-17 because the open fleet composition also permits the same public responses.
```
Labels: line 1 design gap (body limit is in the plan but not the spec); line 2 design gap (the plan's Nuances mention it, the spec has no clause); line 3 design gap in the spec, tied to the open fleet composition (C-8 `Open:`): HTTP cannot tell one-square ships from longer ones. It matches the mutation probe: with-build #15 left C-17's mutant (`result = 'hit'` -> `'sunk'`) surviving.

## What I could not determine

- Whether the blind suite passes on the finished product: it was never run against any product in these folders and I was told not to run products or tests. Rows 10 and 11 in particular (whether `placement()` and the instrument recognise `{board, remaining, afloat, shots}` and a CJS `require('../game')` in `test/game.test.js`) are readings of the code against build-1.md and game.js, not observations.
- Whether the with-build session took `crypto.randomInt` from game.js or guessed it (see the names table).
- Whether blind's 17 `search_replace` edits changed behaviour of tolerance code, only the final files are counted; the intermediate adapter had 462 lines and the final 481 (command #15 `wc -l`).
- "Product source files read" for with-build counts game.js, server.js, index.html, test/game.test.js from one `cat` command; whether it also read parts again via the editor tool is not visible (the `search_replace` tool was not used; there is no read tool in the event stream).
