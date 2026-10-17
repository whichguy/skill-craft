'use strict';

/** Return `names` in ascending code-point order (case-sensitive: 'Z' sorts before 'a') as a new array. */
function sortNames(names) {
  if (!Array.isArray(names)) throw new TypeError('names must be an array');
  return names.slice().sort((a, b) => (a < b ? -1 : a > b ? 1 : 0));
}

module.exports = { sortNames };
