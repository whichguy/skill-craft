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
const m = L.modelFor(fleet);
    for (const sh of fleet) for (const c of sh.cells) {
      const want = m.expect(c.row, c.col), x = await L.fire(s.port, g, c.row, c.col);
      if (want === 'sunk') check(x.json.result === 'sunk', 'the shot completing a ship at ' + c.row + ',' + c.col + ' answered ' + x.json.result);
    }
  } finally { await s.close(); }
});
