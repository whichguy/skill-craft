'use strict';
const L = require('./_lib.js');
const C = require('./_cdp.js');
const { check } = L;
L.run(async () => {
  const s = await L.inproc({ random: L.seeded(12) });
  try {
    const a = (await L.getJson(s.port, '/api/new')).json.game, b = (await L.getJson(s.port, '/api/new')).json.game;
    const x = await L.fire(s.port, a, 0, 0);
    check(x.status === 200, 'game A shot answered ' + x.status);
    const y = await L.fire(s.port, b, 0, 0);
    check(y.status === 200, "a shot at game B's cell (0,0) answered " + y.status + ' after game A fired there');
    const z = await L.fire(s.port, b, 0, 0);
    check(z.status === 409, 'repeat in game B answered ' + z.status);
  } finally { await s.close(); }
});
