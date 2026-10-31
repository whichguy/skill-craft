'use strict';
const L = require('./_lib.js');
const C = require('./_cdp.js');
const { check } = L;
L.run(async () => {
  const SEED = 21;
  await C.withPage(SEED, async (page, base, srv) => {
    const fleet = L.fleetOf(SEED);
    await C.ready(page, base, C.ALLOW);
    const w = C.waterCell(fleet);
    check(await C.shoot(page, w.row, w.col), 'first shot not sent');
    const n = page.fires().length;
    await C.shoot(page, w.row, w.col); await L.sleep(300);
    check(page.fires().length === n, 'a click on an already-fired cell sent another request');
  });
});
