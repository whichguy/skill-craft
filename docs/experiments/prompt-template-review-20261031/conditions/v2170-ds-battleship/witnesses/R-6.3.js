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
let prev = 5, sunk = 0;
    for (const x of resp) {
      if (x.result === 'sunk') { sunk++; check(x.shipsRemaining === prev - 1, 'a sunk response reported ' + x.shipsRemaining + ' after ' + prev); }
      prev = x.shipsRemaining;
    }
    check(sunk === 5 && prev === 0, 'sunk ' + sunk + ', final remaining ' + prev);
  } finally { await s.close(); }
});
