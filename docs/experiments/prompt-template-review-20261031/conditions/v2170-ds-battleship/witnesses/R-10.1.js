'use strict';
const L = require('./_lib.js');
const C = require('./_cdp.js');
const { check } = L;
L.run(async () => {
  const SEED = 21;
  await C.withPage(SEED, async (page, base, srv) => {
    const fleet = L.fleetOf(SEED);
    await C.ready(page, base, C.ALLOW);
    check(page.news().length === 1, 'the page requested ' + page.news().length + ' games on load');
    await C.shoot(page, 0, 0);
    const b = JSON.parse(page.fires()[0].postData);
    check(typeof b.game === 'string' && /^[0-9a-f-]{36}$/.test(b.game), 'the first shot carried game ' + JSON.stringify(b.game));
  });
});
