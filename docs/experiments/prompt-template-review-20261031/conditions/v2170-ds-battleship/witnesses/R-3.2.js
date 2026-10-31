'use strict';
const L = require('./_lib.js');
const C = require('./_cdp.js');
const { check } = L;
L.run(async () => {
  for (let seed = 1; seed <= 50; seed++) {
    const fleet = L.rules().createGame({ random: L.seeded(seed) }).fleet;
    const lens = fleet.map((s) => s.cells.length).join(',');
    check(lens === '5,4,3,3,2', 'seed ' + seed + ' ship cell counts ' + lens);
    const all = new Set(fleet.flatMap((s) => s.cells.map((c) => c.row + ',' + c.col)));
    check(all.size === 17, 'seed ' + seed + ' has ' + all.size + ' distinct ship cells');
  }
});
