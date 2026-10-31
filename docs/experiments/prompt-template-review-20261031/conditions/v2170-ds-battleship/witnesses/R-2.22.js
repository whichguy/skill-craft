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
    const n = page.news().length; await C.clickNewGame(page); await L.sleep(500);
    check(page.news().length === n + 1, 'New game started no game');
    const bad = [];
    for (let r = 0; r < 10; r++) for (let c = 0; c < 10; c++) { const i = await C.info(page, r, c); if (C.marked(i)) bad.push(r + ',' + c); }
    check(bad.length === 0, 'cells still show previous results after New game: ' + bad.slice(0, 5));
  });
});
