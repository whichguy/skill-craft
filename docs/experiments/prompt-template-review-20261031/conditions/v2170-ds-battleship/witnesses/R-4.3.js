'use strict';
const L = require('./_lib.js');
const C = require('./_cdp.js');
const { check } = L;
L.run(async () => {
  const s = await L.inproc({ random: L.seeded(9) });
  try {
    const r = await L.getJson(s.port, '/api/new');
    check(r.json && Object.keys(r.json).sort().join() === 'game,ships,size', 'keys ' + (r.json && Object.keys(r.json)));
  } finally { await s.close(); }
});
