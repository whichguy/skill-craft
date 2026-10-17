'use strict';

/** Return `names` in ascending order as a new array. */
function sortNames(names) {
  if (!Array.isArray(names)) throw new TypeError('names must be an array');
  return names.slice().sort((a, b) => a.localeCompare(b));
}

module.exports = { sortNames };
