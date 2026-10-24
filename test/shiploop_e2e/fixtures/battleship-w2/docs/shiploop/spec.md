# Battleship

New product. The as-of baseline has no behavior to preserve (`notes/current-system-baseline.md`). Request sentences are S1–S5 in the run `request.md`. Research defaults are in `notes/research.md` and are labeled below. They are not extra user sentences.

Pending: the in-process rules for the destroyer example, a seeded five-ship fleet, overlap rejection, touching ships, and cells outside 0 through 9 are observed passing under `node --test`. The HTTP requests, the page, and the server's import of the rules module remain open. The discovery baseline `node --test` reported `tests 0`; that observation stays historical.

## Requirements

### R-1 Single-player server without npm

Basis: S1. Preserved behavior: none. The game is one human player against a fleet the computer placed. It is served by a Node.js HTTP server. The server and the rules module load only Node built-in modules. No `npm install` and no `node_modules` are required to start or to test.

State: none of its own. The process is the runtime.

Acceptance:

- Positive: from a directory that has no `node_modules`, `node server.js` starts the HTTP server. Confirm by: start the process and receive a later criterion's HTTP response. Pass when the process is listening without an install step.
- Failure: n/a: there is no package manager step whose failure this requirement defines. A missing `server.js` is an incomplete build, not a runtime branch.
- Boundary: n/a: S1 sets a dependency ban, not a numeric limit.
- Consumer surface: the local process started by the player.
- Confirm by: `node server.js` with no install, plus a module-load review that imports use only `node:` built-ins.

### R-2 Listen port

Basis: S2. Preserved behavior: none.

Acceptance:

- Positive: with `PORT=3456`, the server accepts HTTP on `127.0.0.1:3456`. With `PORT` unset, it accepts HTTP on `127.0.0.1:3000`. Confirm by: `GET /api/new` to that host and port. Pass when the status is 200 and the body matches R-4.
- Failure: if `PORT` is empty, not an integer, or outside 1 through 65535, the process exits with a non-zero status and does not listen. Confirm by: start with `PORT=abc` and with `PORT=0`. Pass when the exit code is not 0 and no new game can be created on that port.
- Boundary: `PORT=1` and `PORT=65535` are valid integers. Confirm by: the same start rule as the positive case when the environment allows binding them. If the operating system refuses the bind, the process exits non-zero; that refusal is the operating system, not a second port rule.
- Consumer surface: the listen socket.
- Confirm by: the starts above.

### R-3 Playable page

Basis: S3. Preserved behavior: none. The page is the player's surface. It is one HTML document.

UI premises (no repository design system; no extra component library, because R-1 bans npm):

- Components: a heading, a 10 by 10 grid of buttons, a text region for the last shot, and a control that starts a new game.
- Interaction: loading the page requests a new game (R-4). Activating a cell sends a fire (R-5) for that row and column. The cell then shows `miss`, `hit`, or `sunk` to match `result`. When `gameOver` is true, the status region includes `Fleet sunk` and the page does not send another fire.
- Skin: the document uses its own CSS. Miss, hit, and sunk are visually distinct. No remote font, image, or script.

State: the page may remember which cells it has fired at for display. The server remains the authority for hit, miss, sunk, and game over.

Acceptance:

- Positive: `GET /` returns 200 and `Content-Type` containing `text/html`. The document title is exactly `Battleship`. The grid has 100 buttons. Each button exposes its row and column as integers 0 through 9, for example `data-row` and `data-col`. The document's script requests `GET /api/new` and, when a button is activated, sends `POST /api/fire` with JSON `{"game":"<id from that response>","row":<that button's row>,"col":<that button's column>}`. When the fire response has `gameOver` true, the status region includes the text `Fleet sunk` and the page sends no further fire. Confirm by: fetch `/` and parse the document, then load it in a browser, activate one cell, and read the cell text. Pass when the title, 100 labeled buttons, both API paths, and the POST field names are present, and the activated cell shows `miss`, `hit`, or `sunk`. A page that only has a title and 100 buttons, with no `/api/new` or `/api/fire` call, fails.
- Failure: `GET /no-such-page` returns 404. Confirm by: that request. Pass when the status is 404.
- Boundary: the title string is `Battleship` with no extra words. Row and column labels include 0 and 9. Confirm by: the same parsed document. Pass when the title is equal to `Battleship` and both 0 and 9 occur as labels.
- Consumer surface: the browser page served to the player.
- Confirm by: the HTML parse above, and a browser check that loads `/`, starts a game, activates one cell, and shows a miss, hit, or sunk state on that cell.

### R-4 Start a game

Basis: S4, first clause. Preserved behavior: none. Design default from research Q-3 and Q-4: the computer places the fleet in memory before the response, and the response does not contain the placement.

Affected state: a game record held only in the server process, keyed by `game`. Before: no record for the new id. After a successful create: one record, no shots fired, five ships placed under R-7, `gameOver` false. The record ends when the process exits. A later fire with that id then fails under R-5.

Service: one Node process. The `GET` response is the completion. No queue, cache, or second authority. Revocation is not applicable; the id dies with the process.

Acceptance:

- Positive: `GET /api/new` returns 200 and `Content-Type` containing `application/json`. The body is an object with a string `game` field. Two calls return two different `game` strings. Confirm by: two fetches. Pass when both statuses are 200, both ids are non-empty strings, and the ids differ.
- Failure: n/a: this route has no body to reject. A non-GET method is R-5's method rule.
- Boundary: the JSON has no ship names, coordinates, or cell lists. Confirm by: parse the body and list its keys and nested values. Pass when no value is an array of positions and no key names a ship.
- Consumer surface: `GET /api/new`.
- Confirm by: the two fetches above.

### R-5 Fire at a cell

Basis: S4, second clause. Preserved behavior: none. Design defaults from research Q-3, recorded here so the result words are testable:

- `row` and `col` are integers 0 through 9.
- `result` is `hit` when the cell is a ship and that ship still has another unfired cell.
- `result` is `sunk` when the cell is the last unfired cell of its ship.
- `result` is `miss` when the cell is not a ship.
- `gameOver` is a boolean on every successful fire. It is true only when every ship cell of that game has been fired.
- A second fire on the same cell returns the same `result` as the first fire and does not change ships or `gameOver`.
- The body does not include ship coordinates.

Affected state: the game from R-4. Before a new cell is fired, that cell is unfired. After a successful first fire, that cell is fired. Occupied cells of other ships stay as they were. An error leaves the game unchanged. Process exit removes the game.

Example, rules call with a caller-supplied placement of one destroyer on `(0,0)` and `(0,1)` and no other ship:

1. Fire `row` 0, `col` 0. Expect `result` `hit` and `gameOver` false.
2. Fire `row` 0, `col` 0 again. Expect `result` `hit` and `gameOver` false.
3. Fire `row` 1, `col` 0. Expect `result` `miss` and `gameOver` false.
4. Fire `row` 0, `col` 1. Expect `result` `sunk` and `gameOver` true.

HTTP example, full game, placement unknown to the client:

1. `GET /api/new` and read `game`.
2. `POST /api/fire` with body `{"game":"<that id>","row":0,"col":0}`.
3. Expect 200 and body `{"result":"miss","gameOver":false}` or the same shape with `hit` or `sunk`. `gameOver` may be true only if that single cell were the entire fleet, which R-7 forbids, so this first shot has `gameOver` false.
4. Fire every cell from `(0,0)` through `(9,9)` once. The last response that covers the final ship cell has `result` `sunk` and `gameOver` true. Responses after that, including repeats, keep `gameOver` true.

Acceptance:

- Positive: `POST /api/fire` with `{"game":"<id from R-4>","row":0,"col":0}` returns 200 JSON with `result` set to `miss`, `hit`, or `sunk`, and `gameOver` a boolean. Confirm by: that request after `GET /api/new`. Pass when the status is 200 and those two fields match that set.
- Failure: unknown `game`, missing `game`, `row`, or `col`, a non-integer `row` or `col`, a `row` or `col` outside 0 through 9, and a body that is not JSON each return 400 and `{"error":"<non-empty string>"}`. The game, when it already exists, is unchanged. Confirm by: those five requests against a known game, with a rules read of occupied cells before and after where a game exists. Pass when each status is 400 and the occupied unfired set is unchanged.
- Boundary: `row` 0, `row` 9, `col` 0, and `col` 9 are accepted. `row` -1 and `row` 10 are 400. A repeat fire returns the first `result` and the same `gameOver`. `GET /api/fire` and `POST /api/new` return 405. Confirm by: those requests. Pass when the corner cells are 200 for a live game, the out-of-range cells are 400, the repeat matches the first body, and the wrong methods are 405.
- Consumer surface: `POST /api/fire`, and the rules functions the server uses.
- Confirm by: the HTTP requests above, plus the destroyer example as a `node:test` case that calls the rules with that placement.

Open gap: the destroyer example is satisfied in process. The HTTP example and the HTTP acceptance checks in this clause are not satisfied. `server.js` does not exist.

### R-6 Rules module and tests

Basis: S5. Preserved behavior: none. The server uses a rules module for placing the fleet and resolving a shot. It does not inline a second copy of those rules. Tests live under `test/` and use `node:test`. The command `node --test`, run from the repository root, runs them.

The rules module accepts a caller-supplied placement so a test can replay the R-5 destroyer example exactly. The HTTP server does not take a placement from the client. It places the R-7 fleet itself.

Acceptance:

- Positive: `node --test` from the repository root exits 0. The run includes a `node:test` case under `test/` that imports the same rules module the server imports and replays the R-5 destroyer example: placement `(0,0)` and `(0,1)`; fire `(0,0)` expects `hit` and `gameOver` false; the same fire again expects `hit` and `gameOver` false; fire `(1,0)` expects `miss` and `gameOver` false; fire `(0,1)` expects `sunk` and `gameOver` true. Confirm by: `node --test`. Pass when the exit code is 0 and that case is reported passed. A file that only loads the module, or a test that does not assert those four results, fails this criterion.
- Failure: n/a: a failing test is a broken build of this requirement, not a player-facing branch.
- Boundary: n/a: S5 names the runner and the directory, not a count cap. The named destroyer case is the floor.
- Consumer surface: `node --test` and the server's module import.
- Confirm by: `node --test`, and a source check that `server.js` and the test import the same rules module.

Open gap: `node --test` exits 0 and the destroyer case is reported passed. The server's module import is not satisfied.

### R-7 Computer fleet placement

Basis: design default in research Q-3, because S3 and S4 say a fleet and every ship, and they do not name lengths. Not a user sentence. Preserved behavior: none.

The fleet is five ships: carrier 5, battleship 4, cruiser 3, submarine 3, destroyer 2. Each ship is a straight horizontal or vertical run of that many cells on the 10 by 10 board. Ships do not overlap and do not leave the board. Ships may touch. The server placement uses a random legal layout. A caller-supplied placement is rejected when it breaks those rules, except that a test may supply a smaller set only through the rules test entry that R-6 names. The server path always uses all five ships.

Creating a server game either returns a legal five-ship placement or fails the create. It does not return a partial fleet.

Acceptance:

- Positive: a server game from R-4 occupies 17 cells (5+4+3+3+2), in five straight runs of those lengths, all inside 0 through 9, with no shared cell. Confirm by: a rules test that creates a server placement, including one with a fixed random seed so the run is replayable. Pass when the cell count, lengths, bounds, and disjointness hold.
- Failure: a caller-supplied placement that overlaps or leaves the board is rejected and does not become a game. Confirm by: a rules test with carrier and battleship sharing `(0,0)`. Pass when placement is rejected and no game id is stored.
- Boundary: two ships touching on an edge are legal. A ship of length 5 on row 0, columns 0 through 4, is legal. A ship of length 5 on row 0, columns 6 through 10, is illegal. Confirm by: those three supplied placements. Pass when the first two are accepted and the third is rejected.
- Consumer surface: the rules module. The player never sees this layout (R-4, R-5).
- Confirm by: the rules tests above.

Open gap: the in-process seed fleet, the overlap rejection, touching ships, and the column bounds are satisfied. A server game that occupies the five-ship fleet is not satisfied until the server places it.

## Non-functional requirements

- Dependencies. Operating condition: a machine with Node.js, observed at v25.9.0, and no install rights required. Criterion: R-1. Verification: start and `node --test` without `npm install`.
- Privacy. The player is anonymous. The ship layout is hidden as in R-4 and R-5. The server does not log ship coordinates. No account data is stored. Verification: response and log checks in the fire tests.
- Latency, throughput, and uptime. Excluded: the request sets no numeric target. The game is one local process.
- Capacity. Excluded as a number: the request sets no player or game cap. Practical limit is process memory. Games are not written to disk (R-4).
- Accessibility score. Excluded as a named standard: the request names none. The playable control is a button grid under R-3 so a cell can be activated.

## Retired

none.
