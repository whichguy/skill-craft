'use strict';
const L = require('./_lib.js');
const C = require('./_cdp.js');
const { check } = L;
L.run(async () => {
  let returned, threw = false;
  try { returned = L.rules().createGame({ random: () => 0 }); } catch { threw = true; }
  check(threw, 'createGame returned a fleet for an unplaceable source: ' + JSON.stringify(returned && returned.fleet && returned.fleet.map((s) => s.length)));
});
