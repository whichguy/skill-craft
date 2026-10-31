'use strict';
const L = require('./_lib.js');
const C = require('./_cdp.js');
const { check } = L;
L.run(async () => {
  for (let seed = 1; seed <= 1000; seed++) {
    const fleet = L.rules().createGame({ random: L.seeded(seed) }).fleet;
    for (const s of fleet) for (const c of s.cells) check(c.row >= 0 && c.row <= 9 && c.col >= 0 && c.col <= 9, 'seed ' + seed + ' has a cell off the board: ' + JSON.stringify(c));
  }
});
