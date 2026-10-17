'use strict';

/** The arithmetic mean of an array of numbers; an empty array has the mean 0. */
function mean(values) {
  if (!Array.isArray(values)) throw new TypeError('values must be an array');
  if (values.length === 0) return 0;
  return values.reduce((sum, value) => sum + value, 0) / values.length;
}

module.exports = { mean };
