'use strict';
const L = require('./_lib.js');
const C = require('./_cdp.js');
const { check } = L;
L.run(async () => {
  const s = await L.inproc({ random: L.seeded(2) });
  try {
    const g = (await L.getJson(s.port, '/api/new')).json.game;
const body = JSON.stringify({ game: g, row: 0, col: 0 });
    const big = body + ' '.repeat(1024 * 1024 + 1 - body.length);
    check(big.length === 1024 * 1024 + 1, 'test body size');
    const x = await L.rawFire(s.port, big);
    check(x.status === 413, 'a body of 1 MB + 1 byte answered ' + x.status);
  } finally { await s.close(); }
});
