'use strict';
const L = require('./_lib.js');
const C = require('./_cdp.js');
const { check } = L;
L.run(async () => {
  for (let seed = 1; seed <= 20; seed++) {
    const fleet = L.rules().createGame({ random: L.seeded(seed) }).fleet;
    check(fleet.length === 5, 'seed ' + seed + ' dealt ' + fleet.length + ' ships');
  }
});
