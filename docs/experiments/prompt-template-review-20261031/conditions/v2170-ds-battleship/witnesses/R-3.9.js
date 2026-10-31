'use strict';
const L = require('./_lib.js');
const C = require('./_cdp.js');
const { check } = L;
L.run(async () => {
  let calls = 0;
  try { L.rules().createGame({ random: () => { calls++; return 0; } }); } catch { /* expected */ }
  // each placement attempt draws orientation, row and column (3 draws); the first ship is placed at the first try,
  // the second can never be placed, so total draws = 3 + 3 * attempts. At most 200 attempts => <= 603 draws.
  check(calls <= 603, 'a source that always returns 0 was consulted ' + calls + ' times (more than 200 attempts)');
  check(calls >= 3, 'the random source was not consulted');
});
