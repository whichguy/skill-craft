import sys; sys.path.insert(0, '/private/tmp/claude-501/-Users-dadleet-src-skill-craft/ddd28884-3bee-490a-b072-5207d26ab322/scratchpad/conditions/v2170-ds-battleship')
from mk_common import write

def seeds(n): return f"for (let seed = 1; seed <= {n}; seed++) {{ const fleet = L.rules().createGame({{ random: L.seeded(seed) }}).fleet;"

write('R-3.1', r"""
L.run(async () => {
  for (let seed = 1; seed <= 20; seed++) {
    const fleet = L.rules().createGame({ random: L.seeded(seed) }).fleet;
    check(fleet.length === 5, 'seed ' + seed + ' dealt ' + fleet.length + ' ships');
  }
});""")
write('R-3.2', r"""
L.run(async () => {
  for (let seed = 1; seed <= 50; seed++) {
    const fleet = L.rules().createGame({ random: L.seeded(seed) }).fleet;
    const lens = fleet.map((s) => s.cells.length).join(',');
    check(lens === '5,4,3,3,2', 'seed ' + seed + ' ship cell counts ' + lens);
    const all = new Set(fleet.flatMap((s) => s.cells.map((c) => c.row + ',' + c.col)));
    check(all.size === 17, 'seed ' + seed + ' has ' + all.size + ' distinct ship cells');
  }
});""")
write('R-3.3', r"""
L.run(async () => {
  for (let seed = 1; seed <= 1000; seed++) {
    const fleet = L.rules().createGame({ random: L.seeded(seed) }).fleet;
    for (const s of fleet) for (const c of s.cells) check(c.row >= 0 && c.row <= 9 && c.col >= 0 && c.col <= 9, 'seed ' + seed + ' has a cell off the board: ' + JSON.stringify(c));
  }
});""")
write('R-3.4', r"""
L.run(async () => {
  for (let seed = 1; seed <= 500; seed++) {
    const fleet = L.rules().createGame({ random: L.seeded(seed) }).fleet;
    for (const s of fleet) {
      const rows = new Set(s.cells.map((c) => c.row)), cols = new Set(s.cells.map((c) => c.col));
      check(rows.size === 1 || cols.size === 1, 'seed ' + seed + ' ship not axis-aligned: ' + JSON.stringify(s.cells));
    }
  }
});""")
write('R-3.5', r"""
L.run(async () => {
  for (let seed = 1; seed <= 500; seed++) {
    const fleet = L.rules().createGame({ random: L.seeded(seed) }).fleet;
    const seen = new Set();
    for (const s of fleet) for (const c of s.cells) { const k = c.row + ',' + c.col; check(!seen.has(k), 'seed ' + seed + ' cell ' + k + ' is shared'); seen.add(k); }
  }
});""")
write('R-3.6', r"""
L.run(async () => {
  let touching = 0;
  for (let seed = 1; seed <= 300; seed++) {
    const fleet = L.rules().createGame({ random: L.seeded(seed) }).fleet;
    for (let i = 0; i < fleet.length; i++) for (let j = i + 1; j < fleet.length; j++) {
      if (fleet[i].cells.some((a) => fleet[j].cells.some((b) => Math.abs(a.row - b.row) + Math.abs(a.col - b.col) === 1))) touching++;
    }
  }
  check(touching > 0, 'in 300 seeded placements no two ships ever touched');
});""")
write('R-3.7', r"""
L.run(async () => {
  for (let seed = 1; seed <= 20; seed++) {
    const a = JSON.stringify(L.rules().createGame({ random: L.seeded(seed) }).fleet);
    const b = JSON.stringify(L.rules().createGame({ random: L.seeded(seed) }).fleet);
    check(a === b, 'seed ' + seed + ' dealt two different fleets');
  }
});""")
write('R-3.8', r"""
L.run(async () => {
  const set = new Set();
  for (let seed = 1; seed <= 20; seed++) set.add(JSON.stringify(L.rules().createGame({ random: L.seeded(seed) }).fleet));
  check(set.size > 1, 'seeds 1..20 produced a single fleet');
});""")
write('R-3.9', r"""
L.run(async () => {
  let calls = 0;
  try { L.rules().createGame({ random: () => { calls++; return 0; } }); } catch { /* expected */ }
  // each placement attempt draws orientation, row and column (3 draws); the first ship is placed at the first try,
  // the second can never be placed, so total draws = 3 + 3 * attempts. At most 200 attempts => <= 603 draws.
  check(calls <= 603, 'a source that always returns 0 was consulted ' + calls + ' times (more than 200 attempts)');
  check(calls >= 3, 'the random source was not consulted');
});""")
write('R-3.10', r"""
L.run(async () => {
  let err, returned;
  try { returned = L.rules().createGame({ random: () => 0 }); } catch (e) { err = e; }
  check(err !== undefined, 'createGame returned instead of throwing');
  check(err instanceof Error, 'the thrown value is not an Error: ' + typeof err);
});""")
write('R-3.11', r"""
L.run(async () => {
  let err;
  try { L.rules().createGame({ random: () => 0 }); } catch (e) { err = e; }
  check(err instanceof Error, 'no Error thrown');
  check(/placement|place/i.test(err.message), 'message does not name placement: ' + err.message);
});""")
write('R-3.12', r"""
L.run(async () => {
  let returned, threw = false;
  try { returned = L.rules().createGame({ random: () => 0 }); } catch { threw = true; }
  check(threw, 'createGame returned a fleet for an unplaceable source: ' + JSON.stringify(returned && returned.fleet && returned.fleet.map((s) => s.length)));
});""")
write('R-3.13', r"""
L.run(async () => {
  const p = await L.freePort();
  const s = L.spawnServer({ port: p });
  try {
    await L.waitFor(async () => { try { return (await L.getJson(p, '/api/new')).status === 200; } catch { return false; } }, 6000, 'start');
    async function pattern() {
      const g = (await L.getJson(p, '/api/new')).json.game;
      const seq = [];
      for (let r = 0; r < 10; r++) for (let c = 0; c < 10; c++) seq.push((await L.fire(p, g, r, c)).json.result[0]);
      return seq.join('');
    }
    const pats = new Set();
    for (let i = 0; i < 3; i++) pats.add(await pattern());
    check(pats.size > 1, 'three games in one process had the same fleet');
  } finally { await s.kill(); }
});""")
write('R-3.14', r"""
L.run(async () => {
  const s = await L.inproc({ random: L.seeded(3) });
  try {
    const r = await L.getJson(s.port, '/api/new');
    check(r.status === 200 && r.json, 'no JSON from /api/new');
    for (const [k, v] of Object.entries(r.json)) check(typeof v === 'string' || typeof v === 'number', 'field ' + k + ' is a ' + typeof v + ' (possible ship data)');
    check(!/carrier|battleship|cruiser|submarine|destroyer|cells|fleet|"row"|"col"/i.test(r.text), 'body mentions ship data: ' + r.text.slice(0, 200));
  } finally { await s.close(); }
});""")
write('R-3.15', r"""
L.run(async () => {
  const s = await L.inproc({ random: L.seeded(11) });
  try {
    const fleet = L.fleetOf(11);
    const g = await L.getJson(s.port, '/api/new');
    check(g.status === 200, '/api/new failed');
    const r = await L.getJson(s.port, '/');
    check(!/carrier|submarine|destroyer|data-ship|ship-cell|occupied/i.test(r.text), 'the page names ships');
    for (const ship of fleet) for (const c of ship.cells) {
      const pats = ['"row":' + c.row + ',"col":' + c.col, '"col":' + c.col + ',"row":' + c.row, 'row: ' + c.row + ', col: ' + c.col, '[' + c.row + ',' + c.col + ']', '[' + c.row + ', ' + c.col + ']'];
      for (const p of pats) check(!r.text.includes(p), 'the page embeds ship cell ' + p);
    }
  } finally { await s.close(); }
});""")
write('R-3.16', r"""
L.run(async () => {
  const s = await L.inproc({ random: L.seeded(4) });
  try {
    const g = (await L.getJson(s.port, '/api/new')).json.game;
    for (let r = 0; r < 10; r++) for (let c = 0; c < 10; c++) {
      const x = await L.fire(s.port, g, r, c);
      if (x.status === 409) break;
      check(x.status === 200, 'status ' + x.status);
      check(Object.keys(x.json).sort().join() === 'gameOver,result,shipsRemaining', 'keys were ' + Object.keys(x.json).sort().join());
    }
  } finally { await s.close(); }
});""")

# ---------------- R-4 ----------------
def new(wid, body):
    write(wid, "L.run(async () => {\n  const s = await L.inproc({ random: L.seeded(9) });\n  try {\n    const r = await L.getJson(s.port, '/api/new');\n    " + body + "\n  } finally { await s.close(); }\n});")
new('R-4.1', "check(r.status === 200, 'status ' + r.status);")
new('R-4.2', "check(/^application\\/json/.test(r.headers['content-type'] || ''), 'content-type ' + r.headers['content-type']);")
new('R-4.3', "check(r.json && Object.keys(r.json).sort().join() === 'game,ships,size', 'keys ' + (r.json && Object.keys(r.json)));")
new('R-4.4', "check(r.json && r.json.size === 10, 'size was ' + (r.json && r.json.size));")
new('R-4.5', "check(r.json && r.json.ships === 5, 'ships was ' + (r.json && r.json.ships));")
new('R-4.6', "check(/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/.test(r.json.game), 'id ' + r.json.game);")
new('R-4.7', "const r2 = await L.getJson(s.port, '/api/new'); check(r.json.game !== r2.json.game, 'two calls returned the same id ' + r.json.game);")
new('R-4.8', """const fleet = L.fleetOf(9), m = L.modelFor(fleet), g = r.json.game;
    for (let i = 0; i < 100; i++) {
      const row = Math.floor(i / 10), col = i % 10;
      const x = await L.fire(s.port, g, row, col);
      check(x.status === 200, 'shot ' + row + ',' + col + ' answered ' + x.status);
      check(x.json.result === m.expect(row, col), 'shot ' + row + ',' + col + ' result ' + x.json.result + ' differs from the game that /api/new started');
    }
    check((await L.fire(s.port, g, 0, 0)).status === 409, 'the finished game did not remember its state');""")
print('ok')
