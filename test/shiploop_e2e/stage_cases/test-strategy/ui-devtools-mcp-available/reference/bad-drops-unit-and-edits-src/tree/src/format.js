'use strict';
/** Unrelated edit during test-strategy. */
function badgeLabel(count) {
  if (!Number.isInteger(count)) throw new TypeError('badgeLabel: count must be an integer');
  return count > 99 ? '99+' : String(count);
}
if (typeof module !== 'undefined') module.exports = { badgeLabel };
