'use strict';
const L = require('./_lib.js');
const C = require('./_cdp.js');
const { check } = L;
L.run(async () => {
  const s = await L.inproc(); try { const r = await L.getJson(s.port, '/'); check(r.status === 200, 'GET / answered ' + r.status); check(r.headers['content-type'] === 'text/html; charset=utf-8', 'content-type was ' + r.headers['content-type']); } finally { await s.close(); }
});
