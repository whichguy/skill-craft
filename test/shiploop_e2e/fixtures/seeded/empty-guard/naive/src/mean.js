'use strict';

/** The arithmetic mean of an array of numbers. */
function mean(values) {
  if (!Array.isArray(values)) throw new TypeError('values must be an array');
  return values.reduce((sum, value) => sum + value, 0) / values.length;
}

module.exports = { mean };
