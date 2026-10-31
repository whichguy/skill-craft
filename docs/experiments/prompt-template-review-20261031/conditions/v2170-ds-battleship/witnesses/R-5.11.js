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
const a = await L.fire(s.port, g, 2, 2), b = await L.fire(s.port, g, 2, 2);
    check(a.status === 200, 'first shot ' + a.status);
    check(b.status === 409, 'repeat answered ' + b.status);
    check(b.json && typeof b.json.error === 'string' && b.json.error.length > 0, 'repeat body ' + b.text);
  } finally { await s.close(); }
});
