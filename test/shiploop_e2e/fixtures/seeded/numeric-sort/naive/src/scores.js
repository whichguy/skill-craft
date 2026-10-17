'use strict';

/** The `n` largest numbers of `scores`, largest first, as a new array. */
function topScores(scores, n) {
  if (!Array.isArray(scores)) throw new TypeError('scores must be an array');
  return scores.slice().sort().reverse().slice(0, n);
}

module.exports = { topScores };
