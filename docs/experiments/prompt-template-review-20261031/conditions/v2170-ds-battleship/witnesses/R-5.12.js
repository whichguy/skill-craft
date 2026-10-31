'use strict';
const L = require('./_lib.js');
const C = require('./_cdp.js');
const { check } = L;
L.run(async () => {
  const SEED = 5;
  const s = await L.inproc({ random: L.seeded(SEED) });
  try {
    const g = (await L.getJson(s.port, '/api/new')).json.game;
    const fleet = L.fleetOf(SEED);
    const shipCells = fleet.flatMap((sh) => sh.cells);
    const isShip = (r, c) => shipCells.some((x) => x.row === r && x.col === c);
const first = shipCells[3];
    const resp = [];
    resp.push(await L.fire(s.port, g, first.row, first.col));
    const r2 = await L.fire(s.port, g, first.row, first.col), r3 = await L.fire(s.port, g, first.row, first.col);
    check(r2.status === 409 && r3.status === 409, 'repeats answered ' + r2.status + ' and ' + r3.status);
    let over = false;
    for (let r = 0; r < 10 && !over; r++) for (let c = 0; c < 10 && !over; c++) {
      if (r === first.row && c === first.col) continue;
      const x = await L.fire(s.port, g, r, c);
      check(x.status === 200, 'shot ' + r + ',' + c + ' answered ' + x.status);
      resp.push(x);
      if (x.json.gameOver) over = true;
    }
    const sunk = resp.filter((x) => x.json.result === 'sunk').length, hit = resp.filter((x) => x.json.result === 'hit').length;
    check(sunk === 5 && hit === 12, 'totals after the repeats: sunk ' + sunk + ' hit ' + hit);
    const last = resp[resp.length - 1].json;
    check(last.gameOver === true && last.shipsRemaining === 0, 'final state ' + JSON.stringify(last));
  } finally { await s.close(); }
});
