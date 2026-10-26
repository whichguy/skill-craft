# Architecture

How the Battleship game is built. What it must do is `spec.md`. Runtime versions and commands are `environment.md`.

## Stack

Node.js standard library only. HTTP is `node:http`. Tests are `node:test` and `node:assert/strict`. Game ids are `node:crypto` `randomUUID`. No framework and no npm package, because R-1 forbids them. Observed on Node v25.9.0 (`scratch/probe-http.txt`, `scratch/probe-crypto.txt`).

## Structure

- `server.js` owns the listen socket, routing, JSON parsing, and the HTML response. It calls the rules module for a new game and a shot. It calls `listen` only when it is the main module. Imported, it exports `start(port)`, which binds `127.0.0.1` and returns the server. Tests pass `0` so the operating system assigns the port. The CLI reads `PORT` and never treats `0` as that request: `PORT=0` exits non-zero (R-2).
- `game.js` owns placement and shot resolution. The server imports it. Tests import the same file. The client cannot pass a placement.
- The HTML page is a string `server.js` sends for `GET /`. No second static server and no asset pipeline.
- Module format: CommonJS. There is no `package.json`. `server.js`, `game.js`, and `test/*.js` use `require`. `server.js` uses `node:…` or `./game.js`. A file in `test/` uses `node:…` or `../game.js`. Probed with `require('node:http')` and a sibling file (`scratch/probe-cjs.txt`, exit 0), and from a nested file (`.shiploop-improve/.experiments/nav-f1d3df93f69f4c68b21fa25b1153775f/nav-9f56f5c26826429fa01037c60c995cdf/probe-parent-require.txt`, exit 0): `require('./game.js')` there is `MODULE_NOT_FOUND`, and `require('../game.js')` loads the parent module.
- Names: both modules sit at the worktree root. Tests sit in `test/`. Nothing else is added. No package prefix. `server.js` names the rules module `./game.js`. A file in `test/` names it `../game.js`. Both specifiers are that one file. `require('./game.js')` from `test/` would be `test/game.js`, which is not the rules module.
- Data, one local process: a `Map` from game id string to `{ships, fired cells}`. No schema file, no migration, no disk, no second store. Ship cells are not a response field and are not logged. The map ends when the process exits. Practical bound is process memory; the spec sets no numeric quota.

## Conventions

No existing house style. New code uses the Node built-ins above, CommonJS `require`, early returns for bad input, and no logging of ship coordinates. Tests live in `test/` and use `node:test`. Titles start with the ID from `environment.md`. `server.js` loads `require('./game.js')`. A file in `test/` loads `require('../game.js')`. `require('./game.js')` from `test/` would look for `test/game.js`, which is not the rules module.

## Interfaces and boundaries

- `GET /` returns the HTML page.
- `GET /api/new` returns `{"game":"<id>"}`.
- `POST /api/fire` with `{"game","row","col"}` returns `{"result","gameOver"}` or `{"error"}`.
- `start(port)` on `server.js` binds `127.0.0.1` to `port` and returns the `node:http` server. Port `0` means the operating system assigns one. The test reads `server.address().port`. The CLI path is the only reader of `PORT`, and it rejects `0`.
- `createGame({ships})` stores a caller placement. `ships` is a list of `{name, cells}`. `cells` is a list of `[row, col]` pairs. The TC-5 input is `{ships:[{name:"destroyer", cells:[[0,0],[0,1]]}]}`. The HTTP routes do not expose this form. A smaller fleet is allowed only here (R-6). Success returns `{game, ships}` with the stored ships. Overlap or a cell outside 0..9 returns `{error:"<non-empty>"}` and stores no id.
- `createGame({seed})` with no `ships` places the five-ship fleet and returns `{game, ships}`. Each ship is `{name, cells}`. The names and lengths are carrier 5, battleship 4, cruiser 3, submarine 3, and destroyer 2. Seed `1` is the replay value for TC-8. The same seed returns the same `ships`. A cell set alone is not the oracle: ships may touch, so a union of cells does not prove the runs. The server calls this form with its own seed, never accepts ships from the client, and its HTTP body is only `{game}`.
- `fire(game, row, col)` returns `{result, gameOver}` for a legal shot. An illegal shot returns `{error:"<non-empty>"}` and does not change occupied cells or `gameOver`. `occupiedCells(game)` returns the occupied coordinates for an in-process assertion. No HTTP route returns that set.
- State: a `Map` from game id to the game, inside the one process. It is not written to disk. There is no cache, queue, or second service. A shot is finished when the HTTP response is sent.

## Real-boundary checks

All product checks are local. There is no deployed target. A local pass is the only pass. No remote framework, install, or registration.

- Rules cases `TC-5`, `TC-7`, `TC-8`, `TC-9`, and `TC-10`, plus their `(a)` sub-cases, passed in this worktree on 2026-10-18 (`node --test`, tests 9). HTTP cases `TC-1` through `TC-4`, `TC-6`, `TC-11`, and `TC-12` stay planned: `server.js` does not exist. Target for those: `127.0.0.1` through `start(0)`, or a spawned CLI for the `PORT` cases. `PORT=0` is not the ephemeral target.
- Cache, async recovery, and remote reconciliation do not apply. One process, one response.
- `TC-B1` browser procedure, planned, opt-in, not in the default suite. Actor: the player. Start: `PORT=3456 node server.js` already listening, which today cannot be started because `server.js` does not exist. Entry: open `http://127.0.0.1:3456/`. Initial state: the page has requested a new game. Steps: read the document title `Battleship`; activate the button for row 0 column 0; read that cell. Expect the cell text to be `miss`, `hit`, or `sunk`. Tool: a host browser. Probe on 2026-10-18: the host tool list has no browser (`scratch/browser-probe.txt`). A stand-in file `scratch/stand-in.html` was written and was not opened. This failed probe leaves R-3's rendered click, and the rendered difference among miss, hit, and sunk, unobserved. Owner: verify, when a browser tool exists. It does not block the local suite.

## Decisions

W1 added no decision. AD-1 through AD-6 stay accepted. Nothing moves to ## Superseded.

### AD-1 Node standard library HTTP

Choice: `node:http` in `server.js`. Why: R-1 bans npm, and the probe showed `node:http` can answer JSON. Alternative: Express or another framework. Status: accepted for this product.

### AD-2 Rules module `game.js`

Choice: placement and shots live in `game.js`, imported by `server.js` and by `test/`. Why: S5 requires one module the server uses. Alternative: rules inline in `server.js`, which tests could not import without listening. Status: accepted.

### AD-3 Process memory

Choice: games live in a `Map` until the process exits. Why: the request does not ask for saved games. Alternative: a file or database, which adds durability the spec excludes. Status: accepted.

### AD-4 HTML in the server response

Choice: `GET /` sends one HTML document from `server.js`. Why: one process, no static host, no npm assets. Alternative: a separate file is also standard library, and can replace the string later without an API change. Status: accepted as the string-in-server form.

### AD-5 CommonJS and no package manifest

Choice: `require` in `.js` files, no `package.json`. Why: Node treats extensionless-manifest `.js` as CommonJS, and R-1 does not ask for a manifest. A sibling probe loaded `node:http`. A nested probe loaded the parent module with `require('../game.js')` and did not load it with `require('./game.js')`. Alternative: `"type": "module"` in `package.json`, which adds a manifest the request does not need. Status: accepted.

### AD-6 Request/response page, server holds the fleet

Choice: one HTTP request/response channel and a simple 10 by 10 button grid. Why: the request says a small game, and freshness is the response to the click. A client-only page was rejected because S1 requires a Node HTTP server and R-4 hides the fleet from the player. No WebSocket, no poll loop, no cache. Alternative: an animated board. Not used; the request does not ask for one. Status: accepted. The rendered click stays TC-B1 at verify.

## Superseded

none.
