#!/usr/bin/env python3
"""Generate conditions.json from the frozen requirements text only (no repo/run_dir access)."""
import json, re, sys

REQ = '/Users/dadleet/src/skill-craft/docs/experiments/prompt-template-review-20261031/conditions/v2170-ds-battleship.requirements.json'
OUT = '/Users/dadleet/src/skill-craft/docs/experiments/prompt-template-review-20261031/conditions/v2170-ds-battleship/conditions.json'
reqs = json.load(open(REQ))['requirements']
norm = lambda s: re.sub(r'\s+', ' ', s)
nreq = {k: norm(v) for k, v in reqs.items()}

C = True
X = False
rows = []
def add(id, quote, observable, kind, cand=True, why=None):
    r = id.split('.')[0]
    rows.append(dict(id=id, requirement=r, quote=quote, observable=observable, kind=kind,
                     candidate=cand, **({'exclude_reason': why} if not cand else {})))

# ---------------- R-1 ----------------
add('R-1.1', 'starts serving and the process keeps running',
    'after `node server.js` starts, the process is still alive and still answers GET /api/new with 200 several seconds later', 'behaviour')
add('R-1.2', 'with `PORT=8081`, it listens on 8081',
    'with PORT=8081 the process listens on 8081 (the startup line / a request to 8081 succeeds)', 'boundary')
add('R-1.3', 'an integer in `1..65535`',
    'PORT=65535 (upper edge) is accepted: the process listens on 65535, not the 3000 fallback', 'boundary')
add('R-1.4', 'an integer in `1..65535`',
    'PORT=65536 (one above the upper edge) is rejected: the process listens on 3000', 'boundary')
add('R-1.5', 'an integer in `1..65535`',
    'PORT=1 (lower edge) is accepted: the process attempts to listen on 1, not the 3000 fallback', 'boundary')
add('R-1.6', 'With `PORT` unset, the server listens on 3000',
    'with PORT unset the process listens on 3000', 'boundary')
add('R-1.7', 'non-numeric',
    'PORT=abc does not crash the server and the process listens on the default 3000', 'error')
add('R-1.8', 'the empty string',
    'PORT="" does not crash the server and the process listens on the default 3000', 'error')
add('R-1.9', 'zero',
    'PORT=0 falls back: the process listens on 3000 (not an ephemeral port)', 'error')
add('R-1.10', '`70000`',
    'PORT=70000 (out of range) falls back: the process listens on 3000', 'error')
add('R-1.11', 'negative',
    'PORT=-1 falls back: the process listens on 3000', 'error')
add('R-1.12', '`1.5`',
    'PORT=1.5 (non-integer) falls back: the process listens on 3000', 'error')
add('R-1.13', 'a non-zero exit',
    'starting a second server on a port already in use exits with a non-zero status', 'error')
add('R-1.14', 'a clear error message',
    'starting a second server on a port already in use writes a non-empty error message naming the problem to stderr', 'error')
add('R-1.15', 'The service binds `127.0.0.1` only',
    'a connection to the host\'s non-loopback address on the listening port is refused while 127.0.0.1 answers', 'behaviour')
add('R-1.16', 'the process\'s startup log line',
    'the startup output (stdout/stderr) contains an http URL / port naming where the server listens', 'format')
add('R-1.17', 'Nothing is installed and nothing is built.',
    'no install or build step is needed; node_modules / package.json absent', 'structural', X,
    'structural: absence of dependencies/build step is a property of the repository contents, not an observable behaviour of the running service')

# ---------------- R-2 ----------------
add('R-2.1', 'returns a complete HTML document (`Content-Type: text/html; charset=utf-8`)',
    'GET / returns status 200 with Content-Type exactly text/html; charset=utf-8', 'format')
add('R-2.2', 'whose `<title>` is exactly `Battleship`',
    'the body of GET / contains <title>Battleship</title> exactly', 'format')
add('R-2.3', 'The response body already contains the 10×10 grid as 100',
    'the body of GET / matches /data-row="\\d" data-col="\\d"/g exactly 100 times (cells present in served HTML, no client script needed)', 'format')
add('R-2.4', 'with `R` and `C` in 0–9',
    'each of the ten data-row values 0..9 appears exactly 10 times and data-col values likewise (no row/col 10, no gaps)', 'boundary')
add('R-2.5', '`data-row="0"` `data-col="0"` is the top-left cell',
    'data-row="0" data-col="0" is the first cell in document order in the served body', 'format')
add('R-2.6', '`<button class="cell" data-row="R" data-col="C" aria-label="…">`',
    'every one of the 100 cells is a <button class="cell"> with a non-empty aria-label that names its coordinates', 'format')
add('R-2.7', 'no CDN, no build step',
    'no src or href value in the served body begins with http://, https:// or //', 'behaviour')
add('R-2.8', 'announces each outcome in a `role="status"` region',
    'the served body contains an element with role="status" (the status region)', 'format')
add('R-2.9', 'offers a "New game" control',
    'the served page offers a control whose text is "New game"', 'format')
add('R-2.10', 'Clicking a cell fires exactly one `POST /api/fire` for that cell\'s `data-row`/`data-col` with no navigation or document reload',
    'in a browser, one click on a cell sends exactly one POST /api/fire carrying that cell\'s data-row/data-col and the document does not navigate/reload', 'behaviour')
add('R-2.11', 'renders the returned outcome on it',
    'after a shot the clicked cell is marked with the response result (miss, hit or sunk), different results shown differently', 'behaviour')
add('R-2.12', 'shows how many ships remain',
    'on load the page displays the number of ships remaining (5)', 'behaviour')
add('R-2.13', 'updates the displayed ships-remaining count to the response\'s `shipsRemaining`',
    'after a sink the displayed count equals the response\'s shipsRemaining (drops by one)', 'behaviour')
add('R-2.14', 'announces each outcome in a',
    'after a shot the status region text describes the outcome (miss/hit/sunk) and remaining ships', 'behaviour')
add('R-2.15', 'A cell that has already been fired at cannot be fired again from the page (it is not clickable)',
    'clicking an already-fired cell sends no request', 'boundary')
add('R-2.16', 'the grid does not accept input while a shot is in flight',
    'while a shot request is pending (slow response), a click on another cell sends no second request', 'boundary')
add('R-2.17', 'and after the game ends',
    'after gameOver a click on an unfired cell sends no request', 'boundary')
add('R-2.18', 'the page shows the error in the status region',
    'when the shot request fails (network error or non-2xx) the status region shows an error message', 'error')
add('R-2.19', 're-enables the grid rather than appearing to have fired',
    'after a failed shot the cell is not marked as fired and the grid accepts a retry', 'error')
add('R-2.20', 'the same status region announces the win in words (that all five ships are sunk)',
    'when the last ship sinks the status region text says all five ships are sunk', 'behaviour')
add('R-2.21', 'the "New game" control remains available',
    'after the win the New game control is present and enabled', 'behaviour')
add('R-2.22', '"New game" starts a fresh board whose cells show no previous results',
    'after New game every cell is unmarked', 'behaviour')
add('R-2.23', '"New game" starts a fresh board',
    'after New game the ships-remaining count is back to 5 and a new game id is used (GET /api/new issued)', 'behaviour')
add('R-2.24', 'Every cell is reachable and fireable by keyboard',
    'Tab reaches a cell and Enter on it fires exactly one shot', 'behaviour')
add('R-2.25', 'keeps a visible focus indicator',
    'a focused cell has a visible focus ring (computed outline/box-shadow not none)', 'behaviour')
add('R-2.26', 'each fired cell\'s outcome is readable as text rather than conveyed by colour alone',
    'a fired cell\'s text content or accessible name states the outcome, not only a colour class', 'behaviour')
add('R-2.27', 'without focus moving off the fired cell',
    'after Enter on a cell, document.activeElement is still that cell', 'behaviour')
add('R-2.28', 'inert for the duration of a request',
    'while a shot is in flight clicking New game changes nothing (no start request, board unchanged)', 'boundary')
add('R-2.29', 'a failed start leaves the board exactly as it was',
    'a refused/failed New game on a finished board leaves the board, its marks and closed state exactly as before', 'error')
add('R-2.30', 'an off-contract shot answer is reported rather than marked',
    'a 200 answer lacking the contract fields is reported in the status region and the cell stays unmarked', 'error')

# ---------------- R-3 ----------------
add('R-3.1', 'Each new game places five ships',
    'a created game has exactly five ships', 'behaviour')
add('R-3.2', 'carrier 5, battleship 4, cruiser 3, submarine 3, destroyer 2 (17 cells)',
    'ship lengths are exactly 5, 4, 3, 3, 2; together 17 distinct cells (12 hit + 5 sunk results in a full walk)', 'behaviour')
add('R-3.3', 'entirely inside the 10×10 board',
    'every ship cell has 0 <= row <= 9 and 0 <= col <= 9 over many seeded placements', 'boundary')
add('R-3.4', 'axis-aligned',
    'each ship\'s cells share a single row or a single column', 'behaviour')
add('R-3.5', 'with no cell shared by two ships',
    'no two ships share a cell over many seeded placements', 'behaviour')
add('R-3.6', 'Ships may touch.',
    'among many seeded placements some fleets have ships on adjacent cells (placement does not forbid touching)', 'boundary')
add('R-3.7', 'Placement is driven by an injectable random source so it can be reproduced in tests.',
    'two games created from the same seed have identical fleets', 'behaviour')
add('R-3.8', 'seeds `1..20` produce more than one distinct fleet',
    'different seeds produce different fleets', 'behaviour')
add('R-3.9', 'Each ship is attempted at\nmost 200 times'.replace('\n', ' '),
    'a random source that always returns 0 makes at most 200 placement attempts per ship before giving up', 'boundary')
add('R-3.10', 'game creation throws an `Error`',
    'with an exhausted placement budget game creation throws an Error instead of returning a fleet', 'error')
add('R-3.11', 'whose\nmessage names placement'.replace('\n', ' '),
    'the thrown Error\'s message mentions placement', 'error')
add('R-3.12', 'instead of returning a partial fleet',
    'game creation with an exhausted budget does not return a partial fleet or overlapping ships', 'error')
add('R-3.13', 'at random',
    'across new games in one server process fleets differ (placement uses a real random source by default)', 'behaviour')
add('R-3.14', 'No API response and no page payload ever contains ship positions\n  before those cells are fired at.'.replace('\n  ', ' '),
    'the /api/new body carries no ship/fleet positions', 'behaviour')
add('R-3.15', 'the served page names no ship cell',
    'the page source served by GET / names no ship cell (no fleet in HTML/JS)', 'behaviour')
add('R-3.16', 'every `/api/fire` answer carries\nexactly `result`, `gameOver` and `shipsRemaining`'.replace('\n', ' '),
    'every /api/fire answer has exactly the keys result, gameOver, shipsRemaining; no fired-cell list or ship data', 'format')

# ---------------- R-4 ----------------
add('R-4.1', 'Returns `200`',
    'GET /api/new answers status 200', 'format')
add('R-4.2', '`Content-Type: application/json`',
    'GET /api/new carries an application/json content type', 'format')
add('R-4.3', 'its payload\n  contains exactly `game`, `size` and `ships`'.replace('\n  ', ' '),
    'the /api/new payload has exactly the keys game, size, ships (no extras)', 'format')
add('R-4.4', '"size": 10',
    'the size field of /api/new is the number 10', 'format')
add('R-4.5', '"ships": 5',
    'the ships field of /api/new is the number 5', 'format')
add('R-4.6', 'RFC 4122 version\n  4 UUID in lower-case hex'.replace('\n  ', ' '),
    'the id matches /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/', 'format')
add('R-4.7', 'unique per call',
    'two consecutive /api/new calls return different ids', 'behaviour')
add('R-4.8', 'identifies that game\'s state in the server process',
    'the id returned by /api/new works with POST /api/fire (200) and the game state persists across requests', 'behaviour')

# ---------------- R-5 ----------------
add('R-5.1', '(row 0 is\nthe top row)'.replace('\n', ' '),
    'row addresses rows and col addresses columns (not swapped): a shot at (r,c) hits what the rules place at row r column c', 'behaviour')
add('R-5.2', 'A shot at an unfired cell of a ship reports `hit`, unless it completes that ship',
    'a shot at an unfired cell of a ship that does not complete it answers result "hit"', 'behaviour')
add('R-5.3', 'in which case it reports `sunk`',
    'the shot that completes a ship answers result "sunk"', 'behaviour')
add('R-5.4', 'a shot at water reports `miss`',
    'a shot at water answers result "miss"', 'behaviour')
add('R-5.5', 'A successful response is `200` with',
    'a successful fire answers 200 with a JSON body whose result is miss|hit|sunk, gameOver is boolean and shipsRemaining an integer', 'format')
add('R-5.6', 'are accepted at both extremes, `0` and `9`',
    'row=0,col=0 and row=9,col=9 are accepted (200)', 'boundary')
add('R-5.7', 'rejected one\n  step outside (`-1`, `10`) with `400`'.replace('\n  ', ' '),
    'row=-1 answers 400', 'boundary')
add('R-5.8', 'rejected one\n  step outside (`-1`, `10`) with `400`'.replace('\n  ', ' '),
    'row=10 answers 400', 'boundary')
add('R-5.9', 'rejected one\n  step outside (`-1`, `10`) with `400`'.replace('\n  ', ' '),
    'col=-1 answers 400', 'boundary')
add('R-5.10', 'rejected one\n  step outside (`-1`, `10`) with `400`'.replace('\n  ', ' '),
    'col=10 answers 400', 'boundary')
add('R-5.11', 'A repeated shot at an already-fired cell returns `409` with\n  `{"error": "..."}`'.replace('\n  ', ' '),
    'a second shot at the same cell answers 409 with a JSON {"error": ...} body', 'error')
add('R-5.12', 'changes nothing: `shipsRemaining` and later results are unaffected',
    'after a refused repeat shot the game reconciles: later results and shipsRemaining are as if the repeat never happened; firing twice at a ship cell leaves the ship needing the same hits', 'error')
add('R-5.13', 'Accepts a JSON body',
    'a valid JSON body {"game","row","col"} fires the shot', 'behaviour', X,
    'duplicate of other conditions (R-5.2..R-5.6 exercise the accepted body); not separately observable')

# ---------------- R-6 ----------------
add('R-6.1', 'false\nuntil the shot that sinks the last ship'.replace('\n', ' '),
    'with one ship still afloat (the 16th ship cell fired) the response has gameOver false and shipsRemaining 1', 'boundary')
add('R-6.2', 'true from then on',
    'the response to the 17th ship cell has gameOver true and shipsRemaining 0', 'boundary')
add('R-6.3', 'decreases by one on exactly the five `sunk`\n  responses'.replace('\n  ', ' '),
    'shipsRemaining decreases by exactly one on each of the five sunk responses (5 to 0)', 'behaviour')
add('R-6.4', '`shipsRemaining` counts ships not yet sunk',
    'hit and miss responses leave shipsRemaining unchanged', 'behaviour')
add('R-6.5', 'a further shot at an unfired cell is refused with `409`',
    'after gameOver a shot at an unfired cell answers 409', 'error')
add('R-6.6', 'and does not change the game; `gameOver` stays true',
    'after the refused post-gameOver shot another shot is still refused 409 and the game is not reopened', 'error')

# ---------------- R-7 ----------------
add('R-7.1', 'a\nmalformed JSON body'.replace('\n', ' '),
    'POST /api/fire with a malformed JSON body answers 400 {"error"}', 'error')
add('R-7.2', 'a missing, wrong-type or empty `game`',
    'POST /api/fire with body {} (missing game) answers 400', 'error')
add('R-7.3', 'a missing, wrong-type or empty `game`',
    'POST /api/fire with a wrong-type game (number) answers 400', 'error')
add('R-7.4', 'only a missing, non-string or empty `game` is `400`',
    'POST /api/fire with game "" answers 400', 'error')
add('R-7.5', 'a non-integer `row`/`col`',
    '{"game":id,"row":1.5,"col":0} answers 400', 'error')
add('R-7.6', 'a non-integer `row`/`col`',
    '{"game":id,"row":"1","col":0} answers 400', 'error')
add('R-7.7', 'a non-integer `row`/`col`',
    '{"game":id,"row":0,"col":1.5} answers 400', 'error')
add('R-7.8', 'a non-integer `row`/`col`',
    '{"game":id,"row":0,"col":"1"} answers 400', 'error')
add('R-7.9', '`404` for a non-empty string id the server does not hold',
    'a well-formed but unknown UUID (00000000-0000-4000-8000-000000000000) answers 404', 'error')
add('R-7.10', 'any non-empty string id the server does not hold is `404`, whether or not it\nlooks like a UUID'.replace('\n', ' '),
    'game "not-a-uuid" answers 404, not 400', 'error')
add('R-7.11', '`413` for a body over 1 MB',
    'a body of 1 MB + 1 byte answers 413', 'error')
add('R-7.12', 'over 1 MB',
    'a valid JSON fire body of just under 1 MB (whitespace padded) is not rejected as too large', 'boundary')
add('R-7.13', 'A known path reached with the wrong method\n(`GET /api/fire`'.replace('\n', ' '),
    'GET /api/fire answers 405', 'error')
add('R-7.14', '`POST /api/new`',
    'POST /api/new answers 405', 'error')
add('R-7.15', '`POST /`',
    'POST / answers 405', 'error')
add('R-7.16', 'so `/api/new?x=1` is `/api/new`',
    'GET /api/new?x=1 answers 200 like /api/new', 'boundary')
add('R-7.17', '(`/api/fire/` is `404`, not `405`)',
    'GET /api/fire/ (trailing slash) answers 404, not 405', 'boundary')
add('R-7.18', '`/api` are unknown paths',
    'GET /api answers 404', 'boundary')
add('R-7.19', 'An unknown path such as `/nope` returns `404` JSON, not the page',
    'GET /nope answers 404 with a JSON body, not the HTML page', 'error')
add('R-7.20', 'Every\nerror body is `{"error": "<message>"}`'.replace('\n', ' '),
    'every error body parses as a JSON object whose only key is a non-empty string "error"', 'format')
add('R-7.21', 'with a JSON content type',
    'every error response (e.g. 405, 413, 404, 409) carries a JSON content type', 'format')
add('R-7.22', 'No request can crash the\nprocess.'.replace('\n', ' '),
    'after a malformed body the server still answers a valid GET /api/new with 200', 'error')
add('R-7.23', 'a body over 1 MB',
    'after a body over 1 MB the server still answers a valid GET /api/new with 200', 'error')
add('R-7.24', 'a request target\nWHATWG `URL` refuses (`GET http://[`) answers `400` and the process keeps serving'.replace('\n', ' '),
    'a request with target http://[ answers 400 and the process keeps serving', 'error')
add('R-7.25', 'that path now answers `500` and keeps serving',
    'when the rules cannot deal a fleet, GET /api/new answers 500 {"error"}, stores no game and the process keeps serving', 'error')

# ---------------- R-8 ----------------
add('R-8.1', 'can be required and exercised in a plain Node process\n  with no server running'.replace('\n  ', ' '),
    'requiring battleship.js in a plain node process does not start a server or open a port and exits normally', 'behaviour')
add('R-8.2', 'It imports nothing from\n`node:http`, knows nothing about requests or responses'.replace('\n', ' '),
    'the module source has no http/req/res reference', 'structural', X,
    'structural: a property of source files, checked by reading the source, not an observable runtime behaviour')
add('R-8.3', '`server.js` contains no fleet data or result strings of its own',
    'server.js has no ship names or miss/hit/sunk literals', 'structural', X,
    'structural: a property of source files, checked by reading the source')
add('R-8.4', 'is the only place the rules live',
    'rules are in battleship.js only', 'structural', X,
    'structural: code organisation, not observable from outside')

# ---------------- R-9 ----------------
add('R-9.1', 'discovered and run by the bare command `node --test` from the\nrepository root'.replace('\n', ' '),
    'node --test from repo root exits 0 reporting at least 14 passing tests', 'tests-themselves', X,
    'tests-themselves: the requirement describes the test suite, not the product')
add('R-9.2', 'A deliberately broken rules expectation makes the run exit non-zero',
    'a broken expectation fails the run', 'tests-themselves', X,
    'tests-themselves: the requirement describes the test suite, not the product')
add('R-9.3', 'The suite passes with no `node_modules` present and no `package.json`\n  required.'.replace('\n  ', ' '),
    'no node_modules and no package.json', 'preserved', X,
    'structural/preserved: repository contents, no runtime behaviour to violate')
add('R-9.4', 'The suite includes, at the rules layer, cases covering',
    'the test names cover the listed cases', 'tests-themselves', X,
    'tests-themselves: the requirement lists what the tests must cover')
add('R-9.5', 'use `node:test` and\n`node:assert/strict`'.replace('\n', ' '),
    'test files import node:test and node:assert/strict', 'structural', X,
    'structural: a property of test source files')

# ---------------- R-10 ----------------
add('R-10.1', 'the page starts a new game on load',
    'loading the page issues GET /api/new and the page uses the returned id for its shots', 'behaviour')
add('R-10.2', 'A page reload starts a fresh game',
    'after a reload the document shows 100 unmarked cells and the count back at 5', 'behaviour')
add('R-10.3', 'the earlier game id is no\n  longer used by that page'.replace('\n  ', ' '),
    'after a reload the page\'s next shot carries a different game id than before the reload', 'behaviour')
add('R-10.4', 'it never guesses a result optimistically beyond a pending marker',
    'a shot whose request fails leaves every cell unmarked', 'error')
add('R-10.5', 'There is no persistence: restarting the process discards every game',
    'after a server restart (same port) an id issued before the restart answers 404 on fire; games are not written to disk', 'behaviour')
add('R-10.6', 'the\n  page\'s next shot reports an error'.replace('\n  ', ' '),
    'after a restart the page\'s next shot reports an error in the status region, marks no cell and leaves the count unchanged', 'error')
add('R-10.7', 'the player can start a new game without reloading being\n  required'.replace('\n  ', ' '),
    'after the error from a restarted server, New game deals a fresh board with no page reload', 'error')
add('R-10.8', 'firing at a cell in game A never\n  changes game B\'s `shipsRemaining` or its cells'.replace('\n  ', ' '),
    'a shot at cell (0,0) in game A does not mark (0,0) as fired in game B: B can fire there (200) and then repeats get 409', 'boundary')
add('R-10.9', 'game B still answers a shot at a cell it\n  has not had fired at with `200` and `gameOver: false`'.replace('\n  ', ' '),
    'driving game A to gameOver leaves game B\'s shipsRemaining and gameOver untouched (B answers 200, gameOver false, shipsRemaining 5 or 4)', 'boundary')
add('R-10.10', 'produce exactly one `200` and one `409`',
    'two simultaneous POST /api/fire for the same cell give exactly one 200 and one 409', 'boundary')
add('R-10.11', 'reflects that cell having been fired at once, not twice',
    'after the concurrent double-shot the game\'s shipsRemaining/results reflect the cell fired once', 'boundary')
add('R-10.12', 'No identity, login, sharing or per-user record is introduced.',
    'no identity/login/sharing endpoints or records', 'structural', X,
    'structural: a negative scope statement; there is no single outside observation that violates exactly this')

# --- remove None placeholder artefacts ---
rows = [r for r in rows if r]

# validation
bad = 0
seen = set()
for r in rows:
    assert r['id'] not in seen, r['id']
    seen.add(r['id'])
    q = norm(r['quote'])
    if q not in nreq[r['requirement']]:
        bad += 1
        print('QUOTE NOT FOUND', r['id'], repr(q), file=sys.stderr)
if bad:
    sys.exit(1)
json.dump(rows, open(OUT, 'w'), indent=1, ensure_ascii=False)
print(len(rows), 'rows;', sum(r['candidate'] for r in rows), 'candidates')
