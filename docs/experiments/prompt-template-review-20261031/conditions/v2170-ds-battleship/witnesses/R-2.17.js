'use strict';
const L = require('./_lib.js');
const C = require('./_cdp.js');
const { check } = L;
L.run(async () => {
  const SEED = 21;
  await C.withPage(SEED, async (page, base, srv) => {
    const fleet = L.fleetOf(SEED);
    await C.ready(page, base, C.ALLOW);
    await C.win(page, fleet);
    check(/win|sunk/i.test(await C.statusOf(page)), 'game did not end: ' + await C.statusOf(page));
    const n = page.fires().length, w = C.waterCell(fleet);
    await C.shoot(page, w.row, w.col); await L.sleep(300);
    check(page.fires().length === n, 'after the game ended a click sent another request');
  });
});
