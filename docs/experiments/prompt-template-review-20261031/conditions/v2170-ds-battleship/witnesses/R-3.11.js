'use strict';
const L = require('./_lib.js');
const C = require('./_cdp.js');
const { check } = L;
L.run(async () => {
  let err;
  try { L.rules().createGame({ random: () => 0 }); } catch (e) { err = e; }
  check(err instanceof Error, 'no Error thrown');
  check(/placement|place/i.test(err.message), 'message does not name placement: ' + err.message);
});
