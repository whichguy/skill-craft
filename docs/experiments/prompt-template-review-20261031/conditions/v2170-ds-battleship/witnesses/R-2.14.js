'use strict';
const L = require('./_lib.js');
const C = require('./_cdp.js');
const { check } = L;
L.run(async () => {
  const SEED = 21;
  await C.withPage(SEED, async (page, base, srv) => {
    const fleet = L.fleetOf(SEED);
    await C.ready(page, base, C.ALLOW);
    const w = C.waterCell(fleet), d = fleet[4].cells; const out = {};
    await C.shoot(page, w.row, w.col); out.miss = await C.statusOf(page);
    await C.shoot(page, d[0].row, d[0].col); out.hit = await C.statusOf(page);
    await C.shoot(page, d[1].row, d[1].col); out.sunk = await C.statusOf(page);
    for (const k of ['miss', 'hit', 'sunk']) check(new RegExp(k, 'i').test(out[k]), 'after a ' + k + ' the status region says ' + JSON.stringify(out[k]));
  });
});
