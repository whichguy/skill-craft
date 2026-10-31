'use strict';
const L = require('./_lib.js');
const C = require('./_cdp.js');
const { check } = L;
L.run(async () => {
  for (let seed = 1; seed <= 500; seed++) {
    const fleet = L.rules().createGame({ random: L.seeded(seed) }).fleet;
    const seen = new Set();
    for (const s of fleet) for (const c of s.cells) { const k = c.row + ',' + c.col; check(!seen.has(k), 'seed ' + seed + ' cell ' + k + ' is shared'); seen.add(k); }
  }
});
