'use strict';
const L = require('./_lib.js');
const C = require('./_cdp.js');
const { check } = L;
L.run(async () => {
  const SEED = 21;
  await C.withPage(SEED, async (page, base) => {
    let bad = false;
    await C.ready(page, base, (rq) => (bad && rq.method === 'POST' && /api\/fire/.test(rq.url) ? { action: 'fulfill', status: 200, body: '{"result":"banana","gameOver":false,"shipsRemaining":3}' } : { action: 'continue' }));
    bad = true;
    const before = await C.info(page, 6, 6), tb = await C.text(page);
    await page.clickCell(6, 6); await L.sleep(500);
    const after = await C.info(page, 6, 6), ta = await C.text(page);
    check(!C.marked(after) && after.html === before.html, 'an off-contract answer marked the cell: ' + after.html);
    check(/Ships remaining:?\s*5\b/i.test(ta), 'an off-contract answer changed the count: ' + ta.slice(0, 80));
    const st = await C.statusOf(page);
    check(st.length > 0 && !/Firing/i.test(st), 'the off-contract answer was not reported: ' + JSON.stringify(st));
  });
});
