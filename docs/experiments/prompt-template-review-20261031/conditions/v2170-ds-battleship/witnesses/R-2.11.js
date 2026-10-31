'use strict';
const L = require('./_lib.js');
const C = require('./_cdp.js');
const { check } = L;
L.run(async () => {
  const SEED = 21;
  await C.withPage(SEED, async (page, base, srv) => {
    const fleet = L.fleetOf(SEED);
    await C.ready(page, base, C.ALLOW);
    const w = C.waterCell(fleet), d = fleet[4].cells;
    await C.shoot(page, w.row, w.col); const miss = await C.info(page, w.row, w.col);
    await C.shoot(page, d[0].row, d[0].col); const hit = await C.info(page, d[0].row, d[0].col);
    await C.shoot(page, d[1].row, d[1].col); const sunk = await C.info(page, d[1].row, d[1].col);
    for (const [word, i] of [['miss', miss], ['hit', hit], ['sunk', sunk]]) check(new RegExp(word, 'i').test(i.label) || i.result === word, 'the ' + word + ' cell shows ' + JSON.stringify([i.text, i.label, i.result]));
    check(new Set([miss.text, hit.text, sunk.text]).size === 3, 'miss, hit and sunk are not shown differently: ' + JSON.stringify([miss.text, hit.text, sunk.text]));
  });
});
