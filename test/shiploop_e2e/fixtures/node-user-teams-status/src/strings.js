'use strict';

/** Upper-case the first character of `text`. */
function capitalize(text) {
  if (typeof text !== 'string') throw new TypeError('text must be a string');
  return text.charAt(0).toUpperCase() + text.slice(1);
}

/** Shorten `text` to at most `max` characters, ending in an ellipsis when it was cut. */
function truncate(text, max) {
  if (typeof text !== 'string') throw new TypeError('text must be a string');
  if (!Number.isInteger(max) || max < 1) throw new RangeError('max must be a positive integer');
  return text.length <= max ? text : text.slice(0, max - 1) + '…';
}

module.exports = { capitalize, truncate };
