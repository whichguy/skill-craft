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
// game 1 (shots at ship cells only): a non-completing hit never changes the count
    let cur = 5;
    for (const x of resp) { if (x.result === 'hit') check(x.shipsRemaining === cur, 'a hit changed the count from ' + cur + ' to ' + x.shipsRemaining); cur = x.shipsRemaining; }
    // game 2: walk until the first miss and check hits and the miss left the count at 5
    const g2 = (await L.getJson(s.port, '/api/new')).json.game;
    let sawMiss = false;
    for (let i = 0; i < 100 && !sawMiss; i++) {
      const x = await L.fire(s.port, g2, Math.floor(i / 10), i % 10);
      if (x.json.result === 'miss') sawMiss = true;
      if (x.json.result === 'miss' || x.json.result === 'hit') check(x.json.shipsRemaining === 5, 'a ' + x.json.result + ' reported ' + x.json.shipsRemaining + ' ships remaining');
    }
    check(sawMiss, 'no miss seen');
  } finally { await s.close(); }
});
