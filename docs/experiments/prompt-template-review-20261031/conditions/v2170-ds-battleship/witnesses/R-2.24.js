'use strict';
const L = require('./_lib.js');
const C = require('./_cdp.js');
const { check } = L;
L.run(async () => {
  const SEED = 21;
  await C.withPage(SEED, async (page, base, srv) => {
    const fleet = L.fleetOf(SEED);
    await C.ready(page, base, C.ALLOW);
    let ok = false;
    for (let i = 0; i < 6 && !ok; i++) { await page.tab(); ok = await page.eval(`document.activeElement.classList.contains('cell')`); }
    check(ok, 'Tab never reached a cell');
    const at = await page.eval(`({ r: Number(document.activeElement.dataset.row), c: Number(document.activeElement.dataset.col) })`);
    await page.enter(); await L.sleep(500);
    check(page.fires().length === 1, 'Enter on a focused cell sent ' + page.fires().length + ' shots');
    const b = JSON.parse(page.fires()[0].postData); check(b.row === at.r && b.col === at.c, 'Enter fired ' + page.fires()[0].postData + ' instead of the focused cell ' + JSON.stringify(at));
  });
});
