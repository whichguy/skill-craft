# Variant table: condition id -> list of (file, old, new). Every `old` must occur exactly once in the copy.
S, R = "server.js", "rules.js"
SEND_NEW = "sendJson(response, 200, { game: id });"
FIRE_OK = "sendJson(response, 200, { result: shot.result, gameOver: shot.gameOver });"
RANGE = "if (!Number.isInteger(row) || row < 0 || row > 9 || !Number.isInteger(col) || col < 0 || col > 9) {"
REPEAT = "  if (shots.has(key)) {\n    return { result: shots.get(key), gameOver: fleetSunk(game, shots) };\n  }\n"
SHOT_ERR = "    if (shot === undefined) {\n      sendJson(response, 400, { error: 'invalid shot' });"
BTN = "      buttons += '<button type=\"button\" data-row=\"' + row + '\" data-col=\"' + col\n        + '\" aria-label=\"' + name + '\">' + name + '</button>';"
OVER_BEFORE_ANCHOR = "  let ship = null;\n  for (const candidate of game.ships) {"
FINAL_RET = "  return { result, gameOver: fleetSunk(game, shots) };"
CLASH = "        if (occupied.has(key)) {\n          clash = true;\n        }\n"
FLEET_ORDER = "  ['Cruiser', 3],\n  ['Submarine', 3],\n  ['Destroyer', 2],"
PARSE_RET = "  return { kind: 'ok', game: parsed.game, row: parsed.row, col: parsed.col };"
GAME_CHECK = "  if (typeof parsed.game !== 'string' || parsed.game.length === 0) {\n    return { kind: 'shot' };\n  }"
NOTOBJ = "  if (parsed === null || typeof parsed !== 'object' || Array.isArray(parsed)) {"
LISTEN_PORT = "    throw new Error('PORT must be an integer from 1 to 65535; received ' + port);\n  }\n  return port;"
EMPTY = "  if (raw === undefined || raw === '') {"
GUARD = "  if (gameId === '') {\n    if (statusLine.textContent !== 'The game did not start.') {\n      setStatus('The game is not ready.');\n    }\n    return;\n  }"
GAMES = "const games = new Map();\n"
PERSIST_LOADER = """const games = new Map();
const fs = require('node:fs');
const STORE = require('node:path').join(__dirname, '.games.json');
function saveGames() {
  fs.writeFileSync(STORE, JSON.stringify([...games].map(([id, g]) => [id, { ships: g.ships, shots: g.shots ? [...g.shots] : [] }])));
}
try {
  for (const [id, g] of JSON.parse(fs.readFileSync(STORE, 'utf8'))) {
    games.set(id, { ships: g.ships, shots: new Map(g.shots) });
  }
} catch (error) {
  // no store yet
}
"""
FLEET_SUNK = """function fleetSunk(game, shots) {
  for (const ship of game.ships) {
    for (const [cellRow, cellCol] of ship.cells) {
      if (!shots.has(cellRow + ',' + cellCol)) {
        return false;
      }
    }
  }
  return true;
}"""
FLEET_SUNK_EARLY = """function fleetSunk(game, shots) {
  let open = 0;
  for (const ship of game.ships) {
    for (const [cellRow, cellCol] of ship.cells) {
      if (!shots.has(cellRow + ',' + cellCol)) {
        open += 1;
      }
    }
  }
  return open <= 1;
}"""

MUT = {
 "R-1.1": [(S, "server.listen(port, '127.0.0.1');", "// server.listen(port, '127.0.0.1');")],
 "R-2.1": [(S, LISTEN_PORT, "    throw new Error('PORT must be an integer from 1 to 65535; received ' + port);\n  }\n  if (port < 4000) {\n    return 3000;\n  }\n  return port;")],
 "R-2.2": [(S, EMPTY + "\n    return 3000;\n  }", "  if (raw === undefined) {\n    return 3001;\n  }\n  if (raw === '') {\n    return 3000;\n  }")],
 "R-2.3": [(S, EMPTY, "  if (raw === undefined) {")],
 "R-2.4": [(S, "if (port < 1 || port > 65535) {", "if (port < 0 || port > 65535) {")],
 "R-2.5": [(S, "  const port = Number(raw);\n", "  const port = Number(raw);\n  if (port < 0) {\n    return 3000;\n  }\n")],
 "R-2.6": [(S, "if (port < 1 || port > 65535) {", "if (port > 65535) {\n    return 3000;\n  }\n  if (port < 1) {")],
 "R-2.7": [(S, "  if (!/^-?\\d+$/.test(raw)) {", "  if (!/^-?\\d+$/.test(raw)) {\n    return 3000;\n  }\n  if (!/^-?\\d+$/.test(raw)) {")],
 "R-3.1": [(S, "send(response, 200, 'text/html; charset=utf-8', pageHtml());", "send(response, 201, 'text/html; charset=utf-8', pageHtml());")],
 "R-3.2": [(S, "send(response, 200, 'text/html; charset=utf-8', pageHtml());", "send(response, 200, 'text/plain; charset=utf-8', pageHtml());")],
 "R-3.3": [(S, "<title>Battleship</title>", "<title>Battleship Game</title>")],
 "R-3.4": [(S, "+ buttons + '</div>'", "+ buttons + '<button type=\"button\" data-row=\"0\" data-col=\"0\" aria-label=\"row 0 column 0\">row 0 column 0</button></div>'")],
 "R-3.5": [(S, "  return 'row ' + row + ' column ' + col;\n}\n\n// One static", "  return row === 3 && col === 4 ? 'row 4 column 3' : 'row ' + row + ' column ' + col;\n}\n\n// One static")],
 "R-3.6": [(S, "+ '<script>' + clientScript + '</script></body></html>';", "+ '<script>window.fleet=[[0,0],[0,1],[0,2],[0,3],[0,4]];</script><script>' + clientScript + '</script></body></html>';")],
 "R-3.7": [(S, BTN, "      buttons += '<button type=\"button\" data-row=\"' + row + '\" data-col=\"' + col\n        + '\" aria-label=\"' + name + '\"' + (row === 0 && col === 0 ? ' title=\"Carrier\"' : '') + '>' + name + '</button>';")],
 "R-3.8": [(S, "body: JSON.stringify({ game: gameId, row: row, col: col }),", "body: JSON.stringify({ game: gameId, row: col, col: row }),")],
 "R-3.9": [(S, "    shown = 'Sunk';", "    shown = 'Hit';")],
 "R-3.10": [(S, "showCell(button, 'Pending');", "showCell(button, 'Miss');")],
 "R-3.11": [(S, "    button.dataset.shot = '';\n", "")],
 "R-3.12": [(S, "    setStatus('The shot did not land.');\n", "")],
 "R-3.13": [(S, "\nstartGame();\n`;", "\n`;")],
 "R-3.14": [(S, GUARD, GUARD.replace("    return;\n  }", "  }"))],
 "R-3.15": [(S, "buttons += '<button type=\"button\" data-row=\"'", "buttons += '<span role=\"button\" data-row=\"'"),
            (S, "+ name + '</button>';", "+ name + '</span>';"),
            (S, "document.querySelectorAll('button')", "document.querySelectorAll('[data-row]')")],
 "R-3.16": [(S, "    games.set(id, placed);\n", "    games.set(id, placed);\n    request.socket.once('close', () => games.delete(id));\n")],
 "R-4.1": [(S, SEND_NEW, "sendJson(response, 201, { game: id });")],
 "R-4.2": [(S, SEND_NEW, "send(response, 200, 'text/plain; charset=utf-8', JSON.stringify({ game: id }));")],
 "R-4.3": [(S, SEND_NEW, "sendJson(response, 200, { game: id, version: 1 });")],
 "R-4.4": [(S, SEND_NEW, "sendJson(response, 200, { game: Number.parseInt(id.slice(0, 8), 16) });")],
 "R-4.5": [(S, "const id = crypto.randomUUID();", "const id = 'game';")],
 "R-4.6": [(S, "response.writeHead(405, {", "response.writeHead(400, {")],
 "R-4.7": [(S, "  if (request.method === 'POST' && path === '/api/new') {\n", "  if (request.method === 'POST' && path === '/api/new') {\n    games.set(crypto.randomUUID(), placeFleet(serverRandom));\n")],
 "R-4.8": [(S, SEND_NEW, "sendJson(response, 200, { game: id, board: placed.ships.map((ship) => ship.cells) });")],
 "R-4.9": [(R, FLEET_ORDER, "  ['Cruiser', 2],\n  ['Submarine', 3],\n  ['Destroyer', 3],")],
 "R-4.10": [(R, "['Submarine', 3],", "['Sub', 3],")],
 "R-4.11": [(R, "const cellRow = horizontal ? row : row + offset;", "const cellRow = horizontal ? row + (length === 2 ? offset : 0) : row + offset;")],
 "R-4.12": [(R, "const colMax = horizontal ? 10 - length : 9;", "const colMax = horizontal ? 11 - length : 9;")],
 "R-4.13": [(R, CLASH, "")],
 "R-4.14": [(R, "if (occupied.has(key)) {", "if (occupied.has(key) || [[-1, 0], [1, 0], [0, -1], [0, 1]].some(([dr, dc]) => occupied.has((cellRow + dr) + ',' + (cellCol + dc)))) {")],
 "R-4.15": [(S, "  if (request.method === 'GET' && path === '/api/new') {\n    const placed", "  if (request.method === 'GET' && path === '/api/new') {\n    const raw = await readBody(request);\n    if (raw === '') {\n      sendJson(response, 400, { error: 'invalid JSON' });\n      return;\n    }\n    const placed")],
 "R-4.16": [(R, FLEET_ORDER, "  ['Submarine', 3],\n  ['Cruiser', 3],\n  ['Destroyer', 2],")],
 "R-4.17": [(R, "      const row = Math.floor(random() * (rowMax + 1));\n      const col = Math.floor(random() * (colMax + 1));", "      const col = Math.floor(random() * (colMax + 1));\n      const row = Math.floor(random() * (rowMax + 1));")],
 "R-4.18": [(R, "random() < 0.5", "random() <= 0.5")],
 "R-4.19": [(R, "const rowMax = horizontal ? 9 : 10 - length;", "const rowMax = horizontal ? 8 : 10 - length;")],
 "R-4.20": [(R, "const rowMax = horizontal ? 9 : 10 - length;", "const rowMax = horizontal ? 9 : 9 - length;")],
 "R-4.21": [(R, "const colMax = horizontal ? 10 - length : 9;", "const colMax = horizontal ? 9 - length : 9;")],
 "R-4.22": [(R, "const colMax = horizontal ? 10 - length : 9;", "const colMax = horizontal ? 10 - length : 8;")],
 "R-4.23": [(R, "Math.floor(random() * (rowMax + 1))", "Math.floor(random() * rowMax)"), (R, "Math.floor(random() * (colMax + 1))", "Math.floor(random() * colMax)")],
 "R-4.24": [(R, "const cellCol = horizontal ? col + offset : col;", "const cellCol = horizontal ? col + (length - 1 - offset) : col;")],
 "R-4.25": [(R, "const cellRow = horizontal ? row : row + offset;", "const cellRow = horizontal ? row : row + (length - 1 - offset);")],
 "R-4.26": [(R, "    let cells = null;\n    while (cells === null) {\n      const horizontal = random() < 0.5;\n", "    let cells = null;\n    const horizontal = random() < 0.5;\n    while (cells === null) {\n")],
 "R-4.27": [(S, "const placed = placeFleet(serverRandom);", "const placed = (globalThis.sharedFleet = globalThis.sharedFleet || placeFleet(serverRandom));")],
 "R-4.28": [(S, "const shot = fireShot(stored, parsed.row, parsed.col);", "const shot = fireShot({ ships: stored.ships }, parsed.row, parsed.col);")],
 "R-4.29": [(S, GAMES, PERSIST_LOADER), (S, "    games.set(id, placed);\n", "    games.set(id, placed);\n    saveGames();\n"), (S, FIRE_OK, "saveGames();\n    " + FIRE_OK)],
 "R-5.1": [(R, "result = open ? 'hit' : 'sunk';", "result = open ? 'hit' : 'sank';")],
 "R-5.2": [(S, FIRE_OK, "sendJson(response, 200, shot.gameOver ? { result: shot.result, gameOver: true } : { result: shot.result });")],
 "R-5.3": [(R, "result = open ? 'hit' : 'sunk';", "result = open ? (ship.label === 'Submarine' ? 'miss' : 'hit') : 'sunk';")],
 "R-5.4": [(R, "result = open ? 'hit' : 'sunk';", "result = open || ship.label === 'Destroyer' ? 'hit' : 'sunk';")],
 "R-5.5": [(R, "let result = 'miss';", "let result = col === 9 ? 'hit' : 'miss';")],
 "R-5.6": [(R, FLEET_SUNK, FLEET_SUNK_EARLY)],
 "R-5.7": [(R, OVER_BEFORE_ANCHOR, "  const overBefore = fleetSunk(game, shots);\n" + OVER_BEFORE_ANCHOR), (R, FINAL_RET, "  return { result, gameOver: overBefore };")],
 "R-5.8": [(R, OVER_BEFORE_ANCHOR, "  const overBefore = fleetSunk(game, shots);\n" + OVER_BEFORE_ANCHOR), (R, FINAL_RET, "  return { result, gameOver: fleetSunk(game, shots) && !overBefore };")],
 "R-5.9": [(R, REPEAT, "  if (shots.has(key)) {\n    for (const other of game.ships) {\n      if (other.cells.some(([cr, cc]) => cr === row && cc === col)) {\n        other.hits = (other.hits || 0) + 1;\n      }\n    }\n    return { result: shots.get(key), gameOver: fleetSunk(game, shots) };\n  }\n"),
           (R, "result = open ? 'hit' : 'sunk';", "ship.hits = (ship.hits || 0) + 1;\n    result = open && ship.hits < ship.cells.length ? 'hit' : 'sunk';")],
 "R-5.10": [(R, REPEAT, "")],
 "R-5.11": [(R, "return { result: shots.get(key), gameOver: fleetSunk(game, shots) };", "return { result: shots.get(key), gameOver: false };")],
 "R-5.12": [(R, "let result = 'miss';", "let result = fleetSunk(game, shots) ? 'hit' : 'miss';")],
 "R-5.13": [(S, SHOT_ERR, "    if (shot === undefined) {\n      fireShot(stored, Math.min(9, Math.max(0, Math.trunc(Number(parsed.row)))), Math.min(9, Math.max(0, Math.trunc(Number(parsed.col)))));\n      sendJson(response, 400, { error: 'invalid shot' });")],
 "R-5.14": [(S, SHOT_ERR, "    if (shot === undefined) {\n      if (stored.shots) {\n        const keys = [...stored.shots].filter(([, v]) => v !== 'miss').map(([k]) => k);\n        if (keys.length > 0) {\n          stored.shots.delete(keys[keys.length - 1]);\n        }\n      }\n      sendJson(response, 400, { error: 'invalid shot' });")],
 "R-5.15": [(S, "sendJson(response, 404, { error: 'unknown game' });", "sendJson(response, 400, { error: 'unknown game' });")],
 "R-5.16": [(S, "  } catch (error) {\n    return { kind: 'json' };", "  } catch (error) {\n    return { kind: 'shot' };")],
 "R-5.17": [(S, NOTOBJ, "  if (typeof parsed !== 'object' || Array.isArray(parsed)) {")],
 "R-5.18": [(S, NOTOBJ, "  if (parsed === null || typeof parsed !== 'object') {")],
 "R-5.19": [(S, NOTOBJ, "  if (parsed === null || Array.isArray(parsed)) {")],
 "R-5.20": [(S, GAME_CHECK, "  if (parsed.game !== undefined && (typeof parsed.game !== 'string' || parsed.game.length === 0)) {\n    return { kind: 'shot' };\n  }")],
 "R-5.21": [(S, PARSE_RET, "  return { kind: 'ok', game: parsed.game, row: parsed.row === undefined ? 0 : parsed.row, col: parsed.col };")],
 "R-5.22": [(S, PARSE_RET, "  return { kind: 'ok', game: parsed.game, row: parsed.row, col: parsed.col === undefined ? 0 : parsed.col };")],
 "R-5.23": [(S, GAME_CHECK, "  if (parsed.game === undefined || parsed.game === '') {\n    return { kind: 'shot' };\n  }")],
 "R-5.24": [(S, PARSE_RET, "  return { kind: 'ok', game: parsed.game, row: typeof parsed.row === 'number' ? Math.trunc(parsed.row) : parsed.row, col: parsed.col };")],
 "R-5.25": [(S, PARSE_RET, "  return { kind: 'ok', game: parsed.game, row: parsed.row, col: typeof parsed.col === 'number' ? Math.trunc(parsed.col) : parsed.col };")],
 "R-5.26": [(R, "row > 9", "row > 10")],
 "R-5.27": [(R, "row < 0", "row < -1")],
 "R-5.28": [(R, "col > 9", "col > 10")],
 "R-5.29": [(R, "col < 0", "col < -1")],
 "R-5.30": [(R, "col > 9", "col > 8")],
 "R-5.31": [(R, "row < 0", "row < 1")],
 "R-5.32": [(S, FIRE_OK, "sendJson(response, 200, { result: shot.result, gameOver: shot.gameOver, shots: stored.shots.size });")],
 "R-5.33": [(S, FIRE_OK, "sendJson(response, 200, shot.result === 'sunk' ? { result: shot.result, gameOver: shot.gameOver, ship: stored.ships.find((other) => other.cells.some(([cr, cc]) => cr === parsed.row && cc === parsed.col)).cells } : { result: shot.result, gameOver: shot.gameOver });")],
 "R-5.34": [(S, FIRE_OK, "sendJson(response, 201, { result: shot.result, gameOver: shot.gameOver });")],
 "R-5.35": [(S, FIRE_OK, "send(response, 200, 'text/plain; charset=utf-8', JSON.stringify({ result: shot.result, gameOver: shot.gameOver }));")],
 "R-5.36": [(R, "    return undefined;\n  }\n  if (game.shots === undefined) {", "    if (Number.isInteger(row) && Number.isInteger(col)) {\n      if (game.shots === undefined) {\n        game.shots = new Map();\n      }\n      game.shots.set(Math.min(9, Math.max(0, row)) + ',' + Math.min(9, Math.max(0, col)), 'miss');\n    }\n    return undefined;\n  }\n  if (game.shots === undefined) {")],
}
