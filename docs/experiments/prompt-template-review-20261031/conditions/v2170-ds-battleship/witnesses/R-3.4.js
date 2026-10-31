'use strict';
const L = require('./_lib.js');
const C = require('./_cdp.js');
const { check } = L;
L.run(async () => {
  for (let seed = 1; seed <= 500; seed++) {
    const fleet = L.rules().createGame({ random: L.seeded(seed) }).fleet;
    for (const s of fleet) {
      const rows = new Set(s.cells.map((c) => c.row)), cols = new Set(s.cells.map((c) => c.col));
      check(rows.size === 1 || cols.size === 1, 'seed ' + seed + ' ship not axis-aligned: ' + JSON.stringify(s.cells));
    }
  }
});
