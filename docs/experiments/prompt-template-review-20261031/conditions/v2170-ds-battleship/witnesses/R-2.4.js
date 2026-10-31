'use strict';
const L = require('./_lib.js');
const C = require('./_cdp.js');
const { check } = L;
L.run(async () => {
  const s = await L.inproc(); try { const r = await L.getJson(s.port, '/'); const rows = {}, cols = {};
    for (const m of r.text.matchAll(/data-row="(\d+)" data-col="(\d+)"/g)) { rows[m[1]] = (rows[m[1]] || 0) + 1; cols[m[2]] = (cols[m[2]] || 0) + 1; }
    for (let i = 0; i < 10; i++) { check(rows[i] === 10, 'data-row=' + i + ' appears ' + rows[i] + ' times'); check(cols[i] === 10, 'data-col=' + i + ' appears ' + cols[i] + ' times'); }
    check(Object.keys(rows).length === 10 && Object.keys(cols).length === 10, 'unexpected row/col values ' + Object.keys(rows) + ' / ' + Object.keys(cols)); } finally { await s.close(); }
});
