'use strict';
const L = require('./_lib.js');
const C = require('./_cdp.js');
const { check } = L;
L.run(async () => {
  const SEED = 21;
  await C.withPage(SEED, async (page, base) => {
    const fleet = L.fleetOf(SEED);
    let failNew = false;
    await C.ready(page, base, (rq) => (failNew && /api\/new/.test(rq.url) ? { action: 'fulfill', status: 500, body: '{"error":"boom"}' } : { action: 'continue' }));
    await C.win(page, fleet);
    failNew = true;
    await C.clickNewGame(page); await L.sleep(500);
    check((await C.statusOf(page)).length > 0, 'no status after the refused New game');
    const n = page.fires().length, w = C.waterCell(fleet);
    await C.shoot(page, w.row, w.col); await L.sleep(300);
    check(page.fires().length === n, 'after a refused New game the finished board accepted a shot');
    const h = fleet[0].cells[0]; const i = await C.info(page, h.row, h.col);
    check(C.marked(i), 'the finished board lost its marks after a refused New game: ' + JSON.stringify([i.text, i.label]));
  });
});
