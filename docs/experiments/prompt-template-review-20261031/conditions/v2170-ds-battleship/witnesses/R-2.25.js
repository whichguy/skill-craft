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
    const cs = await page.eval(`(() => { const s = getComputedStyle(document.activeElement); return { os: s.outlineStyle, ow: parseFloat(s.outlineWidth), bs: s.boxShadow }; })()`);
    check((cs.os !== 'none' && cs.ow > 0) || (cs.bs && cs.bs !== 'none'), 'a focused cell shows no focus indicator: ' + JSON.stringify(cs));
  });
});
