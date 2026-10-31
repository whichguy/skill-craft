'use strict';
const L = require('./_lib.js');
const C = require('./_cdp.js');
const { check } = L;
L.run(async () => {
  const s = await L.inproc({ random: L.seeded(9) });
  try {
    const r = await L.getJson(s.port, '/api/new');
    let done = false; const fleet = L.fleetOf(9), m = L.modelFor(fleet), g = r.json.game;
    for (let i = 0; i < 100; i++) {
      const row = Math.floor(i / 10), col = i % 10;
      const x = await L.fire(s.port, g, row, col);
      if (x.status === 409 && done) break;
      check(x.status === 200, 'shot ' + row + ',' + col + ' answered ' + x.status);
      if (x.json.gameOver) done = true;
      check(x.json.result === m.expect(row, col), 'shot ' + row + ',' + col + ' result ' + x.json.result + ' differs from the game that /api/new started');
    }
    check((await L.fire(s.port, g, 0, 0)).status === 409, 'the finished game did not remember its state');
  } finally { await s.close(); }
});
