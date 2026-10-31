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
const x = await L.fire(s.port, g, 0, 0);
    check(x.status === 200, 'status ' + x.status);
    check(['miss', 'hit', 'sunk'].includes(x.json.result), 'result ' + x.json.result);
    check(typeof x.json.gameOver === 'boolean', 'gameOver is a ' + typeof x.json.gameOver);
    check(Number.isInteger(x.json.shipsRemaining), 'shipsRemaining is ' + JSON.stringify(x.json.shipsRemaining));
  } finally { await s.close(); }
});
