'use strict';
const L = require('./_lib.js');
const C = require('./_cdp.js');
const { check } = L;
L.run(async () => {
  const s = await L.inproc({ random: L.seeded(12) });
  try {
    const a = (await L.getJson(s.port, '/api/new')).json.game, b = (await L.getJson(s.port, '/api/new')).json.game;
    // drive game A to gameOver with a row-major walk
    for (let i = 0; i < 100; i++) { const x = await L.fire(s.port, a, Math.floor(i / 10), i % 10); if (x.json && x.json.gameOver) break; }
    let waterB = null;
    const y = await L.fire(s.port, b, 9, 9);
    check(y.status === 200, "game B's shot after game A ended answered " + y.status);
    check(y.json.gameOver === false && y.json.shipsRemaining >= 4, "game B's answer after game A ended: " + JSON.stringify(y.json));
  } finally { await s.close(); }
});
