'use strict';
const L = require('./_lib.js');
const C = require('./_cdp.js');
const { check } = L;
L.run(async () => {
  const SEED = 21;
  await C.withPage(SEED, async (page, base, srv) => {
    const fleet = L.fleetOf(SEED);
    await C.ready(page, base, C.ALLOW);
    const d = fleet[4].cells;
    await C.shoot(page, d[0].row, d[0].col); await C.shoot(page, d[1].row, d[1].col);
    const t = await C.text(page); check(/Ships remaining:?\s*4\b/i.test(t), 'after a sink the count shown is not 4; visible text: ' + JSON.stringify(t.slice(0, 120)));
  });
});
