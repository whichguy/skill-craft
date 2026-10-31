'use strict';
const L = require('./_lib.js');
const C = require('./_cdp.js');
const { check } = L;
L.run(async () => {
  let err, returned;
  try { returned = L.rules().createGame({ random: () => 0 }); } catch (e) { err = e; }
  check(err !== undefined, 'createGame returned instead of throwing');
  check(err instanceof Error, 'the thrown value is not an Error: ' + typeof err);
});
