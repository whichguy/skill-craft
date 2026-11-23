'use strict';

/**
 * How long the outbox waits before it tries a failed delivery again: 1 s after the first failure, then twice as long
 * after each one, never more than five minutes.
 */

const BASE_MS = 1000;
const MAX_MS = 5 * 60 * 1000;

/** The wait after the `failures`-th failed attempt (1 for the first). */
function delayFor(failures, { base = BASE_MS, max = MAX_MS } = {}) {
  if (!Number.isInteger(failures) || failures < 1) throw new RangeError('failures must be a positive integer');
  return Math.min(max, base * 2 ** (failures - 1));
}

module.exports = { BASE_MS, MAX_MS, delayFor };
