'use strict';
const L = require('./_lib.js');
const C = require('./_cdp.js');
const { check } = L;
L.run(async () => {
  const SEED = 21;
  await C.withPage(SEED, async (page, base, srv) => {
    const fleet = L.fleetOf(SEED);
    await C.ready(page, base, C.ALLOW);
    const t = await C.text(page); check(/Ships remaining:?\s*5\b/i.test(t), 'the page does not display 5 ships remaining; visible text: ' + JSON.stringify(t.slice(0, 120)));
  });
});
