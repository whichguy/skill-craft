'use strict';
const L = require('./_lib.js');
const C = require('./_cdp.js');
const { check } = L;
L.run(async () => {
  const s = await L.inproc(); try { const r = await L.getJson(s.port, '/'); const n = (r.text.match(/data-row="\d" data-col="\d"/g) || []).length; check(n === 100, 'cell count in served body was ' + n); } finally { await s.close(); }
});
