'use strict';
const L = require('./_lib.js');
const C = require('./_cdp.js');
const { check } = L;
L.run(async () => {
  const s = await L.inproc({ random: L.seeded(2) });
  try {
    const g = (await L.getJson(s.port, '/api/new')).json.game;
const body = JSON.stringify({ game: g, row: 0, col: 0 });
    const big = body + ' '.repeat(1000000 - body.length);
    const x = await L.rawFire(s.port, big);
    check(x.status !== 413 && x.status === 200, 'a valid body of 1,000,000 bytes answered ' + x.status);
  } finally { await s.close(); }
});
