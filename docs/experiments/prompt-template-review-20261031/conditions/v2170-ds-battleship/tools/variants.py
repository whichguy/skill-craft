"""Variant table: id -> list of (file, old, new) exact replacements (each old must occur exactly once)
(or (file, regex, new, 're')). Applied to the unchanged copy to make one product-code violation per condition."""
SRV, BAT, IDX = 'server.js', 'battleship.js', 'public/index.html'
V = {}

# ---------------- R-1: start / PORT ----------------
FIRST = "  if (typeof value !== 'string' || !/^\\d+$/.test(value)) return DEFAULT_PORT;"
V['R-1.1'] = [(SRV, "  server.listen(port, '127.0.0.1', () => {", "  setTimeout(() => process.exit(0), 3000);\n  server.listen(port, '127.0.0.1', () => {")]
V['R-1.2'] = [(SRV, "  return port >= 1 && port <= 65535 ? port : DEFAULT_PORT;", "  return DEFAULT_PORT;")]
V['R-1.3'] = [(SRV, "port <= 65535 ?", "port <= 65534 ?")]
V['R-1.4'] = [(SRV, "port <= 65535 ?", "port <= 65536 ?")]
V['R-1.5'] = [(SRV, "port >= 1 &&", "port >= 2 &&")]
V['R-1.6'] = [(SRV, FIRST, "  if (typeof value !== 'string') return 3001;\n  if (!/^\\d+$/.test(value)) return DEFAULT_PORT;")]
V['R-1.7'] = [(SRV, FIRST, "  if (typeof value === 'string' && /^[A-Za-z]+$/.test(value)) return 0;\n" + FIRST)]
V['R-1.8'] = [(SRV, FIRST, "  if (value === '') return 0;\n" + FIRST)]
V['R-1.9'] = [(SRV, "port >= 1 &&", "port >= 0 &&")]
V['R-1.10'] = [(SRV, "port <= 65535 ?", "port <= 99999 ?")]
V['R-1.11'] = [(SRV, FIRST, "  if (typeof value !== 'string' || !/^-?\\d+$/.test(value)) return DEFAULT_PORT;"),
               (SRV, "  const port = Number(value);", "  const port = Math.abs(Number(value));")]
V['R-1.12'] = [(SRV, FIRST, "  if (typeof value !== 'string' || !/^\\d+(\\.\\d+)?$/.test(value)) return DEFAULT_PORT;"),
               (SRV, "  const port = Number(value);", "  const port = Math.floor(Number(value));")]
V['R-1.13'] = [(SRV, "      process.exit(1);", "      process.exit(0);")]
V['R-1.14'] = [(SRV, "      console.error(`Battleship could not start: port ${port} is already in use`);\n", "")]
V['R-1.15'] = [(SRV, "  server.listen(port, '127.0.0.1', () => {", "  server.listen(port, () => {")]
V['R-1.16'] = [(SRV, "    console.log(`Battleship listening on http://localhost:${port}`);", "    console.log('Battleship is up');")]

# ---------------- R-2: page ----------------
V['R-2.1'] = [(SRV, "'text/html; charset=utf-8'", "'text/html'")]
V['R-2.2'] = [(IDX, "<title>Battleship</title>", "<title>Battleship Game</title>")]
V['R-2.3'] = [(SRV, "      squares.push(`<button class=\"cell\"", "      if (row === 9 && col === 9) continue;\n      squares.push(`<button class=\"cell\"")]
V['R-2.4'] = [(SRV, "data-row=\"${row}\" data-col=\"${col}\"", "data-row=\"${Math.min(row, 8)}\" data-col=\"${col}\"")]
V['R-2.5'] = [(SRV, "for (let row = 0; row < BOARD_SIZE; row += 1) {", "for (let row = BOARD_SIZE - 1; row >= 0; row -= 1) {")]
V['R-2.6'] = [(SRV, "        + ` aria-label=\"Row ${row + 1}, column ${col + 1}\">?</button>`);", "        + `>?</button>`);")]
V['R-2.7'] = [(IDX, "<title>Battleship</title>", "<title>Battleship</title>\n<link rel=\"stylesheet\" href=\"https://cdn.invalid/battleship.css\">")]
V['R-2.8'] = [(IDX, '<p id="status" role="status" aria-live="polite">', '<p id="status" aria-live="polite">')]
V['R-2.9'] = [(IDX, '<button id="new-game" type="button">New game</button>', '<button id="new-game" type="button">Restart</button>')]
FETCH = "      const response = await fetch('/api/fire', {"
V['R-2.10'] = [(IDX, FETCH, "      fetch('/api/fire', { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ game: document.body.dataset.game, row: Number(square.dataset.row), col: Number(square.dataset.col) }) }).catch(() => {});\n" + FETCH)]
V['R-2.11'] = [(IDX, "      square.dataset.result = outcome.result;\n      square.textContent = MARKS[outcome.result];",
                     "      const shown = outcome.result === 'sunk' ? 'hit' : outcome.result;\n      square.dataset.result = shown;\n      square.textContent = MARKS[shown];"),
               (IDX, "`${squareName(square)}, ${outcome.result}`", "`${squareName(square)}, ${shown}`")]
V['R-2.12'] = [(IDX, '<p>Ships remaining: <span id="remaining">5</span></p>', '<p hidden>Ships remaining: <span id="remaining">5</span></p>')]
V['R-2.13'] = [(IDX, "      remaining.textContent = String(outcome.shipsRemaining);", "      if (outcome.result !== 'sunk') remaining.textContent = String(outcome.shipsRemaining);")]
V['R-2.14'] = [(IDX, "        say(`${squareName(square)}: ${outcome.result}. `\n          + `${shipCount(outcome.shipsRemaining)} remaining.`);", "        say(`${squareName(square)} fired. ${shipCount(outcome.shipsRemaining)} remaining.`);")]
V['R-2.15'] = [(IDX, " || square.dataset.result !== undefined) return;", ") return;")]
V['R-2.16'] = [(IDX, "if (closed || inFlight || grid.dataset.locked === 'true' || square.dataset.result !== undefined) return;", "if (closed || square.dataset.result !== undefined) return;"),
               (IDX, "    setLocked(true);\n    setBusy(true);\n    say(`Firing at", "    setBusy(true);\n    say(`Firing at")]
V['R-2.17'] = [(IDX, "        closed = true;\n        say('All five ships are sunk. You win! Choose New game to play again.');\n        setLocked(true);", "        say('All five ships are sunk. You win! Choose New game to play again.');\n        setLocked(false);")]
CATCH = "      say(`${squareName(square)}: the shot did not reach the server (${error.message}).`);\n      setLocked(false);"
V['R-2.18'] = [(IDX, CATCH, "      setLocked(false);")]
V['R-2.19'] = [(IDX, CATCH, "      say(`${squareName(square)}: the shot did not reach the server (${error.message}).`);")]
V['R-2.20'] = [(IDX, "'All five ships are sunk. You win! Choose New game to play again.'", "'You win! Choose New game to play again.'")]
V['R-2.21'] = [(IDX, "        closed = true;\n", "        closed = true;\n        newGame.disabled = true;\n")]
V['R-2.22'] = [(IDX, "      for (const square of squares) clear(square);\n", "")]
V['R-2.23'] = [(IDX, "      remaining.textContent = String(started.ships);\n", "")]
V['R-2.24'] = [(SRV, "data-row=\"${row}\" data-col=\"${col}\"", "data-row=\"${row}\" data-col=\"${col}\" tabindex=\"-1\"")]
V['R-2.25'] = [(IDX, ".cell:focus-visible { outline: 3px solid #b34700; outline-offset: 1px; }", ".cell:focus-visible { outline: none; }")]
V['R-2.26'] = [(IDX, "      square.textContent = MARKS[outcome.result];", "      square.textContent = '';"),
               (IDX, "      square.setAttribute('aria-label', `${squareName(square)}, ${outcome.result}`);", "      square.setAttribute('aria-label', squareName(square));")]
V['R-2.27'] = [(IDX, "      remaining.textContent = String(outcome.shipsRemaining);\n", "      remaining.textContent = String(outcome.shipsRemaining);\n      square.blur();\n")]
V['R-2.28'] = [(IDX, "    if (inFlight) return;\n", "")]
V['R-2.29'] = [(IDX, "        say(`Could not start a game: ${failureText(started, response)}. Choose New game to try again.`);\n        setLocked(wasClosed || !hadGame);\n        return;",
                     "        say(`Could not start a game: ${failureText(started, response)}. Choose New game to try again.`);\n        closed = false;\n        setLocked(false);\n        return;")]
V['R-2.30'] = [(IDX, "      if (outcome === null || typeof outcome.gameOver !== 'boolean'\n          || !Number.isInteger(outcome.shipsRemaining) || outcome.shipsRemaining < 0\n          || outcome.gameOver !== (outcome.shipsRemaining === 0)\n          || !Object.hasOwn(MARKS, outcome.result)) {", "      if (outcome === null) {")]

# ---------------- R-3: placement ----------------
V['R-3.1'] = [(BAT, "  { name: 'destroyer', length: 2 },\n", "")]
V['R-3.2'] = [(BAT, "{ name: 'destroyer', length: 2 }", "{ name: 'destroyer', length: 3 }")]
V['R-3.3'] = [(BAT, "if (cellRow >= BOARD_SIZE || cellCol >= BOARD_SIZE) return null;", "if (cellRow > BOARD_SIZE || cellCol > BOARD_SIZE) return null;")]
V['R-3.4'] = [(BAT, "const cellCol = horizontal ? col + offset : col;", "const cellCol = horizontal ? col + offset : col + (offset > 0 ? 1 : 0);")]
V['R-3.5'] = [(BAT, "if (drawn !== null && !drawn.some((cell) => taken.has(key(cell.row, cell.col)))) {", "if (drawn !== null) {")]
V['R-3.6'] = [(BAT, "!drawn.some((cell) => taken.has(key(cell.row, cell.col)))", "!drawn.some((cell) => [[0, 0], [1, 0], [-1, 0], [0, 1], [0, -1]].some(([dr, dc]) => taken.has(key(cell.row + dr, cell.col + dc))))")]
V['R-3.7'] = [(BAT, "const horizontal = random() < 0.5;", "const horizontal = Math.random() < 0.5;")]
LCG = "(() => { let a = 12345; return () => { a = (a * 1664525 + 1013904223) % 4294967296; return a / 4294967296; }; })()"
V['R-3.8'] = [(BAT, "  return { fleet: placeFleet(random), shots: new Map(), over: false };", "  placeFleet(random);\n  return { fleet: placeFleet(" + LCG + "), shots: new Map(), over: false };")]
V['R-3.9'] = [(BAT, "const PLACEMENT_ATTEMPTS = 200;", "const PLACEMENT_ATTEMPTS = 5000;")]
V['R-3.10'] = [(BAT, "      throw new Error('could not place ' + spec.name + ' after ' + PLACEMENT_ATTEMPTS +\n        ' attempts: placement failed');", "      throw 'could not place ' + spec.name + ' after ' + PLACEMENT_ATTEMPTS + ' attempts: placement failed';")]
V['R-3.11'] = [(BAT, "      throw new Error('could not place ' + spec.name + ' after ' + PLACEMENT_ATTEMPTS +\n        ' attempts: placement failed');", "      throw new Error('no room for ' + spec.name);")]
V['R-3.12'] = [(BAT, "      throw new Error('could not place ' + spec.name + ' after ' + PLACEMENT_ATTEMPTS +\n        ' attempts: placement failed');", "      cells = Array.from({ length: spec.length }, (_, i) => ({ row: 0, col: i }));")]
V['R-3.13'] = [(SRV, "const MAX_BODY_BYTES = 1024 * 1024;", "const MAX_BODY_BYTES = 1024 * 1024;\nconst fixedRandom = () => { let a = 12345; return () => { a = (a * 1664525 + 1013904223) % 4294967296; return a / 4294967296; }; };"),
                (SRV, "        game = createGame({ random });", "        game = createGame({ random: random === Math.random ? fixedRandom() : random });")]
NEW200 = "      sendJson(response, 200, { game: id, size: BOARD_SIZE, ships: FLEET.length });"
V['R-3.14'] = [(SRV, NEW200, "      sendJson(response, 200, { game: id, size: BOARD_SIZE, ships: FLEET.length, fleet: game.fleet });")]
V['R-3.15'] = [(SRV, "  const games = new Map();", "  const games = new Map();\n  let lastGame = null;"),
               (SRV, "      games.set(id, game);", "      games.set(id, game);\n      lastGame = game;"),
               (SRV, "    response.end(PAGE.replace(GRID_PLACEHOLDER, () => renderGrid()));", "    response.end(PAGE.replace(GRID_PLACEHOLDER, () => renderGrid()).replace('</body>', () => '<script>window.fleet = ' + JSON.stringify(lastGame ? lastGame.fleet : []) + ';</script></body>'));")]
V['R-3.16'] = [(SRV, "      sendJson(response, 200, outcome);", "      sendJson(response, 200, { ...outcome, fired: game.shots.size });")]

# ---------------- R-4: /api/new ----------------
V['R-4.1'] = [(SRV, NEW200, "      sendJson(response, 201, { game: id, size: BOARD_SIZE, ships: FLEET.length });")]
V['R-4.2'] = [(SRV, NEW200, "      response.writeHead(200, { 'content-type': 'text/plain' });\n      response.end(JSON.stringify({ game: id, size: BOARD_SIZE, ships: FLEET.length }));")]
V['R-4.3'] = [(SRV, NEW200, "      sendJson(response, 200, { game: id, size: BOARD_SIZE, ships: FLEET.length, version: 1 });")]
V['R-4.4'] = [(SRV, NEW200, "      sendJson(response, 200, { game: id, size: BOARD_SIZE * BOARD_SIZE, ships: FLEET.length });")]
V['R-4.5'] = [(SRV, NEW200, "      sendJson(response, 200, { game: id, size: BOARD_SIZE, ships: FLEET.length + 1 });")]
V['R-4.6'] = [(SRV, "      const id = crypto.randomUUID();", "      const id = crypto.randomUUID().toUpperCase();")]
V['R-4.7'] = [(SRV, "const MAX_BODY_BYTES = 1024 * 1024;", "const MAX_BODY_BYTES = 1024 * 1024;\nconst SHARED_ID = crypto.randomUUID();"),
              (SRV, "      const id = crypto.randomUUID();", "      const id = SHARED_ID;")]
V['R-4.8'] = [(SRV, "      const game = games.get(shot.game);", "      const known = games.get(shot.game);\n      const game = known === undefined ? undefined : createGame();")]

# ---------------- R-5: fire ----------------
V['R-5.1'] = [(SRV, "outcome = fire(game, shot.row, shot.col);", "outcome = fire(game, shot.col, shot.row);")]
V['R-5.2'] = [(BAT, "    result = afloat.length === 1 ? 'sunk' : 'hit';", "    result = 'sunk';")]
V['R-5.3'] = [(BAT, "    result = afloat.length === 1 ? 'sunk' : 'hit';", "    result = 'hit';")]
V['R-5.4'] = [(BAT, "  let result = 'miss';", "  let result = 'hit';")]
V['R-5.5'] = [(SRV, "      sendJson(response, 200, outcome);", "      sendJson(response, 200, { ...outcome, gameOver: String(outcome.gameOver) });")]
V['R-5.6'] = [(SRV, "value >= 0 && value < BOARD_SIZE;", "value >= 0 && value < BOARD_SIZE - 1;")]
COORD = "      if (!isCoordinate(shot.row) || !isCoordinate(shot.col)) {"
V['R-5.7'] = [(SRV, COORD, "      if (!(Number.isInteger(shot.row) && shot.row < BOARD_SIZE) || !isCoordinate(shot.col)) {")]
V['R-5.8'] = [(SRV, COORD, "      if (!(Number.isInteger(shot.row) && shot.row >= 0) || !isCoordinate(shot.col)) {")]
V['R-5.9'] = [(SRV, COORD, "      if (!isCoordinate(shot.row) || !(Number.isInteger(shot.col) && shot.col < BOARD_SIZE)) {")]
V['R-5.10'] = [(SRV, COORD, "      if (!isCoordinate(shot.row) || !(Number.isInteger(shot.col) && shot.col >= 0)) {")]
V['R-5.11'] = [(SRV, "        sendJson(response, 409, { error: error.message });", "        sendJson(response, error.code === 'already-fired' ? 400 : 409, { error: error.message });")]
V['R-5.12'] = [(BAT, "  if (game.shots.has(cellKey)) {\n", "  if (game.shots.has(cellKey)) {\n    game.shots.delete(cellKey);\n")]

# ---------------- R-6: game over ----------------
RET = "  return { result, gameOver: game.over, shipsRemaining: remaining };"
V['R-6.1'] = [(BAT, "  if (remaining === 0) game.over = true;", "  if (remaining <= 1) game.over = true;")]
V['R-6.2'] = [(BAT, "  if (remaining === 0) game.over = true;", "  if (remaining === -1) game.over = true;")]
V['R-6.3'] = [(BAT, RET, "  return { result, gameOver: game.over, shipsRemaining: remaining + (result === 'sunk' && ship.length === 2 ? 1 : 0) };")]
V['R-6.4'] = [(BAT, RET, "  return { result, gameOver: game.over, shipsRemaining: result === 'hit' ? remaining - 1 : remaining };")]
V['R-6.5'] = [(BAT, "  if (game.over) {\n    const error", "  if (false && game.over) {\n    const error")]
V['R-6.6'] = [(BAT, "    error.code = 'game-over';\n", "    error.code = 'game-over';\n    game.over = false;\n")]

# ---------------- R-7: errors ----------------
V['R-7.1'] = [(SRV, "sendJson(response, 400, { error: 'the request body is not valid JSON' });", "sendJson(response, 500, { error: 'the request body is not valid JSON' });")]
GAMECHK = "      if (typeof shot.game !== 'string' || shot.game === '') {"
V['R-7.2'] = [(SRV, GAMECHK, "      if (shot.game !== undefined && (typeof shot.game !== 'string' || shot.game === '')) {")]
V['R-7.3'] = [(SRV, GAMECHK, "      if (shot.game === undefined || shot.game === '' || shot.game === null) {")]
V['R-7.4'] = [(SRV, GAMECHK, "      if (typeof shot.game !== 'string') {")]
V['R-7.5'] = [(SRV, COORD, "      if (!(Number.isFinite(shot.row) && shot.row >= 0 && shot.row < BOARD_SIZE) || !isCoordinate(shot.col)) {")]
V['R-7.6'] = [(SRV, COORD, "      if (!isCoordinate(Number(shot.row)) || !isCoordinate(shot.col)) {")]
V['R-7.7'] = [(SRV, COORD, "      if (!isCoordinate(shot.row) || !(Number.isFinite(shot.col) && shot.col >= 0 && shot.col < BOARD_SIZE)) {")]
V['R-7.8'] = [(SRV, COORD, "      if (!isCoordinate(shot.row) || !isCoordinate(Number(shot.col))) {")]
NOGAME = "        sendJson(response, 404, { error: 'no game with that id' });"
V['R-7.9'] = [(SRV, NOGAME, "        sendJson(response, /^[0-9a-f]{8}-[0-9a-f]{4}-/.test(shot.game) ? 400 : 404, { error: 'no game with that id' });")]
V['R-7.10'] = [(SRV, NOGAME, "        sendJson(response, /^[0-9a-f]{8}-[0-9a-f]{4}-/.test(shot.game) ? 404 : 400, { error: 'no game with that id' });")]
V['R-7.11'] = [(SRV, "const MAX_BODY_BYTES = 1024 * 1024;", "const MAX_BODY_BYTES = Infinity;")]
V['R-7.12'] = [(SRV, "const MAX_BODY_BYTES = 1024 * 1024;", "const MAX_BODY_BYTES = 64 * 1024;")]
WM = "    if (request.method !== method) {"
V['R-7.13'] = [(SRV, WM, "    if (request.method !== method && !(pathname === '/api/fire' && request.method === 'GET')) {")]
V['R-7.14'] = [(SRV, WM, "    if (request.method !== method && !(pathname === '/api/new' && request.method === 'POST')) {")]
V['R-7.15'] = [(SRV, WM, "    if (request.method !== method && !(pathname === '/' && request.method === 'POST')) {")]
V['R-7.16'] = [(SRV, "      pathname = new URL(request.url, 'http://localhost').pathname;", "      const u = new URL(request.url, 'http://localhost');\n      pathname = u.pathname + u.search;")]
V['R-7.17'] = [(SRV, "    const method = ROUTE_METHODS.get(pathname);", "    const method = ROUTE_METHODS.get(pathname.length > 1 ? pathname.replace(/\\/$/, '') : pathname);")]
V['R-7.18'] = [(SRV, "  ['/api/fire', 'POST'],", "  ['/api', 'GET'],\n  ['/api/fire', 'POST'],")]
V['R-7.19'] = [(SRV, "      sendJson(response, 404, { error: `no route for ${pathname}` });", "      if (request.method === 'GET') {\n        response.writeHead(200, { 'content-type': 'text/html; charset=utf-8' });\n        response.end(PAGE.replace(GRID_PLACEHOLDER, () => renderGrid()));\n        return;\n      }\n      sendJson(response, 404, { error: `no route for ${pathname}` });")]
M405 = "      sendJson(response, 405, { error: `method ${request.method} is not allowed on ${pathname}` });"
V['R-7.20'] = [(SRV, M405, "      sendJson(response, 405, { message: `method ${request.method} is not allowed on ${pathname}` });")]
V['R-7.21'] = [(SRV, M405, "      response.writeHead(405, { 'content-type': 'text/plain' });\n      response.end(JSON.stringify({ error: `method ${request.method} is not allowed on ${pathname}` }));")]
V['R-7.22'] = [(SRV, "        sendJson(response, 400, { error: 'the request body is not valid JSON' });\n        return;", "        sendJson(response, 400, { error: 'the request body is not valid JSON' });\n        setImmediate(() => { throw new Error('boom'); });\n        return;")]
V['R-7.23'] = [(SRV, "      error.status = 413;\n      reject(error);", "      error.status = 413;\n      reject(error);\n      setTimeout(() => { throw new Error('boom'); }, 30);")]
V['R-7.24'] = [(SRV, "    let pathname;\n    try {\n      pathname = new URL(request.url, 'http://localhost').pathname;\n    } catch {\n      sendJson(response, 400, { error: 'the request target is not a URL path' });\n      return;\n    }", "    const pathname = new URL(request.url, 'http://localhost').pathname;")]
V['R-7.25'] = [(SRV, None, None, 'special')]  # filled by the generator (multi-line try/catch removal)

# ---------------- R-8 ----------------
V['R-8.1'] = [(BAT, "module.exports = { BOARD_SIZE, FLEET, createGame, fire, shipsRemaining, isOver };", "module.exports = { BOARD_SIZE, FLEET, createGame, fire, shipsRemaining, isOver };\nrequire('node:http').createServer(() => {}).listen(0, '127.0.0.1').unref();")]

# ---------------- R-10 ----------------
V['R-10.1'] = [(IDX, "  startGame();\n</script>", "</script>")]
V['R-10.2'] = [(IDX, "      remaining.textContent = String(started.ships);", "      remaining.textContent = sessionStorage.getItem('remaining') || String(started.ships);"),
               (IDX, "      remaining.textContent = String(outcome.shipsRemaining);\n", "      remaining.textContent = String(outcome.shipsRemaining);\n      sessionStorage.setItem('remaining', String(outcome.shipsRemaining));\n")]
V['R-10.3'] = [(IDX, "    if (inFlight) return;\n", "    if (!window.__booted) {\n      window.__booted = true;\n      const saved = sessionStorage.getItem('game');\n      if (saved) { document.body.dataset.game = saved; say('Resuming your game.'); setLocked(false); return; }\n    }\n    if (inFlight) return;\n"),
               (IDX, "      document.body.dataset.game = started.game;", "      document.body.dataset.game = started.game;\n      sessionStorage.setItem('game', started.game);")]
V['R-10.4'] = [(IDX, "    say(`Firing at ${squareName(square)}…`);", "    say(`Firing at ${squareName(square)}…`);\n    square.dataset.result = 'miss';\n    square.textContent = 'M';")]
V['R-10.5'] = [(SRV, "const MAX_BODY_BYTES = 1024 * 1024;", "const MAX_BODY_BYTES = 1024 * 1024;\nconst GAMES_FILE = path.join(__dirname, 'games.json');\nfunction loadGames() {\n  const games = new Map();\n  try {\n    for (const [id, g] of JSON.parse(fs.readFileSync(GAMES_FILE, 'utf8'))) games.set(id, { fleet: g.fleet, shots: new Map(g.shots), over: g.over });\n  } catch { /* none yet */ }\n  return games;\n}\nfunction saveGames(games) {\n  fs.writeFileSync(GAMES_FILE, JSON.stringify([...games].map(([id, g]) => [id, { fleet: g.fleet, shots: [...g.shots], over: g.over }])));\n}"),
               (SRV, "  const games = new Map();\n  return http.createServer", "  const games = loadGames();\n  return http.createServer"),
               (SRV, "      games.set(id, game);", "      games.set(id, game);\n      saveGames(games);"),
               (SRV, "      sendJson(response, 200, outcome);", "      saveGames(games);\n      sendJson(response, 200, outcome);")]
V['R-10.6'] = [(IDX, "? `${squareName(square)}: ${failureText(outcome, response)}. Choose New game to try again.`", "? ''")]
V['R-10.7'] = [(IDX, "      if (!response.ok) {\n", "      if (!response.ok) {\n        if (response.status === 404) newGame.disabled = true;\n")]
KEYLINE = "const key = (row, col) => row + ',' + col;"
V['R-10.8'] = [(BAT, KEYLINE, KEYLINE + "\nconst FIRED_EVER = new Set();"),
               (BAT, "  if (game.shots.has(cellKey)) {", "  if (game.shots.has(cellKey) || FIRED_EVER.has(cellKey)) {"),
               (BAT, "  game.shots.set(cellKey, result);", "  game.shots.set(cellKey, result);\n  FIRED_EVER.add(cellKey);")]
V['R-10.9'] = [(BAT, KEYLINE, KEYLINE + "\nlet ANY_OVER = false;"),
               (BAT, "  if (game.over) {\n    const error", "  if (game.over || ANY_OVER) {\n    const error"),
               (BAT, "  if (remaining === 0) game.over = true;", "  if (remaining === 0) { game.over = true; ANY_OVER = true; }")]
V['R-10.10'] = [(SRV, "    .then((raw) => {", "    .then(async (raw) => {"),
                (SRV, "        outcome = fire(game, shot.row, shot.col);", "        const snap = { fleet: game.fleet, shots: new Map(game.shots), over: game.over };\n        await new Promise((resolve) => setTimeout(resolve, 40));\n        outcome = fire(snap, shot.row, shot.col);\n        game.shots = snap.shots;\n        game.over = snap.over;")]
V['R-10.11'] = V['R-5.12']
