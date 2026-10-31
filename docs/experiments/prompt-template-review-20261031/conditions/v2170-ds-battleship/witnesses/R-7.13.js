'use strict';
const L = require('./_lib.js');
const C = require('./_cdp.js');
const { check } = L;
L.run(async () => {
  const s = await L.inproc({ random: L.seeded(2) });
  try {
    const g = (await L.getJson(s.port, '/api/new')).json.game;
const x = await L.req(s.port, 'GET', '/api/fire'); check(x.status === 405, 'GET /api/fire answered ' + x.status);
  } finally { await s.close(); }
});
