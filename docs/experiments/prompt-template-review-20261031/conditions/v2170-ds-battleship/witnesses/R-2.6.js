'use strict';
const L = require('./_lib.js');
const C = require('./_cdp.js');
const { check } = L;
L.run(async () => {
  const s = await L.inproc(); try { const r = await L.getJson(s.port, '/'); const cells = r.text.match(/<button[^>]*class="cell"[^>]*>/g) || [];
    check(cells.length === 100, 'button.cell count ' + cells.length);
    for (const c of cells) { const m = /aria-label="([^"]+)"/.exec(c); check(m, 'cell without an aria-label: ' + c); check(/\d/.test(m[1]), 'aria-label does not name coordinates: ' + m[1]); } } finally { await s.close(); }
});
