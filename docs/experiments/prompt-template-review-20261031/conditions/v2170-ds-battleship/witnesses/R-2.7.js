'use strict';
const L = require('./_lib.js');
const C = require('./_cdp.js');
const { check } = L;
L.run(async () => {
  const s = await L.inproc(); try { const r = await L.getJson(s.port, '/'); const bad = [...r.text.matchAll(/\b(?:src|href)\s*=\s*["']([^"']*)["']/gi)].map((m) => m[1]).filter((v) => /^(https?:)?\/\//i.test(v)); check(bad.length === 0, 'off-origin references: ' + bad); } finally { await s.close(); }
});
