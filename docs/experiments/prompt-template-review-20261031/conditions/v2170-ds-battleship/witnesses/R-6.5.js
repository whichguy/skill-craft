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
let water = null;
    for (let r = 0; r < 10 && !water; r++) for (let c = 0; c < 10 && !water; c++) if (!isShip(r, c)) water = { r, c };
    const x = await L.fire(s.port, g, water.r, water.c);
    check(x.status === 409, 'a shot at an unfired cell after gameOver answered ' + x.status);
  } finally { await s.close(); }
});
