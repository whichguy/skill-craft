'use strict';
const L = require('./_lib.js');
const C = require('./_cdp.js');
const { check } = L;
L.run(async () => {
  const SEED = 21;
  await C.withPage(SEED, async (page, base) => {
    let failing = true;
    await C.ready(page, base, (rq) => (failing && rq.method === 'POST' && /api\/fire/.test(rq.url) ? { action: 'fail' } : { action: 'continue' }));
    await page.clickCell(4, 4); await L.sleep(400);
    const i = await C.info(page, 4, 4);
    check(!C.marked(i), 'a failed shot left the cell marked: ' + JSON.stringify([i.text, i.label, i.result]));
    failing = false;
    const sent = await C.shoot(page, 4, 4);
    check(sent, 'after the failure a retry click on the same cell sent nothing (grid stayed locked)');
    const j = await C.info(page, 4, 4);
    check(C.marked(j), 'the retry was not rendered: ' + JSON.stringify([j.text, j.label, j.result]));
  });
});
