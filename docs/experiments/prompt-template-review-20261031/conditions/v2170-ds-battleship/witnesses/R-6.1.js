'use strict';
const L = require('./_lib.js');
const C = require('./_cdp.js');
const { check } = L;
L.run(async () => {
  const SEED = 6;
  const s = await L.inproc({ random: L.seeded(SEED) });
  try {
    const g = (await L.getJson(s.port, '/api/new')).json.game;
    const fleet = L.fleetOf(SEED);
    const order = fleet.flatMap((sh) => sh.cells);
    const resp = [];
    for (const c of order) resp.push((await L.fire(s.port, g, c.row, c.col)).json);
    const isShip = (r, c) => order.some((x) => x.row === r && x.col === c);
const r16 = resp[15]; check(r16.gameOver === false && r16.shipsRemaining === 1, 'after the 16th ship cell: ' + JSON.stringify(r16));
  } finally { await s.close(); }
});
