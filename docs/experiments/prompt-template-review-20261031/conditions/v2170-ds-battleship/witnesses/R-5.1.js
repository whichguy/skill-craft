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
    for (let r = 0; r < 10; r++) for (let c = 0; c < 10; c++) {
      const x = await L.fire(s.port, g, r, c);
      if (x.status !== 200) break;
      const want = m.expect(r, c);
      check((x.json.result === 'miss') === (want === 'miss'), 'a shot at row ' + r + ' col ' + c + ' answered ' + x.json.result + ' but the product dealt ' + (isShip(r, c) ? 'a ship' : 'water') + ' there');
    }
  } finally { await s.close(); }
});
