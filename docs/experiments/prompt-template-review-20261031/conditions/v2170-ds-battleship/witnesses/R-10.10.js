'use strict';
const L = require('./_lib.js');
const C = require('./_cdp.js');
const { check } = L;
L.run(async () => {
  const s = await L.inproc({ random: L.seeded(12) });
  try {
    const a = (await L.getJson(s.port, '/api/new')).json.game, b = (await L.getJson(s.port, '/api/new')).json.game;
    const fleet = L.fleetOf(12); // first game dealt from seed 12 is game A
    const c = fleet[0].cells[0];
    const [x, y] = await Promise.all([L.fire(s.port, a, c.row, c.col), L.fire(s.port, a, c.row, c.col)]);
    check([x.status, y.status].sort().join() === '200,409', 'two simultaneous shots at one cell answered ' + [x.status, y.status]);
  } finally { await s.close(); }
});
