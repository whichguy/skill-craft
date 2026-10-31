'use strict';
const L = require('./_lib.js');
const C = require('./_cdp.js');
const { check } = L;
L.run(async () => {
  const s = await L.inproc({ random: L.seeded(12) });
  try {
    const a = (await L.getJson(s.port, '/api/new')).json.game, b = (await L.getJson(s.port, '/api/new')).json.game;
    const fleet = L.fleetOf(12);
    const c = fleet[0].cells[0];
    const [x, y] = await Promise.all([L.fire(s.port, a, c.row, c.col), L.fire(s.port, a, c.row, c.col)]);
    const ok = [x, y].find((r) => r.status === 200);
    check(ok && ok.json.shipsRemaining === 5, 'the accepted shot reported ' + JSON.stringify(ok && ok.json));
    const again = await L.fire(s.port, a, c.row, c.col);
    check(again.status === 409, 'after the simultaneous pair the cell counts as fired once, but a further shot answered ' + again.status);
    // the rest of the game reconciles: sunk 5, hit 12 including the pair's accepted shot
    const m = L.modelFor(fleet); m.expect(c.row, c.col);
    let sunk = ok.json.result === 'sunk' ? 1 : 0, hit = ok.json.result === 'hit' ? 1 : 0, last = ok.json, over = false;
    for (let i = 0; i < 100 && !over; i++) {
      const r = Math.floor(i / 10), cc = i % 10;
      if (r === c.row && cc === c.col) continue;
      const q = await L.fire(s.port, a, r, cc);
      check(q.status === 200, 'shot ' + r + ',' + cc + ' answered ' + q.status);
      if (q.json.result === 'sunk') sunk++; if (q.json.result === 'hit') hit++;
      last = q.json; if (q.json.gameOver) over = true;
    }
    check(sunk === 5 && hit === 12 && last.shipsRemaining === 0, 'totals sunk ' + sunk + ' hit ' + hit + ' final ' + JSON.stringify(last));
  } finally { await s.close(); }
});
