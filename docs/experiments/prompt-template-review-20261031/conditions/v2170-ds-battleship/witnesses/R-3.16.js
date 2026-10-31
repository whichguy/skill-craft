'use strict';
const L = require('./_lib.js');
const C = require('./_cdp.js');
const { check } = L;
L.run(async () => {
  const s = await L.inproc({ random: L.seeded(4) });
  try {
    const g = (await L.getJson(s.port, '/api/new')).json.game;
    for (let r = 0; r < 10; r++) for (let c = 0; c < 10; c++) {
      const x = await L.fire(s.port, g, r, c);
      if (x.status === 409) break;
      check(x.status === 200, 'status ' + x.status);
      check(Object.keys(x.json).sort().join() === 'gameOver,result,shipsRemaining', 'keys were ' + Object.keys(x.json).sort().join());
    }
  } finally { await s.close(); }
});
