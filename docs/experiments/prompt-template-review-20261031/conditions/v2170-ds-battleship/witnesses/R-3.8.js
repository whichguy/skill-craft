'use strict';
const L = require('./_lib.js');
const C = require('./_cdp.js');
const { check } = L;
L.run(async () => {
  const set = new Set();
  for (let seed = 1; seed <= 20; seed++) set.add(JSON.stringify(L.rules().createGame({ random: L.seeded(seed) }).fleet));
  check(set.size > 1, 'seeds 1..20 produced a single fleet');
});
