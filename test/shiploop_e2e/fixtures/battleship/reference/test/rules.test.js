const test = require('node:test');
const assert = require('node:assert/strict');
const { createGame, fire } = require('../rules');

test('shots report misses, hits, sinks, and the completed game', () => {
  const game = createGame('reference');
  assert.equal(fire(game, 9, 9).result, 'miss');
  assert.equal(fire(game, 0, 0).result, 'hit');
  const firstSink = fire(game, 0, 1);
  assert.equal(firstSink.result, 'sunk');
  assert.equal(firstSink.gameOver, false);
  const lastSink = fire(game, 1, 0);
  assert.equal(lastSink.result, 'sunk');
  assert.equal(lastSink.gameOver, true);
  assert.equal(lastSink.shots, 4);
  assert.equal(lastSink.hits, 3);
});
