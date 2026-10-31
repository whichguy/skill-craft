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
for (let r = 0; r < 10; r++) for (let c = 0; c < 10; c++) {
      if (isShip(r, c)) continue;
      const x = await L.fire(s.port, g, r, c);
      check(x.status === 200 && x.json.result === 'miss', 'water at ' + r + ',' + c + ' answered ' + x.status + ' ' + (x.json && x.json.result));
    }
  } finally { await s.close(); }
});
