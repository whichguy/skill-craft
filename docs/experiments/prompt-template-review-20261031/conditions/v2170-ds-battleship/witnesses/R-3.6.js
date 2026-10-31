'use strict';
const L = require('./_lib.js');
const C = require('./_cdp.js');
const { check } = L;
L.run(async () => {
  let touching = 0;
  for (let seed = 1; seed <= 300; seed++) {
    const fleet = L.rules().createGame({ random: L.seeded(seed) }).fleet;
    for (let i = 0; i < fleet.length; i++) for (let j = i + 1; j < fleet.length; j++) {
      if (fleet[i].cells.some((a) => fleet[j].cells.some((b) => Math.abs(a.row - b.row) + Math.abs(a.col - b.col) === 1))) touching++;
    }
  }
  check(touching > 0, 'in 300 seeded placements no two ships ever touched');
});
