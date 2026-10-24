'use strict';
/** The price after a percentage discount, rounded to cents. Throws RangeError for a pct outside 0..100. */
const { cents } = require('./money');
function discount(price, pct) {
  if (!Number.isFinite(price) || price < 0) throw new RangeError('discount: price must be a non-negative number');
  if (!Number.isFinite(pct) || pct < 0 || pct > 100) throw new RangeError('discount: pct must be within 0..100');
  return cents(price * (1 - pct / 100));
}
module.exports = { discount };
