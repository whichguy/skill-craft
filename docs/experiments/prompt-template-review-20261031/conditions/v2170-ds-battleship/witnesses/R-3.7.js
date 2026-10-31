'use strict';
const L = require('./_lib.js');
const C = require('./_cdp.js');
const { check } = L;
L.run(async () => {
  for (let seed = 1; seed <= 20; seed++) {
    const a = JSON.stringify(L.rules().createGame({ random: L.seeded(seed) }).fleet);
    const b = JSON.stringify(L.rules().createGame({ random: L.seeded(seed) }).fleet);
    check(a === b, 'seed ' + seed + ' dealt two different fleets');
  }
});
