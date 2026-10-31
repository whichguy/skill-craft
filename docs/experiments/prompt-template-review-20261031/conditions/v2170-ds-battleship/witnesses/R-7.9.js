'use strict';
const L = require('./_lib.js');
const C = require('./_cdp.js');
const { check } = L;
L.run(async () => {
  const s = await L.inproc({ random: L.seeded(2) });
  try {
    const g = (await L.getJson(s.port, '/api/new')).json.game;
const x = await L.rawFire(s.port, JSON.stringify({ game: '00000000-0000-4000-8000-000000000000', row: 0, col: 0 }));
    check(x.status === 404, 'unknown UUID' + ' answered ' + x.status + ' ' + x.text.slice(0, 100));
  } finally { await s.close(); }
});
