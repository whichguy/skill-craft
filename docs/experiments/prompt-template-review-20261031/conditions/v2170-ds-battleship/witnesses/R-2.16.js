'use strict';
const L = require('./_lib.js');
const C = require('./_cdp.js');
const { check } = L;
L.run(async () => {
  const SEED = 21;
  await C.withPage(SEED, async (page, base, srv) => {
    const fleet = L.fleetOf(SEED);
    await C.ready(page, base, (rq) => (rq.method === 'POST' && /api\/fire/.test(rq.url) ? { action: 'hold' } : { action: 'continue' }));
    const a = fleet[0].cells[0], b = fleet[1].cells[0];
    await page.clickCell(a.row, a.col); await L.sleep(300);
    await page.clickCell(b.row, b.col); await L.sleep(150);
    await page.clickCell(a.row, a.col); await L.sleep(300);
    check(page.fires().length === 1, 'while a shot was in flight the page sent ' + page.fires().length + ' requests');
  });
});
