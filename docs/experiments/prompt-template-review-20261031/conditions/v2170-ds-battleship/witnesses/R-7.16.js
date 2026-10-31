'use strict';
const L = require('./_lib.js');
const C = require('./_cdp.js');
const { check } = L;
L.run(async () => {
  const s = await L.inproc({ random: L.seeded(2) });
  try {
    const g = (await L.getJson(s.port, '/api/new')).json.game;
const x = await L.getJson(s.port, '/api/new?x=1'); check(x.status === 200 && x.json && typeof x.json.game === 'string', 'GET /api/new?x=1 answered ' + x.status);
  } finally { await s.close(); }
});
