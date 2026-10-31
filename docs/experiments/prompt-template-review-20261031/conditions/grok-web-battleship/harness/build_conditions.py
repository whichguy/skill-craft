import json, sys, re

BASE = "/Users/dadleet/src/skill-craft/docs/experiments/prompt-template-review-20261031/conditions"
req = json.load(open(f"{BASE}/grok-web-battleship.requirements.json"))["requirements"]

# (requirement, quote, observable, kind, candidate, exclude_reason)
C = []
def add(r, quote, observable, kind, cand=True, why=""):
    C.append((r, quote, observable, kind, cand, why))

# ---------------- R-1
add("R-1", "`node server.js` starts a listening HTTP server",
    "start `node server.js` with a free PORT and no node_modules; a TCP connection to that port is accepted and an HTTP GET gets an HTTP reply",
    "behaviour")
add("R-1", "It uses Node's built-in HTTP only.",
    "no outside observable beyond the server answering HTTP; a code-reading property",
    "structural", False, "how the server is built; not distinguishable from outside beyond R-1.1")
add("R-1", "the repository has no dependency manifest that `npm install` must satisfy",
    "absence of a required install step in the repository",
    "structural", False, "repository-file property, not product behaviour")

# ---------------- R-2
add("R-2", "`PORT=3456 node server.js` accepts a connection on `127.0.0.1:3456`",
    "start the server with PORT=3456; a TCP connection to 127.0.0.1:3456 is accepted", "behaviour")
add("R-2", "unset `PORT` accepts a connection on `127.0.0.1:3000`",
    "start the server with PORT removed from the environment; a TCP connection to 127.0.0.1:3000 is accepted", "boundary")
add("R-2", "Empty or unset `PORT` means 3000.",
    "start the server with PORT set to the empty string; a TCP connection to 127.0.0.1:3000 is accepted", "boundary")
for v, nm in (("0", "PORT=0"), ("-1", "PORT=-1"), ("65536", "PORT=65536"), ("abc", "PORT=abc")):
    add("R-2", "`PORT=0`, `PORT=-1`, `PORT=65536`, and `PORT=abc` each exit non-zero without keeping a listening socket",
        f"start the server with {nm}; the process exits non-zero and no listening socket remains for it", "error")
add("R-2", "and not as a requirement on 3000",
    "the text states no requirement about port 3000 when PORT is set",
    "behaviour", False, "the span only says port 3000 is not required when PORT is set; it imposes no condition")

# ---------------- R-3
add("R-3", "`GET /` returns 200", "GET / over HTTP; status is 200", "format")
add("R-3", "200 `text/html`", "GET /; the Content-Type header is text/html", "format")
add("R-3", "whose document title is exactly `Battleship`", "GET /; the <title> text is exactly Battleship", "format")
add("R-3", "with 100 fire controls", "GET /; the page has exactly 100 fire controls", "format")
add("R-3", "labeled with their row and column for every pair in `0..9` × `0..9`",
    "GET /; every pair (row, col) in 0..9 x 0..9 has a control whose accessible name carries that row and column", "format")
add("R-3", "the HTML contains no ship coordinate list", "GET /; the body has no embedded array of ship coordinates", "boundary")
add("R-3", "no ship name placed on a cell before a shot", "GET /; no cell carries a ship name (Carrier, Battleship, Cruiser, Submarine, Destroyer)", "boundary")
add("R-3", "sends `POST /api/fire` with that id, row, and column",
    "browser session: load /, wait for GET /api/new, activate one cell; the page sends POST /api/fire with that id, the cell's row and column", "behaviour")
add("R-3", "then shows that response's `result`",
    "browser session: after the response, the cell shows the response's result (Miss, Hit or Sunk)", "behaviour")
add("R-3", "while the request has not returned, the control does not show Hit, Miss, or Sunk",
    "browser session with a delayed fire response: the cell shows a pending state, not Hit, Miss or Sunk", "behaviour")
add("R-3", "A transport failure leaves the cell unshot",
    "browser session with the fire request failing: the cell stays unshot (still a fire control, no result shown)", "error")
add("R-3", "A transport failure leaves the cell unshot and shows an error.",
    "browser session with the fire request failing: the page shows an error", "error")
add("R-3", "then `GET /api/new`",
    "browser session: loading / makes the page request GET /api/new", "behaviour")
add("R-3", "It does not send a fire before that id exists.",
    "browser session with a delayed GET /api/new: activating a cell before the id arrives sends no POST /api/fire", "behaviour")
add("R-3", "A click or keyboard activation on an unshot cell is the fire control.",
    "browser session: keyboard activation (Enter or Space on a focused cell) fires like a click", "behaviour")
add("R-3", "Process exit removes games; closing the tab does not.",
    "HTTP: a game created on one connection is still playable from a new connection after the first connection closes", "behaviour")
add("R-3", "No animation is required.", "none: nothing is required", "behaviour", False, "states that nothing is required")
add("R-3", "one 10×10 grid of buttons, a status line, no framework skin",
    "look of the page", "structural", False, "UI premise about appearance; not an outside-observable condition with an exact criterion")
add("R-3", "the page may remember shots it has displayed.", "none: permission, not a requirement", "behaviour", False, "a permission (may), not a condition")
add("R-3", "The player never places or sees ships before a shot.",
    "no placing control and no ship shown before a shot", "behaviour", False, "covered by the HTML boundary conditions and by R-4 conditions")

# ---------------- R-4
add("R-4", "`GET /api/new` returns 200", "GET /api/new; status is 200", "format")
add("R-4", "returns 200 `application/json`", "GET /api/new; Content-Type is application/json", "format")
add("R-4", "with exactly the property `game`", "GET /api/new; the parsed JSON object has exactly one key, game", "format")
add("R-4", "a non-empty string", "GET /api/new; game is a string of length > 0", "format")
add("R-4", "A second call returns a different `game`.", "two GET /api/new calls return different game values", "behaviour")
add("R-4", "A non-GET method returns 405", "POST /api/new returns status 405", "error")
add("R-4", "A non-GET method returns 405 and creates no game.",
    "after POST /api/new no game exists that was not created by a GET (no new game appears)", "error")
add("R-4", "the JSON has no coordinate, ship, or board property",
    "GET /api/new; no key or value of the JSON names a coordinate, ship or board", "boundary")
add("R-4", "five ships, lengths 5, 4, 3, 3, 2",
    "rules module with any random: the fleet has five ships of lengths 5, 4, 3, 3, 2 (17 distinct cells); over HTTP a 100-cell sweep gives 17 hit-or-sunk results and five sunk results", "boundary")
add("R-4", "labels Carrier, Battleship, Cruiser, Submarine, Destroyer",
    "rules module: the fleet's ships carry these labels, in this order", "format")
add("R-4", "Placement is axis-aligned", "rules module: each ship's cells share one row or one column and are contiguous", "boundary")
add("R-4", "inside the grid", "rules module: every ship cell has row and column in 0..9", "boundary")
add("R-4", "no overlap", "rules module: no cell belongs to two ships", "boundary")
add("R-4", "touching allowed", "rules module with draws that place two ships side by side: the placement is kept, not re-drawn", "behaviour")
add("R-4", "`GET /api/new` does not require a body", "GET /api/new with no body and no content-length returns 200", "behaviour")
add("R-4", "ships in the label order above",
    "rules module with scripted draws: the first three draws place the Carrier, then Battleship, and so on", "behaviour")
add("R-4", "orientation (`random() < 0.5` means horizontal), then start row, then start column",
    "rules module with scripted draws: each ship consumes its draws in the order orientation, start row, start column", "behaviour")
add("R-4", "`random() < 0.5` means horizontal",
    "rules module: a draw below 0.5 gives a horizontal ship, a draw of exactly 0.5 gives a vertical ship", "boundary")
add("R-4", "Legal start rows are `0..9` horizontal",
    "rules module: for a horizontal ship the start row ranges over 0..9 (a row draw near 1 gives row 9)", "boundary")
add("R-4", "`0..(10 - length)` vertical",
    "rules module: for a vertical ship the start row ranges over 0..(10 - length) (a row draw near 1 gives row 10 - length)", "boundary")
add("R-4", "Legal start columns are `0..(10 - length)` horizontal",
    "rules module: for a horizontal ship the start column ranges over 0..(10 - length) (a column draw near 1 gives 10 - length)", "boundary")
add("R-4", "and `0..9` vertical",
    "rules module: for a vertical ship the start column ranges over 0..9 (a column draw near 1 gives column 9)", "boundary")
add("R-4", "The start is `Math.floor(random() * (max + 1))`",
    "rules module: start = floor(draw * (max + 1)) (draw 0.2 on 0..9 gives 2; a draw just below 1 gives max)", "boundary")
add("R-4", "toward increasing column (horizontal)",
    "rules module: a horizontal ship's cells run from the start toward increasing column", "behaviour")
add("R-4", "or increasing row (vertical)",
    "rules module: a vertical ship's cells run from the start toward increasing row", "behaviour")
add("R-4", "If any cell is already occupied, that attempt is discarded and the three draws repeat.",
    "rules module with scripted draws: an overlapping attempt is discarded and the next three draws are used", "behaviour")
add("R-4", "Two requests do not share a game unless they send the same id.",
    "HTTP: firing at game A does not change game B", "behaviour")
add("R-4", "Two requests do not share a game unless they send the same id.",
    "HTTP: two fires with the same id act on the same game (state persists between requests)", "behaviour")
add("R-4", "Restarting the process removes every game.",
    "HTTP: after the server process restarts, a game id from before is unknown (404)", "behaviour")
add("R-4", "The computer places them at creation.", "placement time", "behaviour", False,
    "placement time is not observable from outside; eager and lazy placement answer alike")
add("R-4", "No maximum game count is specified.", "none", "behaviour", False, "states that no limit is specified; no condition")
add("R-4", "No cache of the fleet on the client. No background worker. No login event.",
    "none", "structural", False, "structural service premises; no outside check")
add("R-4", "`GET /api/new` completes in that HTTP response.", "response arrives", "behaviour", False,
    "no time bound or other criterion is stated")

# ---------------- R-5
add("R-5", "`result` is `miss`, `hit`, or `sunk`", "every successful fire body has result in miss, hit, sunk (lower-case)", "format")
add("R-5", "`gameOver` is boolean on every successful fire", "every successful fire body has a boolean gameOver", "format")
add("R-5", "`hit` means the cell is a ship that still has at least one unshot cell after this shot",
    "first shot at a ship cell whose ship keeps an unshot cell returns hit", "behaviour")
add("R-5", "`sunk` means this shot took that ship's last cell", "the shot that takes a ship's last cell returns sunk", "behaviour")
add("R-5", "`miss` means the cell is not a ship", "first shot at a water cell returns miss", "behaviour")
add("R-5", "`gameOver` is `true` only when every ship has no unshot cell",
    "gameOver is false while any ship cell is unshot", "behaviour")
add("R-5", "including on the shot that sinks the last ship",
    "the response to the shot that takes the last ship cell has gameOver true", "boundary")
add("R-5", "and stays `true` afterward", "every response after the game is over has gameOver true", "behaviour")
add("R-5", "A repeat shot on a cell that already has a result does not change occupancy or which ships are sunk.",
    "repeating a shot (many times) does not change how many cells are hit or which ships are sunk", "behaviour")
add("R-5", "The response `result` is the result stored for that cell on the first shot.",
    "a repeat shot returns the first shot's result (a cell first reported hit is still hit after its ship is sunk)", "behaviour")
add("R-5", "`gameOver` is the game's current value.",
    "a repeat shot returns the game's current gameOver, not the value seen on the first shot", "behaviour")
add("R-5", "Firing one returns `miss` and `gameOver` stays `true`.",
    "after the game is over, a first shot at any remaining cell returns miss", "behaviour")
add("R-5", "Errors do not add a shot and do not change `gameOver`.",
    "an erroring request (bad row, bad col, bad shape) records no shot", "error")
add("R-5", "Errors do not add a shot and do not change `gameOver`.",
    "an erroring request after the game is over leaves gameOver true; an erroring request leaves gameOver false before it", "error")
add("R-5", "unknown `game`: 404 `{\"error\":\"unknown game\"}`", "POST /api/fire with an unknown game id returns 404 with body {\"error\":\"unknown game\"}", "error")
add("R-5", "invalid JSON, or a JSON value that is not an object: 400 `{\"error\":\"invalid JSON\"}`",
    "POST /api/fire with body not-json returns 400 {\"error\":\"invalid JSON\"}", "error")
add("R-5", "invalid JSON, or a JSON value that is not an object: 400 `{\"error\":\"invalid JSON\"}`",
    "POST /api/fire with body null returns 400 {\"error\":\"invalid JSON\"}", "error")
add("R-5", "invalid JSON, or a JSON value that is not an object: 400 `{\"error\":\"invalid JSON\"}`",
    "POST /api/fire with a JSON array body returns 400 {\"error\":\"invalid JSON\"}", "error")
add("R-5", "invalid JSON, or a JSON value that is not an object: 400 `{\"error\":\"invalid JSON\"}`",
    "POST /api/fire with a JSON number or string body returns 400 {\"error\":\"invalid JSON\"}", "error")
add("R-5", "missing `game`, `row`, or `col`, a non-string `game`, or a non-integer `row` or `col`: 400 `{\"error\":\"invalid shot\"}`",
    "POST /api/fire with game missing returns 400 {\"error\":\"invalid shot\"}", "error")
add("R-5", "missing `game`, `row`, or `col`, a non-string `game`, or a non-integer `row` or `col`: 400 `{\"error\":\"invalid shot\"}`",
    "POST /api/fire with row missing returns 400 {\"error\":\"invalid shot\"}", "error")
add("R-5", "missing `game`, `row`, or `col`, a non-string `game`, or a non-integer `row` or `col`: 400 `{\"error\":\"invalid shot\"}`",
    "POST /api/fire with col missing returns 400 {\"error\":\"invalid shot\"}", "error")
add("R-5", "missing `game`, `row`, or `col`, a non-string `game`, or a non-integer `row` or `col`: 400 `{\"error\":\"invalid shot\"}`",
    "POST /api/fire with a non-string game (a number) returns 400 {\"error\":\"invalid shot\"}", "error")
add("R-5", "missing `game`, `row`, or `col`, a non-string `game`, or a non-integer `row` or `col`: 400 `{\"error\":\"invalid shot\"}`",
    "POST /api/fire with a non-integer row (1.5, or the string \"1\") returns 400 {\"error\":\"invalid shot\"}", "error")
add("R-5", "missing `game`, `row`, or `col`, a non-string `game`, or a non-integer `row` or `col`: 400 `{\"error\":\"invalid shot\"}`",
    "POST /api/fire with a non-integer col (1.5, or the string \"1\") returns 400 {\"error\":\"invalid shot\"}", "error")
add("R-5", "`row` or `col` outside `0..9`: 400 `{\"error\":\"invalid shot\"}`",
    "POST /api/fire with row 10 returns 400 {\"error\":\"invalid shot\"}", "boundary")
add("R-5", "`row` or `col` outside `0..9`: 400 `{\"error\":\"invalid shot\"}`",
    "POST /api/fire with row -1 returns 400 {\"error\":\"invalid shot\"}", "boundary")
add("R-5", "`row` or `col` outside `0..9`: 400 `{\"error\":\"invalid shot\"}`",
    "POST /api/fire with col 10 returns 400 {\"error\":\"invalid shot\"}", "boundary")
add("R-5", "`row` or `col` outside `0..9`: 400 `{\"error\":\"invalid shot\"}`",
    "POST /api/fire with col -1 returns 400 {\"error\":\"invalid shot\"}", "boundary")
add("R-5", "`row` or `col` outside `0..9`: 400 `{\"error\":\"invalid shot\"}`",
    "POST /api/fire with row 9 and with col 9 (the inclusive upper bound) is accepted (200)", "boundary")
add("R-5", "`row` or `col` outside `0..9`: 400 `{\"error\":\"invalid shot\"}`",
    "POST /api/fire with row 0 and with col 0 (the inclusive lower bound) is accepted (200)", "boundary")
add("R-5", "A successful body has exactly the properties `result` and `gameOver`.",
    "a successful fire body has exactly the keys result and gameOver", "format")
add("R-5", "It has no ship coordinates.", "a successful fire body names no ship coordinate or ship cell list", "boundary")
add("R-5", "returns 200 JSON each time", "every fire in the sweep returns status 200", "format")
add("R-5", "returns 200 JSON each time", "every fire in the sweep returns Content-Type application/json", "format")
add("R-5", "no state change: `(8,8)` stays `miss` and `gameOver` stays true",
    "rules module: fireShot with row 10 changes no state ((8,8) later still miss, gameOver still true)", "error")
add("R-5", "The HTTP server does not take a caller-supplied `random`", "a request carrying a random has no effect", "structural", False,
    "premise about the test seam, not a product condition with an exact criterion")

# ---------------- R-6
add("R-6", "The server calls a rules module for placement and firing.", "none from outside", "structural", False,
    "code-reading property; an inline copy of the rules answers the same over HTTP")
add("R-6", "`node --test` exits 0. The spec reporter shows a passing test whose name contains `R-4` and one whose name contains `R-5`.",
    "the run's own tests", "tests-themselves", False, "about the run's tests, not the product")
add("R-6", "that `R-5` test loads the rules module and runs the table without calling `listen`",
    "the run's own test file", "tests-themselves", False, "about the run's tests, not the product")
add("R-6", "No npm test runner.", "none", "structural", False, "repository convention")

# ---- emit
counters = {}
out = []
for r, quote, obs, kind, cand, why in C:
    assert r in req, r
    assert quote in req[r], (r, quote)
    counters[r] = counters.get(r, 0) + 1
    row = {"id": f"{r}.{counters[r]}", "requirement": r, "quote": quote, "observable": obs, "kind": kind, "candidate": cand}
    if not cand:
        row["exclude_reason"] = why
    out.append(row)
json.dump(out, open(f"{BASE}/grok-web-battleship/conditions.json", "w"), indent=1, ensure_ascii=False)
print(len(out), "conditions;", sum(1 for x in out if x["candidate"]), "candidates")
from collections import Counter
print(Counter((x["requirement"], x["candidate"]) for x in out))
