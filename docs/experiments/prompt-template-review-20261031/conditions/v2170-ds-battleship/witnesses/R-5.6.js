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
const a = await L.fire(s.port, g, 0, 0), b = await L.fire(s.port, g, 9, 9), c = await L.fire(s.port, g, 0, 9), d = await L.fire(s.port, g, 9, 0);
    check(a.status === 200 && b.status === 200 && c.status === 200 && d.status === 200, 'extreme coordinates answered ' + [a.status, b.status, c.status, d.status]);
  } finally { await s.close(); }
});
