'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const { topScores } = require('../src/scores');

test('topScores returns the largest scores, largest first', () => {
  assert.deepEqual(topScores([3, 1, 2], 2), [3, 2]);
  assert.deepEqual(topScores([3, 1, 2], 5), [3, 2, 1]);
});

test('topScores leaves its argument alone and rejects a non-array', () => {
  const scores = [1, 3, 2];
  topScores(scores, 1);
  assert.deepEqual(scores, [1, 3, 2]);
  assert.throws(() => topScores('123', 1), TypeError);
});
