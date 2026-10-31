'use strict';
const L = require('./_lib.js');
const C = require('./_cdp.js');
const { check } = L;
L.run(async () => {
  const SEED = 21;
  await C.withPage(SEED, async (page, base) => {
    const fleet = L.fleetOf(SEED);
    await C.ready(page, base);
    const d = fleet[4].cells;
    await C.shoot(page, d[0].row, d[0].col); await C.shoot(page, d[1].row, d[1].col);
    check(/Ships remaining:?\s*4\b/i.test(await C.text(page)), 'precondition: count 4');
    await page.reload(); await L.waitFor(() => page.news().length >= 2, 5000, 'second game request'); await L.sleep(300);
    const t = await C.text(page);
    check(/Ships remaining:?\s*5\b/i.test(t), 'after a reload the count shown is not 5: ' + JSON.stringify(t.slice(0, 100)));
    const bad = [];
    for (let r = 0; r < 10; r++) for (let c = 0; c < 10; c++) { const i = await C.info(page, r, c); if (C.marked(i)) bad.push(r + ',' + c); }
    check(bad.length === 0, 'after a reload cells still show results: ' + bad.slice(0, 5));
  });
});
