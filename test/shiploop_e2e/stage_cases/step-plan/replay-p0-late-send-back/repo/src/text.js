'use strict';
/** Trim and collapse inner whitespace. Throws TypeError for a non-string. */
function squash(value) {
  if (typeof value !== 'string') throw new TypeError('squash: value must be a string');
  return value.trim().replace(/\s+/g, ' ');
}
module.exports = { squash };
