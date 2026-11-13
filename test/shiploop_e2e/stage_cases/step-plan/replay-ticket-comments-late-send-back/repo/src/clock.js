'use strict';

/**
 * The clock the service reads the time from. Code takes a clock instead of calling Date itself, so tests can hold
 * time still and move it on.
 */

const systemClock = Object.freeze({ now: () => new Date() });

/** A clock that stands still until it is moved: for tests. */
function manualClock(start = '2025-09-01T08:00:00.000Z') {
  let current = new Date(start).getTime();
  return {
    now: () => new Date(current),
    advance(ms) {
      current += ms;
    },
    set(iso) {
      current = new Date(iso).getTime();
    },
  };
}

module.exports = { manualClock, systemClock };
