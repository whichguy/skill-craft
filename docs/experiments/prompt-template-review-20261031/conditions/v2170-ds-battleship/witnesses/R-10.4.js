'use strict';
const L = require('./_lib.js');
const C = require('./_cdp.js');
const { check } = L;
L.run(async () => {
  const SEED = 21;
  await C.withPage(SEED, async (page, base, srv) => {
    const fleet = L.fleetOf(SEED);
    await C.ready(page, base, (rq) => (rq.method === 'POST' && /api\/fire/.test(rq.url) ? { action: 'fail' } : { action: 'continue' }));
    await page.clickCell(4, 4); await L.sleep(500);
    const bad = [];
    for (let r = 0; r < 10; r++) for (let c = 0; c < 10; c++) { const i = await C.info(page, r, c); if (C.marked(i)) bad.push(r + ',' + c); }
    check(bad.length === 0, 'a failed shot left cells marked: ' + bad);
    check(/Ships remaining:?\s*5\b/i.test(await C.text(page)), 'the count changed after a failed shot');
  });
});
