'use strict';
const L = require('./_lib.js');
const C = require('./_cdp.js');
const { check } = L;
L.run(async () => {
  const s = await L.inproc(); try { const r = await L.getJson(s.port, '/'); check(/role="status"/.test(r.text), 'no role=status element in the served body'); } finally { await s.close(); }
});
