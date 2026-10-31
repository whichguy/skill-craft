'use strict';
const L = require('./_lib.js');
const C = require('./_cdp.js');
const { check } = L;
L.run(async () => {
  const s = await L.inproc({ random: L.seeded(9) });
  try {
    const r = await L.getJson(s.port, '/api/new');
    check(/^application\/json/.test(r.headers['content-type'] || ''), 'content-type ' + r.headers['content-type']);
  } finally { await s.close(); }
});
