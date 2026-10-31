'use strict';
const L = require('./_lib.js');
const C = require('./_cdp.js');
const { check } = L;
L.run(async () => {
  const SEED = 21;
  await C.withPage(SEED, async (page, base, srv) => {
    const fleet = L.fleetOf(SEED);
    await C.ready(page, base, (rq) => (rq.method === 'POST' && /api\/fire/.test(rq.url) ? { action: 'hold' } : { action: 'continue' }));
    await page.clickCell(4, 4); await L.sleep(300);
    const n = page.news().length;
    await C.clickNewGame(page); await L.sleep(400);
    check(page.news().length === n, 'New game started a new game while a shot was in flight');
  });
});
