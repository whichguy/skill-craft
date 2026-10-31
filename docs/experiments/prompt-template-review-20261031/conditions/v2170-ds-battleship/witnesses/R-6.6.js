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
const waters = [];
    for (let r = 0; r < 10; r++) for (let c = 0; c < 10; c++) if (!isShip(r, c)) waters.push({ r, c });
    const a = await L.fire(s.port, g, waters[0].r, waters[0].c), b = await L.fire(s.port, g, waters[1].r, waters[1].c), c2 = await L.fire(s.port, g, waters[0].r, waters[0].c);
    check(a.status === 409 && b.status === 409 && c2.status === 409, 'post-gameOver shots answered ' + [a.status, b.status, c2.status]);
  } finally { await s.close(); }
});
