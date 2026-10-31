'use strict';
const L = require('./_lib.js');
const C = require('./_cdp.js');
const { check } = L;
L.run(async () => {
  const SEED = 21;
  await C.withPage(SEED, async (page, base, srv) => {
    const fleet = L.fleetOf(SEED);
    await C.ready(page, base, C.ALLOW);
    await C.win(page, fleet);
    const t = await C.statusOf(page);
    check(/five/i.test(t) && /sunk/i.test(t), 'win announcement does not say all five ships are sunk: ' + JSON.stringify(t));
  });
});
