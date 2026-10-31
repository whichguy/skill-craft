'use strict';
const L = require('./_lib.js');
const C = require('./_cdp.js');
const { check } = L;
L.run(async () => {
  const s = await L.inproc(); try { const r = await L.getJson(s.port, '/'); const m = /data-row="(\d+)" data-col="(\d+)"/.exec(r.text); check(m && m[1] === '0' && m[2] === '0', 'first cell in document order is ' + (m && m.slice(1, 3))); } finally { await s.close(); }
});
