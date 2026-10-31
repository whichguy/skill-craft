import sys; sys.path.insert(0, '/private/tmp/claude-501/-Users-dadleet-src-skill-craft/ddd28884-3bee-490a-b072-5207d26ab322/scratchpad/conditions/v2170-ds-battleship')
from mk_common import write

# common prelude: seeded in-process server, a game, its fleet
PRE = """const SEED = 5;
  const s = await L.inproc({ random: L.seeded(SEED) });
  try {
    const g = (await L.getJson(s.port, '/api/new')).json.game;
    const fleet = L.fleetOf(SEED);
    const shipCells = fleet.flatMap((sh) => sh.cells);
    const isShip = (r, c) => shipCells.some((x) => x.row === r && x.col === c);
"""
POST = "\n  } finally { await s.close(); }"
def w(wid, body, pre=PRE):
    write(wid, "L.run(async () => {\n  " + pre + body + POST + "\n});")

w('R-5.1', """const m = L.modelFor(fleet);
    for (let r = 0; r < 10; r++) for (let c = 0; c < 10; c++) {
      const x = await L.fire(s.port, g, r, c);
      if (x.status !== 200) break;
      const want = m.expect(r, c);
      check((x.json.result === 'miss') === (want === 'miss'), 'a shot at row ' + r + ' col ' + c + ' answered ' + x.json.result + ' but the product dealt ' + (isShip(r, c) ? 'a ship' : 'water') + ' there');
    }""")
w('R-5.2', """const m = L.modelFor(fleet);
    for (const sh of fleet) for (const c of sh.cells) {
      const want = m.expect(c.row, c.col), x = await L.fire(s.port, g, c.row, c.col);
      if (want === 'hit') check(x.json.result === 'hit', 'ship cell ' + c.row + ',' + c.col + ' (not completing) answered ' + x.json.result);
    }""")
w('R-5.3', """const m = L.modelFor(fleet);
    for (const sh of fleet) for (const c of sh.cells) {
      const want = m.expect(c.row, c.col), x = await L.fire(s.port, g, c.row, c.col);
      if (want === 'sunk') check(x.json.result === 'sunk', 'the shot completing a ship at ' + c.row + ',' + c.col + ' answered ' + x.json.result);
    }""")
w('R-5.4', """for (let r = 0; r < 10; r++) for (let c = 0; c < 10; c++) {
      if (isShip(r, c)) continue;
      const x = await L.fire(s.port, g, r, c);
      check(x.status === 200 && x.json.result === 'miss', 'water at ' + r + ',' + c + ' answered ' + x.status + ' ' + (x.json && x.json.result));
    }""")
w('R-5.5', """const x = await L.fire(s.port, g, 0, 0);
    check(x.status === 200, 'status ' + x.status);
    check(['miss', 'hit', 'sunk'].includes(x.json.result), 'result ' + x.json.result);
    check(typeof x.json.gameOver === 'boolean', 'gameOver is a ' + typeof x.json.gameOver);
    check(Number.isInteger(x.json.shipsRemaining), 'shipsRemaining is ' + JSON.stringify(x.json.shipsRemaining));""")
w('R-5.6', """const a = await L.fire(s.port, g, 0, 0), b = await L.fire(s.port, g, 9, 9), c = await L.fire(s.port, g, 0, 9), d = await L.fire(s.port, g, 9, 0);
    check(a.status === 200 && b.status === 200 && c.status === 200 && d.status === 200, 'extreme coordinates answered ' + [a.status, b.status, c.status, d.status]);""")
w('R-5.7', "const x = await L.fire(s.port, g, -1, 0); check(x.status === 400, 'row -1 answered ' + x.status);")
w('R-5.8', "const x = await L.fire(s.port, g, 10, 0); check(x.status === 400, 'row 10 answered ' + x.status);")
w('R-5.9', "const x = await L.fire(s.port, g, 0, -1); check(x.status === 400, 'col -1 answered ' + x.status);")
w('R-5.10', "const x = await L.fire(s.port, g, 0, 10); check(x.status === 400, 'col 10 answered ' + x.status);")
w('R-5.11', """const a = await L.fire(s.port, g, 2, 2), b = await L.fire(s.port, g, 2, 2);
    check(a.status === 200, 'first shot ' + a.status);
    check(b.status === 409, 'repeat answered ' + b.status);
    check(b.json && typeof b.json.error === 'string' && b.json.error.length > 0, 'repeat body ' + b.text);""")
w('R-5.12', """const first = shipCells[3];
    const resp = [];
    resp.push(await L.fire(s.port, g, first.row, first.col));
    const r2 = await L.fire(s.port, g, first.row, first.col), r3 = await L.fire(s.port, g, first.row, first.col);
    check(r2.status === 409 && r3.status === 409, 'repeats answered ' + r2.status + ' and ' + r3.status);
    for (let r = 0; r < 10; r++) for (let c = 0; c < 10; c++) {
      if (r === first.row && c === first.col) continue;
      const x = await L.fire(s.port, g, r, c);
      check(x.status === 200, 'shot ' + r + ',' + c + ' answered ' + x.status);
      resp.push(x);
      if (x.json.gameOver) break;
    }
    const sunk = resp.filter((x) => x.json.result === 'sunk').length, hit = resp.filter((x) => x.json.result === 'hit').length;
    check(sunk === 5 && hit === 12, 'totals after the repeats: sunk ' + sunk + ' hit ' + hit);
    const last = resp[resp.length - 1].json;
    check(last.gameOver === true && last.shipsRemaining === 0, 'final state ' + JSON.stringify(last));""")

# ---------------- R-6 ----------------
SHIPS = """const SEED = 6;
  const s = await L.inproc({ random: L.seeded(SEED) });
  try {
    const g = (await L.getJson(s.port, '/api/new')).json.game;
    const fleet = L.fleetOf(SEED);
    const order = fleet.flatMap((sh) => sh.cells);
    const resp = [];
    for (const c of order) resp.push((await L.fire(s.port, g, c.row, c.col)).json);
    const isShip = (r, c) => order.some((x) => x.row === r && x.col === c);
"""
w('R-6.1', "const r16 = resp[15]; check(r16.gameOver === false && r16.shipsRemaining === 1, 'after the 16th ship cell: ' + JSON.stringify(r16));", SHIPS)
w('R-6.2', "const r17 = resp[16]; check(r17.gameOver === true && r17.shipsRemaining === 0, 'after the 17th ship cell: ' + JSON.stringify(r17));", SHIPS)
w('R-6.3', """let prev = 5, sunk = 0;
    for (const x of resp) {
      if (x.result === 'sunk') { sunk++; check(x.shipsRemaining === prev - 1, 'a sunk response reported ' + x.shipsRemaining + ' after ' + prev); }
      prev = x.shipsRemaining;
    }
    check(sunk === 5 && prev === 0, 'sunk ' + sunk + ', final remaining ' + prev);""", SHIPS)
w('R-6.4', """// a fresh game: a miss and every non-completing hit must leave the count where it was
    const g2 = (await L.getJson(s.port, '/api/new')).json.game;
    const fleet2 = L.fleetOf(SEED);   // first game's fleet; the second game is dealt from the same stream, so use the model only for hits of game 1
    let prev = 5;
    const m = [];
    // use game 1's recorded responses: a hit or a miss never changed the count
    let cur = 5;
    for (const x of resp) { if (x.result === 'hit') check(x.shipsRemaining === cur, 'a hit changed the count from ' + cur + ' to ' + x.shipsRemaining); cur = x.shipsRemaining; }
    // and a miss in a new game (any cell not on the dealt fleet of game 2 is unknowable, so take the first miss encountered)
    let sawMiss = false;
    for (let i = 0; i < 100 && !sawMiss; i++) { const x = await L.fire(s.port, g2, Math.floor(i / 10), i % 10); if (x.json.result === 'miss') { sawMiss = true; check(x.json.shipsRemaining === 5, 'a miss reported ' + x.json.shipsRemaining); } else if (x.json.result === 'hit') { check(x.json.shipsRemaining === 5, 'a hit reported ' + x.json.shipsRemaining); } }
    check(sawMiss, 'no miss seen');""", SHIPS)
w('R-6.5', """let water = null;
    for (let r = 0; r < 10 && !water; r++) for (let c = 0; c < 10 && !water; c++) if (!isShip(r, c)) water = { r, c };
    const x = await L.fire(s.port, g, water.r, water.c);
    check(x.status === 409, 'a shot at an unfired cell after gameOver answered ' + x.status);""", SHIPS)
w('R-6.6', """const waters = [];
    for (let r = 0; r < 10; r++) for (let c = 0; c < 10; c++) if (!isShip(r, c)) waters.push({ r, c });
    const a = await L.fire(s.port, g, waters[0].r, waters[0].c), b = await L.fire(s.port, g, waters[1].r, waters[1].c), c2 = await L.fire(s.port, g, waters[0].r, waters[0].c);
    check(a.status === 409 && b.status === 409 && c2.status === 409, 'post-gameOver shots answered ' + [a.status, b.status, c2.status]);""", SHIPS)
print('ok')
