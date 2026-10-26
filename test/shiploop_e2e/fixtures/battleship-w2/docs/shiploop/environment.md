# Environment

As of 2026-10-18. Execution worktree `shiploop/run-7c67b8558d4bcbc3`. Product baseline is `7ac98a2e598d5ecf622846d3959154ceffc4158c` (empty tree `4b825dc642cb6eb9a060e54bf8d69288fbee4904`). HEAD is `efe1a9daf036d06eaf7bb80c107d0a9a12eae086` (`feat: W1 Rules module game.js`). That commit includes `game.js`, `test/rules.js`, and the knowledge home as it stood at verify. This carry-forward edits the knowledge home further and does not commit it. `server.js` is still absent. An earlier fact, before that commit, named HEAD `9cb3f03c7d165dcc22d72344b33c2e7eb92413e8` with those product files uncommitted. Source checkout `/Users/dadleet/e2e-runs/2026-10-18/battleship-1/work` on `main` stays at that empty baseline until the guarded return. Revalidate Node and the worktree HEAD before relying on these facts.

## Targets and runtimes

- **Edit and test (observed):** the isolated worktree above. `game.js` and `test/rules.js` are present. `server.js` is not. The source checkout stays at the empty baseline until the guarded return.
- **Runtime (observed):** Node.js `v25.9.0` (`node --version` in the worktree, 2026-10-18). Binding requirement from the request: a Node.js HTTP server with no npm dependencies, so only the standard library.
- **Prepared (2026-10-18):** the same Node, rechecked, exit 0. No `package.json`, no `.github`, and no install. The worktree is `shiploop/run-7c67b8558d4bcbc3` at `7bbc8cc3493f6fbb919fc1df7e51ef8f70113e04`. The source checkout is still `main` at `7ac98a2e` and clean. There is no workflow for a return to start. The guarded return stays at release or handoff. No database and no shared data. No linter is configured, so none was started.
- **Consumer (binding, from the request):** a person running `node server.js` locally. `PORT` selects the listen port; default `3000`. No remote host, account, CI workflow, or deploy config exists (no README, no `.github`, no package manifest).
- **Return route (observed):** ShipLoop copies the worktree delta back to the source checkout at release or handoff. That return does not start a server, run CI, or publish. Revalidate at release-plan.
- **Delivery (proposal):** local process only. The request names that server and grants no remote deploy.

## Commands

No linter, formatter, or type checker is configured. No npm script. On 2026-10-18, before any test file existed, `node --test` exited 0 and reported `tests 0` (`scratch/strategy-full.txt`). That run does not execute the named cases. After `test/rules.js` existed, the same command in this worktree exited 0 and reported tests 9, pass 9: `TC-5`, `TC-5 (a)`, `TC-7`, `TC-8`, `TC-8 (a)`, `TC-9`, `TC-9 (a)`, `TC-10`, and `TC-10 (a)`. HTTP cases are not in that run. `server.js` is still absent. A pass must print the case IDs. Exit 0 with tests 0 is not a pass.

Full suite. Includes every `TC-<number>` test under `test/`. Excludes the browser case `TC-B1`. Cost: seconds, local, no network. Prerequisite: Node, no install. Fixture: rules tests call `game.js` in process. HTTP tests other than TC-2 and TC-11 import `server.js` and call `start(0)`, then close the server. TC-2 and TC-11 spawn `node server.js` because they test the `PORT` environment variable. `PORT=0` is the R-2 failure case, not an ephemeral fixture. Expected IDs once written: TC-1, TC-2, TC-3, TC-4, TC-5, TC-6, TC-7, TC-8, TC-9, TC-10, TC-11, TC-12.

```
node --test
```

Runner start, not the suite. On 2026-10-18 `node --test --help` exited 0 and listed `--test` as "launch test runner on startup" (`scratch/prepare-runner.txt`). It executed no cases. No fixture process is required: rules tests call `game.js` in process, and HTTP tests other than the `PORT` spawns call `start(0)`. `TC-B1` still has no browser tool and is not part of this runner.

Smoke. One rules case, not evidence for the full suite. Same environment. `--test-name-pattern` is a regular expression. `TC-1` with no anchor also selects TC-10, TC-11, and TC-12, so the smoke pattern is anchored to the ID as its own word. Expected ID: TC-5. On 2026-10-18, before `test/` existed, this command exited 0 and reported `tests 0` (`scratch/strategy-smoke-anchored.txt`). After `test/rules.js` existed, the same command exited 0 and reported tests 2, pass 2: `TC-5` and `TC-5 (a)`.

```
node --test --test-name-pattern '^TC-5 '
```

Focused rules cases. Same environment as the full suite. The pattern is the verify rerun of the in-process IDs, each as its own word. On 2026-10-18, at HEAD `efe1a9daf036`, this command exited 0 and reported tests 9, pass 9, fail 0. A `NO_COLOR` and `FORCE_COLOR` warning from the runner is cosmetic.

```
node --test --test-reporter spec --test-name-pattern '^(TC-5|TC-7|TC-8|TC-9|TC-10) '
```

Server, once `server.js` exists. Not a test command.

```
node server.js
```

Browser case, opt-in, not part of the default suite. It needs a host browser tool. The 2026-10-18 probe found none. The anchored pattern exited 0 and reported `tests 0` (`scratch/strategy-browser-anchored.txt`). An earlier unanchored pattern did the same (`scratch/strategy-browser-pattern.txt`). Neither opens a page.

```
node --test --test-name-pattern '^TC-B1 '
```

## Skills

none. No `SHIPLOOP.md` skill index, no `AGENTS.md`, and no repository skill directory. Checked 2026-10-18 at `7ac98a2e`. Revalidate if a skill directory appears.

## Harnesses and suites

Harness: Node's built-in `node:test` and `node:assert/strict`, probed on Node v25.9.0 (`scratch/probe-http.txt`). No extra runner, coverage tool, or npm package. Fit: the request names `node --test`. The rules cases in `test/rules.js` passed on 2026-10-18 (`node --test`, tests 9). The focused command under ## Commands also exited 0 with tests 9, pass 9. HTTP cases remain planned because `server.js` is absent. Isolation: tests do not share a game. `PORT=0` is invalid under R-2, so a spawned `node server.js` is not how a test asks for an ephemeral port. HTTP tests other than the PORT cases import `server.js` and call `start(0)`. That call binds `127.0.0.1` to a port the operating system assigns, and the test closes the server. The file listens on import only when it is the main module. TC-2 is a single test that binds `3000` and `3456` one after another, then tries `1` and `65535` the same way, so a parallel test does not take those ports. Rules tests call `game.js` with a supplied placement or seed `1` and touch no socket. Setup: none beyond that start. Teardown: close the server or drop the in-process game. Revalidate if a test file starts using another runner.

Facility gap: none for rules and HTTP. Browser rendering is a host tool, not a library to install. Probe on 2026-10-18 found no browser tool (`scratch/browser-probe.txt`). Owner of that gap: the verify stage, and only for `TC-B1`. It does not block `node --test`.

Baseline consumed: `node --test` at `7ac98a2e` reported tests 0 (missing coverage, no existing implementation). There is no repair item. The rules cases are the current observation above, not that baseline. The expected RED for `TC-5` applied only before `game.js` existed. Observed 2026-10-18: `TC-5` passed.

Mapping. Rules rows TC-5, TC-7, TC-8, TC-9, and TC-10 passed on 2026-10-18. HTTP rows stay planned:

| ID | Proves | Surface | Due |
| --- | --- | --- | --- |
| TC-1 | R-1 no `npm install`; `GET /api/new` returns 200; `server.js` imports `./game.js` (the same file as TC-5) and no second placement or fire copy; other imports are `node:` built-ins | local HTTP via `start(0)` | test |
| TC-2 | R-2 `PORT=3456`, then unset `PORT` on 3000, each returns 200 and a `game` string; the id from the stopped 3456 process is 400 on the new process; `PORT=1` and `PORT=65535` do the same 200 or exit non-zero when the OS refuses the bind | spawned CLI, one sequential test | test |
| TC-11 | R-2 `PORT=abc`, empty `PORT`, and `PORT=0` each exit non-zero and do not accept a new game | spawned CLI | test |
| TC-3 | R-3 parse: 200 HTML, title exactly `Battleship`, 100 grid buttons with `data-row` and `data-col` covering 0 and 9, a non-grid control that requests `GET /api/new`, script `POST /api/fire` with `game`, `row`, and `col`, `Fleet sunk` on the `gameOver` path, distinct `miss`/`hit`/`sunk` style rules, no remote URL | local HTTP body | test |
| TC-12 | R-3 `GET /no-such-page` is 404 | local HTTP | test |
| TC-4 | R-4 two 200 JSON ids, different non-empty `game` strings, no ship name or coordinate list in the body or in stdout and stderr | local HTTP | test |
| TC-5 | R-5 and R-6 destroyer only on `(0,0)` and `(0,1)`: `(0,0)` hit and `gameOver` false, repeat hit and false, `(1,0)` miss and false, `(0,1)` sunk and true | in-process rules | test |
| TC-6 | R-5 first fire `(0,0)` is 200 with `gameOver` false; each cell `(0,0)` through `(9,9)` is 200 with `result` `miss`, `hit`, or `sunk`; the first response with `gameOver` true has `result` `sunk`; later shots keep `gameOver` true. The test does not read ship cells | local HTTP | test |
| TC-7 | R-5 400 `{"error":"<non-empty>"}` for bad JSON, unknown id, missing fields, non-integer `row`, and `row` or `col` of -1 or 10; occupied cells unchanged on the in-process game; repeat of `(0,0)` returns the first body; `GET /api/fire` and `POST /api/new` are 405 | HTTP status plus in-process read | test |
| TC-8 | R-7 seed `1` returns `{game, ships}`: carrier 5, battleship 4, cruiser 3, submarine 3, destroyer 2, each a straight in-bounds run, no shared cell; the same seed returns the same ships | in-process rules | test |
| TC-9 | R-7 carrier `(0,0)-(0,4)` and battleship `(0,0),(1,0)-(3,0)` overlap: `{error}`, no game id stored | in-process rules | test |
| TC-10 | R-7 destroyers `(0,0)-(0,1)` and `(1,0)-(1,1)` accepted; carrier row 0 columns 0 through 4 accepted; carrier row 0 columns 6 through 10 rejected | in-process rules | test |
| TC-B1 | R-3 player activates one cell and sees `miss`, `hit`, or `sunk` | browser, opt-in | verify |

Replay inputs. Rules calls use `game.js` and passed on 2026-10-18. HTTP calls stay planned: they use `start(0)` except TC-2 and TC-11, which spawn `node server.js`.

- TC-1. Do not run `npm install`. Call `start(0)`, `GET /api/new`, expect 200. Read `server.js` and `game.js` and fail if any import specifier does not start with `node:` or `./game.js`. `server.js` must import `./game.js`, the same file TC-5 imports, and must not define a second placement or fire implementation.
- TC-2. One test, steps in order. `PORT=3456 node server.js`, `GET http://127.0.0.1:3456/api/new`, expect 200 and a string `game`, then stop that process. Start with `env -u PORT node server.js`. `POST http://127.0.0.1:3000/api/fire` with the id from the stopped process and `row` 0, `col` 0 expects 400 and `{"error":"<non-empty>"}`, because that record died with the process. Then `GET http://127.0.0.1:3000/api/new` expects 200 and a string `game`, then stop. `PORT=1` and `PORT=65535`: expect that same 200 shape, or a non-zero exit when the bind fails. No other test binds 3000, 3456, 1, or 65535.
- TC-11. Three spawns: `PORT=abc`, `PORT=` (empty), and `PORT=0`. Each exits non-zero. A `GET /api/new` to that port is not accepted.
- TC-3. `GET /` returns 200 and `Content-Type` containing `text/html`. Parsed title equals `Battleship`. The grid is 100 buttons. Some grid button has `data-row="0"` and some has `data-row="9"`, and the same for `data-col`. A control that is not one of those grid buttons requests `GET /api/new`. The script text requests `GET /api/new` and `POST /api/fire` with the field names `game`, `row`, and `col`. The script contains `Fleet sunk` and, when `gameOver` is true, returns before `POST /api/fire`. The style text has three rules whose text includes `miss`, `hit`, and `sunk`, and those three declaration blocks are not the same string. The document contains no `http://` or `https://` URL. A title and 100 buttons with neither API call fails. Rendered color is not claimed here; TC-B1 is the rendered click, and it is unobserved.
- TC-12. `GET /no-such-page` returns 404.
- TC-4. Two `GET /api/new` calls. Each is 200, `Content-Type` contains `application/json`, and the body is an object whose only required field is a non-empty string `game`. The two strings differ. No value is an array of positions and no key or string is `carrier`, `battleship`, `cruiser`, `submarine`, or `destroyer`. The child process stdout and stderr for those calls also contain none of those names and no substring matching `[` + integer + `,` + integer + `]`.
- TC-5. `createGame` with one destroyer on `(0,0)` and `(0,1)` and no other ship. `fire` `(0,0)` expects `hit` and `gameOver` false. The same fire again expects `hit` and false. `fire` `(1,0)` expects `miss` and false. `fire` `(0,1)` expects `sunk` and true. A load-only test fails. Observed 2026-10-18: the titled test passed. `TC-5 (a)` also passed: after that sink, a repeat of `(0,0)` is `hit` and `gameOver` true, and the occupied cells stay `[[0,0],[0,1]]`.
- TC-6. `GET /api/new`, then `POST /api/fire` `{"game":"<id>","row":0,"col":0}`. Expect 200, `result` one of `miss`, `hit`, or `sunk`, and `gameOver` false. Then fire each cell from row 0 col 0 through row 9 col 9 once, in that order, including corners `(0,9)`, `(9,0)`, and `(9,9)`. Each response is 200 with `result` in that set. The test does not read ship cells. It finds the first response whose `gameOver` is true: that `result` is `sunk`, every earlier response in the sweep has `gameOver` false, and every later response has `gameOver` true.
- TC-7. Two surfaces, not one shared game. In process, `createGame` with the TC-5 destroyer, read `occupiedCells`, then call `fire` with each bad value below and expect `{error:"<non-empty>"}` and the same occupied cells. The bad values are row `1.5`, row `-1`, row `10`, col `-1`, and col `10`, plus a missing row or col on that game. On HTTP, against a live id from `GET /api/new`, each of these is 400 and `{"error":"<non-empty string>"}`: body `not-json`; `{"game":"missing","row":0,"col":0}`; `{}`; `{"game":"<id>"}`; `{"game":"<id>","row":0}`; `{"game":"<id>","col":0}`; `{"game":"<id>","row":1.5,"col":0}`; `{"game":"<id>","row":-1,"col":0}`; `{"game":"<id>","row":10,"col":0}`; `{"game":"<id>","row":0,"col":-1}`; `{"game":"<id>","row":0,"col":10}`. The HTTP call is not what the occupied-cell assertion observes. The server has no route that returns ship cells. Separately, fire `(0,0)` on a live HTTP game, fire it again, and expect the second JSON to equal the first. `GET /api/fire` and `POST /api/new` return 405. Observed 2026-10-18: the in-process half passed in `test/rules.js`. The HTTP half is not run, because `server.js` is absent.
- TC-8. `createGame({seed:1})` with no caller ships. The return is `{game, ships}`. `ships` has carrier with 5 cells, battleship with 4, cruiser with 3, submarine with 3, and destroyer with 2. Each `cells` list is a straight horizontal or vertical run, every coordinate is in 0..9, and no cell is shared. The union has 17 cells. A second call with seed `1` returns the same `ships`. Do not infer the runs from the union alone: ships may touch. Observed 2026-10-18: that test passed. `TC-8 (a)` also passed for seed `2`: the same five names and a second call with equal `ships`.
- TC-9. `createGame` with `{ships:[{name:"carrier", cells:[[0,0],[0,1],[0,2],[0,3],[0,4]]},{name:"battleship", cells:[[0,0],[1,0],[2,0],[3,0]]}]}`. The call returns `{error:"<non-empty>"}` and stores no game id. Observed 2026-10-18: that test passed. `TC-9 (a)` also passed for a share of `(0,2)` and for a destroyer whose two cells are both `(0,0)`.
- TC-10. Three placements. Destroyer `(0,0)-(0,1)` plus destroyer `(1,0)-(1,1)` is accepted. Carrier on row 0, columns 0 through 4, is accepted. Carrier on row 0, columns 6 through 10, is rejected. Observed 2026-10-18: that test passed. `TC-10 (a)` also passed for a carrier that uses row 10 and for a destroyer that uses column `-1`.
- TC-B1. Unreachable today: `server.js` does not exist, and the host has no browser tool. Procedure, when both exist: `node server.js` with `PORT=3456`, open `http://127.0.0.1:3456/`, read title `Battleship`, activate the button for row 0 column 0, read that cell. Expect `miss`, `hit`, or `sunk`. Opt-in only. It does not block `node --test`.

State checks sit inside those cases. Before TC-4, no id. After it, a record exists and a fire with that id is accepted. After an error in TC-7, the unfired occupied set is unchanged on the in-process game. After each failed spawn in TC-11, no game is served.

Non-functional: the dependency ban is TC-1 (no `npm install` before start, and only `node:` imports). Privacy is TC-4 (response body, stdout, and stderr contain no ship name or coordinate list). Latency, uptime, capacity, and an accessibility standard have no numeric check because the spec excludes them.

## ID convention

Each test title begins with its ID as its own word, for example `TC-5 destroyer sequence`. `node --test` prints that title. A title `TC-5a` would not count as `TC-5`. List the IDs already used, once `test/` exists, with:

```
node --test --test-reporter tap
```

That command lists IDs. It is not a second suite. On 2026-10-18, before `test/` existed, it exited 0 and printed `TAP version 13` and `1..0` (`scratch/strategy-tap.txt`). It listed no cases. The test files are the home of the IDs. `TC-B1` is excluded from the default run by not living in a file `node --test` loads, or by `test.skip` unless `BATTLESHIP_BROWSER=1`. Default `node --test` must pass without a browser. Focused runs anchor the pattern (`^TC-5 `) because an unanchored `TC-1` also matches TC-10, TC-11, and TC-12.

## Access and accounts

- **Discovery operator (observed):** this session, local filesystem read and write on the worktree and the source Git directory. No credential store was read.
- **Deployed runtime:** none. There is no deployed process.
- **End user (binding):** one anonymous browser player per game id. No login.
- **Remote accounts:** none. No standing delivery policy.
- **Access open items:** none. A non-mutating `git status` on `/Users/dadleet/e2e-runs/2026-10-18/battleship-1/work` on 2026-10-18 showed `## main` and a clean tree. The local server is the only consumer. No login, deploy credential, or browser account is required. Revalidate if a later stage names a remote target. Prepare rechecked the same checkout on 2026-10-18: still `main` at `7ac98a2e`, clean. The player needs no account to open `http://127.0.0.1:<port>/` once `server.js` exists.

## Platform facts

- **House style (observed):** no formatter or editor config. `game.js` uses CommonJS, early returns, and one-sentence errors that name the constraint and the received value. Commit `7ac98a2e` message is `Empty baseline for the first ShipLoop run`.
- **Canonical code and tests:** `game.js` and `test/rules.js` in the worktree. `server.js` is not written yet.
- **MCP and API contracts:** none in the repository. The request defines the future HTTP contract: `GET /`, `GET /api/new`, `POST /api/fire`.
- **Reusable libraries (probed 2026-10-18, Node v25.9.0):** `node:http` (`createServer`), `node:test`, `node:assert/strict`, and `node:crypto` (`randomUUID`). A scratch server on `127.0.0.1` port 0 accepted `GET /ping` (200 JSON) and `POST` JSON, and returned 400 for invalid JSON. Logs: run `scratch/probe-http.txt` and `scratch/probe-crypto.txt`. No npm package is available or allowed.
- **Runtime state (proposal):** one in-memory map of games inside the server process. It ends when the process exits. No database, cache, or queue.
- **Specs and quality policies:** none in the repository. No README, no `SHIPLOOP.md` before this discovery, no prior requirements.
