'use strict';
const L = require('./_lib.js');
const C = require('./_cdp.js');
const { check } = L;
L.run(async () => {
  const s = await L.inproc({ random: L.seeded(2) });
  try {
    const g = (await L.getJson(s.port, '/api/new')).json.game;
const x = await L.getJson(s.port, '/api'); check(x.status === 404, 'GET /api answered ' + x.status);
  } finally { await s.close(); }
});
