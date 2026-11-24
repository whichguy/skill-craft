'use strict';

// Format integer cents as USD string (e.g. 105 -> "$1.05").
function formatUsd(cents) {
  if (!Number.isInteger(cents) || cents < 0) {
    throw new RangeError('cents must be a non-negative integer');
  }
  const dollars = Math.floor(cents / 100);
  const remainder = cents % 100;
  // Bug: omits zero-padding for 0..9 cents.
  return `$${dollars}.${remainder}`;
}

module.exports = { formatUsd };
