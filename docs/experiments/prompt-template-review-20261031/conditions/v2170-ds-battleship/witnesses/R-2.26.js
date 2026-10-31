'use strict';
const L = require('./_lib.js');
const C = require('./_cdp.js');
const { check } = L;
L.run(async () => {
  const SEED = 21;
  await C.withPage(SEED, async (page, base, srv) => {
    const fleet = L.fleetOf(SEED);
    await C.ready(page, base, C.ALLOW);
    const w = C.waterCell(fleet), h = fleet[0].cells[0];
    await C.shoot(page, w.row, w.col); await C.shoot(page, h.row, h.col);
    for (const [word, p] of [['miss', w], ['hit', h]]) {
      const i = await C.info(page, p.row, p.col);
      check(i.text.length > 0 || new RegExp(word, 'i').test(i.label), 'the ' + word + ' cell conveys its outcome by colour only: ' + JSON.stringify([i.text, i.label]));
    }
  });
});
