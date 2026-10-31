'use strict';
const L = require('./_lib.js');
const C = require('./_cdp.js');
const { check } = L;
L.run(async () => {
  await C.withPage(21, async (page, base) => {
    await C.ready(page, base);
    await C.shoot(page, 0, 0);
    const id1 = JSON.parse(page.fires()[0].postData).game;
    await page.reload(); await L.sleep(800);
    await C.shoot(page, 0, 0);
    const id2 = JSON.parse(page.fires()[page.fires().length - 1].postData).game;
    check(page.news().length === 2, 'the reloaded page did not start a game of its own (' + page.news().length + ' /api/new requests)');
    check(id1 && id2 && id1 !== id2, 'the reloaded page kept using the earlier game id');
  });
});
