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
    const first = JSON.parse(page.fires()[0].postData).game;
    await C.clickNewGame(page); await L.sleep(500);
    const t = await C.text(page);
    check(/Ships remaining:?\s*5\b/i.test(t), 'after New game the count shown is not 5: ' + JSON.stringify(t.slice(0, 100)));
    await C.shoot(page, 0, 0);
    const second = JSON.parse(page.fires()[page.fires().length - 1].postData).game;
    check(second && second !== first, 'New game did not switch to a new game id');
  });
});
