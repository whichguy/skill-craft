'use strict';
const L = require('./_lib.js');
const C = require('./_cdp.js');
const { check } = L;
L.run(async () => {
  const SEED = 21;
  await C.withPage(SEED, async (page, base, srv) => {
    const fleet = L.fleetOf(SEED);
    await C.ready(page, base, (rq) => (rq.method === 'POST' && /api\/fire/.test(rq.url) ? { action: 'fail' } : { action: 'continue' }));
    await page.clickCell(4, 4); await L.sleep(400);
    const t = await C.statusOf(page);
    check(/not reach|fail|error|could not|unable|network/i.test(t), 'status region after a failed request: ' + JSON.stringify(t));
  });
});
