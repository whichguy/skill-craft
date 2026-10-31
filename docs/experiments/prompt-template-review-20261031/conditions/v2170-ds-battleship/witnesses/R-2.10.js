'use strict';
const L = require('./_lib.js');
const C = require('./_cdp.js');
const { check } = L;
L.run(async () => {
  const SEED = 21;
  await C.withPage(SEED, async (page, base, srv) => {
    const fleet = L.fleetOf(SEED);
    await C.ready(page, base, C.ALLOW);
    await page.eval('window.__m = 1');
    const n0 = page.navigations;
    await page.clickCell(3, 4); await L.sleep(500);
    const f = page.fires();
    check(f.length === 1, 'one click sent ' + f.length + ' POST /api/fire requests');
    const b = JSON.parse(f[0].postData);
    check(b.row === 3 && b.col === 4, 'the shot carried ' + f[0].postData);
    check(await page.eval('window.__m') === 1 && page.navigations === n0, 'the document navigated or reloaded');
  });
});
