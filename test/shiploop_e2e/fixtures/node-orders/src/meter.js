'use strict';
/** The platform's work meter. tick() counts one unit of work and throws LimitError past LIMIT ticks (a hard limit). */
const LIMIT = 10000;
class LimitError extends Error {}
let ticks = 0;
function tick() {
  ticks += 1;
  if (ticks > LIMIT) throw new LimitError(`meter: more than ${LIMIT} ticks`);
}
function count() { return ticks; }
function reset() { ticks = 0; }
module.exports = { LIMIT, LimitError, tick, count, reset };
